//! The only code that touches the filesystem. Every write is temp-file →
//! fsync → atomic rename; deletes are renames into `trash/`; unreadable
//! files are quarantined (renamed aside) and reported, never blocking the
//! rest of the roster; nothing is ever rewritten on load.

mod storage;

use std::fs;
use std::io::Write as _;
use std::path::{Path, PathBuf};

use types::{CharacterId, Decision, SheetView, StepId};

pub(crate) use storage::DocState;
use storage::{parse_doc, CharacterDoc, ParsedDoc, SCHEMA_VERSION};

use crate::clock;

#[derive(Debug, thiserror::Error)]
pub(crate) enum StoreError {
    #[error("character '{0}' not found")]
    NotFound(CharacterId),
    #[error("data directory error: {0}")]
    Io(#[from] std::io::Error),
    #[error("{0}")]
    Storage(String),
}

/// A loaded character, handed to routes as data (not the storage struct).
pub(crate) struct Loaded {
    pub id: CharacterId,
    pub state: DocState,
    pub current_step: StepId,
    pub draft_version: u64,
    pub sheet: SheetView,
    pub log: Vec<Decision>,
    pub rules_version: String,
}

impl From<CharacterDoc> for Loaded {
    fn from(doc: CharacterDoc) -> Self {
        Loaded {
            id: CharacterId::new(doc.id),
            state: doc.state,
            current_step: doc.current_step,
            draft_version: doc.draft_version,
            sheet: doc.sheet,
            log: doc.log,
            rules_version: doc.rules_version,
        }
    }
}

pub(crate) struct RosterLoad {
    pub characters: Vec<Loaded>,
    pub problems: Vec<(String, String)>,
}

pub(crate) struct Store {
    data_dir: PathBuf,
}

impl Store {
    /// Open the data directory: create the layout, sweep stray temp files
    /// into trash, and refuse to open if any character file was written by
    /// a newer schema (downgrade guard).
    pub fn open(data_dir: &Path) -> Result<Store, StoreError> {
        fs::create_dir_all(data_dir.join("characters"))?;
        fs::create_dir_all(data_dir.join("trash"))?;
        let store = Store {
            data_dir: data_dir.to_path_buf(),
        };
        store.sweep_temp_files()?;
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

    /// Stray temp files from a crash mid-write are moved to trash on start.
    fn sweep_temp_files(&self) -> Result<(), StoreError> {
        for entry in fs::read_dir(self.characters_dir())?.flatten() {
            let path = entry.path();
            let name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");
            if name.contains(".tmp-") {
                let _ = self.move_to_trash(&path);
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

    /// Load every character; unreadable files are quarantined and reported,
    /// the rest of the roster loads. Nothing is rewritten.
    pub fn load_all(&self) -> Result<RosterLoad, StoreError> {
        let mut characters = Vec::new();
        let mut problems = Vec::new();
        for path in self.character_files()? {
            match fs::read_to_string(&path) {
                Ok(text) => match parse_doc(&text) {
                    ParsedDoc::Ok(doc) => characters.push(doc.into()),
                    ParsedDoc::NewerSchema { version } => {
                        // Startup guard normally catches this; report it
                        // rather than quarantining a healthy future file.
                        problems.push((
                            path.file_name()
                                .and_then(|n| n.to_str())
                                .unwrap_or("unknown")
                                .to_string(),
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
            ParsedDoc::Ok(doc) => Ok(doc.into()),
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
            rules_version: loaded.rules_version.clone(),
            state: loaded.state,
            current_step: loaded.current_step.clone(),
            draft_version: loaded.draft_version,
            sheet: loaded.sheet.clone(),
            log: loaded.log.clone(),
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
