import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Checklist } from './Checklist';
import type { ChecklistEntry } from './engine';

const illegal: ChecklistEntry = {
  severity: 'illegal',
  slot: 'pf2e.boosts.free',
  step: 'boosts',
  rule: 'Attribute boosts',
  message: 'Boosts gained at the same time must go to different attributes',
  source: 'Player Core pg. 19',
};

const incomplete: ChecklistEntry = {
  severity: 'incomplete',
  slot: 'pf2e.skills.trained',
  step: 'class',
  rule: 'Skills',
  message: '1 skill choice(s) left',
  source: 'from Class',
};

describe('Checklist', () => {
  it('separates illegal from incomplete and names the rule', () => {
    render(<Checklist entries={[illegal, incomplete]} onJump={() => undefined} />);
    expect(screen.getByText('Against the rules')).toBeInTheDocument();
    expect(screen.getByText('Still to do')).toBeInTheDocument();
    expect(
      screen.getByText('Boosts gained at the same time must go to different attributes'),
    ).toBeInTheDocument();
    expect(screen.getByText(/Attribute boosts · Player Core pg\. 19/)).toBeInTheDocument();
    expect(screen.getByText('1 skill choice(s) left')).toBeInTheDocument();
  });

  it('jumps to the offending entry on click', async () => {
    const onJump = vi.fn();
    render(<Checklist entries={[illegal]} onJump={onJump} />);
    await userEvent.click(
      screen.getByText('Boosts gained at the same time must go to different attributes'),
    );
    expect(onJump).toHaveBeenCalledWith(illegal);
  });

  it('celebrates an empty checklist', () => {
    render(<Checklist entries={[]} onJump={() => undefined} />);
    expect(screen.getByText(/ready to finalize/i)).toBeInTheDocument();
  });
});
