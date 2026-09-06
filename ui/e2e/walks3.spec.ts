// Spec walks 7–10: fill-remaining preserves confirmed work, the stubborn
// Dex draft, the version-bump review flags (UI leg over the hidden
// test-support fixture, mirroring checks/version_guard.rs), and the
// greyed shelf.
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from '@playwright/test';
import {
  declareFirstGame,
  confirmBoosts,
  confirmOption,
  confirmText,
  createCharacter,
  gotoStep,
  slot,
} from './helpers';
import { TestServer } from './server';

let server: TestServer;

test.beforeEach(async () => {
  server = new TestServer();
  await server.start();
  await declareFirstGame(server);
});

test.afterEach(async () => {
  await server.stop();
});

test('walk 7 — fill the rest: hand-built ancestry and background never move', async ({
  page,
}) => {
  await createCharacter(page, server, 'HalfDone');

  // Half-build by hand: ancestry + background only.
  await gotoStep(page, 'Ancestry');
  await confirmOption(page, 'pf2e.ancestry', 'Leshy');
  await confirmOption(page, 'pf2e.ancestry.heritage', 'Leaf Leshy');
  await confirmOption(page, 'pf2e.ancestry.feat', 'Seedpod');
  await confirmBoosts(page, 'pf2e.boosts.ancestry-free', ['Strength']);
  await gotoStep(page, 'Background');
  await confirmOption(page, 'pf2e.background', 'Nomad');
  await confirmText(page, 'pf2e.background.lore', 'Steppe');
  await confirmBoosts(page, 'pf2e.boosts.background-choice', ['Constitution']);
  await confirmBoosts(page, 'pf2e.boosts.background-free', ['Strength']);

  await page.getByRole('button', { name: 'Fill remaining with suggestions' }).click();
  await expect(page.locator('.notice')).toContainText('Every open choice was filled');

  // Confirmed choices are untouched — same values, no suggested badge.
  await gotoStep(page, 'Ancestry');
  const ancestryCard = slot(page, 'pf2e.ancestry');
  await expect(ancestryCard.locator('.slot-confirmed-value')).toHaveText('Leshy');
  await expect(ancestryCard.locator('.badge-suggested')).toHaveCount(0);
  await gotoStep(page, 'Background');
  await expect(slot(page, 'pf2e.background.lore').locator('.slot-confirmed-value')).toHaveText(
    'Steppe',
  );
  await expect(slot(page, 'pf2e.background.lore').locator('.badge-suggested')).toHaveCount(0);

  // The filled slots carry the suggested badge, and the draft finishes.
  await gotoStep(page, 'Class');
  await expect(slot(page, 'pf2e.class').locator('.badge-suggested')).toBeVisible();
  await page.getByRole('button', { name: 'Finalize character' }).click();
  await expect(page.locator('.sheet-page')).toBeVisible();
  await expect(page.getByText(/Leshy \(Leaf Leshy\) Fighter 1/)).toBeVisible();
  await expect(
    page.locator('.sheet-entry', { has: page.locator('dt', { hasText: 'Steppe Lore' }) }),
  ).toBeVisible();
});

test('walk 8 — the stubborn draft: Dexterity key attribute confirmed first, fill adapts around it', async ({
  page,
}) => {
  await createCharacter(page, server, 'Stubborn');
  await gotoStep(page, 'Class');
  await confirmOption(page, 'pf2e.class', 'Fighter');
  await confirmBoosts(page, 'pf2e.class.key-attribute', ['Dexterity']);

  await page.getByRole('button', { name: 'Fill remaining with suggestions' }).click();
  await expect(page.locator('.notice')).toBeVisible();

  // The confirmed Dexterity pick never moves and stays a player decision.
  const keyCard = slot(page, 'pf2e.class.key-attribute');
  await expect(keyCard.locator('.slot-confirmed-value')).toHaveText('Dexterity');
  await expect(keyCard.locator('.badge-suggested')).toHaveCount(0);

  // Suggestions adapted (draft completes) or the remainder is on the
  // checklist — either way, nothing was overwritten. The current suggested
  // build adapts fully, so the draft is finalizable.
  const checklist = page.getByTestId('checklist');
  const done = await checklist.getByText('Everything checks out').isVisible();
  if (done) {
    await expect(page.getByRole('button', { name: 'Finalize character' })).toBeEnabled();
  } else {
    await expect(page.locator('.notice')).toContainText('still need you');
  }
});

test('walk 9 — the bump: divergent replay flags for review, accept; identical offers quiet re-pin', async ({
  page,
}) => {
  // Fabricate a prior shipped version exactly as checks/version_guard.rs
  // does: build real characters, kill the server, doctor the files, and
  // restart with the hidden --extra-known-versions test-support flag.
  // Versions are per ruleset and prefixed by the system id; the campaign
  // view says which one this directory plays.
  const campaign = (await (await fetch(`${server.url}/api/campaign`)).json()) as {
    system: string;
  };
  const TEST_VERSION = `${campaign.system}-pc.0.0.1-test`;
  const api = async (path: string, body: unknown): Promise<Record<string, unknown>> => {
    const res = await fetch(`${server.url}${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    return (await res.json()) as Record<string, unknown>;
  };
  const make = async (name: string): Promise<string> => {
    const draft = await api('/api/characters', { name });
    const id = draft['id'] as string;
    const confirm = await api(`/api/characters/${id}/confirm`, {
      version: draft['version'],
      decision: {
        id: `${id}-fixture`,
        slot: 'pf2e.ancestry',
        selection: { kind: 'option', value: 'ancestry.goblin' },
        source: 'player',
      },
    });
    expect(confirm['outcome']).toBe('confirmed');
    return id;
  };
  const divergentId = await make('Diver');
  const identicalId = await make('Same');
  await server.stop();

  const doctor = (id: string, edit: (doc: Record<string, unknown>) => void) => {
    const path = join(server.dataDir, 'characters', `${id}.json`);
    const doc = JSON.parse(readFileSync(path, 'utf8')) as Record<string, unknown>;
    edit(doc);
    writeFileSync(path, JSON.stringify(doc, null, 2));
  };
  let oldValueLabel = '';
  doctor(divergentId, (doc) => {
    doc['rules_version'] = TEST_VERSION;
    doc['state'] = 'finalized';
    // A finalized file's stored sheet reflects its whole log (schema v4).
    doc['finalized_through'] = (doc['log'] as unknown[]).length;
    // The stored sheet holds a value current data does not derive — as if
    // the record changed under the old pin.
    const sheet = doc['sheet'] as {
      sections: { title: string; entries: { label: string; value: string }[] }[];
    };
    const entry = sheet.sections[0]?.entries[0];
    if (entry === undefined) {
      throw new Error('fixture sheet has no entries');
    }
    oldValueLabel = entry.label;
    entry.value = '999 (old derivation)';
  });
  doctor(identicalId, (doc) => {
    doc['rules_version'] = TEST_VERSION;
    doc['state'] = 'finalized';
    doc['finalized_through'] = (doc['log'] as unknown[]).length;
  });
  const extraPath = join(server.dataDir, 'extra-known-versions.json');
  // The test-support extras file is keyed by system, so a fabricated prior
  // version can never land in another ruleset's guard.
  writeFileSync(
    extraPath,
    JSON.stringify({ [campaign.system]: { versions: { [TEST_VERSION]: [] } } }),
  );
  server.extraArgs = ['--extra-known-versions', extraPath];
  await server.start();

  // The roster tells both stories apart.
  await page.goto(server.url);
  const diverEntry = page.locator('.roster-entry', { hasText: 'Diver' });
  const sameEntry = page.locator('.roster-entry', { hasText: 'Same' });
  await expect(diverEntry.locator('.version-badge')).toHaveText('Review: values changed');
  await expect(sameEntry.locator('.version-badge')).toHaveText('Data updated — re-pin available');

  // Divergent: old vs new side by side, sheet untouched until accept.
  await diverEntry.locator('.roster-open').click();
  const panel = page.locator('.version-panel');
  await expect(panel).toContainText('Rules data changed');
  await expect(panel).toContainText(TEST_VERSION);
  await expect(panel.locator('.version-diff')).toContainText(oldValueLabel);
  await expect(panel.locator('.version-old')).toHaveText('999 (old derivation)');
  await expect(page.locator('.sheet-page')).toContainText('999 (old derivation)');
  await panel.getByRole('button', { name: 'Accept new values' }).click();
  await expect(page.locator('.version-panel')).toHaveCount(0);
  await expect(page.locator('.sheet-page')).not.toContainText('999 (old derivation)');

  // Identical: the quiet re-pin, one explicit action.
  await page.getByRole('button', { name: '← Roster' }).click();
  await sameEntry.locator('.roster-open').click();
  await expect(page.locator('.version-panel')).toContainText('identical sheet');
  await page.getByRole('button', { name: /Re-pin to/ }).click();
  await expect(page.locator('.version-panel')).toHaveCount(0);

  // Both resolutions stick: the roster shows no flags any more.
  await page.getByRole('button', { name: '← Roster' }).click();
  await expect(page.locator('.version-badge')).toHaveCount(0);
});

test('walk 10 — the greyed shelf: cantrip heritages and Unconventional Weaponry explain themselves', async ({
  page,
}) => {
  await createCharacter(page, server, 'Browser');
  await gotoStep(page, 'Ancestry');
  await confirmOption(page, 'pf2e.ancestry', 'Gnome');

  // Both cantrip-dependent gnome heritages are visible, unpickable, and
  // honest about what is missing.
  const heritageCard = slot(page, 'pf2e.ancestry.heritage');
  const greyedHeritage = (label: string) =>
    heritageCard.locator('.option', { has: page.locator('.option-label', { hasText: label }) });
  await expect(greyedHeritage('Fey-touched Gnome').locator('.option-unavailable')).toHaveText(
    "requires a choice from 'primal cantrips', which has no entries in this rules-data version",
  );
  await expect(greyedHeritage('Fey-touched Gnome').getByRole('radio')).toBeDisabled();
  await expect(greyedHeritage('Wellspring Gnome').locator('.option-unavailable')).toContainText(
    'wellspring cantrips',
  );

  // Unconventional Weaponry (uncommon weapons excluded this slice) greys
  // the same way on the human feat shelf.
  await slot(page, 'pf2e.ancestry').getByRole('button', { name: 'Change…' }).click();
  await page.locator('.modal').getByRole('button', { name: 'Clear and change' }).click();
  await confirmOption(page, 'pf2e.ancestry', 'Human');
  const featCard = slot(page, 'pf2e.ancestry.feat');
  const unconventional = featCard.locator('.option', {
    has: page.locator('.option-label', { hasText: 'Unconventional Weaponry' }),
  });
  await expect(unconventional.locator('.option-unavailable')).toHaveText(
    "requires a choice from 'uncommon weapons', which has no entries in this rules-data version",
  );
  await expect(unconventional.getByRole('radio')).toBeDisabled();
});
