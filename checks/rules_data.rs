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
    let root = checks::workspace_root().join("rules-data");
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
    // equipment.json holds categorized arrays.
    let text = std::fs::read_to_string(root.join("equipment.json")).unwrap();
    let equipment: serde_json::Value = serde_json::from_str(&text).unwrap();
    for (key, records) in equipment.as_object().unwrap() {
        for record in records.as_array().unwrap() {
            assert_license(record, &format!("equipment.json/{key}"));
        }
    }
}

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
