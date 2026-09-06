// The guided creation wizard: non-linear steps with badges, live checklist,
// live summary sidebar, confirm-per-choice durability, and the
// change-confirmed-choice flow with its dependent-clearing prompt.
import { useEffect, useMemo, useState } from 'react';
import {
  abandonLevel,
  amendDecision,
  clearSlot,
  confirmDecision,
  fillRemaining,
  finalizeCharacter,
  setStep as apiSetStep,
} from './api';
import { Checklist } from './Checklist';
import type {
  ChecklistEntry,
  ClearPreview,
  Decision,
  DraftView,
  ProjectionView,
  Selection,
  SheetView,
  StepStatus,
} from './engine';
import { clearPreview as engineClearPreview, initEngine, project as engineProject } from './engine';
import { logFromProjection, newDecisionId } from './log';
import { Sheet } from './Sheet';
import { ClearConfirmDialog, SlotCard } from './SlotCard';
import { SheetDiffTable } from './VersionFlag';

function badge(status: StepStatus): string {
  switch (status) {
    case 'complete':
      return '✓';
    case 'illegal':
      return '!';
    case 'incomplete':
      return '•';
    case 'waiting':
      return '○';
  }
}

/** Semantic selection equality: option lists compare as sets, so
 * unchecking and re-checking a box (which reorders the array) is a no-op,
 * not an "unconfirmed change". */
export function sameSelection(a: Selection, b: Selection): boolean {
  if (a.kind !== b.kind) {
    return false;
  }
  if (a.kind === 'options' && b.kind === 'options') {
    return (
      a.value.length === b.value.length &&
      [...a.value].sort().join('\u0000') === [...b.value].sort().join('\u0000')
    );
  }
  return a.value === b.value;
}

/** An empty tentative selection on a slot with nothing saved is also a
 * no-op: typing into a field and deleting it all must not arm anything. */
export function isRealEdit(saved: Selection | undefined, selection: Selection): boolean {
  if (saved !== undefined) {
    return !sameSelection(saved, selection);
  }
  if (selection.kind === 'text') {
    return selection.value.trim() !== '';
  }
  if (selection.kind === 'options') {
    return selection.value.length > 0;
  }
  return true;
}

export function Wizard({
  initial,
  onFinalized,
  onAbandoned,
  onExit,
}: {
  initial: DraftView;
  onFinalized: (sheet: SheetView) => void;
  /** The draft's pending level was discarded (only offered when the
   * draft view carries one). */
  onAbandoned?: () => void;
  onExit: () => void;
}) {
  const [draft, setDraft] = useState<DraftView>(initial);
  const [currentStep, setCurrentStep] = useState<string>(initial.current_step);
  const [pending, setPending] = useState<Record<string, Selection>>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [engineReady, setEngineReady] = useState(false);
  const [clearDialog, setClearDialog] = useState<{
    slot: string;
    label: string;
    preview: ClearPreview;
  } | null>(null);
  // Transient in-card acknowledgment for saves that leave the slot open —
  // without it, a successful 4-of-5 confirm looks like a dead button.
  const [ack, setAck] = useState<{ slot: string; message: string } | null>(null);
  // A refusal pinned to its card: outcomes render where the player is
  // looking, never only in the top-of-step notice.
  const [cardError, setCardError] = useState<{ slot: string; message: string } | null>(null);
  // Guard against silently discarding real unconfirmed edits on exit.
  const [leaveDialog, setLeaveDialog] = useState(false);
  // The abandon confirmation for a pending level (lists what it discards).
  const [abandonDialog, setAbandonDialog] = useState(false);

  useEffect(() => {
    if (ack === null) {
      return;
    }
    const timer = setTimeout(() => setAck(null), 5000);
    return () => clearTimeout(timer);
  }, [ack]);

  useEffect(() => {
    let cancelled = false;
    initEngine()
      .then(() => {
        if (!cancelled) {
          setEngineReady(true);
        }
      })
      .catch(() => {
        // Previews degrade to server-confirmed state; confirms still work.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const serverLog = useMemo(() => logFromProjection(draft.projection), [draft]);

  // A tentative edit identical to the confirmed selection is not an edit.
  // Pruning on every draft change keeps `pending` meaning exactly "differs
  // from what is saved" — the finalize gate and the unconfirmed-changes
  // chip both rely on that.
  useEffect(() => {
    setPending((p) => {
      const confirmed = new Map(
        logFromProjection(draft.projection).map((d) => [d.slot, d.selection]),
      );
      const kept = Object.entries(p).filter(([slot, selection]) =>
        isRealEdit(confirmed.get(slot), selection),
      );
      return kept.length === Object.keys(p).length ? p : Object.fromEntries(kept);
    });
  }, [draft]);

  // The slots with real unconfirmed edits, with labels for the chip.
  const pendingSlots = useMemo(() => {
    const bySlot = new Map(
      draft.projection.steps.flatMap((st) =>
        st.slots.map((sl) => [sl.id, { label: sl.label, step: st.id }] as const),
      ),
    );
    return Object.keys(pending).flatMap((id) => {
      const found = bySlot.get(id);
      return found === undefined ? [] : [{ id, label: found.label, step: found.step }];
    });
  }, [pending, draft]);

  // The displayed projection: server state plus every tentative selection,
  // recomputed by the local engine. Falls back to the server's projection
  // until the engine is ready (or if a hypothetical doesn't fold).
  const displayed: ProjectionView = useMemo(() => {
    const entries = Object.entries(pending);
    if (!engineReady || entries.length === 0) {
      return draft.projection;
    }
    try {
      // A tentative selection REPLACES the slot's confirmed decision in the
      // hypothetical (amend semantics) — keeping both would double-count a
      // partial slot's picks.
      const hypothetical: Decision[] = serverLog.filter(
        (d) => pending[d.slot] === undefined,
      );
      for (const [slot, selection] of entries) {
        hypothetical.push({
          id: `preview-${slot}`,
          slot,
          selection,
          source: 'player',
          order: hypothetical.length,
        });
      }
      return engineProject(hypothetical);
    } catch {
      return draft.projection;
    }
  }, [draft, pending, serverLog, engineReady]);

  // Step badges, checklist, and the sheet react to tentative selections;
  // the slot editors themselves render the server-confirmed state, so a
  // choice never looks confirmed before it is durably saved.
  const steps = displayed.steps;
  const step =
    draft.projection.steps.find((s) => s.id === currentStep) ?? draft.projection.steps[0];

  const gotoStep = (stepId: string) => {
    setCurrentStep(stepId);
    // Persist the cursor so resume lands here; fire-and-forget.
    void apiSetStep(draft.id, draft.version, stepId).catch(() => undefined);
  };

  const jumpToEntry = (entry: ChecklistEntry) => {
    gotoStep(entry.step);
    requestAnimationFrame(() => {
      document.querySelector(`[data-slot="${entry.slot}"]`)?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    });
  };

  const confirm = async (slot: string, selection: Selection) => {
    setBusy(true);
    setNotice(null);
    setCardError(null);
    try {
      const occupied = serverLog.some((d) => d.slot === slot);
      const send = occupied ? amendDecision : confirmDecision;
      const outcome = await send(draft.id, draft.version, {
        id: newDecisionId(),
        slot,
        selection,
        source: 'player',
      });
      switch (outcome.outcome) {
        case 'confirmed': {
          setDraft(outcome.draft);
          setPending((p) => Object.fromEntries(Object.entries(p).filter(([k]) => k !== slot)));
          // Saved but still unfinished? Say so at the card, or the save is
          // visually indistinguishable from a dead click.
          const saved = outcome.draft.projection.steps
            .flatMap((s) => s.slots)
            .find((s) => s.id === slot);
          if (saved !== undefined && saved.status === 'illegal') {
            // Durably saved, but a rule is broken: say so in the error
            // register, not as a green success.
            const remainder = outcome.draft.projection.checklist.find(
              (e) => e.slot === slot && e.severity === 'illegal',
            );
            setCardError({
              slot,
              message: `Saved, but against the rules${
                remainder !== undefined ? `: ${remainder.message}` : ''
              }`,
            });
          } else if (saved !== undefined && saved.status !== 'complete') {
            const remainder = outcome.draft.projection.checklist.find((e) => e.slot === slot);
            setAck({
              slot,
              message:
                remainder !== undefined ? `Saved — ${remainder.message}` : 'Saved',
            });
          } else {
            setAck(null);
          }
          break;
        }
        case 'conflict':
          // Reload the truth but keep in-progress edits: the prune effect
          // drops any that now match, and the chip shows the rest.
          setDraft(outcome.current);
          setNotice(
            'This draft was changed from another tab — the latest confirmed state has been reloaded.',
          );
          break;
        case 'rejected':
          setCardError({
            slot,
            message: outcome.reasons.map((r) => r.message).join('; '),
          });
          setDraft(outcome.draft);
          break;
      }
    } catch (error) {
      setCardError({
        slot,
        message: `That choice did not save (${String(
          error instanceof Error ? error.message : error,
        )}). The server may be restarting — try again.`,
      });
    } finally {
      setBusy(false);
    }
  };

  const requestChange = (slot: string, label: string) => {
    try {
      const preview = engineReady
        ? engineClearPreview(serverLog, slot)
        : { slot, cleared: serverLog.filter((d) => d.slot === slot).map((d) => ({
            slot: d.slot,
            slot_label: label,
            selection_label: 'this choice',
            selection: d.selection,
          })) };
      setClearDialog({ slot, label, preview });
    } catch (error) {
      setNotice(String(error instanceof Error ? error.message : error));
    }
  };

  const executeClear = async () => {
    if (clearDialog === null) {
      return;
    }
    setBusy(true);
    setNotice(null);
    try {
      const outcome = await clearSlot(draft.id, draft.version, clearDialog.slot);
      if (outcome.outcome === 'cleared') {
        setDraft(outcome.draft);
        setPending({});
      } else {
        setDraft(outcome.current);
        setPending({});
        setNotice('This draft was changed from another tab — reloaded.');
      }
    } catch (error) {
      setNotice(String(error instanceof Error ? error.message : error));
    } finally {
      setClearDialog(null);
      setBusy(false);
    }
  };

  const fillWithSuggestions = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const outcome = await fillRemaining(draft.id, draft.version);
      if (outcome.outcome === 'filled') {
        setDraft(outcome.draft);
        setPending({});
        setNotice(
          outcome.unresolved.length === 0
            ? 'Every open choice was filled with a suggestion — review the badges and finalize.'
            : `Filled what was legal — ${outcome.unresolved.length} slot(s) still need you: ${outcome.unresolved
                .map((u) => u.label)
                .join(', ')}. The checklist has the details.`,
        );
      } else {
        setDraft(outcome.current);
        setPending({});
        setNotice('This draft was changed from another tab — the latest state has been reloaded.');
      }
    } catch (error) {
      setNotice(String(error instanceof Error ? error.message : error));
    } finally {
      setBusy(false);
    }
  };

  const executeAbandon = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const outcome = await abandonLevel(draft.id, draft.version);
      if (outcome.outcome === 'abandoned') {
        onAbandoned?.();
      } else {
        setNotice('This character was changed from another tab — reloaded.');
        onAbandoned?.();
      }
    } catch (error) {
      setNotice(String(error instanceof Error ? error.message : error));
    } finally {
      setAbandonDialog(false);
      setBusy(false);
    }
  };

  const finalize = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const outcome = await finalizeCharacter(draft.id, draft.version);
      switch (outcome.outcome) {
        case 'finalized':
          onFinalized(outcome.sheet);
          break;
        case 'blocked':
          setNotice(
            `Not finished yet — ${outcome.reasons.length} item(s) on the checklist remain.`,
          );
          break;
        case 'conflict':
          setDraft(outcome.current);
          setNotice('This draft was changed from another tab — reloaded.');
          break;
      }
    } catch (error) {
      setNotice(String(error instanceof Error ? error.message : error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="wizard">
      <nav className="wizard-steps">
        <button
          type="button"
          className="wizard-back"
          onClick={() => (pendingSlots.length > 0 ? setLeaveDialog(true) : onExit())}
        >
          ← Roster
        </button>
        <ol>
          {steps.map((s, index) => (
            <li key={s.id}>
              <button
                type="button"
                className={`step-link ${s.id === step?.id ? 'active' : ''} status-${s.status}`}
                onClick={() => gotoStep(s.id)}
              >
                <span className={`step-badge status-${s.status}`}>{badge(s.status)}</span>
                <span>
                  {index + 1}. {s.title}
                </span>
              </button>
            </li>
          ))}
        </ol>
        {!displayed.can_finalize && draft.level_up === undefined && (
          // Hidden (not disabled-with-no-reason) once there is nothing
          // left to fill — or when suggestions don't apply (a pending
          // level: suggested builds cover creation only): a dead control
          // the player can't explain is a banned state.
          <button
            type="button"
            className="fill-remaining"
            disabled={busy}
            data-busy={busy || undefined}
            onClick={() => void fillWithSuggestions()}
            title="Fill every open choice with dm.ai's suggested build — your confirmed choices never move"
          >
            Fill remaining with suggestions
          </button>
        )}
        <button
          type="button"
          className="finalize confirm"
          disabled={!draft.projection.can_finalize || pendingSlots.length > 0 || busy}
          data-busy={busy || undefined}
          aria-describedby={
            !draft.projection.can_finalize || pendingSlots.length > 0
              ? 'finalize-blockers'
              : undefined
          }
          onClick={() => void finalize()}
          title={
            draft.projection.can_finalize && pendingSlots.length === 0
              ? 'Lock in this character'
              : undefined
          }
        >
          {draft.level_up === undefined
            ? 'Finalize character'
            : `Finalize level ${draft.level_up.level}`}
        </button>
        {draft.level_up !== undefined && (
          <button
            type="button"
            className="abandon-level"
            disabled={busy}
            onClick={() => setAbandonDialog(true)}
            title="Discard this level's choices; the finalized character is untouched"
          >
            Abandon level {draft.level_up.level}
          </button>
        )}
        {pendingSlots.length > 0 ? (
          <div className="finalize-blockers pending-chip" id="finalize-blockers" role="status">
            <p>Unconfirmed changes:</p>
            <ul>
              {pendingSlots.map((entry) => (
                <li key={entry.id}>
                  <button
                    type="button"
                    className="pending-jump"
                    onClick={() => {
                      gotoStep(entry.step);
                      requestAnimationFrame(() => {
                        document
                          .querySelector(`[data-slot="${entry.id}"]`)
                          ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                      });
                    }}
                  >
                    {entry.label}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          !draft.projection.can_finalize && (
            <p className="finalize-blockers" id="finalize-blockers">
              Resolve every checklist item to finalize.
            </p>
          )
        )}
      </nav>

      <main className="wizard-main">
        {notice !== null && (
          <div className="notice" role="alert">
            {notice}
          </div>
        )}
        {draft.level_up !== undefined && (
          <section className="level-gains" aria-label="level gains">
            <h2>At level {draft.level_up.level} you gain…</h2>
            <p className="level-gains-intro">
              These change on their own the moment you reach level{' '}
              {draft.level_up.level} — before any choice below. Every value on
              the sheet derives from your level and your choices; the Why column
              is each value's own formula.
            </p>
            {draft.level_up.gains.length === 0 ? (
              <p>Only the choices below — nothing changes on its own.</p>
            ) : (
              <SheetDiffTable
                differences={draft.level_up.gains}
                oldHeading={`Level ${draft.level_up.level - 1}`}
                newHeading={`Level ${draft.level_up.level}`}
              />
            )}
          </section>
        )}
        <h2>{step?.title}</h2>
        {step?.slots.map((slot) => (
          <SlotCard
            key={slot.id}
            slot={slot}
            live={displayed.steps
              .flatMap((s) => s.slots)
              .find((s) => s.id === slot.id)}
            tentative={pending[slot.id] ?? null}
            onTentative={(selection) =>
              setPending((p) => {
                if (selection === null || !isRealEdit(slot.decision?.selection, selection)) {
                  return Object.fromEntries(
                    Object.entries(p).filter(([k]) => k !== slot.id),
                  );
                }
                return { ...p, [slot.id]: selection };
              })
            }
            onConfirm={(selection) => void confirm(slot.id, selection)}
            onRequestChange={() => requestChange(slot.id, slot.label)}
            busy={busy}
            ack={ack !== null && ack.slot === slot.id ? ack.message : null}
            error={
              cardError !== null && cardError.slot === slot.id
                ? cardError.message
                : // A slot made illegal from elsewhere (a school change, a
                  // background grant) explains itself at the card too, not
                  // only in the sidebar checklist.
                  (displayed.checklist.find(
                    (e) => e.slot === slot.id && e.severity === 'illegal',
                  )?.message ?? null)
            }
          />
        ))}
      </main>

      <aside className="wizard-side">
        <Checklist
          entries={displayed.checklist}
          onJump={jumpToEntry}
          pendingCount={pendingSlots.length}
        />
        {draft.level_up !== undefined &&
          draft.level_up.deltas.length > 0 &&
          JSON.stringify(draft.level_up.deltas) !== JSON.stringify(draft.level_up.gains) && (
          // Shown once the level's choices changed something beyond the
          // automatic gains — until then it would only repeat the panel.
          <section className="level-deltas" aria-label="level changes so far">
            <h3>Changes so far (with your choices)</h3>
            <SheetDiffTable
              differences={draft.level_up.deltas}
              oldHeading="Before"
              newHeading="After"
            />
          </section>
        )}
        <Sheet sheet={displayed.sheet} compact />
      </aside>

      {leaveDialog && (
        <div className="modal-backdrop">
          <div className="modal" role="dialog" aria-modal="true">
            <h3>Unconfirmed changes</h3>
            <p>
              You have unconfirmed changes in:{' '}
              {pendingSlots.map((entry) => entry.label).join(', ')}. Leaving
              discards them (your confirmed choices are safe).
            </p>
            <div className="modal-actions">
              <button type="button" onClick={() => setLeaveDialog(false)}>
                Stay
              </button>
              <button
                type="button"
                className="danger"
                onClick={() => {
                  setLeaveDialog(false);
                  onExit();
                }}
              >
                Discard changes and leave
              </button>
            </div>
          </div>
        </div>
      )}
      {clearDialog !== null && (
        <ClearConfirmDialog
          preview={clearDialog.preview}
          slotLabel={clearDialog.label}
          onConfirm={() => void executeClear()}
          onCancel={() => setClearDialog(null)}
        />
      )}
      {abandonDialog && draft.level_up !== undefined && (
        <ClearConfirmDialog
          preview={{ slot: 'level-up', cleared: draft.level_up.pending }}
          slotLabel={`level ${draft.level_up.level}`}
          title={`Abandon level ${draft.level_up.level}?`}
          intro="This discards the level's choices so far; the finalized character is untouched:"
          confirmLabel="Discard and go back"
          onConfirm={() => void executeAbandon()}
          onCancel={() => setAbandonDialog(false)}
        />
      )}
    </div>
  );
}
