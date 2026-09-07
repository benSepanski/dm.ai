// Read-only render of the presentation contract. Knows nothing about games:
// sections, labeled values, optional detail lines.
import { useState } from 'react';
import type { SheetView } from './engine';

export function Sheet({
  sheet,
  compact,
  undecided,
}: {
  sheet: SheetView;
  compact?: boolean;
  /** Entry labels a card the player has not decided yet will set: those
   * values render as "?" with the pointer as their title, so no default
   * the player has not chosen is displayed anywhere on the screen. */
  undecided?: Record<string, string> | undefined;
}) {
  return (
    <div className={`sheet ${compact === true ? 'sheet-compact' : ''}`} data-testid="sheet">
      <header className="sheet-header">
        <h2>{sheet.name !== '' ? sheet.name : 'Unnamed adventurer'}</h2>
        {sheet.summary.map((line, i) => (
          <p key={i} className="sheet-summary">
            {line}
          </p>
        ))}
      </header>
      {sheet.sections.map((section) => (
        <section key={section.title} className="sheet-section">
          <h3>{section.title}</h3>
          <dl>
            {section.entries.map((entry, i) => (
              <SheetEntryRow
                key={`${entry.label}-${i}`}
                label={entry.label}
                value={entry.value}
                detail={entry.detail ?? null}
                compact={compact === true}
                pointer={undecided?.[entry.label] ?? null}
              />
            ))}
          </dl>
        </section>
      ))}
    </div>
  );
}

function SheetEntryRow({
  label,
  value,
  detail,
  compact,
  pointer,
}: {
  label: string;
  value: string;
  detail: string | null;
  compact: boolean;
  /** Set when a card the player has not decided yet will set this value. */
  pointer: string | null;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="sheet-entry">
      <dt>
        {label}
        {!compact && detail !== null && (
          <button
            type="button"
            className="sheet-detail-toggle"
            onClick={() => setOpen((o) => !o)}
            aria-label={`breakdown for ${label}`}
          >
            {open ? '−' : '+'}
          </button>
        )}
      </dt>
      <dd>
        {pointer === null ? (
          <span className="sheet-value">{value}</span>
        ) : (
          <span className="sheet-value sheet-undecided" title={pointer}>
            ?
          </span>
        )}
        {open && detail !== null && <span className="sheet-detail">{detail}</span>}
      </dd>
    </div>
  );
}
