//! Enumeration of shipped records — the same file set as
//! `checks/rules_data.rs` RECORD_FILES, read as raw JSON: the attestation
//! hashes the committed record bytes (canonical form), not a typed
//! projection, so an edit to any field — even one no comparator reads —
//! invalidates the attestation.

use std::fs;

use crate::workspace_root;

/// Which comparator applies to a record.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Kind {
    Ancestry,
    Heritage,
    Background,
    Class,
    AncestryFeat,
    ClassFeat,
    GeneralFeat,
    Skill,
    Weapon,
    Armor,
    Shield,
    Gear,
    Kit,
    Spell,
    /// Arcane theses and schools — Foundry class features; existence +
    /// name is the checkable set (mechanics are prose in both schemas).
    ClassFeature,
}

pub struct OurRecord {
    pub id: String,
    pub name: String,
    pub kind: Kind,
    /// Source grouping for reporting: the file name, with an
    /// `equipment.json/<category>` suffix for equipment records.
    pub file: String,
    pub value: serde_json::Value,
}

/// Every record file holding records, with its comparator kind. Keep in
/// lockstep with `checks/rules_data.rs` RECORD_FILES.
const FLAT_FILES: &[(&str, Kind)] = &[
    ("ancestries.json", Kind::Ancestry),
    ("heritages.json", Kind::Heritage),
    ("ancestry-feats.json", Kind::AncestryFeat),
    ("backgrounds.json", Kind::Background),
    ("classes.json", Kind::Class),
    ("class-feats.json", Kind::ClassFeat),
    ("general-feats.json", Kind::GeneralFeat),
    ("skills.json", Kind::Skill),
];

/// equipment.json holds categorized arrays.
const EQUIPMENT_CATEGORIES: &[(&str, Kind)] = &[
    ("weapons", Kind::Weapon),
    ("armor", Kind::Armor),
    ("shields", Kind::Shield),
    ("gear", Kind::Gear),
    ("kits", Kind::Kit),
];

/// spells.json holds categorized arrays too.
const SPELLS_CATEGORIES: &[(&str, Kind)] = &[
    ("spells", Kind::Spell),
    ("theses", Kind::ClassFeature),
    ("schools", Kind::ClassFeature),
];

pub fn load_all() -> Result<Vec<OurRecord>, String> {
    let root = workspace_root().join("rules-data");
    let mut out = Vec::new();
    for (file, kind) in FLAT_FILES {
        let text =
            fs::read_to_string(root.join(file)).map_err(|e| format!("reading {file}: {e}"))?;
        let records: Vec<serde_json::Value> =
            serde_json::from_str(&text).map_err(|e| format!("parsing {file}: {e}"))?;
        for record in records {
            out.push(to_record(record, *kind, file)?);
        }
    }
    let text = fs::read_to_string(root.join("equipment.json"))
        .map_err(|e| format!("reading equipment.json: {e}"))?;
    let equipment: serde_json::Value =
        serde_json::from_str(&text).map_err(|e| format!("parsing equipment.json: {e}"))?;
    let map = equipment
        .as_object()
        .ok_or("equipment.json is not an object")?;
    // Fail on an unknown category rather than silently skipping records —
    // coverage must be exact in both directions.
    for key in map.keys() {
        if !EQUIPMENT_CATEGORIES.iter().any(|(k, _)| k == key) {
            return Err(format!(
                "equipment.json has unknown category '{key}': teach \
                 reference-check (ours.rs + a comparator) about it"
            ));
        }
    }
    for (key, kind) in EQUIPMENT_CATEGORIES {
        let Some(records) = map.get(*key) else {
            continue;
        };
        let records = records
            .as_array()
            .ok_or_else(|| format!("equipment.json/{key} is not an array"))?;
        for record in records {
            out.push(to_record(
                record.clone(),
                *kind,
                &format!("equipment.json/{key}"),
            )?);
        }
    }
    let text =
        fs::read_to_string(root.join("spells.json")).map_err(|e| format!("reading spells.json: {e}"))?;
    let spells: serde_json::Value =
        serde_json::from_str(&text).map_err(|e| format!("parsing spells.json: {e}"))?;
    let map = spells.as_object().ok_or("spells.json is not an object")?;
    for key in map.keys() {
        if !SPELLS_CATEGORIES.iter().any(|(k, _)| k == key) {
            return Err(format!(
                "spells.json has unknown category '{key}': teach \
                 reference-check (ours.rs + a comparator) about it"
            ));
        }
    }
    for (key, kind) in SPELLS_CATEGORIES {
        let Some(records) = map.get(*key) else {
            continue;
        };
        let records = records
            .as_array()
            .ok_or_else(|| format!("spells.json/{key} is not an array"))?;
        for record in records {
            out.push(to_record(
                record.clone(),
                *kind,
                &format!("spells.json/{key}"),
            )?);
        }
    }
    Ok(out)
}

fn to_record(value: serde_json::Value, kind: Kind, file: &str) -> Result<OurRecord, String> {
    let id = value["id"]
        .as_str()
        .ok_or_else(|| format!("{file}: record without an id"))?
        .to_string();
    let name = value["name"]
        .as_str()
        .ok_or_else(|| format!("{file}: record '{id}' without a name"))?
        .to_string();
    Ok(OurRecord {
        id,
        name,
        kind,
        file: file.to_string(),
        value,
    })
}
