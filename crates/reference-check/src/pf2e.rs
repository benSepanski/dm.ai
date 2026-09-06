//! The PF2e pass: route each shipped record to its Foundry partition, find
//! the Player Core counterpart (or the override-map target), run the
//! Foundry comparator, and sweep reverse completeness over the packs.

use std::collections::{BTreeMap, BTreeSet};

use serde_json::{json, Value};

use crate::attest::{Config, Matched, Pass};
use crate::foundry::{normalize_name, FoundryRecord, Index, Partition};
use crate::ours::{Kind, OurRecord};
use crate::{compare, foundry};

fn partition_for(record: &OurRecord) -> Option<Partition> {
    // Skill feats ship inside general-feats.json under the T2 ID convention
    // `feat.skill.<slug>` (non-skill general feats keep `feat.general.*`);
    // the prefix routes the lookup to the skill-feat partition.
    if record.kind == Kind::GeneralFeat && record.id.starts_with("feat.skill.") {
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
        Kind::Spell => Some(Partition::Spell),
        Kind::ClassFeature => Some(Partition::ClassFeature),
        // No Foundry pack exists for these: PF2e core skills are fixed game
        // vocabulary (not compendium records) and class kits ship only in
        // the book. They are attestable solely via reviewed waivers.
        Kind::Skill | Kind::Kit => None,
        other => unreachable!("{other:?} is not a PF2e record kind"),
    }
}

pub fn run(records: &[OurRecord], config: &Config) -> Result<Pass, String> {
    let index = foundry::load_index()?;

    // Background `skill_feat` fields hold shipped feat IDs; the comparator
    // resolves them to record names through this shipped-data-only map.
    let ctx = compare::Ctx {
        feat_names: records
            .iter()
            .filter(|r| r.kind == Kind::GeneralFeat)
            .map(|r| (r.id.clone(), r.name.clone()))
            .collect(),
    };

    let mut matched = Vec::with_capacity(records.len());
    let mut overrides_used: BTreeSet<String> = BTreeSet::new();
    let mut matched_paths: BTreeSet<String> = BTreeSet::new();

    for record in records {
        let counterpart = find_counterpart(record, &index, config, &mut overrides_used)?;
        let outcome = match &counterpart {
            Some(f) => compare::compare(record, f, &ctx),
            None => compare::fields_for_missing(record.kind),
        };
        if let Some(f) = &counterpart {
            matched_paths.insert(f.path.clone());
        }
        matched.push(Matched {
            found: counterpart.is_some(),
            outcome,
        });
    }

    Ok(Pass {
        matched,
        missing_from_data: reverse_sweep(&index, &matched_paths, config),
        overrides_used,
    })
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
