// The one-pick-per-group editor (architecture: chargen-dnd, "the
// ability-score step in the existing slot vocabulary"): a Multi slot whose
// options carry a group renders one labeled select per group, holds one
// option id per group, and confirms only when every group has a pick.
// Grouping is the render-ready group string — the ids here are opaque.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { OptionView, Selection, SlotView } from './engine';
import { optionGroups, SlotCard } from './SlotCard';

const GROUPS = ['Alpha', 'Beta', 'Gamma'];
const VALUES = ['15', '14', '13'];

function option(group: string, value: string, available = true): OptionView {
  return {
    id: `x.${group.toLowerCase()}.${value}`,
    label: value,
    summary: '',
    details: [],
    available,
    unavailable_reason: available ? undefined : 'already placed',
    group,
  };
}

function groupedSlot(overrides: Partial<SlotView> = {}): SlotView {
  return {
    id: 'test.assign',
    label: 'Assign the array',
    kind: { kind: 'multi', count: GROUPS.length },
    presentation_hint: 'one-per-group',
    locked_reason: undefined,
    required: true,
    status: 'empty',
    meters: [],
    decision: undefined,
    options: GROUPS.flatMap((g) => VALUES.map((v) => option(g, v))),
    ...overrides,
  };
}

function renderCard(tentative: Selection | null, slot = groupedSlot()) {
  const onTentative = vi.fn();
  const onConfirm = vi.fn();
  render(
    <SlotCard
      slot={slot}
      tentative={tentative}
      onTentative={onTentative}
      onConfirm={onConfirm}
      onRequestChange={() => undefined}
      busy={false}
    />,
  );
  return { onTentative, onConfirm };
}

describe('optionGroups', () => {
  it('keeps first-appearance order and buckets the ungrouped remainder', () => {
    const groups = optionGroups([
      option('B', '1'),
      { ...option('A', '2'), group: undefined },
      option('A', '3'),
      option('B', '4'),
    ]);
    expect(groups.map((g) => g.group)).toEqual(['B', '', 'A']);
    expect(groups[0]?.options.map((o) => o.label)).toEqual(['1', '4']);
  });
});

describe('SlotCard one-per-group editor', () => {
  it('renders one select per distinct group, labeled by the group string', () => {
    renderCard(null);
    for (const group of GROUPS) {
      const select = screen.getByLabelText(group);
      expect(select.tagName).toBe('SELECT');
      // Only that group's options, plus the empty choice.
      expect(select.querySelectorAll('option')).toHaveLength(VALUES.length + 1);
    }
    expect(screen.getAllByRole('combobox')).toHaveLength(GROUPS.length);
  });

  it('holds one option id per group and replaces a group pick in place', async () => {
    const { onTentative } = renderCard({ kind: 'options', value: ['x.alpha.15', 'x.beta.14'] });
    expect(screen.getByLabelText('Alpha')).toHaveValue('x.alpha.15');
    expect(screen.getByLabelText('Beta')).toHaveValue('x.beta.14');
    expect(screen.getByLabelText('Gamma')).toHaveValue('');
    await userEvent.selectOptions(screen.getByLabelText('Alpha'), 'x.alpha.13');
    expect(onTentative).toHaveBeenLastCalledWith({
      kind: 'options',
      value: ['x.alpha.13', 'x.beta.14'],
    });
    await userEvent.selectOptions(screen.getByLabelText('Gamma'), 'x.gamma.15');
    expect(onTentative).toHaveBeenLastCalledWith({
      kind: 'options',
      value: ['x.alpha.15', 'x.beta.14', 'x.gamma.15'],
    });
  });

  it('clears the tentative selection when the last pick is emptied', async () => {
    const { onTentative } = renderCard({ kind: 'options', value: ['x.beta.14'] });
    await userEvent.selectOptions(screen.getByLabelText('Beta'), '');
    expect(onTentative).toHaveBeenLastCalledWith(null);
  });

  it('counts the groups still open and confirms only when every group has a pick', async () => {
    const { onConfirm } = renderCard({ kind: 'options', value: ['x.alpha.15'] });
    expect(screen.getByTestId('counter-test.assign')).toHaveTextContent('2 of 3 left');
    const confirm = screen.getByRole('button', { name: /confirm/i });
    expect(confirm).toBeDisabled();
    // The disabled control explains itself (layout sweep: no dead controls).
    const hint = document.getElementById(confirm.getAttribute('aria-describedby') ?? '');
    expect(hint).toHaveTextContent(/2 left/);

    render(<></>);
    const full = { kind: 'options' as const, value: ['x.alpha.15', 'x.beta.14', 'x.gamma.13'] };
    const second = renderCard(full);
    const counters = screen.getAllByTestId('counter-test.assign');
    expect(counters[counters.length - 1]).toHaveTextContent('All choices made');
    const buttons = screen.getAllByRole('button', { name: /confirm/i });
    const enabled = buttons[buttons.length - 1];
    expect(enabled).toBeEnabled();
    await userEvent.click(enabled as HTMLElement);
    expect(second.onConfirm).toHaveBeenCalledWith(full);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('greys an unavailable option with its reason instead of hiding it', () => {
    const slot = groupedSlot();
    slot.options = slot.options.map((o) =>
      o.id === 'x.alpha.14' ? { ...o, available: false, unavailable_reason: 'already placed' } : o,
    );
    renderCard(null, slot);
    const alpha = screen.getByLabelText('Alpha');
    const greyed = Array.from(alpha.querySelectorAll('option')).find(
      (o) => o.value === 'x.alpha.14',
    );
    expect(greyed).toBeDisabled();
    expect(greyed).toHaveTextContent('already placed');
    expect(greyed?.getAttribute('title')).toBe('already placed');
  });

  it('preloads the confirmed picks when the slot is partial (fix in place)', () => {
    const base = groupedSlot();
    renderCard(null, {
      ...base,
      status: 'partial',
      decision: {
        id: 'd1',
        slot: base.id,
        selection: { kind: 'options', value: ['x.gamma.13'] },
        source: 'player',
        order: 0,
      },
    });
    expect(screen.getByLabelText('Gamma')).toHaveValue('x.gamma.13');
    expect(screen.getByLabelText('Alpha')).toHaveValue('');
  });
});
