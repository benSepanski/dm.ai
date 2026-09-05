// The rules-data version flag: a roster badge per status, and the review
// panel showing old vs new values with the explicit resolution actions
// (re-pin / accept / keep-old / resolve-errors). Nothing here computes game
// values — every difference and label arrives from the server's flag.
import { useState } from 'react';
import type { VersionAction } from './api';
import type { SheetDiff, VersionStatus } from './engine';

/** Before/after sheet values, rendered verbatim from the server's diff —
 * the one component for every "what changed" table (version review, the
 * level-up gains and deltas). */
export function SheetDiffTable({
  differences,
  oldHeading,
  newHeading,
}: {
  differences: SheetDiff[];
  oldHeading: string;
  newHeading: string;
}) {
  return (
    <table className="version-diff">
      <thead>
        <tr>
          <th scope="col">Value</th>
          <th scope="col">{oldHeading}</th>
          <th scope="col">{newHeading}</th>
        </tr>
      </thead>
      <tbody>
        {differences.map((d, i) => (
          <tr key={i}>
            <th scope="row">
              {d.section} — {d.label}
            </th>
            <td className="version-old">{d.old}</td>
            <td className="version-new">{d.new}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Small roster badge; renders nothing when the pin is current. */
export function VersionBadge({ status }: { status: VersionStatus }) {
  if (status.status === 'current') {
    return null;
  }
  if (status.status === 'kept_old') {
    return <span className="version-badge version-kept">Old data (kept)</span>;
  }
  if (status.status === 'unknown') {
    return <span className="version-badge version-unknown">Unknown data version</span>;
  }
  const label =
    status.outcome.kind === 'identical'
      ? 'Data updated — re-pin available'
      : status.outcome.kind === 'divergent'
        ? 'Review: values changed'
        : 'Review: replay failed';
  return <span className="version-badge version-review">{label}</span>;
}

/**
 * The flag detail panel. `isDraft` switches the action set: drafts resolve
 * (re-pin or reopen), finalized characters may also keep the old
 * derivation. `onResolve` performs one explicit action; refusals and
 * results surface through the caller.
 */
export function VersionFlagPanel({
  status,
  isDraft,
  busy,
  error,
  onResolve,
}: {
  status: VersionStatus;
  isDraft: boolean;
  busy: boolean;
  error: string | null;
  onResolve: (action: VersionAction) => void;
}) {
  const [confirmingReopen, setConfirmingReopen] = useState(false);
  if (status.status === 'current') {
    return null;
  }

  if (status.status === 'kept_old') {
    return (
      <div className="version-panel" role="status">
        <h2>Old rules data, kept on purpose</h2>
        <p>
          This character stays on its stored sheet from rules data{' '}
          <strong>{status.pinned}</strong> (recorded against {status.evaluated_against}). It will
          be flagged again only when the shipped data changes.
        </p>
      </div>
    );
  }

  if (status.status === 'unknown') {
    return (
      <div className="version-panel version-panel-warn" role="alert">
        <h2>Unknown rules-data version</h2>
        <p>
          This file pins <strong>{status.pinned}</strong>, which this build does not know (it
          ships {status.current}). Replay is impossible; the stored sheet loads read-only.
        </p>
      </div>
    );
  }

  const { pinned, current, outcome } = status;
  return (
    <div className="version-panel version-panel-warn" role="alert">
      <h2>Rules data changed</h2>
      <p>
        Built against <strong>{pinned}</strong>; this app now ships <strong>{current}</strong>.
      </p>

      {outcome.kind === 'identical' && (
        <>
          <p>
            Replaying every decision against the current data produces an identical sheet.
            Re-pinning records that in the file; nothing else changes.
          </p>
          <div className="version-actions">
            <button type="button" className="confirm" disabled={busy} onClick={() => onResolve('repin')}>
              Re-pin to {current}
            </button>
          </div>
        </>
      )}

      {outcome.kind === 'divergent' && (
        <>
          <p>
            Replaying against the current data changes the values below. The stored sheet is
            untouched until you accept; accepting records the old values in the file.
          </p>
          <SheetDiffTable
            differences={outcome.differences}
            oldHeading="Stored (old)"
            newHeading="Current data (new)"
          />
          <div className="version-actions">
            <button type="button" className="confirm" disabled={busy} onClick={() => onResolve('accept')}>
              Accept new values
            </button>
            {!isDraft && (
              <button type="button" disabled={busy} onClick={() => onResolve('keep-old')}>
                Keep old derivation
              </button>
            )}
          </div>
        </>
      )}

      {outcome.kind === 'replay_error' && (
        <>
          <p>
            The decision log no longer replays against current data — decision{' '}
            <strong>{outcome.failing_decision}</strong> on <strong>{outcome.slot}</strong> fails:{' '}
            {outcome.message}. Accepting is unavailable until this is resolved.
          </p>
          {isDraft ? (
            confirmingReopen ? (
              <>
                <p>Resolving reopens these choices (everything else is kept):</p>
                <ul className="version-reopen-list">
                  {(outcome.would_reopen ?? []).map((c, i) => (
                    <li key={i}>
                      <strong>{c.slot_label}</strong> — was {c.selection_label}
                    </li>
                  ))}
                </ul>
                <div className="version-actions">
                  <button
                    type="button"
                    className="danger"
                    disabled={busy}
                    onClick={() => onResolve('resolve-errors')}
                  >
                    Reopen these choices and re-pin
                  </button>
                  <button type="button" disabled={busy} onClick={() => setConfirmingReopen(false)}>
                    Not now
                  </button>
                </div>
              </>
            ) : (
              <div className="version-actions">
                <button type="button" className="confirm" disabled={busy} onClick={() => setConfirmingReopen(true)}>
                  Resolve…
                </button>
              </div>
            )
          ) : (
            <div className="version-actions">
              <button type="button" disabled={busy} onClick={() => onResolve('keep-old')}>
                Keep old derivation
              </button>
            </div>
          )}
        </>
      )}

      {error !== null && (
        <p className="version-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
