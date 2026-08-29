// Spec walks 1–3 (chargen-content, "What Ben checks"): linear Leshy
// breadth, the backwards Gnome, and the Halfling→Orc cascade — driven
// against the real server binary and the built UI it embeds.
import { expect, test } from '@playwright/test';
import {
  confirmBoosts,
  confirmMultiUntilFull,
  confirmOption,
  confirmText,
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

test('walk 1 — linear Leshy breadth: typed Steppe Lore, languages, filtered gear, finalize', async ({
  page,
}) => {
  await createCharacter(page, server, 'Verdan');

  await gotoStep(page, 'Ancestry');
  await confirmOption(page, 'pf2e.ancestry', 'Leshy');
  await confirmOption(page, 'pf2e.ancestry.heritage', 'Leaf Leshy');
  await confirmOption(page, 'pf2e.ancestry.feat', 'Seedpod');
  await confirmBoosts(page, 'pf2e.boosts.ancestry-free', ['Intelligence']);

  await gotoStep(page, 'Background');
  // 39 backgrounds: past the threshold, so the filter box is offered.
  const backgroundCard = slot(page, 'pf2e.background');
  await expect(backgroundCard.getByTestId('option-filter')).toBeVisible();
  await backgroundCard.getByTestId('option-filter').fill('nomad');
  await confirmOption(page, 'pf2e.background', 'Nomad');
  // Nomad's Lore is typed by the player, not picked from a list.
  await confirmText(page, 'pf2e.background.lore', 'Steppe');
  await confirmBoosts(page, 'pf2e.boosts.background-choice', ['Constitution']);
  await confirmBoosts(page, 'pf2e.boosts.background-free', ['Strength']);

  await gotoStep(page, 'Class');
  await confirmOption(page, 'pf2e.class', 'Fighter');
  await confirmBoosts(page, 'pf2e.class.key-attribute', ['Strength']);
  await confirmOption(page, 'pf2e.class.feat', 'Sudden Charge');
  await confirmOption(page, 'pf2e.skills.class-choice', 'Athletics');

  await gotoStep(page, 'Attribute Boosts');
  await confirmBoosts(page, 'pf2e.boosts.free', [
    'Strength',
    'Dexterity',
    'Constitution',
    'Intelligence',
  ]);

  // Trained-skill count grew with the Int boost; the helper fills to the
  // engine's count rather than assuming one.
  await gotoStep(page, 'Class');
  await confirmMultiUntilFull(page, 'pf2e.skills.trained', [
    'Nature',
    'Stealth',
    'Medicine',
    'Acrobatics',
    'Thievery',
  ]);

  // The Int boost opened the language chooser back on the Ancestry step,
  // listing the leshy additional languages.
  await gotoStep(page, 'Ancestry');
  const langCard = slot(page, 'pf2e.ancestry.languages');
  await expect(langCard).toBeVisible();
  await confirmMultiUntilFull(page, 'pf2e.ancestry.languages', ['Elven', 'Draconic', 'Gnomish']);

  await gotoStep(page, 'Equipment');
  // The kit list is short — under the threshold, no filter box.
  await expect(slot(page, 'pf2e.equipment.kit').getByTestId('option-filter')).toHaveCount(0);
  await confirmOption(page, 'pf2e.equipment.kit', 'longsword and steel shield');

  // The shop: grouped by category, one filter spanning all groups.
  const shopCard = slot(page, 'pf2e.equipment.extra');
  await shopCard.scrollIntoViewIfNeeded();
  await expect(shopCard.locator('.option-group-heading')).toHaveText([
    'Weapons',
    'Armor',
    'Shields',
    'Adventuring gear',
  ]);
  await shopCard.getByTestId('option-filter').fill('rope');
  // Filtering to one gear item drops the emptied category headers.
  await expect(shopCard.locator('.option-group-heading')).toHaveText(['Adventuring gear']);
  await shopCard.getByRole('button', { name: /^Rope \(50 feet\)/ }).click();
  await expect(shopCard.locator('.shopping-list')).toContainText('Rope (50 feet)');
  await shopCard.getByRole('button', { name: /confirm/i }).click();
  await expect(shopCard.locator('.slot-confirmed-value')).toBeVisible();

  await page.getByRole('button', { name: 'Finalize character' }).click();
  await expect(page.locator('.sheet-page')).toBeVisible();

  // Hand-checkable values (Player Core): Leshy 8 HP + Con, Small, Speed 25,
  // low-light vision, the typed Lore, and the languages line.
  await expect(page.getByText('Leshy (Leaf Leshy) Fighter 1')).toBeVisible();
  await expect(page.getByText('Small · Speed 25 feet · low-light vision')).toBeVisible();
  await expect(sheetEntry(page, 'Hit Points')).toHaveText('21');
  await expect(sheetEntry(page, 'Armor Class')).toHaveText('17');
  await expect(sheetEntry(page, 'Fortitude')).toHaveText('+8');
  await expect(sheetEntry(page, 'Languages')).toHaveText('Common, Fey, Elven');
  await expect(
    page.locator('.sheet-entry', { has: page.locator('dt', { hasText: 'Steppe Lore' }) }).locator('.sheet-value'),
  ).toHaveText('trained');
  await expect(sheetEntry(page, 'Coins')).toHaveText('5 gp, 7 sp');
});

test('walk 2 — backwards Gnome: equipment first, checklist pulls the rest, Scholar sub-choice', async ({
  page,
}) => {
  await createCharacter(page, server, 'Backwards');

  // Start at the end: the shop works before anything else is chosen.
  await gotoStep(page, 'Equipment');
  await expect(slot(page, 'pf2e.equipment.kit')).toContainText('choose a class first');
  const shopCard = slot(page, 'pf2e.equipment.extra');
  await shopCard.getByTestId('option-filter').fill('rope');
  await shopCard.getByRole('button', { name: /^Rope \(50 feet\)/ }).click();
  await shopCard.getByRole('button', { name: /confirm/i }).click();
  await expect(shopCard.locator('.slot-confirmed-value')).toBeVisible();

  await gotoStep(page, 'Details');
  await expect(slot(page, 'pf2e.details.name').locator('.slot-confirmed-value')).toHaveText(
    'Backwards',
  );

  // Every gap is listed; finalize is blocked.
  await expect(page.getByRole('button', { name: 'Finalize character' })).toBeDisabled();
  const checklist = page.getByTestId('checklist');
  await expect(checklist.getByText('Choose an ancestry')).toBeVisible();
  await expect(checklist.getByText('Choose a background')).toBeVisible();
  await expect(checklist.getByText('Choose a class')).toBeVisible();

  // The checklist drives: each entry jumps to its step.
  await checklist.getByText('Choose a class').click();
  await expect(page.locator('.wizard-main h2')).toHaveText('Class');
  await confirmOption(page, 'pf2e.class', 'Fighter');
  await confirmBoosts(page, 'pf2e.class.key-attribute', ['Strength']);
  await confirmOption(page, 'pf2e.class.feat', 'Reactive Shield');
  await confirmOption(page, 'pf2e.skills.class-choice', 'Athletics');
  await confirmMultiUntilFull(page, 'pf2e.skills.trained', [
    'Survival',
    'Religion',
    'Crafting',
    'Society',
    'Thievery',
  ]);

  await checklist.getByText('Choose a background').click();
  await expect(page.locator('.wizard-main h2')).toHaveText('Background');
  await confirmOption(page, 'pf2e.background', 'Scholar');
  // Scholar's in-background skill pick — and Assurance follows it.
  await confirmOption(page, 'pf2e.background.skill', 'Nature');
  await expect(page.locator('.wizard-side')).toContainText('Assurance (Nature)');
  await confirmBoosts(page, 'pf2e.boosts.background-choice', ['Wisdom']);
  await confirmBoosts(page, 'pf2e.boosts.background-free', ['Strength']);

  await checklist.getByText('Choose an ancestry').click();
  await expect(page.locator('.wizard-main h2')).toHaveText('Ancestry');
  await confirmOption(page, 'pf2e.ancestry', 'Gnome');
  await confirmOption(page, 'pf2e.ancestry.heritage', 'Sensate Gnome');
  await confirmOption(page, 'pf2e.ancestry.feat', 'Animal Accomplice');
  await confirmBoosts(page, 'pf2e.boosts.ancestry-free', ['Dexterity']);

  // One gap left: the free boosts. Finalize stays blocked until it clears.
  await expect(page.getByRole('button', { name: 'Finalize character' })).toBeDisabled();
  await gotoStep(page, 'Attribute Boosts');
  await confirmBoosts(page, 'pf2e.boosts.free', [
    'Strength',
    'Dexterity',
    'Constitution',
    'Wisdom',
  ]);

  // Choosing a class made the kit slot required — the checklist says so
  // and jumps back to Equipment; stay true to the backwards route and buy
  // items individually.
  await checklist.getByText('Take the class kit').click();
  await expect(page.locator('.wizard-main h2')).toHaveText('Equipment');
  await confirmOption(page, 'pf2e.equipment.kit', 'No kit');

  // The moment the last entry clears, finalize unblocks.
  await expect(checklist.getByText('Everything checks out')).toBeVisible();
  await page.getByRole('button', { name: 'Finalize character' }).click();
  await expect(page.locator('.sheet-page')).toBeVisible();
  await expect(page.getByText(/Gnome \(Sensate Gnome\) Fighter 1/)).toBeVisible();
});

test('walk 3 — the cascade: Halfling to Orc lists exactly what clears, no residue', async ({
  page,
}) => {
  await createCharacter(page, server, 'Turncoat');

  await gotoStep(page, 'Ancestry');
  await confirmOption(page, 'pf2e.ancestry', 'Halfling');
  await confirmOption(page, 'pf2e.ancestry.heritage', 'Gutsy Halfling');
  await confirmOption(page, 'pf2e.ancestry.feat', 'Halfling Luck');
  await confirmBoosts(page, 'pf2e.boosts.ancestry-free', ['Strength']);
  await gotoStep(page, 'Attribute Boosts');
  await confirmBoosts(page, 'pf2e.boosts.free', [
    'Strength',
    'Dexterity',
    'Constitution',
    'Wisdom',
  ]);

  // The prompt lists exactly the ancestry-dependent choices — and nothing
  // else (the free boosts stay).
  await gotoStep(page, 'Ancestry');
  await slot(page, 'pf2e.ancestry').getByRole('button', { name: 'Change…' }).click();
  const modal = page.locator('.modal');
  await expect(modal).toContainText('Ancestry: Halfling');
  await expect(modal).toContainText('Heritage: Gutsy Halfling');
  await expect(modal).toContainText('Ancestry feat: Halfling Luck');
  await expect(modal).toContainText('Ancestry free boost: Strength');
  await expect(modal).not.toContainText('Free attribute boosts');
  await modal.getByRole('button', { name: 'Clear and change' }).click();

  // The checklist reopens the cleared slots.
  const checklist = page.getByTestId('checklist');
  await expect(checklist.getByText('Choose an ancestry')).toBeVisible();
  await expect(slot(page, 'pf2e.ancestry.heritage')).toContainText('choose an ancestry first');

  // Re-picking leaves no halfling residue.
  await confirmOption(page, 'pf2e.ancestry', 'Orc');
  const heritageCard = slot(page, 'pf2e.ancestry.heritage');
  await expect(heritageCard.getByText('Hold-Scarred Orc')).toBeVisible();
  await expect(heritageCard.getByText('Gutsy Halfling')).toHaveCount(0);
  await confirmOption(page, 'pf2e.ancestry.heritage', 'Hold-Scarred Orc');
  await confirmOption(page, 'pf2e.ancestry.feat', 'Orc Ferocity');
  await expect(page.locator('.wizard-side')).toContainText('Orc (Hold-Scarred Orc)');
  await expect(page.locator('.wizard-side')).not.toContainText('Halfling');
});
