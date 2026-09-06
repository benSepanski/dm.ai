// The campaign's game (spec chargen-dnd req 1, "two campaigns, one app"):
// a fresh directory asks once which game it plays and never again; the
// roster names the game and carries every shipped license paragraph; a
// directory that already holds characters opens straight to the roster —
// declared, or undeclared and read as its default game; a corrupt
// declaration is reported as the campaign's problem. No game is named by
// id or by name in this file: every label is read back from the server.
import { readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from '@playwright/test';
import { declareFirstGame } from './helpers';
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

async function campaignView(): Promise<{
  system?: string;
  system_name?: string;
  games: { id: string; name: string }[];
  license_lines: string[];
}> {
  return (await (await fetch(`${server.url}/api/campaign`)).json()) as Awaited<
    ReturnType<typeof campaignView>
  >;
}

/** A character created through the API (the campaign must be declared). */
async function createViaApi(name: string): Promise<string> {
  const response = await fetch(`${server.url}/api/characters`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  expect(response.ok).toBe(true);
  return ((await response.json()) as { id: string }).id;
}

test('a fresh directory asks which game it plays; the answer sticks across reloads', async ({
  page,
}) => {
  const shipped = await campaignView();
  expect(shipped.system).toBeUndefined();

  await page.goto(server.url);
  await expect(page.getByText('Which game does this campaign play?')).toBeVisible();
  // Every shipped game is offered, by its render-ready name; nothing else.
  const radios = page.getByRole('radio');
  await expect(radios).toHaveCount(shipped.games.length);
  for (const game of shipped.games) {
    await expect(page.getByRole('radio', { name: game.name })).toBeVisible();
  }
  // The roster's controls are not offered before the game is chosen.
  await expect(page.getByRole('button', { name: 'Create character' })).toHaveCount(0);
  await expectSaneLayout(page);

  // Choose the first listed game.
  const first = shipped.games[0];
  if (first === undefined) {
    throw new Error('no games shipped');
  }
  await page.getByRole('radio', { name: first.name }).check();
  await page.getByRole('button', { name: 'Start campaign' }).click();

  // The roster, labeled with that game, with every license paragraph in
  // order, and the usual controls.
  await expect(page.getByTestId('campaign-label')).toContainText(first.name);
  await expect(page.getByTestId('campaign-label')).not.toContainText('by default');
  await expect(page.getByRole('button', { name: 'Create character' })).toBeVisible();
  const paragraphs = page.locator('.license-notice p');
  await expect(paragraphs).toHaveCount(shipped.license_lines.length);
  for (const [i, line] of shipped.license_lines.entries()) {
    await expect(paragraphs.nth(i)).toHaveText(line);
  }
  await expectSaneLayout(page);

  // The server agrees, and the app never asks again.
  const declared = await campaignView();
  expect(declared.system).toBe(first.id);
  await page.reload();
  await expect(page.getByTestId('campaign-label')).toContainText(first.name);
  await expect(page.getByText('Which game does this campaign play?')).toHaveCount(0);

  // Nor after a server restart over the same directory.
  await server.stop();
  await server.start();
  await page.goto(server.url);
  await expect(page.getByTestId('campaign-label')).toContainText(first.name);
  await expect(page.getByText('Which game does this campaign play?')).toHaveCount(0);
});

test('a racing declaration is refused where the question was asked, and reload moves on', async ({
  page,
}) => {
  const shipped = await campaignView();
  const first = shipped.games[0];
  const last = shipped.games[shipped.games.length - 1];
  // Answering the same game twice is idempotent by design; the race that
  // refuses is two tabs answering differently, which needs two games.
  test.skip(
    first === undefined || last === undefined || first.id === last.id,
    'this build ships one game — no differing answer to race',
  );
  if (first === undefined || last === undefined) {
    return;
  }
  await page.goto(server.url);
  await expect(page.getByText('Which game does this campaign play?')).toBeVisible();
  // Another tab answers first — with the other game.
  const response = await fetch(`${server.url}/api/campaign`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ system: last.id }),
  });
  expect(response.ok).toBe(true);
  const other = (await response.json()) as { system_name: string };

  await page.getByRole('radio', { name: first.name }).check();
  await page.getByRole('button', { name: 'Start campaign' }).click();
  // The typed refusal shows inline; the question is still on screen.
  const refusal = page.locator('.choose-game-error');
  await expect(refusal).toBeVisible();
  await expect(refusal).not.toHaveText('');
  await expect(page.getByText('Which game does this campaign play?')).toBeVisible();
  await expectSaneLayout(page);

  await refusal.getByRole('button', { name: 'Reload' }).click();
  await expect(page.getByTestId('campaign-label')).toContainText(other.system_name);
});

test('a directory already holding a character opens straight to the roster', async ({
  page,
}) => {
  const declared = await declareFirstGame(server);
  await createViaApi('Seeded');
  await page.goto(server.url);
  await expect(page.getByText('Which game does this campaign play?')).toHaveCount(0);
  await expect(page.locator('.roster-entry', { hasText: 'Seeded' })).toBeVisible();
  await expect(page.getByTestId('campaign-label')).toContainText(declared.system_name);
  await expectSaneLayout(page);

  // Direct link to the character: the campaign is fetched first and the
  // wizard opens (its previews need the game the façade was handed).
  await page.locator('.roster-entry', { hasText: 'Seeded' }).locator('.roster-open').click();
  await expect(page.locator('.wizard')).toBeVisible();
  await page.reload();
  await expect(page.locator('.wizard')).toBeVisible();
  await expectSaneLayout(page);
});

test('a pre-declaration directory with characters is never asked and reads as its default game', async ({
  page,
}) => {
  await declareFirstGame(server);
  await createViaApi('Elder');
  await server.stop();
  // A directory from before campaigns named their game: characters, no
  // declaration.
  rmSync(join(server.dataDir, 'campaign.json'));
  await server.start();

  const view = await campaignView();
  expect(view.system).toBeDefined();
  await page.goto(server.url);
  await expect(page.getByText('Which game does this campaign play?')).toHaveCount(0);
  await expect(page.locator('.roster-entry', { hasText: 'Elder' })).toBeVisible();
  const label = page.getByTestId('campaign-label');
  await expect(label).toContainText(view.system_name ?? '');
  await expect(label).toContainText('by default');
  await expectSaneLayout(page);
  // The app wrote no declaration into it.
  expect(() => readFileSync(join(server.dataDir, 'campaign.json'))).toThrow();
});

test('a corrupt declaration is reported as the campaign problem; nothing else is offered', async ({
  page,
}) => {
  await declareFirstGame(server);
  await createViaApi('Stranded');
  await server.stop();
  writeFileSync(join(server.dataDir, 'campaign.json'), 'not json');
  await server.start();

  await page.goto(server.url);
  const problem = page.locator('.campaign-problem');
  await expect(problem).toBeVisible();
  await expect(problem).toContainText('campaign.json');
  await expect(page.getByText('Which game does this campaign play?')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Create character' })).toHaveCount(0);
  // The character file is reported (by file, since it never loaded), not
  // listed as a character.
  await expect(page.locator('.roster-problems p')).toHaveCount(1);
  await expect(page.locator('.roster-problems')).toContainText('campaign declaration');
  await expect(page.locator('.roster-entry')).toHaveCount(0);
  await expectSaneLayout(page);
});
