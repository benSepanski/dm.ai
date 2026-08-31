// roster-ergonomics walks: random mint (variety visible across mints, a
// typed name stands, provenance badges at review) and clone (dialog with
// the prefilled name, the clone opens independent of its source). Every
// screen visited rides the generic layout sweep via the shared helpers.
import { expect, test } from '@playwright/test';
import { expectSaneLayout } from './layout';
import { TestServer } from './server';

const server = new TestServer();

test.beforeAll(async () => {
  await server.start();
});
test.afterAll(async () => {
  await server.stop();
});

test('random mint: one tap lands a filled, badged review draft and mints vary', async ({
  page,
}) => {
  await page.goto(server.url);
  await expectSaneLayout(page);

  // First mint: any class, no name.
  await page.getByRole('button', { name: 'Random character' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await expectSaneLayout(page);
  // The draft is fully filled: no unresolved checklist entries, finalize
  // is offered, and the rolled decisions carry their provenance badge at
  // the cards the review step shows.
  await expect(page.locator('.badge-suggested').first()).toBeVisible();
  const summaryOne = await page.locator('.wizard').textContent();

  // Back to the roster; mint again — the two characters differ (variety
  // is the feature; ancestry+background+name together make a collision
  // vanishingly unlikely).
  await page.goto(`${server.url}/#/`);
  await page.getByRole('button', { name: 'Random character' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  const summaryTwo = await page.locator('.wizard').textContent();
  expect(summaryTwo).not.toEqual(summaryOne);

  // The roster shows two minted drafts.
  await page.goto(`${server.url}/#/`);
  await expect(page.locator('.roster-entry')).toHaveCount(2);
  await expectSaneLayout(page);
});

test('random mint: a typed name stands and a picked class is honored', async ({ page }) => {
  await page.goto(server.url);
  await page.getByPlaceholder('Working name (optional)').fill('Handpicked Hero');
  await page.getByLabel('random character class').selectOption({ label: 'Wizard' });
  await page.getByRole('button', { name: 'Random character' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await expect(page.locator('.wizard')).toContainText('Handpicked Hero');
  await expect(page.locator('.wizard')).toContainText('Wizard');
  await expectSaneLayout(page);
});

test('clone: the dialog prefills "<name> (copy)" and the clone is independent', async ({
  page,
}) => {
  await page.goto(server.url);
  // A stable source: a quick-build Fighter under a typed name (the
  // planner never overwrites it); a draft proves resume-at-step cloning.
  await page.getByPlaceholder('Working name (optional)').fill('Cloneworthy');
  await page.getByRole('button', { name: 'Quick build a Fighter' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await page.goto(`${server.url}/#/`);

  const sourceEntry = page.locator('.roster-entry', { hasText: 'Cloneworthy' }).first();
  await sourceEntry.getByRole('button', { name: 'clone Cloneworthy' }).click();
  const nameInput = page.getByLabel(/name for the clone of/i);
  await expect(nameInput).toHaveValue('Cloneworthy (copy)');
  await nameInput.fill('Cloned Adventurer');
  await expectSaneLayout(page);
  await page.getByRole('button', { name: 'Clone', exact: true }).click();

  // The clone opens as its own character, named at clone time, with the
  // clone badge on its name card.
  await expect(page.locator('.wizard')).toBeVisible();
  await expect(page.locator('.wizard')).toContainText('Cloned Adventurer');
  await expectSaneLayout(page);

  // Both source and clone sit on the roster, independently deletable.
  await page.goto(`${server.url}/#/`);
  await expect(page.locator('.roster-entry', { hasText: 'Cloned Adventurer' })).toHaveCount(1);
  await expect(page.locator('.roster-entry', { hasText: 'Cloneworthy' }).first()).toBeVisible();
});
