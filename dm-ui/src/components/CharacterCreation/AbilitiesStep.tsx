import type { AbilityName, BackgroundOption, CreationOptions } from "../../api/client";
import type { AbilityMethod, CharacterDraft } from "./draft";
import {
  ABILITIES,
  ABILITY_LABELS,
  finalScores,
  formatModifier,
  modifier,
  pointBuySpent,
  scoresForMethod,
} from "./draft";
import { ACCENT, Pill, PillRow, Section, selectStyle } from "./ui";

// Step 2: assign base ability scores (standard array, point buy, or manual
// entry for rolled scores), then allocate the background's +2/+1 (or
// +1/+1/+1) increases among its three abilities.

const METHODS: { id: AbilityMethod; label: string }[] = [
  { id: "standard-array", label: "Standard Array" },
  { id: "point-buy", label: "Point Buy" },
  { id: "manual", label: "Manual / Rolled" },
];

export default function AbilitiesStep({
  draft,
  options,
  background,
  onChange,
}: {
  draft: CharacterDraft;
  options: CreationOptions;
  background: BackgroundOption;
  onChange: (updates: Partial<CharacterDraft>) => void;
}) {
  const setScore = (ability: AbilityName, value: number | null) =>
    onChange({ scores: { ...draft.scores, [ability]: value } });

  const spent = pointBuySpent(draft.scores, options.point_buy_costs);
  const finals = finalScores(draft, background);

  return (
    <div>
      <Section title="Method">
        <PillRow>
          {METHODS.map((m) => (
            <Pill
              key={m.id}
              label={m.label}
              selected={draft.method === m.id}
              onClick={() => onChange({ method: m.id, scores: scoresForMethod(m.id) })}
            />
          ))}
        </PillRow>
      </Section>

      <Section title="Base Scores">
        {draft.method === "point-buy" && (
          <p
            style={{
              margin: "0 0 10px",
              fontSize: 13,
              color: spent > options.point_buy_budget ? "#f44336" : "#aaa",
            }}
          >
            Points spent: {spent} / {options.point_buy_budget}
          </p>
        )}
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
              <div style={{ fontSize: 12, color: "#888", marginBottom: 6 }}>
                {ABILITY_LABELS[ability]}
              </div>
              {draft.method === "standard-array" && (
                <select
                  value={draft.scores[ability] ?? ""}
                  onChange={(e) =>
                    setScore(ability, e.target.value === "" ? null : Number(e.target.value))
                  }
                  style={{ ...selectStyle, width: "100%" }}
                >
                  <option value="">—</option>
                  {options.standard_array.map((v) => (
                    <option
                      key={v}
                      value={v}
                      disabled={ABILITIES.some(
                        (other) => other !== ability && draft.scores[other] === v
                      )}
                    >
                      {v}
                    </option>
                  ))}
                </select>
              )}
              {draft.method === "point-buy" && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 8,
                  }}
                >
                  <StepButton
                    label="−"
                    disabled={(draft.scores[ability] ?? 8) <= 8}
                    onClick={() => setScore(ability, (draft.scores[ability] ?? 8) - 1)}
                  />
                  <span style={{ fontSize: 16, minWidth: 22 }}>{draft.scores[ability]}</span>
                  <StepButton
                    label="+"
                    disabled={(draft.scores[ability] ?? 8) >= 15}
                    onClick={() => setScore(ability, (draft.scores[ability] ?? 8) + 1)}
                  />
                </div>
              )}
              {draft.method === "manual" && (
                <input
                  type="number"
                  min={3}
                  max={18}
                  value={draft.scores[ability] ?? 10}
                  onChange={(e) => {
                    const v = Number(e.target.value);
                    setScore(ability, Math.max(3, Math.min(18, Number.isNaN(v) ? 10 : v)));
                  }}
                  style={{ ...selectStyle, width: "100%", textAlign: "center" }}
                />
              )}
            </div>
          ))}
        </div>
      </Section>

      <Section title={`Background Increases (${background.background})`}>
        <PillRow>
          <Pill
            label="+2 / +1"
            selected={draft.bonusMode === "2-1"}
            onClick={() => onChange({ bonusMode: "2-1" })}
          />
          <Pill
            label="+1 / +1 / +1"
            selected={draft.bonusMode === "1-1-1"}
            onClick={() => onChange({ bonusMode: "1-1-1", bonusPlusTwo: null, bonusPlusOne: null })}
          />
        </PillRow>
        {draft.bonusMode === "2-1" && (
          <div style={{ marginTop: 12, display: "flex", gap: 24, flexWrap: "wrap" }}>
            <BonusPicker
              label="+2 to"
              abilities={background.ability_scores}
              value={draft.bonusPlusTwo}
              disabledValue={draft.bonusPlusOne}
              onPick={(a) => onChange({ bonusPlusTwo: a })}
            />
            <BonusPicker
              label="+1 to"
              abilities={background.ability_scores}
              value={draft.bonusPlusOne}
              disabledValue={draft.bonusPlusTwo}
              onPick={(a) => onChange({ bonusPlusOne: a })}
            />
          </div>
        )}
        {draft.bonusMode === "1-1-1" && (
          <p style={{ margin: "10px 0 0", fontSize: 13, color: "#aaa" }}>
            +1 to {background.ability_scores.map((a) => ABILITY_LABELS[a]).join(", ")}
          </p>
        )}
      </Section>

      {finals && (
        <Section title="Final Scores">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {ABILITIES.map((ability) => {
              const boosted = finals[ability] !== draft.scores[ability];
              return (
                <div
                  key={ability}
                  style={{
                    background: "#16162a",
                    border: boosted ? `1px solid ${ACCENT}` : "1px solid #333",
                    borderRadius: 6,
                    padding: 10,
                    width: 110,
                    textAlign: "center",
                  }}
                >
                  <div style={{ fontSize: 12, color: "#888" }}>{ABILITY_LABELS[ability]}</div>
                  <div style={{ fontSize: 18, color: boosted ? "#e0d7ff" : "#fff" }}>
                    {finals[ability]}
                  </div>
                  <div style={{ fontSize: 12, color: "#888" }}>
                    {formatModifier(modifier(finals[ability]))}
                  </div>
                </div>
              );
            })}
          </div>
        </Section>
      )}
    </div>
  );
}

function StepButton({
  label,
  disabled,
  onClick,
}: {
  label: string;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        width: 24,
        height: 24,
        borderRadius: 4,
        border: "1px solid #444",
        background: disabled ? "#222" : "#333",
        color: disabled ? "#555" : "#fff",
        cursor: disabled ? "not-allowed" : "pointer",
        fontSize: 14,
        lineHeight: 1,
      }}
    >
      {label}
    </button>
  );
}

function BonusPicker({
  label,
  abilities,
  value,
  disabledValue,
  onPick,
}: {
  label: string;
  abilities: AbilityName[];
  value: AbilityName | null;
  disabledValue: AbilityName | null;
  onPick: (ability: AbilityName) => void;
}) {
  return (
    <div>
      <div style={{ fontSize: 12, color: "#888", marginBottom: 6 }}>{label}</div>
      <PillRow>
        {abilities.map((a) => (
          <Pill
            key={a}
            label={ABILITY_LABELS[a]}
            selected={value === a}
            disabled={disabledValue === a}
            onClick={() => onPick(a)}
          />
        ))}
      </PillRow>
    </div>
  );
}
