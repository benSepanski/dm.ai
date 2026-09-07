import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { OptionView, Selection, SlotView } from './engine';
import { SlotCard } from './SlotCard';

// A roll card renders what the engine hands it: a history of render-ready
// entries, a roll button, and an entry grid sized from the slot's kind. It
// never adds two faces together.
function historyEntry(n: number, live: boolean, badge: string): OptionView {
  return {
    id: `set.${n}`,
    label: `total ${n}`,
    summary: live ? `Set ${n} — live` : `Set ${n} — superseded`,
    details: [`faces of set ${n}`],
    available: live,
    unavailable_reason: live ? undefined : 'superseded by a later roll',
    badge,
  };
}

function rollSlot(history: OptionView[], groups = 2, dice = 3, sides = 6): SlotView {
  return {
    id: 'toy.roll',
    label: 'Roll',
    kind: { kind: 'roll', sides, dice, groups },
    presentation_hint: undefined,
    locked_reason: undefined,
    required: true,
    status: history.length === 0 ? 'empty' : 'complete',
    meters: [],
    decision:
      history.length === 0
        ? undefined
        : {
            id: 'r',
            slot: 'toy.roll',
            selection: { kind: 'rolled', value: [] },
            source: 'player',
            order: 0,
          },
    options: history,
  };
}

function renderCard(slot: SlotView, tentative: Selection | null = null) {
  const onTentative = vi.fn();
  const onConfirm = vi.fn();
  const onRoll = vi.fn();
  render(
    <SlotCard
      slot={slot}
      tentative={tentative}
      onTentative={onTentative}
      onConfirm={onConfirm}
      onRoll={onRoll}
      onRequestChange={() => undefined}
      busy={false}
    />,
  );
  return { onTentative, onConfirm, onRoll };
}

describe('SlotCard roll editor', () => {
  it('offers a roll before anything is rolled and asks the server to roll', async () => {
    const { onRoll } = renderCard(rollSlot([]));
    expect(screen.getByText('Nothing rolled yet.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Roll' }));
    expect(onRoll).toHaveBeenCalledTimes(1);
  });

  it('renders the history as the engine describes it, live set marked, and stays open', () => {
    renderCard(
      rollSlot([historyEntry(1, false, 'rolled'), historyEntry(2, true, 'entered')]),
    );
    const history = screen.getByTestId('roll-history-toy.roll');
    const items = within(history).getAllByTestId('roll-set');
    expect(items[0]).toHaveTextContent('total 1');
    expect(items[0]).toHaveTextContent('rolled');
    expect(items[0]).toHaveTextContent('superseded');
    expect(items[1]).toHaveTextContent('total 2');
    expect(items[1]).toHaveTextContent('entered');
    expect(items[1]).toHaveAttribute('data-live', 'true');
    // Re-rolling appends: the card never shows a "Change…" button.
    expect(screen.queryByRole('button', { name: /change/i })).toBeNull();
    expect(screen.getByRole('button', { name: 'Roll again' })).toBeEnabled();
  });

  it('keeps every set visible with a count, the live one last', () => {
    renderCard(rollSlot([1, 2, 3, 4, 5].map((n) => historyEntry(n, n === 5, 'rolled'))));
    const history = screen.getByTestId('roll-history-toy.roll');
    expect(within(history).getAllByTestId('roll-set')).toHaveLength(5);
    expect(screen.getByTestId('roll-count-toy.roll')).toHaveTextContent('5 sets recorded');
    expect(within(history).getAllByTestId('roll-set')[4]).toHaveAttribute('data-live', 'true');
  });

  it('sizes the entry grid from the kind, previews complete entries, and refuses a face off the die', async () => {
    const { onTentative, onConfirm } = renderCard(rollSlot([], 2, 3, 6));
    await userEvent.click(screen.getByRole('button', { name: 'Enter dice' }));
    const inputs = screen.getAllByRole('spinbutton');
    expect(inputs).toHaveLength(6);
    const confirm = screen.getByRole('button', { name: /confirm entered dice/i });
    expect(confirm).toBeDisabled();
    expect(screen.getByText('Enter every die (2 sets of 3).')).toBeInTheDocument();
    // A 7 on a six-sided die: confirm stays disabled with the rule named,
    // and no tentative preview is offered.
    for (const [i, face] of ['6', '5', '3', '1', '2', '7'].entries()) {
      await userEvent.type(inputs[i]!, face);
    }
    expect(onTentative).toHaveBeenLastCalledWith(null);
    expect(confirm).toBeDisabled();
    expect(screen.getByText('Every face must be from 1 to 6.')).toBeInTheDocument();
    // Fix it: a complete, on-die grid previews and confirms as entered.
    await userEvent.clear(inputs[5]!);
    await userEvent.type(inputs[5]!, '4');
    expect(onTentative).toHaveBeenLastCalledWith({
      kind: 'rolled',
      value: [{ groups: [[6, 5, 3], [1, 2, 4]], origin: 'entered' }],
    });
    expect(confirm).toBeEnabled();
    await userEvent.click(confirm);
    expect(onConfirm).toHaveBeenCalledWith({
      kind: 'rolled',
      value: [{ groups: [[6, 5, 3], [1, 2, 4]], origin: 'entered' }],
    });
  });
});
