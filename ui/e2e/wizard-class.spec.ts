// The chargen-wizard spec's user stories, walked against the real server
// binary and the built UI: the first wizard (Sylvenne end to end), illegal
// picks caught at the card, the changed mind (school re-judge, nothing
// destroyed), and the crash at the class step. Every step visit runs the
// layout sweep via the shared helpers.
import { expect, type Page, test } from '@playwright/test';
import {
  confirmBoosts,
  confirmOption,
  createCharacter,
  gotoStep,
  sheetEntry,
  slot,
} from './helpers';
import { expectSaneLayout } from './layout';
import { TestServer } from './server';

let server: TestServer;

test.beforeEach(async () => {
  server = new TestServer();
  await server.start();
});

test.afterEach(async () => {
  await server.stop();
});

/** Check options by EXACT label until the counter is full, then confirm
 * (spell names substring-collide — "Light" is inside "lightning" — so the
 * shared has-text helper is too loose here). */
async function confirmMultiExact(page: Page, slotId: string, labels: string[]) {
  const card = slot(page, slotId);
  await card.scrollIntoViewIfNeeded();
  const counter = card.getByTestId(`counter-${slotId}`);
  for (const label of labels) {
    if ((await counter.textContent())?.includes('All choices made') === true) {
      break;
    }
    await checkExact(page, slotId, label);
  }
  await expect(counter).toHaveText(/All choices made/);
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
}

async function checkExact(page: Page, slotId: string, label: string) {
  await slot(page, slotId)
    .locator(`.option-list li:has(.option-label:text-is("${label}")) input`)
    .check();
}

async function uncheckExact(page: Page, slotId: string, label: string) {
  await slot(page, slotId)
    .locator(`.option-list li:has(.option-label:text-is("${label}")) input`)
    .uncheck();
}

const SPELLBOOK_CANTRIPS = [
  'Caustic Blast',
  'Detect Magic',
  'Electric Arc',
  'Figment',
  'Frostbite',
  'Gouging Claw',
  'Ignition',
  'Light',
  'Message',
  'Shield',
];
// Five free picks + the two Battle Magic curriculum additions.
const SPELLBOOK_RANK1 = [
  'Breathe Fire',
  'Force Barrage',
  'Command',
  'Fear',
  'Grease',
  'Jump',
  'Sleep',
];

/** Sylvenne through the whole class step (build decisions only). */
async function buildSylvenneThroughClass(page: Page) {
  await createCharacter(page, server, 'Sylvenne');
  await gotoStep(page, 'Ancestry');
  await confirmOption(page, 'pf2e.ancestry', 'Elf');
  await confirmOption(page, 'pf2e.ancestry.heritage', 'Arctic Elf');
  await confirmOption(page, 'pf2e.ancestry.feat', 'Unwavering Mien');
  await confirmBoosts(page, 'pf2e.boosts.ancestry-free', ['Wisdom']);
  await gotoStep(page, 'Background');
  await confirmOption(page, 'pf2e.background', 'Artisan');
  await confirmBoosts(page, 'pf2e.boosts.background-choice', ['Intelligence']);
  await confirmBoosts(page, 'pf2e.boosts.background-free', ['Charisma']);
  await gotoStep(page, 'Class');
  await confirmOption(page, 'pf2e.class', 'Wizard');
  await confirmBoosts(page, 'pf2e.class.key-attribute', ['Intelligence']);
  // A Wizard has no level-1 class feat: the Fighter's slot must not exist.
  await expect(slot(page, 'pf2e.class.feat')).toHaveCount(0);
  await confirmOption(page, 'pf2e.class.thesis', 'Spell Substitution');
  await confirmOption(page, 'pf2e.class.school', 'School of Battle Magic');
  // The rank-1 picker announces the curriculum requirement in place.
  await expect(
    slot(page, 'pf2e.class.spellbook.rank1').getByTestId('meter-Curriculum'),
  ).toBeVisible();
  await confirmMultiExact(page, 'pf2e.class.spellbook.cantrips', SPELLBOOK_CANTRIPS);
  await confirmMultiExact(page, 'pf2e.class.spellbook.rank1', SPELLBOOK_RANK1);
}

async function finishSylvenne(page: Page) {
  // Boosts first: the trained-skill and language counts grow with Int.
  await gotoStep(page, 'Attribute Boosts');
  await confirmBoosts(page, 'pf2e.boosts.free', [
    'Intelligence',
    'Dexterity',
    'Constitution',
    'Wisdom',
  ]);
  await gotoStep(page, 'Class');
  await confirmOption(page, 'pf2e.skills.class-choice', 'Arcana');
  await confirmMultiExact(page, 'pf2e.skills.trained', [
    'Society',
    'Occultism',
    'Nature',
    'Stealth',
    'Diplomacy',
    'Deception',
  ]);
  await gotoStep(page, 'Ancestry');
  await confirmMultiExact(page, 'pf2e.ancestry.languages', [
    'Draconic',
    'Empyrean',
    'Fey',
    'Gnomish',
  ]);
  await gotoStep(page, 'Equipment');
  {
    // Two kit rows share the "Wizard Kit" prefix; pick the bare kit.
    const card = slot(page, 'pf2e.equipment.kit');
    await card.getByRole('radio', { name: /^Wizard Kit 1 gp/ }).check();
    await card.getByRole('button', { name: /confirm/i }).click();
    await expect(card.locator('.slot-confirmed-value')).toBeVisible();
  }
  const finalize = page.getByRole('button', { name: 'Finalize character' });
  await expect(finalize).toBeEnabled();
  await finalize.click();
  await expect(page.locator('.sheet-page')).toBeVisible();
  await expectSaneLayout(page);
}

test('the first wizard: Sylvenne end to end, sheet hand-checkable', async ({ page }) => {
  await buildSylvenneThroughClass(page);
  await finishSylvenne(page);

  // The spellcasting block, against the hand calculation.
  await expect(sheetEntry(page, 'Spell attack')).toHaveText('+7');
  await expect(sheetEntry(page, 'Spell DC')).toHaveText('17');
  await expect(sheetEntry(page, 'Rank 1 slots')).toHaveText('3');
  await expect(sheetEntry(page, 'Cantrips').first()).toHaveText('6/day');
  await expect(sheetEntry(page, 'Focus pool')).toHaveText('1 Focus Point');
  // The one rank-1 book line carries the curriculum additions; preparation
  // is plainly a table matter, and no prepared section exists.
  await expect(sheetEntry(page, 'Spellbook (rank 1)')).toContainText('Breathe Fire');
  await expect(sheetEntry(page, 'Preparation')).toHaveText('at the table');
  await expect(page.getByText('Prepared Spells')).toHaveCount(0);
});

test('illegal picks are flagged at the card and clear in place', async ({ page }) => {
  await buildSylvenneThroughClass(page);
  const card = slot(page, 'pf2e.class.spellbook.rank1');
  // Reopen the confirmed picker and swap a curriculum spell out: the
  // curriculum meter goes short where the player is looking.
  await card.getByRole('button', { name: 'Change…' }).click();
  await page.getByRole('button', { name: /clear/i }).click();
  for (const label of [
    'Command',
    'Fear',
    'Grease',
    'Jump',
    'Sleep',
    'Illusory Disguise',
    'Breathe Fire',
  ]) {
    await checkExact(page, 'pf2e.class.spellbook.rank1', label);
  }
  await expect(card.getByTestId('meter-Curriculum')).toContainText('1 of 2');
  await card.getByRole('button', { name: /confirm/i }).click();
  // Saved (an illegal state is still durable — the engine judges, the UI
  // never blocks) — and the card says what is wrong right there.
  await expect(card.getByText(/at least 2 .*curriculum/)).toBeVisible();
  // Fix in place: swap back to a curriculum spell.
  await uncheckExact(page, 'pf2e.class.spellbook.rank1', 'Illusory Disguise');
  await checkExact(page, 'pf2e.class.spellbook.rank1', 'Force Barrage');
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
  await expect(card.getByText(/at least 2 .*curriculum/)).toHaveCount(0);
});

test('the changed mind: swapping schools destroys nothing and re-judges', async ({ page }) => {
  await buildSylvenneThroughClass(page);
  const school = slot(page, 'pf2e.class.school');
  await school.getByRole('button', { name: 'Change…' }).click();
  // The confirmation lists only the school itself — nothing else clears.
  const dialog = page.locator('.modal');
  await expect(dialog.locator('.clear-list li')).toHaveCount(1);
  await expect(dialog).toContainText('Arcane school');
  await page.getByRole('button', { name: /clear/i }).click();
  await confirmOption(page, 'pf2e.class.school', 'School of Protean Form');

  // The spellbook stands — now flagged illegal, so the picker reopens
  // preloaded with every pick intact (fix-in-place); the focus spell
  // follows the school.
  const rank1 = slot(page, 'pf2e.class.spellbook.rank1');
  await expect(
    rank1.locator('.option-list li:has(.option-label:text-is("Breathe Fire")) input'),
  ).toBeChecked();
  await expect(
    rank1.locator('.option-list li:has(.option-label:text-is("Command")) input'),
  ).toBeChecked();
  // (The focus spell's name lives in the entry detail, which the compact
  // sidebar omits — the engine golden pins Scramble Body.)
  await expect(page.locator('.wizard-side')).toContainText('School of Protean Form');
  await expect(page.locator('.wizard-side')).toContainText('must come from the');
});

test('the crash: kill -9 at the class step resumes with the spellbook intact', async ({
  page,
}) => {
  await buildSylvenneThroughClass(page);
  server.killNine();
  await server.start(server.port);
  await page.reload();
  await expect(page.locator('.wizard')).toBeVisible();
  await gotoStep(page, 'Class');
  await expect(
    slot(page, 'pf2e.class.spellbook.cantrips').locator('.slot-confirmed-value'),
  ).toBeVisible();
  await expect(
    slot(page, 'pf2e.class.spellbook.rank1').locator('.slot-confirmed-value'),
  ).toContainText('Breathe Fire');
});
