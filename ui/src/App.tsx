// Hash-routed shell: roster (#/), wizard (#/c/<id>), finalized sheet
// (#/c/<id>/sheet). Refresh-safe; resume lands on the server's step cursor.
// A draft flagged by the rules-data version guard opens blocked behind the
// resolution panel instead of the wizard.
//
// The campaign view comes first on every load: it names the game this
// directory plays (stamped once into the engine façade so the browser
// selects the ruleset the server did), or asks for it on an empty campaign.
import { useCallback, useEffect, useState } from 'react';
import {
  cloneCharacter,
  createCharacter,
  declareCampaign,
  deleteCharacter,
  fetchCampaign,
  fetchCharacter,
  fetchRoster,
  levelUp,
  quickBuild,
  randomMint,
  resolveVersion,
  type VersionAction,
} from './api';
import { ChooseGame } from './ChooseGame';
import type { CampaignView, CharacterView, RosterView } from './engine';
import { selectSystem } from './engine';
import { Roster } from './Roster';
import { Sheet } from './Sheet';
import { VersionFlagPanel } from './VersionFlag';
import { Wizard } from './Wizard';

type Route = { view: 'roster' } | { view: 'character'; id: string };

function parseHash(): Route {
  const match = /^#\/c\/([^/]+)/.exec(window.location.hash);
  if (match?.[1] !== undefined) {
    return { view: 'character', id: decodeURIComponent(match[1]) };
  }
  return { view: 'roster' };
}

export function App() {
  const [route, setRoute] = useState<Route>(parseHash);
  const [campaign, setCampaign] = useState<CampaignView | null>(null);
  const [declareBusy, setDeclareBusy] = useState(false);
  const [declareError, setDeclareError] = useState<string | null>(null);
  const [roster, setRoster] = useState<RosterView | null>(null);
  const [character, setCharacter] = useState<CharacterView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resolveBusy, setResolveBusy] = useState(false);
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [levelBusy, setLevelBusy] = useState(false);

  useEffect(() => {
    const onHashChange = () => setRoute(parseHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  // The campaign view is (re)fetched before any route loads — a direct
  // #/c/<id> link included — so the engine façade knows the game before
  // the wizard's first preview. Refetched on every return to the roster:
  // whether the game may still be chosen changes as characters come and go.
  const refreshCampaign = useCallback(async (): Promise<CampaignView> => {
    const view = await fetchCampaign();
    if (view.system !== undefined) {
      selectSystem(view.system);
    }
    setCampaign(view);
    return view;
  }, []);

  const loadRoute = useCallback(
    async (current: Route) => {
      setError(null);
      setResolveError(null);
      try {
        const view = await refreshCampaign();
        if (current.view === 'roster') {
          setCharacter(null);
          setRoster(await fetchRoster());
        } else if (view.system === undefined) {
          // No game, no characters: a stale character link falls back to
          // whatever the roster shell offers (the question, or the problem).
          setCharacter(null);
          setRoster(await fetchRoster());
          window.location.hash = '#/';
        } else {
          setCharacter(await fetchCharacter(current.id));
        }
      } catch (e) {
        setError(String(e instanceof Error ? e.message : e));
      }
    },
    [refreshCampaign],
  );

  useEffect(() => {
    void loadRoute(route);
  }, [route, loadRoute]);

  const goto = (hash: string) => {
    window.location.hash = hash;
  };

  const declare = (system: string) => {
    setDeclareBusy(true);
    setDeclareError(null);
    declareCampaign(system)
      .then((view) => {
        if (view.system !== undefined) {
          selectSystem(view.system);
        }
        setCampaign(view);
        return loadRoute({ view: 'roster' });
      })
      .catch((e: unknown) => {
        // A typed refusal (someone declared a moment ago, an unknown id)
        // shows where the question was asked; Reload fetches the truth.
        setDeclareError(String(e instanceof Error ? e.message : e));
      })
      .finally(() => setDeclareBusy(false));
  };

  const resolve = (id: string, version: number) => (action: VersionAction) => {
    setResolveBusy(true);
    setResolveError(null);
    resolveVersion(id, action, version)
      .then((outcome) => {
        if (outcome.outcome === 'refused') {
          setResolveError(outcome.message);
        } else {
          // Resolved (or a stale-tab conflict): render the fresh view.
          setCharacter(outcome.character);
        }
      })
      .catch((e: unknown) => {
        setResolveError(String(e instanceof Error ? e.message : e));
      })
      .finally(() => setResolveBusy(false));
  };

  if (error !== null) {
    return (
      <div className="app-error" role="alert">
        <p>{error}</p>
        <button type="button" onClick={() => void loadRoute(route)}>
          Retry
        </button>
        <button type="button" onClick={() => goto('#/')}>
          Back to roster
        </button>
      </div>
    );
  }

  if (route.view === 'roster') {
    if (roster === null || campaign === null) {
      return <p className="loading">Loading…</p>;
    }
    if (campaign.system === undefined && campaign.problem === undefined && campaign.can_declare) {
      return (
        <ChooseGame
          games={campaign.games}
          onDeclare={declare}
          onReload={() => {
            setDeclareError(null);
            void loadRoute({ view: 'roster' });
          }}
          busy={declareBusy}
          error={declareError}
        />
      );
    }
    return (
      <Roster
        roster={roster}
        campaign={campaign}
        onCreate={(name) => {
          void createCharacter(name).then((created) => goto(`#/c/${created.id}`));
        }}
        onQuickBuild={(name) => {
          void quickBuild(name)
            .then((result) => goto(`#/c/${result.draft.id}`))
            .catch((e: unknown) => {
              setError(String(e instanceof Error ? e.message : e));
            });
        }}
        onRandom={(classId, name) =>
          randomMint(classId, name)
            .then((result) => goto(`#/c/${result.draft.id}`))
            .catch((e: unknown) => {
              setError(String(e instanceof Error ? e.message : e));
            })
        }
        onClone={(id, cloneName) =>
          cloneCharacter(id, cloneName)
            .then((result) => goto(`#/c/${result.id}`))
            .catch((e: unknown) => {
              setError(String(e instanceof Error ? e.message : e));
            })
        }
        onOpen={(id) => goto(`#/c/${id}`)}
        onDelete={(id) => {
          void deleteCharacter(id).then(() => loadRoute({ view: 'roster' }));
        }}
      />
    );
  }

  if (character === null) {
    return <p className="loading">Loading…</p>;
  }

  if (character.state === 'draft' || character.state === 'leveling') {
    // Creation drafts and pending levels are the same guided dialog over
    // whatever steps the projection says are live; the router only picks
    // which draft view to hand over.
    const initial = character.state === 'draft' ? character : character.draft;
    return (
      <Wizard
        key={`${character.id}:${initial.version}`}
        initial={initial}
        onFinalized={() => {
          // Reload the truth (the finalized view carries the next level).
          void loadRoute({ view: 'character', id: character.id }).then(() =>
            goto(`#/c/${route.id}/sheet`),
          );
        }}
        onAbandoned={() => void loadRoute({ view: 'character', id: character.id })}
        onExit={() => goto('#/')}
      />
    );
  }

  if (character.state === 'flagged_draft') {
    // The wizard is blocked until the flag is resolved; the stored sheet
    // renders read-only beside the flag.
    return (
      <div className="sheet-page">
        <button type="button" className="wizard-back" onClick={() => goto('#/')}>
          ← Roster
        </button>
        <VersionFlagPanel
          status={character.status}
          isDraft
          busy={resolveBusy}
          error={resolveError}
          onResolve={resolve(character.id, character.version)}
        />
        <Sheet sheet={character.sheet} />
      </div>
    );
  }

  return (
    <div className="sheet-page">
      <button type="button" className="wizard-back" onClick={() => goto('#/')}>
        ← Roster
      </button>
      {character.version_status.status !== 'current' && (
        <VersionFlagPanel
          status={character.version_status}
          isDraft={false}
          busy={resolveBusy}
          error={resolveError}
          onResolve={resolve(character.id, character.version)}
        />
      )}
      {character.next_level !== undefined ? (
        <div className="level-up-bar">
          <button
            type="button"
            className="confirm level-up"
            disabled={levelBusy}
            onClick={() => {
              setLevelBusy(true);
              levelUp(character.id, character.version)
                .then(() => loadRoute({ view: 'character', id: character.id }))
                .catch((e: unknown) => setError(String(e instanceof Error ? e.message : e)))
                .finally(() => setLevelBusy(false));
            }}
          >
            Level up to {character.next_level}
          </button>
        </div>
      ) : (
        character.version_status.status === 'current' && (
          <p className="level-cap-note">Higher levels are coming.</p>
        )
      )}
      <Sheet sheet={character.sheet} />
    </div>
  );
}
