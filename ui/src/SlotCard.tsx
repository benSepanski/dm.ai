// One choice slot: options, tentative selection, confirm, and the
// change-with-dependent-clearing flow. Pure presentation — counts, legality,
// and effects all come from the engine.
import { useState } from 'react';
import type { ClearPreview, Decision, MeterView, OptionView, Selection, SlotView } from './engine';

/**
 * Option lists longer than this get a text filter (spec req 8: full breadth
 * must be scannable at the table). Filtering is in-memory over the
 * render-ready option array — no server calls, no game logic.
 */
export const FILTER_THRESHOLD = 15;

function matchesFilter(option: OptionView, needle: string): boolean {
  return (
    option.label.toLowerCase().includes(needle) ||
    option.summary.toLowerCase().includes(needle)
  );
}

/**
 * The shared filter state for one option list. Lives in the slot editor,
 * which remounts per slot (keyed by slot id), so the query is ephemeral UI
 * state that clears on slot change. Greyed options stay in the results —
 * the filter narrows by text, never by availability.
 */
function useOptionFilter(options: OptionView[]): {
  filterBox: React.ReactNode;
  visible: OptionView[];
} {
  const [query, setQuery] = useState('');
  if (options.length <= FILTER_THRESHOLD) {
    return { filterBox: null, visible: options };
  }
  const needle = query.trim().toLowerCase();
  const visible = needle === '' ? options : options.filter((o) => matchesFilter(o, needle));
  const filterBox = (
    <div className="option-filter">
      <input
        type="search"
        data-testid="option-filter"
        aria-label="Filter options"
        placeholder={`Filter ${options.length} options…`}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {needle !== '' && (
        <span className="option-filter-count" role="status">
          {visible.length === 0
            ? 'No options match'
            : `${visible.length} of ${options.length} shown`}
        </span>
      )}
    </div>
  );
  return { filterBox, visible };
}

export type TentativeSelection = Selection | null;

export function SlotCard({
  slot,
  live,
  tentative,
  onTentative,
  onConfirm,
  onRequestChange,
  busy,
  ack = null,
}: {
  slot: SlotView;
  /** The previewed twin of this slot (meters/status track tentative picks). */
  live?: SlotView | undefined;
  tentative: TentativeSelection;
  onTentative: (selection: TentativeSelection) => void;
  onConfirm: (selection: Selection) => void;
  onRequestChange: () => void;
  busy: boolean;
  /** Transient save acknowledgment ("Saved — 1 skill choice left"). */
  ack?: string | null;
}) {
  const gauges = (live ?? slot).meters;
  if (slot.status === 'locked') {
    return (
      <section className="slot locked status-locked" data-slot={slot.id}>
        <header>
          <h3>{slot.label}</h3>
        </header>
        <p className="slot-locked-reason">🔒 {slot.locked_reason}</p>
      </section>
    );
  }
  const confirmed = slot.decision ?? null;
  // Partial slots stay editable: the editor opens preloaded with the
  // confirmed picks, and Confirm amends in place.
  const editing = confirmed === null || slot.status === 'partial';
  const effectiveTentative =
    tentative ?? (slot.status === 'partial' ? (confirmed?.selection ?? null) : null);
  return (
    <section
      className={`slot status-${slot.status} ${confirmed !== null && !editing ? 'confirmed' : ''}`}
      data-slot={slot.id}
    >
      <header>
        <h3>
          {slot.label}
          {!slot.required && <span className="slot-optional"> (optional)</span>}
          {confirmed?.source === 'suggested' && (
            // Provenance drives the badge: a planner-filled decision says
            // so until the player edits it (re-confirming records the
            // player as the source and the badge flips off).
            <span className="badge-suggested" title="Filled by dm.ai's suggested build — edit to make it yours">
              suggested
            </span>
          )}
        </h3>
        {confirmed !== null && !editing && (
          <button
            type="button"
            className="slot-change"
            onClick={onRequestChange}
            disabled={busy}
          >
            Change…
          </button>
        )}
      </header>
      <MetersRow meters={gauges} />
      {ack !== null && (
        <p className="slot-ack" role="status">
          ✓ {ack}
        </p>
      )}
      {editing ? (
        <SlotEditor
          // Remounting per slot keeps editor-local UI state (the text
          // filter, expanded details) from leaking across slots.
          key={slot.id}
          slot={slot}
          tentative={effectiveTentative}
          onTentative={onTentative}
          onConfirm={onConfirm}
          busy={busy}
        />
      ) : (
        <ConfirmedSummary slot={slot} decision={confirmed} />
      )}
    </section>
  );
}

function MetersRow({ meters }: { meters: MeterView[] }) {
  if (meters.length === 0) {
    return null;
  }
  return (
    <p className="meters">
      {meters.map((meter, i) => (
        <span key={i} className={`meter meter-${meter.state}`} data-testid={`meter-${meter.label}`}>
          {meter.label} {meter.current}
          {meter.limit != null ? ` of ${meter.limit}` : ''}
          {meter.state === 'exceeded' ? ' — over the limit' : ''}
          {meter.state === 'short' ? ' — keep picking' : ''}
        </span>
      ))}
    </p>
  );
}

function ConfirmedSummary({ slot, decision }: { slot: SlotView; decision: Decision }) {
  const label = (id: string) => slot.options.find((o) => o.id === id)?.label ?? id;
  let text: string;
  switch (decision.selection.kind) {
    case 'option':
      text = label(decision.selection.value);
      break;
    case 'options':
      text = decision.selection.value.map(label).join(', ');
      break;
    case 'text':
      text = decision.selection.value;
      break;
  }
  return <p className="slot-confirmed-value">{text}</p>;
}

function SlotEditor({
  slot,
  tentative,
  onTentative,
  onConfirm,
  busy,
}: {
  slot: SlotView;
  tentative: TentativeSelection;
  onTentative: (selection: TentativeSelection) => void;
  onConfirm: (selection: Selection) => void;
  busy: boolean;
}) {
  switch (slot.kind.kind) {
    case 'single':
      return slot.presentation_hint === 'attribute-boosts' ? (
        <SingleBoostEditor
          slot={slot}
          tentative={tentative}
          onTentative={onTentative}
          onConfirm={onConfirm}
          busy={busy}
        />
      ) : (
        <SingleEditor
          slot={slot}
          tentative={tentative}
          onTentative={onTentative}
          onConfirm={onConfirm}
          busy={busy}
        />
      );
    case 'multi':
      // Attribute boosts render as one picker per boost so a player can
      // (wrongly) put two boosts on the same attribute and watch the
      // checklist flag it — the engine judges, the UI never blocks.
      return slot.presentation_hint === 'attribute-boosts' ? (
        <BoostsEditor
          slot={slot}
          count={slot.kind.count}
          tentative={tentative}
          onTentative={onTentative}
          onConfirm={onConfirm}
          busy={busy}
        />
      ) : (
        <MultiEditor
          slot={slot}
          count={slot.kind.count}
          tentative={tentative}
          onTentative={onTentative}
          onConfirm={onConfirm}
          busy={busy}
        />
      );
    case 'list':
      return (
        <ListEditor
          slot={slot}
          tentative={tentative}
          onTentative={onTentative}
          onConfirm={onConfirm}
          busy={busy}
        />
      );
    case 'text':
      return (
        <TextEditor
          multiline={slot.kind.multiline}
          tentative={tentative}
          onTentative={onTentative}
          onConfirm={onConfirm}
          busy={busy}
        />
      );
  }
}

function OptionRow({
  option,
  selected,
  control,
}: {
  option: OptionView;
  selected: boolean;
  control: React.ReactNode;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <li className={`option ${selected ? 'selected' : ''} ${option.available ? '' : 'unavailable'}`}>
      <label>
        {control}
        <span className="option-body">
          <span className="option-label">{option.label}</span>
          {option.summary !== '' && <span className="option-summary">{option.summary}</span>}
          {!option.available && option.unavailable_reason != null && (
            <span className="option-unavailable">{option.unavailable_reason}</span>
          )}
          {expanded &&
            option.details.map((d, i) => (
              <span key={i} className="option-detail">
                {d}
              </span>
            ))}
        </span>
      </label>
      {option.details.length > 0 && (
        <button
          type="button"
          className="option-toggle"
          onClick={() => setExpanded((e) => !e)}
          aria-label={expanded ? 'hide details' : 'show details'}
        >
          {expanded ? '▲' : '▼'}
        </button>
      )}
    </li>
  );
}

function SingleEditor({
  slot,
  tentative,
  onTentative,
  onConfirm,
  busy,
}: {
  slot: SlotView;
  tentative: TentativeSelection;
  onTentative: (selection: TentativeSelection) => void;
  onConfirm: (selection: Selection) => void;
  busy: boolean;
}) {
  const picked = tentative?.kind === 'option' ? tentative.value : null;
  const { filterBox, visible } = useOptionFilter(slot.options);
  return (
    <div>
      {filterBox}
      <ul className="option-list">
        {visible.map((option) => (
          <OptionRow
            key={option.id}
            option={option}
            selected={picked === option.id}
            control={
              <input
                type="radio"
                name={slot.id}
                checked={picked === option.id}
                disabled={!option.available || busy}
                onChange={() => onTentative({ kind: 'option', value: option.id })}
              />
            }
          />
        ))}
      </ul>
      <footer className="slot-actions">
        <button
          type="button"
          className="confirm"
          disabled={picked === null || busy}
          onClick={() => picked !== null && onConfirm({ kind: 'option', value: picked })}
        >
          Confirm {slot.label.toLowerCase()}
        </button>
      </footer>
    </div>
  );
}

function MultiEditor({
  slot,
  count,
  tentative,
  onTentative,
  onConfirm,
  busy,
}: {
  slot: SlotView;
  count: number;
  tentative: TentativeSelection;
  onTentative: (selection: TentativeSelection) => void;
  onConfirm: (selection: Selection) => void;
  busy: boolean;
}) {
  const picked = tentative?.kind === 'options' ? tentative.value : [];
  const remaining = count - picked.length;
  const toggle = (id: string) => {
    const next = picked.includes(id) ? picked.filter((p) => p !== id) : [...picked, id];
    onTentative({ kind: 'options', value: next });
  };
  const { filterBox, visible } = useOptionFilter(slot.options);
  return (
    <div>
      <p className="multi-counter" data-testid={`counter-${slot.id}`}>
        {remaining > 0
          ? `${remaining} of ${count} choice${count === 1 ? '' : 's'} left`
          : remaining === 0
            ? 'All choices made'
            : `${-remaining} too many selected`}
      </p>
      {filterBox}
      <ul className="option-list">
        {visible.map((option) => (
          <OptionRow
            key={option.id}
            option={option}
            selected={picked.includes(option.id)}
            control={
              <input
                type="checkbox"
                checked={picked.includes(option.id)}
                disabled={(!option.available && !picked.includes(option.id)) || busy}
                onChange={() => toggle(option.id)}
              />
            }
          />
        ))}
      </ul>
      <footer className="slot-actions">
        <button
          type="button"
          className="confirm"
          disabled={picked.length === 0 || busy}
          onClick={() => onConfirm({ kind: 'options', value: picked })}
        >
          Confirm {slot.label.toLowerCase()}
        </button>
      </footer>
    </div>
  );
}



function SingleBoostEditor({
  slot,
  tentative,
  onTentative,
  onConfirm,
  busy,
}: {
  slot: SlotView;
  tentative: TentativeSelection;
  onTentative: (selection: TentativeSelection) => void;
  onConfirm: (selection: Selection) => void;
  busy: boolean;
}) {
  const picked = tentative?.kind === 'option' ? tentative.value : '';
  return (
    <div>
      <div className="boost-rows">
        <label className="boost-row">
          <span>Boost</span>
          <select
            value={picked}
            disabled={busy}
            onChange={(e) =>
              onTentative(
                e.target.value === '' ? null : { kind: 'option', value: e.target.value },
              )
            }
          >
            <option value="">— choose an attribute —</option>
            {slot.options.map((option) => (
              <option key={option.id} value={option.id} disabled={!option.available}>
                {option.label}
                {option.available ? '' : ` (${option.unavailable_reason ?? 'unavailable'})`}
              </option>
            ))}
          </select>
        </label>
      </div>
      <footer className="slot-actions">
        <button
          type="button"
          className="confirm"
          disabled={picked === '' || busy}
          onClick={() => picked !== '' && onConfirm({ kind: 'option', value: picked })}
        >
          Confirm {slot.label.toLowerCase()}
        </button>
      </footer>
    </div>
  );
}

function BoostsEditor({
  slot,
  count,
  tentative,
  onTentative,
  onConfirm,
  busy,
}: {
  slot: SlotView;
  count: number;
  tentative: TentativeSelection;
  onTentative: (selection: TentativeSelection) => void;
  onConfirm: (selection: Selection) => void;
  busy: boolean;
}) {
  const picked = tentative?.kind === 'options' ? tentative.value : [];
  const rows = Array.from({ length: count }, (_, i) => picked[i] ?? '');
  const setRow = (index: number, value: string) => {
    const next = [...rows];
    next[index] = value;
    onTentative({ kind: 'options', value: next.filter((v) => v !== '') });
  };
  const remaining = count - picked.length;
  return (
    <div>
      <p className="multi-counter" data-testid={`counter-${slot.id}`}>
        {remaining > 0
          ? `${remaining} of ${count} boost${count === 1 ? '' : 's'} left`
          : 'All boosts assigned'}
      </p>
      <div className="boost-rows">
        {rows.map((value, index) => (
          <label key={index} className="boost-row">
            <span>Boost {count > 1 ? index + 1 : ''}</span>
            <select
              value={value}
              disabled={busy}
              onChange={(e) => setRow(index, e.target.value)}
            >
              <option value="">— choose an attribute —</option>
              {slot.options.map((option) => (
                <option key={option.id} value={option.id} disabled={!option.available}>
                  {option.label}
                  {option.available ? '' : ` (${option.unavailable_reason ?? 'unavailable'})`}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
      <footer className="slot-actions">
        <button
          type="button"
          className="confirm"
          disabled={picked.length === 0 || busy}
          onClick={() => onConfirm({ kind: 'options', value: picked })}
        >
          Confirm {slot.label.toLowerCase()}
        </button>
      </footer>
    </div>
  );
}

/**
 * Category headers for the shopping list. The data arrives categorized —
 * every equipment option ID is namespaced by its category — so grouping is
 * pure presentation over the render-ready array.
 */
const SHOP_GROUPS: readonly { prefix: string; label: string }[] = [
  { prefix: 'weapon.', label: 'Weapons' },
  { prefix: 'armor.', label: 'Armor' },
  { prefix: 'shield.', label: 'Shields' },
  { prefix: 'gear.', label: 'Adventuring gear' },
];

function groupShopOptions(
  options: OptionView[],
): { label: string; options: OptionView[] }[] {
  const groups = SHOP_GROUPS.map((g) => ({ label: g.label, options: [] as OptionView[] }));
  const other: OptionView[] = [];
  for (const option of options) {
    const index = SHOP_GROUPS.findIndex((g) => option.id.startsWith(g.prefix));
    if (index >= 0) {
      groups[index]?.options.push(option);
    } else {
      other.push(option);
    }
  }
  if (other.length > 0) {
    groups.push({ label: 'Other items', options: other });
  }
  return groups.filter((g) => g.options.length > 0);
}

function ListEditor({
  slot,
  tentative,
  onTentative,
  onConfirm,
  busy,
}: {
  slot: SlotView;
  tentative: TentativeSelection;
  onTentative: (selection: TentativeSelection) => void;
  onConfirm: (selection: Selection) => void;
  busy: boolean;
}) {
  const picked = tentative?.kind === 'options' ? tentative.value : [];
  const add = (id: string) => onTentative({ kind: 'options', value: [...picked, id] });
  const removeAt = (index: number) =>
    onTentative({ kind: 'options', value: picked.filter((_, i) => i !== index) });
  // The filter spans every category group; empty groups drop their headers.
  const { filterBox, visible } = useOptionFilter(slot.options);
  const grouped =
    slot.presentation_hint === 'shopping-list'
      ? groupShopOptions(visible)
      : [{ label: '', options: visible }];
  const addRow = (option: OptionView) => (
    <OptionRow
      key={option.id}
      option={option}
      selected={false}
      control={
        <button
          type="button"
          className="option-add"
          onClick={() => add(option.id)}
          disabled={busy}
        >
          Add
        </button>
      }
    />
  );
  return (
    <div>
      {picked.length > 0 && (
        <ul className="shopping-list">
          {picked.map((id, index) => (
            <li key={`${id}-${index}`}>
              {slot.options.find((o) => o.id === id)?.label ?? id}
              <button type="button" onClick={() => removeAt(index)} disabled={busy}>
                remove
              </button>
            </li>
          ))}
        </ul>
      )}
      {filterBox}
      {grouped.map((group) => (
        <div key={group.label} className="option-group">
          {group.label !== '' && (
            <h4 className="option-group-heading">{group.label}</h4>
          )}
          <ul className="option-list">{group.options.map(addRow)}</ul>
        </div>
      ))}
      <footer className="slot-actions">
        <button
          type="button"
          className="confirm"
          disabled={busy}
          onClick={() => onConfirm({ kind: 'options', value: picked })}
        >
          Confirm {slot.label.toLowerCase()}
        </button>
      </footer>
    </div>
  );
}

function TextEditor({
  multiline,
  tentative,
  onTentative,
  onConfirm,
  busy,
}: {
  multiline: boolean;
  tentative: TentativeSelection;
  onTentative: (selection: TentativeSelection) => void;
  onConfirm: (selection: Selection) => void;
  busy: boolean;
}) {
  const value = tentative?.kind === 'text' ? tentative.value : '';
  return (
    <div>
      {multiline ? (
        <textarea
          value={value}
          rows={4}
          onChange={(e) => onTentative({ kind: 'text', value: e.target.value })}
          disabled={busy}
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onTentative({ kind: 'text', value: e.target.value })}
          disabled={busy}
        />
      )}
      <footer className="slot-actions">
        <button
          type="button"
          className="confirm"
          disabled={value.trim() === '' || busy}
          onClick={() => onConfirm({ kind: 'text', value })}
        >
          Confirm
        </button>
      </footer>
    </div>
  );
}

/// The change-confirmation dialog: lists exactly what will be cleared.
export function ClearConfirmDialog({
  preview,
  slotLabel,
  onConfirm,
  onCancel,
}: {
  preview: ClearPreview;
  slotLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal">
        <h3>Change {slotLabel}?</h3>
        <p>This clears the following confirmed choices:</p>
        <ul className="clear-list">
          {preview.cleared.map((cleared, i) => (
            <li key={i}>
              <strong>{cleared.slot_label}</strong>: {cleared.selection_label}
            </li>
          ))}
        </ul>
        <footer className="modal-actions">
          <button type="button" onClick={onCancel}>
            Keep everything
          </button>
          <button type="button" className="danger" onClick={onConfirm}>
            Clear and change
          </button>
        </footer>
      </div>
    </div>
  );
}
