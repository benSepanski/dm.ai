import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { CharacterBuildResponse, CreationOptions } from "../../api/client";
import { api } from "../../api/client";
import { mapCharacterResponse } from "../../api/mappers";
import { useGameStore } from "../../store/gameStore";
import AbilitiesStep from "./AbilitiesStep";
import OriginStep from "./OriginStep";
import ReviewStep from "./ReviewStep";
import SkillsStep from "./SkillsStep";
import {
  abilitiesStepValid,
  backgroundOptionFor,
  classOptionFor,
  emptyDraft,
  originStepValid,
  skillsStepValid,
  toBuildRequest,
  type CharacterDraft,
} from "./draft";
import { ACCENT } from "./ui";

const STEP_TITLES = ["Origin", "Ability Scores", "Skills & Equipment", "Review"];

// Four-step character creation wizard at /world/:worldId/create-character.
// Reference data comes from /characters/creation/options (the engine's data
// registries); submitting runs the engine's build_character on the server.
export default function CharacterCreationWizard() {
  const { worldId } = useParams<{ worldId: string }>();
  const navigate = useNavigate();
  const { sessionId, upsertCharacter } = useGameStore();

  const [options, setOptions] = useState<CreationOptions | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [draft, setDraft] = useState<CharacterDraft>(emptyDraft);
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [created, setCreated] = useState<CharacterBuildResponse | null>(null);

  useEffect(() => {
    api
      .getCreationOptions()
      .then(setOptions)
      .catch((err) =>
        setLoadError(err instanceof Error ? err.message : "Failed to load creation options")
      );
  }, []);

  const onChange = useCallback(
    (updates: Partial<CharacterDraft>) => setDraft((d) => ({ ...d, ...updates })),
    []
  );

  const exitToGame = useCallback(() => {
    navigate(sessionId ? `/session/${sessionId}` : "/", { replace: true });
  }, [navigate, sessionId]);

  const handleCreate = useCallback(async () => {
    if (!options || !worldId) return;
    const background = backgroundOptionFor(draft, options);
    if (!background) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await api.buildCharacter(
        toBuildRequest(draft, worldId, background, sessionId)
      );
      upsertCharacter(mapCharacterResponse(result.character));
      setCreated(result);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Failed to create character");
    } finally {
      setSubmitting(false);
    }
  }, [options, worldId, draft, sessionId, upsertCharacter]);

  if (!worldId) {
    return <Shell>Missing world id in URL.</Shell>;
  }
  if (loadError) {
    return <Shell>Failed to load creation options: {loadError}</Shell>;
  }
  if (!options) {
    return <Shell>Loading creation options…</Shell>;
  }

  if (created) {
    return (
      <Shell>
        <SuccessPanel result={created} onDone={exitToGame} />
      </Shell>
    );
  }

  const classOption = classOptionFor(draft, options);
  const background = backgroundOptionFor(draft, options);
  const stepValid = [
    originStepValid(draft),
    abilitiesStepValid(draft, options),
    classOption !== null && skillsStepValid(draft, classOption),
    true,
  ][step];
  const isLastStep = step === STEP_TITLES.length - 1;

  return (
    <Shell>
      <header style={{ display: "flex", alignItems: "center", marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 20, color: "#e0d7ff", flex: 1 }}>
          Create Character
        </h2>
        <button
          onClick={exitToGame}
          style={{
            padding: "4px 10px",
            background: "#333",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            fontSize: 12,
          }}
        >
          Cancel
        </button>
      </header>

      {/* Step indicator */}
      <div style={{ display: "flex", gap: 8, marginBottom: 24, flexWrap: "wrap" }}>
        {STEP_TITLES.map((title, i) => (
          <div
            key={title}
            style={{
              padding: "4px 10px",
              borderRadius: 4,
              fontSize: 12,
              background: i === step ? ACCENT : i < step ? `${ACCENT}55` : "#222",
              color: i <= step ? "#fff" : "#777",
            }}
          >
            {i + 1}. {title}
          </div>
        ))}
      </div>

      {step === 0 && <OriginStep draft={draft} options={options} onChange={onChange} />}
      {step === 1 && background && (
        <AbilitiesStep
          draft={draft}
          options={options}
          background={background}
          onChange={onChange}
        />
      )}
      {step === 2 && classOption && background && (
        <SkillsStep
          draft={draft}
          options={options}
          classOption={classOption}
          background={background}
          onChange={onChange}
        />
      )}
      {step === 3 && background && (
        <ReviewStep draft={draft} options={options} background={background} />
      )}

      {submitError && (
        <p
          style={{
            color: "#f44336",
            fontSize: 13,
            background: "#2a1010",
            padding: "8px 10px",
            borderRadius: 4,
          }}
        >
          {submitError}
        </p>
      )}

      <footer style={{ display: "flex", gap: 8, marginTop: 24 }}>
        {step > 0 && (
          <button onClick={() => setStep(step - 1)} style={navButtonStyle(false)}>
            Back
          </button>
        )}
        <div style={{ flex: 1 }} />
        {isLastStep ? (
          <button
            onClick={handleCreate}
            disabled={submitting}
            style={navButtonStyle(!submitting)}
          >
            {submitting ? "Creating…" : "Create Character"}
          </button>
        ) : (
          <button
            onClick={() => setStep(step + 1)}
            disabled={!stepValid}
            style={navButtonStyle(stepValid)}
          >
            Next
          </button>
        )}
      </footer>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0d0d1a",
        color: "#fff",
        fontFamily: "sans-serif",
        display: "flex",
        justifyContent: "center",
        padding: 24,
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          background: "#1a1a2e",
          borderRadius: 8,
          padding: 24,
          width: "100%",
          maxWidth: 860,
          boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
          alignSelf: "flex-start",
        }}
      >
        {children}
      </div>
    </div>
  );
}

function navButtonStyle(enabled: boolean): React.CSSProperties {
  return {
    padding: "8px 20px",
    background: enabled ? ACCENT : "#444",
    color: "#fff",
    border: "none",
    borderRadius: 4,
    fontSize: 14,
    fontWeight: "bold",
    cursor: enabled ? "pointer" : "not-allowed",
  };
}

function SuccessPanel({
  result,
  onDone,
}: {
  result: CharacterBuildResponse;
  onDone: () => void;
}) {
  const char = result.character;
  return (
    <div>
      <h2 style={{ margin: "0 0 16px", fontSize: 20, color: "#e0d7ff" }}>
        {char.name} joins the party!
      </h2>
      <p style={{ margin: "0 0 16px", fontSize: 14, color: "#ccc" }}>
        Level {char.level} {char.race} {char.char_class} — HP {char.hp_max}, AC {char.ac},
        Speed {char.speed} ft.
      </p>
      {result.warnings.length > 0 && (
        <div
          style={{
            background: "#2a2210",
            border: "1px solid #6b5a1e",
            borderRadius: 4,
            padding: "8px 12px",
            marginBottom: 16,
          }}
        >
          {result.warnings.map((w) => (
            <p key={w} style={{ margin: "4px 0", fontSize: 13, color: "#e0c36a" }}>
              {w}
            </p>
          ))}
        </div>
      )}
      <button onClick={onDone} style={navButtonStyle(true)}>
        Done
      </button>
    </div>
  );
}
