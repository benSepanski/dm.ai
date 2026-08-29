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

use std::collections::BTreeMap;

use serde_json::Value;

use crate::foundry::FoundryRecord;
use crate::ours::{Kind, OurRecord};

pub struct Outcome {
    pub fields_checked: Vec<&'static str>,
    pub mismatches: Vec<&'static str>,
}

/// Cross-record context the comparators need: background `skill_feat`
/// fields hold shipped feat IDs, so comparing against Foundry's granted
/// feat names requires the shipped id -> name mapping. Our data only —
/// no ground-truth content.
pub struct Ctx {
    pub feat_names: BTreeMap<String, String>,
}

pub fn fields_for_missing(kind: Kind) -> Outcome {
    let _ = kind;
    Outcome {
        fields_checked: vec!["existence", "name"],
        mismatches: vec!["existence"],
    }
}

pub fn compare(our: &OurRecord, foundry: &FoundryRecord, ctx: &Ctx) -> Outcome {
    match our.kind {
        Kind::Ancestry => ancestry(&our.value, foundry.system()),
        Kind::Heritage => Outcome {
            // Heritage mechanics are prose in both schemas; existence +
            // name (established by the match itself) is the checkable set.
            fields_checked: vec!["existence", "name"],
            mismatches: vec![],
        },
        Kind::Background => background(&our.value, foundry.system(), ctx),
        Kind::Class => class(&our.value, foundry.system()),
        Kind::AncestryFeat => feat(&our.value, foundry.system(), "ancestry", None),
        Kind::ClassFeat => feat(&our.value, foundry.system(), "class", Some("fighter")),
        // Skill feats ship inside general-feats.json under the T2 ID
        // convention `feat.skill.<slug>`; they compare against Foundry's
        // `skill` category.
        Kind::GeneralFeat => {
            let category = if our.id.starts_with("feat.skill.") {
                "skill"
            } else {
                "general"
            };
            feat(&our.value, foundry.system(), category, None)
        }
        Kind::Weapon => weapon(&our.value, foundry),
        Kind::Armor => armor(&our.value, foundry.system()),
        Kind::Shield => shield(&our.value, foundry.system()),
        Kind::Gear => gear(&our.value, foundry),
        Kind::Spell => spell(&our.value, foundry),
        Kind::ClassFeature => Outcome {
            // Thesis and school mechanics are prose in both schemas;
            // existence + name (established by the match itself) is the
            // checkable set. Curriculum lists are review-verified.
            fields_checked: vec!["existence", "name"],
            mismatches: vec![],
        },
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

/// Foundry bulk {value: f64} -> our bulk string ("L", "1", "2", "—").
/// Foundry's 0 is the book's "—" (negligible) — the table has no "0" row.
fn bulk_str(bulk: &Value) -> Option<String> {
    let v = bulk.get("value")?.as_f64()?;
    if v == 0.0 {
        return Some("—".to_string());
    }
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
    // Dice-notation bridge: the book prints "Two-Hand 1d8" / "Fatal 1d12";
    // Foundry drops the die count ("two-hand-d8"). Normalize "1dN" -> "dN".
    let tokens: Vec<String> = t
        .split_whitespace()
        .map(|w| match w.strip_prefix("1d") {
            Some(rest) if !rest.is_empty() && rest.chars().all(|c| c.is_ascii_digit()) => {
                format!("d{rest}")
            }
            _ => w.to_string(),
        })
        .collect();
    tokens.join("-")
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

fn background(our: &Value, s: &Value, ctx: &Ctx) -> Outcome {
    let mut mm = Vec::new();
    let (_fixed, choices, _free) = boost_slots(&s["boosts"]);
    let our_choice = sorted_lower(str_vec(&our["boost_choice"]).into_iter());
    check(&mut mm, "boosts", choices.contains(&our_choice));
    // Sub-choice encoding bridge: a background with `skill_choice` ships
    // `skill: ""`, and Foundry encodes choice-based training as an empty
    // trainedSkills list (the choice lives in prose/rule elements there),
    // so the checkable projection is emptiness agreement. Same for a
    // player-named Lore (`lore: ""` + `lore_player_named`).
    let foundry_skills = sorted_lower(str_vec(&s["trainedSkills"]["value"]).into_iter());
    let our_skill = str_of(&our["skill"]);
    let skill_ok = if our_skill.is_empty() && !str_vec(&our["skill_choice"]).is_empty() {
        foundry_skills.is_empty()
    } else {
        vec![our_skill.rsplit('.').next().unwrap_or("").replace('-', " ")] == foundry_skills
    };
    check(&mut mm, "skill", skill_ok);
    let foundry_lore = sorted_lower(str_vec(&s["trainedSkills"]["lore"]).into_iter());
    let our_lore = str_of(&our["lore"]);
    let lore_ok = if our_lore.is_empty() && our["lore_player_named"].as_bool() == Some(true) {
        foundry_lore.is_empty()
    } else {
        vec![our_lore.to_lowercase()] == foundry_lore
    };
    check(&mut mm, "lore", lore_ok);
    let granted: Vec<String> = s["items"]
        .as_object()
        .map(|m| {
            m.values()
                .map(|i| str_of(&i["name"]).to_lowercase())
                .collect()
        })
        .unwrap_or_default();
    // `skill_feat` holds a shipped feat ID; resolve it to the record's name
    // for the membership test. Choice-dependent grants
    // (`skill_feat_by_choice`, skill_feat "") and parameterized grants
    // (`skill_feat_display`, e.g. "Assurance (Survival)") are not encoded
    // as granted items by Foundry, so those accept an empty grant list —
    // but a listed grant must still resolve to our feat's name.
    let our_feat_id = str_of(&our["skill_feat"]);
    let feat_ok = if our_feat_id.is_empty() {
        granted.is_empty()
    } else {
        let resolved = ctx.feat_names.get(our_feat_id).map(|n| n.to_lowercase());
        match resolved {
            Some(name) => {
                granted.contains(&name)
                    || (our.get("skill_feat_display").is_some() && granted.is_empty())
            }
            None => false, // an unresolvable feat ID is always a mismatch
        }
    };
    check(&mut mm, "skill_feat", feat_ok);
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
        // Melee weapons with the incremented Thrown trait ("thrown 10 ft.")
        // carry the increment in the traits set (thrown-10), already
        // compared above, and Foundry's range is null for them. Ranged
        // thrown weapons (dart, javelin, bola) carry the plain "thrown"
        // trait and the increment in Foundry's range field.
        let our_range = our["range"].as_str().unwrap_or("");
        let thrown_in_traits = our_traits
            .iter()
            .any(|t| t.strip_prefix("thrown-").is_some_and(|r| !r.is_empty()));
        let our_increment = if our_range.to_lowercase().starts_with("thrown") && thrown_in_traits {
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
    // The book's "—" Strength entry (no requirement) ships as `str_req: 0`
    // in our schema; Foundry encodes it as null.
    check(
        &mut mm,
        "strength",
        i64_of(&our["str_req"]) == s["strength"].as_i64().unwrap_or(0),
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

/// Spells: rank (with the cantrip rule), traditions, traits, action cost,
/// defense, range, area, targets, duration, and — where Foundry structures
/// it — the heightening shape. Normalization bridges (systematic, not
/// per-record):
/// - our rank 0 = Foundry level 1 + `cantrip` trait; ranked spells match
///   the level with no cantrip trait
/// - `focus` is a directory in Foundry (`spells/focus/`), a flag here (the
///   Focus trait itself appears in both schemas and is compared)
/// - rarity (Uncommon/Rare) is a printed trait but a separate `rarity`
///   field in Foundry — dropped from our side of the trait comparison
/// - focus spells carry no tradition list in Foundry — skipped for them
/// - our "AC" defense = printed Defense line of attack spells; Foundry
///   models those as no defense + the `attack` trait
/// - area {type, value} renders as "<value>-foot <type>"
/// - a sustained duration with no printed time renders as "sustained"
fn spell(our: &Value, f: &FoundryRecord) -> Outcome {
    let s = f.system();
    let mut fields = vec![
        "existence",
        "name",
        "rank",
        "traits",
        "actions",
        "defense",
        "range",
        "targets",
        "duration",
    ];
    let mut mm = Vec::new();

    let foundry_traits: Vec<String> = s["traits"]["value"]
        .as_array()
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str())
                .map(str::to_lowercase)
                .collect()
        })
        .unwrap_or_default();
    let is_cantrip_f = foundry_traits.iter().any(|t| t == "cantrip");
    let is_focus_f = f.path.contains("/focus/");
    let our_rank = i64_of(&our["rank"]);
    let our_focus = our["focus"].as_bool().unwrap_or(false);
    let f_level = s["level"]["value"].as_i64().unwrap_or(-1);
    let rank_ok = if our_rank == 0 {
        is_cantrip_f && f_level == 1
    } else {
        !is_cantrip_f && f_level == our_rank
    };
    check(&mut mm, "rank", rank_ok && our_focus == is_focus_f);

    if !our_focus {
        fields.push("traditions");
        let ours = sorted_lower(
            our["traditions"]
                .as_array()
                .unwrap_or(&vec![])
                .iter()
                .filter_map(|v| v.as_str())
                .map(String::from),
        );
        let theirs = sorted_lower(
            s["traits"]["traditions"]
                .as_array()
                .unwrap_or(&vec![])
                .iter()
                .filter_map(|v| v.as_str())
                .map(String::from),
        );
        check(&mut mm, "traditions", ours == theirs);
    }

    let ours_traits = sorted_lower(
        our["traits"]
            .as_array()
            .unwrap_or(&vec![])
            .iter()
            .filter_map(|v| v.as_str())
            .filter(|t| !t.eq_ignore_ascii_case("uncommon") && !t.eq_ignore_ascii_case("rare"))
            .map(String::from),
    );
    let mut theirs_traits = foundry_traits.clone();
    theirs_traits.sort();
    check(&mut mm, "traits", ours_traits == theirs_traits);

    check(
        &mut mm,
        "actions",
        str_of(&our["actions"]) == s["time"]["value"].as_str().unwrap_or(""),
    );

    let our_defense = our["defense"].as_str();
    let defense_ok = match &s["defense"]["save"] {
        Value::Object(save) => {
            let stat = save["statistic"].as_str().unwrap_or("");
            let basic = save["basic"].as_bool().unwrap_or(false);
            let expected = if basic {
                format!("basic {}", capitalize_ascii(stat))
            } else {
                capitalize_ascii(stat)
            };
            our_defense == Some(expected.as_str())
        }
        _ => {
            // No save in Foundry: an attack spell's printed Defense is AC.
            if foundry_traits.iter().any(|t| t == "attack") {
                our_defense == Some("AC")
            } else {
                our_defense.is_none()
            }
        }
    };
    check(&mut mm, "defense", defense_ok);

    let f_range = s["range"]["value"].as_str().unwrap_or("");
    check(
        &mut mm,
        "range",
        our["range"].as_str().unwrap_or("") == f_range,
    );

    // Area is checkable only when Foundry structures it (Grease models its
    // dual area/target in prose).
    if let (Some(t), Some(v)) = (s["area"]["type"].as_str(), s["area"]["value"].as_i64()) {
        fields.push("area");
        let expected = format!("{v}-foot {t}");
        check(
            &mut mm,
            "area",
            our["area"].as_str() == Some(expected.as_str()),
        );
    }

    let f_targets = s["target"]["value"].as_str().unwrap_or("");
    check(
        &mut mm,
        "targets",
        our["targets"].as_str().unwrap_or("") == f_targets,
    );

    let f_duration = s["duration"]["value"].as_str().unwrap_or("");
    let sustained = s["duration"]["sustained"].as_bool().unwrap_or(false);
    let expected_duration = if f_duration.is_empty() && sustained {
        "sustained".to_string()
    } else {
        f_duration.to_string()
    };
    check(
        &mut mm,
        "duration",
        our["duration"].as_str().unwrap_or("") == expected_duration,
    );

    // Heightening shape, when Foundry structures it. Interval entries must
    // have a matching per_rank step; fixed entries must cover Foundry's
    // structured levels (we may carry MORE printed entries than Foundry
    // structures — those are review-verified).
    match s["heightening"]["type"].as_str() {
        Some("interval") => {
            fields.push("heightening");
            let interval = s["heightening"]["interval"].as_i64().unwrap_or(1);
            let ok = our["heightening"].as_array().is_some_and(|entries| {
                entries.iter().any(|e| {
                    e["kind"].as_str() == Some("per_rank") && e["step"].as_i64() == Some(interval)
                })
            });
            check(&mut mm, "heightening", ok);
        }
        Some("fixed") => {
            fields.push("heightening");
            let levels: Vec<i64> = s["heightening"]["levels"]
                .as_object()
                .map(|m| m.keys().filter_map(|k| k.parse().ok()).collect())
                .unwrap_or_default();
            let ours: Vec<i64> = our["heightening"]
                .as_array()
                .map(|a| {
                    a.iter()
                        .filter(|e| e["kind"].as_str() == Some("fixed"))
                        .filter_map(|e| e["rank"].as_i64())
                        .collect()
                })
                .unwrap_or_default();
            let ok = levels.iter().all(|l| ours.contains(l));
            check(&mut mm, "heightening", ok);
        }
        _ => {}
    }

    Outcome {
        fields_checked: fields,
        mismatches: mm,
    }
}

fn capitalize_ascii(s: &str) -> String {
    let mut out = s.to_string();
    if let Some(first) = out.get_mut(0..1) {
        first.make_ascii_uppercase();
    }
    out
}
