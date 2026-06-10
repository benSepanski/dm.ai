# NOTE: exceeds 400 LoC — single cohesive data module
"""D&D 5.5e feat data (2024 PHB chapter 5)."""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import Ability, Feat

_ALL_ABILITIES: list[Ability] = list(Ability)
_MENTAL: list[Ability] = [Ability.INTELLIGENCE, Ability.WISDOM, Ability.CHARISMA]
_STR_DEX: list[Ability] = [Ability.STRENGTH, Ability.DEXTERITY]


@dataclass(frozen=True)
class FeatData:
    """Typed feat definition.

    ``ability_increase_options`` lists the abilities a general feat can
    raise by 1 (empty for feats granting no increase). Category is
    available via ``feat.category``.
    """

    feat: Feat
    description: str
    prerequisite: str | None = None
    repeatable: bool = False
    ability_increase_options: list[Ability] = field(default_factory=list)


FEATS: dict[Feat, FeatData] = {
    # ------------------------------------------------------------------
    # Origin feats
    # ------------------------------------------------------------------
    Feat.ALERT: FeatData(
        feat=Feat.ALERT,
        description=(
            "Add your Proficiency Bonus to Initiative rolls, and after rolling "
            "Initiative you may swap your result with a willing ally's."
        ),
    ),
    Feat.CRAFTER: FeatData(
        feat=Feat.CRAFTER,
        description=(
            "Gain proficiency with three Artisan's Tools of your choice, a 20% "
            "discount when buying nonmagical equipment, and faster crafting "
            "during rests."
        ),
    ),
    Feat.HEALER: FeatData(
        feat=Feat.HEALER,
        description=(
            "Use a Healer's Kit as a Utilize action to let a creature spend one "
            "of its Hit Point Dice plus your Proficiency Bonus, and reroll 1s on "
            "any dice you roll to restore Hit Points."
        ),
    ),
    Feat.LUCKY: FeatData(
        feat=Feat.LUCKY,
        description=(
            "You have Luck Points equal to your Proficiency Bonus, regained on a "
            "Long Rest; spend one to give yourself Advantage on a D20 Test or to "
            "impose Disadvantage on an attack roll against you."
        ),
    ),
    Feat.MAGIC_INITIATE: FeatData(
        feat=Feat.MAGIC_INITIATE,
        description=(
            "Choose the Cleric, Druid, or Wizard spell list: learn two cantrips "
            "and one level 1 spell from it, castable once per Long Rest for free "
            "and with any slots you have."
        ),
        repeatable=True,
    ),
    Feat.MUSICIAN: FeatData(
        feat=Feat.MUSICIAN,
        description=(
            "Gain proficiency with three Musical Instruments and, after a Short "
            "or Long Rest, play a song to grant Heroic Inspiration to allies "
            "(up to your Proficiency Bonus in number)."
        ),
    ),
    Feat.SAVAGE_ATTACKER: FeatData(
        feat=Feat.SAVAGE_ATTACKER,
        description=(
            "Once per turn when you hit with a weapon, roll its damage dice "
            "twice and use either result."
        ),
    ),
    Feat.SKILLED: FeatData(
        feat=Feat.SKILLED,
        description="Gain proficiency in any combination of three skills or tools of your choice.",
        repeatable=True,
    ),
    Feat.TAVERN_BRAWLER: FeatData(
        feat=Feat.TAVERN_BRAWLER,
        description=(
            "Your Unarmed Strikes deal 1d4 damage and you reroll 1s on their "
            "damage; you can shove a creature 5 feet once per turn when you hit "
            "it with an Unarmed Strike, and you have proficiency with improvised "
            "weapons."
        ),
    ),
    Feat.TOUGH: FeatData(
        feat=Feat.TOUGH,
        description=(
            "Your Hit Point maximum increases by 2 per character level, now and "
            "whenever you gain a level."
        ),
    ),
    # ------------------------------------------------------------------
    # General feats
    # ------------------------------------------------------------------
    Feat.ABILITY_SCORE_IMPROVEMENT: FeatData(
        feat=Feat.ABILITY_SCORE_IMPROVEMENT,
        description=(
            "Increase one ability score by 2 or two ability scores by 1 each, "
            "to a maximum of 20."
        ),
        prerequisite="Level 4+",
        repeatable=True,
        ability_increase_options=_ALL_ABILITIES,
    ),
    Feat.ACTOR: FeatData(
        feat=Feat.ACTOR,
        description=(
            "Gain +1 Charisma, Advantage on Deception and Performance checks "
            "made to impersonate someone, and the ability to mimic voices and "
            "sounds you've heard."
        ),
        prerequisite="Level 4+, Charisma 13+",
        ability_increase_options=[Ability.CHARISMA],
    ),
    Feat.ATHLETE: FeatData(
        feat=Feat.ATHLETE,
        description=(
            "Gain +1 Strength or Dexterity, a Climb Speed equal to your Speed, "
            "the ability to stand from Prone with only 5 feet of movement, and "
            "running jumps after just 5 feet."
        ),
        prerequisite="Level 4+, Strength or Dexterity 13+",
        ability_increase_options=_STR_DEX,
    ),
    Feat.CHARGER: FeatData(
        feat=Feat.CHARGER,
        description=(
            "Gain +1 Strength or Dexterity; when you Dash you gain extra Speed, "
            "and once per turn after moving 10+ feet straight toward a target "
            "you can add 1d8 damage or push it 10 feet on a hit."
        ),
        prerequisite="Level 4+, Strength or Dexterity 13+",
        ability_increase_options=_STR_DEX,
    ),
    Feat.CHEF: FeatData(
        feat=Feat.CHEF,
        description=(
            "Gain +1 Constitution or Wisdom and proficiency with Cook's "
            "Utensils; special food you prepare during rests restores extra Hit "
            "Points or grants Temporary Hit Points."
        ),
        prerequisite="Level 4+",
        ability_increase_options=[Ability.CONSTITUTION, Ability.WISDOM],
    ),
    Feat.CROSSBOW_EXPERT: FeatData(
        feat=Feat.CROSSBOW_EXPERT,
        description=(
            "Gain +1 Dexterity; you ignore the Loading property of crossbows, "
            "suffer no Disadvantage for firing within 5 feet of an enemy, and "
            "can add your ability modifier to off-hand crossbow damage with the "
            "Light property."
        ),
        prerequisite="Level 4+, Dexterity 13+",
        ability_increase_options=[Ability.DEXTERITY],
    ),
    Feat.CRUSHER: FeatData(
        feat=Feat.CRUSHER,
        description=(
            "Gain +1 Strength or Constitution; once per turn when you deal "
            "Bludgeoning damage you can move the target 5 feet, and your "
            "critical hits with Bludgeoning damage grant Advantage on attacks "
            "against the target until your next turn."
        ),
        prerequisite="Level 4+",
        ability_increase_options=[Ability.STRENGTH, Ability.CONSTITUTION],
    ),
    Feat.DEFENSIVE_DUELIST: FeatData(
        feat=Feat.DEFENSIVE_DUELIST,
        description=(
            "Gain +1 Dexterity; while wielding a Finesse weapon, use your "
            "Reaction to add your Proficiency Bonus to AC against a melee "
            "attack, possibly turning it into a miss."
        ),
        prerequisite="Level 4+, Dexterity 13+",
        ability_increase_options=[Ability.DEXTERITY],
    ),
    Feat.DUAL_WIELDER: FeatData(
        feat=Feat.DUAL_WIELDER,
        description=(
            "Gain +1 Strength or Dexterity; you can make an extra attack as a "
            "Bonus Action with a different non-Two-Handed weapon while "
            "two-weapon fighting, and you can draw or stow two weapons at once."
        ),
        prerequisite="Level 4+, Strength or Dexterity 13+",
        ability_increase_options=_STR_DEX,
    ),
    Feat.DURABLE: FeatData(
        feat=Feat.DURABLE,
        description=(
            "Gain +1 Constitution, Advantage on Death Saving Throws, and the "
            "ability to spend a Hit Point Die to heal as a Bonus Action."
        ),
        prerequisite="Level 4+",
        ability_increase_options=[Ability.CONSTITUTION],
    ),
    Feat.ELEMENTAL_ADEPT: FeatData(
        feat=Feat.ELEMENTAL_ADEPT,
        description=(
            "Gain +1 Intelligence, Wisdom, or Charisma; choose Acid, Cold, "
            "Fire, Lightning, or Thunder — your spells ignore Resistance to "
            "that type, and you treat 1s on those damage dice as 2s."
        ),
        prerequisite="Level 4+, Spellcasting or Pact Magic feature",
        repeatable=True,
        ability_increase_options=_MENTAL,
    ),
    Feat.FEY_TOUCHED: FeatData(
        feat=Feat.FEY_TOUCHED,
        description=(
            "Gain +1 Intelligence, Wisdom, or Charisma; learn Misty Step and "
            "one level 1 Divination or Enchantment spell, each castable once "
            "per Long Rest for free and with any slots you have."
        ),
        prerequisite="Level 4+",
        ability_increase_options=_MENTAL,
    ),
    Feat.GRAPPLER: FeatData(
        feat=Feat.GRAPPLER,
        description=(
            "Gain +1 Strength or Dexterity; when you hit a creature with an "
            "Unarmed Strike you can damage and grapple it at once, you have "
            "Advantage on attacks against creatures you're grappling, and you "
            "can move grappled creatures of your size or smaller without the "
            "speed penalty."
        ),
        prerequisite="Level 4+, Strength or Dexterity 13+",
        ability_increase_options=_STR_DEX,
    ),
    Feat.GREAT_WEAPON_MASTER: FeatData(
        feat=Feat.GREAT_WEAPON_MASTER,
        description=(
            "Gain +1 Strength; once per turn add your Proficiency Bonus to "
            "damage with a Heavy weapon, and after scoring a critical hit or "
            "dropping a creature to 0 Hit Points you can make one melee attack "
            "as a Bonus Action."
        ),
        prerequisite="Level 4+, Strength 13+",
        ability_increase_options=[Ability.STRENGTH],
    ),
    Feat.HEAVILY_ARMORED: FeatData(
        feat=Feat.HEAVILY_ARMORED,
        description="Gain +1 Strength or Constitution and training with Heavy armor.",
        prerequisite="Level 4+, Medium armor training",
        ability_increase_options=[Ability.STRENGTH, Ability.CONSTITUTION],
    ),
    Feat.HEAVY_ARMOR_MASTER: FeatData(
        feat=Feat.HEAVY_ARMOR_MASTER,
        description=(
            "Gain +1 Strength or Constitution; while wearing Heavy armor, "
            "reduce incoming Bludgeoning, Piercing, and Slashing damage by your "
            "Proficiency Bonus."
        ),
        prerequisite="Level 4+, Heavy armor training",
        ability_increase_options=[Ability.STRENGTH, Ability.CONSTITUTION],
    ),
    Feat.INSPIRING_LEADER: FeatData(
        feat=Feat.INSPIRING_LEADER,
        description=(
            "Gain +1 Wisdom or Charisma; after a rest, give an inspiring speech "
            "to grant up to six creatures Temporary Hit Points equal to your "
            "level plus the chosen ability's modifier."
        ),
        prerequisite="Level 4+, Wisdom or Charisma 13+",
        ability_increase_options=[Ability.WISDOM, Ability.CHARISMA],
    ),
    Feat.KEEN_MIND: FeatData(
        feat=Feat.KEEN_MIND,
        description=(
            "Gain +1 Intelligence, proficiency (or Expertise) in an "
            "Intelligence skill, and the ability to take the Study action as a "
            "Bonus Action."
        ),
        prerequisite="Level 4+",
        ability_increase_options=[Ability.INTELLIGENCE],
    ),
    Feat.LIGHTLY_ARMORED: FeatData(
        feat=Feat.LIGHTLY_ARMORED,
        description=("Gain +1 Strength or Dexterity and training with Light armor and Shields."),
        prerequisite="Level 4+",
        ability_increase_options=_STR_DEX,
    ),
    Feat.MAGE_SLAYER: FeatData(
        feat=Feat.MAGE_SLAYER,
        description=(
            "Gain +1 Strength or Dexterity; creatures you damage have "
            "Disadvantage on Concentration saves, and once per rest you can "
            "turn a failed Intelligence, Wisdom, or Charisma save into a "
            "success."
        ),
        prerequisite="Level 4+",
        ability_increase_options=_STR_DEX,
    ),
    Feat.MARTIAL_WEAPON_TRAINING: FeatData(
        feat=Feat.MARTIAL_WEAPON_TRAINING,
        description="Gain +1 Strength or Dexterity and proficiency with Martial weapons.",
        prerequisite="Level 4+",
        ability_increase_options=_STR_DEX,
    ),
    Feat.MEDIUM_ARMOR_MASTER: FeatData(
        feat=Feat.MEDIUM_ARMOR_MASTER,
        description=(
            "Gain +1 Strength or Dexterity; while wearing Medium armor you can "
            "add up to 3 (rather than 2) of your Dexterity modifier to AC."
        ),
        prerequisite="Level 4+, Medium armor training",
        ability_increase_options=_STR_DEX,
    ),
    Feat.MODERATELY_ARMORED: FeatData(
        feat=Feat.MODERATELY_ARMORED,
        description="Gain +1 Strength or Dexterity and training with Medium armor.",
        prerequisite="Level 4+, Light armor training",
        ability_increase_options=_STR_DEX,
    ),
    Feat.MOUNTED_COMBATANT: FeatData(
        feat=Feat.MOUNTED_COMBATANT,
        description=(
            "Gain +1 Strength, Dexterity, or Wisdom; while mounted you have "
            "Advantage on attacks against unmounted smaller creatures, can "
            "redirect attacks from your mount to yourself, and your mount takes "
            "no damage on successful Dexterity saves for half."
        ),
        prerequisite="Level 4+",
        ability_increase_options=[Ability.STRENGTH, Ability.DEXTERITY, Ability.WISDOM],
    ),
    Feat.OBSERVANT: FeatData(
        feat=Feat.OBSERVANT,
        description=(
            "Gain +1 Intelligence or Wisdom, proficiency (or Expertise) in "
            "Insight, Investigation, or Perception, and the ability to take "
            "the Search action as a Bonus Action."
        ),
        prerequisite="Level 4+",
        ability_increase_options=[Ability.INTELLIGENCE, Ability.WISDOM],
    ),
    Feat.PIERCER: FeatData(
        feat=Feat.PIERCER,
        description=(
            "Gain +1 Strength or Dexterity; once per turn reroll one Piercing "
            "damage die, and your critical hits with Piercing damage roll one "
            "extra damage die."
        ),
        prerequisite="Level 4+",
        ability_increase_options=_STR_DEX,
    ),
    Feat.POISONER: FeatData(
        feat=Feat.POISONER,
        description=(
            "Gain +1 Dexterity or Intelligence; your damage ignores Poison "
            "Resistance, you gain proficiency with the Poisoner's Kit, and you "
            "can brew potent poisons that poison targets who fail a "
            "Constitution save."
        ),
        prerequisite="Level 4+",
        ability_increase_options=[Ability.DEXTERITY, Ability.INTELLIGENCE],
    ),
    Feat.POLEARM_MASTER: FeatData(
        feat=Feat.POLEARM_MASTER,
        description=(
            "Gain +1 Strength or Dexterity; while wielding a polearm such as a "
            "glaive, halberd, or quarterstaff you can make a Bonus Action butt-"
            "end attack (1d4), and creatures provoke an Opportunity Attack from "
            "you when they enter your reach."
        ),
        prerequisite="Level 4+, Strength or Dexterity 13+",
        ability_increase_options=_STR_DEX,
    ),
    Feat.RESILIENT: FeatData(
        feat=Feat.RESILIENT,
        description=(
            "Choose an ability in which you lack saving throw proficiency: "
            "gain +1 to that ability and proficiency in its saving throws."
        ),
        prerequisite="Level 4+",
        ability_increase_options=_ALL_ABILITIES,
    ),
    Feat.RITUAL_CASTER: FeatData(
        feat=Feat.RITUAL_CASTER,
        description=(
            "Gain +1 Intelligence, Wisdom, or Charisma; learn two level 1 "
            "Ritual spells from the Cleric, Druid, or Wizard list, and once per "
            "Long Rest you can cast one of your Rituals without the extra "
            "ritual time."
        ),
        prerequisite="Level 4+, Intelligence, Wisdom, or Charisma 13+",
        ability_increase_options=_MENTAL,
    ),
    Feat.SENTINEL: FeatData(
        feat=Feat.SENTINEL,
        description=(
            "Gain +1 Strength or Dexterity; you can make Opportunity Attacks "
            "against creatures that Disengage or that attack your allies "
            "within your reach, and your Opportunity Attack hits reduce a "
            "creature's Speed to 0 for the turn."
        ),
        prerequisite="Level 4+, Strength or Dexterity 13+",
        ability_increase_options=_STR_DEX,
    ),
    Feat.SHADOW_TOUCHED: FeatData(
        feat=Feat.SHADOW_TOUCHED,
        description=(
            "Gain +1 Intelligence, Wisdom, or Charisma; learn Invisibility and "
            "one level 1 Illusion or Necromancy spell, each castable once per "
            "Long Rest for free and with any slots you have."
        ),
        prerequisite="Level 4+",
        ability_increase_options=_MENTAL,
    ),
    Feat.SHARPSHOOTER: FeatData(
        feat=Feat.SHARPSHOOTER,
        description=(
            "Gain +1 Dexterity; your ranged weapon attacks ignore Half and "
            "Three-Quarters Cover, take no Disadvantage at long range, and take "
            "no Disadvantage from enemies within 5 feet."
        ),
        prerequisite="Level 4+, Dexterity 13+",
        ability_increase_options=[Ability.DEXTERITY],
    ),
    Feat.SHIELD_MASTER: FeatData(
        feat=Feat.SHIELD_MASTER,
        description=(
            "Gain +1 Strength; once per turn when you hit with a melee attack "
            "you can shove a creature with your Shield, and you can interpose "
            "your Shield to take no damage on a successful Dexterity save for "
            "half damage."
        ),
        prerequisite="Level 4+, Shield training",
        ability_increase_options=[Ability.STRENGTH],
    ),
    Feat.SKILL_EXPERT: FeatData(
        feat=Feat.SKILL_EXPERT,
        description=(
            "Gain +1 to one ability score, proficiency in one skill, and "
            "Expertise in a skill in which you're proficient."
        ),
        prerequisite="Level 4+",
        ability_increase_options=_ALL_ABILITIES,
    ),
    Feat.SKULKER: FeatData(
        feat=Feat.SKULKER,
        description=(
            "Gain +1 Dexterity and Blindsight to 10 feet; you can attempt to "
            "Hide while only Lightly Obscured, and missing with a ranged attack "
            "while hidden doesn't reveal your position."
        ),
        prerequisite="Level 4+, Dexterity 13+",
        ability_increase_options=[Ability.DEXTERITY],
    ),
    Feat.SLASHER: FeatData(
        feat=Feat.SLASHER,
        description=(
            "Gain +1 Strength or Dexterity; once per turn when you deal "
            "Slashing damage you can reduce the target's Speed by 10 feet, and "
            "your Slashing critical hits give the target Disadvantage on its "
            "attacks until your next turn."
        ),
        prerequisite="Level 4+",
        ability_increase_options=_STR_DEX,
    ),
    Feat.SPEEDY: FeatData(
        feat=Feat.SPEEDY,
        description=(
            "Gain +1 Dexterity or Constitution, +10 feet of Speed, no movement "
            "penalty from Difficult Terrain when you Dash, and immunity to "
            "Opportunity Attacks from creatures you move away from."
        ),
        prerequisite="Level 4+, Dexterity or Constitution 13+",
        ability_increase_options=[Ability.DEXTERITY, Ability.CONSTITUTION],
    ),
    Feat.SPELL_SNIPER: FeatData(
        feat=Feat.SPELL_SNIPER,
        description=(
            "Gain +1 Intelligence, Wisdom, or Charisma; your spell attacks add "
            "60 feet of range, ignore Half and Three-Quarters Cover, and take "
            "no Disadvantage from enemies within 5 feet."
        ),
        prerequisite="Level 4+, Spellcasting or Pact Magic feature",
        ability_increase_options=_MENTAL,
    ),
    Feat.TELEKINETIC: FeatData(
        feat=Feat.TELEKINETIC,
        description=(
            "Gain +1 Intelligence, Wisdom, or Charisma; learn Mage Hand (cast "
            "invisibly and without components) and gain a Bonus Action "
            "telekinetic shove that moves a creature 5 feet on a failed "
            "Strength save."
        ),
        prerequisite="Level 4+",
        ability_increase_options=_MENTAL,
    ),
    Feat.TELEPATHIC: FeatData(
        feat=Feat.TELEPATHIC,
        description=(
            "Gain +1 Intelligence, Wisdom, or Charisma; speak telepathically to "
            "creatures within 60 feet, and cast Detect Thoughts once per Long "
            "Rest without a slot (and with any slots you have)."
        ),
        prerequisite="Level 4+",
        ability_increase_options=_MENTAL,
    ),
    Feat.WAR_CASTER: FeatData(
        feat=Feat.WAR_CASTER,
        description=(
            "Gain +1 Intelligence, Wisdom, or Charisma, Advantage on "
            "Concentration saves, somatic casting with full hands, and the "
            "option to cast a spell instead of striking when making an "
            "Opportunity Attack."
        ),
        prerequisite="Level 4+, Spellcasting or Pact Magic feature",
        ability_increase_options=_MENTAL,
    ),
    Feat.WEAPON_MASTER: FeatData(
        feat=Feat.WEAPON_MASTER,
        description=(
            "Gain +1 Strength or Dexterity and the ability to use the Mastery "
            "property of one kind of weapon with which you're proficient."
        ),
        prerequisite="Level 4+",
        ability_increase_options=_STR_DEX,
    ),
    # ------------------------------------------------------------------
    # Fighting style feats
    # ------------------------------------------------------------------
    Feat.ARCHERY: FeatData(
        feat=Feat.ARCHERY,
        description="You gain a +2 bonus to attack rolls you make with Ranged weapons.",
        prerequisite="Fighting Style feature",
    ),
    Feat.BLIND_FIGHTING: FeatData(
        feat=Feat.BLIND_FIGHTING,
        description="You gain Blindsight with a range of 10 feet.",
        prerequisite="Fighting Style feature",
    ),
    Feat.DEFENSE: FeatData(
        feat=Feat.DEFENSE,
        description="While wearing Light, Medium, or Heavy armor, you gain +1 to Armor Class.",
        prerequisite="Fighting Style feature",
    ),
    Feat.DUELING: FeatData(
        feat=Feat.DUELING,
        description=(
            "While wielding a melee weapon in one hand with no other weapon, "
            "you gain +2 to that weapon's damage rolls."
        ),
        prerequisite="Fighting Style feature",
    ),
    Feat.GREAT_WEAPON_FIGHTING: FeatData(
        feat=Feat.GREAT_WEAPON_FIGHTING,
        description=(
            "When you roll damage with a melee weapon held in two hands, treat "
            "any 1 or 2 on a damage die as a 3."
        ),
        prerequisite="Fighting Style feature",
    ),
    Feat.INTERCEPTION: FeatData(
        feat=Feat.INTERCEPTION,
        description=(
            "When a creature you can see hits another creature within 5 feet "
            "of you, use your Reaction to reduce the damage by 1d10 plus your "
            "Proficiency Bonus (requires a weapon or Shield)."
        ),
        prerequisite="Fighting Style feature",
    ),
    Feat.PROTECTION: FeatData(
        feat=Feat.PROTECTION,
        description=(
            "While wielding a Shield, use your Reaction to impose Disadvantage "
            "on an attack against a creature within 5 feet of you."
        ),
        prerequisite="Fighting Style feature",
    ),
    Feat.THROWN_WEAPON_FIGHTING: FeatData(
        feat=Feat.THROWN_WEAPON_FIGHTING,
        description=(
            "You gain +2 to damage rolls with weapons that have the Thrown "
            "property when you make ranged attacks with them."
        ),
        prerequisite="Fighting Style feature",
    ),
    Feat.TWO_WEAPON_FIGHTING: FeatData(
        feat=Feat.TWO_WEAPON_FIGHTING,
        description=(
            "When you make the extra attack of two-weapon fighting, you add "
            "your ability modifier to that attack's damage."
        ),
        prerequisite="Fighting Style feature",
    ),
    Feat.UNARMED_FIGHTING: FeatData(
        feat=Feat.UNARMED_FIGHTING,
        description=(
            "Your Unarmed Strikes deal 1d6 + Strength damage (1d8 with both "
            "hands free), and at the start of each of your turns you deal 1d4 "
            "Bludgeoning damage to a creature you're grappling."
        ),
        prerequisite="Fighting Style feature",
    ),
    # ------------------------------------------------------------------
    # Epic boons
    # ------------------------------------------------------------------
    Feat.BOON_OF_COMBAT_PROWESS: FeatData(
        feat=Feat.BOON_OF_COMBAT_PROWESS,
        description=(
            "Increase one ability score by 1 (max 30); once per turn, when you "
            "miss with an attack roll, you can hit instead."
        ),
        prerequisite="Level 19+",
        ability_increase_options=_ALL_ABILITIES,
    ),
    Feat.BOON_OF_DIMENSIONAL_TRAVEL: FeatData(
        feat=Feat.BOON_OF_DIMENSIONAL_TRAVEL,
        description=(
            "Increase one ability score by 1 (max 30); immediately after taking "
            "the Attack or Magic actions, you can teleport up to 30 feet to a "
            "space you can see."
        ),
        prerequisite="Level 19+",
        ability_increase_options=_ALL_ABILITIES,
    ),
    Feat.BOON_OF_ENERGY_RESISTANCE: FeatData(
        feat=Feat.BOON_OF_ENERGY_RESISTANCE,
        description=(
            "Increase one ability score by 1 (max 30); gain Resistance to two "
            "damage types of your choice (changeable on a Long Rest), and you "
            "can use a Reaction to redirect resisted energy damage at a nearby "
            "creature."
        ),
        prerequisite="Level 19+",
        ability_increase_options=_ALL_ABILITIES,
    ),
    Feat.BOON_OF_FATE: FeatData(
        feat=Feat.BOON_OF_FATE,
        description=(
            "Increase one ability score by 1 (max 30); when a creature within "
            "60 feet succeeds or fails a D20 Test, you can roll 2d4 and add or "
            "subtract the total, recharging on Initiative or a rest."
        ),
        prerequisite="Level 19+",
        ability_increase_options=_ALL_ABILITIES,
    ),
    Feat.BOON_OF_FORTITUDE: FeatData(
        feat=Feat.BOON_OF_FORTITUDE,
        description=(
            "Increase one ability score by 1 (max 30); your Hit Point maximum "
            "increases by 40, and whenever you regain Hit Points you regain an "
            "extra 10 (once per turn)."
        ),
        prerequisite="Level 19+",
        ability_increase_options=_ALL_ABILITIES,
    ),
    Feat.BOON_OF_IRRESISTIBLE_OFFENSE: FeatData(
        feat=Feat.BOON_OF_IRRESISTIBLE_OFFENSE,
        description=(
            "Increase Strength or Dexterity by 1 (max 30); your Bludgeoning, "
            "Piercing, and Slashing damage ignores Resistance, and rolling a "
            "natural 20 on an attack adds bonus damage equal to the raised "
            "score."
        ),
        prerequisite="Level 19+",
        ability_increase_options=_STR_DEX,
    ),
    Feat.BOON_OF_RECOVERY: FeatData(
        feat=Feat.BOON_OF_RECOVERY,
        description=(
            "Increase one ability score by 1 (max 30); once per Long Rest, when "
            "you would drop to 0 Hit Points, drop to half your maximum instead, "
            "and you can spend pooled Recovery dice as a Bonus Action to heal."
        ),
        prerequisite="Level 19+",
        ability_increase_options=_ALL_ABILITIES,
    ),
    Feat.BOON_OF_SKILL: FeatData(
        feat=Feat.BOON_OF_SKILL,
        description=(
            "Increase one ability score by 1 (max 30); you gain proficiency in "
            "every skill and Expertise in one skill of your choice."
        ),
        prerequisite="Level 19+",
        ability_increase_options=_ALL_ABILITIES,
    ),
    Feat.BOON_OF_SPEED: FeatData(
        feat=Feat.BOON_OF_SPEED,
        description=(
            "Increase one ability score by 1 (max 30); your Speed increases by "
            "30 feet, and as a Bonus Action you can end the Grappled condition "
            "on yourself."
        ),
        prerequisite="Level 19+",
        ability_increase_options=_ALL_ABILITIES,
    ),
    Feat.BOON_OF_SPELL_RECALL: FeatData(
        feat=Feat.BOON_OF_SPELL_RECALL,
        description=(
            "Increase Intelligence, Wisdom, or Charisma by 1 (max 30); whenever "
            "you cast a spell with a level 1-4 slot, roll 1d4 — if the roll "
            "matches the slot's level, the slot isn't expended."
        ),
        prerequisite="Level 19+, Spellcasting feature",
        ability_increase_options=_MENTAL,
    ),
    Feat.BOON_OF_THE_NIGHT_SPIRIT: FeatData(
        feat=Feat.BOON_OF_THE_NIGHT_SPIRIT,
        description=(
            "Increase one ability score by 1 (max 30); while in Dim Light or "
            "Darkness you can become Invisible as a Bonus Action and you have "
            "Resistance to all damage except Psychic and Radiant."
        ),
        prerequisite="Level 19+",
        ability_increase_options=_ALL_ABILITIES,
    ),
    Feat.BOON_OF_TRUESIGHT: FeatData(
        feat=Feat.BOON_OF_TRUESIGHT,
        description="Increase one ability score by 1 (max 30); you gain Truesight to 60 feet.",
        prerequisite="Level 19+",
        ability_increase_options=_ALL_ABILITIES,
    ),
}


def get_feat(feat: Feat) -> FeatData | None:
    """Look up feat data; None if not registered."""
    return FEATS.get(feat)
