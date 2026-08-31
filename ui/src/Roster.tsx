// The character roster: create / resume / view / delete (asks once, then
// moves the file to trash), quick build, random mint (class picker), clone
// (asks for the new name), quarantine reports, and the ORC notice.
import { useState } from 'react';
import type { RosterView } from './engine';
import { VersionBadge } from './VersionFlag';

export function Roster({
  roster,
  onCreate,
  onQuickBuild,
  onRandom,
  onClone,
  onOpen,
  onDelete,
}: {
  roster: RosterView;
  onCreate: (name: string | null) => void;
  /** One tap: a draft filled with the app's suggested Fighter build. */
  onQuickBuild: (name: string | null) => void;
  /** One tap: a random, legal, named draft of the picked class (null =
   * any). Resolves when the mint lands so the button can re-enable. */
  onRandom: (classId: string | null, name: string | null) => Promise<void>;
  /** Duplicate a character under a new name. */
  onClone: (id: string, name: string) => Promise<void>;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const [name, setName] = useState('');
  const [randomClass, setRandomClass] = useState<string>('any');
  const [minting, setMinting] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState<string | null>(null);
  const [cloning, setCloning] = useState<{ id: string; name: string } | null>(null);
  const [cloneBusy, setCloneBusy] = useState(false);
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
              {cloning?.id === entry.id ? (
                <form
                  className="roster-clone-confirm"
                  onSubmit={(e) => {
                    e.preventDefault();
                    const cloneName = cloning.name.trim();
                    if (cloneName === '') {
                      return;
                    }
                    setCloneBusy(true);
                    void onClone(entry.id, cloneName).finally(() => {
                      setCloneBusy(false);
                      setCloning(null);
                    });
                  }}
                >
                  <input
                    type="text"
                    aria-label={`name for the clone of ${entry.name}`}
                    value={cloning.name}
                    onChange={(e) => setCloning({ id: entry.id, name: e.target.value })}
                  />
                  <button type="submit" className="confirm" disabled={cloneBusy}>
                    Clone
                  </button>
                  <button type="button" onClick={() => setCloning(null)} disabled={cloneBusy}>
                    Cancel
                  </button>
                </form>
              ) : (
                <button
                  type="button"
                  className="roster-clone"
                  aria-label={`clone ${entry.name}`}
                  title="Duplicate this character as a new, independent copy"
                  onClick={() => setCloning({ id: entry.id, name: `${entry.name} (copy)` })}
                >
                  Clone
                </button>
              )}
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
        <span className="roster-random">
          <button
            type="button"
            className="quick-build"
            disabled={minting}
            title="Create a random, rules-legal draft — every choice rolled, review and finalize"
            onClick={() => {
              setMinting(true);
              void onRandom(
                randomClass === 'any' ? null : randomClass,
                name.trim() === '' ? null : name.trim(),
              ).finally(() => setMinting(false));
              setName('');
            }}
          >
            {minting ? 'Rolling…' : 'Random character'}
          </button>
          <select
            aria-label="random character class"
            title="Which class the random character rolls (part of Random character)"
            value={randomClass}
            onChange={(e) => setRandomClass(e.target.value)}
          >
            <option value="any">any class</option>
            {(roster.classes ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </span>
      </form>

      <footer className="license-notice">
        {roster.license_notice.split('\n\n').map((paragraph, i) => (
          <p key={i}>{paragraph}</p>
        ))}
      </footer>
    </div>
  );
}
