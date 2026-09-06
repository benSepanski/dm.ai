// The shell's campaign-first flow, with the server API and the engine
// façade mocked: an undeclared campaign asks which game; declaring lands on
// the roster labeled with that game; a refusal shows inline; a campaign
// with a problem shows it and offers nothing else; a resolved campaign
// stamps its system into the façade before any route loads.
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CampaignView, RosterView } from './engine';

const api = vi.hoisted(() => ({
  fetchCampaign: vi.fn(),
  declareCampaign: vi.fn(),
  fetchRoster: vi.fn(),
  fetchCharacter: vi.fn(),
}));
const engine = vi.hoisted(() => ({ selectSystem: vi.fn() }));

vi.mock('./api', () => ({
  fetchCampaign: api.fetchCampaign,
  declareCampaign: api.declareCampaign,
  fetchRoster: api.fetchRoster,
  fetchCharacter: api.fetchCharacter,
  createCharacter: vi.fn(),
  deleteCharacter: vi.fn(),
  levelUp: vi.fn(),
  quickBuild: vi.fn(),
  randomMint: vi.fn(),
  cloneCharacter: vi.fn(),
  resolveVersion: vi.fn(),
}));
vi.mock('./engine', () => ({
  selectSystem: engine.selectSystem,
  initEngine: () => Promise.resolve(),
  project: vi.fn(),
  preview: vi.fn(),
  clearPreview: vi.fn(),
}));

import { App } from './App';

const GAMES = [
  { id: 'first-game', name: 'First Game' },
  { id: 'second-game', name: 'Second Game' },
];
const LICENSE = ['License paragraph one.', 'License paragraph two.'];

function undeclared(): CampaignView {
  return { inferred: false, can_declare: true, games: GAMES, license_lines: LICENSE };
}
function declared(id: string, name: string, inferred = false): CampaignView {
  return {
    system: id,
    system_name: name,
    inferred,
    can_declare: !inferred,
    games: GAMES,
    license_lines: LICENSE,
  };
}
function emptyRoster(quickBuild?: { id: string; name: string }): RosterView {
  const roster: RosterView = { entries: [], problems: [], classes: [] };
  if (quickBuild !== undefined) {
    roster.quick_build = quickBuild;
  }
  return roster;
}

/** Set the route before rendering — and let the hashchange event the
 * assignment queues fire now, not mid-test as a spurious route reload. */
async function setHash(hash: string) {
  window.location.hash = hash;
  await new Promise((resolve) => setTimeout(resolve, 0));
}

beforeEach(async () => {
  vi.clearAllMocks();
  await setHash('#/');
  api.fetchRoster.mockResolvedValue(emptyRoster());
});

describe('App campaign-first flow', () => {
  it('asks which game an undeclared campaign plays, then lands on the labeled roster', async () => {
    api.fetchCampaign.mockResolvedValue(undeclared());
    api.declareCampaign.mockImplementation((id: string) => {
      const view = declared(id, GAMES.find((g) => g.id === id)?.name ?? id);
      api.fetchCampaign.mockResolvedValue(view);
      return Promise.resolve(view);
    });
    render(<App />);
    expect(await screen.findByText('Which game does this campaign play?')).toBeInTheDocument();
    expect(engine.selectSystem).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole('radio', { name: 'Second Game' }));
    await userEvent.click(screen.getByRole('button', { name: 'Start campaign' }));

    expect(api.declareCampaign).toHaveBeenCalledWith('second-game');
    expect(await screen.findByTestId('campaign-label')).toHaveTextContent('Second Game');
    expect(engine.selectSystem).toHaveBeenCalledWith('second-game');
    // Every license paragraph, in order, from the campaign view.
    const notice = document.querySelector('.license-notice');
    expect(Array.from(notice?.querySelectorAll('p') ?? []).map((p) => p.textContent)).toEqual(
      LICENSE,
    );
    expect(screen.queryByText('Which game does this campaign play?')).not.toBeInTheDocument();
  });

  it('shows a typed refusal inline and stays on the question', async () => {
    api.fetchCampaign.mockResolvedValue(undeclared());
    api.declareCampaign.mockRejectedValue(new Error('declared a moment ago — reload'));
    render(<App />);
    await screen.findByText('Which game does this campaign play?');
    await userEvent.click(screen.getByRole('radio', { name: 'First Game' }));
    await userEvent.click(screen.getByRole('button', { name: 'Start campaign' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('declared a moment ago');
    expect(screen.getByText('Which game does this campaign play?')).toBeInTheDocument();
  });

  it('never asks a resolved campaign and stamps its system before loading the route', async () => {
    api.fetchCampaign.mockResolvedValue(declared('first-game', 'First Game', true));
    api.fetchRoster.mockResolvedValue(emptyRoster({ id: 'c.x', name: 'Exemplar' }));
    render(<App />);
    expect(await screen.findByTestId('campaign-label')).toHaveTextContent('First Game');
    expect(screen.getByTestId('campaign-label')).toHaveTextContent(/by default/);
    expect(screen.queryByText('Which game does this campaign play?')).not.toBeInTheDocument();
    expect(engine.selectSystem).toHaveBeenCalledWith('first-game');
    // Quick build reads the roster's own class name.
    expect(screen.getByRole('button', { name: 'Quick build a Exemplar' })).toBeInTheDocument();
  });

  it('offers no quick build when the roster carries none', async () => {
    api.fetchCampaign.mockResolvedValue(declared('first-game', 'First Game'));
    render(<App />);
    await screen.findByTestId('campaign-label');
    expect(screen.queryByRole('button', { name: /quick build/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create character' })).toBeInTheDocument();
  });

  it('shows a campaign problem prominently and offers nothing else', async () => {
    api.fetchCampaign.mockResolvedValue({
      inferred: false,
      can_declare: false,
      problem: 'the campaign declaration is not valid JSON — fix or remove the file',
      games: GAMES,
      license_lines: LICENSE,
    });
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('not valid JSON');
    expect(screen.queryByText('Which game does this campaign play?')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Create character' })).not.toBeInTheDocument();
    expect(engine.selectSystem).not.toHaveBeenCalled();
  });

  it('fetches the campaign before a direct character link', async () => {
    await setHash('#/c/some-id');
    const order: string[] = [];
    api.fetchCampaign.mockImplementation(() => {
      order.push('campaign');
      return Promise.resolve(declared('first-game', 'First Game'));
    });
    api.fetchCharacter.mockImplementation(() => {
      order.push('character');
      return new Promise(() => undefined); // never resolves; the order is the point
    });
    render(<App />);
    await waitFor(() => expect(order).toEqual(['campaign', 'character']));
    expect(engine.selectSystem).toHaveBeenCalledWith('first-game');
  });
});
