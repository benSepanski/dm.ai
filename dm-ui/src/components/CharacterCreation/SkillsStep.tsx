import type { BackgroundOption, ClassOption, CreationOptions } from "../../api/client";
import type { CharacterDraft } from "./draft";
import { ABILITY_LABELS, titleCase } from "./draft";
import { Pill, PillRow, Section, selectStyle } from "./ui";

// Step 3: class skill choices (background skills are granted automatically),
// extra languages, and starting armor/shield filtered to the class's
// armor training.

const MAX_EXTRA_LANGUAGES = 2;

export default function SkillsStep({
  draft,
  options,
  classOption,
  background,
  onChange,
}: {
  draft: CharacterDraft;
  options: CreationOptions;
  classOption: ClassOption;
  background: BackgroundOption;
  onChange: (updates: Partial<CharacterDraft>) => void;
}) {
  const toggleSkill = (skill: string) => {
    if (draft.skills.includes(skill)) {
      onChange({ skills: draft.skills.filter((s) => s !== skill) });
    } else if (draft.skills.length < classOption.num_skill_choices) {
      onChange({ skills: [...draft.skills, skill] });
    }
  };

  const toggleLanguage = (language: string) => {
    if (draft.extraLanguages.includes(language)) {
      onChange({ extraLanguages: draft.extraLanguages.filter((l) => l !== language) });
    } else if (draft.extraLanguages.length < MAX_EXTRA_LANGUAGES) {
      onChange({ extraLanguages: [...draft.extraLanguages, language] });
    }
  };

  const skillLabel = (skill: string) => {
    const governing = options.skills.find((s) => s.skill === skill)?.governing_ability;
    return `${titleCase(skill)}${governing ? ` (${ABILITY_LABELS[governing]})` : ""}`;
  };

  const wearableArmor = options.armor.filter((a) =>
    classOption.armor_training.includes(a.armor_type)
  );
  const canUseShield = classOption.armor_training.includes("shield");

  return (
    <div>
      <Section
        title={`Class Skills (choose ${classOption.num_skill_choices} — ${draft.skills.length} selected)`}
      >
        <PillRow>
          {classOption.skill_choices.map((skill) => (
            <Pill
              key={skill}
              label={skillLabel(skill)}
              selected={draft.skills.includes(skill)}
              disabled={
                !draft.skills.includes(skill) &&
                (draft.skills.length >= classOption.num_skill_choices ||
                  background.skill_proficiencies.includes(skill))
              }
              onClick={() => toggleSkill(skill)}
            />
          ))}
        </PillRow>
        <p style={{ margin: "10px 0 0", fontSize: 13, color: "#aaa" }}>
          From {background.background}:{" "}
          {background.skill_proficiencies.map(titleCase).join(", ")}
        </p>
      </Section>

      <Section title={`Languages (Common + up to ${MAX_EXTRA_LANGUAGES} more)`}>
        <PillRow>
          {options.languages
            .filter((l) => l !== "Common")
            .map((language) => (
              <Pill
                key={language}
                label={language}
                selected={draft.extraLanguages.includes(language)}
                disabled={
                  !draft.extraLanguages.includes(language) &&
                  draft.extraLanguages.length >= MAX_EXTRA_LANGUAGES
                }
                onClick={() => toggleLanguage(language)}
              />
            ))}
        </PillRow>
      </Section>

      <Section title="Starting Armor">
        {wearableArmor.length === 0 ? (
          <p style={{ margin: 0, fontSize: 13, color: "#aaa" }}>
            {classOption.character_class}s have no armor training — starting unarmored.
          </p>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
            <select
              value={draft.armorName ?? ""}
              onChange={(e) => onChange({ armorName: e.target.value || null })}
              style={selectStyle}
            >
              <option value="">Unarmored</option>
              {wearableArmor.map((a) => (
                <option key={a.name} value={a.name}>
                  {a.name} (AC {a.base_ac}
                  {a.dex_bonus ? ` + DEX${a.dex_cap !== null ? ` max ${a.dex_cap}` : ""}` : ""}
                  {a.stealth_disadvantage ? ", stealth disadv." : ""})
                </option>
              ))}
            </select>
            {canUseShield && (
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  fontSize: 13,
                  color: "#ccc",
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={draft.shield}
                  onChange={(e) => onChange({ shield: e.target.checked })}
                />
                Shield (+2 AC)
              </label>
            )}
          </div>
        )}
      </Section>
    </div>
  );
}
