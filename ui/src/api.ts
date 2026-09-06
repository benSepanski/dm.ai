// Typed fetch wrappers over the server API. All shapes come from the
// generated engine types — the single source of truth for the wire.
import type {
  AbandonLevelOutcome,
  CampaignView,
  CharacterView,
  ClearOutcome,
  CloneResult,
  ConfirmOutcome,
  DecisionInput,
  DraftView,
  FillRemainingOutcome,
  FinalizeOutcome,
  LevelUpOutcome,
  QuickBuildResult,
  RosterView,
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

/** The campaign view: which game this directory plays (if resolved), the
 * games this build ships, and every shipped license paragraph. Fetched
 * before anything else — the roster label, the choose-game screen, and
 * the engine façade all read it. */
export function fetchCampaign(): Promise<CampaignView> {
  return request('/api/campaign');
}

/** Declare which game an empty campaign plays. The server refuses typed
 * (422 with a message) when the id is unknown, the campaign already holds
 * a character, or another tab declared a moment ago. */
export function declareCampaign(system: string): Promise<CampaignView> {
  return request('/api/campaign', {
    method: 'POST',
    body: JSON.stringify({ system }),
  });
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

/** One tap to a random, legal, named draft — every slot rolled from its
 * legal options (never the published suggested build). The client-minted
 * request ID doubles as the entropy and makes retries safe. */
export function randomMint(
  classId: string | null,
  name: string | null,
): Promise<QuickBuildResult> {
  return request('/api/characters/random-mint', {
    method: 'POST',
    body: JSON.stringify({ request_id: newDecisionId(), class_id: classId, name }),
  });
}

/** Duplicate a character as a new file and identity; the clone's only log
 * difference is the name decision. Retries are safe (first write wins). */
export function cloneCharacter(sourceId: string, name: string): Promise<CloneResult> {
  return request('/api/characters/clone', {
    method: 'POST',
    body: JSON.stringify({ request_id: newDecisionId(), source_id: sourceId, name }),
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

/** Start (or resume) a level-up on a finalized character: appends the
 * level's advance decision as the pending tail's head. Idempotent. */
export function levelUp(id: string, version: number): Promise<LevelUpOutcome> {
  return request(`/api/characters/${encodeURIComponent(id)}/level-up`, {
    method: 'POST',
    body: JSON.stringify({ version }),
  });
}

/** Discard the pending level; the finalized character stands untouched. */
export function abandonLevel(id: string, version: number): Promise<AbandonLevelOutcome> {
  return request(`/api/characters/${encodeURIComponent(id)}/level-up/abandon`, {
    method: 'POST',
    body: JSON.stringify({ version }),
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
