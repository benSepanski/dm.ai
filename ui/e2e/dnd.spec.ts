// The 5.5e stories (spec chargen-dnd), walked against the real server
// binary and the built UI it embeds: the second campaign (choose-game,
// Brannock through every card, a hand-checked sheet), the buy (point buy,
// the overspend, the gold alternative), level 2's empty level and the
// level-3 subclass (abandon, mid-level resume by reload and by kill -9,
// the cap note), jumping ahead, and the wrong drawer. Every screen visited
// rides the layout sweep through the shared helpers.
//
// "The PF2e directory is never asked" is campaign.spec.ts's business
// ("a directory already holding a character opens straight to the roster"
// and "a pre-declaration directory with characters is never asked") — not
// duplicated here.
//
// A test file may name the systems it drives; the shipped UI never does.
// The games are read from the campaign view and matched by name.
import { copyFileSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, type Locator, type Page, test } from '@playwright/test';
import {
  confirmMultiUntilFull,
  confirmOption,
  createCharacter,
  gotoStep,
  sideSheetEntry,
  slot,
} from './helpers';
import { expectSaneLayout } from './layout';
import { TestServer } from './server';

interface CampaignView {
  system?: string;
  system_name?: string;
  games: { id: string; name: string }[];
  license_lines: string[];
}

async function campaignView(server: TestServer): Promise<CampaignView> {
  return (await (await fetch(`${server.url}/api/campaign`)).json()) as CampaignView;
}

/** The shipped game whose name matches (the 5.5e one, or the other). */
async function gameNamed(server: TestServer, pattern: RegExp, negate = false) {
  const view = await campaignView(server);
  const game = view.games.find((g) => pattern.test(g.name) !== negate);
  if (game === undefined) {
    throw new Error(`no shipped game ${negate ? 'not ' : ''}matching ${pattern}`);
  }
  return game;
}

async function declareGame(server: TestServer, id: string): Promise<CampaignView> {
  const response = await fetch(`${server.url}/api/campaign`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ system: id }),
  });
  if (!response.ok) {
    throw new Error(`declaring ${id} failed: ${response.status} ${await response.text()}`);
  }
  return (await response.json()) as CampaignView;
}

async function createViaApi(server: TestServer, name: string): Promise<string> {
  const response = await fetch(`${server.url}/api/characters`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  expect(response.ok).toBe(true);
  return ((await response.json()) as { id: string }).id;
}

/**
 * A sheet entry's value, scoped to a titled section (Strength is both an
 * ability score and a saving throw). The dt carries the label plus the
 * breakdown toggle's glyph on the full sheet, hence the tolerant tail.
 */
function sectionEntry(root: Locator, section: string, label: string) {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return root
    .locator('.sheet-section', { has: root.page().getByRole('heading', { name: section }) })
    .locator('.sheet-entry')
    .filter({ has: root.page().locator('dt', { hasText: new RegExp(`^${escaped}[+−]?$`) }) })
    .locator('.sheet-value');
}

/** Open an entry's breakdown on the full sheet and return its text. */
function sectionDetail(root: Locator, section: string, label: string) {
  return root
    .locator('.sheet-section', { has: root.page().getByRole('heading', { name: section }) })
    .locator('.sheet-entry')
    .filter({ has: root.page().getByRole('button', { name: `breakdown for ${label}` }) });
}

/** The one-select-per-ability assignment editor: set each ability's score. */
async function assignScores(page: Page, scores: Record<string, number>) {
  const card = slot(page, 'dnd5e.scores.assign');
  await card.scrollIntoViewIfNeeded();
  for (const [ability, value] of Object.entries(scores)) {
    await card
      .locator('.select-row', { hasText: ability })
      .locator('select')
      .selectOption({ label: String(value) });
  }
}

async function confirmScores(page: Page, scores: Record<string, number>) {
  await assignScores(page, scores);
  const card = slot(page, 'dnd5e.scores.assign');
  await expect(card.getByTestId('counter-dnd5e.scores.assign')).toHaveText('All choices made');
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
}

/**
 * Brannock, as the crate's own walk builds him: Human Soldier Fighter,
 * Standard Array (Str 15, Con 14, Dex 13, Wis 12, Cha 10, Int 8), Str +2 /
 * Con +1, Perception and Alert from the Human, Acrobatics and Insight,
 * Defense, Greatsword / Flail / Javelin masteries, package A, the
 * Soldier's package. Leaves the wizard ready to finalize.
 */
async function buildBrannock(page: Page, server: TestServer) {
  await createCharacter(page, server, 'Brannock');
  const side = page.locator('.wizard-side');

  await gotoStep(page, 'Class');
  await confirmOption(page, 'dnd5e.class', 'Fighter');

  await gotoStep(page, 'Origin');
  await confirmOption(page, 'dnd5e.background', 'Soldier');
  // The increase card opens with the seven legal distributions.
  await expect(slot(page, 'dnd5e.background.increase').getByRole('radio')).toHaveCount(7);
  await confirmOption(page, 'dnd5e.background.increase', 'Strength +2, Constitution +1');
  // The Soldier's origin feat lands in the sidebar as he watches.
  await expect(side).toContainText('Savage Attacker');
  await confirmOption(page, 'dnd5e.species', 'Human');
  await confirmOption(page, 'dnd5e.species.skill', 'Perception');
  await confirmOption(page, 'dnd5e.species.feat', 'Alert');
  await expect(side).toContainText('Human Fighter 1');

  await gotoStep(page, 'Ability Scores');
  await confirmOption(page, 'dnd5e.scores.method', 'Standard Array');
  await confirmScores(page, {
    Strength: 15,
    Dexterity: 13,
    Constitution: 14,
    Intelligence: 8,
    Wisdom: 12,
    Charisma: 10,
  });
  // The increases stack on top as distributed, live.
  await expect(sectionEntry(side, 'Ability Scores', 'Strength')).toHaveText('17 (+3)');
  await expect(sectionEntry(side, 'Ability Scores', 'Constitution')).toHaveText('15 (+2)');

  await gotoStep(page, 'Class Choices');
  await confirmMultiUntilFull(page, 'dnd5e.class.skills', ['Acrobatics', 'Insight']);
  await confirmOption(page, 'dnd5e.class.style', 'Defense');
  await confirmMultiUntilFull(page, 'dnd5e.class.masteries', ['Greatsword', 'Flail', 'Javelin']);

  await gotoStep(page, 'Equipment');
  await confirmOption(page, 'dnd5e.background.equipment', 'Soldier equipment package');
  await confirmOption(page, 'dnd5e.equipment.package', 'Package A');

  await gotoStep(page, 'Details');
  await expect(slot(page, 'dnd5e.details.name').locator('.slot-confirmed-value')).toHaveText(
    'Brannock',
  );
  await expect(page.getByTestId('checklist').getByText('Everything checks out')).toBeVisible();
}

async function finalizeCreation(page: Page) {
  await page.getByRole('button', { name: 'Finalize character' }).click();
  await expect(page.locator('.sheet-page')).toBeVisible();
  await expectSaneLayout(page);
}

let server: TestServer;

test.beforeEach(async () => {
  server = new TestServer();
  await server.start();
});

test.afterEach(async () => {
  await server.stop();
});

test('the second campaign: choose 5.5e, walk Brannock through every card, a hand-checked sheet', async ({
  page,
}) => {
  const dnd = await gameNamed(server, /5\.5e/);
  const shipped = await campaignView(server);

  // A fresh directory asks; he picks 5.5e.
  await page.goto(server.url);
  await expect(page.getByText('Which game does this campaign play?')).toBeVisible();
  await page.getByRole('radio', { name: dnd.name }).check();
  await page.getByRole('button', { name: 'Start campaign' }).click();

  // The roster says so, carries the SRD attribution, offers no quick build
  // (suggested builds are a PF2e thing), and the server agrees.
  await expect(page.getByTestId('campaign-label')).toContainText(dnd.name);
  await expect(page.getByText('No characters yet')).toBeVisible();
  await expect(page.getByRole('button', { name: /Quick build/ })).toHaveCount(0);
  await expect(page.locator('.license-notice p')).toHaveCount(shipped.license_lines.length);
  await expect(
    page.getByText(/This work includes material from the System Reference Document 5\.2\.1/),
  ).toBeVisible();
  await expectSaneLayout(page);
  expect((await campaignView(server)).system).toBe(dnd.id);

  // The 5.5e sequence, as its own steps.
  await buildBrannock(page, server);
  await expect(page.locator('.wizard-steps .step-link')).toHaveText([
    /1\. Class/,
    /2\. Origin/,
    /3\. Ability Scores/,
    /4\. Class Choices/,
    /5\. Equipment/,
    /6\. Details/,
  ]);
  await finalizeCreation(page);

  // Hand calculation (SRD 5.2.1), matching the crate's own Brannock test:
  // scores = array + Soldier's +2 Str / +1 Con; HP 10 + Con 2; AC chain
  // mail 16 + Defense 1; initiative Dex +1 + proficiency (Alert); saves
  // proficient in Str and Con; skills from Soldier, Human, and Fighter;
  // package A's weapons at +5; 148 lb carried; 4 + 14 GP.
  const sheet = page.locator('.sheet-page');
  await expect(sheet.locator('.sheet-summary').first()).toHaveText('Human Fighter 1');
  const entry = (section: string, label: string) => sectionEntry(sheet, section, label);
  await expect(entry('Ability Scores', 'Strength')).toHaveText('17 (+3)');
  await expect(entry('Ability Scores', 'Dexterity')).toHaveText('13 (+1)');
  await expect(entry('Ability Scores', 'Constitution')).toHaveText('15 (+2)');
  await expect(entry('Ability Scores', 'Intelligence')).toHaveText('8 (-1)');
  await expect(entry('Ability Scores', 'Wisdom')).toHaveText('12 (+1)');
  await expect(entry('Ability Scores', 'Charisma')).toHaveText('10 (+0)');
  await expect(entry('Combat', 'Hit Points')).toHaveText('12');
  await expect(entry('Combat', 'Armor Class')).toHaveText('17');
  await expect(entry('Combat', 'Initiative')).toHaveText('+3');
  await expect(entry('Combat', 'Speed')).toHaveText('30 ft.');
  await expect(entry('Combat', 'Proficiency Bonus')).toHaveText('+2');
  await expect(entry('Combat', 'Hit Dice')).toHaveText('1d10');
  await expect(entry('Combat', 'Passive Perception')).toHaveText('13');
  await expect(entry('Saving Throws', 'Strength')).toHaveText('+5');
  await expect(entry('Saving Throws', 'Constitution')).toHaveText('+4');
  await expect(entry('Saving Throws', 'Dexterity')).toHaveText('+1');
  await expect(entry('Saving Throws', 'Intelligence')).toHaveText('-1');
  await expect(entry('Skills', 'Athletics')).toHaveText('+5');
  await expect(entry('Skills', 'Intimidation')).toHaveText('+2');
  await expect(entry('Skills', 'Perception')).toHaveText('+3');
  await expect(entry('Skills', 'Acrobatics')).toHaveText('+3');
  await expect(entry('Skills', 'Insight')).toHaveText('+3');
  await expect(entry('Skills', 'Stealth')).toHaveText('+1');
  await expect(entry('Attacks', 'Greatsword')).toHaveText('+5 · 2d6+3 Slashing');
  await expect(entry('Attacks', 'Flail')).toHaveText('+5 · 1d8+3 Bludgeoning');
  await expect(entry('Attacks', 'Javelin')).toHaveText('+5 · 1d6+3 Piercing');
  await expect(entry('Attacks', 'Spear')).toHaveText('+5 · 1d6+3 Piercing (1d8+3 two-handed)');
  await expect(entry('Attacks', 'Shortbow')).toHaveText('+3 · 1d6+1 Piercing');
  await expect(entry('Features', 'Fighting Style')).toHaveText('Defense');
  await expect(entry('Features', 'Weapon Mastery')).toContainText('Greatsword (Graze)');
  await expect(entry('Features', 'Tool Proficiency')).toHaveText('Gaming Set');
  await expect(entry('Equipment', 'Chain Mail')).toHaveText('55 lb.');
  await expect(entry('Equipment', 'Total Weight')).toHaveText('148 lb.');
  await expect(entry('Equipment', 'Coin')).toHaveText('18 GP');
  // The AC breakdown names both the armor and the style.
  const ac = sectionDetail(sheet, 'Combat', 'Armor Class');
  await ac.getByRole('button', { name: 'breakdown for Armor Class' }).click();
  await expect(ac.locator('.sheet-detail')).toContainText('Chain Mail');
  await expect(ac.locator('.sheet-detail')).toContainText('Defense');
  await expectSaneLayout(page);

  // Finalized on the roster, under the game's label.
  await page.getByRole('button', { name: '← Roster' }).click();
  await expect(page.locator('.roster-entry', { hasText: 'Brannock' })).toContainText('View sheet');
  await expect(page.getByTestId('campaign-label')).toContainText(dnd.name);
});

test('the buy: the point-buy meter drains, an overspend is against the rules, the gold alternative', async ({
  page,
}) => {
  const dnd = await gameNamed(server, /5\.5e/);
  await declareGame(server, dnd.id);
  await createCharacter(page, server, 'Pell');
  const side = page.locator('.wizard-side');

  await gotoStep(page, 'Class');
  await confirmOption(page, 'dnd5e.class', 'Fighter');
  await gotoStep(page, 'Origin');
  await confirmOption(page, 'dnd5e.background', 'Criminal');
  await confirmOption(
    page,
    'dnd5e.background.increase',
    'Dexterity +1, Constitution +1, Intelligence +1',
  );
  await confirmOption(page, 'dnd5e.species', 'Halfling');

  await gotoStep(page, 'Ability Scores');
  await confirmOption(page, 'dnd5e.scores.method', 'Point Buy');
  const card = slot(page, 'dnd5e.scores.assign');
  const meter = card.getByTestId('meter-Points');
  await expect(meter).toHaveText('Points 27 of 27');

  // 15, 15, 15, 8, 8, 8 costs exactly 27 — the meter drains to zero.
  await assignScores(page, {
    Strength: 15,
    Dexterity: 15,
    Constitution: 15,
    Intelligence: 8,
    Wisdom: 8,
    Charisma: 8,
  });
  await expect(meter).toHaveText('Points 0 of 27');
  const checklist = page.getByTestId('checklist');
  await expect(checklist.getByText('Against the rules')).toHaveCount(0);

  // One more point is one too many: the meter shows the true overshoot
  // and the checklist names the rule, live, before anything is confirmed.
  await assignScores(page, { Intelligence: 9 });
  await expect(meter).toHaveText('Points -1 of 27 — over the limit');
  await expect(meter).toHaveClass(/meter-exceeded/);
  await expect(checklist.getByText('Against the rules')).toBeVisible();
  const illegal = checklist.locator('.checklist-item.illegal');
  await expect(illegal).toHaveCount(1);
  await expect(illegal).toContainText("You've spent 28 points but the budget is 27");
  await expect(illegal.locator('.checklist-meta')).toContainText('Point Cost');
  await expectSaneLayout(page);

  // A legal buy (13, 15, 14, 8, 12, 10 = 27); the Criminal's +1s stack on
  // top, and the sidebar shows the result as he confirms.
  await confirmScores(page, {
    Strength: 13,
    Dexterity: 15,
    Constitution: 14,
    Intelligence: 8,
    Wisdom: 12,
    Charisma: 10,
  });
  await expect(checklist.getByText('Against the rules')).toHaveCount(0);
  await expect(sectionEntry(side, 'Ability Scores', 'Dexterity')).toHaveText('16 (+3)');
  await expect(sectionEntry(side, 'Ability Scores', 'Constitution')).toHaveText('15 (+2)');
  await expect(sectionEntry(side, 'Ability Scores', 'Intelligence')).toHaveText('9 (-1)');

  await gotoStep(page, 'Class Choices');
  await confirmMultiUntilFull(page, 'dnd5e.class.skills', ['Athletics', 'Perception']);
  await confirmOption(page, 'dnd5e.class.style', 'Archery');
  await confirmMultiUntilFull(page, 'dnd5e.class.masteries', ['Longbow', 'Rapier', 'Dagger']);

  // The gold alternative on both cards.
  await gotoStep(page, 'Equipment');
  await confirmOption(page, 'dnd5e.background.equipment', '50 GP instead');
  await confirmOption(page, 'dnd5e.equipment.package', 'Option C');
  await expect(page.getByTestId('checklist').getByText('Everything checks out')).toBeVisible();
  await finalizeCreation(page);

  // Coin 155 + 50; unarmored AC 10 + Dex 3; nothing to attack with; nothing
  // carried; HP 10 + Con 2; a Small halfling.
  const sheet = page.locator('.sheet-page');
  const entry = (section: string, label: string) => sectionEntry(sheet, section, label);
  await expect(sheet.locator('.sheet-summary').first()).toHaveText('Halfling Fighter 1');
  await expect(sheet.locator('.sheet-summary').nth(1)).toHaveText(/^Small/);
  await expect(entry('Equipment', 'Coin')).toHaveText('205 GP');
  await expect(entry('Equipment', 'Total Weight')).toHaveText('0 lb.');
  await expect(entry('Combat', 'Armor Class')).toHaveText('13');
  const ac = sectionDetail(sheet, 'Combat', 'Armor Class');
  await ac.getByRole('button', { name: 'breakdown for Armor Class' }).click();
  await expect(ac.locator('.sheet-detail')).toContainText('unarmored');
  await expect(entry('Combat', 'Hit Points')).toHaveText('12');
  await expect(entry('Ability Scores', 'Dexterity')).toHaveText('16 (+3)');
  await expect(entry('Ability Scores', 'Intelligence')).toHaveText('9 (-1)');
  const attacks = sheet.locator('.sheet-section', {
    has: page.getByRole('heading', { name: 'Attacks' }),
  });
  await expect(attacks).toBeVisible();
  await expect(attacks.locator('.sheet-entry')).toHaveCount(0);
  await expectSaneLayout(page);
});

test("level 2's empty level and the level-3 subclass: abandon, resume mid-level, the cap", async ({
  page,
}) => {
  const dnd = await gameNamed(server, /5\.5e/);
  await declareGame(server, dnd.id);
  await buildBrannock(page, server);
  await finalizeCreation(page);
  const sheet = page.locator('.sheet-page');

  // Level 2: the gains panel carries the fixed features and the HP by the
  // fixed die value; no choice card; finalize is open at once.
  await page.getByRole('button', { name: 'Level up to 2' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await expectSaneLayout(page);
  await expect(page.getByRole('heading', { name: /At level 2 you gain/ })).toBeVisible();
  const gains = page.locator('.level-gains');
  await expect(gains).toContainText('Action Surge');
  await expect(gains).toContainText('Tactical Mind');
  await expect(gains).toContainText('Hit Points');
  await expect(page.locator('.wizard-main [data-slot]')).toHaveCount(0);
  await expect(page.locator('.wizard-steps .step-link')).toHaveText([/Level 2/]);
  await expect(page.getByTestId('checklist').getByText('Everything checks out')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Finalize level 2' })).toBeEnabled();
  await page.getByRole('button', { name: 'Finalize level 2' }).click();
  await expect(sheet).toBeVisible();
  await expect(sheet.locator('.sheet-summary').first()).toHaveText('Human Fighter 2');
  await expect(sectionEntry(sheet, 'Combat', 'Hit Points')).toHaveText('20');
  await expect(sectionEntry(sheet, 'Features', 'Action Surge')).toHaveText('Fighter 2');
  await expectSaneLayout(page);

  // Level 3: one card, the Fighter Subclass, with the Champion as its only
  // option; finalize waits on it.
  const subclass = slot(page, 'dnd5e.level.3.subclass');
  await page.getByRole('button', { name: 'Level up to 3' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await expectSaneLayout(page);
  await expect(page.locator('.wizard-main [data-slot]')).toHaveCount(1);
  await expect(subclass).toBeVisible();
  await expect(subclass.getByRole('radio')).toHaveCount(1);
  await expect(subclass.locator('label:has-text("Champion") input')).toBeVisible();
  const checklist = page.getByTestId('checklist');
  await expect(checklist.getByText('Choose a subclass')).toBeVisible();
  await expect(checklist.locator('.checklist-meta')).toContainText('Fighter Subclass');
  await expect(page.getByRole('button', { name: 'Finalize level 3' })).toBeDisabled();
  await confirmOption(page, 'dnd5e.level.3.subclass', 'Champion');

  // Abandon once: the confirm lists the pick; the sheet is its level-2 self.
  await page.getByRole('button', { name: 'Abandon level 3' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Abandon level 3?');
  await expect(dialog).toContainText('Advance to level 3');
  await expect(dialog).toContainText('Subclass: Champion');
  await expectSaneLayout(page);
  await page.getByRole('button', { name: 'Discard and go back' }).click();
  await expect(sheet.locator('.sheet-summary').first()).toHaveText('Human Fighter 2');
  await expect(page.getByRole('button', { name: 'Level up to 3' })).toBeVisible();

  // Level again, pick, and resume mid-level: a reload lands on the same
  // step with the pick intact...
  await page.getByRole('button', { name: 'Level up to 3' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await confirmOption(page, 'dnd5e.level.3.subclass', 'Champion');
  await page.reload();
  await expect(page.locator('.wizard')).toBeVisible();
  await expect(page.locator('.wizard-steps .step-link')).toHaveText([/Level 3/]);
  await expect(subclass.locator('.slot-confirmed-value')).toHaveText('Champion');

  // ...and so does a kill -9 with a restart over the same directory: the
  // roster offers the resume with the old level showing.
  server.killNine();
  await server.start(server.port);
  await page.goto(`${server.url}/#/`);
  const rosterEntry = page.locator('.roster-entry', { hasText: 'Brannock' });
  await expect(rosterEntry).toContainText('Leveling up — resume');
  await expect(rosterEntry).toContainText('Fighter 2');
  await rosterEntry.locator('.roster-open').click();
  await expect(page.locator('.wizard')).toBeVisible();
  await expect(subclass.locator('.slot-confirmed-value')).toHaveText('Champion');
  await expectSaneLayout(page);

  // The deltas list the Champion's features; finalize; the cap note.
  const deltas = page.locator('.level-deltas');
  await expect(deltas).toContainText('Improved Critical');
  await expect(deltas).toContainText('Remarkable Athlete');
  await page.getByRole('button', { name: 'Finalize level 3' }).click();
  await expect(sheet).toBeVisible();
  await expect(sheet.locator('.sheet-summary').first()).toHaveText('Human Fighter 3 (Champion)');
  await expect(sectionEntry(sheet, 'Combat', 'Hit Points')).toHaveText('28');
  await expect(sectionEntry(sheet, 'Combat', 'Hit Dice')).toHaveText('3d10');
  await expect(sectionEntry(sheet, 'Combat', 'Proficiency Bonus')).toHaveText('+2');
  await expect(sectionEntry(sheet, 'Features', 'Improved Critical')).toHaveText('Champion 3');
  await expect(sectionEntry(sheet, 'Features', 'Remarkable Athlete')).toBeVisible();
  await expect(page.getByRole('button', { name: /Level up to/ })).toHaveCount(0);
  await expect(page.locator('.level-cap-note')).toContainText('Higher levels are coming');
  await expectSaneLayout(page);
});

test('jumping ahead: equipment before the fighting style works, the checklist lists the gaps', async ({
  page,
}) => {
  const dnd = await gameNamed(server, /5\.5e/);
  await declareGame(server, dnd.id);
  await createCharacter(page, server, 'Eager');
  const side = page.locator('.wizard-side');

  await gotoStep(page, 'Class');
  await confirmOption(page, 'dnd5e.class', 'Fighter');

  // Straight to Equipment: the class package is usable with what is
  // known, the background's card explains its lock.
  await gotoStep(page, 'Equipment');
  await expect(slot(page, 'dnd5e.background.equipment')).toContainText('choose a background first');
  await confirmOption(page, 'dnd5e.equipment.package', 'Package A');
  // Chain mail alone: AC 16, no style yet.
  await expect(sideSheetEntry(page, 'Armor Class')).toHaveText('16');

  // Finalize is blocked and every gap is listed, the style among them.
  await expect(page.getByRole('button', { name: 'Finalize character' })).toBeDisabled();
  const checklist = page.getByTestId('checklist');
  await expect(checklist.getByText('Choose a background')).toBeVisible();
  await expect(checklist.getByText('Choose a species')).toBeVisible();
  await expect(checklist.getByText('Choose how to generate your ability scores')).toBeVisible();
  await expect(checklist.getByText('Choose a Fighting Style feat')).toBeVisible();
  await expectSaneLayout(page);

  // The entry jumps back to its step; the pick re-derives the sidebar.
  await checklist.getByText('Choose a Fighting Style feat').click();
  await expect(page.locator('.wizard-main h2')).toHaveText('Class Choices');
  await confirmOption(page, 'dnd5e.class.style', 'Defense');
  await expect(checklist.getByText('Choose a Fighting Style feat')).toHaveCount(0);
  await expect(sideSheetEntry(page, 'Armor Class')).toHaveText('17');
  await expect(sectionEntry(side, 'Features', 'Fighting Style')).toHaveText('Defense');
  await expectSaneLayout(page);
});

test("the wrong drawer: a 5.5e character in a PF2e campaign's directory is refused in place, untouched", async ({
  page,
}) => {
  // This server is the 5.5e campaign; a second one is the other game's.
  const dnd = await gameNamed(server, /5\.5e/);
  const other = await gameNamed(server, /5\.5e/, true);
  await declareGame(server, dnd.id);
  const brannockId = await createViaApi(server, 'Brannock');
  const sourceFile = join(server.dataDir, 'characters', `${brannockId}.json`);
  const original = readFileSync(sourceFile);

  const pf2e = new TestServer();
  await pf2e.start();
  try {
    const declared = await declareGame(pf2e, other.id);
    await createViaApi(pf2e, 'Torvald');
    // Ben copies Brannock's file into the other campaign's drawer.
    const copied = join(pf2e.dataDir, 'characters', `${brannockId}.json`);
    copyFileSync(sourceFile, copied);

    await page.goto(pf2e.url);
    await expect(page.getByTestId('campaign-label')).toContainText(declared.system_name ?? '');
    // The problem names the file and both games; every other character
    // loads; the stranger is not an entry.
    const problems = page.locator('.roster-problems p');
    await expect(problems).toHaveCount(1);
    await expect(problems).toContainText(`${brannockId}.json`);
    // The server words the refusal with the games' ids today (see the
    // report); either the id or the render-ready name is the game named.
    const either = (game: { id: string; name: string }) =>
      `(${game.id}|${game.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`;
    await expect(problems).toContainText(new RegExp(`belongs to a ${either(dnd)} campaign`));
    await expect(problems).toContainText(new RegExp(`this campaign plays ${either(other)}`));
    await expect(problems).toContainText('the file is untouched');
    await expect(page.locator('.roster-entry')).toHaveCount(1);
    await expect(page.locator('.roster-entry', { hasText: 'Torvald' })).toBeVisible();
    await expect(page.locator('.roster-entry', { hasText: 'Brannock' })).toHaveCount(0);
    await expectSaneLayout(page);

    // Nothing rewrote or moved the file: same bytes, still in characters/,
    // nothing quarantined — and a restart over the directory says the same.
    expect(readFileSync(copied).equals(original)).toBe(true);
    expect(readdirSync(join(pf2e.dataDir, 'characters'))).toContain(`${brannockId}.json`);
    await pf2e.stop();
    await pf2e.start();
    await page.goto(pf2e.url);
    await expect(page.locator('.roster-problems p')).toHaveCount(1);
    await expect(page.locator('.roster-entry', { hasText: 'Torvald' })).toBeVisible();
    expect(readFileSync(copied).equals(original)).toBe(true);
    expect(
      readdirSync(join(pf2e.dataDir, 'characters')).filter((f) => f.endsWith('.json')),
    ).toHaveLength(2);
  } finally {
    await pf2e.stop();
  }

  // Back in its own drawer, Brannock is a plain roster entry, unchanged.
  await page.goto(server.url);
  await expect(page.locator('.roster-entry', { hasText: 'Brannock' })).toBeVisible();
  await expect(page.locator('.roster-problems')).toHaveCount(0);
  expect(readFileSync(sourceFile).equals(original)).toBe(true);
});
