// Hash-routed shell: roster (#/), wizard (#/c/<id>), finalized sheet
// (#/c/<id>/sheet). Refresh-safe; resume lands on the server's step cursor.
// A draft flagged by the rules-data version guard opens blocked behind the
// resolution panel instead of the wizard.
import { useCallback, useEffect, useState } from 'react';
import {
  createCharacter,
  deleteCharacter,
  fetchCharacter,
  fetchRoster,
  quickBuild,
  resolveVersion,
  type VersionAction,
} from './api';
import type { CharacterView, RosterView } from './engine';
import { PrepEditor } from './PrepEditor';
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
  const [roster, setRoster] = useState<RosterView | null>(null);
  const [character, setCharacter] = useState<CharacterView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resolveBusy, setResolveBusy] = useState(false);
  const [resolveError, setResolveError] = useState<string | null>(null);

  useEffect(() => {
    const onHashChange = () => setRoute(parseHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const loadRoute = useCallback(async (current: Route) => {
    setError(null);
    setResolveError(null);
    try {
      if (current.view === 'roster') {
        setCharacter(null);
        setRoster(await fetchRoster());
      } else {
        setCharacter(await fetchCharacter(current.id));
      }
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    }
  }, []);

  useEffect(() => {
    void loadRoute(route);
  }, [route, loadRoute]);

  const goto = (hash: string) => {
    window.location.hash = hash;
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
    if (roster === null) {
      return <p className="loading">Loading…</p>;
    }
    return (
      <Roster
        roster={roster}
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

  if (character.state === 'draft') {
    return (
      <Wizard
        key={character.id}
        initial={character}
        onFinalized={() => {
          // Refetch: the finalized view carries the display sheet plus the
          // prep editor's projection, which only the server can compute.
          setCharacter(null);
          goto(`#/c/${route.id}/sheet`);
          void loadRoute({ view: 'character', id: route.id });
        }}
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
      <Sheet sheet={character.sheet} />
      {(character.prep !== undefined && character.prep !== null) && (
        <PrepEditor
          characterId={character.id}
          version={character.version}
          prep={character.prep}
          prepBroken={character.prep_broken ?? false}
          onSaved={setCharacter}
        />
      )}
    </div>
  );
}
