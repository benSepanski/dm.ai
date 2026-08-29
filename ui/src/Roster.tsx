// The character roster: create / resume / view / delete (asks once, then
// moves the file to trash), quarantine reports, and the ORC notice.
import { useState } from 'react';
import type { RosterView } from './engine';
import { VersionBadge } from './VersionFlag';

export function Roster({
  roster,
  onCreate,
  onQuickBuild,
  onOpen,
  onDelete,
}: {
  roster: RosterView;
  onCreate: (name: string | null) => void;
  /** One tap: a draft filled with the app's suggested Fighter build. */
  onQuickBuild: (name: string | null) => void;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const [name, setName] = useState('');
  const [confirmingDelete, setConfirmingDelete] = useState<string | null>(null);
  return (
    <div className="roster">
      <header className="roster-header">
        <h1>dm.ai — characters</h1>
      </header>

      {roster.problems.length > 0 && (
        <div className="roster-problems" role="alert">
          {roster.problems.map((problem, i) => (
            <p key={i}>
              <strong>{problem.file}</strong> {problem.message}
            </p>
          ))}
        </div>
      )}

      {roster.entries.length === 0 ? (
        <p className="roster-empty">No characters yet — create the first one.</p>
      ) : (
        <ul className="roster-list">
          {roster.entries.map((entry) => (
            <li key={entry.id} className="roster-entry">
              <button type="button" className="roster-open" onClick={() => onOpen(entry.id)}>
                <span className="roster-name">{entry.name}</span>
                <span className="roster-summary">{entry.summary}</span>
                <span className="roster-state">
                  {entry.state.state === 'draft'
                    ? `Resume creating (${entry.state.resume_label})`
                    : 'View sheet'}
                </span>
                <VersionBadge status={entry.version} />
              </button>
              {confirmingDelete === entry.id ? (
                <span className="roster-delete-confirm">
                  Move to trash?
                  <button type="button" className="danger" onClick={() => onDelete(entry.id)}>
                    Delete
                  </button>
                  <button type="button" onClick={() => setConfirmingDelete(null)}>
                    Keep
                  </button>
                </span>
              ) : (
                <button
                  type="button"
                  className="roster-delete"
                  aria-label={`delete ${entry.name}`}
                  onClick={() => setConfirmingDelete(entry.id)}
                >
                  Delete
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <form
        className="roster-create"
        onSubmit={(e) => {
          e.preventDefault();
          onCreate(name.trim() === '' ? null : name.trim());
          setName('');
        }}
      >
        <input
          type="text"
          placeholder="Working name (optional)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button type="submit" className="confirm">
          Create character
        </button>
        <button
          type="button"
          className="quick-build"
          title="Create a draft with every choice pre-filled by dm.ai's suggested build — review, tweak, and finalize"
          onClick={() => {
            onQuickBuild(name.trim() === '' ? null : name.trim());
            setName('');
          }}
        >
          Quick build a Fighter
        </button>
      </form>

      <footer className="license-notice">
        {roster.license_notice.split('\n\n').map((paragraph, i) => (
          <p key={i}>{paragraph}</p>
        ))}
      </footer>
    </div>
  );
}
