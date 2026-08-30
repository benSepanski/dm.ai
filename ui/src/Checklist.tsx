// The persistent validation checklist: incomplete vs illegal, every entry
// naming its rule and jumping to the offending step/slot.
import type { ChecklistEntry } from './engine';

export function Checklist({
  entries,
  onJump,
  pendingCount = 0,
}: {
  entries: ChecklistEntry[];
  onJump: (entry: ChecklistEntry) => void;
  /** Slots with unconfirmed edits — a clean checklist is not "ready to
   * finalize" while any exist, and the banner must not claim it is. */
  pendingCount?: number;
}) {
  if (entries.length === 0) {
    return (
      <div className="checklist checklist-clear" data-testid="checklist">
        <p className="checklist-done">
          {pendingCount === 0
            ? '✓ Everything checks out — ready to finalize.'
            : '✓ Everything checks out — confirm your unconfirmed changes to finalize.'}
        </p>
      </div>
    );
  }
  const illegal = entries.filter((e) => e.severity === 'illegal');
  const incomplete = entries.filter((e) => e.severity === 'incomplete');
  return (
    <div className="checklist" data-testid="checklist">
      {illegal.length > 0 && (
        <section>
          <h3 className="checklist-heading illegal">Against the rules</h3>
          <ul>
            {illegal.map((entry, i) => (
              <ChecklistItem key={`illegal-${i}`} entry={entry} onJump={onJump} />
            ))}
          </ul>
        </section>
      )}
      {incomplete.length > 0 && (
        <section>
          <h3 className="checklist-heading incomplete">Still to do</h3>
          <ul>
            {incomplete.map((entry, i) => (
              <ChecklistItem key={`incomplete-${i}`} entry={entry} onJump={onJump} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function ChecklistItem({
  entry,
  onJump,
}: {
  entry: ChecklistEntry;
  onJump: (entry: ChecklistEntry) => void;
}) {
  return (
    <li className={`checklist-item ${entry.severity}`}>
      <button type="button" className="checklist-jump" onClick={() => onJump(entry)}>
        <span className="checklist-message">{entry.message}</span>
        <span className="checklist-meta">
          {entry.rule} · {entry.source}
        </span>
      </button>
    </li>
  );
}
