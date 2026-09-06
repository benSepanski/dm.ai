// The choose-game screen renders whatever games the campaign view lists —
// the names and ids here are placeholders, never a shipped game.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ChooseGame } from './ChooseGame';

const GAMES = [
  { id: 'first-game', name: 'First Game' },
  { id: 'second-game', name: 'Second Game' },
];

describe('ChooseGame', () => {
  it('asks the question, lists every game by name, and explains the disabled start', () => {
    render(
      <ChooseGame games={GAMES} onDeclare={vi.fn()} onReload={vi.fn()} busy={false} error={null} />,
    );
    expect(screen.getByText('Which game does this campaign play?')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'First Game' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Second Game' })).toBeInTheDocument();
    const start = screen.getByRole('button', { name: 'Start campaign' });
    expect(start).toBeDisabled();
    const hint = document.getElementById(start.getAttribute('aria-describedby') ?? '');
    expect(hint).toHaveTextContent(/pick a game/i);
  });

  it('declares the picked game id on start', async () => {
    const onDeclare = vi.fn();
    render(
      <ChooseGame games={GAMES} onDeclare={onDeclare} onReload={vi.fn()} busy={false} error={null} />,
    );
    await userEvent.click(screen.getByRole('radio', { name: 'Second Game' }));
    await userEvent.click(screen.getByRole('button', { name: 'Start campaign' }));
    expect(onDeclare).toHaveBeenCalledWith('second-game');
  });

  it('preselects the only game when just one ships', () => {
    render(
      <ChooseGame
        games={[GAMES[0] as (typeof GAMES)[number]]}
        onDeclare={vi.fn()}
        onReload={vi.fn()}
        busy={false}
        error={null}
      />,
    );
    expect(screen.getByRole('radio', { name: 'First Game' })).toBeChecked();
    expect(screen.getByRole('button', { name: 'Start campaign' })).toBeEnabled();
  });

  it('shows a typed refusal inline with a reload', async () => {
    const onReload = vi.fn();
    render(
      <ChooseGame
        games={GAMES}
        onDeclare={vi.fn()}
        onReload={onReload}
        busy={false}
        error="this campaign was declared a moment ago — reload"
      />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('declared a moment ago');
    await userEvent.click(screen.getByRole('button', { name: 'Reload' }));
    expect(onReload).toHaveBeenCalled();
  });
});
