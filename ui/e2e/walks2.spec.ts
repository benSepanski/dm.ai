// Spec walks 4–6: versatile heritage union, the Canny Acumen chooser
// chain (with a trained-gated feat greying), and the one-tap quick build.
import { expect, test } from '@playwright/test';
import {
  declareFirstGame,
  confirmOption,
  confirmText,
  createCharacter,
  gotoStep,
  sideSheetEntry,
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

test('walk 4 — versatile heritage: Aiuvarin beside the dwarf heritages, feat list becomes the union', async ({
  page,
}) => {
  await createCharacter(page, server, 'Halfblood');
  await gotoStep(page, 'Ancestry');
  await confirmOption(page, 'pf2e.ancestry', 'Dwarf');

  // Aiuvarin is offered alongside the dwarf heritages.
  const heritageCard = slot(page, 'pf2e.ancestry.heritage');
  await expect(heritageCard.locator('.option-label', { hasText: /^Rock Dwarf$/ })).toBeVisible();
  await expect(heritageCard.locator('.option-label', { hasText: /^Aiuvarin$/ })).toBeVisible();
  await confirmOption(page, 'pf2e.ancestry.heritage', 'Aiuvarin');

  // The ancestry-feat catalog is now the dwarf + Aiuvarin union — big
  // enough that the filter appears, and it finds both sides of the union.
  const featCard = slot(page, 'pf2e.ancestry.feat');
  const filter = featCard.getByTestId('option-filter');
  await expect(filter).toBeVisible();
  await expect(featCard.locator('.option-label', { hasText: /^Rock Runner$/ })).toBeVisible();
  await filter.fill('atavism');
  await expect(featCard.locator('.option-label', { hasText: /^Elf Atavism$/ })).toBeVisible();
  await expect(featCard.locator('.option-label', { hasText: /^Rock Runner$/ })).toHaveCount(0);

  // A cantrip-dependent option in the union stays visible, greyed, with
  // its reason — filtering does not hide the shelf.
  await filter.fill('otherworldly');
  await expect(featCard.locator('.option-label', { hasText: /^Otherworldly Magic$/ })).toBeVisible();
  await expect(featCard.locator('.option-unavailable')).toContainText(
    'no entries in this rules-data version',
  );

  await filter.fill('atavism');
  await confirmOption(page, 'pf2e.ancestry.feat', 'Elf Atavism');
});

test('walk 5 — the chooser chain: Versatile Human, Canny Acumen, expert save on the sheet', async ({
  page,
}) => {
  await createCharacter(page, server, 'Canny');
  await gotoStep(page, 'Ancestry');
  await confirmOption(page, 'pf2e.ancestry', 'Human');
  await confirmOption(page, 'pf2e.ancestry.heritage', 'Versatile Human');

  // A class first, so the save baseline is visible on the live sheet.
  await gotoStep(page, 'Class');
  await confirmOption(page, 'pf2e.class', 'Fighter');
  await expect(sideSheetEntry(page, 'Will')).toHaveText('+3');

  // Versatile Human opened a general-feat slot with the full catalog —
  // 67 entries, so the filter carries the browsing.
  await gotoStep(page, 'Ancestry');
  const featCard = slot(page, 'pf2e.feats.general.heritage');
  const filter = featCard.getByTestId('option-filter');
  await expect(filter).toBeVisible();

  // A skill feat whose trained-in prerequisite is not met greys and names
  // the rule.
  await filter.fill('battle medicine');
  await expect(featCard.locator('.option-label', { hasText: /^Battle Medicine$/ })).toBeVisible();
  await expect(featCard.locator('.option-unavailable')).toHaveText(
    'requires trained in Medicine',
  );
  await expect(featCard.getByRole('radio')).toBeDisabled();

  // Pick Canny Acumen; its save chooser opens as a follow-up slot.
  await filter.fill('canny');
  await confirmOption(page, 'pf2e.feats.general.heritage', 'Canny Acumen');
  const profCard = slot(page, 'pf2e.feats.proficiency-choice');
  await expect(profCard).toBeVisible();
  await expect(profCard.getByText('becomes expert · from Canny Acumen').first()).toBeVisible();
  await confirmOption(page, 'pf2e.feats.proficiency-choice', 'Will');

  // Expert proficiency lands on the sheet: Will +3 (trained) → +5 (expert).
  await expect(sideSheetEntry(page, 'Will')).toHaveText('+5');
});

test('walk 6 — quick build: badges everywhere, swap one, rename, finalize', async ({ page }) => {
  await page.goto(server.url);
  await page.getByRole('button', { name: 'Quick build a Fighter' }).click();
  await expect(page.locator('.wizard')).toBeVisible();

  // Every slot is filled and the checklist is empty — review state.
  const checklist = page.getByTestId('checklist');
  await expect(checklist.getByText('Everything checks out')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Finalize character' })).toBeEnabled();

  // The suggestions announce themselves, step by step.
  await gotoStep(page, 'Ancestry');
  await expect(page.locator('.badge-suggested').first()).toBeVisible();
  const ancestryBadges = await page.locator('.badge-suggested').count();
  expect(ancestryBadges).toBeGreaterThanOrEqual(3);

  // Swap one suggestion: the badge flips to a player decision.
  await gotoStep(page, 'Class');
  const featCard = slot(page, 'pf2e.class.feat');
  await expect(featCard.locator('.badge-suggested')).toBeVisible();
  await featCard.getByRole('button', { name: 'Change…' }).click();
  await page.locator('.modal').getByRole('button', { name: 'Clear and change' }).click();
  await confirmOption(page, 'pf2e.class.feat', 'Vicious Swing');
  await expect(featCard.locator('.badge-suggested')).toHaveCount(0);
  // The neighbours keep theirs.
  await expect(slot(page, 'pf2e.class').locator('.badge-suggested')).toBeVisible();

  // Rename, then finalize.
  await gotoStep(page, 'Details');
  const nameCard = slot(page, 'pf2e.details.name');
  await nameCard.getByRole('button', { name: 'Change…' }).click();
  await page.locator('.modal').getByRole('button', { name: 'Clear and change' }).click();
  await confirmText(page, 'pf2e.details.name', 'Bram the Bold');

  await page.getByRole('button', { name: 'Finalize character' }).click();
  await expect(page.locator('.sheet-page')).toBeVisible();
  await expect(page.locator('.sheet-header h2')).toHaveText('Bram the Bold');
});
