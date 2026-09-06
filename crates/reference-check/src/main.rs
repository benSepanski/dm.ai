//! reference-check — compares shipped rules-data against a pinned,
//! content-hash-verified ground-truth snapshot and writes the committed
//! attestation (`rules-data/<system>/attestation.json`).
//!
//! Two systems, two sources, two comparators, one attestation schema
//! (architecture chargen-dnd, "Attestation gets a second source under one
//! top-level schema"): `--system pf2e` (the default) matches against a
//! Foundry pf2e release tag; `--system dnd5e` matches against a pinned
//! commit of a Markdown mirror of SRD 5.2.1 that also carries the official
//! PDF (hash-verified inside the tarball). A `match` on the system selects
//! the source and comparator — there is no source trait.
//!
//! Subcommands:
//!   fetch   download the pinned ground-truth tarball into the gitignored
//!           `.reference-cache/<system>/`, verify it against the pinned
//!           sha256, and extract the subset the matcher reads. The only
//!           network-touching path in the repo's tooling.
//!   attest  verify the cache against the pin (never attest against
//!           unverified content), match every shipped record, and write the
//!           attestation. Offline once the cache exists.
//!
//! Trust chain (architecture doc, "Trust must be mechanical"): pinned
//! snapshot -> deliberate tool run -> committed attestation -> offline CI
//! check (`checks/attestation.rs`). HARD RULE: no ground-truth value, text,
//! or description ever reaches the attestation or any committed file —
//! match verdicts, field names, hashes, and counts only; names of
//! published records are the one permitted identifier.
//!
//! Waivers and overrides live in `crates/reference-check/overrides.json`
//! (committed, reviewed like code), one block per system. A waiver is bound
//! to the sha256 of the comparison state it excuses (mismatched field names
//! plus our record's content hash — no ground-truth bytes), so a waiver
//! whose mismatch disappears or shifts fails THIS tool loudly. The offline check
//! cannot recompute that binding (no network in CI); it verifies waiver
//! hygiene (reason + state_hash present) and seals everything else with the
//! per-record content hashes.

mod attest;
mod cache;
mod canon;
mod compare;
mod dnd5e;
mod foundry;
mod ours;
mod pf2e;
mod srd;

use std::path::PathBuf;

/// The pinned PF2e ground-truth snapshot: the latest stable Pathfinder 2e
/// release tag of github.com/foundryvtt/pf2e at pin time (2026-08-29).
/// `sf2e-*` and `*-anachronism-*` tags are other product lines; `pf2e-*`
/// is the Pathfinder system line.
pub const FOUNDRY_TAG: &str = "pf2e-8.4.1";

/// sha256 of the GitHub source tarball for FOUNDRY_TAG, computed on first
/// fetch (2026-08-29) and baked in. GitHub generates these tarballs on the
/// fly; the bytes have historically been stable per tag, and if GitHub ever
/// changes its compression the fetch fails loudly against this pin — that
/// is the desired behavior (re-pinning is a deliberate, reviewed edit here,
/// never a silent drift).
pub const FOUNDRY_SHA256: &str = "b0a649e6f9859350f7eca86e85082ac68b20309f4335c77bf6e1643aff009c8a";

/// The pinned 5.5e ground-truth snapshot (spec chargen-dnd, Risks →
/// Licensing: a machine-readable copy of SRD 5.2.1 with clear provenance).
/// github.com/your5e/5e-srd-markdown splits the official SRD 5.2.1 PDF
/// into per-topic Markdown under `dnd/521/markdown/` and ships the PDF it
/// was split from alongside; this is the `main` head at pin time
/// (2026-09-06). The archive is fetched by commit sha, never by branch.
pub const SRD_REPO: &str = "your5e/5e-srd-markdown";
pub const SRD_COMMIT: &str = "f1f5060fd975aa2ffc3e4b336560ded479934d80";

/// sha256 of the GitHub source tarball for SRD_COMMIT, computed on first
/// fetch (2026-09-06, stable across two downloads) and baked in.
pub const SRD_SHA256: &str = "aa80f8b8d768a1b54d4426a3f3194b061ec0d4ae0b4462784670758e545b6dc6";

/// sha256 of the official SRD 5.2.1 PDF (`dnd/521/SRD_CC_v5.2.1.pdf`)
/// carried inside that tarball — the same digest `rules-data/dnd5e/
/// manifest.json` records for the PDF the records were transcribed from.
/// `fetch` hashes the archive entry in flight (the PDF is never written to
/// disk) and refuses a mirror whose PDF is not that document, which closes
/// the provenance chain: mirror -> the PDF it was split from -> our pages.
pub const SRD_PDF_SHA256: &str = "8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87";

/// Which rules system a run attests. Selected by `--system`; PF2e is the
/// default so existing usage is unchanged.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum System {
    Pf2e,
    Dnd5e,
}

impl System {
    /// The `rules-data/<id>/` and `.reference-cache/<id>/` directory name.
    pub fn id(self) -> &'static str {
        match self {
            System::Pf2e => "pf2e",
            System::Dnd5e => "dnd5e",
        }
    }

    fn parse(s: &str) -> Option<System> {
        match s {
            "pf2e" => Some(System::Pf2e),
            "dnd5e" => Some(System::Dnd5e),
            _ => None,
        }
    }
}

/// Where a system's ground truth comes from: the pinned tarball and the
/// subset of it the matcher reads. Plain data selected by a `match` on the
/// system (no source trait).
pub struct Pin {
    /// Cache file stem and extraction directory name.
    pub tag: &'static str,
    pub url: String,
    pub sha256: &'static str,
    /// Top-level directory inside the tarball.
    pub top_dir: String,
    /// Tarball entry prefixes (relative to `top_dir`) to extract.
    pub needed: Vec<String>,
    /// An entry (relative to `top_dir`) whose sha256 must equal the given
    /// digest; hashed in flight and never written to disk.
    pub inner_hash: Option<(String, &'static str)>,
}

impl System {
    pub fn pin(self) -> Pin {
        match self {
            System::Pf2e => Pin {
                tag: FOUNDRY_TAG,
                url: format!(
                    "https://github.com/foundryvtt/pf2e/archive/refs/tags/{FOUNDRY_TAG}.tar.gz"
                ),
                sha256: FOUNDRY_SHA256,
                top_dir: format!("pf2e-{FOUNDRY_TAG}"),
                needed: foundry::NEEDED_PACKS
                    .iter()
                    .map(|p| format!("packs/pf2e/{p}/"))
                    .collect(),
                inner_hash: None,
            },
            System::Dnd5e => Pin {
                tag: &SRD_COMMIT[..12],
                url: format!("https://github.com/{SRD_REPO}/archive/{SRD_COMMIT}.tar.gz"),
                sha256: SRD_SHA256,
                top_dir: format!(
                    "{}-{SRD_COMMIT}",
                    SRD_REPO.rsplit('/').next().expect("owner/name")
                ),
                needed: srd::NEEDED_PATHS
                    .iter()
                    .map(|p| format!("dnd/521/markdown/{p}"))
                    .collect(),
                inner_hash: Some(("dnd/521/SRD_CC_v5.2.1.pdf".to_string(), SRD_PDF_SHA256)),
            },
        }
    }
}

/// Workspace root, resolved from this crate's manifest directory.
pub fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|p| p.parent())
        .expect("crates/reference-check sits two levels under the root")
        .to_path_buf()
}

fn usage() -> i32 {
    eprintln!(
        "usage: reference-check <fetch|attest> [--system pf2e|dnd5e]\n  \
         fetch   download + verify + extract the pinned snapshot \
         (pf2e: Foundry {FOUNDRY_TAG}; dnd5e: {SRD_REPO}@{})\n  \
         attest  verify the cache, match all shipped records, write \
         rules-data/<system>/attestation.json\n  \
         --system defaults to pf2e",
        &SRD_COMMIT[..12]
    );
    2
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let mut system = System::Pf2e;
    let mut rest = args.iter().skip(2);
    while let Some(arg) = rest.next() {
        match arg.as_str() {
            "--system" => match rest.next().and_then(|s| System::parse(s)) {
                Some(s) => system = s,
                None => std::process::exit(usage()),
            },
            _ => std::process::exit(usage()),
        }
    }
    let code = match args.get(1).map(String::as_str) {
        Some("fetch") => run(cache::fetch(system)),
        Some("attest") => run(attest::attest(system)),
        _ => usage(),
    };
    std::process::exit(code);
}

fn run(result: Result<(), String>) -> i32 {
    match result {
        Ok(()) => 0,
        Err(msg) => {
            eprintln!("reference-check: {msg}");
            1
        }
    }
}
