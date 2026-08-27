// Read-only render of the presentation contract. Knows nothing about games:
// sections, labeled values, optional detail lines.
import { useState } from 'react';
import type { SheetView } from './engine';

export function Sheet({ sheet, compact }: { sheet: SheetView; compact?: boolean }) {
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
}: {
  label: string;
  value: string;
  detail: string | null;
  compact: boolean;
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
        <span className="sheet-value">{value}</span>
        {open && detail !== null && <span className="sheet-detail">{detail}</span>}
      </dd>
    </div>
  );
}
