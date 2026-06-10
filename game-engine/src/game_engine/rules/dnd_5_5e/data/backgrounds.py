"""D&D 5.5e background data (2024 PHB chapter 4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import Ability, Background, Feat, Skill


@dataclass(frozen=True)
class BackgroundData:
    """Typed background definition (2024 PHB).

    ``ability_scores`` are the three abilities the background can
    increase (+2/+1 or +1/+1/+1 split chosen at creation).
    """

    background: Background
    ability_scores: list[Ability]
    skill_proficiencies: list[Skill]
    tool_proficiency: str
    origin_feat: Feat
    equipment: list[str] = field(default_factory=list)
    description: str = ""


BACKGROUNDS: dict[Background, BackgroundData] = {
    Background.ACOLYTE: BackgroundData(
        background=Background.ACOLYTE,
        ability_scores=[Ability.INTELLIGENCE, Ability.WISDOM, Ability.CHARISMA],
        skill_proficiencies=[Skill.INSIGHT, Skill.RELIGION],
        tool_proficiency="Calligrapher's Supplies",
        origin_feat=Feat.MAGIC_INITIATE,
        equipment=[
            "Calligrapher's Supplies",
            "Holy Symbol",
            "Book (prayers)",
            "Parchment (10 sheets)",
            "Robe",
            "8 gp",
        ],
        description=(
            "You served in a temple, learning sacred rites and the first "
            "stirrings of divine magic."
        ),
    ),
    Background.ARTISAN: BackgroundData(
        background=Background.ARTISAN,
        ability_scores=[Ability.STRENGTH, Ability.DEXTERITY, Ability.INTELLIGENCE],
        skill_proficiencies=[Skill.INVESTIGATION, Skill.PERSUASION],
        tool_proficiency="Artisan's Tools (choice)",
        origin_feat=Feat.CRAFTER,
        equipment=[
            "Artisan's Tools (choice)",
            "Pouch (2)",
            "Traveler's Clothes",
            "32 gp",
        ],
        description=(
            "You apprenticed in a workshop, mastering a craft and the patient "
            "eye for detail that comes with it."
        ),
    ),
    Background.CHARLATAN: BackgroundData(
        background=Background.CHARLATAN,
        ability_scores=[Ability.DEXTERITY, Ability.CONSTITUTION, Ability.CHARISMA],
        skill_proficiencies=[Skill.DECEPTION, Skill.SLEIGHT_OF_HAND],
        tool_proficiency="Forgery Kit",
        origin_feat=Feat.SKILLED,
        equipment=[
            "Forgery Kit",
            "Costume",
            "Fine Clothes",
            "15 gp",
        ],
        description=(
            "You made your living on cons and forged papers, learning to read "
            "marks and talk your way out of anything."
        ),
    ),
    Background.CRIMINAL: BackgroundData(
        background=Background.CRIMINAL,
        ability_scores=[Ability.DEXTERITY, Ability.CONSTITUTION, Ability.INTELLIGENCE],
        skill_proficiencies=[Skill.SLEIGHT_OF_HAND, Skill.STEALTH],
        tool_proficiency="Thieves' Tools",
        origin_feat=Feat.ALERT,
        equipment=[
            "Dagger (2)",
            "Thieves' Tools",
            "Crowbar",
            "Pouch (2)",
            "Traveler's Clothes",
            "16 gp",
        ],
        description=(
            "You ran with the underworld, where quick hands, quiet feet, and "
            "constant vigilance kept you alive."
        ),
    ),
    Background.ENTERTAINER: BackgroundData(
        background=Background.ENTERTAINER,
        ability_scores=[Ability.STRENGTH, Ability.DEXTERITY, Ability.CHARISMA],
        skill_proficiencies=[Skill.ACROBATICS, Skill.PERFORMANCE],
        tool_proficiency="Musical Instrument (choice)",
        origin_feat=Feat.MUSICIAN,
        equipment=[
            "Musical Instrument (choice)",
            "Costume (2)",
            "Mirror",
            "Perfume",
            "Traveler's Clothes",
            "11 gp",
        ],
        description=(
            "You toured taverns and fairs, captivating crowds with music, "
            "tumbling, and showmanship."
        ),
    ),
    Background.FARMER: BackgroundData(
        background=Background.FARMER,
        ability_scores=[Ability.STRENGTH, Ability.CONSTITUTION, Ability.WISDOM],
        skill_proficiencies=[Skill.ANIMAL_HANDLING, Skill.NATURE],
        tool_proficiency="Carpenter's Tools",
        origin_feat=Feat.TOUGH,
        equipment=[
            "Sickle",
            "Carpenter's Tools",
            "Healer's Kit",
            "Iron Pot",
            "Shovel",
            "30 gp",
        ],
        description=(
            "Seasons of hard labor in field and barn gave you a sturdy frame "
            "and an instinct for living things."
        ),
    ),
    Background.GUARD: BackgroundData(
        background=Background.GUARD,
        ability_scores=[Ability.STRENGTH, Ability.INTELLIGENCE, Ability.WISDOM],
        skill_proficiencies=[Skill.ATHLETICS, Skill.PERCEPTION],
        tool_proficiency="Gaming Set (choice)",
        origin_feat=Feat.ALERT,
        equipment=[
            "Spear",
            "Light Crossbow",
            "Bolts (20)",
            "Gaming Set (choice)",
            "Hooded Lantern",
            "Manacles",
            "Quiver",
            "Traveler's Clothes",
            "12 gp",
        ],
        description=(
            "Long watches on wall and gate taught you to spot trouble early "
            "and stand your ground when it arrives."
        ),
    ),
    Background.GUIDE: BackgroundData(
        background=Background.GUIDE,
        ability_scores=[Ability.DEXTERITY, Ability.CONSTITUTION, Ability.WISDOM],
        skill_proficiencies=[Skill.STEALTH, Skill.SURVIVAL],
        tool_proficiency="Cartographer's Tools",
        origin_feat=Feat.MAGIC_INITIATE,
        equipment=[
            "Shortbow",
            "Arrows (20)",
            "Cartographer's Tools",
            "Bedroll",
            "Quiver",
            "Tent",
            "Traveler's Clothes",
            "3 gp",
        ],
        description=(
            "You came of age in the wilds, leading travelers along hidden "
            "paths and brushing against the magic of untamed places."
        ),
    ),
    Background.HERMIT: BackgroundData(
        background=Background.HERMIT,
        ability_scores=[Ability.CONSTITUTION, Ability.WISDOM, Ability.CHARISMA],
        skill_proficiencies=[Skill.MEDICINE, Skill.RELIGION],
        tool_proficiency="Herbalism Kit",
        origin_feat=Feat.HEALER,
        equipment=[
            "Quarterstaff",
            "Herbalism Kit",
            "Bedroll",
            "Book (philosophy)",
            "Lamp",
            "Oil (3 flasks)",
            "Traveler's Clothes",
            "16 gp",
        ],
        description=(
            "Years of solitude spent in contemplation and tending your own "
            "hurts made you a healer of body and spirit."
        ),
    ),
    Background.MERCHANT: BackgroundData(
        background=Background.MERCHANT,
        ability_scores=[Ability.CONSTITUTION, Ability.INTELLIGENCE, Ability.CHARISMA],
        skill_proficiencies=[Skill.ANIMAL_HANDLING, Skill.PERSUASION],
        tool_proficiency="Navigator's Tools",
        origin_feat=Feat.LUCKY,
        equipment=[
            "Navigator's Tools",
            "Pouch (2)",
            "Traveler's Clothes",
            "22 gp",
        ],
        description=(
            "You traveled trade routes buying low and selling high, trusting "
            "charm and a touch of luck to close every deal."
        ),
    ),
    Background.NOBLE: BackgroundData(
        background=Background.NOBLE,
        ability_scores=[Ability.STRENGTH, Ability.INTELLIGENCE, Ability.CHARISMA],
        skill_proficiencies=[Skill.HISTORY, Skill.PERSUASION],
        tool_proficiency="Gaming Set (choice)",
        origin_feat=Feat.SKILLED,
        equipment=[
            "Gaming Set (choice)",
            "Fine Clothes",
            "Perfume",
            "29 gp",
        ],
        description=(
            "Raised among courtly intrigue, you learned history, etiquette, "
            "and how to bend conversations to your favor."
        ),
    ),
    Background.SAGE: BackgroundData(
        background=Background.SAGE,
        ability_scores=[Ability.CONSTITUTION, Ability.INTELLIGENCE, Ability.WISDOM],
        skill_proficiencies=[Skill.ARCANA, Skill.HISTORY],
        tool_proficiency="Calligrapher's Supplies",
        origin_feat=Feat.MAGIC_INITIATE,
        equipment=[
            "Quarterstaff",
            "Calligrapher's Supplies",
            "Book (history)",
            "Parchment (8 sheets)",
            "Robe",
            "8 gp",
        ],
        description=(
            "You spent years among books and scholars, absorbing lore of the "
            "arcane and ages past."
        ),
    ),
    Background.SAILOR: BackgroundData(
        background=Background.SAILOR,
        ability_scores=[Ability.STRENGTH, Ability.DEXTERITY, Ability.WISDOM],
        skill_proficiencies=[Skill.ACROBATICS, Skill.PERCEPTION],
        tool_proficiency="Navigator's Tools",
        origin_feat=Feat.TAVERN_BRAWLER,
        equipment=[
            "Dagger",
            "Navigator's Tools",
            "Rope",
            "Traveler's Clothes",
            "20 gp",
        ],
        description=(
            "Life aboard ship gave you sure footing on swaying decks and a "
            "habit of settling disputes with your fists."
        ),
    ),
    Background.SCRIBE: BackgroundData(
        background=Background.SCRIBE,
        ability_scores=[Ability.DEXTERITY, Ability.INTELLIGENCE, Ability.WISDOM],
        skill_proficiencies=[Skill.INVESTIGATION, Skill.PERCEPTION],
        tool_proficiency="Calligrapher's Supplies",
        origin_feat=Feat.SKILLED,
        equipment=[
            "Calligrapher's Supplies",
            "Fine Clothes",
            "Lamp",
            "Oil (3 flasks)",
            "Parchment (12 sheets)",
            "23 gp",
        ],
        description=(
            "You worked in a scriptorium copying records and contracts, "
            "developing a sharp eye for errors and hidden details."
        ),
    ),
    Background.SOLDIER: BackgroundData(
        background=Background.SOLDIER,
        ability_scores=[Ability.STRENGTH, Ability.DEXTERITY, Ability.CONSTITUTION],
        skill_proficiencies=[Skill.ATHLETICS, Skill.INTIMIDATION],
        tool_proficiency="Gaming Set (choice)",
        origin_feat=Feat.SAVAGE_ATTACKER,
        equipment=[
            "Spear",
            "Shortbow",
            "Arrows (20)",
            "Gaming Set (choice)",
            "Healer's Kit",
            "Quiver",
            "Traveler's Clothes",
            "14 gp",
        ],
        description=(
            "Drilled in camp and tested in battle, you know how to strike "
            "hard and keep marching."
        ),
    ),
    Background.WAYFARER: BackgroundData(
        background=Background.WAYFARER,
        ability_scores=[Ability.DEXTERITY, Ability.WISDOM, Ability.CHARISMA],
        skill_proficiencies=[Skill.INSIGHT, Skill.STEALTH],
        tool_proficiency="Thieves' Tools",
        origin_feat=Feat.LUCKY,
        equipment=[
            "Dagger (2)",
            "Thieves' Tools",
            "Gaming Set (choice)",
            "Bedroll",
            "Pouch (2)",
            "Traveler's Clothes",
            "16 gp",
        ],
        description=(
            "You grew up on the streets and the road with no place to call "
            "home, surviving on wit, stealth, and fortune's favor."
        ),
    ),
}


def get_background(background: Background) -> BackgroundData | None:
    """Look up background data; None if not registered."""
    return BACKGROUNDS.get(background)
