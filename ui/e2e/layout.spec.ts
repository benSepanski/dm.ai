// The layout stress spec (architecture: chargen-wizard): beyond the sweep
// that rides every story step, deliberately provoke the worst case — the
// wordiest shipped records with every detail expanded — at desktop and
// narrow (tablet) viewports.
import { expect, type Page, test } from '@playwright/test';
import { declareFirstGame, confirmBoosts, confirmOption, createCharacter, gotoStep, slot } from './helpers';
import { expectSaneLayout } from './layout';
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

async function openWizardClassStep(page: Page) {
  await createCharacter(page, server, 'Wordy');
  await gotoStep(page, 'Class');
  await confirmOption(page, 'pf2e.class', 'Wizard');
  await confirmBoosts(page, 'pf2e.class.key-attribute', ['Intelligence']);
  await confirmOption(page, 'pf2e.class.school', 'School of Battle Magic');
}

/** Expand every option-detail toggle currently on screen. */
async function expandAllDetails(page: Page) {
  const toggles = page.getByRole('button', { name: 'show details' });
  const count = await toggles.count();
  for (let i = 0; i < count; i += 1) {
    // Always click the first remaining "show details" — clicking mutates
    // the list as buttons flip to "hide details".
    await toggles.first().click();
  }
}

for (const [name, width, height] of [
  ['desktop', 1440, 900],
  ['tablet', 820, 1180],
] as const) {
  test(`the wordiest content holds up at ${name} width`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await openWizardClassStep(page);
    // The spell pickers hold the longest prose shipped; expand all of it.
    await slot(page, 'pf2e.class.spellbook.rank1').scrollIntoViewIfNeeded();
    await expandAllDetails(page);
    await expectSaneLayout(page);
    // The filter's empty state and long option lists too.
    const filter = page.getByTestId('option-filter').first();
    if ((await filter.count()) > 0) {
      await filter.fill('zzzz-no-match');
      await expectSaneLayout(page);
      await filter.fill('');
    }
    await expect(page.locator('.wizard')).toBeVisible();
  });
}
