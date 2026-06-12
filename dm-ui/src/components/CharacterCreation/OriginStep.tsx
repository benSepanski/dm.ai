import type { CreationOptions } from "../../api/client";
import type { CharacterDraft } from "./draft";
import { ABILITY_LABELS, backgroundOptionFor, classOptionFor, titleCase } from "./draft";
import { DetailCard, DetailLine, Pill, PillRow, Section, inputStyle, selectStyle } from "./ui";

// Step 1: name + the three origin choices (class, species, background) and
// an optional alignment. Picking a background resets the ability-bonus and
// skill choices made in later steps, since their option sets change.

export default function OriginStep({
  draft,
  options,
  onChange,
}: {
  draft: CharacterDraft;
  options: CreationOptions;
  onChange: (updates: Partial<CharacterDraft>) => void;
}) {
  const classOption = classOptionFor(draft, options);
  const speciesOption = options.species.find((s) => s.species === draft.species) ?? null;
  const backgroundOption = backgroundOptionFor(draft, options);

  return (
    <div>
      <Section title="Name">
        <input
          value={draft.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder="Character name"
          style={{ ...inputStyle, maxWidth: 360 }}
        />
      </Section>

      <Section title="Class">
        <PillRow>
          {options.classes.map((c) => (
            <Pill
              key={c.character_class}
              label={c.character_class}
              selected={draft.characterClass === c.character_class}
              onClick={() =>
                onChange({ characterClass: c.character_class, skills: [], armorName: null, shield: false })
              }
            />
          ))}
        </PillRow>
        {classOption && (
          <DetailCard>
            <DetailLine label="Hit die" value={`d${classOption.hit_die}`} />
            <DetailLine
              label="Primary"
              value={classOption.primary_abilities.map((a) => ABILITY_LABELS[a]).join(", ")}
            />
            <DetailLine
              label="Saving throws"
              value={classOption.saving_throw_proficiencies
                .map((a) => ABILITY_LABELS[a])
                .join(", ")}
            />
            <DetailLine
              label="Armor training"
              value={
                classOption.armor_training.length
                  ? classOption.armor_training.map(titleCase).join(", ")
                  : "None"
              }
            />
            <DetailLine
              label="Spellcasting"
              value={classOption.spellcasting ? "Yes" : "No"}
            />
          </DetailCard>
        )}
      </Section>

      <Section title="Species">
        <PillRow>
          {options.species.map((s) => (
            <Pill
              key={s.species}
              label={s.species}
              selected={draft.species === s.species}
              onClick={() => onChange({ species: s.species })}
            />
          ))}
        </PillRow>
        {speciesOption && (
          <DetailCard>
            <p style={{ margin: "0 0 8px" }}>{speciesOption.description}</p>
            <DetailLine label="Speed" value={`${speciesOption.speed} ft.`} />
            {speciesOption.darkvision_ft > 0 && (
              <DetailLine label="Darkvision" value={`${speciesOption.darkvision_ft} ft.`} />
            )}
            {speciesOption.damage_resistances.length > 0 && (
              <DetailLine
                label="Resistances"
                value={speciesOption.damage_resistances.map(titleCase).join(", ")}
              />
            )}
            {speciesOption.traits.map((t) => (
              <DetailLine key={t.name} label={t.name} value={t.description} />
            ))}
          </DetailCard>
        )}
      </Section>

      <Section title="Background">
        <PillRow>
          {options.backgrounds.map((b) => (
            <Pill
              key={b.background}
              label={b.background}
              selected={draft.background === b.background}
              onClick={() =>
                onChange({
                  background: b.background,
                  bonusPlusTwo: null,
                  bonusPlusOne: null,
                  skills: [],
                })
              }
            />
          ))}
        </PillRow>
        {backgroundOption && (
          <DetailCard>
            <p style={{ margin: "0 0 8px" }}>{backgroundOption.description}</p>
            <DetailLine
              label="Ability scores"
              value={backgroundOption.ability_scores.map((a) => ABILITY_LABELS[a]).join(", ")}
            />
            <DetailLine
              label="Skills"
              value={backgroundOption.skill_proficiencies.map(titleCase).join(", ")}
            />
            <DetailLine label="Tool" value={backgroundOption.tool_proficiency} />
            <DetailLine label="Origin feat" value={backgroundOption.origin_feat} />
            <DetailLine label="Equipment" value={backgroundOption.equipment.join(", ")} />
          </DetailCard>
        )}
      </Section>

      <Section title="Alignment (optional)">
        <select
          value={draft.alignment ?? ""}
          onChange={(e) => onChange({ alignment: e.target.value || null })}
          style={selectStyle}
        >
          <option value="">No alignment</option>
          {options.alignments.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </Section>
    </div>
  );
}
