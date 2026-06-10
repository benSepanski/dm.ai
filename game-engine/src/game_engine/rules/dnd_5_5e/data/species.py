"""D&D 5.5e species data (SRD 5.2 / 2024 PHB chapter 4)."""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import CreatureSize, CreatureType, DamageType, Species


@dataclass(frozen=True)
class SpeciesTraitData:
    """A named species trait with display text."""

    name: str
    description: str


@dataclass(frozen=True)
class SpeciesData:
    """Typed species definition."""

    species: Species
    creature_type: CreatureType
    size_options: list[CreatureSize]
    speed: int
    darkvision_ft: int
    traits: list[SpeciesTraitData] = field(default_factory=list)
    damage_resistances: list[DamageType] = field(default_factory=list)
    description: str = ""


SPECIES: dict[Species, SpeciesData] = {
    Species.DWARF: SpeciesData(
        species=Species.DWARF,
        creature_type=CreatureType.HUMANOID,
        size_options=[CreatureSize.MEDIUM],
        speed=30,
        darkvision_ft=120,
        traits=[
            SpeciesTraitData(
                name="Dwarven Resilience",
                description=(
                    "You have Advantage on saving throws you make to avoid or "
                    "end the Poisoned condition."
                ),
            ),
            SpeciesTraitData(
                name="Dwarven Toughness",
                description=(
                    "Your Hit Point maximum increases by 1 and grows by another "
                    "1 each time you gain a level."
                ),
            ),
            SpeciesTraitData(
                name="Stonecunning",
                description=(
                    "As a Bonus Action while on a stone surface or touching one, "
                    "you gain Tremorsense with a range of 60 feet for 10 minutes; "
                    "usable a number of times equal to your Proficiency Bonus per "
                    "Long Rest."
                ),
            ),
        ],
        damage_resistances=[DamageType.POISON],
        description=(
            "Stout, long-lived folk of mountain and hill, dwarves combine hardy "
            "constitutions with an uncanny sense for stone and earth."
        ),
    ),
    Species.ELF: SpeciesData(
        species=Species.ELF,
        creature_type=CreatureType.HUMANOID,
        size_options=[CreatureSize.MEDIUM],
        speed=30,
        darkvision_ft=60,
        traits=[
            SpeciesTraitData(
                name="Elven Lineage",
                description=(
                    "Choose a lineage (Drow, High Elf, or Wood Elf) that grants "
                    "an extra benefit at level 1 and additional spells at levels "
                    "3 and 5."
                ),
            ),
            SpeciesTraitData(
                name="Fey Ancestry",
                description=(
                    "You have Advantage on saving throws you make to avoid or "
                    "end the Charmed condition."
                ),
            ),
            SpeciesTraitData(
                name="Keen Senses",
                description=(
                    "You gain proficiency in Insight, Perception, or Survival " "(your choice)."
                ),
            ),
            SpeciesTraitData(
                name="Trance",
                description=(
                    "You don't need sleep and magic can't put you to sleep; a "
                    "Long Rest takes you only 4 hours spent in a meditative trance."
                ),
            ),
        ],
        description=(
            "Graceful and long-lived people with ties to the Feywild, elves "
            "perceive the world with senses sharpened by centuries of memory."
        ),
    ),
    Species.HUMAN: SpeciesData(
        species=Species.HUMAN,
        creature_type=CreatureType.HUMANOID,
        size_options=[CreatureSize.MEDIUM, CreatureSize.SMALL],
        speed=30,
        darkvision_ft=0,
        traits=[
            SpeciesTraitData(
                name="Resourceful",
                description="You regain Heroic Inspiration whenever you finish a Long Rest.",
            ),
            SpeciesTraitData(
                name="Skillful",
                description="You gain proficiency in one skill of your choice.",
            ),
            SpeciesTraitData(
                name="Versatile",
                description="You gain an Origin feat of your choice.",
            ),
        ],
        description=(
            "Adaptable and ambitious, humans thrive in every land, making up "
            "for short lives with drive, ingenuity, and broad talents."
        ),
    ),
    Species.DRAGONBORN: SpeciesData(
        species=Species.DRAGONBORN,
        creature_type=CreatureType.HUMANOID,
        size_options=[CreatureSize.MEDIUM],
        speed=30,
        darkvision_ft=60,
        traits=[
            SpeciesTraitData(
                name="Draconic Ancestry",
                description=(
                    "Choose a dragon ancestor; it determines the damage type of "
                    "your Breath Weapon and Damage Resistance traits."
                ),
            ),
            SpeciesTraitData(
                name="Breath Weapon",
                description=(
                    "Replace one attack with a 15-foot cone or 30-foot line exhalation "
                    "dealing 1d10 damage of your ancestry's type (Dexterity save for "
                    "half); damage grows at higher levels, usable Proficiency Bonus "
                    "times per Long Rest."
                ),
            ),
            SpeciesTraitData(
                name="Damage Resistance",
                description="You have Resistance to the damage type of your draconic ancestry.",
            ),
            SpeciesTraitData(
                name="Draconic Flight",
                description=(
                    "Starting at level 5, as a Bonus Action you can sprout spectral "
                    "wings granting a Fly Speed equal to your Speed for 10 minutes, "
                    "once per Long Rest."
                ),
            ),
        ],
        description=(
            "Proud descendants of dragons, dragonborn carry the elemental power "
            "of their ancestors in scale, breath, and bearing."
        ),
    ),
    Species.GNOME: SpeciesData(
        species=Species.GNOME,
        creature_type=CreatureType.HUMANOID,
        size_options=[CreatureSize.SMALL],
        speed=30,
        darkvision_ft=60,
        traits=[
            SpeciesTraitData(
                name="Gnomish Cunning",
                description=(
                    "You have Advantage on Intelligence, Wisdom, and Charisma " "saving throws."
                ),
            ),
            SpeciesTraitData(
                name="Gnomish Lineage",
                description=(
                    "Choose a lineage (Forest Gnome or Rock Gnome) that grants "
                    "innate magic such as minor illusions or mending and tinkering "
                    "tricks."
                ),
            ),
        ],
        description=(
            "Small, inventive, and irrepressibly curious, gnomes pair quick "
            "minds with a streak of innate magic."
        ),
    ),
    Species.GOLIATH: SpeciesData(
        species=Species.GOLIATH,
        creature_type=CreatureType.HUMANOID,
        size_options=[CreatureSize.MEDIUM],
        speed=35,
        darkvision_ft=0,
        traits=[
            SpeciesTraitData(
                name="Giant Ancestry",
                description=(
                    "Choose a giant ancestor that grants a supernatural boon "
                    "(such as Stone's Endurance or Fire's Burn), usable "
                    "Proficiency Bonus times per Long Rest."
                ),
            ),
            SpeciesTraitData(
                name="Large Form",
                description=(
                    "Starting at level 5, as a Bonus Action you can become Large "
                    "for 10 minutes, gaining Advantage on Strength checks and +10 "
                    "feet of Speed, once per Long Rest."
                ),
            ),
            SpeciesTraitData(
                name="Powerful Build",
                description=(
                    "You have Advantage on saving throws to end the Grappled "
                    "condition, and you count as one size larger for carrying "
                    "capacity."
                ),
            ),
        ],
        description=(
            "Towering kin of the giants, goliaths stride mountain paths with "
            "long legs and the strength of their ancestral lines."
        ),
    ),
    Species.HALFLING: SpeciesData(
        species=Species.HALFLING,
        creature_type=CreatureType.HUMANOID,
        size_options=[CreatureSize.SMALL],
        speed=30,
        darkvision_ft=0,
        traits=[
            SpeciesTraitData(
                name="Brave",
                description=(
                    "You have Advantage on saving throws you make to avoid or "
                    "end the Frightened condition."
                ),
            ),
            SpeciesTraitData(
                name="Halfling Nimbleness",
                description=(
                    "You can move through the space of any creature that is a "
                    "size larger than you, though you can't stop there."
                ),
            ),
            SpeciesTraitData(
                name="Luck",
                description=(
                    "When you roll a 1 on the d20 of a D20 Test, you can reroll "
                    "the die and must use the new roll."
                ),
            ),
            SpeciesTraitData(
                name="Naturally Stealthy",
                description=(
                    "You can take the Hide action even when obscured only by a "
                    "creature at least one size larger than you."
                ),
            ),
        ],
        description=(
            "Cheerful, hospitable wanderers of small stature, halflings slip "
            "through danger on quick feet and uncanny good fortune."
        ),
    ),
    Species.ORC: SpeciesData(
        species=Species.ORC,
        creature_type=CreatureType.HUMANOID,
        size_options=[CreatureSize.MEDIUM],
        speed=30,
        darkvision_ft=120,
        traits=[
            SpeciesTraitData(
                name="Adrenaline Rush",
                description=(
                    "You can take the Dash action as a Bonus Action; when you do, "
                    "you gain Temporary Hit Points equal to your Proficiency Bonus. "
                    "Usable Proficiency Bonus times per Short or Long Rest."
                ),
            ),
            SpeciesTraitData(
                name="Relentless Endurance",
                description=(
                    "When reduced to 0 Hit Points without being killed outright, "
                    "you drop to 1 Hit Point instead, once per Long Rest."
                ),
            ),
        ],
        description=(
            "Hardy and determined, orcs draw on surging adrenaline and sheer "
            "endurance to push through wounds that would fell others."
        ),
    ),
    Species.TIEFLING: SpeciesData(
        species=Species.TIEFLING,
        creature_type=CreatureType.HUMANOID,
        size_options=[CreatureSize.MEDIUM, CreatureSize.SMALL],
        speed=30,
        darkvision_ft=60,
        traits=[
            SpeciesTraitData(
                name="Fiendish Legacy",
                description=(
                    "Choose a legacy (Abyssal, Chthonic, or Infernal) that grants "
                    "Resistance to an associated damage type and spells at levels "
                    "1, 3, and 5."
                ),
            ),
            SpeciesTraitData(
                name="Otherworldly Presence",
                description=(
                    "You know the Thaumaturgy cantrip, cast with the spellcasting "
                    "ability chosen for your Fiendish Legacy."
                ),
            ),
        ],
        description=(
            "Marked by a fiendish bloodline, tieflings channel the magic of "
            "their otherworldly heritage through horns, tails, and arcane gifts."
        ),
    ),
}


def get_species(species: Species) -> SpeciesData | None:
    """Look up species data; None if not registered."""
    return SPECIES.get(species)
