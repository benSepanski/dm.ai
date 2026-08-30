// Reconstruct the decision log from a projection (the server's view types
// carry each slot's confirmed decision; order restores chronology). Used to
// feed the local WASM engine for live previews — never to compute values.
import type { Decision, ProjectionView } from './engine';

export function logFromProjection(projection: ProjectionView): Decision[] {
  const decisions: Decision[] = [];
  for (const step of projection.steps) {
    for (const slot of step.slots) {
      if (slot.decision !== undefined && slot.decision !== null) {
        decisions.push(slot.decision);
      }
    }
  }
  decisions.sort((a, b) => a.order - b.order);
  return decisions;
}

export function newDecisionId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `d-${Date.now().toString(16)}-${Math.floor(Math.random() * 1e9).toString(16)}`;
}
