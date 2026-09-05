//! The dm.ai table server: axum routes over the native engine, crash-safe
//! JSON persistence, and the built UI served from the binary.
//!
//! Run: `cargo run --release -p server -- --data-dir ./campaign`
//! Verify: `cargo run --release -p server -- --data-dir ./campaign verify`

mod clock;
mod persistence;
mod routes;
mod version;

use std::net::{Ipv4Addr, SocketAddr, TcpListener};
use std::path::PathBuf;
use std::sync::Arc;

use axum::http::{header, StatusCode, Uri};
use axum::response::IntoResponse;
use clap::Parser;
use rust_embed::RustEmbed;
use tokio::sync::Mutex;

use persistence::Store;
use routes::App;

#[derive(RustEmbed)]
#[folder = "$CARGO_MANIFEST_DIR/../../ui/dist"]
struct UiAssets;

// Rules data ships inside the binary — same commit, same data, both
// runtimes; a corrupt file is a build-time refusal (parse at startup).
const RULES_MANIFEST: &str = include_str!("../../../rules-data/manifest.json");
const RULES_ANCESTRIES: &str = include_str!("../../../rules-data/ancestries.json");
const RULES_HERITAGES: &str = include_str!("../../../rules-data/heritages.json");
const RULES_ANCESTRY_FEATS: &str = include_str!("../../../rules-data/ancestry-feats.json");
const RULES_BACKGROUNDS: &str = include_str!("../../../rules-data/backgrounds.json");
const RULES_CLASSES: &str = include_str!("../../../rules-data/classes.json");
const RULES_CLASS_FEATS: &str = include_str!("../../../rules-data/class-feats.json");
const RULES_GENERAL_FEATS: &str = include_str!("../../../rules-data/general-feats.json");
const RULES_SKILLS: &str = include_str!("../../../rules-data/skills.json");
const RULES_EQUIPMENT: &str = include_str!("../../../rules-data/equipment.json");
const RULES_SPELLS: &str = include_str!("../../../rules-data/spells.json");
// The lineage record: ID sets of every shipped data version. The server
// only needs its key set — a pin is "older known" when it appears in the
// manifest's supersedes chain AND here.
const RULES_SHIPPED_VERSIONS: &str = include_str!("../../../rules-data/shipped-versions.json");

fn load_rules() -> Result<ruleset_pf2e::RulesData, String> {
    ruleset_pf2e::RulesData::parse(&ruleset_pf2e::RulesDataFiles {
        manifest: RULES_MANIFEST,
        ancestries: RULES_ANCESTRIES,
        heritages: RULES_HERITAGES,
        ancestry_feats: RULES_ANCESTRY_FEATS,
        backgrounds: RULES_BACKGROUNDS,
        classes: RULES_CLASSES,
        class_feats: RULES_CLASS_FEATS,
        general_feats: RULES_GENERAL_FEATS,
        skills: RULES_SKILLS,
        equipment: RULES_EQUIPMENT,
        spells: RULES_SPELLS,
    })
    .map_err(|e| format!("rules data is corrupt — refusing to start: {e}"))
}

#[derive(Parser)]
#[command(name = "dm.ai server", about = "The dm.ai table server")]
struct Cli {
    /// Campaign data directory (created if missing).
    #[arg(long)]
    data_dir: PathBuf,
    /// Port to serve on; taken ports walk to the next free one. 0 = OS pick.
    #[arg(long, default_value_t = 8080)]
    port: u16,
    /// The random-name pools file (app data; read at mint time so edits
    /// need no rebuild). Default resolves against the working directory.
    #[arg(long, default_value = "app-data/name-pools.json")]
    name_pools: PathBuf,
    /// TEST-SUPPORT ONLY (hidden): a JSON file of extra versions to treat
    /// as older-known, same shape as rules-data/shipped-versions.json. The
    /// checks suite uses it to fabricate a prior shipped version; nothing
    /// in production passes it. Its use is announced on stderr.
    #[arg(long, hide = true)]
    extra_known_versions: Option<PathBuf>,
    #[command(subcommand)]
    command: Option<Command>,
}

#[derive(clap::Subcommand)]
enum Command {
    /// Replay every character's decision log and report divergence from the
    /// stored sheet. Never modifies anything.
    Verify,
}

fn main() {
    let cli = Cli::parse();
    let rules = match load_rules() {
        Ok(r) => r,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2);
        }
    };
    let known = match version::KnownVersions::assemble(
        ruleset_pf2e::rules_version(&rules),
        &rules.manifest.supersedes,
        RULES_SHIPPED_VERSIONS,
        cli.extra_known_versions.as_deref(),
    ) {
        Ok(k) => k,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2);
        }
    };
    match cli.command {
        Some(Command::Verify) => verify(cli.data_dir, rules, known),
        None => serve(cli.data_dir, cli.port, rules, known, cli.name_pools),
    }
}

fn verify(data_dir: PathBuf, rules: ruleset_pf2e::RulesData, known: version::KnownVersions) {
    let rules_version = ruleset_pf2e::rules_version(&rules).to_string();
    let engine = ruleset_pf2e::engine(Arc::new(rules));
    let store = match Store::open(&data_dir) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2);
        }
    };
    let load = match store.load_all() {
        Ok(l) => l,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2);
        }
    };
    let mut failures = 0;
    for (file, message) in &load.problems {
        failures += 1;
        println!("CORRUPT   {file}: {message}");
    }
    for c in &load.characters {
        if c.rules_version != rules_version {
            // Older-known pins replay against current data; unknown pins
            // cannot. The version guard's load-time statuses, in print.
            match version::status_for(&engine, &known, c) {
                types::VersionStatus::KeptOld {
                    pinned,
                    evaluated_against,
                } => {
                    println!(
                        "KEPT-OLD  {} ({}): pins older known version '{pinned}'; keeping the old derivation was recorded (evaluated against '{evaluated_against}') — not re-flagged",
                        c.id, c.sheet.name
                    );
                }
                types::VersionStatus::OlderKnown {
                    pinned, outcome, ..
                } => match outcome {
                    types::ReplayOutcome::Identical => {
                        println!(
                            "OLD-IDENT {} ({}): pins older known version '{pinned}'; replay against current '{rules_version}' is identical — eligible for re-pin",
                            c.id, c.sheet.name
                        );
                    }
                    types::ReplayOutcome::Divergent { differences } => {
                        failures += 1;
                        println!(
                            "OLD-DIVER {} ({}): pins older known version '{pinned}'; replay against current '{rules_version}' diverges — flagged for review, the stored sheet remains what the app loads",
                            c.id, c.sheet.name
                        );
                        for d in &differences {
                            println!(
                                "          {} / {}: stored '{}', replay '{}'",
                                d.section, d.label, d.old, d.new
                            );
                        }
                    }
                    types::ReplayOutcome::ReplayError {
                        message,
                        failing_decision,
                        ..
                    } => {
                        failures += 1;
                        println!(
                            "OLD-BROKE {} ({}): pins older known version '{pinned}'; log does not replay against current '{rules_version}' (failing decision '{failing_decision}': {message}) — accept unavailable until resolved",
                            c.id, c.sheet.name
                        );
                    }
                },
                _ => {
                    failures += 1;
                    println!(
                        "UNKNOWN   {}: pins rules-data version '{}' (this build ships '{}') — not an older known version, replay impossible; the materialized sheet still loads",
                        c.id, c.rules_version, rules_version
                    );
                }
            }
            continue;
        }
        // A pending level's tail must fold cleanly on top of the prefix,
        // and must be one level's decisions: an advance at its head, and
        // only one. The stored sheet is judged against the prefix alone.
        if c.has_pending_tail() {
            let tail = c.pending_tail();
            let advances = tail
                .iter()
                .filter(|d| ruleset_pf2e::advance_level_of(d.slot.as_str()).is_some())
                .count();
            let head_is_advance = tail
                .first()
                .is_some_and(|d| ruleset_pf2e::advance_level_of(d.slot.as_str()).is_some());
            if !head_is_advance || advances != 1 {
                failures += 1;
                println!(
                    "TAIL-BAD  {} ({}): the pending level-up's decisions do not start with exactly one level advance — abandon the level-up to recover",
                    c.id, c.sheet.name
                );
            } else if let Err(e) = engine.fold(&c.log) {
                failures += 1;
                println!(
                    "TAIL-BROKE {} ({}): the pending level-up no longer replays: {e} — abandon the level-up to recover",
                    c.id, c.sheet.name
                );
            }
        }
        match engine.sheet(c.finalized_prefix()) {
            Ok(replayed) if replayed == c.sheet => {
                println!("OK        {} ({})", c.id, c.sheet.name);
            }
            Ok(replayed) => {
                failures += 1;
                println!("DIVERGED  {} ({}): stored sheet does not match replay of its decision log — the file was hand-edited or the rules changed. The stored sheet remains what the app loads.", c.id, c.sheet.name);
                for section in &replayed.sections {
                    for entry in &section.entries {
                        if c.sheet
                            .entry(&section.title, &entry.label)
                            .map(|e| &e.value)
                            != Some(&entry.value)
                        {
                            println!(
                                "          {} / {}: stored '{}', replay '{}'",
                                section.title,
                                entry.label,
                                c.sheet
                                    .entry(&section.title, &entry.label)
                                    .map(|e| e.value.as_str())
                                    .unwrap_or("<missing>"),
                                entry.value
                            );
                        }
                    }
                }
            }
            Err(e) => {
                failures += 1;
                println!("BROKEN    {}: decision log does not replay: {e}", c.id);
            }
        }
    }
    println!(
        "verify: {} character(s), {failures} problem(s)",
        load.characters.len() + load.problems.len()
    );
    if failures > 0 {
        std::process::exit(1);
    }
}

fn serve(
    data_dir: PathBuf,
    port: u16,
    rules: ruleset_pf2e::RulesData,
    known: version::KnownVersions,
    name_pools: PathBuf,
) {
    if let Err(e) = std::fs::create_dir_all(&data_dir) {
        eprintln!("cannot create data directory: {e}");
        std::process::exit(2);
    }
    if let Err(e) = persistence::acquire_lock(&data_dir) {
        eprintln!("{e}");
        std::process::exit(3);
    }
    let store = match Store::open(&data_dir) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2);
        }
    };

    let notice = &rules.manifest.license_notice;
    let license_notice = format!(
        "{}\n\n{}\n\n{}",
        notice.orc_notice, notice.attribution, notice.reserved
    );
    let rules_version = ruleset_pf2e::rules_version(&rules).to_string();
    // Per-class suggested builds, resolved from the class records before the
    // data moves into the engine.
    let suggested = ruleset_pf2e::suggested_builds(&rules);
    let rules = Arc::new(rules);
    let engine = ruleset_pf2e::engine(rules.clone());

    // Bind: with the lock held, a taken port walks to the next free one
    // (never silently fail to serve). Port 0 lets the OS pick.
    let listener = bind_walking(port);
    let addr = listener
        .local_addr()
        .expect("bound listener has an address");
    let url = format!("http://127.0.0.1:{}", addr.port());
    let _ = persistence::write_lock(&data_dir, &url);

    let app = Arc::new(App {
        engine,
        rules,
        store: Mutex::new(store),
        rules_version,
        known,
        license_notice,
        suggested,
        name_pools,
    });

    println!("Serving at {url}");

    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .expect("tokio runtime");
    runtime.block_on(async move {
        listener
            .set_nonblocking(true)
            .expect("nonblocking listener");
        let listener = tokio::net::TcpListener::from_std(listener).expect("tokio listener");
        let router = routes::router(app).fallback(static_assets);
        axum::serve(listener, router).await.expect("server run");
    });
}

fn bind_walking(port: u16) -> TcpListener {
    let mut candidate = port;
    loop {
        let addr = SocketAddr::from((Ipv4Addr::LOCALHOST, candidate));
        match TcpListener::bind(addr) {
            Ok(l) => return l,
            Err(e) if candidate != 0 && candidate < port.saturating_add(20) => {
                eprintln!(
                    "port {candidate} unavailable ({e}); trying {}",
                    candidate + 1
                );
                candidate += 1;
            }
            Err(e) => {
                eprintln!("could not bind a port: {e}");
                std::process::exit(2);
            }
        }
    }
}

async fn static_assets(uri: Uri) -> impl IntoResponse {
    let path = uri.path().trim_start_matches('/');
    let path = if path.is_empty() { "index.html" } else { path };
    match UiAssets::get(path) {
        Some(file) => {
            let mime = mime_guess::from_path(path).first_or_octet_stream();
            (
                [(header::CONTENT_TYPE, mime.as_ref().to_string())],
                file.data.into_owned(),
            )
                .into_response()
        }
        None if !path.starts_with("api/") => {
            // SPA fallback: unknown non-API paths get the app shell.
            match UiAssets::get("index.html") {
                Some(file) => (
                    [(header::CONTENT_TYPE, "text/html".to_string())],
                    file.data.into_owned(),
                )
                    .into_response(),
                None => StatusCode::NOT_FOUND.into_response(),
            }
        }
        None => StatusCode::NOT_FOUND.into_response(),
    }
}
