# NOTE: exceeds 400 LoC — single cohesive data module
"""D&D 5.5e adventuring gear, tools, and equipment packs (2024 PHB ch. 6)."""

from __future__ import annotations

from dataclasses import dataclass, field

from game_engine.types import Ability


@dataclass(frozen=True)
class GearData:
    """A piece of adventuring gear."""

    name: str
    cost_gp: float
    weight_lb: float
    description: str


@dataclass(frozen=True)
class ToolData:
    """An artisan's tool or other tool, with its governing ability."""

    name: str
    cost_gp: float
    weight_lb: float
    ability: Ability
    description: str


@dataclass(frozen=True)
class PackData:
    """An equipment pack and its contents (item names reference GEAR)."""

    name: str
    cost_gp: float
    contents: list[str] = field(default_factory=list)


GEAR: list[GearData] = [
    GearData("Acid", 25.0, 1.0, "A vial of corrosive liquid that can be thrown at a target."),
    GearData(
        "Alchemist's Fire",
        50.0,
        1.0,
        "A flask of sticky, volatile fluid that ignites when exposed to air.",
    ),
    GearData("Antitoxin", 50.0, 0.0, "A vial of cloudy tonic that fortifies against poison."),
    GearData(
        "Arcane Focus", 10.0, 1.0, "A crystal, orb, rod, staff, or wand for channeling spells."
    ),
    GearData("Arrows", 1.0, 1.0, "A bundle of twenty arrows for bows."),
    GearData("Backpack", 2.0, 5.0, "A leather pack with straps, holding up to 30 pounds of gear."),
    GearData(
        "Ball Bearings", 1.0, 2.0, "A pouch of a thousand tiny metal spheres to scatter underfoot."
    ),
    GearData("Bedroll", 1.0, 7.0, "A padded sleeping roll that keeps out the night chill."),
    GearData("Bell", 1.0, 0.0, "A small brass bell that rings clearly when shaken."),
    GearData("Blanket", 0.5, 3.0, "A thick woolen blanket for warmth on the road."),
    GearData(
        "Block and Tackle", 1.0, 5.0, "A pulley rig that lets you hoist four times your lift."
    ),
    GearData("Bolts", 1.0, 1.5, "A case of twenty crossbow bolts."),
    GearData("Book", 25.0, 5.0, "A bound volume of lore, poetry, or history."),
    GearData("Bullets, Firearm", 3.0, 2.0, "Ten lead balls sized for musket or pistol."),
    GearData("Bullets, Sling", 0.04, 1.5, "Twenty smooth stones shaped for a sling."),
    GearData("Caltrops", 1.0, 2.0, "A bag of twenty spiked jacks that always land point-upward."),
    GearData("Candle", 0.01, 0.0, "A tallow candle that burns for one hour, shedding dim light."),
    GearData("Chain", 5.0, 10.0, "Ten feet of sturdy iron links."),
    GearData("Chest", 5.0, 25.0, "A wooden strongbox with an iron clasp, holding 12 cubic feet."),
    GearData(
        "Component Pouch",
        25.0,
        2.0,
        "A belt pouch with compartments for spell components.",
    ),
    GearData("Costume", 5.0, 4.0, "Theatrical clothing suited to a particular role."),
    GearData("Crowbar", 2.0, 5.0, "An iron pry bar that grants leverage for forcing things open."),
    GearData("Fine Clothes", 15.0, 6.0, "Elegant garments cut to impress at court."),
    GearData("Grappling Hook", 2.0, 4.0, "A barbed iron hook made to snag ledges and rigging."),
    GearData("Hammer", 1.0, 3.0, "A one-handed maul for driving pitons and nails."),
    GearData(
        "Healer's Kit", 5.0, 3.0, "Bandages and salves with ten uses to stabilize the dying."
    ),
    GearData("Holy Symbol", 5.0, 1.0, "An emblem of a deity used as a divine spellcasting focus."),
    GearData("Holy Water", 25.0, 1.0, "A blessed flask that sears undead and fiends."),
    GearData("Ink", 10.0, 0.0, "A small bottle of black writing ink."),
    GearData("Ink Pen", 0.02, 0.0, "A carved wooden pen with a metal nib."),
    GearData("Lamp", 0.5, 1.0, "An oil lamp casting bright light in a 15-foot radius."),
    GearData("Lantern, Bullseye", 10.0, 2.0, "A hooded lamp that throws a 60-foot cone of light."),
    GearData(
        "Lantern, Hooded", 5.0, 2.0, "A shuttered lantern shedding light in a 30-foot radius."
    ),
    GearData("Lock", 10.0, 1.0, "An iron lock with a key; DC 15 to pick without it."),
    GearData("Manacles", 2.0, 6.0, "Iron restraints sized for Small or Medium creatures."),
    GearData("Map", 1.0, 0.0, "A drawn chart of a region, city, or dungeon."),
    GearData("Mirror", 5.0, 0.5, "A polished steel hand mirror."),
    GearData("Needles", 1.0, 1.0, "Fifty slender darts sized for a blowgun."),
    GearData("Oil", 0.1, 1.0, "A clay flask of lamp oil; slick when spilled, fierce when lit."),
    GearData("Paper", 0.2, 0.0, "One crisp sheet of pressed paper."),
    GearData("Parchment", 0.1, 0.0, "One sheet of scraped and dried hide for writing."),
    GearData("Perfume", 5.0, 0.0, "A vial of fragrant scent favored by diplomats."),
    GearData("Piton", 0.05, 0.25, "An iron spike that anchors a rope when hammered into rock."),
    GearData("Pole", 0.05, 7.0, "A 10-foot wooden pole for prodding suspicious flagstones."),
    GearData("Potion of Healing", 50.0, 0.5, "A red draught that restores 2d4 + 2 hit points."),
    GearData("Pouch", 0.5, 1.0, "A small belt pouch that holds up to 6 pounds."),
    GearData("Quiver", 1.0, 1.0, "A leather case that holds up to 20 arrows."),
    GearData("Rations", 0.5, 2.0, "One day of dry travel food: jerky, hardtack, and fruit."),
    GearData("Robe", 1.0, 4.0, "A loose hooded garment of plain cloth."),
    GearData("Rope", 1.0, 5.0, "Fifty feet of strong hempen rope; burst DC 20."),
    GearData("Sack", 0.01, 0.5, "A cloth bag that holds up to 30 pounds."),
    GearData("Shovel", 2.0, 5.0, "A sturdy spade for digging through earth."),
    GearData("Spellbook", 50.0, 3.0, "A leather-bound tome of one hundred blank vellum pages."),
    GearData("Tent", 2.0, 20.0, "A two-person canvas shelter with poles and stakes."),
    GearData("Tinderbox", 0.5, 1.0, "Flint, steel, and tinder for kindling a fire."),
    GearData("Torch", 0.01, 1.0, "A pitch-soaked brand that burns for one hour."),
    GearData("Vial", 1.0, 0.0, "A small glass vessel that holds 4 ounces of liquid."),
    GearData("Waterskin", 0.2, 5.0, "A leather skin holding four pints of water."),
]

TOOLS: list[ToolData] = [
    # --- Artisan's tools ---
    ToolData(
        "Alchemist's Supplies",
        50.0,
        8.0,
        Ability.INTELLIGENCE,
        "Beakers and reagents for identifying and brewing substances.",
    ),
    ToolData(
        "Brewer's Supplies",
        20.0,
        9.0,
        Ability.INTELLIGENCE,
        "Kettles and casks for fermenting ales and detecting tainted drink.",
    ),
    ToolData(
        "Calligrapher's Supplies",
        10.0,
        5.0,
        Ability.DEXTERITY,
        "Fine pens and inks for elegant scripts and spotting forgeries.",
    ),
    ToolData(
        "Carpenter's Tools",
        8.0,
        6.0,
        Ability.STRENGTH,
        "Saws, hammers, and chisels for building wooden structures.",
    ),
    ToolData(
        "Cartographer's Tools",
        15.0,
        6.0,
        Ability.WISDOM,
        "Quills, compasses, and vellum for drafting accurate maps.",
    ),
    ToolData(
        "Cobbler's Tools",
        5.0,
        5.0,
        Ability.DEXTERITY,
        "Awls and lasts for crafting and mending footwear.",
    ),
    ToolData(
        "Cook's Utensils",
        1.0,
        8.0,
        Ability.WISDOM,
        "Pots and knives for preparing hearty, morale-lifting meals.",
    ),
    ToolData(
        "Glassblower's Tools",
        30.0,
        5.0,
        Ability.INTELLIGENCE,
        "Pipes and tongs for shaping molten glass.",
    ),
    ToolData(
        "Jeweler's Tools",
        25.0,
        2.0,
        Ability.INTELLIGENCE,
        "Loupes and pliers for cutting gems and appraising treasure.",
    ),
    ToolData(
        "Leatherworker's Tools",
        5.0,
        5.0,
        Ability.DEXTERITY,
        "Knives and punches for working hides into goods.",
    ),
    ToolData(
        "Mason's Tools",
        10.0,
        8.0,
        Ability.STRENGTH,
        "Trowels and chisels for shaping and judging stonework.",
    ),
    ToolData(
        "Painter's Supplies",
        10.0,
        5.0,
        Ability.WISDOM,
        "Brushes and pigments for portraits and murals.",
    ),
    ToolData(
        "Potter's Tools",
        10.0,
        3.0,
        Ability.INTELLIGENCE,
        "A wheel and ribs for throwing and firing clay vessels.",
    ),
    ToolData(
        "Smith's Tools",
        20.0,
        8.0,
        Ability.STRENGTH,
        "Hammers and tongs for forging and repairing metalwork.",
    ),
    ToolData(
        "Tinker's Tools",
        50.0,
        10.0,
        Ability.DEXTERITY,
        "Small files, springs, and solder for fixing gadgets.",
    ),
    ToolData(
        "Weaver's Tools",
        1.0,
        5.0,
        Ability.DEXTERITY,
        "A loom, thread, and needles for cloth and tapestry.",
    ),
    ToolData(
        "Woodcarver's Tools",
        1.0,
        5.0,
        Ability.DEXTERITY,
        "Knives and gouges for carving wood into useful shapes.",
    ),
    # --- Other tools and kits ---
    ToolData(
        "Disguise Kit",
        25.0,
        3.0,
        Ability.CHARISMA,
        "Cosmetics, dyes, and props for adopting another face.",
    ),
    ToolData(
        "Forgery Kit",
        15.0,
        5.0,
        Ability.DEXTERITY,
        "Papers, seals, and inks for duplicating documents.",
    ),
    ToolData(
        "Gaming Set",
        1.0,
        0.0,
        Ability.WISDOM,
        "Dice or cards for games of chance and reading opponents.",
    ),
    ToolData(
        "Herbalism Kit",
        5.0,
        3.0,
        Ability.INTELLIGENCE,
        "Clippers and pouches for gathering herbs and brewing remedies.",
    ),
    ToolData(
        "Musical Instrument",
        20.0,
        1.0,
        Ability.CHARISMA,
        "An instrument such as a lute, flute, or drum for performance.",
    ),
    ToolData(
        "Navigator's Tools",
        25.0,
        2.0,
        Ability.WISDOM,
        "A sextant, charts, and calipers for plotting courses.",
    ),
    ToolData(
        "Poisoner's Kit",
        50.0,
        2.0,
        Ability.INTELLIGENCE,
        "Vials and ingredients for preparing and detecting toxins.",
    ),
    ToolData(
        "Thieves' Tools",
        25.0,
        1.0,
        Ability.DEXTERITY,
        "Picks and probes for defeating locks and disarming traps.",
    ),
]

PACKS: list[PackData] = [
    PackData(
        "Burglar's Pack",
        16.0,
        [
            "Backpack",
            "Ball Bearings",
            "Bell",
            "Candle (10)",
            "Crowbar",
            "Lantern, Hooded",
            "Oil (7)",
            "Rations (5)",
            "Rope",
            "Tinderbox",
            "Waterskin",
        ],
    ),
    PackData(
        "Diplomat's Pack",
        39.0,
        [
            "Chest",
            "Fine Clothes",
            "Ink",
            "Ink Pen (5)",
            "Lamp",
            "Oil (4)",
            "Paper (5)",
            "Parchment (5)",
            "Perfume",
        ],
    ),
    PackData(
        "Dungeoneer's Pack",
        12.0,
        [
            "Backpack",
            "Caltrops",
            "Crowbar",
            "Oil (2)",
            "Rations (10)",
            "Rope",
            "Tinderbox",
            "Torch (10)",
            "Waterskin",
        ],
    ),
    PackData(
        "Entertainer's Pack",
        40.0,
        [
            "Backpack",
            "Bedroll",
            "Bell",
            "Costume (3)",
            "Lantern, Bullseye",
            "Mirror",
            "Rations (9)",
            "Tinderbox",
            "Waterskin",
        ],
    ),
    PackData(
        "Explorer's Pack",
        10.0,
        [
            "Backpack",
            "Bedroll",
            "Oil (2)",
            "Rations (10)",
            "Rope",
            "Tinderbox",
            "Torch (10)",
            "Waterskin",
        ],
    ),
    PackData(
        "Priest's Pack",
        33.0,
        [
            "Backpack",
            "Blanket",
            "Holy Water",
            "Lamp",
            "Rations (7)",
            "Robe",
            "Tinderbox",
        ],
    ),
    PackData(
        "Scholar's Pack",
        40.0,
        [
            "Backpack",
            "Book",
            "Ink",
            "Ink Pen",
            "Lamp",
            "Oil (10)",
            "Parchment (10)",
            "Tinderbox",
        ],
    ),
]

GEAR_BY_NAME: dict[str, GearData] = {g.name.lower(): g for g in GEAR}
TOOLS_BY_NAME: dict[str, ToolData] = {t.name.lower(): t for t in TOOLS}
PACKS_BY_NAME: dict[str, PackData] = {p.name.lower(): p for p in PACKS}


def get_gear(name: str) -> GearData | None:
    """Look up gear by case-insensitive name; None if unknown."""
    return GEAR_BY_NAME.get(name.lower())


def get_tool(name: str) -> ToolData | None:
    """Look up a tool by case-insensitive name; None if unknown."""
    return TOOLS_BY_NAME.get(name.lower())
