// Typed fetch wrappers over the server API. All shapes come from the
// generated engine types — the single source of truth for the wire.
import type {
  CharacterView,
  ClearOutcome,
  ConfirmOutcome,
  DecisionInput,
  DraftView,
  FillRemainingOutcome,
  FinalizeOutcome,
  LifecycleState,
  PrepSaveOutcome,
  QuickBuildResult,
  RosterView,
  ScopedChoice,
  SlotId,
  StepId,
  VersionResolutionOutcome,
} from './engine';
import { newDecisionId } from './log';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'content-type': 'application/json' },
    ...init,
  });
  if (!response.ok && response.status !== 204) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { message?: string };
      if (body.message !== undefined) {
        message = body.message;
      }
    } catch {
      // Non-JSON error body; keep the status line.
    }
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function fetchRoster(): Promise<RosterView> {
  return request('/api/roster');
}

export function createCharacter(name: string | null): Promise<DraftView> {
  return request('/api/characters', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

/** One tap to a complete, reviewable draft filled with the app's suggested
 * build. The client-minted request ID makes retries safe (server-side
 * idempotency). */
export function quickBuild(name: string | null): Promise<QuickBuildResult> {
  return request('/api/characters/quick-build', {
    method: 'POST',
    body: JSON.stringify({ request_id: newDecisionId(), name }),
  });
}

/** Fill only the open slots of a draft with suggestions; confirmed choices
 * never move. */
export function fillRemaining(id: string, version: number): Promise<FillRemainingOutcome> {
  return request(`/api/characters/${encodeURIComponent(id)}/fill-remaining`, {
    method: 'POST',
    body: JSON.stringify({ request_id: newDecisionId(), version }),
  });
}

export function fetchCharacter(id: string): Promise<CharacterView> {
  return request(`/api/characters/${encodeURIComponent(id)}`);
}

export function deleteCharacter(id: string): Promise<void> {
  return request(`/api/characters/${encodeURIComponent(id)}`, { method: 'DELETE' });
}

export function confirmDecision(
  id: string,
  version: number,
  decision: DecisionInput,
): Promise<ConfirmOutcome> {
  return request(`/api/characters/${encodeURIComponent(id)}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ version, decision }),
  });
}

/** Replace a slot's existing decision atomically (finish a partial pick). */
export function amendDecision(
  id: string,
  version: number,
  decision: DecisionInput,
): Promise<ConfirmOutcome> {
  return request(`/api/characters/${encodeURIComponent(id)}/amend`, {
    method: 'POST',
    body: JSON.stringify({ version, decision }),
  });
}

export function clearSlot(id: string, version: number, slot: SlotId): Promise<ClearOutcome> {
  return request(`/api/characters/${encodeURIComponent(id)}/clear`, {
    method: 'POST',
    body: JSON.stringify({ version, slot }),
  });
}

export function setStep(id: string, version: number, step: StepId): Promise<DraftView> {
  return request(`/api/characters/${encodeURIComponent(id)}/step`, {
    method: 'POST',
    body: JSON.stringify({ version, step }),
  });
}

export function finalizeCharacter(id: string, version: number): Promise<FinalizeOutcome> {
  return request(`/api/characters/${encodeURIComponent(id)}/finalize`, {
    method: 'POST',
    body: JSON.stringify({ version }),
  });
}

/** Replace the scoped preparation section wholesale (drafts mid-wizard and
 * finalized characters' "change prepared spells" alike). The client-minted
 * request ID makes retries safe. */
export function savePrep(
  id: string,
  version: number,
  expectedState: LifecycleState,
  choices: ScopedChoice[],
): Promise<PrepSaveOutcome> {
  return request(`/api/characters/${encodeURIComponent(id)}/prep`, {
    method: 'POST',
    body: JSON.stringify({
      request_id: newDecisionId(),
      version,
      expected_state: expectedState,
      choices,
    }),
  });
}

/** The explicit rules-data version-resolution actions (spec req 6). */
export type VersionAction = 'repin' | 'accept' | 'keep-old' | 'resolve-errors';

export function resolveVersion(
  id: string,
  action: VersionAction,
  version: number,
): Promise<VersionResolutionOutcome> {
  return request(`/api/characters/${encodeURIComponent(id)}/version/${action}`, {
    method: 'POST',
    body: JSON.stringify({ version }),
  });
}
