// Reconstruct the decision log from a projection (the server's view types
// carry each slot's confirmed decision; order restores chronology). Used to
// feed the local WASM engine for live previews — never to compute values.
// Scoped slots (preparation) are NOT log entries: their selections come
// back separately via prepFromProjection.
import type { Decision, ProjectionView, ScopedChoice } from './engine';

export function logFromProjection(projection: ProjectionView): Decision[] {
  const decisions: Decision[] = [];
  for (const step of projection.steps) {
    for (const slot of step.slots) {
      if (!slot.scoped && slot.decision !== undefined && slot.decision !== null) {
        decisions.push(slot.decision);
      }
    }
  }
  decisions.sort((a, b) => a.order - b.order);
  return decisions;
}

/** The scoped (preparation) choice set as the projection carries it. */
export function prepFromProjection(projection: ProjectionView): ScopedChoice[] {
  const choices: ScopedChoice[] = [];
  for (const step of projection.steps) {
    for (const slot of step.slots) {
      if (slot.scoped && slot.decision !== undefined && slot.decision !== null) {
        choices.push({ slot: slot.id, selection: slot.decision.selection });
      }
    }
  }
  return choices;
}

export function newDecisionId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `d-${Date.now().toString(16)}-${Math.floor(Math.random() * 1e9).toString(16)}`;
}
