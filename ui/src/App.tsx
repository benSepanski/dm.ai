// Hash-routed shell: roster (#/), wizard (#/c/<id>), finalized sheet
// (#/c/<id>/sheet). Refresh-safe; resume lands on the server's step cursor.
import { useCallback, useEffect, useState } from 'react';
import { createCharacter, deleteCharacter, fetchCharacter, fetchRoster } from './api';
import type { DraftView, RosterView, SheetView } from './engine';
import { Roster } from './Roster';
import { Sheet } from './Sheet';
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
  const [draft, setDraft] = useState<DraftView | null>(null);
  const [sheet, setSheet] = useState<SheetView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onHashChange = () => setRoute(parseHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const loadRoute = useCallback(async (current: Route) => {
    setError(null);
    try {
      if (current.view === 'roster') {
        setDraft(null);
        setSheet(null);
        setRoster(await fetchRoster());
      } else {
        const character = await fetchCharacter(current.id);
        if (character.state === 'draft') {
          setSheet(null);
          setDraft(character);
        } else {
          setDraft(null);
          setSheet(character.sheet);
        }
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
        onOpen={(id) => goto(`#/c/${id}`)}
        onDelete={(id) => {
          void deleteCharacter(id).then(() => loadRoute({ view: 'roster' }));
        }}
      />
    );
  }

  if (draft !== null) {
    return (
      <Wizard
        key={draft.id}
        initial={draft}
        onFinalized={(finalSheet) => {
          setSheet(finalSheet);
          setDraft(null);
          goto(`#/c/${route.id}/sheet`);
        }}
        onExit={() => goto('#/')}
      />
    );
  }

  if (sheet !== null) {
    return (
      <div className="sheet-page">
        <button type="button" className="wizard-back" onClick={() => goto('#/')}>
          ← Roster
        </button>
        <Sheet sheet={sheet} />
      </div>
    );
  }

  return <p className="loading">Loading…</p>;
}
