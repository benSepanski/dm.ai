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
// Four free picks + the two curriculum additions — plus a third
// curriculum spell as a free pick, so the build over-satisfies the
// minimum (the meter must read "2 of 2", never "3 of 2").
const SPELLBOOK_RANK1 = [
  'Breathe Fire',
  'Force Barrage',
  'Mystic Armor',
  'Command',
  'Fear',
  'Grease',
  'Jump',
];

/** Sylvenne to a confirmed school, rank-1 picker open. */
async function buildSylvenneToSchool(page: Page) {
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
}

/** Sylvenne through the whole class step (build decisions only). */
async function buildSylvenneThroughClass(page: Page) {
  await buildSylvenneToSchool(page);
  const rank1 = slot(page, 'pf2e.class.spellbook.rank1');
  // Curriculum spells stand out: a labeled group split plus a badge chip
  // on each curriculum row (the chip survives filtering, unlike order).
  await expect(
    rank1.locator('.option-group-heading', { hasText: 'School of Battle Magic curriculum' }),
  ).toBeVisible();
  await expect(
    rank1.locator('.option-group-heading', { hasText: 'Other arcane spells' }),
  ).toBeVisible();
  await expect(
    rank1.locator('li:has(.option-label:text-is("Breathe Fire")) .option-badge'),
  ).toHaveText('Curriculum');
  await confirmMultiExact(page, 'pf2e.class.spellbook.cantrips', SPELLBOOK_CANTRIPS);
  await confirmMultiExact(page, 'pf2e.class.spellbook.rank1', SPELLBOOK_RANK1);
  // Three curriculum picks over a minimum of two: a requirement meter
  // caps at its target instead of reading like an error.
  await expect(rank1.getByTestId('meter-Curriculum')).toContainText('2 of 2');
}

async function completeSylvenne(page: Page) {
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
  await expect(page.getByRole('button', { name: 'Finalize character' })).toBeEnabled();
}

async function finishSylvenne(page: Page) {
  await completeSylvenne(page);
  await page.getByRole('button', { name: 'Finalize character' }).click();
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
  await expect(card).toHaveClass(/status-illegal/);
  // Fix in place: swap back to a curriculum spell. The red frame lifts
  // with the live preview — while the fix is still unconfirmed — the
  // same way the meters and the message do.
  await uncheckExact(page, 'pf2e.class.spellbook.rank1', 'Illusory Disguise');
  await checkExact(page, 'pf2e.class.spellbook.rank1', 'Force Barrage');
  await expect(card).not.toHaveClass(/status-illegal/);
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

test('the meander: no-op edits never block finalize, real ones explain themselves', async ({
  page,
}) => {
  await buildSylvenneThroughClass(page);
  await completeSylvenne(page);
  const finalize = page.getByRole('button', { name: 'Finalize character' });

  // Typing into an optional field and thinking better of it is a no-op.
  await gotoStep(page, 'Details');
  const notes = slot(page, 'pf2e.details.description');
  await notes.locator('textarea, input[type=text]').first().fill('x');
  await expect(finalize).toBeDisabled();
  await notes.locator('textarea, input[type=text]').first().fill('');
  await expect(finalize).toBeEnabled();
  await expect(page.locator('.pending-chip')).toHaveCount(0);

  // A real unconfirmed edit blocks — and says so, with a jump link.
  await notes.locator('textarea, input[type=text]').first().fill('Brave and curious');
  await expect(finalize).toBeDisabled();
  const chip = page.locator('.pending-chip');
  await expect(chip).toContainText('Unconfirmed changes');
  await expect(chip).toContainText('Appearance & notes');
  // The sidebar must not claim "ready to finalize" while an edit hangs.
  await expect(page.getByTestId('checklist')).toContainText('confirm your unconfirmed changes');

  // Leaving warns instead of silently discarding.
  await page.getByRole('button', { name: '← Roster' }).click();
  const dialog = page.locator('.modal', { hasText: 'Unconfirmed changes' });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: 'Stay' }).click();

  // Confirming the edit unblocks finalize.
  await notes.getByRole('button', { name: /confirm/i }).click();
  await expect(page.locator('.pending-chip')).toHaveCount(0);
  await expect(finalize).toBeEnabled();
  await finalize.click();
  await expect(page.locator('.sheet-page')).toBeVisible();
});

test('the overshoot: over-filling a picker shows the true count as a violation', async ({
  page,
}) => {
  await buildSylvenneToSchool(page);
  const rank1 = slot(page, 'pf2e.class.spellbook.rank1');
  for (const label of SPELLBOOK_RANK1) {
    await checkExact(page, 'pf2e.class.spellbook.rank1', label);
  }
  await checkExact(page, 'pf2e.class.spellbook.rank1', 'Sleep');
  // Eight picks in a seven-slot book: the counter and the Chosen meter
  // both show the real number and flag it — capacity never clamps.
  await expect(rank1.getByTestId(`counter-pf2e.class.spellbook.rank1`)).toContainText(
    '1 too many',
  );
  await expect(rank1.getByTestId('meter-Chosen')).toContainText('8 of 7');
  await expect(rank1.getByTestId('meter-Chosen')).toContainText('over the limit');
  await uncheckExact(page, 'pf2e.class.spellbook.rank1', 'Sleep');
  await expect(rank1.getByTestId('meter-Chosen')).toContainText('7 of 7');
});

test('the details stay readable after commitment', async ({ page }) => {
  await buildSylvenneToSchool(page);
  const school = slot(page, 'pf2e.class.school');
  // The school is confirmed and closed — its details must still open in
  // place, without undoing the choice.
  await school.getByRole('button', { name: /details/i }).click();
  await expect(school.locator('.confirmed-details')).toContainText('School of Battle Magic');
  await expect(school.getByRole('button', { name: 'Change…' })).toBeVisible();
});

test('the owned skill: a background grant claims the skill and the free pick re-judges', async ({
  page,
}) => {
  await createCharacter(page, server, 'Grix');
  await gotoStep(page, 'Class');
  await confirmOption(page, 'pf2e.class', 'Fighter');
  await confirmBoosts(page, 'pf2e.class.key-attribute', ['Strength']);
  await confirmOption(page, 'pf2e.skills.class-choice', 'Acrobatics');
  await confirmMultiExact(page, 'pf2e.skills.trained', [
    'Thievery',
    'Stealth',
    'Deception',
  ]);
  // Street Urchin grants Thievery — the grant owns it now.
  await gotoStep(page, 'Background');
  await confirmOption(page, 'pf2e.background', 'Street Urchin');
  await gotoStep(page, 'Class');
  const trained = slot(page, 'pf2e.skills.trained');
  // No surprise "replacement" card: the free pick re-judges where it was
  // made, editable in place with the picks preloaded.
  await expect(page.locator('[data-slot="pf2e.skills.replacement-1"]')).toHaveCount(0);
  await expect(trained.getByText(/Thievery now comes from Background: Street Urchin/)).toBeVisible();
  await expect(
    trained.locator('.option-list li:has(.option-label:text-is("Thievery")) input'),
  ).toBeChecked();
  await uncheckExact(page, 'pf2e.skills.trained', 'Thievery');
  await checkExact(page, 'pf2e.skills.trained', 'Society');
  await trained.getByRole('button', { name: /confirm/i }).click();
  await expect(trained.getByText(/now comes from/)).toHaveCount(0);
});
