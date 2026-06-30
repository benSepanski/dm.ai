import type { BackgroundOption, CreationOptions } from "../../api/client";
import type { CharacterDraft } from "./draft";
import {
  ABILITIES,
  ABILITY_LABELS,
  classOptionFor,
  finalScores,
  formatModifier,
  modifier,
  titleCase,
} from "./draft";
import { DetailCard, DetailLine, Section } from "./ui";

// Step 4: read-only summary of every choice. The engine computes HP, AC,
// and proficiencies on the server when the wizard submits.

export default function ReviewStep({
  draft,
  options,
  background,
}: {
  draft: CharacterDraft;
  options: CreationOptions;
  background: BackgroundOption;
}) {
  const finals = finalScores(draft, background);
  const speciesOption = options.species.find((s) => s.species === draft.species);
  const classOption = classOptionFor(draft, options);

  return (
    <div>
      <Section title="Summary">
        <DetailCard>
          <DetailLine label="Name" value={draft.name.trim()} />
          <DetailLine
            label="Origin"
            value={`${draft.species} ${draft.characterClass}, ${background.background}`}
          />
          <DetailLine label="Alignment" value={draft.alignment ?? "None"} />
          {speciesOption && <DetailLine label="Speed" value={`${speciesOption.speed} ft.`} />}
          <DetailLine label="Origin feat" value={background.origin_feat} />
        </DetailCard>
      </Section>

      {finals && (
        <Section title="Ability Scores (after background increases)">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {ABILITIES.map((ability) => (
              <div
                key={ability}
                style={{
                  background: "#16162a",
                  border: "1px solid #333",
                  borderRadius: 6,
                  padding: 10,
                  width: 110,
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: 12, color: "#888" }}>{ABILITY_LABELS[ability]}</div>
                <div style={{ fontSize: 18 }}>{finals[ability]}</div>
                <div style={{ fontSize: 12, color: "#888" }}>
                  {formatModifier(modifier(finals[ability]))}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      <Section title="Proficiencies & Gear">
        <DetailCard>
          <DetailLine
            label="Skills"
            value={[...draft.skills, ...background.skill_proficiencies]
              .map(titleCase)
              .join(", ")}
          />
          <DetailLine label="Tool" value={background.tool_proficiency} />
          <DetailLine
            label="Languages"
            value={["Common", ...draft.extraLanguages].join(", ")}
          />
          <DetailLine
            label="Armor"
            value={`${draft.armorName ?? "Unarmored"}${draft.shield ? " + Shield" : ""}`}
          />
          <DetailLine label="Equipment" value={background.equipment.join(", ")} />
          {classOption && classOption.weapon_mastery_count > 0 && (
            <DetailLine
              label="Weapon Masteries"
              value={
                draft.weaponMasteries.length > 0
                  ? draft.weaponMasteries.join(", ")
                  : "(none selected)"
              }
            />
          )}
        </DetailCard>
        <p style={{ margin: "10px 0 0", fontSize: 12, color: "#777" }}>
          Hit points, armor class, and spell slots are computed by the rule engine when you
          create the character.
        </p>
      </Section>
    </div>
  );
}
