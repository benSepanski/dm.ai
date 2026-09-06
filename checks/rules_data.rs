//! Rules-data integrity lint, per system directory: files parse, IDs are
//! unique and stable-shaped, every record carries license metadata from
//! its system's allowlisted book under its system's license, the manifest
//! names its directory and carries its attribution text, version strings
//! carry the system prefix, cross-references resolve, and the reserved-noun
//! scrub runs per system.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};

/// Files in a system directory that are config/meta, not records.
const META_FILES: &[&str] = &[
    "manifest.json",
    "denylist.json",
    "shipped-versions.json",
    "attestation.json",
];

/// Per-system licensing facts the lint holds records to. Adding a system
/// or a book is a deliberate edit here AND a manifest-attribution
/// extension in the same change (spec req 9).
struct SystemLicense {
    system: &'static str,
    books: &'static [&'static str],
    license: &'static str,
    /// Text the manifest's license notice must carry (joined).
    notice_must_contain: &'static [&'static str],
}

const SYSTEMS: &[SystemLicense] = &[
    SystemLicense {
        system: "pf2e",
        books: &["Pathfinder Player Core"],
        license: "ORC",
        notice_must_contain: &["ORC License", "Pathfinder Player Core", "Reserved Material"],
    },
    SystemLicense {
        system: "dnd5e",
        books: &["System Reference Document 5.2.1"],
        license: "CC-BY-4.0",
        notice_must_contain: &[
            "System Reference Document 5.2.1",
            "Creative Commons Attribution 4.0",
        ],
    },
];

fn rules_root() -> PathBuf {
    checks::workspace_root().join("rules-data")
}

/// Every system directory under rules-data/.
fn system_dirs() -> Vec<(String, PathBuf)> {
    let mut dirs: Vec<(String, PathBuf)> = std::fs::read_dir(rules_root())
        .unwrap()
        .flatten()
        .filter(|e| e.path().is_dir())
        .map(|e| (e.file_name().to_string_lossy().to_string(), e.path()))
        .collect();
    dirs.sort();
    assert!(
        !dirs.is_empty(),
        "rules-data/ holds one directory per system"
    );
    dirs
}

fn license_for(system: &str) -> &'static SystemLicense {
    SYSTEMS
        .iter()
        .find(|s| s.system == system)
        .unwrap_or_else(|| {
            panic!("rules-data/{system}/ has no licensing entry in checks/rules_data.rs — adding a system is a deliberate edit here")
        })
}

fn read_json(path: &Path) -> serde_json::Value {
    serde_json::from_str(&std::fs::read_to_string(path).unwrap())
        .unwrap_or_else(|e| panic!("{} parses: {e}", path.display()))
}

/// Record files of a system directory (every .json that is not meta).
fn record_files(dir: &Path) -> Vec<PathBuf> {
    let mut files: Vec<PathBuf> = std::fs::read_dir(dir)
        .unwrap()
        .flatten()
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|e| e == "json"))
        .filter(|p| {
            !META_FILES.contains(&p.file_name().and_then(|n| n.to_str()).unwrap_or_default())
        })
        .collect();
    files.sort();
    files
}

/// Records of one file: a flat array, or an object of categorized arrays.
fn records_in(path: &Path) -> Vec<(String, serde_json::Value)> {
    let value = read_json(path);
    let file = path.file_name().unwrap().to_string_lossy().to_string();
    let records: Vec<serde_json::Value> = match value {
        serde_json::Value::Array(items) => items,
        serde_json::Value::Object(map) => map
            .values()
            .flat_map(|arr| {
                arr.as_array()
                    .unwrap_or_else(|| panic!("{file}: categorized file holds arrays"))
                    .clone()
            })
            .collect(),
        _ => panic!("{file}: a record file is an array or an object of arrays"),
    };
    records
        .into_iter()
        .map(|r| {
            let id = r["id"]
                .as_str()
                .unwrap_or_else(|| panic!("{file}: every record carries an id"))
                .to_string();
            (id, r)
        })
        .collect()
}

/// Collect (record id, record) from every record file of a system.
fn all_records(dir: &Path) -> Vec<(String, serde_json::Value)> {
    record_files(dir)
        .iter()
        .flat_map(|f| records_in(f))
        .collect()
}

#[test]
fn rules_data_parses_and_is_internally_consistent() {
    // RulesData::parse runs the full integrity pass (unique IDs, resolvable
    // cross-references); a violation panics with the offending record.
    let _ = checks::load_rules_data();
    // Every system directory's files at least parse as records with ids,
    // unique per system.
    for (system, dir) in system_dirs() {
        let mut seen = BTreeSet::new();
        for (id, _) in all_records(&dir) {
            assert!(
                seen.insert(id.clone()),
                "{system}: duplicate record id '{id}'"
            );
        }
        assert!(!seen.is_empty(), "{system}: ships no records");
    }
}

#[test]
fn every_record_carries_license_metadata() {
    for (system, dir) in system_dirs() {
        let license = license_for(&system);
        for file in record_files(&dir) {
            let name = file.file_name().unwrap().to_string_lossy().to_string();
            for (id, record) in records_in(&file) {
                assert_license(license, &record, &id, &format!("{system}/{name}"));
            }
        }
    }
}

fn assert_license(license: &SystemLicense, record: &serde_json::Value, id: &str, file: &str) {
    let source = record
        .get("source")
        .unwrap_or_else(|| panic!("{file}: record '{id}' has no source metadata"));
    for field in ["book", "page", "url", "license", "attribution"] {
        assert!(
            source.get(field).is_some(),
            "{file}: record '{id}' source is missing '{field}'"
        );
    }
    assert_eq!(
        source["license"].as_str(),
        Some(license.license),
        "{file}: record '{id}' must carry the {} license tag",
        license.license
    );
    let book = source["book"].as_str().unwrap_or("<no book>");
    assert!(
        license.books.contains(&book),
        "{file}: record '{id}' cites book '{book}' — outside the allowlist; \
         adding a book requires extending the manifest attribution in the \
         same change"
    );
    assert!(
        !source["attribution"]
            .as_str()
            .unwrap_or("")
            .trim()
            .is_empty(),
        "{file}: record '{id}' carries an empty attribution"
    );
}

/// The manifest names its directory (the selector key), every version it
/// names carries the system prefix, and its notice carries the system's
/// attribution text.
#[test]
fn manifests_name_their_system_and_carry_their_notice() {
    for (system, dir) in system_dirs() {
        let license = license_for(&system);
        let manifest = read_json(&dir.join("manifest.json"));
        assert_eq!(
            manifest["system"].as_str(),
            Some(system.as_str()),
            "{system}: manifest.system must equal the directory name"
        );
        let prefix = format!("{system}-");
        let version = manifest["version"].as_str().unwrap_or("");
        assert!(
            version.starts_with(&prefix),
            "{system}: version '{version}' must begin with '{prefix}'"
        );
        for v in manifest["supersedes"].as_array().into_iter().flatten() {
            assert!(
                v.as_str().unwrap_or("").starts_with(&prefix),
                "{system}: superseded version {v} must begin with '{prefix}'"
            );
        }
        let shipped = read_json(&dir.join("shipped-versions.json"));
        for key in shipped["versions"].as_object().unwrap().keys() {
            assert!(
                key.starts_with(&prefix),
                "{system}: shipped version '{key}' must begin with '{prefix}'"
            );
        }
        let notice = serde_json::to_string(&manifest["license_notice"]).unwrap();
        for needle in license.notice_must_contain {
            assert!(
                notice.contains(needle),
                "{system}: license notice must mention '{needle}'"
            );
        }
    }
}

/// Reserved-noun scrub (chargen-content spec req 5): no denylisted proper
/// noun in any shipped record's name or text. The denylist itself and
/// attestation waivers are repo tooling, exempt from this scan by
/// construction (only record files are scanned). Exceptions carry a
/// per-record reason. A system whose license reserves nothing ships an
/// empty term list.
#[test]
fn no_reserved_proper_nouns_in_records() {
    for (system, dir) in system_dirs() {
        let denylist = read_json(&dir.join("denylist.json"));
        let terms: Vec<String> = denylist["terms"]
            .as_array()
            .unwrap()
            .iter()
            .map(|t| t.as_str().unwrap().to_lowercase())
            .collect();
        let exceptions: BTreeMap<String, String> = denylist["exceptions"]
            .as_array()
            .unwrap()
            .iter()
            .map(|e| {
                let reason = e["reason"].as_str().unwrap_or("");
                assert!(
                    !reason.is_empty(),
                    "{system}: denylist exception for '{}' must carry a reason",
                    e["id"]
                );
                (e["id"].as_str().unwrap().to_string(), reason.to_string())
            })
            .collect();

        for (id, record) in all_records(&dir) {
            if exceptions.contains_key(&id) {
                continue;
            }
            let mut haystacks: Vec<(String, String)> = Vec::new();
            collect_strings(&record, "", &mut haystacks);
            for (path, text) in haystacks {
                // The url field legitimately encodes original names
                // (renamed records keep their url pointing at the original).
                if path.ends_with("url") {
                    continue;
                }
                let lower = text.to_lowercase();
                for term in &terms {
                    assert!(
                        !contains_word(&lower, term),
                        "{system}: record '{id}' field '{path}' contains reserved noun \
                         '{term}': scrub it per the ORC AxE deletion pattern, or \
                         add a reasoned exception in rules-data/{system}/denylist.json"
                    );
                }
            }
        }
    }
}

/// Word-boundary containment: `term` matches only when not embedded inside
/// a longer alphanumeric run ("torag" must not match "storage"). Both
/// inputs are already lowercased.
fn contains_word(haystack: &str, term: &str) -> bool {
    let bytes = haystack.as_bytes();
    let mut from = 0;
    while let Some(pos) = haystack[from..].find(term) {
        let start = from + pos;
        let end = start + term.len();
        let alnum = |b: u8| b.is_ascii_alphanumeric();
        let before_ok = start == 0 || !alnum(bytes[start - 1]);
        let after_ok = end == bytes.len() || !alnum(bytes[end]);
        if before_ok && after_ok {
            return true;
        }
        from = start + 1;
    }
    false
}

fn collect_strings(value: &serde_json::Value, path: &str, out: &mut Vec<(String, String)>) {
    match value {
        serde_json::Value::String(s) => out.push((path.to_string(), s.clone())),
        serde_json::Value::Array(items) => {
            for (i, item) in items.iter().enumerate() {
                collect_strings(item, &format!("{path}[{i}]"), out);
            }
        }
        serde_json::Value::Object(map) => {
            for (key, item) in map {
                let child = if path.is_empty() {
                    key.clone()
                } else {
                    format!("{path}.{key}")
                };
                collect_strings(item, &child, out);
            }
        }
        _ => {}
    }
}

/// ID immutability + version lineage, one artifact per system: every
/// version in the manifest's `supersedes` list has its ID set recorded in
/// shipped-versions.json, the current version's ID set is recorded too and
/// equals the shipped records, and every recorded ID of every shipped
/// version still resolves in current data (wrong records are deprecated,
/// never deleted).
#[test]
fn shipped_ids_are_immutable_and_lineage_is_recorded() {
    for (system, dir) in system_dirs() {
        let shipped = read_json(&dir.join("shipped-versions.json"));
        let versions = shipped["versions"].as_object().unwrap();
        let manifest = read_json(&dir.join("manifest.json"));
        for superseded in manifest["supersedes"].as_array().into_iter().flatten() {
            let superseded = superseded.as_str().unwrap();
            assert!(
                versions.contains_key(superseded),
                "{system}: manifest supersedes '{superseded}' but shipped-versions.json has \
                 no ID set for it — append the superseded version's IDs at bump time"
            );
        }
        let current: BTreeSet<String> = all_records(&dir).into_iter().map(|(id, _)| id).collect();
        for (version, ids) in versions {
            for id in ids.as_array().unwrap() {
                let id = id.as_str().unwrap();
                assert!(
                    current.contains(id),
                    "{system}: record '{id}' (shipped in {version}) is missing from current \
                     data: shipped IDs are never deleted — deprecate the record \
                     (unselectable in new drafts, still resolvable) instead"
                );
            }
        }
        let current_version = manifest["version"].as_str().unwrap();
        if let Some(recorded) = versions.get(current_version) {
            let recorded: BTreeSet<String> = recorded
                .as_array()
                .unwrap()
                .iter()
                .map(|v| v.as_str().unwrap().to_string())
                .collect();
            assert_eq!(
                recorded, current,
                "{system}: the recorded ID set for '{current_version}' must equal the shipped records"
            );
        }
    }
}

/// Name pools (roster-ergonomics req 4): own-authored app data living
/// OUTSIDE rules-data/ (which keeps it out of attestation and
/// reference-check by construction). Every shipped ancestry (PF2e) and
/// species (5.5e) has a pool of at least a dozen usable names, the default
/// pool is non-empty, no name is blank, and no record carries license
/// metadata — pools are not rules content.
#[test]
fn name_pools_cover_every_shipped_ancestry_and_species() {
    let root = checks::workspace_root();
    let pools_path = root.join("app-data/name-pools.json");
    assert!(
        pools_path.starts_with(root.join("app-data")),
        "pools live outside rules-data/"
    );
    let pools: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(&pools_path).unwrap())
            .expect("app-data/name-pools.json parses");
    let default = pools["default"].as_array().expect("default pool");
    assert!(!default.is_empty(), "the default pool backs every fallback");

    let text = serde_json::to_string(&pools).unwrap();
    assert!(
        !text.contains("\"license\"") && !text.contains("\"attribution\""),
        "name pools are app data — no license machinery"
    );

    let by_key = pools["pools"].as_object().expect("pools map");
    for (system, dir) in system_dirs() {
        for file in ["ancestries.json", "species.json"] {
            let path = dir.join(file);
            if !path.exists() {
                continue;
            }
            for (id, _) in records_in(&path) {
                let pool = by_key
                    .get(&id)
                    .and_then(|p| p.as_array())
                    .unwrap_or_else(|| panic!("{system}: shipped '{id}' has no name pool"));
                assert!(
                    pool.len() >= 12,
                    "{system}: '{id}' pool has {} names — at least a dozen required",
                    pool.len()
                );
            }
        }
    }
    for (pool_id, pool) in by_key {
        for name in pool.as_array().expect("pool is a list") {
            let name = name.as_str().expect("names are strings");
            assert!(!name.trim().is_empty(), "blank name in pool '{pool_id}'");
        }
    }
    for name in default {
        assert!(
            !name.as_str().unwrap().trim().is_empty(),
            "blank default name"
        );
    }
}

/// Advancement data (level-up architecture): every shipped PF2e class
/// defines every level through the shipped cap (the ruleset's integrity
/// check refuses otherwise — asserted here as data facts), fixed features
/// are records with namespaced IDs, a caster's slot table reaches the cap,
/// and the level-3 world's cap is exactly 3.
#[test]
fn advancement_tables_reach_the_shipped_cap() {
    let data = checks::load_rules_data();
    let cap = data.max_advancement_level();
    assert_eq!(
        cap, 3,
        "the level-3 world: every class advances to exactly 3"
    );
    for class in &data.classes {
        let levels: Vec<u32> = class.advancement.iter().map(|a| a.level).collect();
        assert_eq!(
            levels,
            (2..=cap).collect::<Vec<_>>(),
            "{}: advancement must run 2..={cap}",
            class.id
        );
        for adv in &class.advancement {
            for feature in &adv.features {
                assert!(
                    feature.id.starts_with("feature."),
                    "{}: feature '{}' must carry a 'feature.' ID",
                    class.id,
                    feature.id
                );
            }
        }
        if let Some(sc) = &class.spellcasting {
            for level in 2..=cap {
                assert!(
                    sc.slots_by_level.contains_key(&level),
                    "{}: spell slot table must define level {level}",
                    class.id
                );
            }
        }
    }
    // The level-2 and level-3 catalogs exist for both classes: at least one
    // level-2 class feat per class, at least one level-2 skill feat, at
    // least one level-3 general feat, and rank-2 arcane spells.
    for class in &data.classes {
        assert!(
            data.class_feats
                .iter()
                .any(|f| f.class == class.id && f.level == 2),
            "{}: ships no level-2 class feat",
            class.id
        );
    }
    assert!(data
        .general_feats
        .iter()
        .any(|f| f.id.starts_with("feat.skill.") && f.level == 2));
    assert!(data
        .general_feats
        .iter()
        .any(|f| f.id.starts_with("feat.general.") && f.level == 3));
    assert!(data
        .spells
        .spells
        .iter()
        .any(|s| s.rank == 2 && s.traditions.iter().any(|t| t == "arcane")));
}

/// 5.5e advancement data as JSON facts: every class's advancement runs
/// 2..=3 contiguously, fixed features carry `feature.` IDs, and every
/// subclass record cross-references a shipped class.
#[test]
fn dnd5e_advancement_tables_reach_the_shipped_cap() {
    let dir = rules_root().join("dnd5e");
    if !dir.exists() {
        panic!("rules-data/dnd5e/ must exist (chargen-dnd)");
    }
    let classes = read_json(&dir.join("classes.json"));
    let class_ids: BTreeSet<String> = classes
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["id"].as_str().unwrap().to_string())
        .collect();
    assert!(!class_ids.is_empty(), "dnd5e ships at least one class");
    for class in classes.as_array().unwrap() {
        let id = class["id"].as_str().unwrap();
        let levels: Vec<u64> = class["advancement"]
            .as_array()
            .unwrap_or_else(|| panic!("{id}: advancement block"))
            .iter()
            .map(|a| a["level"].as_u64().unwrap())
            .collect();
        assert_eq!(levels, vec![2, 3], "{id}: advancement must run 2..=3");
        for adv in class["advancement"].as_array().unwrap() {
            for feature in adv["features"].as_array().into_iter().flatten() {
                assert!(
                    feature["id"].as_str().unwrap_or("").starts_with("feature."),
                    "{id}: feature ids carry a 'feature.' prefix"
                );
            }
        }
    }
    let subclasses = read_json(&dir.join("subclasses.json"));
    assert!(
        !subclasses.as_array().unwrap().is_empty(),
        "dnd5e ships at least one subclass"
    );
    for sub in subclasses.as_array().unwrap() {
        let class = sub["class"].as_str().unwrap_or("");
        assert!(
            class_ids.contains(class),
            "subclass '{}' names class '{class}', which is not shipped",
            sub["id"]
        );
    }
}
