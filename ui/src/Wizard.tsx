// The guided creation wizard: non-linear steps with badges, live checklist,
// live summary sidebar, confirm-per-choice durability, and the
// change-confirmed-choice flow with its dependent-clearing prompt.
import { useEffect, useMemo, useState } from 'react';
import {
  clearSlot,
  confirmDecision,
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

function badge(status: StepStatus): string {
  switch (status) {
    case 'complete':
      return '✓';
    case 'illegal':
      return '!';
    case 'incomplete':
      return '•';
  }
}

export function Wizard({
  initial,
  onFinalized,
  onExit,
}: {
  initial: DraftView;
  onFinalized: (sheet: SheetView) => void;
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

  // The displayed projection: server state plus every tentative selection,
  // recomputed by the local engine. Falls back to the server's projection
  // until the engine is ready (or if a hypothetical doesn't fold).
  const displayed: ProjectionView = useMemo(() => {
    const entries = Object.entries(pending);
    if (!engineReady || entries.length === 0) {
      return draft.projection;
    }
    try {
      const hypothetical: Decision[] = [...serverLog];
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
    try {
      const outcome = await confirmDecision(draft.id, draft.version, {
        id: newDecisionId(),
        slot,
        selection,
        source: 'player',
      });
      switch (outcome.outcome) {
        case 'confirmed':
          setDraft(outcome.draft);
          setPending((p) => Object.fromEntries(Object.entries(p).filter(([k]) => k !== slot)));
          break;
        case 'conflict':
          setDraft(outcome.current);
          setPending({});
          setNotice(
            'This draft was changed from another tab — the latest confirmed state has been reloaded.',
          );
          break;
        case 'rejected':
          setNotice(
            `The server refused that choice: ${outcome.reasons
              .map((r) => r.message)
              .join('; ')}`,
          );
          setDraft(outcome.draft);
          break;
      }
    } catch (error) {
      setNotice(
        `That choice did not save (${String(
          error instanceof Error ? error.message : error,
        )}). The server may be restarting — try again.`,
      );
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
          setPending({});
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
        <button type="button" className="wizard-back" onClick={onExit}>
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
        <button
          type="button"
          className="finalize confirm"
          disabled={!displayed.can_finalize || Object.keys(pending).length > 0 || busy}
          onClick={() => void finalize()}
          title={
            displayed.can_finalize
              ? 'Lock in this character'
              : 'Resolve every checklist item to finalize'
          }
        >
          Finalize character
        </button>
      </nav>

      <main className="wizard-main">
        {notice !== null && (
          <div className="notice" role="alert">
            {notice}
          </div>
        )}
        <h2>{step?.title}</h2>
        {step?.slots.map((slot) => (
          <SlotCard
            key={slot.id}
            slot={slot}
            tentative={pending[slot.id] ?? null}
            onTentative={(selection) =>
              setPending((p) => {
                if (selection === null) {
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
          />
        ))}
      </main>

      <aside className="wizard-side">
        <Checklist entries={displayed.checklist} onJump={jumpToEntry} />
        <Sheet sheet={displayed.sheet} compact />
      </aside>

      {clearDialog !== null && (
        <ClearConfirmDialog
          preview={clearDialog.preview}
          slotLabel={clearDialog.label}
          onConfirm={() => void executeClear()}
          onCancel={() => setClearDialog(null)}
        />
      )}
    </div>
  );
}
