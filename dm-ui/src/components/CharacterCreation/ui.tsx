import type { CSSProperties, ReactNode } from "react";

// Shared look-and-feel for the creation wizard, matching the dashboard's
// dark inline-style theme.

export const ACCENT = "#7c6af7";

export const inputStyle: CSSProperties = {
  width: "100%",
  padding: "8px 10px",
  borderRadius: 4,
  border: "1px solid #444",
  background: "#111",
  color: "#fff",
  fontSize: 14,
  boxSizing: "border-box",
};

export const selectStyle: CSSProperties = {
  padding: "6px 8px",
  borderRadius: 4,
  border: "1px solid #444",
  background: "#111",
  color: "#fff",
  fontSize: 13,
};

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={{ marginBottom: 24 }}>
      <h3
        style={{
          margin: "0 0 8px",
          fontSize: 13,
          color: "#ccc",
          textTransform: "uppercase",
          letterSpacing: 0.5,
        }}
      >
        {title}
      </h3>
      {children}
    </section>
  );
}

export function Pill({
  label,
  selected,
  onClick,
  disabled = false,
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "6px 12px",
        borderRadius: 16,
        border: selected ? `1px solid ${ACCENT}` : "1px solid #444",
        background: selected ? `${ACCENT}33` : "#16162a",
        color: disabled ? "#666" : selected ? "#e0d7ff" : "#ccc",
        fontSize: 13,
        cursor: disabled ? "not-allowed" : "pointer",
      }}
    >
      {label}
    </button>
  );
}

export function PillRow({ children }: { children: ReactNode }) {
  return <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>{children}</div>;
}

export function DetailCard({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        marginTop: 10,
        padding: 12,
        background: "#16162a",
        border: "1px solid #333",
        borderRadius: 6,
        fontSize: 13,
        color: "#bbb",
        lineHeight: 1.5,
      }}
    >
      {children}
    </div>
  );
}

export function DetailLine({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ marginBottom: 4 }}>
      <span style={{ color: "#888" }}>{label}: </span>
      <span style={{ color: "#ddd" }}>{value}</span>
    </div>
  );
}
