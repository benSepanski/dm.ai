//! Per-kind field comparators. Each returns which fields were mechanically
//! checked and which mismatched — FIELD NAMES ONLY. No Foundry value ever
//! leaves this module; diagnostics name the field, never the ground truth.
//!
//! Encoding bridges (our schema <-> Foundry's), applied as normalization
//! rather than waivers because they are systematic, not per-record:
//! - sizes: "med"/"sm"/"lg" <-> "medium"/"small"/"large"
//! - proficiency ranks: trained/expert/master/legendary <-> 1/2/3/4
//! - prices: {pp,gp,sp,cp} -> copper pieces
//! - bulk: 0.1 -> "L", integers -> decimal strings
//! - traits: lowercased, "ft."/periods stripped, spaces -> dashes
//!   ("thrown 10 ft." <-> "thrown-10")
//! - hands: "held-in-one-hand" -> "1", "held-in-two-hands" -> "2",
//!   "held-in-one-plus-hands" -> "1+"
//!
//! Anything that is a real content difference (e.g. Foundry's systemic
//! `consumable` trait on ammunition) stays a mismatch and needs a reviewed
//! waiver.

use serde_json::Value;

use crate::foundry::FoundryRecord;
use crate::ours::{Kind, OurRecord};

pub struct Outcome {
    pub fields_checked: Vec<&'static str>,
    pub mismatches: Vec<&'static str>,
}

pub fn fields_for_missing(kind: Kind) -> Outcome {
    let _ = kind;
    Outcome {
        fields_checked: vec!["existence", "name"],
        mismatches: vec!["existence"],
    }
}

pub fn compare(our: &OurRecord, foundry: &FoundryRecord) -> Outcome {
    match our.kind {
        Kind::Ancestry => ancestry(&our.value, foundry.system()),
        Kind::Heritage => Outcome {
            // Heritage mechanics are prose in both schemas; existence +
            // name (established by the match itself) is the checkable set.
            fields_checked: vec!["existence", "name"],
            mismatches: vec![],
        },
        Kind::Background => background(&our.value, foundry.system()),
        Kind::Class => class(&our.value, foundry.system()),
        Kind::AncestryFeat => feat(&our.value, foundry.system(), "ancestry", None),
        Kind::ClassFeat => feat(&our.value, foundry.system(), "class", Some("fighter")),
        // A record-level `category` field (once skill feats ship) overrides
        // the file-level default so skill feats compare against Foundry's
        // `skill` category.
        Kind::GeneralFeat => {
            let category = our.value["category"].as_str().unwrap_or("general");
            feat(&our.value, foundry.system(), category, None)
        }
        Kind::Weapon => weapon(&our.value, foundry),
        Kind::Armor => armor(&our.value, foundry.system()),
        Kind::Shield => shield(&our.value, foundry.system()),
        Kind::Gear => gear(&our.value, foundry),
        // Skills and kits have no Foundry counterpart partition; the match
        // loop never gets here for them.
        Kind::Skill | Kind::Kit => unreachable!("no Foundry partition for skills/kits"),
    }
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

fn sorted_lower(items: impl Iterator<Item = String>) -> Vec<String> {
    let mut v: Vec<String> = items.map(|s| s.to_lowercase()).collect();
    v.sort();
    v
}

/// Foundry price {value: {pp,gp,sp,cp}} -> copper. A `per` field (ammo
/// bundles) prices the whole bundle, matching our bundle records.
fn price_cp(price: &Value) -> i64 {
    let v = &price["value"];
    v["pp"].as_i64().unwrap_or(0) * 1000
        + v["gp"].as_i64().unwrap_or(0) * 100
        + v["sp"].as_i64().unwrap_or(0) * 10
        + v["cp"].as_i64().unwrap_or(0)
}

/// Foundry bulk {value: f64} -> our bulk string ("L", "1", "2", "0").
fn bulk_str(bulk: &Value) -> Option<String> {
    let v = bulk.get("value")?.as_f64()?;
    if (v - 0.1).abs() < 1e-9 {
        return Some("L".to_string());
    }
    if v.fract() == 0.0 {
        return Some(format!("{}", v as i64));
    }
    Some(format!("{v}"))
}

fn norm_trait(t: &str) -> String {
    let t = t.to_lowercase().replace("ft.", "").replace('.', "");
    t.split_whitespace().collect::<Vec<_>>().join("-")
}

fn size_name(foundry: &str) -> &str {
    match foundry {
        "med" => "medium",
        "sm" => "small",
        "lg" => "large",
        other => other,
    }
}

fn rank(name: &str) -> i64 {
    match name {
        "untrained" => 0,
        "trained" => 1,
        "expert" => 2,
        "master" => 3,
        "legendary" => 4,
        _ => i64::MIN,
    }
}

/// Foundry boost/flaw slots: single-attribute slots are fixed picks, full
/// six-attribute slots are free boosts; two-attribute slots are choices.
fn boost_slots(slots: &Value) -> (Vec<String>, Vec<Vec<String>>, i64) {
    let mut fixed = Vec::new();
    let mut choices = Vec::new();
    let mut free = 0;
    if let Some(map) = slots.as_object() {
        for slot in map.values() {
            let attrs: Vec<String> = slot["value"]
                .as_array()
                .map(|a| a.iter().map(|v| str_of(v).to_string()).collect())
                .unwrap_or_default();
            match attrs.len() {
                1 => fixed.push(attrs[0].clone()),
                n if n >= 6 => free += 1,
                0 => {}
                _ => choices.push({
                    let mut c = attrs;
                    c.sort();
                    c
                }),
            }
        }
    }
    fixed.sort();
    (fixed, choices, free)
}

fn str_vec(v: &Value) -> Vec<String> {
    v.as_array()
        .map(|a| a.iter().map(|x| str_of(x).to_string()).collect())
        .unwrap_or_default()
}

// ---- comparators --------------------------------------------------------

fn ancestry(our: &Value, s: &Value) -> Outcome {
    let mut mm = Vec::new();
    check(&mut mm, "hp", i64_of(&our["hp"]) == i64_of(&s["hp"]));
    check(
        &mut mm,
        "size",
        str_of(&our["size"]) == size_name(str_of(&s["size"])),
    );
    check(
        &mut mm,
        "speed",
        i64_of(&our["speed"]) == i64_of(&s["speed"]),
    );
    let (fixed, _choices, free) = boost_slots(&s["boosts"]);
    check(
        &mut mm,
        "boosts",
        sorted_lower(str_vec(&our["boosts"]).into_iter()) == fixed
            && i64_of(&our["free_boosts"]) == free,
    );
    let (fixed_flaws, _, _) = boost_slots(&s["flaws"]);
    check(
        &mut mm,
        "flaws",
        sorted_lower(str_vec(&our["flaws"]).into_iter()) == fixed_flaws,
    );
    check(
        &mut mm,
        "languages",
        sorted_lower(str_vec(&our["languages"]).into_iter())
            == sorted_lower(str_vec(&s["languages"]["value"]).into_iter()),
    );
    Outcome {
        fields_checked: vec![
            "existence",
            "name",
            "hp",
            "size",
            "speed",
            "boosts",
            "flaws",
            "languages",
        ],
        mismatches: mm,
    }
}

fn background(our: &Value, s: &Value) -> Outcome {
    let mut mm = Vec::new();
    let (_fixed, choices, _free) = boost_slots(&s["boosts"]);
    let our_choice = sorted_lower(str_vec(&our["boost_choice"]).into_iter());
    check(&mut mm, "boosts", choices.contains(&our_choice));
    let our_skill = str_of(&our["skill"])
        .rsplit('.')
        .next()
        .unwrap_or("")
        .replace('-', " ");
    check(
        &mut mm,
        "skill",
        vec![our_skill] == sorted_lower(str_vec(&s["trainedSkills"]["value"]).into_iter()),
    );
    check(
        &mut mm,
        "lore",
        vec![str_of(&our["lore"]).to_lowercase()]
            == sorted_lower(str_vec(&s["trainedSkills"]["lore"]).into_iter()),
    );
    let granted: Vec<String> = s["items"]
        .as_object()
        .map(|m| {
            m.values()
                .map(|i| str_of(&i["name"]).to_lowercase())
                .collect()
        })
        .unwrap_or_default();
    check(
        &mut mm,
        "skill_feat",
        granted.contains(&str_of(&our["skill_feat"]).to_lowercase()),
    );
    Outcome {
        fields_checked: vec!["existence", "name", "boosts", "skill", "lore", "skill_feat"],
        mismatches: mm,
    }
}

fn class(our: &Value, s: &Value) -> Outcome {
    let mut mm = Vec::new();
    check(
        &mut mm,
        "key_attribute",
        sorted_lower(str_vec(&our["key_attribute_choice"]).into_iter())
            == sorted_lower(str_vec(&s["keyAbility"]["value"]).into_iter()),
    );
    check(
        &mut mm,
        "hp_per_level",
        i64_of(&our["hp_per_level"]) == i64_of(&s["hp"]),
    );
    let p = &our["proficiencies"];
    check(
        &mut mm,
        "perception",
        rank(str_of(&p["perception"])) == i64_of(&s["perception"]),
    );
    let st = &s["savingThrows"];
    check(
        &mut mm,
        "saves",
        rank(str_of(&p["fortitude"])) == i64_of(&st["fortitude"])
            && rank(str_of(&p["reflex"])) == i64_of(&st["reflex"])
            && rank(str_of(&p["will"])) == i64_of(&st["will"]),
    );
    let at = &s["attacks"];
    check(
        &mut mm,
        "attacks",
        rank(str_of(&p["simple_weapons"])) == i64_of(&at["simple"])
            && rank(str_of(&p["martial_weapons"])) == i64_of(&at["martial"])
            && rank(str_of(&p["advanced_weapons"])) == i64_of(&at["advanced"])
            && rank(str_of(&p["unarmed_attacks"])) == i64_of(&at["unarmed"]),
    );
    let df = &s["defenses"];
    let armor_rank = rank(str_of(&p["armor"]));
    check(
        &mut mm,
        "defenses",
        i64_of(&df["light"]) == armor_rank
            && i64_of(&df["medium"]) == armor_rank
            && i64_of(&df["heavy"]) == armor_rank
            && i64_of(&df["unarmored"]) == rank(str_of(&p["unarmored_defense"])),
    );
    // class_dc and the trained-skill choice are not mechanically encoded on
    // Foundry's class record (classDC is null; trainedSkills.value is empty
    // for choice-based classes) — they stay human-verified, so they are
    // deliberately absent from fields_checked.
    Outcome {
        fields_checked: vec![
            "existence",
            "name",
            "key_attribute",
            "hp_per_level",
            "perception",
            "saves",
            "attacks",
            "defenses",
        ],
        mismatches: mm,
    }
}

fn feat(our: &Value, s: &Value, category: &str, required_trait: Option<&str>) -> Outcome {
    let mut mm = Vec::new();
    let mut fields = vec!["existence", "name", "level", "category", "prerequisites"];
    check(
        &mut mm,
        "level",
        i64_of(&our["level"]) == i64_of(&s["level"]["value"]),
    );
    check(&mut mm, "category", str_of(&s["category"]) == category);
    if let Some(t) = required_trait {
        fields.push("traits");
        let traits = str_vec(&s["traits"]["value"]);
        check(&mut mm, "traits", traits.iter().any(|x| x == t));
    }
    // Prerequisite lines are prose in both schemas; the mechanical check is
    // emptiness agreement (a feat we ship as prerequisite-free must be
    // prerequisite-free upstream, and vice versa).
    let ours_empty = our["prerequisites"].as_array().is_none_or(Vec::is_empty);
    let foundry_empty = s["prerequisites"]["value"]
        .as_array()
        .is_none_or(Vec::is_empty);
    check(&mut mm, "prerequisites", ours_empty == foundry_empty);
    if !our["actions"].is_null() && our.get("actions").is_some() {
        fields.push("actions");
        let (our_type, our_count) = parse_actions(str_of(&our["actions"]));
        let f_type = str_of(&s["actionType"]["value"]);
        let f_count = s["actions"]["value"].as_i64();
        check(
            &mut mm,
            "actions",
            our_type == f_type && our_count == f_count,
        );
    }
    Outcome {
        fields_checked: fields,
        mismatches: mm,
    }
}

/// "1 action (press)" -> ("action", Some(1)); "Reaction" -> ("reaction",
/// None); "Free action" -> ("free", None).
fn parse_actions(text: &str) -> (&'static str, Option<i64>) {
    let lower = text.to_lowercase();
    if lower.starts_with("reaction") {
        return ("reaction", None);
    }
    if lower.starts_with("free") {
        return ("free", None);
    }
    let count = lower
        .split_whitespace()
        .next()
        .and_then(|w| w.parse::<i64>().ok());
    match count {
        Some(n) => ("action", Some(n)),
        None => ("passive", None),
    }
}

fn weapon(our: &Value, f: &FoundryRecord) -> Outcome {
    let s = f.system();
    let is_ammo = f.item_type() == "ammo";
    let mut mm = Vec::new();
    let mut fields = vec!["existence", "name", "price", "bulk", "traits"];
    check(
        &mut mm,
        "price",
        i64_of(&our["price_cp"]) == price_cp(&s["price"]),
    );
    check(
        &mut mm,
        "bulk",
        Some(str_of(&our["bulk"]).to_string()) == bulk_str(&s["bulk"]),
    );
    let our_traits = sorted_lower(str_vec(&our["traits"]).iter().map(|t| norm_trait(t)));
    let f_traits = sorted_lower(str_vec(&s["traits"]["value"]).iter().map(|t| norm_trait(t)));
    check(&mut mm, "traits", our_traits == f_traits);
    if !is_ammo {
        fields.extend(["damage", "group", "category", "hands", "range"]);
        let d = &s["damage"];
        let our_damage = str_of(&our["damage"]);
        let mut parts = our_damage.split_whitespace();
        let dice = parts.next().unwrap_or("");
        let dtype = match parts.next().unwrap_or("") {
            "P" => "piercing",
            "S" => "slashing",
            "B" => "bludgeoning",
            other => other,
        };
        check(
            &mut mm,
            "damage",
            dice == format!("{}{}", i64_of(&d["dice"]), str_of(&d["die"]))
                && dtype == str_of(&d["damageType"]),
        );
        check(
            &mut mm,
            "group",
            str_of(&our["group"]).to_lowercase() == str_of(&s["group"]).to_lowercase(),
        );
        check(
            &mut mm,
            "category",
            str_of(&our["category"]) == str_of(&s["category"]),
        );
        let f_hands = match str_of(&s["usage"]["value"]) {
            "held-in-one-hand" => "1",
            "held-in-two-hands" => "2",
            "held-in-one-plus-hands" => "1+",
            other => other,
        };
        check(&mut mm, "hands", str_of(&our["hands"]) == f_hands);
        // Our range strings carry prose ("60 ft. / reload 0", "thrown 10
        // ft."); the mechanical projection is the range-increment number.
        // Thrown increments live in the traits set (thrown-10), already
        // compared above, and Foundry's range is null for melee weapons.
        let our_range = our["range"].as_str().unwrap_or("");
        let our_increment = if our_range.to_lowercase().starts_with("thrown") {
            None
        } else {
            our_range
                .split_whitespace()
                .find_map(|w| w.parse::<i64>().ok())
        };
        check(&mut mm, "range", our_increment == s["range"].as_i64());
    }
    Outcome {
        fields_checked: fields,
        mismatches: mm,
    }
}

fn armor(our: &Value, s: &Value) -> Outcome {
    let mut mm = Vec::new();
    check(
        &mut mm,
        "price",
        i64_of(&our["price_cp"]) == price_cp(&s["price"]),
    );
    check(
        &mut mm,
        "ac_bonus",
        i64_of(&our["ac_bonus"]) == i64_of(&s["acBonus"]),
    );
    check(
        &mut mm,
        "dex_cap",
        i64_of(&our["dex_cap"]) == i64_of(&s["dexCap"]),
    );
    check(
        &mut mm,
        "check_penalty",
        i64_of(&our["check_penalty"]) == i64_of(&s["checkPenalty"]),
    );
    check(
        &mut mm,
        "speed_penalty",
        i64_of(&our["speed_penalty"]) == i64_of(&s["speedPenalty"]),
    );
    check(
        &mut mm,
        "strength",
        i64_of(&our["str_req"]) == i64_of(&s["strength"]),
    );
    check(
        &mut mm,
        "bulk",
        Some(str_of(&our["bulk"]).to_string()) == bulk_str(&s["bulk"]),
    );
    check(
        &mut mm,
        "group",
        str_of(&our["group"]).to_lowercase() == str_of(&s["group"]).to_lowercase(),
    );
    check(
        &mut mm,
        "category",
        str_of(&our["category"]) == str_of(&s["category"]),
    );
    Outcome {
        fields_checked: vec![
            "existence",
            "name",
            "price",
            "ac_bonus",
            "dex_cap",
            "check_penalty",
            "speed_penalty",
            "strength",
            "bulk",
            "group",
            "category",
        ],
        mismatches: mm,
    }
}

fn shield(our: &Value, s: &Value) -> Outcome {
    let mut mm = Vec::new();
    check(
        &mut mm,
        "price",
        i64_of(&our["price_cp"]) == price_cp(&s["price"]),
    );
    check(
        &mut mm,
        "ac_bonus",
        i64_of(&our["ac_bonus"]) == i64_of(&s["acBonus"]),
    );
    check(
        &mut mm,
        "hardness",
        i64_of(&our["hardness"]) == i64_of(&s["hardness"]),
    );
    let f_hp = i64_of(&s["hp"]["max"]);
    check(&mut mm, "hp", i64_of(&our["hp"]) == f_hp);
    // Foundry stores no explicit BT; the rulebook invariant is BT = HP/2.
    check(&mut mm, "bt", i64_of(&our["bt"]) == f_hp / 2);
    check(
        &mut mm,
        "bulk",
        Some(str_of(&our["bulk"]).to_string()) == bulk_str(&s["bulk"]),
    );
    Outcome {
        fields_checked: vec![
            "existence",
            "name",
            "price",
            "ac_bonus",
            "hardness",
            "hp",
            "bt",
            "bulk",
        ],
        mismatches: mm,
    }
}

fn gear(our: &Value, f: &FoundryRecord) -> Outcome {
    let s = f.system();
    let mut mm = Vec::new();
    let mut fields = vec!["existence", "name", "price"];
    check(
        &mut mm,
        "price",
        i64_of(&our["price_cp"]) == price_cp(&s["price"]),
    );
    // Foundry `kit` records (e.g. Adventurer's Pack) carry no bulk of their
    // own — the contents do — so bulk is checkable only on plain equipment.
    if f.item_type() != "kit" {
        fields.push("bulk");
        check(
            &mut mm,
            "bulk",
            Some(str_of(&our["bulk"]).to_string()) == bulk_str(&s["bulk"]),
        );
    }
    Outcome {
        fields_checked: fields,
        mismatches: mm,
    }
}
