//! Replay determinism: fold(log) equals the stored sheet for all fixture
//! characters, and the golden sheets are hand-verified against Player Core
//! (page references inline). Plus property tests: random wizard sessions
//! never break projection invariants.

use engine_core::AppendOutcome;
use types::{Decision, DecisionId, DecisionInput, DecisionSource, OptionId, Selection, SlotId};

fn engine() -> ruleset_pf2e::Pf2eEngine {
    ruleset_pf2e::engine(std::sync::Arc::new(checks::load_rules_data()))
}

fn confirm(
    engine: &ruleset_pf2e::Pf2eEngine,
    log: &mut Vec<Decision>,
    n: &mut u32,
    slot: &str,
    selection: Selection,
) {
    *n += 1;
    let input = DecisionInput {
        id: DecisionId::new(format!("golden-{n}")),
        slot: SlotId::new(slot),
        selection,
        source: DecisionSource::Player,
    };
    match engine.append(log, input) {
        Ok(AppendOutcome::Appended(new_log)) => *log = new_log,
        other => panic!("golden confirm on '{slot}' rejected: {other:?}"),
    }
}

fn one(id: &str) -> Selection {
    Selection::Option(OptionId::new(id))
}
fn many(ids: &[&str]) -> Selection {
    Selection::Options(ids.iter().map(|i| OptionId::new(*i)).collect())
}

/// Torvald, the spec's first-run Dwarf Fighter. Values hand-verified against
/// Pathfinder Player Core: proficiency pg. 11, boosts pg. 17-19, Dwarf
/// pg. 42-44, Warrior pg. 88, Fighter pg. 136-141, armor pg. 273,
/// weapons pg. 277-280, kit pg. 268, Bulk pg. 269-271.
fn torvald_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(engine, &mut log, n, "pf2e.ancestry", one("ancestry.dwarf"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.dwarf.rock"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.dwarf.rock-runner"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.str"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.warrior"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.str"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.con"),
    );
    confirm(engine, &mut log, n, "pf2e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.str"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.feat",
        one("feat.class.fighter.sudden-charge"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.athletics"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&["skill.survival", "skill.religion", "skill.crafting"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.str", "attr.dex", "attr.con", "attr.wis"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.kit",
        one("kit.fighter.sword-and-board"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Torvald".into()),
    );
    log
}

/// Elyse, a Human archer exercising Skilled Human's chooser and the
/// armor check/speed penalty for an unmet Strength requirement.
fn elyse_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(engine, &mut log, n, "pf2e.ancestry", one("ancestry.human"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.human.skilled"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.heritage-choice",
        one("skill.medicine"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.human.cooperative-nature"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.dex", "attr.wis"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.hunter"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.dex"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.str"),
    );
    confirm(engine, &mut log, n, "pf2e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.dex"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.feat",
        one("feat.class.fighter.point-blank-stance"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.acrobatics"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&[
            "skill.stealth",
            "skill.athletics",
            "skill.society",
            "skill.thievery",
        ]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.dex", "attr.con", "attr.wis", "attr.int"]),
    );
    // Int +1 grants one bonus language from the human list (chargen-content:
    // the language chooser opened once ancestries carried additional
    // languages; hand-verified addition to the golden).
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.languages",
        many(&["lang.elven"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.kit",
        one("kit.fighter.longbow"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Elyse".into()),
    );
    log
}

/// Krivvy, an Unbreakable Goblin street urchin, built out of order so the
/// background's Thievery grant collides with an existing skill pick and
/// forces the replacement rule.
fn krivvy_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(engine, &mut log, n, "pf2e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.dex"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.acrobatics"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&["skill.thievery", "skill.stealth", "skill.deception"]),
    );
    confirm(engine, &mut log, n, "pf2e.ancestry", one("ancestry.goblin"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.goblin.unbreakable"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.goblin.goblin-song"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.con"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.street-urchin"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.con"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.str"),
    );
    // The background granted Thievery, already trained above: replacement.
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.replacement-1",
        one("skill.society"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.feat",
        one("feat.class.fighter.exacting-strike"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.dex", "attr.con", "attr.str", "attr.cha"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.kit",
        one("equipment.no-kit"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.extra",
        many(&[
            "armor.leather",
            "weapon.shortsword",
            "weapon.sling",
            "weapon.sling-bullets",
            "gear.adventurers-pack",
        ]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Krivvy".into()),
    );
    log
}

/// Caelith, a Whisper Elf Scholar exercising the background skill
/// sub-choice (Scholar trains a chosen skill, and the skill feat follows
/// the choice), Nimble Elf's speed bonus, and the Int-driven language
/// chooser (Int +2 buys two extra trained skills and two languages).
/// Values hand-verified against Pathfinder Player Core: Elf pg. 46-48,
/// Scholar pg. 88, greatsword pg. 280, scale mail pg. 273.
fn caelith_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(engine, &mut log, n, "pf2e.ancestry", one("ancestry.elf"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.elf.whisper"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.elf.nimble-elf"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.str"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.scholar"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background.skill",
        one("skill.occultism"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.int"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.str"),
    );
    confirm(engine, &mut log, n, "pf2e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.str"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.feat",
        one("feat.class.fighter.vicious-swing"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.athletics"),
    );
    // 3 + Int 2 = 5 trained picks (elf Int boost + Scholar's Int boost).
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&[
            "skill.survival",
            "skill.arcana",
            "skill.crafting",
            "skill.medicine",
            "skill.religion",
        ]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.str", "attr.dex", "attr.con", "attr.wis"]),
    );
    // Int +2 grants two bonus languages from the elf list.
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.languages",
        many(&["lang.draconic", "lang.fey"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.kit",
        one("kit.fighter.greatsword"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Caelith".into()),
    );
    log
}

/// Fizzwick, a Sensate Gnome barkeep exercising Gnome Obsession's
/// player-named Lore (the feat-lore text slot) and a Dex build whose
/// Strength -1 fails the studded leather requirement (armor check penalty)
/// and lands negative Strength on damage. Player Core: Gnome pg. 50-52,
/// Barkeep pg. 84, studded leather pg. 273, rapier pg. 278.
fn fizzwick_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(engine, &mut log, n, "pf2e.ancestry", one("ancestry.gnome"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.gnome.sensate"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.gnome.gnome-obsession"),
    );
    // Gnome Obsession's ChooseLore opens the feat-lore text slot.
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.feat-lore",
        Selection::Text("Clockwork".into()),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.dex"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.barkeep"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.con"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.dex"),
    );
    confirm(engine, &mut log, n, "pf2e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.dex"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.feat",
        one("feat.class.fighter.combat-assessment"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.acrobatics"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&["skill.stealth", "skill.thievery", "skill.deception"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.dex", "attr.con", "attr.wis", "attr.cha"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.kit",
        one("equipment.no-kit"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.extra",
        many(&[
            "armor.studded-leather",
            "weapon.rapier",
            "weapon.dagger",
            "gear.adventurers-pack",
            "gear.mug",
        ]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Fizzwick".into()),
    );
    log
}

/// Wenna, a Nomadic Halfling nomad exercising the heritage's two bonus
/// languages at Int +0 (the chooser opens on the bonus-language effect
/// alone) and the Nomad background's player-named Lore, slinging with
/// negative Strength through propulsive. Player Core: Halfling pg. 58-60,
/// Nomad pg. 88, sling pg. 279, leather armor pg. 273.
fn wenna_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry",
        one("ancestry.halfling"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.halfling.nomadic"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.halfling.titan-slinger"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.con"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.nomad"),
    );
    // Nomad's Lore is player-named.
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background.lore",
        Selection::Text("Steppe".into()),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.wis"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.dex"),
    );
    confirm(engine, &mut log, n, "pf2e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.dex"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.feat",
        one("feat.class.fighter.snagging-strike"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.acrobatics"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&["skill.stealth", "skill.nature", "skill.medicine"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.dex", "attr.con", "attr.wis", "attr.cha"]),
    );
    // Int +0: both picks come from Nomadic Halfling's bonus languages.
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.languages",
        many(&["lang.dwarven", "lang.goblin"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.kit",
        one("equipment.no-kit"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.extra",
        many(&[
            "armor.leather",
            "weapon.sling",
            "weapon.sling-bullets",
            "weapon.dagger",
            "gear.adventurers-pack",
            "gear.bedroll",
        ]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Wenna".into()),
    );
    log
}

/// Bramble, a Root Leshy field medic exercising the ancestry-HP override
/// (10 instead of 8), Seedpod's ranged unarmed attack, and Int -1
/// shrinking the trained-skill count to 2. Player Core: Leshy pg. 66-68,
/// Field Medic pg. 86, hatchet/light hammer pg. 278.
fn bramble_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(engine, &mut log, n, "pf2e.ancestry", one("ancestry.leshy"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.leshy.root"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.leshy.seedpod"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.str"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.field-medic"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.con"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.str"),
    );
    confirm(engine, &mut log, n, "pf2e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.str"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.feat",
        one("feat.class.fighter.double-slice"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.athletics"),
    );
    // 3 + Int (-1) = 2 trained picks.
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&["skill.nature", "skill.stealth"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.str", "attr.dex", "attr.con", "attr.wis"]),
    );
    // Base kit (no option) plus a purchased twin-weapon set.
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.kit",
        one("kit.fighter"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.extra",
        many(&["weapon.hatchet", "weapon.light-hammer"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Bramble".into()),
    );
    log
}

/// Grashk, a Hold-Scarred Orc miner exercising the 12-HP ancestry
/// override and Iron Fists' replaces-fist unarmed attack, in hide armor
/// whose Strength requirement is met (check/speed penalties waived).
/// Player Core: Orc pg. 70-72, Miner pg. 87, hide armor pg. 273,
/// warhammer pg. 278.
fn grashk_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(engine, &mut log, n, "pf2e.ancestry", one("ancestry.orc"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.orc.hold-scarred"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.orc.iron-fists"),
    );
    // Orc has no fixed boosts: two free ancestry boosts.
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.str", "attr.con"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.miner"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.str"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.con"),
    );
    confirm(engine, &mut log, n, "pf2e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.str"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.feat",
        one("feat.class.fighter.reactive-shield"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.athletics"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&["skill.intimidation", "skill.nature", "skill.religion"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.str", "attr.dex", "attr.con", "attr.wis"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.kit",
        one("equipment.no-kit"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.extra",
        many(&[
            "armor.hide",
            "weapon.warhammer",
            "shield.steel",
            "weapon.javelin",
            "gear.adventurers-pack",
            "gear.torch",
        ]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Grashk".into()),
    );
    log
}

/// Maera, a Dwarf with the Aiuvarin versatile heritage taking an aiuvarin
/// feat (Earned Glory) through the feat-catalog union, stacking the
/// heritage's low-light vision next to dwarven darkvision. Player Core:
/// Dwarf pg. 42-44, Aiuvarin pg. 82, Bounty Hunter pg. 85.
fn maera_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(engine, &mut log, n, "pf2e.ancestry", one("ancestry.dwarf"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.versatile.aiuvarin"),
    );
    // An aiuvarin-keyed feat, legal only through the union rule.
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.aiuvarin.earned-glory"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.str"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.bounty-hunter"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.str"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.con"),
    );
    confirm(engine, &mut log, n, "pf2e.class", one("class.fighter"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.str"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.feat",
        one("feat.class.fighter.sudden-charge"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.athletics"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&["skill.medicine", "skill.society", "skill.intimidation"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.str", "attr.dex", "attr.con", "attr.wis"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.kit",
        one("kit.fighter.sword-and-board"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.equipment.extra",
        many(&["weapon.javelin", "gear.rope"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Maera".into()),
    );
    log
}

/// Garrek Ironvale, the shipped fighter suggested build, expanded on an
/// empty log through the engine's own planner. This pins the
/// dm.ai-authored suggested_build block: any change to its candidates
/// shows up as a golden/fixture diff.
fn garrek_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let data = checks::load_rules_data();
    let builds = ruleset_pf2e::suggested_builds(&data);
    let (_, map) = builds
        .into_iter()
        .find(|(id, _)| id == "class.fighter")
        .expect("class.fighter ships a suggested build");
    let plan = engine
        .expand_suggestions(
            &[],
            &|slot| map.get(slot).cloned(),
            &|slot| DecisionId::new(format!("qb.{slot}")),
            types::DecisionSource::Suggested,
        )
        .expect("the shipped suggested build expands on an empty log");
    assert!(
        plan.unresolved.is_empty(),
        "the shipped suggested build left slots unresolved: {:#?}",
        plan.unresolved
    );
    plan.log
}

fn assert_entry(sheet: &types::SheetView, section: &str, label: &str, value: &str) {
    let entry = sheet
        .entry(section, label)
        .unwrap_or_else(|| panic!("sheet is missing {section} / {label}"));
    assert_eq!(
        entry.value, value,
        "{section} / {label}: got '{}' (detail: {:?}), hand calculation says '{value}'",
        entry.value, entry.detail
    );
}

#[test]
fn golden_torvald_dwarf_fighter() {
    let engine = engine();
    let log = torvald_log(&engine);
    let projection = engine.project(&log, &[]).unwrap();
    assert!(
        projection.can_finalize,
        "Torvald should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.name, "Torvald");
    assert_eq!(sheet.summary[0], "Dwarf (Rock Dwarf) Fighter 1");

    // Modifiers: Str +4 (ancestry free, background, class key, free boost),
    // Dex +1, Con +3, Int +0, Wis +2, Cha -1 (dwarf flaw).
    assert_entry(sheet, "Attributes", "Strength", "+4");
    assert_entry(sheet, "Attributes", "Dexterity", "+1");
    assert_entry(sheet, "Attributes", "Constitution", "+3");
    assert_entry(sheet, "Attributes", "Intelligence", "+0");
    assert_entry(sheet, "Attributes", "Wisdom", "+2");
    assert_entry(sheet, "Attributes", "Charisma", "-1");

    // HP 23 = 10 ancestry + 10 class + 3 Con (Player Core pg. 42, 136).
    assert_entry(sheet, "Defense", "Hit Points", "23");
    // AC 17 = 10 + 1 Dex (scale mail cap +2) + 3 item + 3 trained.
    assert_entry(sheet, "Defense", "Armor Class", "17");
    // Saves: Fort +8 (expert 5 + Con 3), Ref +6, Will +5; Perception +7.
    assert_entry(sheet, "Defense", "Fortitude", "+8");
    assert_entry(sheet, "Defense", "Reflex", "+6");
    assert_entry(sheet, "Defense", "Will", "+5");
    assert_entry(sheet, "Defense", "Perception", "+7");
    assert_entry(sheet, "Defense", "Class DC", "17");

    // Longsword +9 (martial expert 5 + Str 4), 1d8+4 S.
    assert_entry(sheet, "Attacks", "Longsword", "+9 · 1d8 S+4");
    assert_entry(sheet, "Attacks", "Dagger", "+9 · 1d4 P+4");

    // Skills: Athletics +7 trained (Str 4, no armor penalty — Str meets the
    // scale mail requirement), Intimidation +2 (Warrior), Acrobatics +1
    // untrained.
    assert_entry(sheet, "Skills", "Athletics", "+7");
    assert_entry(sheet, "Skills", "Intimidation", "+2");
    assert_entry(sheet, "Skills", "Acrobatics", "+1");
    assert_entry(sheet, "Skills", "Survival", "+5");
    assert_entry(sheet, "Skills", "Religion", "+5");
    assert_entry(sheet, "Skills", "Crafting", "+3");

    // Coins: 15 gp - 5 gp 8 sp kit - 3 gp option = 6 gp 2 sp.
    assert_entry(sheet, "Equipment", "Coins", "6 gp, 2 sp");
    // Bulk: scale mail 2 (worn) + longsword 1 + shield 1 + pack 1 +
    // dagger L + grappling hook L = 5 Bulk, 2 L.
    assert_entry(sheet, "Equipment", "Bulk", "5 Bulk, 2 L");

    // Speed 20 (dwarf); scale mail penalty waived (Str +4 >= +2 req).
    assert!(
        sheet.summary[1].contains("Speed 20 feet"),
        "summary: {:?}",
        sheet.summary
    );
}

#[test]
fn golden_elyse_human_archer() {
    let engine = engine();
    let log = elyse_log(&engine);
    let projection = engine.project(&log, &[]).unwrap();
    assert!(
        projection.can_finalize,
        "Elyse should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.summary[0], "Human (Skilled Human) Fighter 1");
    assert_entry(sheet, "Attributes", "Strength", "+1");
    assert_entry(sheet, "Attributes", "Dexterity", "+4");
    assert_entry(sheet, "Attributes", "Constitution", "+1");
    assert_entry(sheet, "Attributes", "Intelligence", "+1");
    assert_entry(sheet, "Attributes", "Wisdom", "+2");
    assert_entry(sheet, "Attributes", "Charisma", "+0");
    // HP 19 = 8 + 10 + 1.
    assert_entry(sheet, "Defense", "Hit Points", "19");
    // AC 18 = 10 + 2 (Dex capped by scale mail) + 3 + 3.
    assert_entry(sheet, "Defense", "Armor Class", "18");
    // Longbow +9 (martial expert 5 + Dex 4), 1d8 P, no Str to damage.
    assert_entry(sheet, "Attacks", "Longbow", "+9 · 1d8 P");
    // Armor check penalty applies (Str +1 < scale mail's +2 requirement):
    // Acrobatics trained 3 + Dex 4 - 2 armor = +5; Athletics 3 + 1 - 2 = +2.
    assert_entry(sheet, "Skills", "Acrobatics", "+5");
    assert_entry(sheet, "Skills", "Athletics", "+2");
    assert_entry(sheet, "Skills", "Medicine", "+5");
    // Speed 25 - 5 (unmet Str requirement keeps the scale mail penalty).
    assert!(
        sheet.summary[1].contains("Speed 20 feet"),
        "summary: {:?}",
        sheet.summary
    );
    // Coins: 15 gp - 5 gp 8 sp - 6 gp 2 sp = 3 gp.
    assert_entry(sheet, "Equipment", "Coins", "3 gp");
}

#[test]
fn golden_krivvy_goblin_replacement() {
    let engine = engine();
    let log = krivvy_log(&engine);
    let projection = engine.project(&log, &[]).unwrap();
    assert!(
        projection.can_finalize,
        "Krivvy should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.summary[0], "Goblin (Unbreakable Goblin) Fighter 1");
    // Unbreakable Goblin: ancestry HP 10 instead of 6 -> 10 + 10 + 3 Con.
    assert_entry(sheet, "Defense", "Hit Points", "23");
    // Small size, darkvision.
    assert!(sheet.summary[1].starts_with("Small"), "{:?}", sheet.summary);
    assert!(sheet.summary[1].contains("darkvision"));
    // AC 17 = 10 + 3 Dex (leather cap +4) + 1 leather + 3 trained.
    assert_entry(sheet, "Defense", "Armor Class", "17");
    // Replacement rule: Thievery stayed trained from the class picks, and
    // the background's collision was replaced with Society.
    assert_entry(sheet, "Skills", "Thievery", "+6");
    assert_entry(sheet, "Skills", "Society", "+3");
    // Shortsword: finesse, Dex +3 > Str +2 -> +8 to hit, Str to damage.
    assert_entry(sheet, "Attacks", "Shortsword", "+8 · 1d6 P+2");
    // Sling: propulsive, half Str (+1) to damage.
    assert_entry(sheet, "Attacks", "Sling", "+8 · 1d6 B+1");
    // Coins: 15 gp - 4 gp 4 sp 1 cp itemized = 10 gp 5 sp 9 cp.
    assert_entry(sheet, "Equipment", "Coins", "10 gp, 5 sp, 9 cp");
    // Bulk: leather 1 + pack 1 + shortsword L + sling L + bullets L.
    assert_entry(sheet, "Equipment", "Bulk", "2 Bulk, 3 L");
}

#[test]
fn golden_caelith_elf_scholar_sub_choice() {
    let engine = engine();
    let log = caelith_log(&engine);
    let projection = engine.project(&log, &[]).unwrap();
    assert!(
        projection.can_finalize,
        "Caelith should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.name, "Caelith");
    assert_eq!(sheet.summary[0], "Elf (Whisper Elf) Fighter 1");

    // Str +4 (ancestry free, background free, class key, free boost),
    // Dex +2 (ancestry fixed, free), Con 0 (elf flaw + free boost),
    // Int +2 (ancestry fixed, background choice), Wis +1 (free), Cha +0.
    assert_entry(sheet, "Attributes", "Strength", "+4");
    assert_entry(sheet, "Attributes", "Dexterity", "+2");
    assert_entry(sheet, "Attributes", "Constitution", "+0");
    assert_entry(sheet, "Attributes", "Intelligence", "+2");
    assert_entry(sheet, "Attributes", "Wisdom", "+1");
    assert_entry(sheet, "Attributes", "Charisma", "+0");

    // HP 16 = 6 elf + 10 class + 0 Con.
    assert_entry(sheet, "Defense", "Hit Points", "16");
    // AC 18 = 10 + 2 Dex (scale mail cap +2) + 3 item + 3 trained.
    assert_entry(sheet, "Defense", "Armor Class", "18");
    // Fort +5 (expert 5 + 0), Ref +7 (5 + 2), Will +4 (trained 3 + 1),
    // Perception +6 (expert 5 + 1).
    assert_entry(sheet, "Defense", "Fortitude", "+5");
    assert_entry(sheet, "Defense", "Reflex", "+7");
    assert_entry(sheet, "Defense", "Will", "+4");
    assert_entry(sheet, "Defense", "Perception", "+6");
    assert_entry(sheet, "Defense", "Class DC", "17");

    // Greatsword +9 (martial expert 5 + Str 4), 1d12 S + 4.
    assert_entry(sheet, "Attacks", "Greatsword", "+9 · 1d12 S+4");
    assert_entry(sheet, "Attacks", "Dagger", "+9 · 1d4 P+4");

    // Str +4 meets scale mail's +2 requirement: no check penalty.
    assert_entry(sheet, "Skills", "Athletics", "+7");
    // Occultism trained by the Scholar sub-choice: 3 + Int 2.
    assert_entry(sheet, "Skills", "Occultism", "+5");
    assert_entry(sheet, "Skills", "Arcana", "+5");
    assert_entry(sheet, "Skills", "Crafting", "+5");
    assert_entry(sheet, "Skills", "Medicine", "+4");
    assert_entry(sheet, "Skills", "Religion", "+4");
    assert_entry(sheet, "Skills", "Survival", "+4");
    // Untrained Acrobatics is bare Dex.
    assert_entry(sheet, "Skills", "Acrobatics", "+2");

    // The skill feat follows the sub-choice pick: Assurance (Occultism).
    assert_entry(
        sheet,
        "Features",
        "Assurance (Occultism)",
        "skill feat — Scholar",
    );
    assert_entry(sheet, "Languages & Lore", "Academia Lore", "trained");
    // Elf defaults first, then the two Int-bought picks in pick order.
    assert_entry(
        sheet,
        "Languages & Lore",
        "Languages",
        "Common, Elven, Draconic, Fey",
    );

    // Coins: 15 gp - 5 gp 8 sp kit - 2 gp greatsword option = 7 gp 2 sp.
    assert_entry(sheet, "Equipment", "Coins", "7 gp, 2 sp");
    // Bulk: scale mail 2 (worn) + greatsword 2 + pack 1 + dagger L +
    // grappling hook L.
    assert_entry(sheet, "Equipment", "Bulk", "5 Bulk, 2 L");

    // Speed 35 = elf 30 + Nimble Elf 5; scale mail penalty waived (Str
    // meets the requirement).
    assert!(
        sheet.summary[1].contains("Speed 35 feet"),
        "summary: {:?}",
        sheet.summary
    );
    assert!(sheet.summary[1].contains("low-light vision"));
}

#[test]
fn golden_fizzwick_gnome_obsession_lore() {
    let engine = engine();
    let log = fizzwick_log(&engine);
    let projection = engine.project(&log, &[]).unwrap();
    assert!(
        projection.can_finalize,
        "Fizzwick should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.summary[0], "Gnome (Sensate Gnome) Fighter 1");

    // Str -1 (gnome flaw), Dex +4 (ancestry free, background free, class
    // key, free), Con +3 (ancestry fixed, background choice, free),
    // Int +0, Wis +1 (free), Cha +2 (ancestry fixed, free).
    assert_entry(sheet, "Attributes", "Strength", "-1");
    assert_entry(sheet, "Attributes", "Dexterity", "+4");
    assert_entry(sheet, "Attributes", "Constitution", "+3");
    assert_entry(sheet, "Attributes", "Charisma", "+2");

    // HP 21 = 8 gnome + 10 class + 3 Con.
    assert_entry(sheet, "Defense", "Hit Points", "21");
    // AC 18 = 10 + 3 Dex (studded leather cap +3) + 2 item + 3 trained.
    assert_entry(sheet, "Defense", "Armor Class", "18");
    assert_entry(sheet, "Defense", "Fortitude", "+8");
    assert_entry(sheet, "Defense", "Reflex", "+9");
    assert_entry(sheet, "Defense", "Will", "+4");
    assert_entry(sheet, "Defense", "Perception", "+6");
    assert_entry(sheet, "Defense", "Class DC", "17");

    // Finesse rapier rides Dex to hit (+9 = expert 5 + Dex 4) but Str -1
    // still applies to damage.
    assert_entry(sheet, "Attacks", "Rapier", "+9 · 1d6 P-1");
    assert_entry(sheet, "Attacks", "Dagger", "+9 · 1d4 P-1");

    // Str -1 misses studded leather's +1 requirement: -1 check penalty on
    // Str/Dex skills. Acrobatics 3 trained + 4 Dex - 1 armor.
    assert_entry(sheet, "Skills", "Acrobatics", "+6");
    assert_entry(sheet, "Skills", "Stealth", "+6");
    assert_entry(sheet, "Skills", "Thievery", "+6");
    assert_entry(sheet, "Skills", "Deception", "+5");
    assert_entry(sheet, "Skills", "Diplomacy", "+5");
    // Untrained Athletics: 0 - 1 Str - 1 armor check penalty.
    assert_entry(sheet, "Skills", "Athletics", "-2");

    // Gnome Obsession's Lore carries the player-typed name.
    assert_entry(sheet, "Languages & Lore", "Clockwork Lore", "trained");
    assert_entry(sheet, "Languages & Lore", "Alcohol Lore", "trained");
    assert_entry(
        sheet,
        "Languages & Lore",
        "Languages",
        "Common, Fey, Gnomish",
    );
    assert_entry(sheet, "Features", "Hobnobber", "skill feat — Barkeep");

    // Coins: 15 gp - (3 gp + 2 gp + 2 sp + 1 gp 5 sp + 1 cp itemized)
    // = 8 gp 2 sp 9 cp.
    assert_entry(sheet, "Equipment", "Coins", "8 gp, 2 sp, 9 cp");
    // Bulk: studded leather 1 (worn) + rapier 1 + pack 1 + dagger L
    // (mug is negligible).
    assert_entry(sheet, "Equipment", "Bulk", "3 Bulk, 1 L");

    assert!(sheet.summary[1].starts_with("Small"), "{:?}", sheet.summary);
    assert!(sheet.summary[1].contains("Speed 25 feet"));
    assert!(sheet.summary[1].contains("scent (imprecise) 30 feet"));
}

#[test]
fn golden_wenna_halfling_nomadic_languages() {
    let engine = engine();
    let log = wenna_log(&engine);
    let projection = engine.project(&log, &[]).unwrap();
    assert!(
        projection.can_finalize,
        "Wenna should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.summary[0], "Halfling (Nomadic Halfling) Fighter 1");

    // Str -1 (halfling flaw), Dex +4, Con +2, Int +0, Wis +3, Cha +1.
    assert_entry(sheet, "Attributes", "Strength", "-1");
    assert_entry(sheet, "Attributes", "Dexterity", "+4");
    assert_entry(sheet, "Attributes", "Constitution", "+2");
    assert_entry(sheet, "Attributes", "Intelligence", "+0");
    assert_entry(sheet, "Attributes", "Wisdom", "+3");

    // HP 18 = 6 halfling + 10 class + 2 Con.
    assert_entry(sheet, "Defense", "Hit Points", "18");
    // AC 18 = 10 + 4 Dex (leather cap +4) + 1 item + 3 trained.
    assert_entry(sheet, "Defense", "Armor Class", "18");
    assert_entry(sheet, "Defense", "Fortitude", "+7");
    assert_entry(sheet, "Defense", "Reflex", "+9");
    assert_entry(sheet, "Defense", "Will", "+6");
    assert_entry(sheet, "Defense", "Perception", "+8");

    // Sling +9 (simple expert 5 + Dex 4); propulsive adds the full
    // negative Str (-1) to damage.
    assert_entry(sheet, "Attacks", "Sling", "+9 · 1d6 B-1");
    assert_entry(sheet, "Attacks", "Dagger", "+9 · 1d4 P-1");

    // Str -1 misses even leather's +0 requirement: -1 check penalty.
    assert_entry(sheet, "Skills", "Acrobatics", "+6");
    assert_entry(sheet, "Skills", "Stealth", "+6");
    assert_entry(sheet, "Skills", "Nature", "+6");
    assert_entry(sheet, "Skills", "Medicine", "+6");
    assert_entry(sheet, "Skills", "Survival", "+6");
    assert_entry(sheet, "Skills", "Athletics", "-2");

    // Nomadic Halfling: two bonus languages despite Int +0, from the
    // halfling additional-language list; Nomad's Lore is player-named.
    assert_entry(
        sheet,
        "Languages & Lore",
        "Languages",
        "Common, Halfling, Dwarven, Goblin",
    );
    assert_entry(sheet, "Languages & Lore", "Steppe Lore", "trained");
    assert_entry(
        sheet,
        "Features",
        "Assurance (Survival)",
        "skill feat — Nomad",
    );

    // Coins: 15 gp - (2 gp + 1 cp + 2 sp + 1 gp 5 sp + 2 cp itemized;
    // the sling is free) = 11 gp 2 sp 7 cp.
    assert_entry(sheet, "Equipment", "Coins", "11 gp, 2 sp, 7 cp");
    // Bulk: leather 1 (worn) + pack 1 + sling L + bullets L + dagger L +
    // bedroll L.
    assert_entry(sheet, "Equipment", "Bulk", "2 Bulk, 4 L");

    assert!(sheet.summary[1].starts_with("Small"), "{:?}", sheet.summary);
    assert!(sheet.summary[1].contains("Speed 25 feet"));
}

#[test]
fn golden_bramble_leshy_root_hp_override() {
    let engine = engine();
    let log = bramble_log(&engine);
    let projection = engine.project(&log, &[]).unwrap();
    assert!(
        projection.can_finalize,
        "Bramble should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.summary[0], "Leshy (Root Leshy) Fighter 1");

    // Str +4, Dex +1, Con +3, Int -1 (leshy flaw), Wis +2, Cha +0.
    assert_entry(sheet, "Attributes", "Strength", "+4");
    assert_entry(sheet, "Attributes", "Constitution", "+3");
    assert_entry(sheet, "Attributes", "Intelligence", "-1");
    assert_entry(sheet, "Attributes", "Wisdom", "+2");

    // Root Leshy: ancestry HP 10 instead of 8 -> 10 + 10 class + 3 Con.
    assert_entry(sheet, "Defense", "Hit Points", "23");
    // AC 17 = 10 + 1 Dex (scale mail cap +2) + 3 item + 3 trained.
    assert_entry(sheet, "Defense", "Armor Class", "17");
    assert_entry(sheet, "Defense", "Fortitude", "+8");
    assert_entry(sheet, "Defense", "Reflex", "+6");
    assert_entry(sheet, "Defense", "Will", "+5");
    assert_entry(sheet, "Defense", "Perception", "+7");

    // Seedpod is a true ranged unarmed attack: Dex to hit (expert 5 + 1),
    // no attribute to damage.
    assert_entry(sheet, "Attacks", "Seedpod", "+6 · 1d4 B");
    // The double-slice pair: both melee on Str.
    assert_entry(sheet, "Attacks", "Hatchet", "+9 · 1d6 S+4");
    assert_entry(sheet, "Attacks", "Light Hammer", "+9 · 1d6 B+4");

    // Int -1 cuts the fighter's additional skills to 2 (3 + Int, min 0).
    assert_entry(sheet, "Skills", "Athletics", "+7");
    assert_entry(sheet, "Skills", "Nature", "+5");
    assert_entry(sheet, "Skills", "Stealth", "+4");
    assert_entry(sheet, "Skills", "Medicine", "+5");
    // Untrained Int skill carries the flaw.
    assert_entry(sheet, "Skills", "Arcana", "-1");

    assert_entry(sheet, "Languages & Lore", "Warfare Lore", "trained");
    // Int -1: no language chooser, ancestry defaults only.
    assert_entry(sheet, "Languages & Lore", "Languages", "Common, Fey");
    assert_entry(
        sheet,
        "Features",
        "Battle Medicine",
        "skill feat — Field Medic",
    );

    // Coins: 15 gp - 5 gp 8 sp kit - 4 sp hatchet - 3 sp light hammer
    // = 8 gp 5 sp.
    assert_entry(sheet, "Equipment", "Coins", "8 gp, 5 sp");
    // Bulk: scale mail 2 (worn) + pack 1 + dagger L + grappling hook L +
    // hatchet L + light hammer L.
    assert_entry(sheet, "Equipment", "Bulk", "3 Bulk, 4 L");

    assert!(sheet.summary[1].starts_with("Small"), "{:?}", sheet.summary);
    assert!(sheet.summary[1].contains("Speed 25 feet"));
    assert!(sheet.summary[1].contains("low-light vision"));
}

#[test]
fn golden_grashk_orc_iron_fists() {
    let engine = engine();
    let log = grashk_log(&engine);
    let projection = engine.project(&log, &[]).unwrap();
    assert!(
        projection.can_finalize,
        "Grashk should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.summary[0], "Orc (Hold-Scarred Orc) Fighter 1");

    // Str +4, Dex +1, Con +3, Int +0, Wis +1, Cha +0 (orc: two free
    // ancestry boosts, no fixed, no flaw).
    assert_entry(sheet, "Attributes", "Strength", "+4");
    assert_entry(sheet, "Attributes", "Dexterity", "+1");
    assert_entry(sheet, "Attributes", "Constitution", "+3");
    assert_entry(sheet, "Attributes", "Charisma", "+0");

    // Hold-Scarred Orc: ancestry HP 12 instead of 10 -> 12 + 10 + 3 Con.
    assert_entry(sheet, "Defense", "Hit Points", "25");
    // AC 17 = 10 + 1 Dex (hide cap +2) + 3 item + 3 trained.
    assert_entry(sheet, "Defense", "Armor Class", "17");
    assert_entry(sheet, "Defense", "Fortitude", "+8");
    assert_entry(sheet, "Defense", "Reflex", "+6");
    assert_entry(sheet, "Defense", "Will", "+4");
    assert_entry(sheet, "Defense", "Perception", "+6");
    assert_entry(sheet, "Defense", "Class DC", "17");

    // Iron Fists replaces the default fist: same 1d4 B on Str (finesse but
    // Dex +1 < Str +4), rendered as an effect-granted unarmed attack.
    assert_entry(sheet, "Attacks", "Fist", "+9 · 1d4 B (+4)");
    assert_entry(sheet, "Attacks", "Warhammer", "+9 · 1d8 B+4");
    // Thrown weapons stay on melee (Str) rules.
    assert_entry(sheet, "Attacks", "Javelin", "+9 · 1d6 P+4");

    // Str +4 meets hide's +2 requirement: no check penalty, and the -5
    // speed penalty is reduced to 0.
    assert_entry(sheet, "Skills", "Athletics", "+7");
    assert_entry(sheet, "Skills", "Intimidation", "+3");
    assert_entry(sheet, "Skills", "Nature", "+4");
    assert_entry(sheet, "Skills", "Religion", "+4");
    assert_entry(sheet, "Skills", "Survival", "+4");

    assert_entry(sheet, "Languages & Lore", "Mining Lore", "trained");
    assert_entry(sheet, "Languages & Lore", "Languages", "Common, Orcish");
    assert_entry(
        sheet,
        "Features",
        "Terrain Expertise (Underground)",
        "skill feat — Miner",
    );

    // Coins: 15 gp - (2 gp + 1 gp + 2 gp + 1 sp + 1 gp 5 sp + 1 cp
    // itemized) = 8 gp 3 sp 9 cp.
    assert_entry(sheet, "Equipment", "Coins", "8 gp, 3 sp, 9 cp");
    // Bulk: hide 2 (worn) + warhammer 1 + steel shield 1 + pack 1 +
    // javelin L + torch L.
    assert_entry(sheet, "Equipment", "Bulk", "5 Bulk, 2 L");

    assert!(
        sheet.summary[1].contains("Speed 25 feet"),
        "hide's speed penalty must be waived at Str +4: {:?}",
        sheet.summary
    );
    assert!(sheet.summary[1].contains("darkvision"));
}

#[test]
fn golden_maera_dwarf_aiuvarin_union() {
    let engine = engine();
    let log = maera_log(&engine);
    let projection = engine.project(&log, &[]).unwrap();
    assert!(
        projection.can_finalize,
        "Maera should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    // The versatile heritage renders in the identity line like any other.
    assert_eq!(sheet.summary[0], "Dwarf (Aiuvarin) Fighter 1");

    // Str +4, Dex +1, Con +3, Int +0, Wis +2, Cha -1 (dwarf flaw).
    assert_entry(sheet, "Attributes", "Strength", "+4");
    assert_entry(sheet, "Attributes", "Constitution", "+3");
    assert_entry(sheet, "Attributes", "Wisdom", "+2");
    assert_entry(sheet, "Attributes", "Charisma", "-1");

    // HP 23 = 10 dwarf + 10 class + 3 Con (versatile heritage: no
    // override, dwarf HP stands).
    assert_entry(sheet, "Defense", "Hit Points", "23");
    assert_entry(sheet, "Defense", "Armor Class", "17");
    assert_entry(sheet, "Defense", "Fortitude", "+8");
    assert_entry(sheet, "Defense", "Reflex", "+6");
    assert_entry(sheet, "Defense", "Will", "+5");
    assert_entry(sheet, "Defense", "Perception", "+7");

    assert_entry(sheet, "Attacks", "Longsword", "+9 · 1d8 S+4");
    assert_entry(sheet, "Attacks", "Javelin", "+9 · 1d6 P+4");

    // Earned Glory (an aiuvarin feat taken through the union) trains
    // Performance: 3 trained + Cha -1.
    assert_entry(sheet, "Skills", "Performance", "+2");
    assert_entry(sheet, "Skills", "Athletics", "+7");
    assert_entry(sheet, "Skills", "Survival", "+5");
    assert_entry(sheet, "Skills", "Medicine", "+5");
    assert_entry(sheet, "Skills", "Society", "+3");
    assert_entry(sheet, "Skills", "Intimidation", "+2");

    assert_entry(sheet, "Languages & Lore", "Legal Lore", "trained");
    assert_entry(sheet, "Languages & Lore", "Languages", "Common, Dwarven");
    assert_entry(
        sheet,
        "Features",
        "Experienced Tracker",
        "skill feat — Bounty Hunter",
    );

    // Coins: 15 gp - 5 gp 8 sp kit - 3 gp option - 1 sp javelin -
    // 5 sp rope = 5 gp 6 sp.
    assert_entry(sheet, "Equipment", "Coins", "5 gp, 6 sp");
    // Bulk: scale mail 2 (worn) + longsword 1 + shield 1 + pack 1 +
    // dagger L + hook L + javelin L + rope L.
    assert_entry(sheet, "Equipment", "Bulk", "5 Bulk, 4 L");

    // Dwarf darkvision stands; the heritage's low-light vision lists
    // alongside it. Speed 20 (dwarf), armor penalty waived.
    assert!(
        sheet.summary[1].contains("Speed 20 feet"),
        "summary: {:?}",
        sheet.summary
    );
    assert!(sheet.summary[1].contains("darkvision"));
    assert!(sheet.summary[1].contains("low-light vision"));
}

#[test]
fn golden_garrek_quick_build() {
    let engine = engine();
    let log = garrek_log(&engine);
    // Every decision carries the suggested provenance.
    assert!(
        log.iter()
            .all(|d| d.source == types::DecisionSource::Suggested),
        "quick-build decisions must carry the Suggested source"
    );
    let projection = engine.project(&log, &[]).unwrap();
    assert!(
        projection.can_finalize,
        "the expanded suggested build must be review-ready: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.name, "Garrek Ironvale");
    assert_eq!(sheet.summary[0], "Human (Skilled Human) Fighter 1");

    // The planner takes the first legal candidates: ancestry-free
    // [str, con], background choice str + free wis, class key str, free
    // boosts [str, dex, con, wis] -> Str +4, Dex +1, Con +2, Int +0,
    // Wis +2, Cha +0.
    assert_entry(sheet, "Attributes", "Strength", "+4");
    assert_entry(sheet, "Attributes", "Dexterity", "+1");
    assert_entry(sheet, "Attributes", "Constitution", "+2");
    assert_entry(sheet, "Attributes", "Intelligence", "+0");
    assert_entry(sheet, "Attributes", "Wisdom", "+2");
    assert_entry(sheet, "Attributes", "Charisma", "+0");

    // HP 20 = 8 human + 10 class + 2 Con.
    assert_entry(sheet, "Defense", "Hit Points", "20");
    // AC 17 = 10 + 1 Dex (scale mail cap +2) + 3 item + 3 trained.
    assert_entry(sheet, "Defense", "Armor Class", "17");
    assert_entry(sheet, "Defense", "Fortitude", "+7");
    assert_entry(sheet, "Defense", "Reflex", "+6");
    assert_entry(sheet, "Defense", "Will", "+5");
    assert_entry(sheet, "Defense", "Perception", "+7");
    assert_entry(sheet, "Defense", "Class DC", "17");

    // Sword-and-board: longsword +9 (expert 5 + Str 4), 1d8 S + 4.
    assert_entry(sheet, "Attacks", "Longsword", "+9 · 1d8 S+4");
    assert_entry(sheet, "Attacks", "Dagger", "+9 · 1d4 P+4");

    // Class choice Athletics; Skilled Human takes the first legal
    // heritage candidate (Diplomacy); Warrior trains Intimidation; the
    // trained picks resolve to Acrobatics, Medicine, Survival.
    assert_entry(sheet, "Skills", "Athletics", "+7");
    assert_entry(sheet, "Skills", "Diplomacy", "+3");
    assert_entry(sheet, "Skills", "Intimidation", "+3");
    assert_entry(sheet, "Skills", "Acrobatics", "+4");
    assert_entry(sheet, "Skills", "Medicine", "+5");
    assert_entry(sheet, "Skills", "Survival", "+5");

    assert_entry(sheet, "Languages & Lore", "Warfare Lore", "trained");
    // Int +0: the suggested language candidates never fire.
    assert_entry(sheet, "Languages & Lore", "Languages", "Common");

    // Coins: 15 gp - 5 gp 8 sp kit - 3 gp option = 6 gp 2 sp.
    assert_entry(sheet, "Equipment", "Coins", "6 gp, 2 sp");
    assert_entry(sheet, "Equipment", "Bulk", "5 Bulk, 2 L");

    assert!(
        sheet.summary[1].contains("Speed 25 feet"),
        "summary: {:?}",
        sheet.summary
    );
}

/// The committed fixture logs must stay in sync with the golden builders —
/// they are the shared input for the WASM/native parity smoke.
#[test]
fn fixture_logs_match_golden_builders() {
    let engine = engine();
    for (name, log) in [
        ("torvald", torvald_log(&engine)),
        ("elyse", elyse_log(&engine)),
        ("krivvy", krivvy_log(&engine)),
        ("caelith", caelith_log(&engine)),
        ("fizzwick", fizzwick_log(&engine)),
        ("wenna", wenna_log(&engine)),
        ("bramble", bramble_log(&engine)),
        ("grashk", grashk_log(&engine)),
        ("maera", maera_log(&engine)),
        ("garrek", garrek_log(&engine)),
    ] {
        let path = checks::workspace_root().join(format!("checks/fixtures/{name}.log.json"));
        let on_disk = std::fs::read_to_string(&path)
            .unwrap_or_else(|_| panic!("missing fixture {path:?} — run the regen test"));
        let parsed: Vec<Decision> = serde_json::from_str(&on_disk).expect("fixture parses");
        assert_eq!(
            parsed, log,
            "fixture {name} is stale — rerun: cargo test -p checks --test replay regen_fixtures -- --ignored"
        );
        // And replay of the fixture reproduces the same sheet twice.
        assert_eq!(engine.sheet(&parsed).unwrap(), engine.sheet(&log).unwrap());
    }
}

/// Regenerates the committed fixtures. Run manually after a deliberate
/// golden-build change: cargo test -p checks --test replay regen_fixtures -- --ignored
#[test]
#[ignore]
fn regen_fixtures() {
    let engine = engine();
    let dir = checks::workspace_root().join("checks/fixtures");
    std::fs::create_dir_all(&dir).unwrap();
    for (name, log) in [
        ("torvald", torvald_log(&engine)),
        ("elyse", elyse_log(&engine)),
        ("krivvy", krivvy_log(&engine)),
        ("caelith", caelith_log(&engine)),
        ("fizzwick", fizzwick_log(&engine)),
        ("wenna", wenna_log(&engine)),
        ("bramble", bramble_log(&engine)),
        ("grashk", grashk_log(&engine)),
        ("maera", maera_log(&engine)),
        ("garrek", garrek_log(&engine)),
    ] {
        let path = dir.join(format!("{name}.log.json"));
        std::fs::write(&path, serde_json::to_string_pretty(&log).unwrap()).unwrap();
        // Alongside each log, the expected sheet — the parity smoke and the
        // persistence fixtures reuse these.
        let sheet = engine.sheet(&log).unwrap();
        let sheet_path = dir.join(format!("{name}.sheet.json"));
        std::fs::write(&sheet_path, serde_json::to_string_pretty(&sheet).unwrap()).unwrap();
    }
}

#[test]
fn fixture_sheets_match_replay() {
    let engine = engine();
    for name in [
        "torvald", "elyse", "krivvy", "caelith", "fizzwick", "wenna", "bramble", "grashk", "maera",
        "garrek",
    ] {
        let dir = checks::workspace_root().join("checks/fixtures");
        let log: Vec<Decision> = serde_json::from_str(
            &std::fs::read_to_string(dir.join(format!("{name}.log.json"))).unwrap(),
        )
        .unwrap();
        let stored: types::SheetView = serde_json::from_str(
            &std::fs::read_to_string(dir.join(format!("{name}.sheet.json"))).unwrap(),
        )
        .unwrap();
        assert_eq!(
            engine.sheet(&log).unwrap(),
            stored,
            "replay of fixture '{name}' diverges from its stored sheet"
        );
    }
}

mod properties {
    use super::*;
    use proptest::prelude::*;

    #[derive(Debug, Clone)]
    enum Op {
        Confirm { slot: usize, pick: usize },
        Clear { slot: usize },
    }

    fn ops() -> impl Strategy<Value = Vec<Op>> {
        proptest::collection::vec(
            prop_oneof![
                (0usize..64, 0usize..8).prop_map(|(slot, pick)| Op::Confirm { slot, pick }),
                (0usize..64).prop_map(|slot| Op::Clear { slot }),
            ],
            0..30,
        )
    }

    proptest! {
        #![proptest_config(ProptestConfig::with_cases(48))]
        /// Random walks over the real PF2e slot graph, driven through the
        /// projection (as a client would be): whatever happens, projection
        /// stays deterministic, orders stay dense, at most one decision per
        /// slot, and can_finalize tracks the checklist.
        #[test]
        fn pf2e_random_walk(ops in ops()) {
            let engine = engine();
            let mut log: Vec<Decision> = vec![];
            let mut n = 0u32;
            for op in ops {
                let projection = engine.project(&log, &[]).unwrap();
                let open_slots: Vec<_> = projection
                    .steps
                    .iter()
                    .flat_map(|s| &s.slots)
                    .filter(|s| s.locked_reason.is_none())
                    .collect();
                if open_slots.is_empty() {
                    break;
                }
                match op {
                    Op::Confirm { slot, pick } => {
                        let slot_view = open_slots[slot % open_slots.len()];
                        if slot_view.decision.is_some() {
                            continue;
                        }
                        let available: Vec<_> =
                            slot_view.options.iter().filter(|o| o.available).collect();
                        let selection = match &slot_view.kind {
                            types::SlotViewKind::Single => {
                                if available.is_empty() { continue; }
                                Selection::Option(available[pick % available.len()].id.clone())
                            }
                            types::SlotViewKind::Multi { count } => {
                                if available.is_empty() { continue; }
                                // Sometimes under- or over-pick on purpose.
                                let take = (pick % (*count as usize + 2)).min(available.len());
                                Selection::Options(
                                    available.iter().cycle().skip(pick % available.len()).take(take).map(|o| o.id.clone()).collect(),
                                )
                            }
                            types::SlotViewKind::List => {
                                let take = pick % 3;
                                Selection::Options(
                                    available.iter().take(take).map(|o| o.id.clone()).collect(),
                                )
                            }
                            types::SlotViewKind::Text { .. } => {
                                Selection::Text(format!("text-{pick}"))
                            }
                        };
                        n += 1;
                        let input = DecisionInput {
                            id: DecisionId::new(format!("walk-{n}")),
                            slot: slot_view.id.clone(),
                            selection,
                            source: DecisionSource::Player,
                        };
                        if let Ok(AppendOutcome::Appended(new_log)) = engine.append(&log, input) {
                            log = new_log;
                        }
                    }
                    Op::Clear { slot } => {
                        let slot_view = open_slots[slot % open_slots.len()];
                        if slot_view.decision.is_none() {
                            continue;
                        }
                        if let Ok((new_log, _)) = engine.clear(&log, &[], &slot_view.id) {
                            log = new_log;
                        }
                    }
                }

                let orders: Vec<u32> = log.iter().map(|d| d.order).collect();
                prop_assert_eq!(&orders, &(0..log.len() as u32).collect::<Vec<_>>());
                let mut seen = std::collections::BTreeSet::new();
                for d in &log {
                    prop_assert!(seen.insert(d.slot.clone()));
                }
                let p1 = engine.project(&log, &[]).unwrap();
                let p2 = engine.project(&log, &[]).unwrap();
                prop_assert_eq!(&p1, &p2);
                prop_assert_eq!(p1.can_finalize, p1.checklist.is_empty());
                // Coherence: statuses, entries, and explanations agree.
                for slot in p1.steps.iter().flat_map(|s| &s.slots) {
                    match slot.status {
                        types::SlotStatus::Locked => {
                            prop_assert!(slot.locked_reason.is_some());
                        }
                        types::SlotStatus::Partial | types::SlotStatus::Illegal => {
                            prop_assert!(
                                p1.checklist.iter().any(|e| e.slot == slot.id),
                                "{} is {:?} with no checklist entry",
                                slot.id, slot.status
                            );
                        }
                        _ => {}
                    }
                }
                for entry in &p1.checklist {
                    let target = p1
                        .steps
                        .iter()
                        .flat_map(|s| &s.slots)
                        .find(|s| s.id == entry.slot);
                    prop_assert!(target.is_some(), "entry for absent slot {}", entry.slot);
                    prop_assert!(
                        target.unwrap().status != types::SlotStatus::Complete,
                        "entry against Complete slot {}", entry.slot
                    );
                }
            }
        }
    }
}

// ---- chargen-wizard goldens: the PF2e Wizard and the prep section ----

fn scoped_one(slot: &str, option: &str) -> types::ScopedChoice {
    types::ScopedChoice {
        slot: SlotId::new(slot),
        selection: one(option),
    }
}

fn scoped_many(slot: &str, options: &[&str]) -> types::ScopedChoice {
    types::ScopedChoice {
        slot: SlotId::new(slot),
        selection: many(options),
    }
}

/// Sylvenne, an Arctic Elf Artisan Wizard of the School of Battle Magic.
/// Hand-verified against Player Core: Elf pg. 56 (Dex+Int+free, Con flaw),
/// Artisan pg. 84, Wizard pg. 192-199.
fn sylvenne_log(engine: &ruleset_pf2e::Pf2eEngine) -> Vec<Decision> {
    let mut log = Vec::new();
    let n = &mut 0;
    confirm(engine, &mut log, n, "pf2e.ancestry", one("ancestry.elf"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.heritage",
        one("heritage.elf.arctic"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.feat",
        one("feat.ancestry.elf.unwavering-mien"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.ancestry-free",
        many(&["attr.wis"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.background",
        one("background.artisan"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-choice",
        one("attr.int"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.background-free",
        one("attr.cha"),
    );
    confirm(engine, &mut log, n, "pf2e.class", one("class.wizard"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.key-attribute",
        one("attr.int"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.thesis",
        one("thesis.spell-substitution"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.school",
        one("school.battle-magic"),
    );
    confirm(
        engine,
        &mut log,
        n,
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
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.spellbook.rank1",
        many(&[
            "spell.command",
            "spell.fear",
            "spell.grease",
            "spell.jump",
            "spell.sleep",
        ]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.class.spellbook.curriculum",
        many(&["spell.breathe-fire", "spell.force-barrage"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.class-choice",
        one("skill.arcana"),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.skills.trained",
        many(&[
            "skill.society",
            "skill.occultism",
            "skill.nature",
            "skill.stealth",
            "skill.diplomacy",
            "skill.deception",
        ]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.boosts.free",
        many(&["attr.int", "attr.dex", "attr.con", "attr.wis"]),
    );
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.ancestry.languages",
        many(&["lang.draconic", "lang.empyrean", "lang.fey", "lang.gnomish"]),
    );
    confirm(engine, &mut log, n, "pf2e.equipment.kit", one("kit.wizard"));
    confirm(
        engine,
        &mut log,
        n,
        "pf2e.details.name",
        Selection::Text("Sylvenne".into()),
    );
    log
}

/// Sylvenne's initial preparation. The school preparations come straight
/// from the curriculum (no spellbook membership required — the printed
/// rule), which Telekinetic Projectile and Mystic Armor deliberately
/// exercise: neither is in her book.
fn sylvenne_prep() -> Vec<types::ScopedChoice> {
    vec![
        scoped_many(
            "pf2e.prep.cantrips",
            &[
                "spell.shield",
                "spell.ignition",
                "spell.electric-arc",
                "spell.detect-magic",
                "spell.light",
            ],
        ),
        scoped_many("pf2e.prep.rank1", &["spell.fear", "spell.command"]),
        scoped_one("pf2e.prep.school-cantrip", "spell.telekinetic-projectile"),
        scoped_one("pf2e.prep.school-rank1", "spell.mystic-armor"),
    ]
}

#[test]
fn golden_sylvenne_elf_wizard_battle_magic() {
    let engine = engine();
    let log = sylvenne_log(&engine);
    let prep = sylvenne_prep();
    let projection = engine.project(&log, &prep).unwrap();
    assert!(
        projection.can_finalize,
        "Sylvenne should be complete and legal: {:#?}",
        projection.checklist
    );
    let sheet = &projection.sheet;
    assert_eq!(sheet.name, "Sylvenne");
    assert_eq!(sheet.summary[0], "Elf (Arctic Elf) Wizard 1");

    // Modifiers: Dex +2 (elf, free), Con +0 (flaw + free), Int +4 (elf,
    // background choice, class key, free), Wis +2 (ancestry free, free),
    // Cha +1 (background free).
    assert_entry(sheet, "Attributes", "Strength", "+0");
    assert_entry(sheet, "Attributes", "Dexterity", "+2");
    assert_entry(sheet, "Attributes", "Constitution", "+0");
    assert_entry(sheet, "Attributes", "Intelligence", "+4");
    assert_entry(sheet, "Attributes", "Wisdom", "+2");
    assert_entry(sheet, "Attributes", "Charisma", "+1");

    // HP 12 = 6 elf + 6 class + 0 Con. AC 15 = 10 + 2 Dex + 3 trained
    // unarmored. Saves: Fort +3, Ref +5, Will +7 (expert 5 + Wis 2);
    // Perception +5 (trained 3 + Wis 2); Class DC 17.
    assert_entry(sheet, "Defense", "Hit Points", "12");
    assert_entry(sheet, "Defense", "Armor Class", "15");
    assert_entry(sheet, "Defense", "Fortitude", "+3");
    assert_entry(sheet, "Defense", "Reflex", "+5");
    assert_entry(sheet, "Defense", "Will", "+7");
    assert_entry(sheet, "Defense", "Perception", "+5");
    assert_entry(sheet, "Defense", "Class DC", "17");

    // Spellcasting: attack +7 (trained 3 + Int 4), DC 17; 5+1 cantrips,
    // 2+1 rank-1 slots; focus pool from the school.
    assert_entry(sheet, "Spellcasting", "Tradition", "Arcane");
    assert_entry(sheet, "Spellcasting", "Spell attack", "+7");
    assert_entry(sheet, "Spellcasting", "Spell DC", "17");
    assert_entry(sheet, "Spellcasting", "Cantrips", "6 prepared");
    assert_entry(sheet, "Spellcasting", "Rank 1 slots", "3");
    assert_entry(sheet, "Spellcasting", "Arcane thesis", "Spell Substitution");
    assert_entry(
        sheet,
        "Spellcasting",
        "Arcane school",
        "School of Battle Magic",
    );
    assert_entry(sheet, "Spellcasting", "Focus pool", "1 Focus Point");
    let focus = sheet.entry("Spellcasting", "Focus pool").unwrap();
    assert!(
        focus.detail.as_deref().unwrap().contains("Force Bolt"),
        "the school grants Force Bolt: {focus:?}"
    );

    // Skills: Arcana +7 (class, trained 3 + Int 4), Crafting +7 (Artisan).
    assert_entry(sheet, "Skills", "Arcana", "+7");
    assert_entry(sheet, "Skills", "Crafting", "+7");

    // The projection's displayed sheet carries the prepared section; the
    // school preparations show curriculum spells not in her book.
    let prepared = sheet
        .sections
        .iter()
        .find(|s| s.title == "Prepared Spells")
        .expect("displayed sheet carries the prepared section");
    let entry = |label: &str| {
        prepared
            .entries
            .iter()
            .find(|e| e.label == label)
            .unwrap_or_else(|| panic!("prepared section missing {label}"))
    };
    assert_eq!(
        entry("Cantrips").value,
        "Shield, Ignition, Electric Arc, Detect Magic, Light"
    );
    assert_eq!(entry("Rank 1").value, "Fear, Command");
    assert_eq!(entry("School cantrip").value, "Telekinetic Projectile");
    assert_eq!(entry("School slot (rank 1)").value, "Mystic Armor");
}

/// Replay purity: the materialized sheet is fold(log) alone — byte-for-byte
/// identical whatever the prep section holds — and prep entries never
/// enter the log.
#[test]
fn stored_sheet_is_pure_over_prep() {
    let engine = engine();
    let log = sylvenne_log(&engine);
    let bare = engine.sheet(&log).unwrap();
    assert!(
        !bare.sections.iter().any(|s| s.title == "Prepared Spells"),
        "the materialized sheet never contains scoped sections"
    );
    // Same log, different (or absent, or nonsense) prep: same sheet.
    let json_bare = serde_json::to_string(&bare).unwrap();
    for prep in [
        Vec::new(),
        sylvenne_prep(),
        vec![scoped_one("pf2e.prep.cantrips", "spell.sleep")],
        vec![scoped_one("nonsense.slot", "spell.sleep")],
    ] {
        let _ = engine.project(&log, &prep).unwrap();
        let again = engine.sheet(&log).unwrap();
        assert_eq!(serde_json::to_string(&again).unwrap(), json_bare);
    }
}

/// Incomplete or illegal preparation blocks finalize through the same
/// checklist as build gaps.
#[test]
fn prep_gaps_and_illegal_prep_block_finalize() {
    let engine = engine();
    let log = sylvenne_log(&engine);
    // No prep at all: incomplete entries, no finalize.
    let empty = engine.project(&log, &[]).unwrap();
    assert!(!empty.can_finalize);
    // A spell not in the book: Illegal entry.
    let mut bad = sylvenne_prep();
    bad[1] = scoped_many("pf2e.prep.rank1", &["spell.fear", "spell.grim-tendrils"]);
    let p = engine.project(&log, &bad).unwrap();
    assert!(!p.can_finalize);
    assert!(p
        .checklist
        .iter()
        .any(|e| e.severity == types::ChecklistSeverity::Illegal
            && e.message.contains("not in your spellbook")));
    // A non-curriculum spell in the school slot: Illegal entry.
    let mut bad = sylvenne_prep();
    bad[3] = scoped_one("pf2e.prep.school-rank1", "spell.sleep");
    let p = engine.project(&log, &bad).unwrap();
    assert!(p
        .checklist
        .iter()
        .any(|e| e.severity == types::ChecklistSeverity::Illegal
            && e.message.contains("curriculum")));
    // Overfilled rank: Illegal entry.
    let mut bad = sylvenne_prep();
    bad[1] = scoped_many(
        "pf2e.prep.rank1",
        &["spell.fear", "spell.command", "spell.sleep"],
    );
    let p = engine.project(&log, &bad).unwrap();
    assert!(p
        .checklist
        .iter()
        .any(|e| e.severity == types::ChecklistSeverity::Illegal
            && e.message.contains("only 2 can be prepared")));
}

/// The changed-school cascade: everything curriculum-derived clears — and
/// ONLY what the preview listed — while school-independent preparation
/// survives. (Preparing the same spell twice is also exercised here.)
#[test]
fn changing_school_cascades_exactly_as_previewed() {
    let engine = engine();
    let log = sylvenne_log(&engine);
    let prep = sylvenne_prep();

    let preview = engine
        .clear_preview(&log, &prep, &SlotId::new("pf2e.class.school"))
        .unwrap();
    let mut previewed: Vec<String> = preview.cleared.iter().map(|c| c.slot.to_string()).collect();
    previewed.sort();
    assert_eq!(
        previewed,
        vec![
            "pf2e.class.school",
            "pf2e.class.spellbook.curriculum",
            "pf2e.prep.rank1",
            "pf2e.prep.school-cantrip",
            "pf2e.prep.school-rank1",
        ],
        "the confirmation lists exactly the curriculum-derived decisions"
    );

    let (out, surviving) = engine
        .amend(
            &log,
            &prep,
            DecisionInput {
                id: DecisionId::new("golden-school-swap"),
                slot: SlotId::new("pf2e.class.school"),
                selection: one("school.protean-form"),
                source: DecisionSource::Player,
            },
        )
        .unwrap();
    let AppendOutcome::Appended(new_log) = out else {
        panic!("school amend must append");
    };
    // Exactly the previewed prep slots cleared; the cantrip prep survived.
    let surviving_slots: Vec<&str> = surviving.iter().map(|c| c.slot.as_str()).collect();
    assert_eq!(surviving_slots, vec!["pf2e.prep.cantrips"]);
    // The new state re-opens the curriculum slots under the new school.
    let p = engine.project(&new_log, &surviving).unwrap();
    assert!(!p.can_finalize);
    let focus = p.sheet.entry("Spellcasting", "Focus pool").unwrap();
    assert!(
        focus.detail.as_deref().unwrap().contains("Scramble Body"),
        "the new school grants its own focus spell: {focus:?}"
    );

    // Revised-prep fixture: refill under the new school and finalize again.
    let refilled = vec![
        surviving[0].clone(),
        scoped_many("pf2e.prep.rank1", &["spell.fear", "spell.fear"]),
        scoped_one("pf2e.prep.school-cantrip", "spell.gouging-claw"),
        scoped_one("pf2e.prep.school-rank1", "spell.pest-form"),
    ];
    // The curriculum spellbook additions must be re-picked first.
    let (out, refilled_prep) = engine
        .amend(
            &log_with(
                &engine,
                &new_log,
                "pf2e.class.spellbook.curriculum",
                many(&["spell.pest-form", "spell.spider-sting"]),
            ),
            &refilled,
            DecisionInput {
                id: DecisionId::new("golden-noop-name"),
                slot: SlotId::new("pf2e.details.name"),
                selection: Selection::Text("Sylvenne".into()),
                source: DecisionSource::Player,
            },
        )
        .unwrap();
    let AppendOutcome::Appended(final_log) = out else {
        panic!("name amend must append");
    };
    let p = engine.project(&final_log, &refilled_prep).unwrap();
    assert!(
        p.can_finalize,
        "refilled Protean Sylvenne is legal: {:#?}",
        p.checklist
    );
}

fn log_with(
    engine: &ruleset_pf2e::Pf2eEngine,
    log: &[Decision],
    slot: &str,
    selection: Selection,
) -> Vec<Decision> {
    let input = DecisionInput {
        id: DecisionId::new(format!("golden-extra-{slot}")),
        slot: SlotId::new(slot),
        selection,
        source: DecisionSource::Player,
    };
    match engine.append(log, input) {
        Ok(AppendOutcome::Appended(new_log)) => new_log,
        other => panic!("append on '{slot}' rejected: {other:?}"),
    }
}
