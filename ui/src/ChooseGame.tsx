// The one question an empty campaign asks: which game does it play? The
// games come from the campaign view (names and ids alike) — this screen
// knows no game by name. A typed refusal from the server (someone else
// declared a moment ago, an id this build no longer ships) renders inline.
import { useState } from 'react';
import type { GameOption } from './engine';

export function ChooseGame({
  games,
  onDeclare,
  onReload,
  busy,
  error,
}: {
  games: GameOption[];
  /** Resolves when the declaration landed (the caller moves on to the
   * roster) or rejects with the server's typed message. */
  onDeclare: (system: string) => void;
  /** Fetch the campaign again — offered beside a refusal, since the usual
   * reason is that another tab already answered. */
  onReload: () => void;
  busy: boolean;
  error: string | null;
}) {
  const [picked, setPicked] = useState<string | null>(games.length === 1 ? (games[0]?.id ?? null) : null);
  const hintId = 'choose-game-hint';
  const disabledReason = picked === null ? 'Pick a game to start the campaign.' : null;
  return (
    <div className="choose-game">
      <header className="roster-header">
        <h1>dm.ai — characters</h1>
      </header>
      <form
        className="choose-game-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (picked !== null) {
            onDeclare(picked);
          }
        }}
      >
        <h2 id="choose-game-question">Which game does this campaign play?</h2>
        <p className="choose-game-intro">
          A campaign plays one game. Its characters are created and leveled by
          that game&apos;s rules; the choice is fixed once the first character
          exists.
        </p>
        <ul className="choose-game-list" role="radiogroup" aria-labelledby="choose-game-question">
          {games.map((game) => (
            <li key={game.id} className={`choose-game-option ${picked === game.id ? 'selected' : ''}`}>
              <label>
                <input
                  type="radio"
                  name="game"
                  value={game.id}
                  checked={picked === game.id}
                  disabled={busy}
                  onChange={() => setPicked(game.id)}
                />
                <span className="choose-game-name">{game.name}</span>
              </label>
            </li>
          ))}
        </ul>
        {error !== null && (
          <div className="choose-game-error" role="alert">
            <p>{error}</p>
            <button type="button" onClick={onReload} disabled={busy}>
              Reload
            </button>
          </div>
        )}
        <footer className="slot-actions">
          {disabledReason !== null && (
            <p className="confirm-hint" id={hintId}>
              {disabledReason}
            </p>
          )}
          <button
            type="submit"
            className="confirm"
            disabled={disabledReason !== null || busy}
            data-busy={busy || undefined}
            aria-describedby={disabledReason !== null ? hintId : undefined}
          >
            Start campaign
          </button>
        </footer>
      </form>
    </div>
  );
}
