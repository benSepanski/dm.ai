//! The only code that touches the filesystem. Every write is temp-file →
//! fsync → atomic rename; deletes are renames into `trash/`; unreadable
//! files are quarantined (renamed aside) and reported, never blocking the
//! rest of the roster; nothing is ever rewritten on load.
//!
//! The campaign declaration (`campaign.json` at the data-dir root) is store
//! state too: read when the store opens, written create-exclusively the
//! first time and by rename when changed while the campaign is empty. A
//! character file from another game is refused in place — reported, never
//! loaded, never written, never moved.

mod storage;

use std::fs;
use std::io::Write as _;
use std::path::{Path, PathBuf};

use types::{CharacterId, Decision, SheetView, StepId};

use storage::{parse_doc, CharacterDoc, ParsedDoc, SCHEMA_VERSION};
pub(crate) use storage::{DocState, KeepOldMarker, VersionEvent};

use crate::clock;

/// The declaration file's name and its one-line content shape, named in
/// every message that asks Ben to fix one by hand.
pub(crate) const DECLARATION_FILE: &str = "campaign.json";
const DECLARATION_SCHEMA: u32 = 1;

#[derive(Debug, thiserror::Error)]
pub(crate) enum StoreError {
    #[error("character '{0}' not found")]
    NotFound(CharacterId),
    #[error("data directory error: {0}")]
    Io(#[from] std::io::Error),
    #[error("{0}")]
    Storage(String),
    /// A valid file in the wrong context (another game's character, or a
    /// system field disagreeing with its pin): refused in place, typed.
    #[error("{0}")]
    Refused(String),
}

/// A loaded character, handed to routes as data (not the storage struct).
pub(crate) struct Loaded {
    pub id: CharacterId,
    /// The game this character belongs to (explicit on v5 files; inferred
    /// from a registered pin prefix, else PF2e, on older files).
    pub system: String,
    pub state: DocState,
    pub current_step: StepId,
    pub draft_version: u64,
    pub sheet: SheetView,
    pub log: Vec<Decision>,
    /// How many decisions the stored sheet reflects: the finalized prefix.
    /// 0 on a creation draft; the log length on a finalized character with
    /// no pending level; less than the log length while a level is pending.
    pub finalized_through: usize,
    pub rules_version: String,
    /// Recorded version-resolution actions; preserved by every save.
    pub version_history: Vec<VersionEvent>,
    /// Standing keep-old decision, if any; preserved by every save.
    pub keep_old: Option<KeepOldMarker>,
}

impl Loaded {
    /// The part of the log the stored sheet reflects — the ONLY thing
    /// verify, version status, version accept, and clone ever fold: the
    /// whole log for a creation draft (its sheet tracks every confirm),
    /// the finalized prefix for a finalized character (a pending level's
    /// tail is never part of the stored sheet).
    pub fn finalized_prefix(&self) -> &[Decision] {
        match self.state {
            DocState::Draft => &self.log,
            DocState::Finalized => &self.log[..self.finalized_through.min(self.log.len())],
        }
    }

    /// The pending level's decisions (empty when none is pending).
    pub fn pending_tail(&self) -> &[Decision] {
        &self.log[self.finalized_through.min(self.log.len())..]
    }

    pub fn has_pending_tail(&self) -> bool {
        self.state == DocState::Finalized && self.finalized_through < self.log.len()
    }
}

/// The system id a rules-version pin names, when its prefix is one of the
/// registered systems (`<system>-<source>.<semver>`).
fn registered_prefix<'a>(rules_version: &str, systems: &'a [String]) -> Option<&'a str> {
    systems
        .iter()
        .find(|s| {
            rules_version
                .strip_prefix(s.as_str())
                .is_some_and(|rest| rest.starts_with('-'))
        })
        .map(String::as_str)
}

/// The game a document belongs to: its explicit field, else its pin's
/// registered prefix, else PF2e (every pre-slice file). A field that
/// disagrees with a registered prefix is a refusal, not an inference.
fn document_system(doc: &CharacterDoc, systems: &[String]) -> Result<String, String> {
    let prefix = registered_prefix(&doc.rules_version, systems);
    match (&doc.system, prefix) {
        (Some(field), Some(prefix)) if field != prefix => Err(format!(
            "names game '{field}' but pins rules-data version '{}' of game '{prefix}'",
            doc.rules_version
        )),
        (Some(field), _) => Ok(field.clone()),
        (None, Some(prefix)) => Ok(prefix.to_string()),
        (None, None) => Ok("pf2e".to_string()),
    }
}

fn loaded_from(doc: CharacterDoc, system: String) -> Loaded {
    // Pre-v4 files carry no marker: a draft's whole log is pending
    // creation work (0), a finalized file's whole log is reflected by
    // its sheet (the log length). Never written back by loading.
    // A finalized document can never carry a marker of 0 (the creation
    // prefix is never empty), so 0 on a finalized file is "unset" — a
    // hand-flipped state on a draft file — and reads as the log length.
    let finalized_through = match (doc.state, doc.finalized_through) {
        (DocState::Draft, _) => 0,
        (DocState::Finalized, Some(marker)) if marker > 0 => marker,
        (DocState::Finalized, _) => doc.log.len(),
    };
    Loaded {
        id: CharacterId::new(doc.id),
        system,
        state: doc.state,
        current_step: doc.current_step,
        draft_version: doc.draft_version,
        sheet: doc.sheet,
        log: doc.log,
        finalized_through,
        rules_version: doc.rules_version,
        version_history: doc.version_history,
        keep_old: doc.keep_old,
    }
}

pub(crate) struct RosterLoad {
    pub characters: Vec<Loaded>,
    pub problems: Vec<(String, String)>,
}

/// The campaign declaration as read from disk.
#[derive(Debug, Clone, PartialEq, Eq)]
enum Declaration {
    Absent,
    Declared(String),
    Corrupt(String),
}

/// Where the campaign stands on its game, for the campaign view and
/// `verify`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct CampaignStatus {
    /// The game the campaign plays, when it can be resolved (declared, or
    /// inferred PF2e for an undeclared directory that holds characters).
    pub system: Option<String>,
    /// True when the system was inferred rather than declared.
    pub inferred: bool,
    /// Why no game could be resolved (corrupt or missing declaration),
    /// render-ready and naming the fix.
    pub problem: Option<String>,
}

pub(crate) struct Store {
    data_dir: PathBuf,
    /// Every shipped system id (declaration values and pin prefixes).
    systems: Vec<String>,
    declaration: Declaration,
}

impl Store {
    /// Open the data directory: create the layout, sweep stray temp files
    /// into trash, read the declaration, and refuse to open if any
    /// character file was written by a newer schema (downgrade guard).
    pub fn open(data_dir: &Path, systems: &[String]) -> Result<Store, StoreError> {
        fs::create_dir_all(data_dir.join("characters"))?;
        fs::create_dir_all(data_dir.join("trash"))?;
        let mut store = Store {
            data_dir: data_dir.to_path_buf(),
            systems: systems.to_vec(),
            declaration: Declaration::Absent,
        };
        store.sweep_temp_files()?;
        store.declaration = store.read_declaration();
        // Downgrade guard.
        for path in store.character_files()? {
            let Ok(text) = fs::read_to_string(&path) else {
                continue;
            };
            if let ParsedDoc::NewerSchema { version } = parse_doc(&text) {
                return Err(StoreError::Storage(format!(
                    "{} has schema version {version}, but this build understands only {SCHEMA_VERSION}. \
                     The data directory was written by a newer dm.ai — refusing to open it.",
                    path.display()
                )));
            }
        }
        Ok(store)
    }

    fn declaration_path(&self) -> PathBuf {
        self.data_dir.join(DECLARATION_FILE)
    }

    fn read_declaration(&self) -> Declaration {
        let path = self.declaration_path();
        let text = match fs::read_to_string(&path) {
            Ok(t) => t,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Declaration::Absent,
            Err(e) => return Declaration::Corrupt(format!("could not be read ({e})")),
        };
        let value: serde_json::Value = match serde_json::from_str(&text) {
            Ok(v) => v,
            Err(e) => return Declaration::Corrupt(format!("is not valid JSON ({e})")),
        };
        let Some(system) = value.get("system").and_then(|s| s.as_str()) else {
            return Declaration::Corrupt("has no \"system\" field".into());
        };
        if !self.systems.iter().any(|s| s == system) {
            return Declaration::Corrupt(format!(
                "names game '{system}', which this build does not ship"
            ));
        }
        Declaration::Declared(system.to_string())
    }

    /// The game this campaign plays, if it can be resolved: the declared
    /// system; else, for an undeclared directory that holds characters,
    /// PF2e — unless a file names another game, which is a missing
    /// declaration, never an inference.
    pub fn system(&self) -> Option<&str> {
        match &self.declaration {
            Declaration::Declared(s) => Some(s),
            Declaration::Corrupt(_) => None,
            Declaration::Absent => {
                let (has_files, foreign) = self.undeclared_scan();
                if has_files && foreign.is_none() {
                    Some("pf2e")
                } else {
                    None
                }
            }
        }
    }

    /// For an undeclared directory: whether any character file exists, and
    /// the first file that names a game other than PF2e.
    fn undeclared_scan(&self) -> (bool, Option<(String, String)>) {
        let files = self.character_files().unwrap_or_default();
        let mut foreign = None;
        for path in &files {
            let Ok(text) = fs::read_to_string(path) else {
                continue;
            };
            if let ParsedDoc::Ok(doc) = parse_doc(&text) {
                if let Ok(system) = document_system(&doc, &self.systems) {
                    if system != "pf2e" && foreign.is_none() {
                        let file = path
                            .file_name()
                            .and_then(|n| n.to_str())
                            .unwrap_or("unknown")
                            .to_string();
                        foreign = Some((file, system));
                    }
                }
            }
        }
        (!files.is_empty(), foreign)
    }

    pub fn campaign_status(&self) -> CampaignStatus {
        match &self.declaration {
            Declaration::Declared(s) => CampaignStatus {
                system: Some(s.clone()),
                inferred: false,
                problem: None,
            },
            Declaration::Corrupt(why) => CampaignStatus {
                system: None,
                inferred: false,
                problem: Some(format!(
                    "the campaign declaration {} {why} — fix or remove the file (its content is one line: {{\"schema_version\": {DECLARATION_SCHEMA}, \"system\": \"<game>\"}})",
                    self.declaration_path().display()
                )),
            },
            Declaration::Absent => {
                let (has_files, foreign) = self.undeclared_scan();
                match (has_files, foreign) {
                    (true, Some((file, system))) => CampaignStatus {
                        system: None,
                        inferred: false,
                        problem: Some(format!(
                            "this campaign has no declaration, but {file} names game '{system}' — write {} with the one line {{\"schema_version\": {DECLARATION_SCHEMA}, \"system\": \"{system}\"}}",
                            self.declaration_path().display()
                        )),
                    },
                    (true, None) => CampaignStatus {
                        system: Some("pf2e".to_string()),
                        inferred: true,
                        problem: None,
                    },
                    (false, _) => CampaignStatus {
                        system: None,
                        inferred: false,
                        problem: None,
                    },
                }
            }
        }
    }

    /// Whether the campaign holds no character: no `.json` in
    /// `characters/`, `trash/`, or `quarantine/` whose stem is not a swept
    /// temp. A swept temp never fixes the game; a trashed or quarantined
    /// character always does.
    pub fn is_empty(&self) -> bool {
        for sub in ["characters", "trash", "quarantine"] {
            let Ok(entries) = fs::read_dir(self.data_dir.join(sub)) else {
                continue;
            };
            for entry in entries.flatten() {
                let path = entry.path();
                let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
                if name.contains(".tmp-") {
                    continue;
                }
                if path.extension().is_some_and(|e| e == "json") {
                    return false;
                }
            }
        }
        true
    }

    /// Declare (or, while the campaign is empty, change) the game. The
    /// first declaration is create-exclusive: a temp at the root, fsync,
    /// hard-link to the declaration name (fails if one exists), unlink the
    /// temp. A change is temp → fsync → rename. Anything else refuses,
    /// typed, and writes nothing.
    pub fn declare(&mut self, system: &str) -> Result<(), StoreError> {
        if !self.systems.iter().any(|s| s == system) {
            return Err(StoreError::Refused(format!(
                "'{system}' is not a game this build ships"
            )));
        }
        if !self.is_empty() {
            return Err(StoreError::Refused(match &self.declaration {
                Declaration::Declared(current) if current == system => {
                    format!("this campaign already plays {system}")
                }
                Declaration::Declared(current) => format!(
                    "this campaign plays {current} and holds characters — its game cannot change"
                ),
                _ => "this campaign already holds characters — its game is fixed (an undeclared campaign with characters is Pathfinder 2e)".to_string(),
            }));
        }
        let text = format!(
            "{{\n  \"schema_version\": {DECLARATION_SCHEMA},\n  \"system\": \"{system}\"\n}}\n"
        );
        let target = self.declaration_path();
        let tmp = self
            .data_dir
            .join(format!("{DECLARATION_FILE}.tmp-{}", std::process::id()));
        {
            let mut f = fs::File::create(&tmp)?;
            f.write_all(text.as_bytes())?;
            f.sync_all()?;
        }
        let outcome = match &self.declaration {
            Declaration::Absent => {
                // Create-exclusive: a racing second declaration fails here.
                let linked = fs::hard_link(&tmp, &target);
                // The temp is a second directory entry for the very bytes
                // now linked under the declaration name — unlinking it
                // loses nothing, so the never-unlink rule (which protects
                // character data) is deliberately not applied here.
                #[allow(clippy::disallowed_methods)]
                let _ = fs::remove_file(&tmp);
                linked.map_err(|e| {
                    if e.kind() == std::io::ErrorKind::AlreadyExists {
                        StoreError::Refused(
                            "this campaign was declared a moment ago — reload".into(),
                        )
                    } else {
                        StoreError::Io(e)
                    }
                })
            }
            _ => fs::rename(&tmp, &target).map_err(StoreError::Io),
        };
        if let Ok(dir) = fs::File::open(&self.data_dir) {
            let _ = dir.sync_all();
        }
        outcome?;
        self.declaration = self.read_declaration();
        Ok(())
    }

    fn characters_dir(&self) -> PathBuf {
        self.data_dir.join("characters")
    }

    fn character_path(&self, id: &CharacterId) -> PathBuf {
        self.characters_dir().join(format!("{id}.json"))
    }

    fn character_files(&self) -> Result<Vec<PathBuf>, StoreError> {
        let mut files: Vec<PathBuf> = fs::read_dir(self.characters_dir())?
            .flatten()
            .map(|e| e.path())
            .filter(|p| p.extension().is_some_and(|e| e == "json"))
            .collect();
        files.sort();
        Ok(files)
    }

    /// Stray temp files from a crash mid-write are moved to trash on start
    /// — character temps under `characters/`, declaration temps at the
    /// root.
    fn sweep_temp_files(&self) -> Result<(), StoreError> {
        for dir in [self.characters_dir(), self.data_dir.clone()] {
            for entry in fs::read_dir(&dir)?.flatten() {
                let path = entry.path();
                if path.is_dir() {
                    continue;
                }
                let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
                if name.contains(".tmp-") {
                    let _ = self.move_to_trash(&path);
                }
            }
        }
        Ok(())
    }

    /// Rename a file into trash/ under a timestamped name that never
    /// overwrites an earlier trashed copy. The app never unlinks.
    fn move_to_trash(&self, path: &Path) -> Result<PathBuf, StoreError> {
        let stem = path.file_stem().and_then(|s| s.to_str()).unwrap_or("file");
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("json");
        let mut candidate = self
            .data_dir
            .join("trash")
            .join(format!("{stem}-{}.{ext}", clock::now_millis()));
        let mut n = 0;
        while candidate.exists() {
            n += 1;
            candidate = self
                .data_dir
                .join("trash")
                .join(format!("{stem}-{}-{n}.{ext}", clock::now_millis()));
        }
        fs::rename(path, &candidate)?;
        Ok(candidate)
    }

    /// Quarantine an unreadable file: rename aside into quarantine/. The
    /// report is produced even when the rename itself fails.
    fn quarantine(&self, path: &Path, message: &str) -> (String, String) {
        let file = path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown")
            .to_string();
        let qdir = self.data_dir.join("quarantine");
        let attempted = fs::create_dir_all(&qdir).and_then(|_| {
            let dest = qdir.join(format!("{file}.{}", clock::now_millis()));
            fs::rename(path, &dest)
        });
        let note = match attempted {
            Ok(_) => format!("could not be read — quarantined ({message})"),
            Err(e) => format!(
                "could not be read ({message}); quarantine failed too ({e}) — file left in place"
            ),
        };
        (file, note)
    }

    /// Admit a parsed document into this campaign, or say why it is
    /// refused in place (never moved, never written).
    fn admit(&self, doc: CharacterDoc) -> Result<Loaded, String> {
        let system = document_system(&doc, &self.systems)?;
        match self.system() {
            Some(campaign) if campaign == system => Ok(loaded_from(doc, system)),
            Some(campaign) => Err(format!(
                "belongs to a {} campaign, and this campaign plays {} — copy it into a campaign of its game; the file is untouched",
                system, campaign
            )),
            None => Err(
                "this campaign has no resolvable game, so no character can load — see the campaign declaration".to_string(),
            ),
        }
    }

    /// Load every character; unreadable files are quarantined and reported,
    /// files from another game are refused in place and reported, the rest
    /// of the roster loads. Nothing is rewritten.
    pub fn load_all(&self) -> Result<RosterLoad, StoreError> {
        let mut characters = Vec::new();
        let mut problems = Vec::new();
        for path in self.character_files()? {
            let file = path
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("unknown")
                .to_string();
            match fs::read_to_string(&path) {
                Ok(text) => match parse_doc(&text) {
                    ParsedDoc::Ok(doc) => match self.admit(*doc) {
                        Ok(loaded) => characters.push(loaded),
                        Err(why) => problems.push((file, format!("{why} — not loaded"))),
                    },
                    ParsedDoc::NewerSchema { version } => {
                        // Startup guard normally catches this; report it
                        // rather than quarantining a healthy future file.
                        problems.push((
                            file,
                            format!("written by a newer dm.ai (schema {version}) — not loaded"),
                        ));
                    }
                    ParsedDoc::Corrupt { message } => {
                        problems.push(self.quarantine(&path, &message));
                    }
                },
                Err(e) => problems.push(self.quarantine(&path, &e.to_string())),
            }
        }
        Ok(RosterLoad {
            characters,
            problems,
        })
    }

    pub fn load(&self, id: &CharacterId) -> Result<Loaded, StoreError> {
        let path = self.character_path(id);
        let text = fs::read_to_string(&path).map_err(|_| StoreError::NotFound(id.clone()))?;
        match parse_doc(&text) {
            ParsedDoc::Ok(doc) => self.admit(*doc).map_err(StoreError::Refused),
            ParsedDoc::NewerSchema { version } => Err(StoreError::Storage(format!(
                "written by a newer dm.ai (schema {version})"
            ))),
            ParsedDoc::Corrupt { message } => Err(StoreError::Storage(message)),
        }
    }

    /// Durably persist a character: temp file in the same directory, fsync,
    /// atomic rename over the target, fsync the directory.
    pub fn save(&self, loaded: &Loaded) -> Result<(), StoreError> {
        let doc = CharacterDoc {
            schema_version: SCHEMA_VERSION,
            id: loaded.id.to_string(),
            system: Some(loaded.system.clone()),
            rules_version: loaded.rules_version.clone(),
            state: loaded.state,
            current_step: loaded.current_step.clone(),
            draft_version: loaded.draft_version,
            sheet: loaded.sheet.clone(),
            log: loaded.log.clone(),
            finalized_through: Some(loaded.finalized_through),
            version_history: loaded.version_history.clone(),
            keep_old: loaded.keep_old.clone(),
        };
        let target = self.character_path(&loaded.id);
        let tmp = self
            .characters_dir()
            .join(format!("{}.tmp-{}", loaded.id, std::process::id()));
        let text =
            serde_json::to_string_pretty(&doc).map_err(|e| StoreError::Storage(e.to_string()))?;
        {
            let mut f = fs::File::create(&tmp)?;
            f.write_all(text.as_bytes())?;
            f.sync_all()?;
        }
        fs::rename(&tmp, &target)?;
        if let Ok(dir) = fs::File::open(self.characters_dir()) {
            let _ = dir.sync_all();
        }
        Ok(())
    }

    /// Move a character's file to trash/ (recoverable by hand, invisible
    /// to the app).
    pub fn delete(&self, id: &CharacterId) -> Result<(), StoreError> {
        let path = self.character_path(id);
        if !path.exists() {
            return Err(StoreError::NotFound(id.clone()));
        }
        self.move_to_trash(&path)?;
        Ok(())
    }

    pub fn mint_character_id(&self) -> CharacterId {
        CharacterId::new(format!("c-{}", clock::mint_id()))
    }
}

/// The pid-checked data-dir lockfile: a second instance refuses to start
/// instead of becoming a silent second authority. Stale locks (dead pid)
/// are taken over; the lock is never unlinked.
pub(crate) fn acquire_lock(data_dir: &Path) -> Result<(), String> {
    let path = data_dir.join("server.lock");
    if let Ok(text) = fs::read_to_string(&path) {
        let mut lines = text.lines();
        if let Some(pid) = lines.next().and_then(|l| l.trim().parse::<i32>().ok()) {
            let alive = pid > 0 && unsafe_kill_probe(pid);
            if alive && pid != std::process::id() as i32 {
                let url = lines.next().unwrap_or("<unknown>");
                return Err(format!(
                    "this data directory is already being served by process {pid} at {url} — \
                     refusing to start a second instance"
                ));
            }
        }
    }
    write_lock(data_dir, "<starting>")
}

/// Record the bound URL in the lockfile so the refusal message can name it.
pub(crate) fn write_lock(data_dir: &Path, url: &str) -> Result<(), String> {
    let path = data_dir.join("server.lock");
    fs::write(&path, format!("{}\n{url}\n", std::process::id()))
        .map_err(|e| format!("could not write lockfile: {e}"))
}

/// kill(pid, 0) probes liveness without sending a signal.
fn unsafe_kill_probe(pid: i32) -> bool {
    // Safety-free wrapper: libc::kill with signal 0 only checks existence.
    #[allow(unsafe_code)]
    unsafe {
        libc::kill(pid, 0) == 0
    }
}
