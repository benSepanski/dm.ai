//! reference-check — compares shipped rules-data against a pinned,
//! content-hash-verified Foundry pf2e snapshot and writes the committed
//! attestation (`rules-data/attestation.json`).
//!
//! Subcommands:
//!   fetch   download the pinned ground-truth tarball into the gitignored
//!           `.reference-cache/`, verify it against the pinned sha256, and
//!           extract the pack subset the matcher reads. The only
//!           network-touching path in the repo's tooling.
//!   attest  verify the cache against the pin (never attest against
//!           unverified content), match every shipped record, and write the
//!           attestation. Offline once the cache exists.
//!
//! Trust chain (architecture doc, "Trust must be mechanical"): pinned
//! snapshot -> deliberate tool run -> committed attestation -> offline CI
//! check (`checks/attestation.rs`). HARD RULE: no Foundry value, text, or
//! description ever reaches the attestation or any committed file — match
//! verdicts, field names, hashes, and counts only; names of published
//! records are the one permitted identifier.
//!
//! Waivers and overrides live in `crates/reference-check/overrides.json`
//! (committed, reviewed like code). A waiver is bound to the sha256 of the
//! comparison state it excuses (mismatched field names + our record's
//! content hash — no ground-truth bytes), so a waiver whose mismatch
//! disappears or shifts fails THIS tool loudly. The offline check cannot
//! recompute that binding (no network in CI); it verifies waiver hygiene
//! (reason + state_hash present) and seals everything else with the
//! per-record content hashes.

mod attest;
mod cache;
mod canon;
mod compare;
mod foundry;
mod ours;

use std::path::PathBuf;

/// The pinned ground-truth snapshot: the latest stable Pathfinder 2e
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

pub fn tarball_url() -> String {
    format!("https://github.com/foundryvtt/pf2e/archive/refs/tags/{FOUNDRY_TAG}.tar.gz")
}

/// Workspace root, resolved from this crate's manifest directory.
pub fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|p| p.parent())
        .expect("crates/reference-check sits two levels under the root")
        .to_path_buf()
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let code = match args.get(1).map(String::as_str) {
        Some("fetch") => run(cache::fetch()),
        Some("attest") => run(attest::attest()),
        _ => {
            eprintln!(
                "usage: reference-check <fetch|attest>\n  \
                 fetch   download + verify + extract the pinned Foundry \
                 snapshot ({FOUNDRY_TAG})\n  \
                 attest  verify the cache, match all shipped records, write \
                 rules-data/attestation.json"
            );
            2
        }
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
