import type {
  AbilityName,
  AbilityScores,
  BackgroundOption,
  CharacterBuildRequest,
  ClassOption,
  CreationOptions,
  WeaponMasteryOption,
} from "../../api/client";

// In-progress character draft plus the pure validation/derivation logic the
// wizard steps share. The server (game engine) remains the source of truth
// for HP/AC/proficiencies — this module only validates the player's choices.

export const ABILITIES: AbilityName[] = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
];

export const ABILITY_LABELS: Record<AbilityName, string> = {
  strength: "STR",
  dexterity: "DEX",
  constitution: "CON",
  intelligence: "INT",
  wisdom: "WIS",
  charisma: "CHA",
};

export type AbilityMethod = "standard-array" | "point-buy" | "manual";
export type BonusMode = "2-1" | "1-1-1";

export interface CharacterDraft {
  name: string;
  characterClass: string | null;
  species: string | null;
  background: string | null;
  alignment: string | null;
  method: AbilityMethod;
  // Base scores before background increases; null = not yet assigned
  // (standard array starts unassigned).
  scores: Record<AbilityName, number | null>;
  bonusMode: BonusMode;
  bonusPlusTwo: AbilityName | null;
  bonusPlusOne: AbilityName | null;
  skills: string[];
  // Languages known in addition to Common.
  extraLanguages: string[];
  armorName: string | null;
  shield: boolean;
  // Weapon names chosen for mastery (only for classes that get masteries).
  weaponMasteries: string[];
}

export function scoresForMethod(method: AbilityMethod): Record<AbilityName, number | null> {
  const start = method === "standard-array" ? null : method === "point-buy" ? 8 : 10;
  return Object.fromEntries(ABILITIES.map((a) => [a, start])) as Record<
    AbilityName,
    number | null
  >;
}

export function emptyDraft(): CharacterDraft {
  return {
    name: "",
    characterClass: null,
    species: null,
    background: null,
    alignment: null,
    method: "standard-array",
    scores: scoresForMethod("standard-array"),
    bonusMode: "2-1",
    bonusPlusTwo: null,
    bonusPlusOne: null,
    skills: [],
    extraLanguages: [],
    armorName: null,
    shield: false,
    weaponMasteries: [],
  };
}

// Return weapons eligible for mastery selection for the given class.
// Classes with both simple+martial get the full list; classes with only
// simple training get simple + Light/Finesse martial weapons (covers Rogue).
export function masteryWeaponsFor(
  classOption: ClassOption,
  allWeapons: WeaponMasteryOption[]
): WeaponMasteryOption[] {
  const categories = new Set(classOption.weapon_category_training);
  if (categories.has("martial")) return allWeapons;
  return allWeapons.filter(
    (w) =>
      w.category === "simple" ||
      w.properties.includes("finesse") ||
      w.properties.includes("light")
  );
}

export function modifier(score: number): number {
  return Math.floor((score - 10) / 2);
}

export function formatModifier(mod: number): string {
  return mod >= 0 ? `+${mod}` : `${mod}`;
}

export function titleCase(value: string): string {
  return value.replace(/\b\w/g, (c) => c.toUpperCase());
}

export function pointBuySpent(
  scores: Record<AbilityName, number | null>,
  costs: Record<string, number>
): number {
  return ABILITIES.reduce((total, a) => total + (costs[String(scores[a] ?? 8)] ?? 0), 0);
}

export function classOptionFor(draft: CharacterDraft, options: CreationOptions) {
  return options.classes.find((c) => c.character_class === draft.characterClass) ?? null;
}

export function backgroundOptionFor(draft: CharacterDraft, options: CreationOptions) {
  return options.backgrounds.find((b) => b.background === draft.background) ?? null;
}

// The +2/+1 (or +1/+1/+1) allocation among the background's three abilities.
export function backgroundAllocation(
  draft: CharacterDraft,
  background: BackgroundOption
): Partial<Record<AbilityName, number>> | null {
  if (draft.bonusMode === "1-1-1") {
    return Object.fromEntries(background.ability_scores.map((a) => [a, 1]));
  }
  if (!draft.bonusPlusTwo || !draft.bonusPlusOne) return null;
  return { [draft.bonusPlusTwo]: 2, [draft.bonusPlusOne]: 1 };
}

export function finalScores(
  draft: CharacterDraft,
  background: BackgroundOption
): AbilityScores | null {
  if (ABILITIES.some((a) => draft.scores[a] === null)) return null;
  const allocation = backgroundAllocation(draft, background);
  if (allocation === null) return null;
  return Object.fromEntries(
    ABILITIES.map((a) => [a, Math.min(20, (draft.scores[a] as number) + (allocation[a] ?? 0))])
  ) as AbilityScores;
}

// ---- Per-step validation ----

export function originStepValid(draft: CharacterDraft): boolean {
  return Boolean(
    draft.name.trim() && draft.characterClass && draft.species && draft.background
  );
}

export function abilitiesStepValid(draft: CharacterDraft, options: CreationOptions): boolean {
  const assigned = ABILITIES.every((a) => draft.scores[a] !== null);
  if (!assigned) return false;
  if (
    draft.method === "point-buy" &&
    pointBuySpent(draft.scores, options.point_buy_costs) > options.point_buy_budget
  ) {
    return false;
  }
  if (draft.bonusMode === "2-1") {
    return Boolean(
      draft.bonusPlusTwo && draft.bonusPlusOne && draft.bonusPlusTwo !== draft.bonusPlusOne
    );
  }
  return true;
}

export function skillsStepValid(draft: CharacterDraft, classOption: ClassOption): boolean {
  if (draft.skills.length !== classOption.num_skill_choices) return false;
  if (classOption.weapon_mastery_count > 0) {
    return draft.weaponMasteries.length === classOption.weapon_mastery_count;
  }
  return true;
}

export function toBuildRequest(
  draft: CharacterDraft,
  worldId: string,
  background: BackgroundOption,
  sessionId?: string | null
): CharacterBuildRequest {
  return {
    world_id: worldId,
    ...(sessionId ? { session_id: sessionId } : {}),
    name: draft.name.trim(),
    character_class: draft.characterClass as string,
    species: draft.species as string,
    background: background.background,
    ability_scores: Object.fromEntries(
      ABILITIES.map((a) => [a, draft.scores[a] ?? 10])
    ) as AbilityScores,
    skill_choices: draft.skills,
    background_ability_allocation: backgroundAllocation(draft, background),
    languages: ["Common", ...draft.extraLanguages],
    armor_name: draft.armorName,
    shield: draft.shield,
    alignment: draft.alignment,
    weapon_masteries: draft.weaponMasteries.length > 0 ? draft.weaponMasteries : null,
  };
}
