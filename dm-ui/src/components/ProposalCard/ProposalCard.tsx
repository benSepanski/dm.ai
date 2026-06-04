import { useState } from "react";
import { api } from "../../api/client";
import { useGameStore, type ProposalData } from "../../store/gameStore";

const TYPE_LABELS: Record<string, string> = {
  location: "Location",
  character: "Character",
  dungeon: "Dungeon",
  dialogue: "Dialogue",
  combat_action: "Combat Action",
};

const TYPE_COLORS: Record<string, string> = {
  location: "#27ae60",
  character: "#2980b9",
  dungeon: "#7f8c8d",
  dialogue: "#e67e22",
  combat_action: "#c0392b",
};

function ContentField({ label, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined || value === "") return null;
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return (
    <div style={{ marginBottom: 6 }}>
      <span style={{ fontSize: 10, color: "#888", textTransform: "uppercase" }}>{label}</span>
      <p style={{ margin: "2px 0 0", fontSize: 12, color: "#ccc", lineHeight: 1.4 }}>{text}</p>
    </div>
  );
}

function ProposalContent({ content }: { content: Record<string, unknown> | null }) {
  if (!content) return <p style={{ fontSize: 12, color: "#666" }}>No content.</p>;
  // Show the most informative fields first; skip internal bookkeeping fields.
  const skip = new Set(["created_entity_id"]);
  const priority = ["name", "description", "type", "race", "class", "level", "alignment"];
  const keys = [
    ...priority.filter((k) => k in content && !skip.has(k)),
    ...Object.keys(content).filter((k) => !priority.includes(k) && !skip.has(k)),
  ];
  return (
    <div>
      {keys.map((k) => (
        <ContentField key={k} label={k} value={content[k]} />
      ))}
    </div>
  );
}

interface ProposalCardProps {
  proposal: ProposalData;
}

export default function ProposalCard({ proposal }: ProposalCardProps) {
  const { updateProposal } = useGameStore();
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isPending = proposal.status === "pending";
  const typeColor = TYPE_COLORS[proposal.type] ?? "#888";
  const typeLabel = TYPE_LABELS[proposal.type] ?? proposal.type;

  const handleAccept = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.acceptProposal(proposal.id, {
        dm_notes: notes.trim() || undefined,
      });
      updateProposal(proposal.id, { status: result.status, dm_notes: result.dm_notes });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Accept failed");
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.rejectProposal(proposal.id, {
        dm_notes: notes.trim() || undefined,
      });
      updateProposal(proposal.id, { status: result.status, dm_notes: result.dm_notes });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setLoading(false);
    }
  };

  const statusBadge = !isPending
    ? {
        accepted: { label: "Accepted", color: "#27ae60" },
        rejected: { label: "Rejected", color: "#c0392b" },
        modified: { label: "Modified", color: "#e67e22" },
      }[proposal.status]
    : null;

  return (
    <div
      style={{
        background: "#1a1a2e",
        borderRadius: 6,
        padding: 12,
        marginBottom: 8,
        borderLeft: `3px solid ${typeColor}`,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <span
          style={{
            fontSize: 11,
            padding: "2px 6px",
            borderRadius: 10,
            background: typeColor + "33",
            color: typeColor,
            textTransform: "uppercase",
            fontWeight: "bold",
          }}
        >
          {typeLabel}
        </span>
        {statusBadge && (
          <span
            style={{
              fontSize: 11,
              padding: "2px 6px",
              borderRadius: 10,
              background: statusBadge.color + "33",
              color: statusBadge.color,
            }}
          >
            {statusBadge.label}
          </span>
        )}
      </div>

      {/* Content */}
      <ProposalContent content={proposal.content} />

      {/* DM notes (resolved proposals) */}
      {!isPending && proposal.dm_notes && (
        <p style={{ margin: "6px 0 0", fontSize: 11, color: "#888", fontStyle: "italic" }}>
          DM: {proposal.dm_notes}
        </p>
      )}

      {/* Action area (pending only) */}
      {isPending && (
        <div style={{ marginTop: 10 }}>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="DM notes (optional)…"
            rows={2}
            style={{
              width: "100%",
              padding: "4px 6px",
              borderRadius: 4,
              border: "1px solid #444",
              background: "#111",
              color: "#ccc",
              fontSize: 11,
              resize: "vertical",
              boxSizing: "border-box",
              marginBottom: 6,
            }}
          />
          {error && (
            <p style={{ color: "#f44336", fontSize: 11, margin: "0 0 6px" }}>{error}</p>
          )}
          <div style={{ display: "flex", gap: 6 }}>
            <button
              onClick={handleAccept}
              disabled={loading}
              style={{
                flex: 1,
                padding: "5px 0",
                background: loading ? "#333" : "#1e8449",
                color: loading ? "#666" : "#fff",
                border: "none",
                borderRadius: 4,
                cursor: loading ? "not-allowed" : "pointer",
                fontSize: 12,
                fontWeight: "bold",
              }}
            >
              Accept
            </button>
            <button
              onClick={handleReject}
              disabled={loading}
              style={{
                flex: 1,
                padding: "5px 0",
                background: loading ? "#333" : "#7b241c",
                color: loading ? "#666" : "#fff",
                border: "none",
                borderRadius: 4,
                cursor: loading ? "not-allowed" : "pointer",
                fontSize: 12,
              }}
            >
              Reject
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
