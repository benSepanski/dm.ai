//! The 5.5e pass: match each shipped record against the SRD 5.2.1 Markdown
//! mirror (`srd.rs`) by name, run the per-kind comparator, and sweep
//! reverse completeness. FIELD NAMES ONLY leave this module; no SRD value
//! ever reaches a diagnostic or the attestation.
//!
//! What each `fields_checked` entry means, per kind:
//! - every kind: `existence` (a counterpart of that kind exists under the
//!   record's name) and `name` (established by the match itself, except
//!   score methods, which match by kind — see below).
//! - species: `creature_type`; `size` (our size is one the page offers);
//!   `speed`; `darkvision` (range on the Darkvision trait, or none);
//!   `traits` (trait-heading name set, our `choice_trait` counted as one);
//!   `choice_options` (the option name set of a choice trait).
//! - backgrounds: `abilities` (the three-ability set); `feat` (our display
//!   label, or the feat record's name, equals the printed Origin feat);
//!   `skills`; `tool` (the printed tool, "Choose one kind of X" reading as
//!   X); `equipment_items` (item-line count of package A); `equipment_gold`
//!   (package A's coin); `gold_alternative` (option B's coin).
//! - feats: `category` (Origin / Fighting Style / General / Epic Boon).
//! - classes: `primary_abilities`; `hit_die`; `hit_points` (the SRD's
//!   fixed values — level 1 = the die, later levels = half the die + 1 —
//!   against `hp_at_level_1` / `hp_per_level`); `saving_throws`;
//!   `skill_choice` (count and list); `weapon_proficiencies`;
//!   `armor_training`; `features_l1` (level-1 feature names);
//!   `advancement` (per shipped level: feature names and whether the
//!   level is the subclass choice); `weapon_mastery_count` (the Weapon
//!   Mastery column at level 1); `equipment_packages` (per label: item-line
//!   count and coin); `gold_alternative` (label and coin).
//! - subclasses: `class`; `features` ((level, name) set up to the shipped
//!   level cap).
//! - skills: `ability`.
//! - score methods (matched by kind: the array paragraph / the point-cost
//!   paragraph): `name`; `array`; `budget`; `costs` (the score→cost table).
//! - weapons: `category`; `kind` (melee/ranged); `damage` (dice);
//!   `damage_type`; `properties` (name set, range/versatile/ammunition
//!   qualifiers lifted into their own fields); `versatile_damage`;
//!   `range`; `ammunition`; `mastery`; `weight`; `cost`.
//! - armor: `category`; `base_ac`; `add_dex`; `dex_max`; `weight`; `cost`;
//!   and, when the table has the columns (not the Shield table),
//!   `strength_requirement` and `stealth_disadvantage`.
//! - gear: `weight`; `cost`; `amount` when the record name carries a lot
//!   size and the source row has an Amount column ("Arrows (20)").
//! - tools: `weight`; `cost` (a "Varies" tool must be priced as one of its
//!   listed variants).
//!
//! Encoding bridges (systematic, not per-record): coin → copper; "1/4
//! lb." fractions and "—" → pounds; ability names → the shipped three-
//! letter abbreviations; comma-inverted gear names ("Clothes, Traveler's");
//! a record name's parenthetical selects a variant row ("Holy Symbol
//! (Amulet)") or states a lot size ("Arrows (20)"); PDF-split spacing
//! artifacts inside class-table words are bridged by comparing with
//! whitespace removed.

use std::collections::{BTreeMap, BTreeSet};

use serde_json::{json, Value};

use crate::attest::{Config, Matched, Pass};
use crate::compare::{fields_for_missing, Outcome};
use crate::foundry::normalize_name;
use crate::ours::{Kind, OurRecord};
use crate::srd::{self, Srd};

/// Shipped-data-only cross-record context: id → name maps and the class
/// level caps the subclass comparator bounds itself by.
struct Ctx {
    feat_names: BTreeMap<String, String>,
    tool_names: BTreeMap<String, String>,
    skill_names: BTreeMap<String, String>,
    class_names: BTreeMap<String, String>,
    class_caps: BTreeMap<String, i64>,
}

pub fn run(records: &[OurRecord], config: &Config) -> Result<Pass, String> {
    if let Some(id) = config.overrides.keys().next() {
        return Err(format!(
            "override for '{id}': the 5.5e source has no override-map escape hatch (records \
             match by name against page titles and table rows)"
        ));
    }
    let source = srd::load()?;
    let names = |kind: Kind| -> BTreeMap<String, String> {
        records
            .iter()
            .filter(|r| r.kind == kind)
            .map(|r| (r.id.clone(), r.name.clone()))
            .collect()
    };
    let ctx = Ctx {
        feat_names: names(Kind::DndFeat),
        tool_names: names(Kind::DndTool),
        skill_names: names(Kind::DndSkill),
        class_names: names(Kind::DndClass),
        class_caps: records
            .iter()
            .filter(|r| r.kind == Kind::DndClass)
            .map(|r| {
                let cap = r.value["advancement"]
                    .as_array()
                    .map(|a| a.iter().filter_map(|l| l["level"].as_i64()).max())
                    .unwrap_or(None)
                    .unwrap_or(1);
                (r.id.clone(), cap)
            })
            .collect(),
    };

    let mut matched = Vec::with_capacity(records.len());
    // "<category>:<normalized name>" of every counterpart we matched, for
    // the reverse sweep.
    let mut seen: BTreeSet<String> = BTreeSet::new();
    for record in records {
        let (found, outcome) = compare(record, &source, &ctx, &mut seen)?;
        matched.push(Matched { found, outcome });
    }

    Ok(Pass {
        matched,
        missing_from_data: reverse_sweep(&source, &seen, config),
        overrides_used: BTreeSet::new(),
    })
}

fn compare(
    record: &OurRecord,
    source: &Srd,
    ctx: &Ctx,
    seen: &mut BTreeSet<String>,
) -> Result<(bool, Outcome), String> {
    let our = &record.value;
    let key = normalize_name(&record.name);
    let missing = || (false, fields_for_missing(record.kind));
    Ok(match record.kind {
        Kind::DndSpecies => match source.species.get(&key) {
            Some(page) => {
                seen.insert(format!("species:{key}"));
                (true, species(our, page))
            }
            None => missing(),
        },
        Kind::DndBackground => match source.backgrounds.get(&key) {
            Some(entry) => {
                seen.insert(format!("backgrounds:{key}"));
                (true, background(our, entry, ctx))
            }
            None => missing(),
        },
        Kind::DndFeat => match source.feats.get(&key) {
            Some(page) => {
                seen.insert(format!("feats:{key}"));
                (true, feat(our, page))
            }
            None => missing(),
        },
        Kind::DndClass => match source.classes.get(&key) {
            Some(page) => (true, class(our, page, ctx)),
            None => missing(),
        },
        Kind::DndSubclass => match source.subclasses.get(&key) {
            Some(section) => (true, subclass(our, section, ctx)),
            None => missing(),
        },
        Kind::DndSkill => match source.skills.get(&key) {
            Some(ability) => (true, skill(our, ability)),
            None => missing(),
        },
        Kind::DndScoreMethod => {
            let method = match str_of(&our["kind"]) {
                "array" => source.score_array.as_ref(),
                "point-buy" => source.score_points.as_ref(),
                _ => None,
            };
            match method {
                Some(m) => (true, score_method(our, m)),
                None => missing(),
            }
        }
        Kind::DndWeapon => match source.weapons.get(&key) {
            Some(row) => {
                seen.insert(format!("weapons:{key}"));
                (true, weapon(our, row))
            }
            None => missing(),
        },
        Kind::DndArmor => match source.armor.get(&key) {
            Some(row) => {
                seen.insert(format!("armor:{key}"));
                (true, armor(our, row))
            }
            None => missing(),
        },
        Kind::DndGear => match find_gear(&record.name, source) {
            Some((row, lot)) => (true, gear(our, row, lot)),
            None => missing(),
        },
        Kind::DndTool => match source.tool(&key)? {
            Some(page) => (true, tool(our, &page)),
            None => missing(),
        },
        other => unreachable!("{other:?} is not a 5.5e record kind"),
    })
}

/// Gear lookup through the record name's parenthetical: a concrete
/// Adventuring Gear row; else a variant row of a "Varies" base ("Holy
/// Symbol (Amulet)"); else a variant row found under any base by the bare
/// name, whose numeric parenthetical states the lot size ("Arrows (20)").
/// Returns the row and the lot size our name claims, if any.
fn find_gear<'a>(name: &str, source: &'a Srd) -> Option<(&'a srd::GearRow, Option<i64>)> {
    let (base, paren) = srd::split_paren(name);
    let base_key = normalize_name(&base);
    let lot: Option<i64> = paren.as_deref().and_then(|p| p.trim().parse().ok());
    if let Some(row) = source.gear.get(&base_key) {
        if row.weight.is_some() || row.cost.is_some() {
            return Some((row, lot));
        }
        if let Some(variant) = paren
            .as_deref()
            .and_then(|p| source.variants.get(&base_key)?.get(&normalize_name(p)))
        {
            return Some((variant, lot));
        }
    }
    source
        .variants
        .values()
        .find_map(|rows| rows.get(&base_key))
        .map(|row| (row, lot))
}

/// Reverse completeness for the 5.5e slice: the categories the spec names
/// as complete-or-representative, listed by bare published name. Weapons
/// and armor are complete in the slice; species, backgrounds, and the two
/// feat categories are a subset (claims_full_breadth is false for 5.5e, so
/// these are informational).
fn reverse_sweep(
    source: &Srd,
    seen: &BTreeSet<String>,
    config: &Config,
) -> BTreeMap<String, Value> {
    let mut out = BTreeMap::new();
    // `seen_as` is the match-time prefix (feats of both categories are
    // recorded under "feats:"); `category` is the attestation section.
    let mut emit = |category: &str, seen_as: &str, names: Vec<(&String, &str)>| {
        let mut missing: Vec<String> = names
            .into_iter()
            .filter(|(key, _)| !seen.contains(&format!("{seen_as}:{key}")))
            .filter(|(key, _)| {
                !config
                    .spec_exclusions
                    .contains(&(category.to_string(), (*key).clone()))
            })
            .map(|(_, name)| name.to_string())
            .collect();
        missing.sort();
        out.insert(
            category.to_string(),
            json!({ "count": missing.len(), "names": missing }),
        );
    };
    emit(
        "species",
        "species",
        source
            .species
            .iter()
            .map(|(k, p)| (k, p.name.as_str()))
            .collect(),
    );
    emit(
        "backgrounds",
        "backgrounds",
        source
            .backgrounds
            .iter()
            .map(|(k, b)| (k, b.name.as_str()))
            .collect(),
    );
    for (category, wanted) in [
        ("origin_feats", "origin"),
        ("fighting_styles", "fighting-style"),
    ] {
        emit(
            category,
            "feats",
            source
                .feats
                .iter()
                .filter(|(_, f)| f.category == wanted)
                .map(|(k, f)| (k, f.name.as_str()))
                .collect(),
        );
    }
    emit(
        "weapons",
        "weapons",
        source
            .weapons
            .iter()
            .map(|(k, w)| (k, w.name.as_str()))
            .collect(),
    );
    emit(
        "armor",
        "armor",
        source
            .armor
            .iter()
            .map(|(k, a)| (k, a.name.as_str()))
            .collect(),
    );
    out
}

// ---- helpers ------------------------------------------------------------

fn check(mismatches: &mut Vec<&'static str>, field: &'static str, ok: bool) {
    if !ok {
        mismatches.push(field);
    }
}

fn str_of(v: &Value) -> &str {
    v.as_str().unwrap_or("")
}

fn i64_of(v: &Value) -> i64 {
    v.as_i64().unwrap_or(i64::MIN)
}

fn f64_eq(a: Option<f64>, b: &Value) -> bool {
    match (a, b.as_f64()) {
        (Some(a), Some(b)) => (a - b).abs() < 1e-9,
        _ => false,
    }
}

fn str_vec(v: &Value) -> Vec<String> {
    v.as_array()
        .map(|a| a.iter().map(|x| str_of(x).to_string()).collect())
        .unwrap_or_default()
}

fn sorted_norm<I: IntoIterator<Item = S>, S: AsRef<str>>(items: I) -> Vec<String> {
    let mut v: Vec<String> = items
        .into_iter()
        .map(|s| normalize_name(s.as_ref()))
        .collect();
    v.sort();
    v
}

/// Normalized with all whitespace removed — the bridge for the mirror's
/// PDF-split spacing artifacts inside words.
fn squash(s: &str) -> String {
    normalize_name(s).replace(' ', "")
}

fn sorted_squashed<I: IntoIterator<Item = S>, S: AsRef<str>>(items: I) -> Vec<String> {
    let mut v: Vec<String> = items.into_iter().map(|s| squash(s.as_ref())).collect();
    v.sort();
    v
}

fn strip_parens(s: &str) -> String {
    srd::split_paren(s).0
}

/// "Strength or Dexterity" / "Strength and Constitution" → abbreviations.
fn ability_list(text: &str) -> Vec<String> {
    let mut v: Vec<String> = text
        .replace(" or ", ",")
        .replace(" and ", ",")
        .split(',')
        .map(srd::ability_abbr)
        .filter(|a| !a.is_empty())
        .collect();
    v.sort();
    v
}

// ---- comparators --------------------------------------------------------

fn species(our: &Value, page: &srd::SpeciesPage) -> Outcome {
    let mut mm = Vec::new();
    let mut fields = vec![
        "existence",
        "name",
        "creature_type",
        "size",
        "speed",
        "darkvision",
        "traits",
    ];
    check(
        &mut mm,
        "creature_type",
        str_of(&our["creature_type"]).eq_ignore_ascii_case(&page.creature_type),
    );
    check(
        &mut mm,
        "size",
        page.sizes
            .iter()
            .any(|s| s.eq_ignore_ascii_case(str_of(&our["size"]))),
    );
    check(&mut mm, "speed", Some(i64_of(&our["speed"])) == page.speed);
    check(
        &mut mm,
        "darkvision",
        our["darkvision"].as_i64() == page.darkvision,
    );
    let mut our_traits: Vec<String> = our["traits"]
        .as_array()
        .map(|list| {
            list.iter()
                .map(|t| str_of(&t["name"]).to_string())
                .collect()
        })
        .unwrap_or_default();
    if let Some(name) = our["choice_trait"]["name"].as_str() {
        our_traits.push(name.to_string());
    }
    check(
        &mut mm,
        "traits",
        sorted_norm(our_traits) == sorted_norm(&page.traits),
    );
    if let Some(options) = our["choice_trait"]["options"].as_array() {
        fields.push("choice_options");
        let ours = sorted_norm(options.iter().map(|o| str_of(&o["name"])));
        check(
            &mut mm,
            "choice_options",
            ours == sorted_norm(&page.options),
        );
    }
    Outcome {
        fields_checked: fields,
        mismatches: mm,
    }
}

fn background(our: &Value, entry: &srd::BackgroundEntry, ctx: &Ctx) -> Outcome {
    let mut mm = Vec::new();
    let mut ours_abilities = str_vec(&our["abilities"]);
    ours_abilities.sort();
    let mut theirs_abilities = entry.abilities.clone();
    theirs_abilities.sort();
    check(&mut mm, "abilities", ours_abilities == theirs_abilities);

    let our_feat = our["feat_display"]
        .as_str()
        .map(str::to_string)
        .or_else(|| ctx.feat_names.get(str_of(&our["feat"])).cloned());
    check(
        &mut mm,
        "feat",
        our_feat.is_some_and(|f| normalize_name(&f) == normalize_name(&entry.feat)),
    );

    let our_skills: Option<Vec<String>> = str_vec(&our["skills"])
        .iter()
        .map(|id| ctx.skill_names.get(id).cloned())
        .collect();
    check(
        &mut mm,
        "skills",
        our_skills.is_some_and(|s| sorted_norm(s) == sorted_norm(&entry.skills)),
    );

    let their_tool = normalize_name(&entry.tool);
    let their_tool = their_tool
        .strip_prefix("choose one kind of ")
        .unwrap_or(&their_tool)
        .to_string();
    check(
        &mut mm,
        "tool",
        ctx.tool_names
            .get(str_of(&our["tool"]))
            .is_some_and(|t| normalize_name(t) == their_tool),
    );

    let our_items = our["equipment"]["items"]
        .as_array()
        .map(Vec::len)
        .unwrap_or(0);
    check(&mut mm, "equipment_items", our_items == entry.package_items);
    check(
        &mut mm,
        "equipment_gold",
        our["equipment"]["gold"].as_i64() == entry.package_gold,
    );
    check(
        &mut mm,
        "gold_alternative",
        our["gold_alternative"].as_i64() == entry.gold_alternative,
    );
    Outcome {
        fields_checked: vec![
            "existence",
            "name",
            "abilities",
            "feat",
            "skills",
            "tool",
            "equipment_items",
            "equipment_gold",
            "gold_alternative",
        ],
        mismatches: mm,
    }
}

fn feat(our: &Value, page: &srd::FeatPage) -> Outcome {
    let mut mm = Vec::new();
    check(
        &mut mm,
        "category",
        str_of(&our["category"]) == page.category,
    );
    Outcome {
        fields_checked: vec!["existence", "name", "category"],
        mismatches: mm,
    }
}

fn class(our: &Value, page: &srd::ClassPage, ctx: &Ctx) -> Outcome {
    let mut mm = Vec::new();
    let core = |label: &str| -> String {
        page.core
            .iter()
            .find(|(k, _)| squash(k) == squash(label))
            .map(|(_, v)| v.clone())
            .unwrap_or_default()
    };

    let mut ours_primary = str_vec(&our["primary_abilities"]);
    ours_primary.sort();
    check(
        &mut mm,
        "primary_abilities",
        ours_primary == ability_list(&core("Primary Ability")),
    );

    let die = core("Hit Point Die")
        .trim_start_matches(|c: char| !c.eq_ignore_ascii_case(&'d'))
        .trim_start_matches(['D', 'd'])
        .split(|c: char| !c.is_ascii_digit())
        .next()
        .and_then(|n| n.parse::<i64>().ok());
    check(&mut mm, "hit_die", our["hit_die"].as_i64() == die);
    check(
        &mut mm,
        "hit_points",
        die.is_some_and(|d| {
            our["hp_at_level_1"].as_i64() == Some(d)
                && our["hp_per_level"].as_i64() == Some(d / 2 + 1)
        }),
    );

    let mut ours_saves = str_vec(&our["saving_throws"]);
    ours_saves.sort();
    check(
        &mut mm,
        "saving_throws",
        ours_saves == ability_list(&core("Saving Throw Proficiencies")),
    );

    // "Choose 2: Acrobatics, Animal Handling, ..., or Survival"
    let skills_cell = core("Skill Proficiencies");
    let (count, list) = skills_cell.split_once(':').unwrap_or(("", ""));
    let their_count: Option<i64> = count.split_whitespace().find_map(|w| w.parse().ok());
    let their_skills = sorted_squashed(
        list.split(',')
            .map(|s| s.trim().trim_start_matches("or ").trim())
            .filter(|s| !s.is_empty()),
    );
    let our_skills: Option<Vec<String>> = str_vec(&our["skill_choice"]["from"])
        .iter()
        .map(|id| ctx.skill_names.get(id).cloned())
        .collect();
    check(
        &mut mm,
        "skill_choice",
        our["skill_choice"]["count"].as_i64() == their_count
            && our_skills.is_some_and(|s| sorted_squashed(s) == their_skills),
    );

    let vocab = |cell: &str, words: &[&str]| -> Vec<String> {
        let s = squash(cell);
        let mut v: Vec<String> = words
            .iter()
            .filter(|w| s.contains(&squash(w)))
            .map(|w| w.to_string())
            .collect();
        v.sort();
        v
    };
    let mut ours_weapons = str_vec(&our["weapon_proficiencies"]);
    ours_weapons.sort();
    check(
        &mut mm,
        "weapon_proficiencies",
        ours_weapons == vocab(&core("Weapon Proficiencies"), &["simple", "martial"]),
    );
    let mut ours_armor = str_vec(&our["armor_training"]);
    ours_armor.sort();
    check(
        &mut mm,
        "armor_training",
        ours_armor
            == vocab(
                &core("Armor Training"),
                &["light", "medium", "heavy", "shield"],
            ),
    );

    // Features table: level → feature names (parentheticals dropped).
    let mut fields = vec![
        "existence",
        "name",
        "primary_abilities",
        "hit_die",
        "hit_points",
        "saving_throws",
        "skill_choice",
        "weapon_proficiencies",
        "armor_training",
        "features_l1",
        "advancement",
    ];
    let table = page.features.as_ref();
    let features_at = |level: i64| -> Option<Vec<String>> {
        let t = table?;
        let col = t.column("Class Features")?;
        let row = t
            .rows
            .iter()
            .find(|r| r[0].trim().parse::<i64>().ok() == Some(level))?;
        Some(
            row[col]
                .split(',')
                .map(|f| strip_parens(f.trim()))
                .filter(|f| !f.is_empty())
                .collect(),
        )
    };
    let feature_names = |list: &Value| -> Vec<String> {
        list.as_array()
            .map(|a| a.iter().map(|f| str_of(&f["name"]).to_string()).collect())
            .unwrap_or_default()
    };
    check(
        &mut mm,
        "features_l1",
        features_at(1)
            .is_some_and(|f| sorted_norm(f) == sorted_norm(feature_names(&our["features"]))),
    );
    let subclass_marker = squash(&format!("{} Subclass", page.name));
    let advancement_ok = our["advancement"].as_array().is_some_and(|levels| {
        levels.iter().all(|l| {
            let Some(level) = l["level"].as_i64() else {
                return false;
            };
            let Some(theirs) = features_at(level) else {
                return false;
            };
            let their_choice = theirs.iter().any(|f| squash(f) == subclass_marker);
            let their_names: Vec<&String> = theirs
                .iter()
                .filter(|f| squash(f) != subclass_marker)
                .collect();
            l["subclass_choice"].as_bool().unwrap_or(false) == their_choice
                && sorted_norm(their_names) == sorted_norm(feature_names(&l["features"]))
        })
    });
    check(&mut mm, "advancement", advancement_ok);

    if let Some(col) = table.and_then(|t| t.column("Weapon Mastery")) {
        fields.push("weapon_mastery_count");
        let at_l1 = table.and_then(|t| {
            t.rows
                .iter()
                .find(|r| r[0].trim() == "1")
                .and_then(|r| r[col].trim().parse::<i64>().ok())
        });
        check(
            &mut mm,
            "weapon_mastery_count",
            our["weapon_mastery_count"].as_i64() == at_l1,
        );
    }

    fields.extend(["equipment_packages", "gold_alternative"]);
    let packages = srd::parse_choice_packages(&core("Starting Equipment"));
    let their_items: BTreeMap<String, (usize, Option<i64>)> = packages
        .iter()
        .filter(|p| p.items > 0)
        .map(|p| (p.label.to_lowercase(), (p.items, p.gold)))
        .collect();
    let our_packages: BTreeMap<String, (usize, Option<i64>)> = our["equipment_packages"]
        .as_array()
        .map(|a| {
            a.iter()
                .map(|p| {
                    (
                        str_of(&p["label"]).to_lowercase(),
                        (
                            p["items"].as_array().map(Vec::len).unwrap_or(0),
                            p["gold"].as_i64(),
                        ),
                    )
                })
                .collect()
        })
        .unwrap_or_default();
    check(&mut mm, "equipment_packages", our_packages == their_items);
    let their_gold_only = packages.iter().find(|p| p.items == 0);
    check(
        &mut mm,
        "gold_alternative",
        their_gold_only.is_some_and(|p| {
            p.label
                .eq_ignore_ascii_case(str_of(&our["gold_alternative"]["label"]))
                && p.gold == our["gold_alternative"]["gold"].as_i64()
        }),
    );

    Outcome {
        fields_checked: fields,
        mismatches: mm,
    }
}

fn subclass(our: &Value, section: &srd::SubclassSection, ctx: &Ctx) -> Outcome {
    let mut mm = Vec::new();
    let class_id = str_of(&our["class"]);
    check(
        &mut mm,
        "class",
        ctx.class_names
            .get(class_id)
            .is_some_and(|n| normalize_name(n) == normalize_name(&section.class)),
    );
    let cap = ctx.class_caps.get(class_id).copied().unwrap_or(1);
    let mut theirs: Vec<(i64, String)> = section
        .features
        .iter()
        .filter(|(l, _)| *l <= cap)
        .map(|(l, n)| (*l, normalize_name(n)))
        .collect();
    theirs.sort();
    let mut ours: Vec<(i64, String)> = our["features"]
        .as_array()
        .map(|a| {
            a.iter()
                .map(|f| (i64_of(&f["level"]), normalize_name(str_of(&f["name"]))))
                .collect()
        })
        .unwrap_or_default();
    ours.sort();
    check(&mut mm, "features", ours == theirs);
    Outcome {
        fields_checked: vec!["existence", "name", "class", "features"],
        mismatches: mm,
    }
}

fn skill(our: &Value, ability: &str) -> Outcome {
    let mut mm = Vec::new();
    check(&mut mm, "ability", str_of(&our["ability"]) == ability);
    Outcome {
        fields_checked: vec!["existence", "name", "ability"],
        mismatches: mm,
    }
}

fn score_method(our: &Value, method: &srd::ScoreMethod) -> Outcome {
    let mut mm = Vec::new();
    let mut fields = vec!["existence", "name"];
    check(
        &mut mm,
        "name",
        normalize_name(str_of(&our["name"])) == normalize_name(&method.name),
    );
    if str_of(&our["kind"]) == "array" {
        fields.push("array");
        let ours: Vec<i64> = our["array"]
            .as_array()
            .map(|a| a.iter().filter_map(Value::as_i64).collect())
            .unwrap_or_default();
        check(&mut mm, "array", !ours.is_empty() && ours == method.array);
    } else {
        fields.extend(["budget", "costs"]);
        check(&mut mm, "budget", our["budget"].as_i64() == method.budget);
        let ours: BTreeMap<String, i64> = our["costs"]
            .as_object()
            .map(|m| {
                m.iter()
                    .filter_map(|(k, v)| Some((k.clone(), v.as_i64()?)))
                    .collect()
            })
            .unwrap_or_default();
        check(&mut mm, "costs", !ours.is_empty() && ours == method.costs);
    }
    Outcome {
        fields_checked: fields,
        mismatches: mm,
    }
}

fn weapon(our: &Value, row: &srd::WeaponRow) -> Outcome {
    let mut mm = Vec::new();
    check(
        &mut mm,
        "category",
        str_of(&our["category"]) == row.category,
    );
    check(&mut mm, "kind", str_of(&our["kind"]) == row.kind);
    check(
        &mut mm,
        "damage",
        str_of(&our["damage"]).eq_ignore_ascii_case(&row.damage),
    );
    check(
        &mut mm,
        "damage_type",
        str_of(&our["damage_type"]).eq_ignore_ascii_case(&row.damage_type),
    );
    check(
        &mut mm,
        "properties",
        sorted_norm(str_vec(&our["properties"])) == sorted_norm(&row.properties),
    );
    let opt = |v: &Value| v.as_str().map(str::to_lowercase);
    check(
        &mut mm,
        "versatile_damage",
        opt(&our["versatile_damage"]) == row.versatile.as_deref().map(str::to_lowercase),
    );
    check(
        &mut mm,
        "range",
        opt(&our["range"]) == row.range.as_deref().map(str::to_lowercase),
    );
    check(
        &mut mm,
        "ammunition",
        opt(&our["ammunition"]) == row.ammunition.as_deref().map(str::to_lowercase),
    );
    check(
        &mut mm,
        "mastery",
        str_of(&our["mastery"]).eq_ignore_ascii_case(&row.mastery),
    );
    check(&mut mm, "weight", f64_eq(row.weight, &our["weight_lb"]));
    check(&mut mm, "cost", our["cost_cp"].as_i64() == row.cost);
    Outcome {
        fields_checked: vec![
            "existence",
            "name",
            "category",
            "kind",
            "damage",
            "damage_type",
            "properties",
            "versatile_damage",
            "range",
            "ammunition",
            "mastery",
            "weight",
            "cost",
        ],
        mismatches: mm,
    }
}

fn armor(our: &Value, row: &srd::ArmorRow) -> Outcome {
    let mut mm = Vec::new();
    let mut fields = vec![
        "existence",
        "name",
        "category",
        "base_ac",
        "add_dex",
        "dex_max",
        "weight",
        "cost",
    ];
    check(
        &mut mm,
        "category",
        str_of(&our["category"]) == row.category,
    );
    check(
        &mut mm,
        "base_ac",
        our["base_ac"].as_i64() == Some(row.base_ac),
    );
    check(
        &mut mm,
        "add_dex",
        our["add_dex"].as_bool() == Some(row.add_dex),
    );
    check(&mut mm, "dex_max", our["dex_max"].as_i64() == row.dex_max);
    if let Some(strength) = row.strength {
        fields.push("strength_requirement");
        check(
            &mut mm,
            "strength_requirement",
            our["strength_requirement"].as_i64() == strength,
        );
    }
    if let Some(stealth) = row.stealth {
        fields.push("stealth_disadvantage");
        check(
            &mut mm,
            "stealth_disadvantage",
            our["stealth_disadvantage"].as_bool() == Some(stealth),
        );
    }
    check(&mut mm, "weight", f64_eq(row.weight, &our["weight_lb"]));
    check(&mut mm, "cost", our["cost_cp"].as_i64() == row.cost);
    Outcome {
        fields_checked: fields,
        mismatches: mm,
    }
}

fn gear(our: &Value, row: &srd::GearRow, lot: Option<i64>) -> Outcome {
    let mut mm = Vec::new();
    let mut fields = vec!["existence", "name", "weight", "cost"];
    check(&mut mm, "weight", f64_eq(row.weight, &our["weight_lb"]));
    check(&mut mm, "cost", our["cost_cp"].as_i64() == row.cost);
    if lot.is_some() || row.amount.is_some() {
        fields.push("amount");
        check(&mut mm, "amount", lot == row.amount);
    }
    Outcome {
        fields_checked: fields,
        mismatches: mm,
    }
}

fn tool(our: &Value, page: &srd::ToolPage) -> Outcome {
    let mut mm = Vec::new();
    check(&mut mm, "weight", f64_eq(page.weight, &our["weight_lb"]));
    let cost_ok = match page.cost {
        Some(c) => our["cost_cp"].as_i64() == Some(c),
        None => our["cost_cp"]
            .as_i64()
            .is_some_and(|c| page.variant_costs.contains(&c)),
    };
    check(&mut mm, "cost", cost_ok);
    Outcome {
        fields_checked: vec!["existence", "name", "weight", "cost"],
        mismatches: mm,
    }
}
