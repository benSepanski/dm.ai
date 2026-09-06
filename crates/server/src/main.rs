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

use engine_core::Ruleset;

/// Every shipped ruleset, embedded at compile time. Adding a game is one
/// arm here (and one in the wasm crate) — no registry.
fn shipped_rulesets() -> Vec<Arc<dyn Ruleset>> {
    vec![ruleset_pf2e::embedded()]
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
    let rulesets = shipped_rulesets();
    if let Some(path) = cli.extra_known_versions.as_deref() {
        match version::extra_versions_systems(path) {
            Ok(keys) => {
                for key in keys {
                    if !rulesets.iter().any(|r| r.system() == key) {
                        eprintln!(
                            "--extra-known-versions names system '{key}', which this build does not ship"
                        );
                        std::process::exit(2);
                    }
                }
            }
            Err(e) => {
                eprintln!("{e}");
                std::process::exit(2);
            }
        }
    }
    let mut known = std::collections::BTreeMap::new();
    for rs in &rulesets {
        match version::KnownVersions::assemble(
            rs.system(),
            rs.rules_version(),
            rs.supersedes(),
            rs.shipped_versions_json(),
            cli.extra_known_versions.as_deref(),
        ) {
            Ok(k) => {
                known.insert(rs.system().to_string(), k);
            }
            Err(e) => {
                eprintln!("{e}");
                std::process::exit(2);
            }
        }
    }
    match cli.command {
        Some(Command::Verify) => verify(cli.data_dir, rulesets, known),
        None => serve(cli.data_dir, cli.port, rulesets, known, cli.name_pools),
    }
}

fn verify(
    data_dir: PathBuf,
    rulesets: Vec<Arc<dyn Ruleset>>,
    known: std::collections::BTreeMap<String, version::KnownVersions>,
) {
    let systems: Vec<String> = rulesets.iter().map(|r| r.system().to_string()).collect();
    let store = match Store::open(&data_dir, &systems) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2);
        }
    };
    let campaign = store.campaign_status();
    if let Some(problem) = &campaign.problem {
        println!("CAMPAIGN  {problem}");
    }
    let Some(system) = store.system().map(str::to_string) else {
        println!("verify: this campaign has no resolvable game — nothing verified");
        std::process::exit(if campaign.problem.is_some() { 1 } else { 0 });
    };
    let Some(rs) = rulesets.iter().find(|r| r.system() == system) else {
        eprintln!("this campaign is declared for '{system}', which this build does not ship");
        std::process::exit(2);
    };
    let known = &known[&system];
    let engine = rs.engine();
    let rules_version = rs.rules_version().to_string();
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
            match version::status_for(engine, known, c) {
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
            let advances = tail.iter().filter(|d| rs.is_advance_slot(&d.slot)).count();
            let head_is_advance = tail.first().is_some_and(|d| rs.is_advance_slot(&d.slot));
            if !head_is_advance || advances != 1 {
                failures += 1;
                println!(
                    "TAIL-BAD  {} ({}): the pending level-up's decisions do not start with exactly one level advance — abandon the level-up to recover",
                    c.id, c.sheet.name
                );
            } else if let Err(e) = engine.folds(&c.log) {
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
    rulesets: Vec<Arc<dyn Ruleset>>,
    known: std::collections::BTreeMap<String, version::KnownVersions>,
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
    let systems: Vec<String> = rulesets.iter().map(|r| r.system().to_string()).collect();
    let store = match Store::open(&data_dir, &systems) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(2);
        }
    };

    // Bind: with the lock held, a taken port walks to the next free one
    // (never silently fail to serve). Port 0 lets the OS pick.
    let listener = bind_walking(port);
    let addr = listener
        .local_addr()
        .expect("bound listener has an address");
    let url = format!("http://127.0.0.1:{}", addr.port());
    let _ = persistence::write_lock(&data_dir, &url);

    let app = Arc::new(App {
        rulesets,
        known,
        store: Mutex::new(store),
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
