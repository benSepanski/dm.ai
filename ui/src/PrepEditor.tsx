// The finalized sheet's one affordance: "Change prepared spells" — the
// pencil section of the sheet. Reopens just the prep picker: every prep
// slot renders as an open editor preloaded with the current selection
// (build choices stay locked elsewhere). Each confirm saves the WHOLE
// choice set through the prep route with the finalized lifecycle; the
// server re-validates natively (a finished sheet stays table-ready, so an
// incomplete or illegal set is rejected with its reasons) and returns the
// fresh view.
import { useState } from 'react';
import { savePrep } from './api';
import type { CharacterView, ScopedChoice, ScopedProjection, Selection } from './engine';
import { SlotCard } from './SlotCard';

export function PrepEditor({
  characterId,
  version,
  prep,
  prepBroken,
  onSaved,
}: {
  characterId: string;
  version: number;
  prep: ScopedProjection;
  prepBroken: boolean;
  onSaved: (character: CharacterView) => void;
}) {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState<Record<string, Selection>>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const serverChoices: ScopedChoice[] = prep.slots
    .filter((s) => s.decision !== undefined && s.decision !== null)
    .map((s) => ({ slot: s.id, selection: s.decision!.selection }));

  const confirmSlot = async (slot: string, selection: Selection) => {
    setBusy(true);
    setNotice(null);
    try {
      const choices = [...serverChoices.filter((c) => c.slot !== slot), { slot, selection }];
      const outcome = await savePrep(characterId, version, 'finalized', choices);
      switch (outcome.outcome) {
        case 'saved':
          setPending((p) => Object.fromEntries(Object.entries(p).filter(([k]) => k !== slot)));
          onSaved(outcome.character);
          break;
        case 'conflict':
          setNotice('This character was changed from another tab — reloading the latest state.');
          onSaved(outcome.character);
          break;
        case 'rejected':
          setNotice(
            `The server refused that preparation: ${outcome.reasons
              .map((r) => r.message)
              .join('; ')}`,
          );
          break;
      }
    } catch (error) {
      setNotice(
        `That preparation did not save (${String(
          error instanceof Error ? error.message : error,
        )}). The server may be restarting — try again.`,
      );
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <div className="prep-editor-toggle">
        {prepBroken && (
          <div className="notice" role="alert">
            The stored preparation section could not be read — it was left untouched. Open the
            editor to replace it wholesale.
          </div>
        )}
        <button type="button" className="prep-change" onClick={() => setOpen(true)}>
          Change prepared spells
        </button>
      </div>
    );
  }

  return (
    <section className="prep-editor">
      <header className="prep-editor-header">
        <h2>Prepared spells</h2>
        <button type="button" onClick={() => setOpen(false)} disabled={busy}>
          Done
        </button>
      </header>
      <p className="prep-editor-hint">
        Preparation is the pencil section of the sheet — change it any time. Build choices stay
        locked.
      </p>
      {notice !== null && (
        <div className="notice" role="alert">
          {notice}
        </div>
      )}
      {prep.slots.map((slot) => (
        <SlotCard
          key={slot.id}
          // The prep picker is always open: strip the confirmed decision so
          // the editor renders, preloaded with the current selection.
          slot={{ ...slot, decision: undefined, status: 'empty' }}
          tentative={pending[slot.id] ?? slot.decision?.selection ?? null}
          onTentative={(selection) =>
            setPending((p) => {
              if (selection === null) {
                return Object.fromEntries(Object.entries(p).filter(([k]) => k !== slot.id));
              }
              return { ...p, [slot.id]: selection };
            })
          }
          onConfirm={(selection) => void confirmSlot(slot.id, selection)}
          onRequestChange={() => undefined}
          busy={busy}
        />
      ))}
    </section>
  );
}
