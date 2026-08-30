//! Ground-truth cache: fetch, verify, extract. The cache directory is
//! gitignored (`checks/attestation.rs` asserts that) — no Foundry byte is
//! ever committed. Every attest run re-verifies the cached tarball against
//! the pinned sha256 BEFORE any matching; a torn or stale cache fails
//! loudly (or refetches, in `fetch`) — the tool never attests against
//! unverified content.

use std::fs;
use std::path::PathBuf;

use crate::{canon, tarball_url, workspace_root, FOUNDRY_SHA256, FOUNDRY_TAG};

pub const CACHE_DIR: &str = ".reference-cache";

/// Pack directories (under `packs/pf2e/` in the tarball) the matcher reads.
/// Only these are extracted — the tarball also carries bestiaries,
/// adventures, and art the tool has no use for.
const NEEDED_PACKS: &[&str] = &[
    "ancestries",
    "heritages",
    "backgrounds",
    "classes",
    "class-features",
    "spells",
    "feats",
    "equipment",
];

fn cache_root() -> PathBuf {
    workspace_root().join(CACHE_DIR)
}

fn tarball_path() -> PathBuf {
    cache_root().join(format!("{FOUNDRY_TAG}.tar.gz"))
}

/// Extraction target; the `.verified` marker inside records the tarball
/// hash the extraction came from.
fn extract_root() -> PathBuf {
    cache_root().join("extracted").join(FOUNDRY_TAG)
}

fn marker_path() -> PathBuf {
    extract_root().join(".verified")
}

/// Directory holding the extracted `packs/pf2e/` tree.
pub fn packs_root() -> PathBuf {
    extract_root()
        .join(format!("pf2e-{FOUNDRY_TAG}"))
        .join("packs")
        .join("pf2e")
}

/// `fetch`: download (if absent), verify against the pin, extract. A hash
/// mismatch deletes the tarball and refetches once; a second mismatch is a
/// hard failure (the pin is stale or the upstream tarball changed — either
/// way, re-pinning is a deliberate edit to main.rs, never automatic).
pub fn fetch() -> Result<(), String> {
    fs::create_dir_all(cache_root()).map_err(|e| format!("creating {CACHE_DIR}: {e}"))?;
    let path = tarball_path();
    if !path.exists() {
        download(&path)?;
    }
    if verify_tarball().is_err() {
        // Refetch once: download() writes a temp file and renames it over
        // the torn tarball (the workspace-wide no-unlink discipline holds
        // even here — nothing is ever removed, only replaced).
        eprintln!("cached tarball fails the pinned hash; refetching once");
        download(&path)?;
        verify_tarball()?;
    }
    extract()?;
    eprintln!("fetch: {FOUNDRY_TAG} verified ({FOUNDRY_SHA256}) and extracted");
    Ok(())
}

/// Verify cache integrity without touching the network; called by `attest`
/// before any matching. Re-extracts from the verified tarball if the
/// extraction marker is missing or stale.
pub fn ensure_verified() -> Result<(), String> {
    if !tarball_path().exists() {
        return Err(format!(
            "no cached tarball at {}: run `cargo run -p reference-check -- fetch` first",
            tarball_path().display()
        ));
    }
    verify_tarball()?;
    let marker_ok = fs::read_to_string(marker_path())
        .map(|m| m.trim() == FOUNDRY_SHA256)
        .unwrap_or(false);
    if !marker_ok {
        extract()?;
    }
    Ok(())
}

fn verify_tarball() -> Result<(), String> {
    let bytes = fs::read(tarball_path()).map_err(|e| format!("reading cached tarball: {e}"))?;
    let actual = canon::sha256_hex(&bytes);
    if actual != FOUNDRY_SHA256 {
        return Err(format!(
            "cached tarball hash mismatch for {FOUNDRY_TAG}\n  pinned: {FOUNDRY_SHA256}\n  \
             actual: {actual}\nnever attesting against unverified content; delete \
             {CACHE_DIR}/ and re-run `fetch`, or re-pin deliberately in main.rs",
        ));
    }
    Ok(())
}

fn download(path: &std::path::Path) -> Result<(), String> {
    let url = tarball_url();
    eprintln!("downloading {url}");
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(600))
        .build()
        .map_err(|e| format!("building http client: {e}"))?;
    let response = client
        .get(&url)
        .send()
        .and_then(reqwest::blocking::Response::error_for_status)
        .map_err(|e| format!("fetching {url}: {e}"))?;
    let bytes = response
        .bytes()
        .map_err(|e| format!("reading response body: {e}"))?;
    // Write via temp + rename so an interrupted download never masquerades
    // as a cached tarball (verify would catch it anyway; this keeps the
    // failure mode boring).
    let tmp = path.with_extension("part");
    fs::write(&tmp, &bytes).map_err(|e| format!("writing {}: {e}", tmp.display()))?;
    fs::rename(&tmp, path).map_err(|e| format!("renaming into place: {e}"))?;
    Ok(())
}

/// Extract only the needed `packs/pf2e/` subset from the verified tarball,
/// then drop the `.verified` marker naming the hash it came from. Unpacking
/// overwrites in place (extraction dirs are per-tag, and every byte comes
/// from the just-verified tarball, so overwrite is exactly re-extraction);
/// the marker is written only after a complete pass, so an interrupted
/// extraction re-runs on the next invocation.
fn extract() -> Result<(), String> {
    let root = extract_root();
    fs::create_dir_all(&root).map_err(|e| format!("creating extraction dir: {e}"))?;

    let file = fs::File::open(tarball_path()).map_err(|e| format!("opening tarball: {e}"))?;
    let gz = flate2::read::GzDecoder::new(file);
    let mut archive = tar::Archive::new(gz);
    let prefixes: Vec<String> = NEEDED_PACKS
        .iter()
        .map(|p| format!("pf2e-{FOUNDRY_TAG}/packs/pf2e/{p}/"))
        .collect();

    let mut extracted = 0usize;
    for entry in archive
        .entries()
        .map_err(|e| format!("reading tarball: {e}"))?
    {
        let mut entry = entry.map_err(|e| format!("reading tarball entry: {e}"))?;
        let path = entry
            .path()
            .map_err(|e| format!("tarball entry path: {e}"))?
            .to_path_buf();
        let path_str = path.to_string_lossy().to_string();
        if !prefixes.iter().any(|p| path_str.starts_with(p.as_str())) {
            continue;
        }
        // Defensive: refuse absolute paths / parent traversal from the
        // archive (tar::Entry::unpack_in also guards; belt + suspenders).
        if path.is_absolute() || path_str.contains("..") {
            return Err(format!("suspicious tarball path: {path_str}"));
        }
        entry
            .unpack_in(&root)
            .map_err(|e| format!("extracting {path_str}: {e}"))?;
        extracted += 1;
    }
    if extracted == 0 {
        return Err("tarball contained none of the expected pack paths".to_string());
    }
    fs::write(marker_path(), format!("{FOUNDRY_SHA256}\n"))
        .map_err(|e| format!("writing verification marker: {e}"))?;
    eprintln!(
        "extracted {extracted} files from {} packs",
        NEEDED_PACKS.len()
    );
    Ok(())
}
