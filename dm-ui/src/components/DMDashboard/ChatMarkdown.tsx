import { CSSProperties } from "react";
import ReactMarkdown, { Components } from "react-markdown";
import remarkGfm from "remark-gfm";

// Renders AI/DM chat content as markdown. The model reliably emits markdown
// (**bold**, > blockquotes, --- rules, lists), which would otherwise show as
// raw syntax. react-markdown does not render raw HTML by default, so this is
// XSS-safe for untrusted model output.

const para: CSSProperties = { margin: "0 0 8px", lineHeight: 1.6, fontSize: 14 };

const components: Components = {
  p: ({ children }) => <p style={para}>{children}</p>,
  strong: ({ children }) => <strong style={{ fontWeight: 700 }}>{children}</strong>,
  em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
  blockquote: ({ children }) => (
    <blockquote
      style={{
        margin: "0 0 8px",
        padding: "2px 0 2px 12px",
        borderLeft: "3px solid #555",
        color: "#bbb",
        fontStyle: "italic",
      }}
    >
      {children}
    </blockquote>
  ),
  hr: () => <hr style={{ border: "none", borderTop: "1px solid #444", margin: "12px 0" }} />,
  ul: ({ children }) => <ul style={{ margin: "0 0 8px", paddingLeft: 20 }}>{children}</ul>,
  ol: ({ children }) => <ol style={{ margin: "0 0 8px", paddingLeft: 20 }}>{children}</ol>,
  li: ({ children }) => <li style={{ marginBottom: 2, lineHeight: 1.5 }}>{children}</li>,
  h1: ({ children }) => <h1 style={{ fontSize: 18, margin: "4px 0 8px" }}>{children}</h1>,
  h2: ({ children }) => <h2 style={{ fontSize: 16, margin: "4px 0 8px" }}>{children}</h2>,
  h3: ({ children }) => <h3 style={{ fontSize: 15, margin: "4px 0 6px" }}>{children}</h3>,
  code: ({ children }) => (
    <code
      style={{
        background: "#0d0d1a",
        borderRadius: 3,
        padding: "1px 4px",
        fontSize: 13,
        fontFamily: "monospace",
      }}
    >
      {children}
    </code>
  ),
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer" style={{ color: "#9b8cff" }}>
      {children}
    </a>
  ),
};

export default function ChatMarkdown({ content }: { content: string }) {
  return (
    // Strip the trailing margin of the last block so message padding stays even.
    <div style={{ marginBottom: -8 }}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
