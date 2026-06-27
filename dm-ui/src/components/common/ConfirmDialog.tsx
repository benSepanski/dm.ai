interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

// In-app confirmation modal — a styled, non-blocking replacement for the native
// window.confirm(), which freezes the renderer and is auto-dismissed under
// browser automation. Mirrors the GameSettingsModal overlay pattern.
export default function ConfirmDialog({
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 200,
      }}
      onClick={busy ? undefined : onCancel}
    >
      <div
        style={{
          width: 380,
          background: "#16213e",
          border: "1px solid #333",
          borderRadius: 8,
          padding: 20,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: "0 0 8px", fontSize: 16, color: "#e0d7ff" }}>{title}</h3>
        <p style={{ margin: "0 0 20px", fontSize: 13, color: "#bbb", lineHeight: 1.5 }}>
          {message}
        </p>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button
            style={{
              padding: "8px 16px",
              background: "transparent",
              color: "#aaa",
              border: "1px solid #555",
              borderRadius: 4,
              cursor: busy ? "not-allowed" : "pointer",
            }}
            onClick={onCancel}
            disabled={busy}
          >
            {cancelLabel}
          </button>
          <button
            style={{
              padding: "8px 16px",
              background: busy ? "#444" : "#7c6af7",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              fontWeight: "bold",
              cursor: busy ? "not-allowed" : "pointer",
            }}
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? "…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
