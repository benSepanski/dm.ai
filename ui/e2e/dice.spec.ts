// The dnd-dice stories, walked against the real server binary and the
// built UI it embeds: the roll and the reroll with its clearing confirm
// and the history visible; entered dice with a face off the die, forced
// duplicates, and the cap; the double tap; the hit die with a kept reroll,
// the abandoned level, and an entered d10; the seeded badge; and nothing
// else moved (the array path meets no roll card). Every screen visited
// rides the layout sweep through the shared helpers.
//
// A test file may name the systems it drives and parse the numbers the
// engine renders; the shipped UI never does either.
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, type Locator, type Page, test } from '@playwright/test';
import {
  confirmAssignment,
  confirmMultiUntilFull,
  confirmOption,
  createCharacter,
  gotoStep,
  placeScores,
  sideSheetEntry,
  slot,
} from './helpers';
import { expectSaneLayout } from './layout';
import { TestServer } from './server';

interface CampaignView {
  system?: string;
  games: { id: string; name: string }[];
  seeded_dice: boolean;
}

async function campaignView(server: TestServer): Promise<CampaignView> {
  return (await (await fetch(`${server.url}/api/campaign`)).json()) as CampaignView;
}

async function declare5e(server: TestServer): Promise<void> {
  const view = await campaignView(server);
  const game = view.games.find((g) => /5\.5e/.test(g.name));
  if (game === undefined) {
    throw new Error('no shipped 5.5e game');
  }
  const response = await fetch(`${server.url}/api/campaign`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ system: game.id }),
  });
  if (!response.ok) {
    throw new Error(`declaring ${game.id} failed: ${response.status}`);
  }
}

function sectionEntry(root: Locator, section: string, label: string) {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return root
    .locator('.sheet-section', { has: root.page().getByRole('heading', { name: section }) })
    .locator('.sheet-entry')
    .filter({ has: root.page().locator('dt', { hasText: new RegExp(`^${escaped}[+−]?$`) }) });
}

/** The character file on disk whose name decision is `name`. */
function characterFile(server: TestServer, name: string): Record<string, unknown> & {
  log: { slot: string; selection: { kind: string; value: unknown } }[];
} {
  const dir = join(server.dataDir, 'characters');
  for (const entry of readdirSync(dir)) {
    if (!entry.endsWith('.json')) {
      continue;
    }
    const doc = JSON.parse(readFileSync(join(dir, entry), 'utf8')) as ReturnType<
      typeof characterFile
    >;
    if (doc.log.some((d) => d.selection.kind === 'text' && d.selection.value === name)) {
      return doc;
    }
  }
  throw new Error(`no character file named ${name}`);
}

function rollHistory(doc: ReturnType<typeof characterFile>, slotId: string) {
  const decision = doc.log.find((d) => d.slot === slotId);
  return (decision?.selection.value ?? []) as { groups: number[][]; origin: string }[];
}

/** The live set's totals, parsed from the card's render-ready label. */
async function liveTotals(card: Locator): Promise<number[]> {
  const text = await card.locator('.roll-set[data-live] .roll-totals').textContent();
  return (text ?? '').split(',').map((t) => Number(t.trim()));
}

const ABILITIES = ['Strength', 'Dexterity', 'Constitution', 'Intelligence', 'Wisdom', 'Charisma'];

async function assignScores(page: Page, scores: Record<string, number>) {
  await placeScores(page, 'dnd5e.scores.assign', scores);
  await confirmAssignment(page, 'dnd5e.scores.assign');
}

function modifier(score: number): string {
  const m = Math.floor((score - 10) / 2);
  return m >= 0 ? `+${m}` : `−${-m}`;
}

/** Class and origin as Brannock has them; leaves the wizard on the
 * ability-score step with the rolling method chosen. */
async function throughToRolling(page: Page, server: TestServer, name: string) {
  await createCharacter(page, server, name);
  await gotoStep(page, 'Class');
  await confirmOption(page, 'dnd5e.class', 'Fighter');
  await gotoStep(page, 'Origin');
  await confirmOption(page, 'dnd5e.background', 'Soldier');
  await confirmOption(page, 'dnd5e.background.increase', 'Strength +2, Constitution +1');
  await confirmOption(page, 'dnd5e.species', 'Human');
  await confirmOption(page, 'dnd5e.species.skill', 'Perception');
  await confirmOption(page, 'dnd5e.species.feat', 'Alert');
  await gotoStep(page, 'Ability Scores');
  await confirmOption(page, 'dnd5e.scores.method', 'Random Generation');
}

/** Finish a rolled character: assignment from the live set, class choices,
 * equipment; finalize. */
async function finishAndFinalize(page: Page) {
  const card = slot(page, 'dnd5e.scores.roll');
  const totals = [...(await liveTotals(card))].sort((a, b) => b - a);
  const scores = Object.fromEntries(ABILITIES.map((a, i) => [a, totals[i]!]));
  await assignScores(page, scores);
  await gotoStep(page, 'Class Choices');
  await confirmMultiUntilFull(page, 'dnd5e.class.skills', ['Acrobatics', 'Insight']);
  await confirmOption(page, 'dnd5e.class.style', 'Defense');
  await confirmMultiUntilFull(page, 'dnd5e.class.masteries', ['Greatsword', 'Flail', 'Javelin']);
  await gotoStep(page, 'Equipment');
  await confirmOption(page, 'dnd5e.background.equipment', 'Soldier equipment package');
  await confirmOption(page, 'dnd5e.equipment.package', 'Package A');
  await gotoStep(page, 'Details');
  await expect(page.getByTestId('checklist').getByText('Everything checks out')).toBeVisible();
  await page.getByRole('button', { name: 'Finalize character' }).click();
  await expect(page.locator('.sheet-page')).toBeVisible();
  await expectSaneLayout(page);
}

let server: TestServer;

test.beforeEach(async () => {
  server = new TestServer();
  await server.start();
  await declare5e(server);
});

test.afterEach(async () => {
  await server.stop();
});

test('the roll and the reroll: the app rolls, the assignment offers the totals, rolling again asks and keeps the history', async ({
  page,
}) => {
  await throughToRolling(page, server, 'Ysolde');
  const card = slot(page, 'dnd5e.scores.roll');
  const assign = slot(page, 'dnd5e.scores.assign');
  await expect(card).toContainText('Nothing rolled yet.');
  await expect(assign).toHaveClass(/locked/);
  await expect(assign).toContainText('roll your ability scores first');
  await expectSaneLayout(page);

  // The roll: six sets of four faces, the dropped die named, tagged rolled.
  await card.getByRole('button', { name: 'Roll' }).click();
  await expect(card.locator('.roll-set')).toHaveCount(1);
  await expect(card.locator('.roll-set .option-badge')).toHaveText('rolled');
  await expect(card.locator('.roll-faces li')).toHaveCount(6);
  await expect(card.locator('.roll-faces li').first()).toContainText('→');
  await expectSaneLayout(page);

  // Assign the totals, largest to Strength; the Soldier's +2 stacks live.
  const totals = [...(await liveTotals(card))].sort((a, b) => b - a);
  expect(totals).toHaveLength(6);
  const scores = Object.fromEntries(ABILITIES.map((a, i) => [a, totals[i]!]));
  await assignScores(page, scores);
  const side = page.locator('.wizard-side');
  const strength = totals[0]! + 2;
  await expect(sectionEntry(side, 'Ability Scores', 'Strength').locator('.sheet-value')).toHaveText(
    `${strength} (${modifier(strength)})`,
  );

  // Rolling again asks first (the assignment would be cleared), keeps the
  // first set in the record, and clears the assignment.
  await card.getByRole('button', { name: 'Roll again' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Roll again?');
  await expect(dialog).toContainText('Assign ability scores');
  await expectSaneLayout(page);
  await dialog.getByRole('button', { name: 'Roll again' }).click();
  await expect(card.locator('.roll-set')).toHaveCount(2);
  await expect(card.locator('.roll-set').nth(0)).toHaveClass(/roll-superseded/);
  await expect(card.locator('.roll-set').nth(1)).toHaveClass(/roll-live/);
  await expect(assign.locator('.slot-confirmed-value')).toHaveCount(0);
  await expectSaneLayout(page);

  // The file: both sets, in order, tagged.
  const history = rollHistory(characterFile(server, 'Ysolde'), 'dnd5e.scores.roll');
  expect(history).toHaveLength(2);
  expect(history.map((s) => s.origin)).toEqual(['app', 'app']);
  expect(history[0]!.groups).toHaveLength(6);
  expect(history[0]!.groups[0]).toHaveLength(4);
});

test('entered dice: a face off the die is refused, duplicates assign, the cap is reached; a roll on top; the double tap', async ({
  page,
}) => {
  await throughToRolling(page, server, 'Marrow');
  const card = slot(page, 'dnd5e.scores.roll');
  await card.getByRole('button', { name: 'Enter dice' }).click();
  const inputs = card.getByRole('spinbutton');
  await expect(inputs).toHaveCount(24);
  // Two identical sets and a 6, 6, 6, 1; a 7 in the first box is illegal
  // with the rule named.
  const faces = [
    [7, 6, 6, 1],
    [4, 4, 4, 1],
    [4, 4, 4, 1],
    [4, 3, 3, 2],
    [3, 3, 3, 1],
    [6, 1, 1, 1],
  ];
  for (const [g, row] of faces.entries()) {
    for (const [d, face] of row.entries()) {
      await inputs.nth(g * 4 + d).fill(String(face));
    }
  }
  await expect(card).toContainText('Every face must be from 1 to 6.');
  await expect(card.getByRole('button', { name: /confirm entered dice/i })).toBeDisabled();
  await inputs.nth(0).fill('6');
  await expect(card.getByRole('button', { name: /confirm entered dice/i })).toBeEnabled();
  await card.getByRole('button', { name: /confirm entered dice/i }).click();
  await expect(card.locator('.roll-set')).toHaveCount(1);
  await expect(card.locator('.roll-set .option-badge')).toHaveText('entered');
  await expect(card.locator('.roll-set[data-live] .roll-totals')).toHaveText('18, 12, 12, 10, 9, 8');
  await expectSaneLayout(page);

  // The two twelves go to two abilities; 18 + 2 reads 20, the cap, with
  // the step complete.
  await assignScores(page, {
    Strength: 18,
    Dexterity: 12,
    Constitution: 12,
    Intelligence: 9,
    Wisdom: 10,
    Charisma: 8,
  });
  const side = page.locator('.wizard-side');
  await expect(sectionEntry(side, 'Ability Scores', 'Strength').locator('.sheet-value')).toHaveText(
    '20 (+5)',
  );
  await expect(page.locator('.step-link', { hasText: 'Ability Scores' })).toHaveClass(
    /status-complete/,
  );

  // An app roll on top: the entered set stays, superseded; the new one is
  // live and tagged rolled.
  await card.getByRole('button', { name: 'Roll again' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Roll again' }).click();
  await expect(card.locator('.roll-set')).toHaveCount(2);
  await expect(card.locator('.roll-set').nth(0)).toContainText('entered');
  await expect(card.locator('.roll-set').nth(0)).toHaveClass(/roll-superseded/);
  await expect(card.locator('.roll-set').nth(1)).toContainText('rolled');
  await expect(card.locator('.roll-set').nth(1)).toHaveClass(/roll-live/);

  // The double tap: once the button has rested after the last roll, two
  // clicks as fast as the page can take them record exactly one more set
  // (the button is busy after the first, then rests again).
  const again = card.getByRole('button', { name: 'Roll again' });
  await expect(again).toBeEnabled();
  await again.dispatchEvent('click');
  await again.dispatchEvent('click');
  await expect(card.locator('.roll-set')).toHaveCount(3);
  await page.waitForTimeout(400);
  await expect(card.locator('.roll-set')).toHaveCount(3);
  // ...and without a stale-version conflict notice: the second tap was
  // ignored, not raced.
  await expect(page.locator('.notice')).toHaveCount(0);
  expect(rollHistory(characterFile(server, 'Marrow'), 'dnd5e.scores.roll')).toHaveLength(3);
});

test('the hit die: rolled at level 2 with a kept reroll, abandoned with the level, entered at level 3', async ({
  page,
}) => {
  await throughToRolling(page, server, 'Tam');
  await slot(page, 'dnd5e.scores.roll').getByRole('button', { name: 'Roll' }).click();
  await expect(slot(page, 'dnd5e.scores.roll').locator('.roll-set')).toHaveCount(1);
  await finishAndFinalize(page);
  const sheet = page.locator('.sheet-page');

  // Level 2: the gains panel carries the fixed hit points; the one card is
  // the optional fixed-or-roll choice; finalize is open at once.
  await page.getByRole('button', { name: 'Level up to 2' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await expect(page.locator('.level-gains')).toContainText('Hit Points');
  await expect(page.getByTestId('diff-marker-Hit Points')).toContainText('decide below');
  const choice = slot(page, 'dnd5e.level.2.hit-points');
  await expect(choice).toBeVisible();
  await expect(choice).toContainText('(optional)');
  await expect(choice).toContainText('Take the fixed value');
  await expect(choice).toContainText(/= \d+ hit points/);
  await expect(slot(page, 'dnd5e.level.2.hit-die')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Finalize level 2' })).toBeEnabled();
  // The sidebar sheet shows no default either, and the browser engine
  // previews over the full log (no failure notice, ever, during a level).
  await expect(sideSheetEntry(page, 'Hit Points')).toHaveText('?');
  await expect(page.getByTestId('engine-failure')).toHaveCount(0);
  await expectSaneLayout(page);

  // Choose to roll: the die card opens and finalize waits on it.
  await confirmOption(page, 'dnd5e.level.2.hit-points', 'Roll a d10');
  await expect(page.getByTestId('diff-marker-Hit Points')).toContainText('roll below');
  const hitDie = slot(page, 'dnd5e.level.2.hit-die');
  await expect(hitDie).toBeVisible();
  await expect(page.getByRole('button', { name: 'Finalize level 2' })).toBeDisabled();
  await expect(page.getByTestId('checklist')).toContainText('Roll your hit die');

  // Roll a die, then again: both kept, the second live, the gains follow.
  await hitDie.getByRole('button', { name: 'Roll' }).click();
  await expect(hitDie.locator('.roll-set')).toHaveCount(1);
  await hitDie.getByRole('button', { name: 'Roll again' }).click();
  await expect(hitDie.locator('.roll-set')).toHaveCount(2);
  await expect(hitDie.locator('.roll-set').nth(0)).toHaveClass(/roll-superseded/);
  await expect(page.getByTestId('diff-marker-Hit Points')).toHaveCount(0);
  await expect(page.locator('.level-gains')).toContainText('rolled');
  await expect(sideSheetEntry(page, 'Hit Points')).not.toHaveText('?');
  await expect(page.getByRole('button', { name: 'Finalize level 2' })).toBeEnabled();
  // Change the choice back to the fixed value: the dialog names the die
  // it clears; the sheet and the row follow.
  await slot(page, 'dnd5e.level.2.hit-points').getByRole('button', { name: /change/i }).click();
  const change = page.getByRole('dialog');
  await expect(change).toContainText('Change Hit Points?');
  await expect(change).toContainText('roll the hit die');
  await change.getByRole('button', { name: 'Clear and change' }).click();
  await expect(slot(page, 'dnd5e.level.2.hit-die')).toHaveCount(0);
  await expect(page.getByTestId('diff-marker-Hit Points')).toContainText('decide below');
  await confirmOption(page, 'dnd5e.level.2.hit-points', 'Roll a d10');
  await slot(page, 'dnd5e.level.2.hit-die').getByRole('button', { name: 'Roll' }).click();
  await expect(slot(page, 'dnd5e.level.2.hit-die').locator('.roll-set')).toHaveCount(1);
  await expect(page.getByTestId('engine-failure')).toHaveCount(0);
  await expectSaneLayout(page);

  // Abandon: the confirm names the choice and the die; the file holds no trace.
  await page.getByRole('button', { name: 'Abandon level 2' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Abandon level 2?');
  await expect(dialog).toContainText('Hit Points');
  await dialog.getByRole('button', { name: 'Discard and go back' }).click();
  await expect(sheet.locator('.sheet-summary').first()).toHaveText('Human Fighter 1');
  expect(rollHistory(characterFile(server, 'Tam'), 'dnd5e.level.2.hit-die')).toHaveLength(0);

  // Level again and take the fixed value outright: the marker goes, the
  // breakdown says fixed.
  await page.getByRole('button', { name: 'Level up to 2' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await confirmOption(page, 'dnd5e.level.2.hit-points', 'Take the fixed value');
  await expect(page.getByTestId('diff-marker-Hit Points')).toHaveCount(0);
  await page.getByRole('button', { name: 'Finalize level 2' }).click();
  await expect(sheet).toBeVisible();
  await expect(sheet.locator('.sheet-summary').first()).toHaveText('Human Fighter 2');
  const hp2 = sectionEntry(sheet, 'Combat', 'Hit Points');
  await hp2.getByRole('button', { name: 'breakdown for Hit Points' }).click();
  await expect(hp2).toContainText('Level 2: fixed value 6');
  await expectSaneLayout(page);

  // Level 3: the Champion, and a physical d10 — an 11 is refused with the
  // rule named, a 7 is accepted and tagged entered.
  await page.getByRole('button', { name: 'Level up to 3' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await confirmOption(page, 'dnd5e.level.3.subclass', 'Champion');
  await confirmOption(page, 'dnd5e.level.3.hit-points', 'Roll a d10');
  const die3 = slot(page, 'dnd5e.level.3.hit-die');
  await die3.getByRole('button', { name: 'Enter dice' }).click();
  const input = die3.getByRole('spinbutton');
  await expect(input).toHaveCount(1);
  await input.fill('11');
  await expect(die3).toContainText('Every face must be from 1 to 10.');
  await input.fill('7');
  await die3.getByRole('button', { name: /confirm entered dice/i }).click();
  await expect(die3.locator('.roll-set')).toHaveCount(1);
  await expect(die3.locator('.roll-set .roll-totals')).toHaveText('7');
  await expect(die3.locator('.roll-set .option-badge')).toHaveText('entered');
  await page.getByRole('button', { name: 'Finalize level 3' }).click();
  await expect(sheet).toBeVisible();
  const hp3 = sectionEntry(sheet, 'Combat', 'Hit Points');
  await hp3.getByRole('button', { name: 'breakdown for Hit Points' }).click();
  await expect(hp3).toContainText('Level 3: entered 7');
  await expectSaneLayout(page);
});

test('the seeded badge, and nothing else moved: the array path meets no roll card', async ({
  page,
}) => {
  // No flag: no badge.
  await page.goto(server.url);
  await expect(page.getByTestId('seeded-dice')).toHaveCount(0);
  expect((await campaignView(server)).seeded_dice).toBe(false);

  // The array path: no roll card, the assignment as before.
  await createCharacter(page, server, 'Plain');
  await gotoStep(page, 'Ability Scores');
  await confirmOption(page, 'dnd5e.scores.method', 'Standard Array');
  await expect(slot(page, 'dnd5e.scores.roll')).toHaveCount(0);
  await expect(slot(page, 'dnd5e.scores.assign')).not.toHaveClass(/locked/);

  // A seeded server says so on every load.
  const seeded = new TestServer();
  seeded.extraArgs = ['--dice-seed', '7'];
  await seeded.start();
  try {
    await declare5e(seeded);
    expect((await campaignView(seeded)).seeded_dice).toBe(true);
    await page.goto(seeded.url);
    await expect(page.getByTestId('seeded-dice')).toBeVisible();
    await expect(page.getByTestId('seeded-dice')).toContainText('testing only');
    await expectSaneLayout(page);
  } finally {
    await seeded.stop();
  }
});
