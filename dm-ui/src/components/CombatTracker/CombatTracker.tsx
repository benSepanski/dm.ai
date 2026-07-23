import { useCallback, useEffect, useState } from "react";
import { api, type CombatStateResponse, type WeaponMasteryOption } from "../../api/client";
import { mapCharacterResponse } from "../../api/mappers";
import { useGameStore, type ActiveCombat, type CharacterData, type Combatant } from "../../store/gameStore";

// Build the ActiveCombat view by zipping initiative_order (has initiative score)
// with combatants (has hp/ac). Both lists share the same index order set by
// start_combat and never reordered afterward.
function mapCombatResponse(result: CombatStateResponse): ActiveCombat {
  const order = result.initiative_order ?? [];
  const data = result.combatants ?? [];
  const combatants: Combatant[] = order.map((entry, i) => ({
    char_id: entry.character_id,
    name: entry.name,
    hp_current: data[i]?.hp_current ?? 0,
    hp_max: data[i]?.hp_max ?? 0,
    ac: data[i]?.ac ?? 10,
    initiative: entry.initiative,
    is_current_turn: i === result.current_turn_index,
  }));
  return {
    id: result.id,
    round_number: result.round_number,
    current_turn_index: result.current_turn_index,
    combatants,
  };
}

function CombatantRow({ combatant }: { combatant: Combatant }) {
  const pct =
    combatant.hp_max > 0
      ? Math.max(0, Math.min(100, (combatant.hp_current / combatant.hp_max) * 100))
      : 0;
  const color = pct > 50 ? "#4caf50" : pct > 25 ? "#ff9800" : "#f44336";
  return (
    <div
      style={{
        padding: "8px 10px",
        marginBottom: 4,
        borderRadius: 6,
        background: combatant.is_current_turn ? "#2a2a4e" : "#1a1a2e",
        borderLeft: combatant.is_current_turn
          ? "3px solid #7c6af7"
          : "3px solid transparent",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ fontWeight: combatant.is_current_turn ? "bold" : "normal" }}>
          {combatant.is_current_turn ? "▶ " : ""}
          {combatant.name}
        </span>
        <span style={{ fontSize: 12, color: "#aaa" }}>Init {combatant.initiative}</span>
      </div>
      <div
        style={{ background: "#333", borderRadius: 3, height: 6, margin: "4px 0" }}
      >
        <div
          style={{
            width: `${pct}%`,
            background: color,
            height: "100%",
            borderRadius: 3,
          }}
        />
      </div>
      <div style={{ fontSize: 11, color: "#aaa" }}>
        HP {combatant.hp_current}/{combatant.hp_max} · AC {combatant.ac}
      </div>
    </div>
  );
}

// ActionType enum values from the backend (case must match exactly).
const ACTION_BUTTONS = [
  { label: "Attack", action: "Attack", needsTarget: true },
  { label: "Dash", action: "Dash", needsTarget: false },
  { label: "Dodge", action: "Dodge", needsTarget: false },
] as const;

// The server returns FastAPI's default error shape ({"detail": "..."}) for
// HTTPExceptions; fall back to the raw text for anything else.
function parseApiError(err: unknown): string {
  const message = err instanceof Error ? err.message : String(err);
  try {
    const parsed = JSON.parse(message) as { detail?: string };
    return parsed.detail ?? message;
  } catch {
    return message;
  }
}

// PT-29: an equipped weapon is just an equipment string that also names a
// registry weapon. Unarmed Strike is always offered — it's the engine's own
// fallback and isn't a registry entry.
const UNARMED_STRIKE = "Unarmed Strike";

function equippedWeaponNames(
  equipment: string[] | null | undefined,
  weaponOptions: WeaponMasteryOption[]
): string[] {
  const registryNames = new Set(weaponOptions.map((w) => w.name));
  const owned = (equipment ?? []).filter((item) => registryNames.has(item));
  return [UNARMED_STRIKE, ...Array.from(new Set(owned))];
}

function CombatActions({
  sessionId,
  currentActorId,
  combatants,
  weaponOptions,
  disabled,
}: {
  sessionId: string;
  currentActorId: string | undefined;
  combatants: Combatant[];
  weaponOptions: WeaponMasteryOption[];
  disabled: boolean;
}) {
  const { setCombat, addMessage, characters } = useGameStore();
  const [targetId, setTargetId] = useState<string | null>(null);
  const [weaponName, setWeaponName] = useState(UNARMED_STRIKE);
  const [spellName, setSpellName] = useState("");
  const [spellTargetIds, setSpellTargetIds] = useState<string[]>([]);
  const [slotLevelInput, setSlotLevelInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  const targets = combatants.filter((c) => c.char_id !== currentActorId);
  const actor = characters.find((c) => c.id === currentActorId);
  const weaponChoices = equippedWeaponNames(actor?.equipment, weaponOptions);
  const knownSpells = actor?.known_spells ?? [];
  const selectedSpell = spellName || knownSpells[0] || "";

  // Shared by Attack/Dash/Dodge (submitAction) and Cast Spell (castSpell) —
  // both return a CombatStateResponse whose newest combat_log entry may
  // carry narratable flavor_text (PT-23/PT-28).
  const pushFlavorText = useCallback(
    (result: CombatStateResponse) => {
      const lastLog = result.combat_log?.[result.combat_log.length - 1];
      const flavorText = lastLog?.flavor_text;
      if (typeof flavorText === "string" && flavorText) {
        addMessage({
          id: `combat-${result.id}-${result.combat_log!.length}`,
          role: "system",
          content: flavorText,
          timestamp: new Date().toISOString(),
        });
      }
    },
    [addMessage]
  );

  const handleAction = useCallback(
    async (actionType: string, needsTarget: boolean) => {
      if (!currentActorId) return;
      if (needsTarget && !targetId) {
        setError("Select a target first.");
        return;
      }
      setError(null);
      try {
        const result = await api.submitAction(sessionId, {
          actor_id: currentActorId,
          action_type: actionType,
          ...(needsTarget && targetId ? { target_id: targetId } : {}),
          ...(actionType === "Attack" ? { attack_details: { weapon_name: weaponName } } : {}),
        });
        setCombat(mapCombatResponse(result));
        pushFlavorText(result);
        setTargetId(null);
      } catch (err) {
        setError(parseApiError(err));
      }
    },
    [sessionId, currentActorId, targetId, weaponName, setCombat, pushFlavorText]
  );

  const toggleSpellTarget = useCallback((id: string) => {
    setSpellTargetIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  }, []);

  const handleCastSpell = useCallback(async () => {
    if (!currentActorId || !selectedSpell) return;
    setError(null);
    try {
      const trimmedSlot = slotLevelInput.trim();
      const result = await api.castSpell(sessionId, {
        actor_id: currentActorId,
        spell_name: selectedSpell,
        target_ids: spellTargetIds,
        ...(trimmedSlot ? { slot_level: parseInt(trimmedSlot, 10) } : {}),
      });
      setCombat(mapCombatResponse(result));
      pushFlavorText(result);
      setSpellTargetIds([]);
    } catch (err) {
      setError(parseApiError(err));
    }
  }, [
    sessionId,
    currentActorId,
    selectedSpell,
    spellTargetIds,
    slotLevelInput,
    setCombat,
    pushFlavorText,
  ]);

  const handleNextTurn = useCallback(async () => {
    try {
      const result = await api.nextTurn(sessionId);
      setCombat(mapCombatResponse(result));
    } catch (err) {
      console.error("Failed to advance turn:", err);
    }
  }, [sessionId, setCombat]);

  return (
    <div style={{ marginTop: 8 }}>
      {targets.length > 0 && (
        <div style={{ marginBottom: 6 }}>
          <div style={{ fontSize: 11, color: "#aaa", marginBottom: 4 }}>
            Target (for Attack)
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {targets.map((t) => (
              <button
                key={t.char_id}
                onClick={() => setTargetId(t.char_id === targetId ? null : t.char_id)}
                style={{
                  padding: "3px 8px",
                  background: t.char_id === targetId ? "#7c6af7" : "#222",
                  color: "#fff",
                  border: "1px solid #444",
                  borderRadius: 12,
                  cursor: "pointer",
                  fontSize: 11,
                }}
              >
                {t.name}
              </button>
            ))}
          </div>
        </div>
      )}
      {weaponChoices.length > 1 && (
        <div style={{ marginBottom: 6 }}>
          <label style={{ fontSize: 11, color: "#aaa", display: "block", marginBottom: 4 }}>
            Weapon (for Attack)
            <select
              value={weaponName}
              onChange={(e) => setWeaponName(e.target.value)}
              style={{
                display: "block",
                width: "100%",
                marginTop: 2,
                padding: "3px 4px",
                background: "#111",
                border: "1px solid #555",
                borderRadius: 3,
                color: "#fff",
                fontSize: 12,
              }}
            >
              {weaponChoices.map((w) => (
                <option key={w} value={w}>
                  {w}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      {knownSpells.length > 0 && (
        <div
          style={{
            marginBottom: 6,
            padding: 6,
            background: "#151530",
            borderRadius: 4,
          }}
        >
          <label style={{ fontSize: 11, color: "#aaa", display: "block", marginBottom: 4 }}>
            Spell
            <select
              value={selectedSpell}
              onChange={(e) => setSpellName(e.target.value)}
              style={{
                display: "block",
                width: "100%",
                marginTop: 2,
                padding: "3px 4px",
                background: "#111",
                border: "1px solid #555",
                borderRadius: 3,
                color: "#fff",
                fontSize: 12,
              }}
            >
              {knownSpells.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          {targets.length > 0 && (
            <div style={{ marginBottom: 4 }}>
              <div style={{ fontSize: 11, color: "#aaa", marginBottom: 4 }}>
                Targets (optional — pick 0+)
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {targets.map((t) => (
                  <button
                    key={t.char_id}
                    onClick={() => toggleSpellTarget(t.char_id)}
                    style={{
                      padding: "3px 8px",
                      background: spellTargetIds.includes(t.char_id) ? "#7c6af7" : "#222",
                      color: "#fff",
                      border: "1px solid #444",
                      borderRadius: 12,
                      cursor: "pointer",
                      fontSize: 11,
                    }}
                  >
                    {t.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          <label style={{ fontSize: 11, color: "#aaa", display: "block", marginBottom: 4 }}>
            Slot Level (blank = spell's own level)
            <input
              type="number"
              min={1}
              max={9}
              value={slotLevelInput}
              onChange={(e) => setSlotLevelInput(e.target.value)}
              placeholder="e.g. 3 to upcast"
              style={{
                display: "block",
                width: "100%",
                marginTop: 2,
                padding: "3px 4px",
                background: "#111",
                border: "1px solid #555",
                borderRadius: 3,
                color: "#fff",
                fontSize: 12,
              }}
            />
          </label>
          <button
            onClick={handleCastSpell}
            disabled={disabled || !currentActorId}
            style={{
              width: "100%",
              padding: "5px 0",
              background: disabled || !currentActorId ? "#333" : "#5b3a9e",
              color: disabled || !currentActorId ? "#666" : "#fff",
              border: "1px solid #444",
              borderRadius: 4,
              cursor: disabled || !currentActorId ? "not-allowed" : "pointer",
              fontSize: 12,
            }}
          >
            Cast {selectedSpell || "Spell"}
          </button>
        </div>
      )}
      {error && (
        <p style={{ color: "#f44336", fontSize: 11, margin: "0 0 6px" }}>{error}</p>
      )}
      <div style={{ display: "flex", gap: 6 }}>
        {ACTION_BUTTONS.map(({ label, action, needsTarget }) => (
          <button
            key={action}
            onClick={() => handleAction(action, needsTarget)}
            disabled={disabled || !currentActorId}
            style={{
              flex: 1,
              padding: "5px 0",
              background: disabled || !currentActorId ? "#333" : "#2c3e50",
              color: disabled || !currentActorId ? "#666" : "#fff",
              border: "1px solid #444",
              borderRadius: 4,
              cursor: disabled || !currentActorId ? "not-allowed" : "pointer",
              fontSize: 12,
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <button
        onClick={handleNextTurn}
        disabled={disabled}
        style={{
          width: "100%",
          marginTop: 6,
          padding: "5px 0",
          background: disabled ? "#333" : "#1a5276",
          color: disabled ? "#666" : "#fff",
          border: "1px solid #444",
          borderRadius: 4,
          cursor: disabled ? "not-allowed" : "pointer",
          fontSize: 12,
        }}
      >
        Next Turn ▶
      </button>
    </div>
  );
}

// ---- Start Combat dialog ----

interface CombatantEntry {
  char: CharacterData;
  selected: boolean;
  // Overrides for characters missing combat stats — filled in by DM before starting.
  hpMaxOverride: string;
  acOverride: string;
}

function needsStats(char: CharacterData): boolean {
  return char.hp_max === null || char.ac === null;
}

function StatInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11 }}>
      <span style={{ color: "#aaa", minWidth: 28 }}>{label}</span>
      <input
        type="number"
        min={1}
        max={999}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: 48,
          padding: "2px 4px",
          background: "#111",
          border: "1px solid #555",
          borderRadius: 3,
          color: "#fff",
          fontSize: 11,
        }}
      />
    </label>
  );
}

function StartCombatDialog({
  sessionId,
  onClose,
}: {
  sessionId: string;
  onClose: () => void;
}) {
  const { characters, setCombat, upsertCharacter } = useGameStore();

  const [entries, setEntries] = useState<CombatantEntry[]>(() =>
    characters.map((char) => ({
      char,
      selected: char.type === "PC",
      hpMaxOverride: char.hp_max?.toString() ?? "",
      acOverride: char.ac?.toString() ?? "",
    }))
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const update = (id: string, patch: Partial<CombatantEntry>) =>
    setEntries((prev) => prev.map((e) => (e.char.id === id ? { ...e, ...patch } : e)));

  const selected = entries.filter((e) => e.selected);

  // Validate: every selected character must have effective hp_max and ac.
  const missingStats = selected.filter((e) => {
    const hp = e.char.hp_max ?? parseInt(e.hpMaxOverride, 10);
    const ac = e.char.ac ?? parseInt(e.acOverride, 10);
    return !hp || !ac || isNaN(hp) || isNaN(ac);
  });
  const canBegin = selected.length > 0 && missingStats.length === 0 && !loading;

  const handleBegin = async () => {
    setLoading(true);
    setError(null);
    try {
      // PATCH stats for characters whose stats were entered in the dialog.
      for (const entry of selected) {
        if (!needsStats(entry.char)) continue;
        const hp = parseInt(entry.hpMaxOverride, 10);
        const ac = parseInt(entry.acOverride, 10);
        const updated = await api.patchCharacter(entry.char.id, {
          hp_max: hp,
          hp_current: entry.char.hp_current ?? hp,
          ac,
        });
        upsertCharacter(mapCharacterResponse(updated));
      }

      const result = await api.startCombat(
        sessionId,
        selected.map((e) => e.char.id)
      );
      setCombat(mapCombatResponse(result));
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start combat");
    } finally {
      setLoading(false);
    }
  };

  const pcs = entries.filter((e) => e.char.type === "PC");
  const nonPcs = entries.filter((e) => e.char.type !== "PC");

  const renderEntry = (entry: CombatantEntry) => {
    const missing = entry.selected && needsStats(entry.char);
    return (
      <div
        key={entry.char.id}
        style={{
          background: "#1a1a2e",
          borderRadius: 5,
          padding: "7px 10px",
          marginBottom: 6,
          border: missing ? "1px solid #c0392b" : "1px solid transparent",
        }}
      >
        <label
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            cursor: "pointer",
          }}
        >
          <input
            type="checkbox"
            checked={entry.selected}
            onChange={(e) => update(entry.char.id, { selected: e.target.checked })}
            style={{ accentColor: "#7c6af7" }}
          />
          <span style={{ fontWeight: "bold", fontSize: 13 }}>{entry.char.name}</span>
          <span style={{ fontSize: 11, color: "#888" }}>
            {[entry.char.race, entry.char.char_class].filter(Boolean).join(" ")}
          </span>
          {!needsStats(entry.char) && (
            <span style={{ fontSize: 11, color: "#aaa", marginLeft: "auto" }}>
              HP {entry.char.hp_max} · AC {entry.char.ac}
            </span>
          )}
        </label>
        {entry.selected && needsStats(entry.char) && (
          <div
            style={{
              display: "flex",
              gap: 12,
              marginTop: 6,
              paddingLeft: 24,
            }}
          >
            <StatInput
              label="HP"
              value={entry.hpMaxOverride}
              onChange={(v) => update(entry.char.id, { hpMaxOverride: v })}
            />
            <StatInput
              label="AC"
              value={entry.acOverride}
              onChange={(v) => update(entry.char.id, { acOverride: v })}
            />
            <span style={{ fontSize: 11, color: "#c0392b", alignSelf: "center" }}>
              Required
            </span>
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        zIndex: 200,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          background: "#16213e",
          borderRadius: 8,
          padding: 20,
          width: 380,
          maxHeight: "80vh",
          overflow: "auto",
          boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
        }}
      >
        <h3 style={{ margin: "0 0 4px", fontSize: 16, color: "#e0d7ff" }}>Start Combat</h3>
        <p style={{ margin: "0 0 16px", fontSize: 12, color: "#888" }}>
          Select who joins the encounter. Enter HP and AC for characters without stats.
        </p>

        {pcs.length > 0 && (
          <>
            <div style={{ fontSize: 11, color: "#aaa", textTransform: "uppercase", marginBottom: 6 }}>
              Party
            </div>
            {pcs.map(renderEntry)}
          </>
        )}

        {nonPcs.length > 0 && (
          <>
            <div
              style={{
                fontSize: 11,
                color: "#aaa",
                textTransform: "uppercase",
                marginTop: 12,
                marginBottom: 6,
              }}
            >
              Monsters & NPCs
            </div>
            {nonPcs.map(renderEntry)}
          </>
        )}

        {entries.length === 0 && (
          <p style={{ color: "#555", fontSize: 13, textAlign: "center", padding: 16 }}>
            No characters in this world yet.
          </p>
        )}

        {error && (
          <p
            style={{
              color: "#f44336",
              fontSize: 12,
              background: "#2a1010",
              padding: "6px 10px",
              borderRadius: 4,
              margin: "8px 0",
            }}
          >
            {error}
          </p>
        )}

        <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: "8px 0",
              background: "#333",
              color: "#ccc",
              border: "1px solid #555",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleBegin}
            disabled={!canBegin}
            title={
              selected.length === 0
                ? "Select at least one combatant"
                : missingStats.length > 0
                  ? "Fill in HP and AC for all selected combatants"
                  : ""
            }
            style={{
              flex: 2,
              padding: "8px 0",
              background: canBegin ? "#c0392b" : "#555",
              color: canBegin ? "#fff" : "#888",
              border: "none",
              borderRadius: 4,
              cursor: canBegin ? "pointer" : "not-allowed",
              fontSize: 13,
              fontWeight: "bold",
            }}
          >
            {loading ? "Starting…" : `Begin Combat (${selected.length})`}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---- Main CombatTracker ----

export default function CombatTracker() {
  // Players see the initiative tracker live but only the DM gets the
  // controls — the server enforces this too (combat mutations are DM-only).
  const { sessionId, combat, setCombat, isDM } = useGameStore();
  const [showDialog, setShowDialog] = useState(false);
  const [weaponOptions, setWeaponOptions] = useState<WeaponMasteryOption[]>([]);

  // Weapon registry is static game data (not session-scoped) — fetch once
  // so the Attack action's weapon picker (PT-29) can tell which equipment
  // strings name a real weapon.
  useEffect(() => {
    if (!isDM) return;
    api
      .getCreationOptions()
      .then((opts) => setWeaponOptions(opts.weapon_mastery_options))
      .catch((err) => console.error("Failed to load weapon options:", err));
  }, [isDM]);

  const handleEnd = useCallback(async () => {
    if (!sessionId) return;
    try {
      await api.endCombat(sessionId);
      setCombat(null);
    } catch (err) {
      console.error("Failed to end combat:", err);
    }
  }, [sessionId, setCombat]);

  if (!combat) {
    return (
      <section>
        <h3
          style={{
            fontSize: 14,
            color: "#ccc",
            textTransform: "uppercase",
            margin: "0 0 8px",
          }}
        >
          Combat
        </h3>
        <p style={{ color: "#555", fontSize: 13 }}>No active combat.</p>
        {sessionId && isDM && (
          <>
            <button
              onClick={() => setShowDialog(true)}
              style={{
                padding: "6px 12px",
                background: "#c0392b",
                color: "#fff",
                border: "none",
                borderRadius: 4,
                cursor: "pointer",
              }}
            >
              Start Combat
            </button>
            {showDialog && (
              <StartCombatDialog
                sessionId={sessionId}
                onClose={() => setShowDialog(false)}
              />
            )}
          </>
        )}
      </section>
    );
  }

  const currentActorId = combat.combatants[combat.current_turn_index]?.char_id;

  return (
    <section>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 14, color: "#ccc", textTransform: "uppercase" }}>
          Combat · Round {combat.round_number}
        </h3>
        {isDM && (
        <button
          onClick={handleEnd}
          style={{
            padding: "4px 8px",
            background: "#555",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            fontSize: 12,
          }}
        >
          End
        </button>
        )}
      </div>
      {combat.combatants.length === 0 ? (
        <p style={{ color: "#555", fontSize: 13 }}>No combatants in initiative order.</p>
      ) : (
        combat.combatants.map((c) => (
          <CombatantRow key={c.char_id} combatant={c} />
        ))
      )}
      {sessionId && isDM && (
        <CombatActions
          key={currentActorId}
          sessionId={sessionId}
          currentActorId={currentActorId}
          combatants={combat.combatants}
          weaponOptions={weaponOptions}
          disabled={combat.combatants.length === 0}
        />
      )}
    </section>
  );
}
