//! Ground-truth cache: fetch, verify, extract — per system, under
//! `.reference-cache/<system>/`. The cache directory is gitignored as a
//! whole (`checks/attestation.rs` asserts that) — no ground-truth byte is
//! ever committed. Every attest run re-verifies the cached tarball against
//! the pinned sha256 BEFORE any matching; a torn or stale cache fails
//! loudly (or refetches, in `fetch`) — the tool never attests against
//! unverified content.

use std::fs;
use std::io::Read;
use std::path::PathBuf;

use crate::{canon, workspace_root, Pin, System};

pub const CACHE_DIR: &str = ".reference-cache";

fn cache_root(system: System) -> PathBuf {
    workspace_root().join(CACHE_DIR).join(system.id())
}

fn tarball_path(system: System, pin: &Pin) -> PathBuf {
    cache_root(system).join(format!("{}.tar.gz", pin.tag))
}

/// Extraction target; the `.verified` marker inside records the tarball
/// hash the extraction came from.
fn extract_root(system: System, pin: &Pin) -> PathBuf {
    cache_root(system).join("extracted").join(pin.tag)
}

fn marker_path(system: System, pin: &Pin) -> PathBuf {
    extract_root(system, pin).join(".verified")
}

/// The extracted tarball's top-level directory (`<top_dir>/` of the pin).
pub fn source_root(system: System) -> PathBuf {
    let pin = system.pin();
    extract_root(system, &pin).join(&pin.top_dir)
}

/// `fetch`: download (if absent), verify against the pin, extract. A hash
/// mismatch deletes nothing: the tarball is refetched once over the torn
/// one; a second mismatch is a hard failure (the pin is stale or the
/// upstream tarball changed — either way, re-pinning is a deliberate edit
/// to main.rs, never automatic).
pub fn fetch(system: System) -> Result<(), String> {
    let pin = system.pin();
    fs::create_dir_all(cache_root(system))
        .map_err(|e| format!("creating {CACHE_DIR}/{}: {e}", system.id()))?;
    let path = tarball_path(system, &pin);
    if !path.exists() {
        download(&pin, &path)?;
    }
    if verify_tarball(system, &pin).is_err() {
        // Refetch once: download() writes a temp file and renames it over
        // the torn tarball (the workspace-wide no-unlink discipline holds
        // even here — nothing is ever removed, only replaced).
        eprintln!("cached tarball fails the pinned hash; refetching once");
        download(&pin, &path)?;
        verify_tarball(system, &pin)?;
    }
    extract(system, &pin)?;
    eprintln!(
        "fetch: {} {} verified ({}) and extracted",
        system.id(),
        pin.tag,
        pin.sha256
    );
    Ok(())
}

/// Verify cache integrity without touching the network; called by `attest`
/// before any matching. Re-extracts from the verified tarball if the
/// extraction marker is missing or stale.
pub fn ensure_verified(system: System) -> Result<(), String> {
    let pin = system.pin();
    if !tarball_path(system, &pin).exists() {
        return Err(format!(
            "no cached tarball at {}: run `cargo run -p reference-check -- fetch --system {}` first",
            tarball_path(system, &pin).display(),
            system.id()
        ));
    }
    verify_tarball(system, &pin)?;
    let marker_ok = fs::read_to_string(marker_path(system, &pin))
        .map(|m| m.trim() == pin.sha256)
        .unwrap_or(false);
    if !marker_ok {
        extract(system, &pin)?;
    }
    Ok(())
}

fn verify_tarball(system: System, pin: &Pin) -> Result<(), String> {
    let bytes =
        fs::read(tarball_path(system, pin)).map_err(|e| format!("reading cached tarball: {e}"))?;
    let actual = canon::sha256_hex(&bytes);
    if actual != pin.sha256 {
        return Err(format!(
            "cached tarball hash mismatch for {} {}\n  pinned: {}\n  \
             actual: {actual}\nnever attesting against unverified content; move \
             {CACHE_DIR}/{}/ aside and re-run `fetch`, or re-pin deliberately in main.rs",
            system.id(),
            pin.tag,
            pin.sha256,
            system.id(),
        ));
    }
    Ok(())
}

fn download(pin: &Pin, path: &std::path::Path) -> Result<(), String> {
    let url = &pin.url;
    eprintln!("downloading {url}");
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(600))
        .build()
        .map_err(|e| format!("building http client: {e}"))?;
    let response = client
        .get(url)
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

/// Extract only the pin's needed subset from the verified tarball, hash
/// any in-flight-checked entry (the 5.5e PDF) without writing it, then
/// drop the `.verified` marker naming the hash it came from. Unpacking
/// overwrites in place (extraction dirs are per-tag, and every byte comes
/// from the just-verified tarball, so overwrite is exactly re-extraction);
/// the marker is written only after a complete pass, so an interrupted
/// extraction re-runs on the next invocation.
fn extract(system: System, pin: &Pin) -> Result<(), String> {
    let root = extract_root(system, pin);
    fs::create_dir_all(&root).map_err(|e| format!("creating extraction dir: {e}"))?;

    let file =
        fs::File::open(tarball_path(system, pin)).map_err(|e| format!("opening tarball: {e}"))?;
    let gz = flate2::read::GzDecoder::new(file);
    let mut archive = tar::Archive::new(gz);
    let prefixes: Vec<String> = pin
        .needed
        .iter()
        .map(|p| format!("{}/{p}", pin.top_dir))
        .collect();
    let inner = pin
        .inner_hash
        .as_ref()
        .map(|(rel, digest)| (format!("{}/{rel}", pin.top_dir), *digest));
    let mut inner_seen = false;

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
        if let Some((inner_path, digest)) = &inner {
            if &path_str == inner_path {
                let mut bytes = Vec::new();
                entry
                    .read_to_end(&mut bytes)
                    .map_err(|e| format!("reading {path_str}: {e}"))?;
                let actual = canon::sha256_hex(&bytes);
                if &actual != digest {
                    return Err(format!(
                        "{path_str} inside the pinned tarball hashes to {actual}, not the \
                         pinned {digest}: the mirror does not carry the document our records \
                         were transcribed from; never attesting against it"
                    ));
                }
                inner_seen = true;
                continue;
            }
        }
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
        return Err("tarball contained none of the expected paths".to_string());
    }
    if inner.is_some() && !inner_seen {
        return Err("tarball lacks the entry whose hash the pin requires".to_string());
    }
    fs::write(marker_path(system, pin), format!("{}\n", pin.sha256))
        .map_err(|e| format!("writing verification marker: {e}"))?;
    eprintln!(
        "extracted {extracted} files from {} pinned paths",
        pin.needed.len()
    );
    Ok(())
}
