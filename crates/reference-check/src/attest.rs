//! The `attest` subcommand: verify the cache, match every shipped record
//! through the system's comparator, enforce waiver bindings, sweep reverse
//! completeness, and write `rules-data/<system>/attestation.json`.
//!
//! This module is the system-independent half: the verdict loop, the
//! waiver binding, and the one attestation schema. The per-system halves
//! (`pf2e.rs`, `dnd5e.rs`) produce a `Pass` — one `Matched` per shipped
//! record plus the reverse sweep — and are selected by a `match`.
//!
//! Waiver semantics (architecture, "Failure modes"): a waiver in
//! overrides.json is bound to the sha256 of the comparison state it excuses
//! ({counterpart found/missing, mismatched field names, our record's
//! content hash}). If the mismatch disappears (waiver matches nothing) or
//! shifts (different fields, or the record was edited), THIS tool fails —
//! stale-waiver detection is a tool-time responsibility because offline CI
//! cannot see the ground truth. The offline check
//! (`checks/attestation.rs`) verifies waiver hygiene and seals the rest
//! through the per-record content hashes.

use std::collections::{BTreeMap, BTreeSet};

use serde_json::{json, Value};

use crate::compare::Outcome;
use crate::foundry::normalize_name;
use crate::ours::OurRecord;
use crate::{
    cache, canon, dnd5e, ours, pf2e, workspace_root, System, FOUNDRY_SHA256, FOUNDRY_TAG,
    SRD_COMMIT, SRD_PDF_SHA256, SRD_REPO, SRD_SHA256,
};

/// Whether the shipped data claims full breadth for its reverse-sweep
/// categories. PF2e: true (spec chargen-content req 1 complete). 5.5e:
/// false — the slice ships a representative subset (four species, the
/// SRD's four backgrounds; weapons and armor are complete but the claim is
/// per system), so `missing_from_data` is informational there.
fn claims_full_breadth(system: System) -> bool {
    match system {
        System::Pf2e => true,
        System::Dnd5e => false,
    }
}

const CONFIG_PATH: &str = "crates/reference-check/overrides.json";

pub struct Config {
    pub overrides: BTreeMap<String, String>,
    pub waivers: BTreeMap<String, Waiver>,
    /// (sweep category, normalized record name) pairs the spec excludes by
    /// name from full breadth (e.g. Raised by Belief, spec req 1 [call]).
    /// Reasons live in the config file; the reverse sweep skips these so a
    /// future claims_full_breadth=true does not demand out-of-scope records.
    pub spec_exclusions: BTreeSet<(String, String)>,
}

pub struct Waiver {
    pub reason: String,
    pub state_hash: String,
}

/// One shipped record's comparison result, before waivers are applied.
pub struct Matched {
    pub found: bool,
    pub outcome: Outcome,
}

/// A system pass: `matched` is parallel to the record list it was built
/// from; the sweep and override bookkeeping feed the attestation directly.
pub struct Pass {
    pub matched: Vec<Matched>,
    pub missing_from_data: BTreeMap<String, Value>,
    pub overrides_used: BTreeSet<String>,
}

fn load_config(system: System) -> Result<Config, String> {
    let path = workspace_root().join(CONFIG_PATH);
    let text = std::fs::read_to_string(&path).map_err(|e| format!("reading {CONFIG_PATH}: {e}"))?;
    let all: Value =
        serde_json::from_str(&text).map_err(|e| format!("parsing {CONFIG_PATH}: {e}"))?;
    let value = all
        .get(system.id())
        .ok_or_else(|| format!("{CONFIG_PATH} has no '{}' block", system.id()))?;
    let mut overrides = BTreeMap::new();
    if let Some(map) = value["overrides"].as_object() {
        for (id, target) in map {
            let target = target
                .as_str()
                .ok_or_else(|| format!("override for '{id}' must be a source-relative path"))?;
            overrides.insert(id.clone(), target.to_string());
        }
    }
    let mut waivers = BTreeMap::new();
    if let Some(list) = value["waivers"].as_array() {
        for entry in list {
            let id = entry["id"]
                .as_str()
                .ok_or("waiver without an id")?
                .to_string();
            let reason = entry["reason"].as_str().unwrap_or("").to_string();
            if reason.is_empty() {
                return Err(format!("waiver for '{id}' has no reason"));
            }
            let state_hash = entry["state_hash"].as_str().unwrap_or("").to_string();
            if waivers
                .insert(id.clone(), Waiver { reason, state_hash })
                .is_some()
            {
                return Err(format!("duplicate waiver for '{id}'"));
            }
        }
    }
    let mut spec_exclusions = BTreeSet::new();
    if let Some(list) = value["spec_exclusions"].as_array() {
        for entry in list {
            let category = entry["category"]
                .as_str()
                .ok_or("spec_exclusion without a category")?;
            let name = entry["name"]
                .as_str()
                .ok_or("spec_exclusion without a name")?;
            if entry["reason"].as_str().unwrap_or("").is_empty() {
                return Err(format!("spec_exclusion '{name}' has no reason"));
            }
            spec_exclusions.insert((category.to_string(), normalize_name(name)));
        }
    }
    Ok(Config {
        overrides,
        waivers,
        spec_exclusions,
    })
}

/// The per-source `source` block: kind + sha256 are shared across systems;
/// the other keys are short identifiers (a tag, a commit, a url) — never
/// content. `checks/attestation.rs` enforces exactly that shape.
fn source_block(system: System) -> Value {
    match system {
        System::Pf2e => json!({
            "kind": "foundry-pf2e",
            "tag": FOUNDRY_TAG,
            "sha256": FOUNDRY_SHA256,
        }),
        System::Dnd5e => json!({
            "kind": "srd521-markdown",
            "repo": SRD_REPO,
            "commit": SRD_COMMIT,
            "url": format!("https://github.com/{SRD_REPO}/archive/{SRD_COMMIT}.tar.gz"),
            "sha256": SRD_SHA256,
            "pdf_sha256": SRD_PDF_SHA256,
        }),
    }
}

pub fn attest(system: System) -> Result<(), String> {
    // Never attest against unverified content (torn-cache failure mode).
    cache::ensure_verified(system)?;
    let records = ours::load_all(system)?;
    let config = load_config(system)?;

    for id in config.overrides.keys().chain(config.waivers.keys()) {
        if !records.iter().any(|r| &r.id == id) {
            return Err(format!(
                "{CONFIG_PATH} ({}) names '{id}', which is not a shipped record",
                system.id()
            ));
        }
    }

    let pass = match system {
        System::Pf2e => pf2e::run(&records, &config)?,
        System::Dnd5e => dnd5e::run(&records, &config)?,
    };
    assert_eq!(pass.matched.len(), records.len(), "one Matched per record");

    let mut attested: BTreeMap<String, Value> = BTreeMap::new();
    let mut errors: Vec<String> = Vec::new();
    let mut per_file: BTreeMap<String, [usize; 3]> = BTreeMap::new(); // match/waived/mismatch

    for (record, matched) in records.iter().zip(&pass.matched) {
        let (verdict, waiver_json, file_hash) = verdict_for(record, matched, &config, &mut errors);

        let counts = per_file.entry(record.file.clone()).or_default();
        match verdict {
            "match" => counts[0] += 1,
            "waived" => counts[1] += 1,
            _ => counts[2] += 1,
        }

        attested.insert(
            record.id.clone(),
            json!({
                "file_hash": file_hash,
                "verdict": verdict,
                "fields_checked": matched.outcome.fields_checked,
                "mismatches": matched.outcome.mismatches,
                "waiver": waiver_json,
            }),
        );
    }

    let manifest = manifest_version(system)?;

    let attestation = json!({
        "tool_version": env!("CARGO_PKG_VERSION"),
        "source": source_block(system),
        "rules_version": manifest,
        "generated": canon::utc_date_today(),
        "claims_full_breadth": claims_full_breadth(system),
        "records": attested,
        "missing_from_data": pass.missing_from_data,
        "overrides_used": pass.overrides_used,
    });
    let rel = format!("rules-data/{}/attestation.json", system.id());
    let out_path = workspace_root().join(&rel);
    let mut text = serde_json::to_string_pretty(&sorted(&attestation))
        .expect("serializing owned JSON cannot fail");
    text.push('\n');
    std::fs::write(&out_path, text).map_err(|e| format!("writing attestation: {e}"))?;

    eprintln!("attestation written to {rel}");
    eprintln!("  per-file verdicts (match/waived/mismatch):");
    for (file, [m, w, x]) in &per_file {
        eprintln!("    {file}: {m}/{w}/{x}");
    }
    if errors.is_empty() {
        eprintln!("  zero unwaived mismatches; zero stale waivers");
        Ok(())
    } else {
        Err(format!(
            "{} problem(s):\n  {}",
            errors.len(),
            errors.join("\n  ")
        ))
    }
}

/// Apply the waiver binding to one record: (verdict, waiver json,
/// file_hash). Problems are appended to `errors`; the attestation is still
/// written so the printed state_hash can be reviewed into overrides.json.
fn verdict_for(
    record: &OurRecord,
    matched: &Matched,
    config: &Config,
    errors: &mut Vec<String>,
) -> (&'static str, Value, String) {
    let file_hash = canon::record_hash(&record.value);
    let state = json!({
        "counterpart": if matched.found { "found" } else { "missing" },
        "mismatched_fields": matched.outcome.mismatches,
        "record_hash": file_hash,
    });
    let state_hash = canon::sha256_hex(canon::canonical_json(&state).as_bytes());
    let clean = matched.found && matched.outcome.mismatches.is_empty();

    let (verdict, waiver_json) = match (clean, config.waivers.get(&record.id)) {
        (true, None) => ("match", Value::Null),
        (true, Some(_)) => {
            errors.push(format!(
                "stale waiver: '{}' now matches cleanly — remove its waiver \
                 from {CONFIG_PATH}",
                record.id
            ));
            ("match", Value::Null)
        }
        (false, Some(w)) if w.state_hash == state_hash => (
            "waived",
            json!({ "reason": w.reason, "state_hash": w.state_hash }),
        ),
        (false, Some(_)) => {
            errors.push(format!(
                "stale waiver: '{}' mismatch state shifted; current state_hash \
                 is {state_hash} (fields: {:?}) — re-review before updating \
                 {CONFIG_PATH}",
                record.id, matched.outcome.mismatches
            ));
            ("mismatch", Value::Null)
        }
        (false, None) => {
            errors.push(format!(
                "unwaived mismatch: '{}' fields {:?}; waiver state_hash would \
                 be {state_hash}",
                record.id, matched.outcome.mismatches
            ));
            ("mismatch", Value::Null)
        }
    };
    (verdict, waiver_json, file_hash)
}

fn manifest_version(system: System) -> Result<String, String> {
    let path = workspace_root()
        .join("rules-data")
        .join(system.id())
        .join("manifest.json");
    let text = std::fs::read_to_string(&path).map_err(|e| format!("reading manifest.json: {e}"))?;
    let value: Value =
        serde_json::from_str(&text).map_err(|e| format!("parsing manifest.json: {e}"))?;
    value["version"]
        .as_str()
        .map(String::from)
        .ok_or_else(|| "manifest.json has no version".to_string())
}

/// Stable key order for the committed artifact (diffs stay reviewable).
fn sorted(value: &Value) -> Value {
    match value {
        Value::Object(map) => {
            let mut pairs: Vec<(&String, &Value)> = map.iter().collect();
            pairs.sort_by_key(|(k, _)| k.as_str());
            let mut out = serde_json::Map::new();
            for (k, v) in pairs {
                out.insert(k.clone(), sorted(v));
            }
            Value::Object(out)
        }
        Value::Array(items) => Value::Array(items.iter().map(sorted).collect()),
        other => other.clone(),
    }
}
