import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { SheetDiff } from './engine';
import { SheetDiffTable } from './VersionFlag';

// A diff row an undecided card will set shows no number — the fold must
// have one, the player has not chosen it — only the pointer, and only the
// rule line of its explanation.
const rows: SheetDiff[] = [
  {
    section: 'Combat',
    label: 'Vigor',
    old: '10',
    new: '16',
    why: 'The rule.\n• Level 2: default 6 + 0 = 6',
  },
  { section: 'Combat', label: 'Reach', old: '5', new: '10', why: 'Longer arms' },
];

describe('SheetDiffTable markers', () => {
  it('hides the value and the bullets of a marked row, keeps the rest', () => {
    render(
      <SheetDiffTable
        differences={rows}
        oldHeading="Level 1"
        newHeading="Level 2"
        markers={{ Vigor: '🎲 decide below' }}
      />,
    );
    const cells = screen.getAllByRole('cell');
    const vigorNew = cells[1]!;
    expect(vigorNew).toHaveTextContent('?');
    expect(vigorNew).not.toHaveTextContent('16');
    expect(screen.getByTestId('diff-marker-Vigor')).toHaveTextContent('decide below');
    expect(cells[2]).toHaveTextContent('The rule.');
    expect(cells[2]).not.toHaveTextContent('default 6');
    // An unmarked row shows its value and its whole explanation.
    expect(cells[4]).toHaveTextContent('10');
    expect(cells[5]).toHaveTextContent('Longer arms');
  });

  it('shows every value when nothing is marked', () => {
    render(<SheetDiffTable differences={rows} oldHeading="A" newHeading="B" />);
    expect(screen.getAllByRole('cell')[1]).toHaveTextContent('16');
    expect(screen.getAllByRole('cell')[2]).toHaveTextContent('default 6');
  });
});
