//! Enumeration of shipped records, per system — the same file set as
//! `checks/rules_data.rs` RECORD_FILES, read as raw JSON: the attestation
//! hashes the committed record bytes (canonical form), not a typed
//! projection, so an edit to any field — even one no comparator reads —
//! invalidates the attestation.

use std::fs;

use crate::{workspace_root, System};

/// Which comparator applies to a record. PF2e kinds route to the Foundry
/// comparator (`compare.rs`); `Dnd*` kinds route to the SRD comparator
/// (`dnd5e.rs`).
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
    DndSpecies,
    DndBackground,
    DndFeat,
    DndClass,
    DndSubclass,
    DndSkill,
    DndScoreMethod,
    DndWeapon,
    DndArmor,
    DndGear,
    DndTool,
}

pub struct OurRecord {
    pub id: String,
    pub name: String,
    pub kind: Kind,
    /// Source grouping for reporting: the file name, with a
    /// `<file>.json/<category>` suffix for categorized files.
    pub file: String,
    pub value: serde_json::Value,
}

/// A record file: either a flat array or an object of categorized arrays
/// (each category with its own kind). Keep in lockstep with
/// `checks/rules_data.rs` RECORD_FILES.
enum Layout {
    Flat(Kind),
    Categorized(&'static [(&'static str, Kind)]),
}

const PF2E_FILES: &[(&str, Layout)] = &[
    ("ancestries.json", Layout::Flat(Kind::Ancestry)),
    ("heritages.json", Layout::Flat(Kind::Heritage)),
    ("ancestry-feats.json", Layout::Flat(Kind::AncestryFeat)),
    ("backgrounds.json", Layout::Flat(Kind::Background)),
    ("classes.json", Layout::Flat(Kind::Class)),
    ("class-feats.json", Layout::Flat(Kind::ClassFeat)),
    ("general-feats.json", Layout::Flat(Kind::GeneralFeat)),
    ("skills.json", Layout::Flat(Kind::Skill)),
    (
        "equipment.json",
        Layout::Categorized(&[
            ("weapons", Kind::Weapon),
            ("armor", Kind::Armor),
            ("shields", Kind::Shield),
            ("gear", Kind::Gear),
            ("kits", Kind::Kit),
        ]),
    ),
    (
        "spells.json",
        Layout::Categorized(&[
            ("spells", Kind::Spell),
            ("theses", Kind::ClassFeature),
            ("schools", Kind::ClassFeature),
        ]),
    ),
];

const DND5E_FILES: &[(&str, Layout)] = &[
    ("species.json", Layout::Flat(Kind::DndSpecies)),
    ("backgrounds.json", Layout::Flat(Kind::DndBackground)),
    ("feats.json", Layout::Flat(Kind::DndFeat)),
    ("classes.json", Layout::Flat(Kind::DndClass)),
    ("subclasses.json", Layout::Flat(Kind::DndSubclass)),
    ("skills.json", Layout::Flat(Kind::DndSkill)),
    (
        "scores.json",
        Layout::Categorized(&[("methods", Kind::DndScoreMethod)]),
    ),
    (
        "equipment.json",
        Layout::Categorized(&[
            ("weapons", Kind::DndWeapon),
            ("armor", Kind::DndArmor),
            ("gear", Kind::DndGear),
            ("tools", Kind::DndTool),
        ]),
    ),
];

pub fn load_all(system: System) -> Result<Vec<OurRecord>, String> {
    let root = workspace_root().join("rules-data").join(system.id());
    let files = match system {
        System::Pf2e => PF2E_FILES,
        System::Dnd5e => DND5E_FILES,
    };
    let mut out = Vec::new();
    for (file, layout) in files {
        let text =
            fs::read_to_string(root.join(file)).map_err(|e| format!("reading {file}: {e}"))?;
        let value: serde_json::Value =
            serde_json::from_str(&text).map_err(|e| format!("parsing {file}: {e}"))?;
        match layout {
            Layout::Flat(kind) => {
                let records = value
                    .as_array()
                    .ok_or_else(|| format!("{file} is not an array"))?;
                for record in records {
                    out.push(to_record(record.clone(), *kind, file)?);
                }
            }
            Layout::Categorized(categories) => {
                let map = value
                    .as_object()
                    .ok_or_else(|| format!("{file} is not an object"))?;
                // Fail on an unknown category rather than silently skipping
                // records — coverage must be exact in both directions.
                for key in map.keys() {
                    if !categories.iter().any(|(k, _)| k == key) {
                        return Err(format!(
                            "{file} has unknown category '{key}': teach \
                             reference-check (ours.rs + a comparator) about it"
                        ));
                    }
                }
                for (key, kind) in *categories {
                    let Some(records) = map.get(*key) else {
                        continue;
                    };
                    let records = records
                        .as_array()
                        .ok_or_else(|| format!("{file}/{key} is not an array"))?;
                    for record in records {
                        out.push(to_record(record.clone(), *kind, &format!("{file}/{key}"))?);
                    }
                }
            }
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
