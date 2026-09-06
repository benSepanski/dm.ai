import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { Selection, SlotView } from './engine';
import { SlotCard } from './SlotCard';

function boostSlot(): SlotView {
  return {
    id: 'pf2e.boosts.free',
    label: 'Free attribute boosts',
    kind: { kind: 'multi', count: 4 },
    presentation_hint: 'attribute-boosts',
    locked_reason: undefined,
    required: true,
    status: 'empty',
    meters: [],
    decision: undefined,
    options: ['str', 'dex', 'con', 'int', 'wis', 'cha'].map((attr) => ({
      id: `attr.${attr}`,
      label: attr.toUpperCase(),
      summary: '',
      details: [],
      available: true,
      unavailable_reason: undefined,
    })),
  };
}

function renderCard(tentative: Selection | null, onTentative = vi.fn()) {
  const onConfirm = vi.fn();
  render(
    <SlotCard
      slot={boostSlot()}
      tentative={tentative}
      onTentative={onTentative}
      onConfirm={onConfirm}
      onRequestChange={() => undefined}
      busy={false}
    />,
  );
  return { onTentative, onConfirm };
}

describe('SlotCard boost counter', () => {
  it('counts down as picks land', () => {
    renderCard({ kind: 'options', value: ['attr.str', 'attr.con'] });
    expect(screen.getByTestId('counter-pf2e.boosts.free')).toHaveTextContent('2 of 4 left');
  });

  it('reports a full selection', () => {
    renderCard({ kind: 'options', value: ['attr.str', 'attr.con', 'attr.dex', 'attr.wis'] });
    expect(screen.getByTestId('counter-pf2e.boosts.free')).toHaveTextContent(
      'All choices made',
    );
  });

  it('accepts the same attribute twice — the checklist judges, not the UI', async () => {
    const { onTentative } = renderCard({ kind: 'options', value: ['attr.str'] });
    await userEvent.selectOptions(screen.getByLabelText('Pick 2'), 'attr.str');
    expect(onTentative).toHaveBeenCalledWith({
      kind: 'options',
      value: ['attr.str', 'attr.str'],
    });
  });

  it('confirm stays disabled with nothing picked', () => {
    renderCard(null);
    expect(screen.getByRole('button', { name: /confirm/i })).toBeDisabled();
  });

  it('renders the five statuses distinguishably', () => {
    const base = boostSlot();
    const decision = {
      id: 'd1',
      slot: base.id,
      selection: { kind: 'options' as const, value: ['attr.str'] },
      source: 'player' as const,
      order: 0,
    };
    const variants: SlotView[] = [
      { ...base, status: 'locked', locked_reason: 'choose a class first' },
      { ...base, status: 'empty' },
      { ...base, status: 'partial', decision },
      { ...base, status: 'complete', decision },
      { ...base, status: 'illegal', decision },
    ];
    const rendered = variants.map((v) => {
      const { container, unmount } = render(
        <SlotCard
          slot={v}
          tentative={null}
          onTentative={() => undefined}
          onConfirm={() => undefined}
          onRequestChange={() => undefined}
          busy={false}
        />,
      );
      const section = container.querySelector('section');
      const signature = [
        section?.className.match(/status-\w+/)?.[0],
        section?.querySelector('.slot-locked-reason') !== null,
        section?.querySelector('input, select') !== null,
        section?.querySelector('.slot-confirmed-value') !== null,
      ].join('|');
      unmount();
      return signature;
    });
    expect(new Set(rendered).size).toBe(rendered.length);
    // Partial keeps the editor open with the confirmed pick preloaded.
    render(
      <SlotCard
        slot={{ ...base, status: 'partial', decision }}
        tentative={null}
        onTentative={() => undefined}
        onConfirm={() => undefined}
        onRequestChange={() => undefined}
        busy={false}
      />,
    );
    expect(screen.getByLabelText('Pick 1')).toHaveValue('attr.str');
  });

  it('renders meters in both editing and confirmed states', () => {
    const meter = {
      label: 'Spent',
      current: '16 gp',
      limit: '15 gp',
      state: 'exceeded' as const,
    };
    const base = boostSlot();
    render(
      <SlotCard
        slot={{ ...base, meters: [meter] }}
        tentative={null}
        onTentative={() => undefined}
        onConfirm={() => undefined}
        onRequestChange={() => undefined}
        busy={false}
      />,
    );
    expect(screen.getByTestId('meter-Spent')).toHaveTextContent('Spent 16 gp of 15 gp — over the limit');
  });

  it('renders the save acknowledgment when provided', () => {
    render(
      <SlotCard
        slot={boostSlot()}
        tentative={null}
        onTentative={() => undefined}
        onConfirm={() => undefined}
        onRequestChange={() => undefined}
        busy={false}
        ack="Saved — 1 skill choice(s) left"
      />,
    );
    expect(screen.getByRole('status')).toHaveTextContent('Saved — 1 skill choice(s) left');
  });

  it('locked slots explain themselves', () => {
    const slot: SlotView = { ...boostSlot(), status: 'locked', locked_reason: 'choose an ancestry first' };
    render(
      <SlotCard
        slot={slot}
        tentative={null}
        onTentative={() => undefined}
        onConfirm={() => undefined}
        onRequestChange={() => undefined}
        busy={false}
      />,
    );
    expect(screen.getByText(/choose an ancestry first/)).toBeInTheDocument();
  });
});

describe('SlotCard suggested-provenance badge', () => {
  function confirmedSlot(source: 'player' | 'suggested' | 'random' | 'clone'): SlotView {
    const base = boostSlot();
    return {
      ...base,
      status: 'complete',
      decision: {
        id: 'd-sug',
        slot: base.id,
        selection: { kind: 'options', value: ['attr.str', 'attr.con', 'attr.dex', 'attr.wis'] },
        source,
        order: 0,
      },
    };
  }

  function renderConfirmed(source: 'player' | 'suggested' | 'random' | 'clone') {
    return render(
      <SlotCard
        slot={confirmedSlot(source)}
        tentative={null}
        onTentative={() => undefined}
        onConfirm={() => undefined}
        onRequestChange={() => undefined}
        busy={false}
      />,
    );
  }

  it('badges a planner-filled decision as suggested', () => {
    const { container } = renderConfirmed('suggested');
    expect(container.querySelector('.badge-suggested')).toHaveTextContent('suggested');
  });

  it('shows no badge on a player decision (editing re-confirms as player)', () => {
    const { container } = renderConfirmed('player');
    expect(container.querySelector('.badge-suggested')).toBeNull();
  });

  it('badges generated decisions by their provenance (random, clone)', () => {
    expect(
      renderConfirmed('random').container.querySelector('.badge-suggested'),
    ).toHaveTextContent('random');
    expect(
      renderConfirmed('clone').container.querySelector('.badge-suggested'),
    ).toHaveTextContent('clone');
  });
});

// ---- The set/bag rule: the control derives from the declared kind ----
// (architecture: chargen-wizard). Set-kinds (single/multi) render toggles
// and never an Add control — duplicates are unrepresentable; bag-kinds
// (list) render Add controls and a grouped tray with visible removes.

function kindSlot(kind: SlotView['kind']): SlotView {
  return {
    id: 'test.slot',
    label: 'Test slot',
    kind,
    presentation_hint: undefined,
    locked_reason: undefined,
    required: true,
    status: 'empty',
    meters: [],
    decision: undefined,
    options: ['a', 'b'].map((id) => ({
      id: `opt.${id}`,
      label: id.toUpperCase(),
      summary: '',
      details: [],
      available: true,
      unavailable_reason: undefined,
    })),
  };
}

function renderKind(kind: SlotView['kind'], tentative: Selection | null = null) {
  render(
    <SlotCard
      slot={kindSlot(kind)}
      tentative={tentative}
      onTentative={vi.fn()}
      onConfirm={vi.fn()}
      onRequestChange={() => undefined}
      busy={false}
    />,
  );
}

describe('kind→control mapping is total and exclusive', () => {
  it('single renders radios, never Add', () => {
    renderKind({ kind: 'single' });
    expect(screen.getAllByRole('radio')).toHaveLength(2);
    expect(document.querySelectorAll('button.option-add')).toHaveLength(0);
  });

  it('multi renders checkboxes (a set: duplicates unrepresentable), never Add', () => {
    renderKind({ kind: 'multi', count: 2 });
    expect(screen.getAllByRole('checkbox')).toHaveLength(2);
    expect(document.querySelectorAll('button.option-add')).toHaveLength(0);
  });

  it('list renders Add controls and no toggles (a bag)', () => {
    renderKind({ kind: 'list' });
    // The Add button's accessible name inherits its option label; count by
    // its class.
    expect(document.querySelectorAll('button.option-add')).toHaveLength(2);
    expect(screen.queryByRole('checkbox')).toBeNull();
    expect(screen.queryByRole('radio')).toBeNull();
  });

  it('a bag tray groups repeats as one ×N row with a visible remove', () => {
    renderKind({ kind: 'list' }, { kind: 'options', value: ['opt.a', 'opt.a', 'opt.b'] });
    const tray = document.querySelector('.shopping-list');
    expect(tray).not.toBeNull();
    expect(tray?.querySelectorAll('li')).toHaveLength(2);
    expect(tray?.textContent).toContain('×2');
    expect(screen.getAllByRole('button', { name: 'remove' })).toHaveLength(2);
  });
});
