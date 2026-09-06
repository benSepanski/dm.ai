// @vitest-environment node
// WASM <-> native parity smoke: the browser copy of the engine, run on the
// committed fixture logs, must reproduce byte-for-byte the sheets the
// native engine derived (checks/fixtures/*.sheet.json, asserted native-side
// by checks/replay.rs).
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { initEngine, project, selectSystem } from './index';
import type { Decision, SheetView } from './index';

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = join(here, '../../../checks/fixtures');
const wasmBytes = readFileSync(join(here, 'pkg/wasm_bg.wasm'));

// serde writes an absent Option as JSON null; the wasm boundary surfaces it
// as undefined. Same value, different spelling — canonicalize both sides.
function normalize(value: unknown): unknown {
  return JSON.parse(JSON.stringify(value, (_key, v: unknown) => v ?? undefined) ?? 'null') as unknown;
}

describe('wasm/native parity', () => {
  for (const name of ['torvald', 'elyse', 'krivvy']) {
    it(`replays ${name} to the native sheet`, async () => {
      await initEngine(wasmBytes);
      // A test may name a system; shipped source only ever relays the
      // campaign view's id.
      selectSystem('pf2e');
      const log = JSON.parse(
        readFileSync(join(fixtures, `${name}.log.json`), 'utf8'),
      ) as Decision[];
      const expected = JSON.parse(
        readFileSync(join(fixtures, `${name}.sheet.json`), 'utf8'),
      ) as SheetView;
      const projection = project(log);
      expect(normalize(projection.sheet)).toEqual(normalize(expected));
      expect(projection.can_finalize).toBe(true);
    });
  }
});
