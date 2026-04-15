import { useGameStore, type CharacterData } from "../../store/gameStore";

function abilityMod(score: number | null): string {
  if (score === null) return "–";
  const mod = Math.floor((score - 10) / 2);
  return mod >= 0 ? `+${mod}` : `${mod}`;
}

function HpBar({ current, max }: { current: number | null; max: number | null }) {
  if (current === null || max === null || max === 0) return null;
  const pct = Math.max(0, Math.min(100, (current / max) * 100));
  const color = pct > 50 ? "#4caf50" : pct > 25 ? "#ff9800" : "#f44336";
  return (
    <div style={{ background: "#333", borderRadius: 4, height: 8, margin: "4px 0" }}>
      <div
        style={{
          width: `${pct}%`,
          background: color,
          height: "100%",
          borderRadius: 4,
          transition: "width 0.3s",
        }}
      />
    </div>
  );
}

function AbilityGrid({ stats }: { stats: Record<string, number> | null }) {
  const abilities = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"];
  const labels = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 4,
        marginTop: 8,
      }}
    >
      {abilities.map((ab, i) => {
        const score = stats?.[ab] ?? null;
        return (
          <div
            key={ab}
            style={{
              textAlign: "center",
              background: "#222",
              borderRadius: 4,
              padding: "4px 2px",
            }}
          >
            <div style={{ fontSize: 10, color: "#888" }}>{labels[i]}</div>
            <div style={{ fontSize: 14, fontWeight: "bold" }}>{score ?? "–"}</div>
            <div style={{ fontSize: 11, color: "#aaa" }}>{abilityMod(score)}</div>
          </div>
        );
      })}
    </div>
  );
}

function CharacterEntry({ char }: { char: CharacterData }) {
  return (
    <div
      style={{
        background: "#1a1a2e",
        borderRadius: 6,
        padding: 10,
        marginBottom: 8,
      }}
    >
      <div style={{ fontWeight: "bold" }}>{char.name}</div>
      <div style={{ fontSize: 12, color: "#aaa" }}>
        {[char.race, char.char_class, char.level ? `Lvl ${char.level}` : null]
          .filter(Boolean)
          .join(" · ")}
      </div>
      <HpBar current={char.hp_current} max={char.hp_max} />
      <div style={{ fontSize: 12, color: "#ccc" }}>
        HP {char.hp_current ?? "–"}/{char.hp_max ?? "–"} · AC {char.ac ?? "–"}
      </div>
      <AbilityGrid stats={char.stats} />
    </div>
  );
}

export default function CharacterCard() {
  const { characters } = useGameStore();
  return (
    <section style={{ marginTop: 16 }}>
      <h3
        style={{
          margin: "0 0 8px",
          fontSize: 14,
          color: "#ccc",
          textTransform: "uppercase",
        }}
      >
        Party ({characters.length})
      </h3>
      {characters.length === 0 ? (
        <p style={{ color: "#555", fontSize: 13 }}>No characters loaded.</p>
      ) : (
        characters.map((c) => <CharacterEntry key={c.id} char={c} />)
      )}
    </section>
  );
}
