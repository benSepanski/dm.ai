// The grouped assignment editors: a Multi slot whose options carry a group
// renders one row per group and holds one option id per group. Under the
// `assign-pool` hint the values arrive as a tray of chips (one per listing
// — a value offered twice is two chips) placed by tap; under
// `assign-budget` each row steps through its options with the option's
// render-ready cost beside it. Grouping is the render-ready group string
// and chips match rows by position — the ids here are opaque.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { OptionView, Selection, SlotView } from './engine';
import { optionGroups, SlotCard } from './SlotCard';

const GROUPS = ['Alpha', 'Beta', 'Gamma'];
const VALUES = ['15', '14', '13'];

function option(group: string, value: string, id?: string, summary = ''): OptionView {
  return {
    id: id ?? `x.${group.toLowerCase()}.${value}`,
    label: value,
    summary,
    details: [],
    available: true,
    unavailable_reason: undefined,
    group,
  };
}

function groupedSlot(overrides: Partial<SlotView> = {}): SlotView {
  return {
    id: 'test.assign',
    label: 'Assign the array',
    kind: { kind: 'multi', count: GROUPS.length },
    presentation_hint: 'assign-pool',
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

const tray = () => within(screen.getByRole('group', { name: 'values to place' }));
const row = (group: string) => screen.getByTestId(`pool-row-${group}`);

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

describe('SlotCard pool editor', () => {
  it('renders one chip per listing and one row per group', () => {
    renderCard(null);
    expect(tray().getAllByRole('button')).toHaveLength(VALUES.length);
    for (const group of GROUPS) {
      expect(row(group)).toHaveAccessibleName(`${group}: empty`);
    }
    expect(screen.getByTestId('counter-test.assign')).toHaveTextContent('3 of 3 left');
  });

  it('places a held chip on a tapped row and greys the chip', async () => {
    const { onTentative } = renderCard(null);
    await userEvent.click(tray().getByRole('button', { name: '15' }));
    expect(tray().getByRole('button', { name: '15' })).toHaveAttribute('aria-pressed', 'true');
    expect(row('Beta')).toHaveTextContent('place here');
    await userEvent.click(row('Beta'));
    expect(onTentative).toHaveBeenLastCalledWith({ kind: 'options', value: ['x.beta.15'] });
  });

  it('shows placed values, lets a placed value return to the tray, and swaps on a filled row', async () => {
    const { onTentative } = renderCard({ kind: 'options', value: ['x.alpha.15', 'x.beta.14'] });
    expect(row('Alpha')).toHaveAccessibleName('Alpha: 15');
    expect(row('Beta')).toHaveAccessibleName('Beta: 14');
    expect(tray().getByRole('button', { name: '15' })).toBeDisabled();
    expect(tray().getByRole('button', { name: '14' })).toBeDisabled();
    expect(tray().getByRole('button', { name: '13' })).toBeEnabled();
    // Tap a placed value: it returns to the tray.
    await userEvent.click(row('Alpha'));
    expect(onTentative).toHaveBeenLastCalledWith({ kind: 'options', value: ['x.beta.14'] });
    // Hold 13 and tap the filled Beta row: 13 replaces 14 there.
    await userEvent.click(tray().getByRole('button', { name: '13' }));
    await userEvent.click(row('Beta'));
    expect(onTentative).toHaveBeenLastCalledWith({
      kind: 'options',
      value: ['x.alpha.15', 'x.beta.13'],
    });
  });

  it('shows a value offered twice as two chips and lets both be placed', async () => {
    const slot = groupedSlot({
      options: GROUPS.flatMap((g) => [
        option(g, '12'),
        option(g, '12', `x.${g.toLowerCase()}.12.2`),
        option(g, '8'),
      ]),
    });
    const { onTentative } = renderCard({ kind: 'options', value: ['x.alpha.12'] }, slot);
    const twelves = tray().getAllByRole('button', { name: '12' });
    expect(twelves).toHaveLength(2);
    expect(twelves[0]).toBeDisabled();
    expect(twelves[1]).toBeEnabled();
    await userEvent.click(twelves[1]!);
    await userEvent.click(row('Beta'));
    expect(onTentative).toHaveBeenLastCalledWith({
      kind: 'options',
      value: ['x.alpha.12', 'x.beta.12.2'],
    });
  });

  it('confirms only when every row has a value, and the disabled control explains itself', async () => {
    const { onConfirm } = renderCard({ kind: 'options', value: ['x.alpha.15'] });
    const confirm = screen.getByRole('button', { name: /confirm/i });
    expect(confirm).toBeDisabled();
    const hint = document.getElementById(confirm.getAttribute('aria-describedby') ?? '');
    expect(hint).toHaveTextContent(/2 left/);
    render(<></>);
    const full = { kind: 'options' as const, value: ['x.alpha.15', 'x.beta.14', 'x.gamma.13'] };
    const second = renderCard(full);
    const buttons = screen.getAllByRole('button', { name: /confirm/i });
    const enabled = buttons[buttons.length - 1];
    expect(enabled).toBeEnabled();
    await userEvent.click(enabled as HTMLElement);
    expect(second.onConfirm).toHaveBeenCalledWith(full);
    expect(onConfirm).not.toHaveBeenCalled();
  });
});

describe('SlotCard budget editor', () => {
  const COSTS = [
    ['8', '0 points'],
    ['9', '1 points'],
    ['10', '2 points'],
  ] as const;
  function budgetSlot(): SlotView {
    return groupedSlot({
      presentation_hint: 'assign-budget',
      options: GROUPS.flatMap((g) =>
        COSTS.map(([v, cost]) => option(g, v, `y.${g.toLowerCase()}.${v}`, cost)),
      ),
    });
  }

  it('steps each row through its options and shows the cost beside the value', async () => {
    const { onTentative } = renderCard(null, budgetSlot());
    expect(screen.getByTestId('budget-value-Alpha')).toHaveTextContent('—');
    expect(screen.getByRole('button', { name: 'Alpha lower' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Alpha higher' }));
    expect(onTentative).toHaveBeenLastCalledWith({ kind: 'options', value: ['y.alpha.8'] });
  });

  it('renders the current value, its cost, and disables the step at either end', async () => {
    const { onTentative } = renderCard({ kind: 'options', value: ['y.alpha.9', 'y.beta.10'] }, budgetSlot());
    expect(screen.getByTestId('budget-value-Alpha')).toHaveTextContent('9');
    expect(screen.getByTestId('budget-row-Alpha')).toHaveTextContent('1 points');
    expect(screen.getByRole('button', { name: 'Beta higher' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Alpha lower' }));
    expect(onTentative).toHaveBeenLastCalledWith({
      kind: 'options',
      value: ['y.alpha.8', 'y.beta.10'],
    });
    expect(screen.getByTestId('counter-test.assign')).toHaveTextContent('1 of 3 left');
  });
});
