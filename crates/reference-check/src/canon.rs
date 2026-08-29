//! Canonical JSON + hashing. The per-record `file_hash` in the attestation
//! is sha256 over this canonical form; `checks/attestation.rs` recomputes
//! it offline with an IDENTICAL implementation (kept duplicated there —
//! nothing may depend on this crate per the layering allowlist). Any edit
//! here must be mirrored in checks/attestation.rs `canonical_json`.

use sha2::{Digest, Sha256};

/// Deterministic serialization: object keys sorted, compact separators.
pub fn canonical_json(value: &serde_json::Value) -> String {
    serde_json::to_string(&sort_keys(value)).expect("serializing owned JSON cannot fail")
}

fn sort_keys(value: &serde_json::Value) -> serde_json::Value {
    match value {
        serde_json::Value::Object(map) => {
            let mut pairs: Vec<(&String, &serde_json::Value)> = map.iter().collect();
            pairs.sort_by_key(|(k, _)| k.as_str());
            let mut out = serde_json::Map::new();
            for (k, v) in pairs {
                out.insert(k.clone(), sort_keys(v));
            }
            serde_json::Value::Object(out)
        }
        serde_json::Value::Array(items) => {
            serde_json::Value::Array(items.iter().map(sort_keys).collect())
        }
        other => other.clone(),
    }
}

pub fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    let digest = hasher.finalize();
    let mut out = String::with_capacity(64);
    for byte in digest {
        use std::fmt::Write;
        write!(out, "{byte:02x}").expect("writing to String cannot fail");
    }
    out
}

/// sha256 of a record's canonical JSON — the attestation's `file_hash`.
pub fn record_hash(record: &serde_json::Value) -> String {
    sha256_hex(canonical_json(record).as_bytes())
}

/// Today's UTC date as YYYY-MM-DD (civil-from-days, Howard Hinnant's
/// algorithm) — avoids a chrono dependency for one field.
pub fn utc_date_today() -> String {
    // Reviewed exception to the no-ambient-clock ban (clippy.toml): this is
    // dev-tool run metadata (the attestation's `generated` date), mirroring
    // the server::clock exception — no domain derivation reads it.
    #[allow(clippy::disallowed_methods)]
    let secs = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .expect("system clock after 1970")
        .as_secs();
    let days = (secs / 86_400) as i64;
    let z = days + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{y:04}-{m:02}-{d:02}")
}
