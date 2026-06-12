import { useCallback, useEffect, useState } from "react";
import { api } from "../../api/client";
import type { AIProvider, EffectiveGameConfig, GameConfigOverrides } from "../../api/client";

interface GameSettingsModalProps {
  worldId: string;
  onClose: () => void;
}

// Form state mirrors GameConfigOverrides but keeps every field as a string so
// inputs stay controlled; values are parsed/nulled on save.
interface FormState {
  ai_provider: AIProvider | "";
  orchestrator_model: string;
  generation_model: string;
  context_token_limit: string;
  context_preserve_last_n: string;
  database_url: string;
  redis_url: string;
}

const EMPTY_FORM: FormState = {
  ai_provider: "",
  orchestrator_model: "",
  generation_model: "",
  context_token_limit: "",
  context_preserve_last_n: "",
  database_url: "",
  redis_url: "",
};

function toFormState(overrides: GameConfigOverrides): FormState {
  return {
    ai_provider: overrides.ai_provider ?? "",
    orchestrator_model: overrides.orchestrator_model ?? "",
    generation_model: overrides.generation_model ?? "",
    context_token_limit: overrides.context_token_limit?.toString() ?? "",
    context_preserve_last_n: overrides.context_preserve_last_n?.toString() ?? "",
    database_url: overrides.database_url ?? "",
    redis_url: overrides.redis_url ?? "",
  };
}

function toOverrides(form: FormState): GameConfigOverrides {
  return {
    ai_provider: form.ai_provider === "" ? null : form.ai_provider,
    orchestrator_model: form.orchestrator_model.trim() || null,
    generation_model: form.generation_model.trim() || null,
    context_token_limit: form.context_token_limit.trim()
      ? Number(form.context_token_limit)
      : null,
    context_preserve_last_n: form.context_preserve_last_n.trim()
      ? Number(form.context_preserve_last_n)
      : null,
    database_url: form.database_url.trim() || null,
    redis_url: form.redis_url.trim() || null,
  };
}

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 11,
  color: "#888",
  textTransform: "uppercase",
  marginBottom: 4,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  boxSizing: "border-box",
  padding: "6px 10px",
  borderRadius: 4,
  border: "1px solid #555",
  background: "#111",
  color: "#fff",
  fontSize: 13,
};

export default function GameSettingsModal({ worldId, onClose }: GameSettingsModalProps) {
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [effective, setEffective] = useState<EffectiveGameConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getGameConfig(worldId)
      .then((config) => {
        if (cancelled) return;
        setForm(toFormState(config.overrides));
        setEffective(config.effective);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load game settings");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [worldId]);

  const setField = useCallback(
    (field: keyof FormState) =>
      (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
        setForm((f) => ({ ...f, [field]: e.target.value })),
    []
  );

  const save = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      const config = await api.updateGameConfig(worldId, toOverrides(form));
      setForm(toFormState(config.overrides));
      setEffective(config.effective);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save game settings");
    } finally {
      setSaving(false);
    }
  }, [worldId, form, onClose]);

  const field = (
    label: string,
    name: keyof FormState,
    placeholder: string,
    type: "text" | "number" = "text"
  ) => (
    <div style={{ marginBottom: 12 }}>
      <label style={labelStyle}>{label}</label>
      <input
        style={inputStyle}
        type={type}
        value={form[name]}
        onChange={setField(name)}
        placeholder={`default: ${placeholder}`}
      />
    </div>
  );

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: 460,
          maxHeight: "85vh",
          overflow: "auto",
          background: "#16213e",
          border: "1px solid #333",
          borderRadius: 8,
          padding: 20,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: "0 0 4px", fontSize: 16, color: "#e0d7ff" }}>Game Settings</h3>
        <p style={{ margin: "0 0 16px", fontSize: 12, color: "#888" }}>
          Per-game overrides for this campaign. Leave a field empty to use the deployment
          default (shown as the placeholder).
        </p>

        {loading ? (
          <p style={{ color: "#888", fontSize: 13 }}>Loading…</p>
        ) : (
          <>
            <h4 style={{ margin: "0 0 8px", fontSize: 12, color: "#ccc" }}>AI MODELS</h4>
            <div style={{ marginBottom: 12 }}>
              <label style={labelStyle}>AI Provider</label>
              <select
                style={inputStyle}
                value={form.ai_provider}
                onChange={setField("ai_provider")}
              >
                <option value="">default: {effective?.ai_provider ?? "anthropic"}</option>
                <option value="anthropic">anthropic (API key)</option>
                <option value="claude_cli">claude_cli (local claude CLI)</option>
              </select>
            </div>
            {field(
              "Orchestrator model (narrative turns)",
              "orchestrator_model",
              effective?.orchestrator_model ?? ""
            )}
            {field(
              "Generation model (summaries, condensing)",
              "generation_model",
              effective?.generation_model ?? ""
            )}

            <h4 style={{ margin: "16px 0 8px", fontSize: 12, color: "#ccc" }}>
              CONTEXT BUDGET
            </h4>
            {field(
              "Context token limit",
              "context_token_limit",
              effective?.context_token_limit.toString() ?? "",
              "number"
            )}
            {field(
              "Messages kept verbatim when condensing",
              "context_preserve_last_n",
              effective?.context_preserve_last_n.toString() ?? "",
              "number"
            )}

            <h4 style={{ margin: "16px 0 8px", fontSize: 12, color: "#ccc" }}>STORAGE</h4>
            {field("Database URL", "database_url", effective?.database_url ?? "")}
            {field("Redis URL", "redis_url", effective?.redis_url ?? "")}

            {error && (
              <p style={{ color: "#e57373", fontSize: 12, whiteSpace: "pre-wrap" }}>{error}</p>
            )}

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
              <button
                onClick={onClose}
                style={{
                  padding: "6px 14px",
                  background: "#333",
                  color: "#fff",
                  border: "none",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                Cancel
              </button>
              <button
                onClick={save}
                disabled={saving}
                style={{
                  padding: "6px 14px",
                  background: saving ? "#444" : "#7c6af7",
                  color: "#fff",
                  border: "none",
                  borderRadius: 4,
                  cursor: saving ? "not-allowed" : "pointer",
                  fontSize: 13,
                  fontWeight: "bold",
                }}
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
