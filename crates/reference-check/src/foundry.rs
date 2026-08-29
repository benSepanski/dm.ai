//! Loading + indexing the extracted Foundry packs. Records are partitioned
//! by type (the "type partition" of the matching rule) and indexed by
//! normalized name. Publication filtering (title == "Pathfinder Player
//! Core", any remaster-flag variant) happens at match time so a name that
//! collides with a non-Player-Core record reports "wrong publication"
//! rather than silently matching.

use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

use crate::cache;

/// Partitions the matcher searches. Foundry item `type` + feat `category`
/// drive the assignment.
#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Debug)]
pub enum Partition {
    Ancestry,
    Heritage,
    Background,
    Class,
    FeatAncestry,
    FeatClass,
    FeatGeneral,
    FeatSkill,
    Weapon, // includes Foundry `ammo` records
    Armor,
    Shield,
    Gear,  // Foundry `equipment`, `kit`, and `backpack` records
    Spell, // the spells pack (cantrips, ranked spells, focus spells)
    /// The class-features pack (arcane theses and schools match here).
    ClassFeature,
}

pub struct FoundryRecord {
    /// Path relative to `packs/pf2e/` — used in tool diagnostics only,
    /// never written to the attestation.
    pub path: String,
    pub value: serde_json::Value,
}

impl FoundryRecord {
    pub fn system(&self) -> &serde_json::Value {
        &self.value["system"]
    }

    pub fn publication_title(&self) -> &str {
        self.system()["publication"]["title"].as_str().unwrap_or("")
    }

    pub fn is_player_core(&self) -> bool {
        self.publication_title() == "Pathfinder Player Core"
    }

    pub fn rarity(&self) -> &str {
        self.system()["traits"]["rarity"].as_str().unwrap_or("")
    }

    pub fn name(&self) -> &str {
        self.value["name"].as_str().unwrap_or("")
    }

    pub fn item_type(&self) -> &str {
        self.value["type"].as_str().unwrap_or("")
    }
}

pub struct Index {
    by_partition: BTreeMap<Partition, BTreeMap<String, FoundryRecord>>,
}

impl Index {
    pub fn find(&self, partition: Partition, normalized_name: &str) -> Option<&FoundryRecord> {
        self.by_partition.get(&partition)?.get(normalized_name)
    }

    pub fn all(&self, partition: Partition) -> impl Iterator<Item = &FoundryRecord> {
        self.by_partition
            .get(&partition)
            .into_iter()
            .flat_map(BTreeMap::values)
    }

    /// Load a record by pack-relative path — the override-map escape hatch
    /// for names the normalizer cannot bridge.
    pub fn load_by_path(&self, rel_path: &str) -> Result<FoundryRecord, String> {
        let full = cache::packs_root().join(rel_path);
        let value = read_json(&full)?;
        Ok(FoundryRecord {
            path: rel_path.to_string(),
            value,
        })
    }
}

/// Lowercase, strip punctuation (apostrophes, periods, commas, parens,
/// exclamation marks), treat hyphens as spaces, collapse whitespace.
/// "Stonemason's Eye", "Burn It!", and "Lantern (Bull's-Eye)" vs
/// "Lantern (Bull's Eye)" match their Foundry counterparts through this.
pub fn normalize_name(name: &str) -> String {
    let mut out = String::with_capacity(name.len());
    for c in name.to_lowercase().chars() {
        match c {
            '\'' | '\u{2019}' | '.' | '!' | ',' | '(' | ')' => {}
            '-' => out.push(' '),
            c if c.is_whitespace() => out.push(' '),
            c => out.push(c),
        }
    }
    out.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn read_json(path: &Path) -> Result<serde_json::Value, String> {
    let text = fs::read_to_string(path).map_err(|e| format!("reading {}: {e}", path.display()))?;
    serde_json::from_str(&text).map_err(|e| format!("parsing {}: {e}", path.display()))
}

pub fn load_index() -> Result<Index, String> {
    let root = cache::packs_root();
    let mut by_partition: BTreeMap<Partition, BTreeMap<String, FoundryRecord>> = BTreeMap::new();
    let mut insert = |partition: Partition, record: FoundryRecord| {
        by_partition
            .entry(partition)
            .or_default()
            .insert(normalize_name(record.name()), record);
    };

    for (pack, fixed) in [
        ("ancestries", Some(Partition::Ancestry)),
        ("heritages", Some(Partition::Heritage)),
        ("backgrounds", Some(Partition::Background)),
        ("classes", Some(Partition::Class)),
        ("class-features", Some(Partition::ClassFeature)),
        ("spells", None),
        ("feats", None),
        ("equipment", None),
    ] {
        for record in walk_pack(&root, pack)? {
            let partition = match fixed {
                Some(p) => Some(p),
                None if pack == "spells" => match record.item_type() {
                    // Rituals live in the same pack tree but are not
                    // preparation-relevant records; the school/spellbook
                    // subset never references them.
                    "spell" => Some(Partition::Spell),
                    _ => None,
                },
                None if pack == "feats" => {
                    match record.system()["category"].as_str().unwrap_or("") {
                        "ancestry" => Some(Partition::FeatAncestry),
                        "class" => Some(Partition::FeatClass),
                        "general" => Some(Partition::FeatGeneral),
                        "skill" => Some(Partition::FeatSkill),
                        _ => None, // archetype/calling/etc. — out of scope
                    }
                }
                None => match record.item_type() {
                    "weapon" | "ammo" => Some(Partition::Weapon),
                    "armor" => Some(Partition::Armor),
                    "shield" => Some(Partition::Shield),
                    // `consumable` covers book adventuring-gear rows Foundry
                    // types as expendable (candle, chalk, oil, rations).
                    "equipment" | "kit" | "backpack" | "consumable" => Some(Partition::Gear),
                    _ => None, // treasure, containers of no use
                },
            };
            if let Some(partition) = partition {
                insert(partition, record);
            }
        }
    }
    Ok(Index { by_partition })
}

fn walk_pack(root: &Path, pack: &str) -> Result<Vec<FoundryRecord>, String> {
    let mut out = Vec::new();
    let mut stack = vec![root.join(pack)];
    while let Some(dir) = stack.pop() {
        let entries = fs::read_dir(&dir).map_err(|e| format!("reading {}: {e}", dir.display()))?;
        for entry in entries {
            let entry = entry.map_err(|e| format!("dir entry under {pack}: {e}"))?;
            let path = entry.path();
            if path.is_dir() {
                stack.push(path);
            } else if path.extension().is_some_and(|e| e == "json")
                && path.file_name().is_some_and(|n| n != "_folders.json")
            {
                let value = read_json(&path)?;
                let rel = path
                    .strip_prefix(root)
                    .expect("walked path under packs root")
                    .to_string_lossy()
                    .to_string();
                out.push(FoundryRecord { path: rel, value });
            }
        }
    }
    Ok(out)
}
