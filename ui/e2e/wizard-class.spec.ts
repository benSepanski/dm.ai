// The chargen-wizard spec's user stories, walked against the real server
// binary and the built UI: the first wizard (Sylvenne end to end), illegal
// prep caught and fixed, the changed mind (school cascade), the crash at
// the class step, and the pencil edit on the finalized sheet.
import { expect, type Page, test } from '@playwright/test';
import {
  confirmBoosts,
  confirmOption,
  createCharacter,
  gotoStep,
  sheetEntry,
  slot,
} from './helpers';
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
    await card.locator(`.option-list li:has(.option-label:text-is("${label}")) input`).check();
  }
  await expect(counter).toHaveText(/All choices made/);
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
}

/** Add options to a List slot (the prep picker) by label, then confirm. */
async function confirmListAdds(page: Page, slotId: string, labels: string[]) {
  const card = slot(page, slotId);
  await card.scrollIntoViewIfNeeded();
  for (const label of labels) {
    // The Add button's accessible name starts with the option label.
    await addButton(card, label).click();
  }
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
}

function addButton(card: ReturnType<typeof slot>, label: string) {
  return card.getByRole('button', {
    name: new RegExp(`^${label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')} `),
  });
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
const SPELLBOOK_RANK1 = ['Command', 'Fear', 'Grease', 'Jump', 'Sleep'];

/** Sylvenne through the whole class step (spellbook + initial prep). */
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
  await confirmMultiExact(page, 'pf2e.class.spellbook.cantrips', SPELLBOOK_CANTRIPS);
  await confirmMultiExact(page, 'pf2e.class.spellbook.rank1', SPELLBOOK_RANK1);
  await confirmMultiExact(page, 'pf2e.class.spellbook.curriculum', [
    'Breathe Fire',
    'Force Barrage',
  ]);
  // The preparation picker: List slots for the book slots, Single for the
  // school preparations — which come straight from the curriculum
  // (Telekinetic Projectile and Mystic Armor are NOT in her book).
  await confirmListAdds(page, 'pf2e.prep.cantrips', [
    'Shield',
    'Ignition',
    'Electric Arc',
    'Detect Magic',
    'Light',
  ]);
  await confirmListAdds(page, 'pf2e.prep.rank1', ['Fear', 'Command']);
  await confirmOption(page, 'pf2e.prep.school-cantrip', 'Telekinetic Projectile');
  await confirmOption(page, 'pf2e.prep.school-rank1', 'Mystic Armor');
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
}

test('the first wizard: Sylvenne end to end, sheet hand-checkable', async ({ page }) => {
  await buildSylvenneThroughClass(page);
  await finishSylvenne(page);

  // The spellcasting block, against the hand calculation.
  await expect(sheetEntry(page, 'Spell attack')).toHaveText('+7');
  await expect(sheetEntry(page, 'Spell DC')).toHaveText('17');
  await expect(sheetEntry(page, 'Rank 1 slots')).toHaveText('3');
  await expect(sheetEntry(page, 'Cantrips').first()).toHaveText('6 prepared');
  await expect(sheetEntry(page, 'Focus pool')).toHaveText('1 Focus Point');
  // Book vs prepared, clearly distinguished: the prepared section carries
  // the school preparations from the curriculum.
  await expect(page.getByRole('heading', { name: 'Prepared Spells' })).toBeVisible();
  await expect(sheetEntry(page, 'School cantrip')).toHaveText('Telekinetic Projectile');
  await expect(sheetEntry(page, 'School slot (rank 1)')).toHaveText('Mystic Armor');
  // The pencil affordance exists; build choices offer no edit.
  await expect(page.getByRole('button', { name: 'Change prepared spells' })).toBeVisible();
});

test('illegal prep, caught: overfilling a rank is refused and fixable', async ({ page }) => {
  await buildSylvenneThroughClass(page);
  const card = slot(page, 'pf2e.prep.rank1');
  // Reopen the confirmed slot: change → the dialog previews only itself.
  await card.getByRole('button', { name: 'Change…' }).click();
  await page.getByRole('button', { name: /clear/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toHaveCount(0);
  // Overfill: three picks into two slots. The meter flags it live…
  for (const label of ['Fear', 'Command', 'Sleep']) {
    await addButton(card, label).click();
  }
  await expect(card.getByTestId('meter-Prepared')).toContainText('over the limit');
  // …and the server refuses the save, naming the rule.
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(page.locator('.notice')).toContainText('only 2 can be prepared');
  // Fix it: remove one, confirm, and the entry clears.
  await card.locator('.shopping-list li', { hasText: 'Sleep' }).getByRole('button', { name: 'remove' }).click();
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
});

test('the changed mind: swapping schools lists and clears exactly the curriculum-derived choices', async ({
  page,
}) => {
  await buildSylvenneThroughClass(page);
  const school = slot(page, 'pf2e.class.school');
  await school.getByRole('button', { name: 'Change…' }).click();
  // The confirmation lists everything curriculum-derived — and the
  // school-independent cantrip preparation is NOT on the list.
  const dialog = page.locator('.modal');
  await expect(dialog).toContainText('Spellbook: curriculum spells');
  await expect(dialog).toContainText('School cantrip');
  await expect(dialog).toContainText('School slot (rank 1)');
  await expect(dialog).toContainText('Prepared rank-1 spells');
  await expect(dialog).not.toContainText('Prepared cantrips');
  await page.getByRole('button', { name: /clear/i }).click();

  // The cleared slots reopen; the cantrip preparation survives.
  await expect(slot(page, 'pf2e.class.school').locator('.slot-confirmed-value')).toHaveCount(0);
  await expect(
    slot(page, 'pf2e.prep.cantrips').locator('.slot-confirmed-value'),
  ).toBeVisible();
  // Pick the other school: the sidebar sheet swaps to it, the cantrip
  // preparation still shows, and the curriculum-derived entries are empty.
  await confirmOption(page, 'pf2e.class.school', 'School of Protean Form');
  const side = page.locator('.wizard-side');
  await expect(side).toContainText('School of Protean Form');
  await expect(side).toContainText('Shield, Ignition, Electric Arc, Detect Magic, Light');
  await expect(side).toContainText('none chosen yet');
});

test('the crash: kill -9 at the class step resumes with the spellbook intact', async ({
  page,
}) => {
  await buildSylvenneThroughClass(page);
  server.killNine();
  await server.start(server.port);
  await page.goto(`${server.url}/#/c/${await characterId(page)}`);
  await page.reload();
  await expect(page.locator('.wizard')).toBeVisible();
  await gotoStep(page, 'Class');
  await expect(
    slot(page, 'pf2e.class.spellbook.cantrips').locator('.slot-confirmed-value'),
  ).toBeVisible();
  await expect(
    slot(page, 'pf2e.prep.school-rank1').locator('.slot-confirmed-value'),
  ).toHaveText('Mystic Armor');
});

async function characterId(page: Page): Promise<string> {
  const hash = await page.evaluate(() => window.location.hash);
  const match = /^#\/c\/([^/]+)/.exec(hash);
  if (match?.[1] === undefined) {
    throw new Error(`no character id in hash: ${hash}`);
  }
  return decodeURIComponent(match[1]);
}

test('the pencil edit: prepared spells change from the finalized sheet and survive a restart', async ({
  page,
}) => {
  await buildSylvenneThroughClass(page);
  await finishSylvenne(page);

  await page.getByRole('button', { name: 'Change prepared spells' }).click();
  const card = slot(page, 'pf2e.prep.cantrips');
  // The picker opens preloaded with the current preparation; swap one.
  await card.locator('.shopping-list li', { hasText: 'Ignition' }).getByRole('button', { name: 'remove' }).click();
  await addButton(card, 'Frostbite').click();
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(page.locator('.prep-editor .notice')).toHaveCount(0);
  await page.getByRole('button', { name: 'Done' }).click();

  // The displayed sheet reflects the swap (pick order preserved)…
  const swapped = 'Shield, Electric Arc, Detect Magic, Light, Frostbite';
  await expect(page.getByText(swapped)).toBeVisible();
  // …and it survives a full server restart (durably saved).
  server.killNine();
  await server.start(server.port);
  await page.reload();
  await expect(page.getByText(swapped)).toBeVisible();
});
