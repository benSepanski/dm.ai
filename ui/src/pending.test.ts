// The no-op rule (finding 12): a tentative edit identical to the saved
// selection is not an edit — order changes from uncheck/recheck included.
import { describe, expect, it } from 'vitest';
import { isRealEdit, sameSelection } from './Wizard';
import { groupedRows } from './SlotCard';
import type { OptionView } from './engine';

describe('sameSelection', () => {
  it('treats option lists as sets (reorder is a no-op)', () => {
    expect(
      sameSelection(
        { kind: 'options', value: ['a', 'b', 'c'] },
        { kind: 'options', value: ['c', 'a', 'b'] },
      ),
    ).toBe(true);
    expect(
      sameSelection(
        { kind: 'options', value: ['a', 'b'] },
        { kind: 'options', value: ['a', 'b', 'b'] },
      ),
    ).toBe(false);
  });
  it('compares singles and text by value, never across kinds', () => {
    expect(
      sameSelection({ kind: 'option', value: 'x' }, { kind: 'option', value: 'x' }),
    ).toBe(true);
    expect(
      sameSelection({ kind: 'text', value: 'x' }, { kind: 'option', value: 'x' }),
    ).toBe(false);
  });
});

describe('groupedRows', () => {
  const opt = (id: string, group: string | undefined): OptionView => ({
    id,
    label: id,
    summary: '',
    details: [],
    available: true,
    unavailable_reason: undefined,
    group,
    badge: undefined,
  });
  it('interleaves headings when the catalog spans two groups', () => {
    const a = opt('a', 'Curriculum');
    const b = opt('b', 'Curriculum');
    const c = opt('c', 'Other');
    expect(groupedRows([a, b, c], [a, b, c])).toEqual(['Curriculum', a, b, 'Other', c]);
  });
  it('keeps headings on a filtered list (the label survives filtering)', () => {
    const a = opt('a', 'Curriculum');
    const b = opt('b', 'Other');
    expect(groupedRows([a, b], [b])).toEqual(['Other', b]);
  });
  it('emits no headings for a single-group catalog', () => {
    const all = [opt('a', undefined), opt('b', undefined)];
    expect(groupedRows(all, all)).toEqual(all);
  });
});

describe('isRealEdit', () => {
  it('an emptied field on an unconfirmed slot is a no-op', () => {
    expect(isRealEdit(undefined, { kind: 'text', value: '   ' })).toBe(false);
    expect(isRealEdit(undefined, { kind: 'options', value: [] })).toBe(false);
    expect(isRealEdit(undefined, { kind: 'text', value: 'Brave' })).toBe(true);
  });
  it('a saved slot compares against what is saved', () => {
    expect(
      isRealEdit({ kind: 'option', value: 'a' }, { kind: 'option', value: 'a' }),
    ).toBe(false);
    expect(
      isRealEdit({ kind: 'option', value: 'a' }, { kind: 'option', value: 'b' }),
    ).toBe(true);
  });
});
