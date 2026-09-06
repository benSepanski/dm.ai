// The spec's user stories, walked against the real server binary and the
// built UI it embeds: first run, the mistake (caught and cleared), the
// crash (a real SIGKILL), jumping ahead, change-ancestry dependent
// clearing, and delete-to-trash.
import { readdirSync } from 'node:fs';
import { join } from 'node:path';
import { expect, type Page, test } from '@playwright/test';
import { declareFirstGame } from './helpers';
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

async function createCharacter(page: Page, name: string) {
  await page.goto(server.url);
  await page.getByPlaceholder('Working name (optional)').fill(name);
  await page.getByRole('button', { name: 'Create character' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
}

function slot(page: Page, id: string) {
  return page.locator(`[data-slot="${id}"]`);
}

async function confirmOption(page: Page, slotId: string, optionLabel: string) {
  const card = slot(page, slotId);
  await card.scrollIntoViewIfNeeded();
  await card.getByRole('radio').and(card.locator(`label:has-text("${optionLabel}") input`)).check();
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
}

async function confirmBoosts(page: Page, slotId: string, attrs: string[]) {
  const card = slot(page, slotId);
  await card.scrollIntoViewIfNeeded();
  for (const [index, attr] of attrs.entries()) {
    await card.locator('select').nth(index).selectOption({ label: attr });
  }
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
}

async function confirmChecks(page: Page, slotId: string, labels: string[]) {
  const card = slot(page, slotId);
  await card.scrollIntoViewIfNeeded();
  for (const label of labels) {
    await card.locator(`label:has-text("${label}") input`).check();
  }
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
}

async function gotoStep(page: Page, title: string) {
  await page.getByRole('button', { name: new RegExp(`\\d+\\. ${title}`) }).click();
}

/** Torvald end to end, shared by the first-run and crash stories. */
async function buildTorvaldThroughBackground(page: Page) {
  await createCharacter(page, 'Torvald');
  await gotoStep(page, 'Ancestry');
  await confirmOption(page, 'pf2e.ancestry', 'Dwarf');
  await confirmOption(page, 'pf2e.ancestry.heritage', 'Rock Dwarf');
  await confirmOption(page, 'pf2e.ancestry.feat', 'Rock Runner');
  await confirmBoosts(page, 'pf2e.boosts.ancestry-free', ['Strength']);
  await gotoStep(page, 'Background');
  await confirmOption(page, 'pf2e.background', 'Warrior');
  await confirmBoosts(page, 'pf2e.boosts.background-choice', ['Strength']);
  await confirmBoosts(page, 'pf2e.boosts.background-free', ['Constitution']);
}

test('first run: an empty roster through a finalized, hand-checkable sheet', async ({
  page,
}) => {
  await page.goto(server.url);
  await expect(page.getByText('No characters yet')).toBeVisible();
  await expect(page.getByText(/ORC License/).first()).toBeVisible();

  await buildTorvaldThroughBackground(page);

  await gotoStep(page, 'Class');
  await confirmOption(page, 'pf2e.class', 'Fighter');
  await confirmBoosts(page, 'pf2e.class.key-attribute', ['Strength']);
  await confirmOption(page, 'pf2e.class.feat', 'Sudden Charge');
  await confirmOption(page, 'pf2e.skills.class-choice', 'Athletics');
  await confirmChecks(page, 'pf2e.skills.trained', ['Survival', 'Religion', 'Crafting']);

  await gotoStep(page, 'Attribute Boosts');
  await confirmBoosts(page, 'pf2e.boosts.free', [
    'Strength',
    'Dexterity',
    'Constitution',
    'Wisdom',
  ]);

  await gotoStep(page, 'Equipment');
  await confirmOption(page, 'pf2e.equipment.kit', 'longsword and steel shield');

  await gotoStep(page, 'Details');
  const nameCard = slot(page, 'pf2e.details.name');
  await expect(nameCard.locator('.slot-confirmed-value')).toHaveText('Torvald');

  // The live sidebar already shows the derived numbers.
  const sidebar = page.locator('.wizard-side');
  await expect(sidebar.getByText('Dwarf (Rock Dwarf) Fighter 1')).toBeVisible();

  await page.getByRole('button', { name: 'Finalize character' }).click();
  await expect(page.locator('.sheet-page')).toBeVisible();

  // Hand calculation (Player Core): HP 23, AC 17, Fort +8, Ref +6, Will +5,
  // Perception +7, longsword +9 / 1d8 S+4, Bulk 5 Bulk 2 L, 6 gp 2 sp left.
  const entry = (label: string) =>
    page.locator('.sheet-entry', { hasText: label }).locator('.sheet-value');
  await expect(entry('Hit Points')).toHaveText('23');
  await expect(entry('Armor Class')).toHaveText('17');
  await expect(entry('Fortitude')).toHaveText('+8');
  await expect(entry('Reflex')).toHaveText('+6');
  await expect(entry('Will')).toHaveText('+5');
  await expect(entry('Perception')).toHaveText('+7');
  await expect(
    page
      .locator('.sheet-section', { has: page.getByRole('heading', { name: 'Attacks' }) })
      .locator('.sheet-entry', { hasText: 'Longsword' }),
  ).toContainText('+9 · 1d8 S+4');
  await expect(entry('Coins')).toHaveText('6 gp, 2 sp');
  await expect(
    page
      .locator('.sheet-entry', { has: page.locator('dt', { hasText: /^Bulk/ }) })
      .locator('.sheet-value'),
  ).toHaveText('5 Bulk, 2 L');

  // And it survives as finalized on the roster.
  await page.getByRole('button', { name: '← Roster' }).click();
  await expect(page.getByText('View sheet')).toBeVisible();
});

test('the mistake: two boosts on Strength are flagged, jumpable, and clear live', async ({
  page,
}) => {
  await createCharacter(page, 'Blunder');
  await gotoStep(page, 'Attribute Boosts');
  const card = slot(page, 'pf2e.boosts.free');
  await card.locator('select').nth(0).selectOption({ label: 'Strength' });
  await card.locator('select').nth(1).selectOption({ label: 'Strength' });

  // The checklist names the rule, live, before anything is confirmed.
  const checklist = page.getByTestId('checklist');
  await expect(checklist.getByText('Against the rules')).toBeVisible();
  await expect(
    checklist.getByText('Boosts gained at the same time must go to different attributes'),
  ).toBeVisible();

  // Jump ahead somewhere else, then click the entry: it returns to the step.
  await gotoStep(page, 'Concept');
  await checklist
    .getByText('Boosts gained at the same time must go to different attributes')
    .click();
  await expect(card).toBeVisible();

  // Moving the boost to Constitution clears the entry as he watches.
  await card.locator('select').nth(1).selectOption({ label: 'Constitution' });
  await expect(
    checklist.getByText('Boosts gained at the same time must go to different attributes'),
  ).toHaveCount(0);
});

test('the crash: kill -9 mid-wizard, restart, resume at the exact step', async ({ page }) => {
  await buildTorvaldThroughBackground(page);
  await gotoStep(page, 'Class');

  // Half-typed, never confirmed: the one acceptable loss.
  await gotoStep(page, 'Details');
  await slot(page, 'pf2e.details.description').locator('textarea').fill('half-typed notes…');
  await gotoStep(page, 'Class');
  // Give the fire-and-forget cursor write a beat to land; the kill then
  // hits between confirmed steps, exactly like the story.
  await page.waitForTimeout(500);

  server.killNine();
  await server.start();

  await page.goto(server.url);
  await expect(page.getByText(/Resume creating/)).toBeVisible();
  await expect(page.getByText(/step 4 of 7 — Class/)).toBeVisible();
  await page.getByText('Torvald').click();

  // Every confirmed choice is intact; resume landed on Class.
  await expect(page.locator('.wizard-main h2')).toHaveText('Class');
  await gotoStep(page, 'Ancestry');
  await expect(slot(page, 'pf2e.ancestry').locator('.slot-confirmed-value')).toHaveText('Dwarf');
  await expect(slot(page, 'pf2e.ancestry.heritage').locator('.slot-confirmed-value')).toHaveText(
    'Rock Dwarf',
  );
  await gotoStep(page, 'Background');
  await expect(slot(page, 'pf2e.background').locator('.slot-confirmed-value')).toHaveText(
    'Warrior',
  );
  // The half-typed description is gone — and only that.
  await gotoStep(page, 'Details');
  await expect(slot(page, 'pf2e.details.description').locator('textarea')).toHaveValue('');
});

test('jumping ahead: equipment before class works, finalize blocks with every gap listed', async ({
  page,
}) => {
  await createCharacter(page, 'Eager');
  await gotoStep(page, 'Equipment');
  // The step works with what's known: the kit explains its lock, the item
  // list is usable.
  await expect(slot(page, 'pf2e.equipment.kit')).toContainText('choose a class first');
  await expect(slot(page, 'pf2e.equipment.extra')).toBeVisible();

  // Finalize is blocked and the checklist lists the gaps.
  await expect(page.getByRole('button', { name: 'Finalize character' })).toBeDisabled();
  const checklist = page.getByTestId('checklist');
  await expect(checklist.getByText('Choose an ancestry')).toBeVisible();
  await expect(checklist.getByText('Choose a background')).toBeVisible();
  await expect(checklist.getByText('Choose a class')).toBeVisible();

  // "Nothing to do yet" is not "done": Equipment shows the hollow waiting
  // badge, not a green check, while its required kit slot is locked.
  await expect(page.locator('.step-link.status-waiting')).toContainText('6. Equipment');
});

test('a half-confirmed multi slot stays open and finishes in place', async ({ page }) => {
  await createCharacter(page, 'Halfway');
  await gotoStep(page, 'Class');
  await confirmOption(page, 'pf2e.class', 'Fighter');
  const card = slot(page, 'pf2e.skills.trained');
  await card.scrollIntoViewIfNeeded();

  // Confirm just one of the three required picks.
  await card.locator('label:has-text("Survival") input').check();
  await card.getByRole('button', { name: /confirm/i }).click();

  // The slot stays editable, keeps the pick, the meter says how short, and
  // the save acknowledges itself (a partial save must not look like a dead
  // click).
  await expect(card.locator('label:has-text("Survival") input')).toBeChecked();
  await expect(card.getByTestId('meter-Chosen')).toContainText('Chosen 1 of 3 — keep picking');
  await expect(card.locator('.slot-ack')).toContainText('Saved — 2 skill choice(s) left');

  // Finish in place: two more picks, one Confirm — no clearing dialog.
  await card.locator('label:has-text("Religion") input').check();
  await card.locator('label:has-text("Crafting") input').check();
  // The live preview must treat the tentative picks as REPLACING the
  // partial decision, not stacking on it — no phantom "already trained"
  // or over-count entries while editing.
  await expect(card.getByTestId('meter-Chosen')).toContainText('Chosen 3 of 3');
  await expect(page.getByTestId('checklist').getByText(/already trained/)).toHaveCount(0);
  await expect(
    page.getByTestId('checklist').getByText(/but only \d+ allowed/),
  ).toHaveCount(0);
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toHaveText(
    'Survival, Religion, Crafting',
  );
  await expect(card.getByTestId('meter-Chosen')).toContainText('Chosen 3 of 3');
});

test('the equipment budget meter is live and flips when overspent', async ({ page }) => {
  await createCharacter(page, 'Spendthrift');
  await gotoStep(page, 'Equipment');
  const card = slot(page, 'pf2e.equipment.extra');
  await card.scrollIntoViewIfNeeded();

  await expect(card.getByTestId('meter-Remaining')).toContainText('Remaining 15 gp of 15 gp');

  // Two breastplates (16 gp) cross the 15 gp line — the meter flips before
  // anything is confirmed.
  const addBreastplate = card.getByRole('button', { name: /^Breastplate 8 gp/ });
  await addBreastplate.click();
  await addBreastplate.click();
  await expect(card.getByTestId('meter-Remaining')).toContainText('over the limit');

  // Removing one brings it back under.
  await card.locator('.shopping-list').getByRole('button', { name: 'remove' }).first().click();
  await expect(card.getByTestId('meter-Remaining')).toContainText('Remaining 7 gp of 15 gp');
});

test('changing ancestry lists exactly what will be cleared, then reopens those slots', async ({
  page,
}) => {
  await createCharacter(page, 'Fickle');
  await gotoStep(page, 'Ancestry');
  await confirmOption(page, 'pf2e.ancestry', 'Dwarf');
  await confirmOption(page, 'pf2e.ancestry.heritage', 'Forge Dwarf');
  await confirmOption(page, 'pf2e.ancestry.feat', 'Dwarven Doughtiness');
  await confirmBoosts(page, 'pf2e.boosts.ancestry-free', ['Strength']);

  await slot(page, 'pf2e.ancestry').getByRole('button', { name: 'Change…' }).click();
  const modal = page.locator('.modal');
  await expect(modal).toContainText('Ancestry: Dwarf');
  await expect(modal).toContainText('Heritage: Forge Dwarf');
  await expect(modal).toContainText('Ancestry feat: Dwarven Doughtiness');
  await expect(modal).toContainText('Ancestry free boost: Strength');

  await modal.getByRole('button', { name: 'Clear and change' }).click();
  // The slots reopen: heritage locks again behind ancestry, the checklist
  // grows its entries back.
  await expect(slot(page, 'pf2e.ancestry.heritage')).toContainText('choose an ancestry first');
  // The heritage demand reappears only once an ancestry exists again; what
  // must be back immediately is the ancestry gap itself.
  const checklist = page.getByTestId('checklist');
  await expect(checklist.getByText('Choose an ancestry')).toBeVisible();
});

test('a stale tab conflicts instead of interleaving, and reloads itself', async ({
  page,
  context,
}) => {
  await createCharacter(page, 'TwoTabs');
  const url = page.url();
  const pageB = await context.newPage();
  await pageB.goto(url);
  await expect(pageB.locator('.wizard')).toBeVisible();

  // Tab A confirms an ancestry; tab B still holds the old draft version.
  await gotoStep(page, 'Ancestry');
  await confirmOption(page, 'pf2e.ancestry', 'Dwarf');

  // Tab B tries to confirm a different ancestry from its stale view.
  await gotoStep(pageB, 'Ancestry');
  const cardB = slot(pageB, 'pf2e.ancestry');
  await cardB.locator('label:has-text("Elf") input').check();
  await cardB.getByRole('button', { name: /confirm/i }).click();

  // No silent interleave: B is told, and shows the reloaded truth (Dwarf).
  await expect(pageB.locator('.notice')).toContainText('another tab');
  await expect(cardB.locator('.slot-confirmed-value')).toHaveText('Dwarf');
  await pageB.close();
});

test('a confirm while the server is down explains itself and retries cleanly', async ({
  page,
}) => {
  await createCharacter(page, 'Offline');
  await gotoStep(page, 'Ancestry');
  const card = slot(page, 'pf2e.ancestry');
  await card.locator('label:has-text("Dwarf") input').check();

  const port = server.port;
  server.killNine();

  await card.getByRole('button', { name: /confirm/i }).click();
  // The failure is explained AT THE CARD (feedback renders where the
  // player is looking), and the tentative pick survives.
  await expect(card.locator('.slot-error')).toContainText('did not save');
  await expect(card.locator('label:has-text("Dwarf") input')).toBeChecked();

  // Server comes back on the same port; the same button now succeeds.
  await server.start(port);
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toHaveText('Dwarf');
});

test('deleting a draft asks once, then the file sits in trash/', async ({ page }) => {
  await createCharacter(page, 'Doomed');
  await page.getByRole('button', { name: '← Roster' }).click();
  await page.getByRole('button', { name: /delete Doomed/ }).click();
  await expect(page.getByText('Move to trash?')).toBeVisible();
  await page.getByRole('button', { name: 'Delete', exact: true }).click();

  await expect(page.getByText('No characters yet')).toBeVisible();
  const trash = readdirSync(join(server.dataDir, 'trash'));
  expect(trash.length).toBe(1);
  expect(readdirSync(join(server.dataDir, 'characters')).filter((f) => f.endsWith('.json')))
    .toHaveLength(0);
});
