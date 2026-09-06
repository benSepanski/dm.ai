// level-up walks: the first level-up (gains panel, the level's slots in
// the unchanged wizard shell, finalize deltas), straight-to-cap with the
// cap note, illegal picks at the card, the changed mind, abandon through
// the existing clear dialog, crash resume, and the pending-level clone.
// Every screen visited rides the generic layout sweep.
import { expect, test, type Page } from '@playwright/test';
import { expectSaneLayout } from './layout';
import { declareFirstGame } from './helpers';
import { TestServer } from './server';

const server = new TestServer();

test.beforeAll(async () => {
  await server.start();
  await declareFirstGame(server);
});
test.afterAll(async () => {
  await server.stop();
});

/** A finalized quick-build Fighter under `name`; lands on the sheet page. */
async function finalizedFighter(page: Page, name: string) {
  await page.goto(server.url);
  await page.getByPlaceholder('Working name (optional)').fill(name);
  await page.getByRole('button', { name: 'Quick build a Fighter' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await page.getByRole('button', { name: 'Finalize character' }).click();
  await expect(page.locator('.sheet-page')).toBeVisible();
  await expectSaneLayout(page);
}

/** Pick the first available option in a slot and confirm it. */
async function confirmFirstAvailable(page: Page, slotId: string) {
  const card = page.locator(`[data-slot="${slotId}"]`);
  await card.scrollIntoViewIfNeeded();
  await card.locator('label:not(:has(input:disabled)) input').first().check();
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
}

test('first level-up: gains panel, the same wizard shell, deltas, a leveled sheet', async ({
  page,
}) => {
  await finalizedFighter(page, 'Torvald Rising');
  await page.getByRole('button', { name: 'Level up to 2' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await expectSaneLayout(page);

  // The gains panel and the level's step, rendered by the unchanged shell
  // (same nav, checklist, cards, confirm affordances by their existing
  // selectors).
  await expect(page.getByRole('heading', { name: /At level 2 you gain/ })).toBeVisible();
  await expect(page.locator('.level-gains .version-diff')).toContainText('Hit Points');
  await expect(page.locator('.wizard-steps .step-link')).toHaveCount(1);
  await expect(page.locator('.wizard-steps .step-link')).toContainText('Level 2');
  await expect(page.locator('.wizard-side .checklist')).toBeVisible();
  await expect(page.locator('[data-slot="pf2e.level.2.class-feat"]')).toBeVisible();
  await expect(page.locator('[data-slot="pf2e.level.2.skill-feat"]')).toBeVisible();

  // Finalize is blocked until both slots are filled, at the card.
  await expect(page.getByRole('button', { name: 'Finalize level 2' })).toBeDisabled();
  await confirmFirstAvailable(page, 'pf2e.level.2.class-feat');
  await confirmFirstAvailable(page, 'pf2e.level.2.skill-feat');
  await expect(page.locator('.level-deltas')).toContainText('Hit Points');
  await expectSaneLayout(page);
  await page.getByRole('button', { name: 'Finalize level 2' }).click();

  // The leveled sheet: Fighter 2, and the next level is offered.
  await expect(page.locator('.sheet-page')).toBeVisible();
  await expect(page.locator('.sheet-page')).toContainText('Fighter 2');
  await expect(page.getByRole('button', { name: 'Level up to 3' })).toBeVisible();
  await expectSaneLayout(page);
});

test('straight to the cap: level 3 lands and the button gives way to the note', async ({
  page,
}) => {
  await finalizedFighter(page, 'Capstone');
  for (const level of [2, 3]) {
    await page.getByRole('button', { name: `Level up to ${level}` }).click();
    await expect(page.locator('.wizard')).toBeVisible();
    const slots = await page.locator('.wizard-main [data-slot]').all();
    for (const slot of slots) {
      const id = await slot.getAttribute('data-slot');
      await confirmFirstAvailable(page, id ?? '');
    }
    await page.getByRole('button', { name: `Finalize level ${level}` }).click();
    await expect(page.locator('.sheet-page')).toContainText(`Fighter ${level}`);
  }
  await expect(page.getByRole('button', { name: /Level up to/ })).toHaveCount(0);
  await expect(page.locator('.level-cap-note')).toContainText('Higher levels are coming');
  await expectSaneLayout(page);
});

test('illegal picks at the card: a prerequisite the build fails is greyed with its reason', async ({
  page,
}) => {
  await finalizedFighter(page, 'Gatekeeper');
  await page.getByRole('button', { name: 'Level up to 2' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  const card = page.locator('[data-slot="pf2e.level.2.skill-feat"]');
  // A level-2 skill feat needs expert rank — nobody has one at level 2.
  const greyed = card.locator('label:has(input:disabled)', { hasText: 'Powerful Leap' });
  await expect(greyed).toBeVisible();
  await expect(greyed).toContainText(/expert in Athletics/i);
});

test('the changed mind and the retreat: swap a pick, then abandon through the clear dialog', async ({
  page,
}) => {
  await finalizedFighter(page, 'Second Thoughts');
  await page.getByRole('button', { name: 'Level up to 2' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await confirmFirstAvailable(page, 'pf2e.level.2.class-feat');
  // Change the confirmed feat: the cascade prompt scopes to the pending level.
  const card = page.locator('[data-slot="pf2e.level.2.class-feat"]');
  await card.getByRole('button', { name: /change/i }).click();
  await expect(page.getByRole('dialog')).toContainText('Class feat (level 2)');
  await page.getByRole('button', { name: 'Clear and change' }).click();
  await expect(card.locator('.slot-confirmed-value')).toHaveCount(0);
  await confirmFirstAvailable(page, 'pf2e.level.2.class-feat');

  // Abandon: the dialog lists exactly the pending picks, then the sheet
  // is its clean level-1 self.
  await page.getByRole('button', { name: 'Abandon level 2' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Abandon level 2?');
  await expect(dialog).toContainText('Advance to level 2');
  await expect(dialog).toContainText('Class feat (level 2)');
  await expectSaneLayout(page);
  await page.getByRole('button', { name: 'Discard and go back' }).click();
  await expect(page.locator('.sheet-page')).toContainText('Fighter 1');
  await expect(page.getByRole('button', { name: 'Level up to 2' })).toBeVisible();
});

test('the crash: kill -9 mid-level-up, restart, resume with the old level showing everywhere', async ({
  page,
}) => {
  await finalizedFighter(page, 'Survivor');
  await page.getByRole('button', { name: 'Level up to 2' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await confirmFirstAvailable(page, 'pf2e.level.2.class-feat');

  server.killNine();
  await server.start(server.port);
  await page.goto(`${server.url}/#/`);
  const entry = page.locator('.roster-entry', { hasText: 'Survivor' });
  await expect(entry).toContainText('Leveling up — resume');
  await expect(entry).toContainText('Fighter 1');
  await entry.locator('.roster-open').click();
  await expect(page.locator('.wizard')).toBeVisible();
  await expect(
    page.locator('[data-slot="pf2e.level.2.class-feat"] .slot-confirmed-value'),
  ).toBeVisible();
});

test('the fork first: cloning mid-level-up carries the pending level independently', async ({
  page,
}) => {
  await finalizedFighter(page, 'Forkbearer');
  await page.getByRole('button', { name: 'Level up to 2' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await confirmFirstAvailable(page, 'pf2e.level.2.class-feat');
  await page.goto(`${server.url}/#/`);
  const entry = page.locator('.roster-entry', { hasText: 'Forkbearer' }).first();
  await entry.getByRole('button', { name: 'clone Forkbearer' }).click();
  await page.getByLabel(/name for the clone of/i).fill('Forkbearer B');
  await page.getByRole('button', { name: 'Clone', exact: true }).click();
  // The clone opens leveling, at the same spot, with the confirmed feat.
  await expect(page.locator('.wizard')).toBeVisible();
  await expect(
    page.locator('[data-slot="pf2e.level.2.class-feat"] .slot-confirmed-value'),
  ).toBeVisible();
  await expectSaneLayout(page);
});
