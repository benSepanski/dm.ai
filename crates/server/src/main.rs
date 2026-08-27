//! The dm.ai table server: axum routes over the native engine, crash-safe
//! JSON persistence, and the built UI served from the binary.
//!
//! Run: `cargo run --release -p server -- --data-dir ./campaign`
//! Verify: `cargo run --release -p server -- --data-dir ./campaign verify`

mod clock;
mod persistence;
mod routes;

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
    match cli.command {
        Some(Command::Verify) => verify(cli.data_dir, rules),
        None => serve(cli.data_dir, cli.port, rules),
    }
}

fn verify(data_dir: PathBuf, rules: ruleset_pf2e::RulesData) {
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
            failures += 1;
            println!(
                "UNKNOWN   {}: pins rules-data version '{}' (this build ships '{}') — replay impossible; the materialized sheet still loads",
                c.id, c.rules_version, rules_version
            );
            continue;
        }
        match engine.sheet(&c.log) {
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

fn serve(data_dir: PathBuf, port: u16, rules: ruleset_pf2e::RulesData) {
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
    let engine = ruleset_pf2e::engine(Arc::new(rules));

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
        store: Mutex::new(store),
        rules_version,
        license_notice,
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
