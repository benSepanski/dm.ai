// The breadth affordances (spec req 8): long option lists grow a text
// filter, the shopping list groups by category, and greyed options keep
// their reasons under filtering. All in-memory presentation — the option
// arrays arrive render-ready from the engine.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { OptionView, SlotView } from './engine';
import { FILTER_THRESHOLD, SlotCard } from './SlotCard';

function option(id: string, label: string, summary = '', available = true): OptionView {
  return {
    id,
    label,
    summary,
    details: [],
    available,
    unavailable_reason: available ? undefined : 'requires machinery from a later slice',
  };
}

function manyOptions(count: number, prefix = 'opt'): OptionView[] {
  return Array.from({ length: count }, (_, i) =>
    option(`${prefix}.${i}`, `${prefix} number ${i}`),
  );
}

function singleSlot(options: OptionView[], id = 'pf2e.test.single'): SlotView {
  return {
    id,
    label: 'Test choice',
    kind: { kind: 'single' },
    presentation_hint: undefined,
    locked_reason: undefined,
    required: true,
    status: 'empty',
    meters: [],
    decision: undefined,
    options,
  };
}

function renderSlot(slot: SlotView) {
  return render(
    <SlotCard
      slot={slot}
      tentative={null}
      onTentative={vi.fn()}
      onConfirm={vi.fn()}
      onRequestChange={() => undefined}
      busy={false}
    />,
  );
}

describe('option list text filter', () => {
  it('stays absent at or below the threshold', () => {
    renderSlot(singleSlot(manyOptions(FILTER_THRESHOLD)));
    expect(screen.queryByTestId('option-filter')).toBeNull();
  });

  it('appears past the threshold on a radio list', () => {
    renderSlot(singleSlot(manyOptions(FILTER_THRESHOLD + 1)));
    expect(screen.getByTestId('option-filter')).toBeInTheDocument();
  });

  it('appears past the threshold on a multi (checkbox) list', () => {
    renderSlot({
      ...singleSlot(manyOptions(20), 'pf2e.test.multi'),
      kind: { kind: 'multi', count: 3 },
    });
    expect(screen.getByTestId('option-filter')).toBeInTheDocument();
    // The counter is unaffected by the filter machinery.
    expect(screen.getByTestId('counter-pf2e.test.multi')).toHaveTextContent(
      '3 of 3 choices left',
    );
  });

  it('appears past the threshold on an add-row (list) picker', () => {
    renderSlot({
      ...singleSlot(manyOptions(20), 'pf2e.test.list'),
      kind: { kind: 'list' },
    });
    expect(screen.getByTestId('option-filter')).toBeInTheDocument();
    expect(screen.getAllByText('Add')).toHaveLength(20);
  });

  it('matches case-insensitively on name and summary', async () => {
    const options = [
      ...manyOptions(18),
      option('feat.acrobat', 'Steady Balance', 'Keep your feet on narrow surfaces'),
      option('feat.forager', 'Forager', 'Subsist in the wild'),
    ];
    renderSlot(singleSlot(options));

    // Label match, wrong case.
    await userEvent.type(screen.getByTestId('option-filter'), 'sTeAdY');
    expect(screen.getByText('Steady Balance')).toBeInTheDocument();
    expect(screen.queryByText('Forager')).toBeNull();
    expect(screen.getByRole('status')).toHaveTextContent('1 of 20 shown');

    // Summary match.
    await userEvent.clear(screen.getByTestId('option-filter'));
    await userEvent.type(screen.getByTestId('option-filter'), 'SUBSIST');
    expect(screen.getByText('Forager')).toBeInTheDocument();
    expect(screen.queryByText('Steady Balance')).toBeNull();
  });

  it('says so when nothing matches', async () => {
    renderSlot(singleSlot(manyOptions(16)));
    await userEvent.type(screen.getByTestId('option-filter'), 'zzz no such thing');
    expect(screen.getByRole('status')).toHaveTextContent('No options match');
    expect(screen.queryAllByRole('radio')).toHaveLength(0);
  });

  it('keeps greyed options visible, with their reasons, under filtering', async () => {
    const options = [
      ...manyOptions(18),
      option('feat.fey', 'Fey-touched Gnome', 'A cantrip chooser', false),
    ];
    renderSlot(singleSlot(options));
    await userEvent.type(screen.getByTestId('option-filter'), 'fey-touched');
    expect(screen.getByText('Fey-touched Gnome')).toBeInTheDocument();
    expect(screen.getByText('requires machinery from a later slice')).toBeInTheDocument();
    expect(screen.getByRole('radio')).toBeDisabled();
  });

  it('clears when the slot changes', async () => {
    const props = {
      tentative: null,
      onTentative: vi.fn(),
      onConfirm: vi.fn(),
      onRequestChange: () => undefined,
      busy: false,
    };
    const { rerender } = render(
      <SlotCard slot={singleSlot(manyOptions(20, 'alpha'), 'pf2e.a')} {...props} />,
    );
    await userEvent.type(screen.getByTestId('option-filter'), 'alpha number 3');
    expect(screen.getAllByRole('radio')).toHaveLength(1);

    rerender(<SlotCard slot={singleSlot(manyOptions(20, 'beta'), 'pf2e.b')} {...props} />);
    expect(screen.getByTestId('option-filter')).toHaveValue('');
    expect(screen.getAllByRole('radio')).toHaveLength(20);
  });
});

describe('shopping-list category grouping', () => {
  function shopSlot(): SlotView {
    return {
      ...singleSlot(
        [
          option('weapon.longsword', 'Longsword', '1 gp · Bulk 1'),
          option('weapon.dagger', 'Dagger', '2 sp · Bulk L'),
          option('armor.breastplate', 'Breastplate', '8 gp · Bulk 2'),
          option('shield.buckler', 'Buckler', '1 gp · Bulk L'),
          option('gear.rope', 'Rope', '5 sp · Bulk L'),
          ...manyOptions(14, 'gear'),
        ],
        'pf2e.equipment.extra',
      ),
      kind: { kind: 'list' },
      presentation_hint: 'shopping-list',
    };
  }

  it('renders one header per non-empty category', () => {
    renderSlot(shopSlot());
    const headings = screen
      .getAllByRole('heading', { level: 4 })
      .map((h) => h.textContent);
    expect(headings).toEqual(['Weapons', 'Armor', 'Shields', 'Adventuring gear']);
  });

  it('filters across every group and drops emptied headers', async () => {
    renderSlot(shopSlot());
    await userEvent.type(screen.getByTestId('option-filter'), 'buckler');
    const headings = screen
      .getAllByRole('heading', { level: 4 })
      .map((h) => h.textContent);
    expect(headings).toEqual(['Shields']);
    expect(screen.getByText('Buckler')).toBeInTheDocument();
    expect(screen.queryByText('Longsword')).toBeNull();
  });

  it('leaves a plain (ungrouped) list alone', () => {
    renderSlot({
      ...singleSlot(manyOptions(20), 'pf2e.test.plain-list'),
      kind: { kind: 'list' },
    });
    expect(screen.queryAllByRole('heading', { level: 4 })).toHaveLength(0);
  });
});
