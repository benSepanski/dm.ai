//! Shared HTTP fixture: build Sylvenne (the golden Arctic Elf Wizard of
//! the School of Battle Magic) through the real server's API — every build
//! decision through /confirm, the preparation through /prep — and
//! optionally finalize her. Include with `#[path = "wizard_fixture.rs"]`.

use serde_json::{json, Value};

#[allow(dead_code)] // each includer uses the slice it needs
pub struct Built {
    pub id: String,
    pub version: u64,
}

#[allow(dead_code)]
pub fn client() -> reqwest::blocking::Client {
    reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .unwrap()
}

fn one(id: &str) -> Value {
    json!({"kind": "option", "value": id})
}

fn many(ids: &[&str]) -> Value {
    json!({"kind": "options", "value": ids})
}

#[allow(dead_code)]
pub fn confirm(
    client: &reqwest::blocking::Client,
    base: &str,
    id: &str,
    version: u64,
    decision_id: &str,
    slot: &str,
    selection: Value,
) -> u64 {
    let outcome: Value = client
        .post(format!("{base}/api/characters/{id}/confirm"))
        .json(&json!({"version": version, "decision": {
            "id": decision_id, "slot": slot, "selection": selection, "source": "player"
        }}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(
        outcome["outcome"], "confirmed",
        "confirm on '{slot}' failed: {outcome:#?}"
    );
    outcome["draft"]["version"].as_u64().unwrap()
}

#[allow(dead_code)]
pub fn sylvenne_prep_choices() -> Value {
    json!([
        {"slot": "pf2e.prep.cantrips", "selection": many(&[
            "spell.shield", "spell.ignition", "spell.electric-arc",
            "spell.detect-magic", "spell.light"])},
        {"slot": "pf2e.prep.rank1", "selection": many(&["spell.fear", "spell.command"])},
        {"slot": "pf2e.prep.school-cantrip", "selection": one("spell.telekinetic-projectile")},
        {"slot": "pf2e.prep.school-rank1", "selection": one("spell.mystic-armor")},
    ])
}

/// Save a prep choice set; returns the raw outcome.
#[allow(dead_code)]
pub fn prep_save(
    client: &reqwest::blocking::Client,
    base: &str,
    id: &str,
    version: u64,
    request_id: &str,
    expected_state: &str,
    choices: &Value,
) -> Value {
    client
        .post(format!("{base}/api/characters/{id}/prep"))
        .json(&json!({
            "request_id": request_id,
            "version": version,
            "expected_state": expected_state,
            "choices": choices,
        }))
        .send()
        .unwrap()
        .json()
        .unwrap()
}

fn char_version(character: &Value) -> u64 {
    // Draft views nest under "projection"-carrying objects; finalized views
    // carry version at top level.
    character["version"].as_u64().unwrap()
}

/// Build Sylvenne as a draft: every build slot confirmed, prep saved.
#[allow(dead_code)]
pub fn build_sylvenne_draft(client: &reqwest::blocking::Client, base: &str) -> Built {
    let draft: Value = client
        .post(format!("{base}/api/characters"))
        .json(&json!({"name": "Sylvenne"}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    let id = draft["id"].as_str().unwrap().to_string();
    let mut v = draft["version"].as_u64().unwrap();
    let mut n = 0u32;
    let mut c = |slot: &str, sel: Value, v: u64| -> u64 {
        n += 1;
        confirm(client, base, &id, v, &format!("syl-{n}"), slot, sel)
    };
    v = c("pf2e.ancestry", one("ancestry.elf"), v);
    v = c("pf2e.ancestry.heritage", one("heritage.elf.arctic"), v);
    v = c(
        "pf2e.ancestry.feat",
        one("feat.ancestry.elf.unwavering-mien"),
        v,
    );
    v = c("pf2e.boosts.ancestry-free", many(&["attr.wis"]), v);
    v = c("pf2e.background", one("background.artisan"), v);
    v = c("pf2e.boosts.background-choice", one("attr.int"), v);
    v = c("pf2e.boosts.background-free", one("attr.cha"), v);
    v = c("pf2e.class", one("class.wizard"), v);
    v = c("pf2e.class.key-attribute", one("attr.int"), v);
    v = c("pf2e.class.thesis", one("thesis.spell-substitution"), v);
    v = c("pf2e.class.school", one("school.battle-magic"), v);
    v = c(
        "pf2e.class.spellbook.cantrips",
        many(&[
            "spell.caustic-blast",
            "spell.detect-magic",
            "spell.electric-arc",
            "spell.figment",
            "spell.frostbite",
            "spell.gouging-claw",
            "spell.ignition",
            "spell.light",
            "spell.message",
            "spell.shield",
        ]),
        v,
    );
    v = c(
        "pf2e.class.spellbook.rank1",
        many(&[
            "spell.command",
            "spell.fear",
            "spell.grease",
            "spell.jump",
            "spell.sleep",
        ]),
        v,
    );
    v = c(
        "pf2e.class.spellbook.curriculum",
        many(&["spell.breathe-fire", "spell.force-barrage"]),
        v,
    );
    v = c("pf2e.skills.class-choice", one("skill.arcana"), v);
    v = c(
        "pf2e.skills.trained",
        many(&[
            "skill.society",
            "skill.occultism",
            "skill.nature",
            "skill.stealth",
            "skill.diplomacy",
            "skill.deception",
        ]),
        v,
    );
    v = c(
        "pf2e.boosts.free",
        many(&["attr.int", "attr.dex", "attr.con", "attr.wis"]),
        v,
    );
    v = c(
        "pf2e.ancestry.languages",
        many(&["lang.draconic", "lang.empyrean", "lang.fey", "lang.gnomish"]),
        v,
    );
    // The create call already seeded the name slot with "Sylvenne".
    v = c("pf2e.equipment.kit", one("kit.wizard"), v);

    let outcome = prep_save(
        client,
        base,
        &id,
        v,
        "syl-initial-prep",
        "draft",
        &sylvenne_prep_choices(),
    );
    assert_eq!(
        outcome["outcome"], "saved",
        "initial prep save failed: {outcome:#?}"
    );
    let v = char_version(&outcome["character"]);
    Built { id, version: v }
}

/// Build and finalize Sylvenne; returns id + post-finalize write version.
#[allow(dead_code)]
pub fn build_sylvenne_finalized(client: &reqwest::blocking::Client, base: &str) -> Built {
    let built = build_sylvenne_draft(client, base);
    let outcome: Value = client
        .post(format!("{base}/api/characters/{}/finalize", built.id))
        .json(&json!({"version": built.version}))
        .send()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(
        outcome["outcome"], "finalized",
        "finalize failed: {outcome:#?}"
    );
    let character: Value = client
        .get(format!("{base}/api/characters/{}", built.id))
        .send()
        .unwrap()
        .json()
        .unwrap();
    Built {
        id: built.id,
        version: character["version"].as_u64().unwrap(),
    }
}
