//! The server's one sanctioned clock access — used for trash/quarantine
//! timestamps and ID minting, never for anything the engine derives.

use std::sync::atomic::{AtomicU64, Ordering};

static COUNTER: AtomicU64 = AtomicU64::new(0);

/// Milliseconds since the Unix epoch.
#[allow(clippy::disallowed_methods)] // the single sanctioned wall-clock read
pub fn now_millis() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

/// A process-unique, time-ordered identifier suffix.
pub fn mint_id() -> String {
    let n = COUNTER.fetch_add(1, Ordering::Relaxed);
    format!("{:x}-{n:x}", now_millis())
}
