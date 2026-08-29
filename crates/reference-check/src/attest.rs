//! The `attest` subcommand: verify the cache, match every shipped record,
//! enforce waiver bindings, sweep reverse completeness, and write
//! `rules-data/attestation.json`.
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

use crate::foundry::{normalize_name, FoundryRecord, Index, Partition};
use crate::ours::{Kind, OurRecord};
use crate::{cache, canon, compare, foundry, ours, workspace_root, FOUNDRY_SHA256, FOUNDRY_TAG};

/// Set to true only when the shipped data claims full Player Core breadth
/// (spec req 1 complete — the orchestrator flips this when the T3–T5 data
/// tickets land). While false, `missing_from_data` is informational: the
/// offline check asserts it empty only under a true flag.
const CLAIMS_FULL_BREADTH: bool = false;

const CONFIG_PATH: &str = "crates/reference-check/overrides.json";

struct Config {
    overrides: BTreeMap<String, String>,
    waivers: BTreeMap<String, Waiver>,
    /// (sweep category, normalized record name) pairs the spec excludes by
    /// name from full breadth (e.g. Raised by Belief, spec req 1 [call]).
    /// Reasons live in the config file; the reverse sweep skips these so a
    /// future claims_full_breadth=true does not demand out-of-scope records.
    spec_exclusions: BTreeSet<(String, String)>,
}

struct Waiver {
    reason: String,
    state_hash: String,
}

fn load_config() -> Result<Config, String> {
    let path = workspace_root().join(CONFIG_PATH);
    let text = std::fs::read_to_string(&path).map_err(|e| format!("reading {CONFIG_PATH}: {e}"))?;
    let value: Value =
        serde_json::from_str(&text).map_err(|e| format!("parsing {CONFIG_PATH}: {e}"))?;
    let mut overrides = BTreeMap::new();
    if let Some(map) = value["overrides"].as_object() {
        for (id, target) in map {
            let target = target
                .as_str()
                .ok_or_else(|| format!("override for '{id}' must be a pack-relative path"))?;
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

fn partition_for(record: &OurRecord) -> Option<Partition> {
    // A record-level `category: "skill"` (once skill feats ship in the
    // general-feats file) routes the lookup to the skill-feat partition.
    if record.kind == Kind::GeneralFeat && record.value["category"].as_str() == Some("skill") {
        return Some(Partition::FeatSkill);
    }
    match record.kind {
        Kind::Ancestry => Some(Partition::Ancestry),
        Kind::Heritage => Some(Partition::Heritage),
        Kind::Background => Some(Partition::Background),
        Kind::Class => Some(Partition::Class),
        Kind::AncestryFeat => Some(Partition::FeatAncestry),
        Kind::ClassFeat => Some(Partition::FeatClass),
        Kind::GeneralFeat => Some(Partition::FeatGeneral),
        Kind::Weapon => Some(Partition::Weapon),
        Kind::Armor => Some(Partition::Armor),
        Kind::Shield => Some(Partition::Shield),
        Kind::Gear => Some(Partition::Gear),
        // No Foundry pack exists for these: PF2e core skills are fixed game
        // vocabulary (not compendium records) and class kits ship only in
        // the book. They are attestable solely via reviewed waivers.
        Kind::Skill | Kind::Kit => None,
    }
}

pub fn attest() -> Result<(), String> {
    // Never attest against unverified content (torn-cache failure mode).
    cache::ensure_verified()?;
    let records = ours::load_all()?;
    let index = foundry::load_index()?;
    let config = load_config()?;

    for id in config.overrides.keys().chain(config.waivers.keys()) {
        if !records.iter().any(|r| &r.id == id) {
            return Err(format!(
                "{CONFIG_PATH} names '{id}', which is not a shipped record"
            ));
        }
    }

    let mut attested: BTreeMap<String, Value> = BTreeMap::new();
    let mut overrides_used: BTreeSet<String> = BTreeSet::new();
    let mut matched_paths: BTreeSet<String> = BTreeSet::new();
    let mut errors: Vec<String> = Vec::new();
    let mut per_file: BTreeMap<String, [usize; 3]> = BTreeMap::new(); // match/waived/mismatch

    for record in &records {
        let counterpart = find_counterpart(record, &index, &config, &mut overrides_used)?;
        let outcome = match &counterpart {
            Some(f) => compare::compare(record, f),
            None => compare::fields_for_missing(record.kind),
        };
        if let Some(f) = &counterpart {
            matched_paths.insert(f.path.clone());
        }

        let file_hash = canon::record_hash(&record.value);
        let state = json!({
            "counterpart": if counterpart.is_some() { "found" } else { "missing" },
            "mismatched_fields": outcome.mismatches,
            "record_hash": file_hash,
        });
        let state_hash = canon::sha256_hex(canon::canonical_json(&state).as_bytes());
        let clean = counterpart.is_some() && outcome.mismatches.is_empty();

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
                    record.id, outcome.mismatches
                ));
                ("mismatch", Value::Null)
            }
            (false, None) => {
                errors.push(format!(
                    "unwaived mismatch: '{}' fields {:?}; waiver state_hash would \
                     be {state_hash}",
                    record.id, outcome.mismatches
                ));
                ("mismatch", Value::Null)
            }
        };

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
                "fields_checked": outcome.fields_checked,
                "mismatches": outcome.mismatches,
                "waiver": waiver_json,
            }),
        );
    }

    let missing_from_data = reverse_sweep(&index, &matched_paths, &config);
    let manifest = manifest_version()?;

    let attestation = json!({
        "tool_version": env!("CARGO_PKG_VERSION"),
        "foundry_tag": FOUNDRY_TAG,
        "foundry_sha256": FOUNDRY_SHA256,
        "rules_version": manifest,
        "generated": canon::utc_date_today(),
        "claims_full_breadth": CLAIMS_FULL_BREADTH,
        "records": attested,
        "missing_from_data": missing_from_data,
        "overrides_used": overrides_used,
    });
    let out_path = workspace_root().join("rules-data/attestation.json");
    let mut text = serde_json::to_string_pretty(&sorted(&attestation))
        .expect("serializing owned JSON cannot fail");
    text.push('\n');
    std::fs::write(&out_path, text).map_err(|e| format!("writing attestation: {e}"))?;

    eprintln!("attestation written to rules-data/attestation.json");
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

fn find_counterpart(
    record: &OurRecord,
    index: &Index,
    config: &Config,
    overrides_used: &mut BTreeSet<String>,
) -> Result<Option<FoundryRecord>, String> {
    let Some(partition) = partition_for(record) else {
        return Ok(None);
    };
    if let Some(target) = config.overrides.get(&record.id) {
        let found = index.load_by_path(target)?;
        if !found.is_player_core() {
            return Err(format!(
                "override target '{target}' for '{}' is not a Player Core record",
                record.id
            ));
        }
        overrides_used.insert(record.id.clone());
        return Ok(Some(found));
    }
    match index.find(partition, &normalize_name(&record.name)) {
        // Publication filter: a same-name record from another book is not a
        // counterpart (dual-source records keep the Player Core printing in
        // Foundry's packs, so title equality is the whole filter).
        Some(f) if f.is_player_core() => Ok(Some(FoundryRecord {
            path: f.path.clone(),
            value: f.value.clone(),
        })),
        _ => Ok(None),
    }
}

/// Reverse completeness (spec req 4 "completeness runs both ways"): for
/// every category where the spec claims full common-Player-Core breadth,
/// list ground-truth records we do not ship. Only record NAMES and counts
/// cross into the attestation — names of published records are facts, and
/// the one identifier the no-ground-truth-content rule permits.
///
/// The `classes` pack is deliberately not swept: this slice claims breadth
/// for a level-1 Fighter's selectable content, not for other classes.
/// (attestation section name, partition, ground-truth filter).
type SweepCategory = (&'static str, Partition, fn(&FoundryRecord) -> bool);

fn reverse_sweep(
    index: &Index,
    matched_paths: &BTreeSet<String>,
    config: &Config,
) -> BTreeMap<String, Value> {
    let mut out = BTreeMap::new();
    let categories: &[SweepCategory] = &[
        ("ancestries", Partition::Ancestry, |_| true),
        ("heritages", Partition::Heritage, |_| true),
        ("backgrounds", Partition::Background, |_| true),
        ("ancestry_feats_l1", Partition::FeatAncestry, level_1),
        ("fighter_feats_l1", Partition::FeatClass, |f| {
            level_1(f) && has_trait(f, "fighter")
        }),
        ("general_feats_l1", Partition::FeatGeneral, level_1),
        ("skill_feats_l1", Partition::FeatSkill, level_1),
        ("weapons", Partition::Weapon, level_0_item),
        ("armor", Partition::Armor, level_0_item),
        ("shields", Partition::Shield, level_0_item),
        ("gear", Partition::Gear, level_0_item),
    ];
    for (name, partition, filter) in categories {
        let mut names: Vec<String> = index
            .all(*partition)
            .filter(|f| f.is_player_core() && f.rarity() == "common" && filter(f))
            .filter(|f| !matched_paths.contains(&f.path))
            .filter(|f| {
                !config
                    .spec_exclusions
                    .contains(&((*name).to_string(), normalize_name(f.name())))
            })
            .map(|f| f.name().to_string())
            .collect();
        names.sort();
        out.insert(
            (*name).to_string(),
            json!({ "count": names.len(), "names": names }),
        );
    }
    out
}

fn level_1(f: &FoundryRecord) -> bool {
    f.system()["level"]["value"].as_i64() == Some(1)
}

fn level_0_item(f: &FoundryRecord) -> bool {
    f.system()["level"]["value"].as_i64().unwrap_or(0) == 0
}

fn has_trait(f: &FoundryRecord, t: &str) -> bool {
    f.system()["traits"]["value"]
        .as_array()
        .is_some_and(|a| a.iter().any(|v| v.as_str() == Some(t)))
}

fn manifest_version() -> Result<String, String> {
    let path = workspace_root().join("rules-data/manifest.json");
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
