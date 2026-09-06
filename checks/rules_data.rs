//! Rules-data integrity lint: files parse, IDs are unique and stable-shaped,
//! every record carries license metadata, cross-references resolve, and the
//! ORC notice text is present for the app to display.

#[test]
fn rules_data_parses_and_is_internally_consistent() {
    // RulesData::parse runs the full integrity pass (unique IDs, resolvable
    // cross-references); a violation panics with the offending record.
    let _ = checks::load_rules_data();
}

#[test]
fn every_record_carries_license_metadata() {
    let root = checks::workspace_root().join("rules-data/pf2e");
    for file in [
        "ancestries.json",
        "heritages.json",
        "ancestry-feats.json",
        "backgrounds.json",
        "classes.json",
        "class-feats.json",
        "general-feats.json",
        "skills.json",
    ] {
        let text = std::fs::read_to_string(root.join(file)).unwrap();
        let records: Vec<serde_json::Value> = serde_json::from_str(&text).unwrap();
        for record in records {
            assert_license(&record, file);
        }
    }
    // equipment.json and spells.json hold categorized arrays.
    for file in ["equipment.json", "spells.json"] {
        let text = std::fs::read_to_string(root.join(file)).unwrap();
        let value: serde_json::Value = serde_json::from_str(&text).unwrap();
        for (key, records) in value.as_object().unwrap() {
            for record in records.as_array().unwrap() {
                assert_license(record, &format!("{file}/{key}"));
            }
        }
    }
}

/// The only book records may cite. Any new book is a deliberate edit here
/// AND a manifest-attribution extension in the same change (spec req 5).
const ALLOWED_SOURCE_BOOKS: &[&str] = &["Pathfinder Player Core"];

fn assert_license(record: &serde_json::Value, file: &str) {
    let id = record["id"].as_str().unwrap_or("<no id>");
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
        Some("ORC"),
        "{file}: record '{id}' must carry the ORC license tag"
    );
    let book = source["book"].as_str().unwrap_or("<no book>");
    assert!(
        ALLOWED_SOURCE_BOOKS.contains(&book),
        "{file}: record '{id}' cites book '{book}' — outside the allowlist; \
         adding a book requires extending the manifest attribution in the \
         same change"
    );
}

#[test]
fn manifest_carries_the_orc_notice() {
    let data = checks::load_rules_data();
    let notice = &data.manifest.license_notice;
    assert!(
        notice.orc_notice.contains("ORC License"),
        "ORC notice text missing"
    );
    assert!(
        notice.attribution.contains("Pathfinder Player Core"),
        "attribution must name the licensed material"
    );
    assert!(
        notice.reserved.contains("Reserved Material"),
        "reserved-material statement missing"
    );
}

/// Every rules-data file holding records (manifest, denylist, and
/// shipped-versions are config/meta, not records).
const RECORD_FILES: &[&str] = &[
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

/// Collect (record id, full record JSON) from every record file.
fn all_records() -> Vec<(String, serde_json::Value)> {
    let root = checks::workspace_root().join("rules-data/pf2e");
    let mut out = Vec::new();
    for file in RECORD_FILES {
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
            let id = record["id"].as_str().unwrap_or("<no id>").to_string();
            out.push((id, record));
        }
    }
    out
}

/// Reserved-noun scrub (spec req 5): no denylisted proper noun in any
/// shipped record's name or text. The denylist itself and attestation
/// waivers are repo tooling, exempt from this scan by construction (only
/// record files are scanned). Exceptions carry a per-record reason.
#[test]
fn no_reserved_proper_nouns_in_records() {
    let root = checks::workspace_root().join("rules-data/pf2e");
    let denylist: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(root.join("denylist.json")).unwrap())
            .unwrap();
    let terms: Vec<String> = denylist["terms"]
        .as_array()
        .unwrap()
        .iter()
        .map(|t| t.as_str().unwrap().to_lowercase())
        .collect();
    assert!(!terms.is_empty(), "denylist.json has no terms");
    let exceptions: std::collections::BTreeMap<String, String> = denylist["exceptions"]
        .as_array()
        .unwrap()
        .iter()
        .map(|e| {
            let reason = e["reason"].as_str().unwrap_or("");
            assert!(
                !reason.is_empty(),
                "denylist exception for '{}' must carry a reason",
                e["id"]
            );
            (e["id"].as_str().unwrap().to_string(), reason.to_string())
        })
        .collect();

    for (id, record) in all_records() {
        if exceptions.contains_key(&id) {
            continue;
        }
        let mut haystacks: Vec<(String, String)> = Vec::new();
        collect_strings(&record, "", &mut haystacks);
        for (path, text) in haystacks {
            // The url field legitimately encodes original names (renamed
            // records keep their AoN url pointing at the original).
            if path.ends_with("url") {
                continue;
            }
            let lower = text.to_lowercase();
            for term in &terms {
                assert!(
                    !contains_word(&lower, term),
                    "record '{id}' field '{path}' contains reserved noun \
                     '{term}': scrub it per the ORC AxE deletion pattern, or \
                     add a reasoned exception in rules-data/denylist.json"
                );
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

/// ID immutability + version lineage, one artifact (architecture table):
/// every version in the manifest's `supersedes` list has its ID set
/// recorded in shipped-versions.json, and every recorded ID of every
/// shipped version still resolves in current data (wrong records are
/// deprecated, never deleted).
#[test]
fn shipped_ids_are_immutable_and_lineage_is_recorded() {
    let root = checks::workspace_root().join("rules-data/pf2e");
    let shipped: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(root.join("shipped-versions.json")).unwrap())
            .unwrap();
    let versions = shipped["versions"].as_object().unwrap();
    let data = checks::load_rules_data();

    for superseded in &data.manifest.supersedes {
        assert!(
            versions.contains_key(superseded),
            "manifest supersedes '{superseded}' but shipped-versions.json has \
             no ID set for it — append the superseded version's IDs at bump \
             time"
        );
    }

    let current: std::collections::BTreeSet<String> =
        all_records().into_iter().map(|(id, _)| id).collect();
    for (version, ids) in versions {
        for id in ids.as_array().unwrap() {
            let id = id.as_str().unwrap();
            assert!(
                current.contains(id),
                "record '{id}' (shipped in {version}) is missing from current \
                 data: shipped IDs are never deleted — deprecate the record \
                 (unselectable in new drafts, still resolvable) instead"
            );
        }
    }
}

/// Name pools (roster-ergonomics req 4): own-authored app data living
/// OUTSIDE rules-data/ (which keeps it out of attestation and
/// reference-check by construction). Every shipped ancestry has a pool of
/// at least a dozen usable names, the default pool is non-empty, no name
/// is blank, and no record carries license metadata — pools are not rules
/// content.
#[test]
fn name_pools_cover_every_shipped_ancestry() {
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

    let ancestries: serde_json::Value = serde_json::from_str(
        &std::fs::read_to_string(root.join("rules-data/pf2e/ancestries.json")).unwrap(),
    )
    .unwrap();
    let by_ancestry = pools["pools"].as_object().expect("pools map");
    for record in ancestries.as_array().unwrap() {
        let id = record["id"].as_str().unwrap();
        let pool = by_ancestry
            .get(id)
            .and_then(|p| p.as_array())
            .unwrap_or_else(|| panic!("shipped ancestry '{id}' has no name pool"));
        assert!(
            pool.len() >= 12,
            "ancestry '{id}' pool has {} names — at least a dozen required",
            pool.len()
        );
    }
    for (pool_id, pool) in by_ancestry {
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

/// Advancement data (level-up architecture): every shipped class defines
/// every level through the shipped cap (the ruleset's integrity check
/// refuses otherwise — asserted here as data facts), fixed features are
/// records with namespaced IDs, a caster's slot table reaches the cap, and
/// the level-3 world's cap is exactly 3.
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
