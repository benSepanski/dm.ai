// The structured-coverage test: every SlotStatus × SlotViewKind combination
// must have a DECIDED, DISTINGUISHABLE rendering. The enums are the
// coverage checklist — when a future slice adds a variant, this grid forces
// a rendering decision for it. (E2e samples mechanisms; this enumerates.)
import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { Decision, SlotStatus, SlotView, SlotViewKind } from './engine';
import { SlotCard } from './SlotCard';

const KINDS: { name: string; kind: SlotViewKind; decision: Decision['selection'] }[] = [
  { name: 'single', kind: { kind: 'single' }, decision: { kind: 'option', value: 'attr.str' } },
  {
    name: 'multi',
    kind: { kind: 'multi', count: 3 },
    decision: { kind: 'options', value: ['attr.str'] },
  },
  {
    name: 'list',
    kind: { kind: 'list' },
    decision: { kind: 'options', value: ['attr.str', 'attr.str'] },
  },
  { name: 'text', kind: { kind: 'text', multiline: false }, decision: { kind: 'text', value: 'hi' } },
];

const STATUSES: SlotStatus[] = ['locked', 'empty', 'partial', 'complete', 'illegal'];

/** Statuses that imply a confirmed decision exists. Illegal is tested in
 * both shapes (a confirmed-but-wrong slot, and an empty slot carrying a
 * violation, like an overspent budget with nothing picked). */
function decisionsFor(status: SlotStatus): boolean[] {
  switch (status) {
    case 'locked':
    case 'empty':
      return [false];
    case 'partial':
    case 'complete':
      return [true];
    case 'illegal':
      return [true, false];
  }
}

function makeSlot(
  kindSpec: (typeof KINDS)[number],
  status: SlotStatus,
  withDecision: boolean,
): SlotView {
  return {
    id: 'grid.slot',
    label: 'Grid slot',
    kind: kindSpec.kind,
    presentation_hint: undefined,
    locked_reason: status === 'locked' ? 'locked for the grid' : undefined,
    required: true,
    status,
    meters: [],
    decision: withDecision
      ? {
          id: 'g1',
          slot: 'grid.slot',
          selection: kindSpec.decision,
          source: 'player',
          order: 0,
        }
      : undefined,
    options: ['attr.str', 'attr.dex', 'attr.con'].map((id) => ({
      id,
      label: id.toUpperCase(),
      summary: '',
      details: [],
      available: true,
      unavailable_reason: undefined,
    })),
  };
}

interface Affordances {
  statusClass: string | undefined;
  lockedReason: boolean;
  editor: boolean;
  confirmedValue: boolean;
  changeButton: boolean;
  prefilled: boolean;
}

function renderAffordances(slot: SlotView): Affordances {
  const { container, unmount } = render(
    <SlotCard
      slot={slot}
      tentative={null}
      onTentative={() => undefined}
      onConfirm={() => undefined}
      onRequestChange={() => undefined}
      busy={false}
    />,
  );
  const section = container.querySelector('section');
  const inputs = [...container.querySelectorAll('input, select, textarea, button.option-add')];
  const affordances: Affordances = {
    statusClass: /status-\w+/.exec(section?.className ?? '')?.[0],
    lockedReason: container.querySelector('.slot-locked-reason') !== null,
    editor: inputs.length > 0,
    confirmedValue: container.querySelector('.slot-confirmed-value') !== null,
    changeButton:
      [...container.querySelectorAll('button')].some((b) => b.textContent.includes('Change')),
    prefilled:
      [...container.querySelectorAll('input:checked')].length > 0 ||
      [...container.querySelectorAll('input[type=text], textarea')].some(
        (el) => (el as HTMLInputElement).value !== '',
      ) ||
      [...container.querySelectorAll('select')].some(
        (el) => (el as HTMLSelectElement).value !== '',
      ) ||
      container.querySelector('.shopping-list') !== null,
  };
  unmount();
  return affordances;
}

describe('SlotStatus × SlotViewKind rendering grid', () => {
  for (const kindSpec of KINDS) {
    it(`decides and distinguishes every status for a ${kindSpec.name} slot`, () => {
      const signatures = new Map<string, string>();
      for (const status of STATUSES) {
        for (const withDecision of decisionsFor(status)) {
          const slot = makeSlot(kindSpec, status, withDecision);
          const a = renderAffordances(slot);
          const caseName = `${status}${withDecision ? '+decision' : ''}`;

          // Decided: the semantic invariants each status must render.
          expect(a.statusClass, caseName).toBe(`status-${status}`);
          if (status === 'locked') {
            expect(a.lockedReason, caseName).toBe(true);
            expect(a.editor, caseName).toBe(false);
          } else if (status === 'empty') {
            expect(a.editor, caseName).toBe(true);
            expect(a.confirmedValue, caseName).toBe(false);
          } else if (status === 'partial') {
            // Editable in place, with the confirmed picks preloaded.
            expect(a.editor, caseName).toBe(true);
            expect(a.prefilled, caseName).toBe(true);
            expect(a.changeButton, caseName).toBe(false);
          } else if (status === 'complete') {
            expect(a.confirmedValue, caseName).toBe(true);
            expect(a.changeButton, caseName).toBe(true);
            expect(a.editor, caseName).toBe(false);
          } else {
            // Illegal: closed-with-Change when confirmed, editor when not;
            // either way the status class carries the red styling.
            expect(withDecision ? a.confirmedValue : a.editor, caseName).toBe(true);
          }

          // Distinguishable: no two cases of this kind may render with an
          // identical affordance signature.
          const signature = JSON.stringify(a);
          const collision = signatures.get(signature);
          expect(collision, `${caseName} renders identically to ${collision}`).toBeUndefined();
          signatures.set(signature, caseName);
        }
      }
    });
  }
});
