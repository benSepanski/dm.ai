//! Attestation chain (architecture: chargen-content, "Attestation current"
//! row). Offline half of the trust chain: pinned snapshot -> deliberate
//! `reference-check` run -> committed `rules-data/attestation.json` -> this
//! file, on every CI push, with no network.
//!
//! Asserted here: the attestation exists, matches the manifest version,
//! covers every shipped record in both directions, its per-record content
//! hashes equal a fresh recompute over current rules-data (any data edit
//! stales the attestation until the tool is re-run — the forcing function),
//! carries zero "mismatch" verdicts, keeps waiver hygiene, and admits no
//! ground-truth values (strict schema: exact keys, enum verdicts,
//! hex hashes, tight field-name strings, bare record names only).
//!
//! Deliberate split (offline CI cannot see the ground truth): whether a
//! waiver still excuses a REAL mismatch — and fails when its mismatch
//! disappears or shifts — is enforced at tool time by the state_hash
//! binding in `crates/reference-check/overrides.json`; forging past that
//! requires hand-editing the attestation, which review catches as an
//! attestation diff with no matching rules-data diff (architecture,
//! "Deliberately unenforced"). Here we verify the waiver's shape: a
//! non-empty reason and a well-formed state_hash.

use std::collections::BTreeSet;
use std::process::Command;

use sha2::{Digest, Sha256};

const CACHE_DIR: &str = ".reference-cache";

#[test]
fn ground_truth_cache_is_gitignored_and_untracked() {
    let root = checks::workspace_root();
    let gitignore = std::fs::read_to_string(root.join(".gitignore")).expect(".gitignore");
    assert!(
        gitignore
            .lines()
            .any(|l| l.trim() == format!("{CACHE_DIR}/")),
        ".gitignore must ignore {CACHE_DIR}/ — ground-truth bytes never land \
         in the repo"
    );

    // Nothing under the cache path is tracked (belt over the suspenders:
    // a force-add would slip past the ignore).
    let out = Command::new("git")
        .args(["ls-files", CACHE_DIR])
        .current_dir(&root)
        .output()
        .expect("git ls-files");
    let tracked = String::from_utf8_lossy(&out.stdout);
    assert!(
        tracked.trim().is_empty(),
        "tracked files under {CACHE_DIR}/: {tracked}\nground-truth content \
         must never be committed"
    );
}

#[test]
fn ci_never_invokes_the_reference_check_tool() {
    let root = checks::workspace_root();
    let workflows = root.join(".github/workflows");
    for entry in std::fs::read_dir(&workflows)
        .expect("workflows dir")
        .flatten()
    {
        let path = entry.path();
        if path.extension().is_none_or(|e| e != "yml" && e != "yaml") {
            continue;
        }
        let text = std::fs::read_to_string(&path).expect("workflow file");
        assert!(
            !text.contains("reference-check"),
            "{} invokes reference-check: the tool needs the network and runs \
             only as a deliberate local invocation; CI verifies the committed \
             attestation offline",
            path.display()
        );
    }
}

// ---- Attestation content (ticket T6) ------------------------------------

/// Record files the attestation must cover — keep in lockstep with
/// RECORD_FILES in checks/rules_data.rs and FLAT_FILES/EQUIPMENT_CATEGORIES
/// in crates/reference-check/src/ours.rs.
const ATTESTED_RECORD_FILES: &[&str] = &[
    "ancestries.json",
    "heritages.json",
    "ancestry-feats.json",
    "backgrounds.json",
    "classes.json",
    "class-feats.json",
    "general-feats.json",
    "skills.json",
    "equipment.json",
    "spells.json",
];

/// (id, record) for every shipped record, from the committed JSON bytes.
fn current_records() -> Vec<(String, serde_json::Value)> {
    let root = checks::workspace_root().join("rules-data");
    let mut out = Vec::new();
    for file in ATTESTED_RECORD_FILES {
        let text = std::fs::read_to_string(root.join(file)).unwrap();
        let value: serde_json::Value = serde_json::from_str(&text).unwrap();
        let records: Vec<serde_json::Value> = if *file == "equipment.json" || *file == "spells.json"
        {
            value
                .as_object()
                .unwrap()
                .values()
                .flat_map(|arr| arr.as_array().unwrap().clone())
                .collect()
        } else {
            value.as_array().unwrap().clone()
        };
        for record in records {
            let id = record["id"].as_str().expect("record id").to_string();
            out.push((id, record));
        }
    }
    out
}

fn attestation() -> serde_json::Value {
    let path = checks::workspace_root().join("rules-data/attestation.json");
    let text = std::fs::read_to_string(&path).expect(
        "rules-data/attestation.json must exist: run \
         `cargo run -p reference-check -- fetch` then `-- attest`",
    );
    serde_json::from_str(&text).expect("attestation.json parses")
}

/// Canonical JSON (sorted keys, compact) — MUST stay byte-identical to
/// `canonical_json` in crates/reference-check/src/canon.rs: the attested
/// `file_hash` is sha256 over this form.
fn canonical_json(value: &serde_json::Value) -> String {
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
    serde_json::to_string(&sort_keys(value)).unwrap()
}

fn sha256_hex(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    hasher
        .finalize()
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

fn is_hex64(s: &str) -> bool {
    s.len() == 64
        && s.chars()
            .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase())
}

/// Field names in the attestation are snake_case identifiers — anything
/// prose-shaped fails.
fn is_field_name(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 32
        && s.chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_')
}

#[test]
fn attestation_matches_manifest_version() {
    let manifest: serde_json::Value = serde_json::from_str(
        &std::fs::read_to_string(checks::workspace_root().join("rules-data/manifest.json"))
            .unwrap(),
    )
    .unwrap();
    assert_eq!(
        attestation()["rules_version"].as_str(),
        manifest["version"].as_str(),
        "attestation is for a different rules-data version: re-run \
         `cargo run -p reference-check -- attest`"
    );
}

#[test]
fn attestation_covers_every_record_and_hashes_are_current() {
    let att = attestation();
    let records = att["records"].as_object().expect("records object");
    let current = current_records();

    // Coverage, both directions: exactly the shipped ID set, no more, no
    // less.
    let attested_ids: BTreeSet<&str> = records.keys().map(String::as_str).collect();
    let current_ids: BTreeSet<&str> = current.iter().map(|(id, _)| id.as_str()).collect();
    let unattested: Vec<_> = current_ids.difference(&attested_ids).collect();
    let stale: Vec<_> = attested_ids.difference(&current_ids).collect();
    assert!(
        unattested.is_empty() && stale.is_empty(),
        "attestation coverage diverges from shipped records\n  \
         shipped but unattested: {unattested:?}\n  attested but no longer \
         shipped: {stale:?}\nre-run `cargo run -p reference-check -- attest`"
    );

    // Per-record content hash recompute: an in-place edit under an
    // unchanged version string fails here exactly like a coverage gap —
    // this is the forcing function, not an error path.
    for (id, record) in &current {
        let expected = sha256_hex(canonical_json(record).as_bytes());
        let attested = records[id]["file_hash"].as_str().unwrap_or("");
        assert_eq!(
            attested, expected,
            "record '{id}' changed since the attestation was generated: \
             re-run `cargo run -p reference-check -- attest` (and re-review \
             any waiver it invalidates)"
        );
    }
}

#[test]
fn attestation_has_zero_unwaived_mismatches_and_sound_waivers() {
    let att = attestation();
    for (id, entry) in att["records"].as_object().expect("records object") {
        let verdict = entry["verdict"].as_str().unwrap_or("");
        assert_ne!(
            verdict, "mismatch",
            "record '{id}' is attested as an unwaived mismatch: fix the \
             record or add a reviewed waiver in \
             crates/reference-check/overrides.json, then re-run the tool"
        );
        match verdict {
            "match" => assert!(
                entry["waiver"].is_null(),
                "record '{id}': a clean match must not carry a waiver"
            ),
            "waived" => {
                let waiver = &entry["waiver"];
                let reason = waiver["reason"].as_str().unwrap_or("");
                assert!(
                    !reason.trim().is_empty(),
                    "record '{id}': waiver without a reason"
                );
                // The state_hash binds this waiver to the exact mismatch it
                // excuses; the binding itself is enforced at tool time
                // (offline CI has no ground truth to recompute against).
                assert!(
                    is_hex64(waiver["state_hash"].as_str().unwrap_or("")),
                    "record '{id}': waiver state_hash is not a sha256 hex digest"
                );
            }
            other => panic!("record '{id}': unknown verdict '{other}'"),
        }
    }
}

/// Strict schema scan — the no-ground-truth-content rule made mechanical:
/// exact key sets at every level, enum verdicts, hex hashes, snake_case
/// field names, and bare record names (no prose) in `missing_from_data`.
/// Unknown keys are rejected, so a Foundry value or description has no slot
/// to hide in.
#[test]
fn attestation_schema_admits_no_ground_truth_values() {
    let att = attestation();
    let top = att.as_object().expect("attestation is an object");
    let expected_top: BTreeSet<&str> = [
        "tool_version",
        "foundry_tag",
        "foundry_sha256",
        "rules_version",
        "generated",
        "claims_full_breadth",
        "records",
        "missing_from_data",
        "overrides_used",
    ]
    .into_iter()
    .collect();
    let actual_top: BTreeSet<&str> = top.keys().map(String::as_str).collect();
    assert_eq!(actual_top, expected_top, "unexpected top-level keys");

    for key in ["tool_version", "foundry_tag", "rules_version"] {
        let v = att[key].as_str().unwrap_or("");
        assert!(
            !v.is_empty() && v.len() <= 64 && !v.contains(char::is_whitespace),
            "'{key}' must be a short identifier"
        );
    }
    assert!(
        is_hex64(att["foundry_sha256"].as_str().unwrap_or("")),
        "foundry_sha256 must be a sha256 hex digest"
    );
    let generated = att["generated"].as_str().unwrap_or("");
    assert!(
        generated.len() == 10
            && generated
                .chars()
                .enumerate()
                .all(|(i, c)| if i == 4 || i == 7 {
                    c == '-'
                } else {
                    c.is_ascii_digit()
                }),
        "'generated' must be an ISO date (YYYY-MM-DD), got '{generated}'"
    );
    assert!(
        att["claims_full_breadth"].is_boolean(),
        "claims_full_breadth must be a bool"
    );

    let record_ids: BTreeSet<&str> = att["records"]
        .as_object()
        .expect("records object")
        .keys()
        .map(String::as_str)
        .collect();
    for (id, entry) in att["records"].as_object().unwrap() {
        let keys: BTreeSet<&str> = entry
            .as_object()
            .unwrap_or_else(|| panic!("record '{id}' entry is not an object"))
            .keys()
            .map(String::as_str)
            .collect();
        let expected: BTreeSet<&str> = [
            "file_hash",
            "verdict",
            "fields_checked",
            "mismatches",
            "waiver",
        ]
        .into_iter()
        .collect();
        assert_eq!(keys, expected, "record '{id}': unexpected entry keys");
        assert!(
            is_hex64(entry["file_hash"].as_str().unwrap_or("")),
            "record '{id}': file_hash is not a sha256 hex digest"
        );
        let fields: Vec<&str> = entry["fields_checked"]
            .as_array()
            .expect("fields_checked array")
            .iter()
            .map(|v| v.as_str().expect("field name"))
            .collect();
        let mismatches: Vec<&str> = entry["mismatches"]
            .as_array()
            .expect("mismatches array")
            .iter()
            .map(|v| v.as_str().expect("field name"))
            .collect();
        for field in fields.iter().chain(&mismatches) {
            assert!(
                is_field_name(field),
                "record '{id}': '{field}' is not a plain field name"
            );
        }
        for field in &mismatches {
            assert!(
                fields.contains(field),
                "record '{id}': mismatch '{field}' not among fields_checked"
            );
        }
        if let Some(waiver) = entry["waiver"].as_object() {
            let keys: BTreeSet<&str> = waiver.keys().map(String::as_str).collect();
            let expected: BTreeSet<&str> = ["reason", "state_hash"].into_iter().collect();
            assert_eq!(keys, expected, "record '{id}': unexpected waiver keys");
        }
    }

    for (category, entry) in att["missing_from_data"]
        .as_object()
        .expect("missing_from_data object")
    {
        let keys: BTreeSet<&str> = entry
            .as_object()
            .unwrap_or_else(|| panic!("missing_from_data '{category}' is not an object"))
            .keys()
            .map(String::as_str)
            .collect();
        let expected: BTreeSet<&str> = ["count", "names"].into_iter().collect();
        assert_eq!(keys, expected, "'{category}': unexpected keys");
        let names = entry["names"].as_array().expect("names array");
        assert_eq!(
            entry["count"].as_u64(),
            Some(names.len() as u64),
            "'{category}': count disagrees with names"
        );
        for name in names {
            let name = name.as_str().expect("record name");
            // Bare published-record names are the one permitted identifier;
            // anything sentence-shaped fails.
            assert!(
                !name.is_empty() && name.len() <= 64 && !name.contains('\n'),
                "'{category}': '{name}' does not look like a bare record name"
            );
        }
    }

    for id in att["overrides_used"]
        .as_array()
        .expect("overrides_used array")
    {
        let id = id.as_str().expect("override id");
        assert!(
            record_ids.contains(id),
            "overrides_used names '{id}', which is not an attested record"
        );
    }
}

#[test]
fn full_breadth_claim_requires_empty_missing_from_data() {
    let att = attestation();
    if att["claims_full_breadth"].as_bool() != Some(true) {
        // Slice-1 subset data: the reverse-completeness sections are
        // informational until the T3–T5 content tickets land and the tool's
        // CLAIMS_FULL_BREADTH constant is flipped.
        return;
    }
    for (category, entry) in att["missing_from_data"].as_object().unwrap() {
        assert_eq!(
            entry["count"].as_u64(),
            Some(0),
            "data claims full breadth but '{category}' is missing records: \
             {:?}",
            entry["names"]
        );
    }
}
