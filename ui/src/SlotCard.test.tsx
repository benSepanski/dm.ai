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
    expect(screen.getByTestId('counter-pf2e.boosts.free')).toHaveTextContent(
      '2 of 4 boosts left',
    );
  });

  it('reports a full selection', () => {
    renderCard({ kind: 'options', value: ['attr.str', 'attr.con', 'attr.dex', 'attr.wis'] });
    expect(screen.getByTestId('counter-pf2e.boosts.free')).toHaveTextContent(
      'All boosts assigned',
    );
  });

  it('accepts the same attribute twice — the checklist judges, not the UI', async () => {
    const { onTentative } = renderCard({ kind: 'options', value: ['attr.str'] });
    await userEvent.selectOptions(screen.getByLabelText('Boost 2'), 'attr.str');
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
    expect(screen.getByLabelText('Boost 1')).toHaveValue('attr.str');
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
