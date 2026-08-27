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

  it('locked slots explain themselves', () => {
    const slot = { ...boostSlot(), locked_reason: 'choose an ancestry first' };
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
