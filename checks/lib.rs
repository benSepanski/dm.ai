//! Shared helpers for the checks suite (workspace discovery; later: spawning
//! the real server binary for the crash harness and API checks).
#![forbid(unsafe_code)]

use std::path::PathBuf;

/// Absolute path to the workspace root, resolved from this crate's manifest.
pub fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("checks crate sits directly under the workspace root")
        .to_path_buf()
}
