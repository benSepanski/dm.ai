// The thin façade over the WASM engine — the only module allowed to touch
// the generated bindings (eslint enforces this). The UI computes no game
// values: everything it renders arrives through EngineResponse or the
// server's view types.
import initWasm, { engine_request } from './pkg/wasm';
import type {
  ClearPreview,
  Decision,
  DecisionInput,
  EngineRequest,
  EngineResponse,
  ProjectionView,
  SlotId,
} from './pkg/wasm';

export type * from './pkg/wasm';

let ready: Promise<void> | null = null;
let system: string | null = null;

/** The campaign's game system, stamped once from the campaign view; every
 * engine request carries it so the browser selects the same ruleset the
 * server does. */
export function selectSystem(id: string): void {
  system = id;
}

/** Load and instantiate the engine (idempotent). */
export function initEngine(wasmInput?: Parameters<typeof initWasm>[0]): Promise<void> {
  ready ??= initWasm(wasmInput).then(() => undefined);
  return ready;
}

/** One request in, one response out. Call after initEngine resolves. */
export function engineRequest(request: EngineRequest): EngineResponse {
  if (system === null) {
    throw new Error('engine used before the campaign view named its game');
  }
  return engine_request(system, request);
}

function expectProjection(response: EngineResponse): ProjectionView {
  if (response.response === 'projection') {
    return response.projection;
  }
  throw new Error(response.response === 'error' ? response.message : 'unexpected engine response');
}

/** Project the wizard from a decision log; throws on an engine error. */
export function project(log: Decision[]): ProjectionView {
  return expectProjection(engineRequest({ request: 'project', log }));
}

/** Live preview: the wizard as if `candidate` were confirmed. */
export function preview(log: Decision[], candidate: DecisionInput): ProjectionView {
  return expectProjection(engineRequest({ request: 'preview', log, candidate }));
}

/** What changing a confirmed slot would clear. */
export function clearPreview(log: Decision[], slot: SlotId): ClearPreview {
  const response = engineRequest({ request: 'clear_preview', log, slot });
  if (response.response === 'clear_preview') {
    return response.preview;
  }
  throw new Error(response.response === 'error' ? response.message : 'unexpected engine response');
}
