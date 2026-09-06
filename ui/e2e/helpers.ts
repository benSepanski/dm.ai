// Shared driving helpers for the walk scenarios (same idioms as
// stories.spec.ts: role/testid locators, engine-judged waits, no sleeps).
import { expect, type Page } from '@playwright/test';
import { expectSaneLayout } from './layout';
import type { TestServer } from './server';

/**
 * A fresh data directory is an undeclared campaign: character routes refuse
 * until the game is chosen. Walks that start from scratch declare the FIRST
 * game the server lists — never a hard-coded id — before the browser opens.
 * Returns the declared campaign view.
 */
export async function declareFirstGame(server: TestServer): Promise<{
  system: string;
  system_name: string;
  games: { id: string; name: string }[];
  license_lines: string[];
}> {
  const before = (await (await fetch(`${server.url}/api/campaign`)).json()) as {
    games: { id: string; name: string }[];
  };
  const first = before.games[0];
  if (first === undefined) {
    throw new Error('the server ships no games to declare');
  }
  const response = await fetch(`${server.url}/api/campaign`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ system: first.id }),
  });
  if (!response.ok) {
    throw new Error(`declaring ${first.id} failed: ${response.status} ${await response.text()}`);
  }
  return (await response.json()) as Awaited<ReturnType<typeof declareFirstGame>>;
}

export async function createCharacter(page: Page, server: TestServer, name: string) {
  await page.goto(server.url);
  await expectSaneLayout(page);
  await page.getByPlaceholder('Working name (optional)').fill(name);
  await page.getByRole('button', { name: 'Create character' }).click();
  await expect(page.locator('.wizard')).toBeVisible();
  await expectSaneLayout(page);
}

export function slot(page: Page, id: string) {
  return page.locator(`[data-slot="${id}"]`);
}

export async function gotoStep(page: Page, title: string) {
  await page.getByRole('button', { name: new RegExp(`\\d+\\. ${title}`) }).click();
  // The layout sweep rides every step visit: every walk checks every
  // screen it reaches, for free.
  await expectSaneLayout(page);
}

export async function confirmOption(page: Page, slotId: string, optionLabel: string) {
  const card = slot(page, slotId);
  await card.scrollIntoViewIfNeeded();
  await card
    .getByRole('radio')
    .and(card.locator(`label:has-text("${optionLabel}") input`))
    .check();
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
}

export async function confirmBoosts(page: Page, slotId: string, attrs: string[]) {
  const card = slot(page, slotId);
  await card.scrollIntoViewIfNeeded();
  for (const [index, attr] of attrs.entries()) {
    await card.locator('select').nth(index).selectOption({ label: attr });
  }
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
}

export async function confirmText(page: Page, slotId: string, value: string) {
  const card = slot(page, slotId);
  await card.scrollIntoViewIfNeeded();
  await card.locator('input[type="text"]').fill(value);
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toHaveText(value);
}

/**
 * Check candidates one at a time until the slot's counter reports a full
 * selection, then confirm. Dynamic counts (trained skills grow with Int,
 * language choices with bonuses) never brittle the walks this way.
 */
export async function confirmMultiUntilFull(page: Page, slotId: string, candidates: string[]) {
  const card = slot(page, slotId);
  await card.scrollIntoViewIfNeeded();
  const counter = card.getByTestId(`counter-${slotId}`);
  for (const label of candidates) {
    if ((await counter.textContent())?.includes('All choices made') === true) {
      break;
    }
    await card.locator(`label:has-text("${label}") input`).check();
  }
  await expect(counter).toHaveText(/All choices made/);
  await card.getByRole('button', { name: /confirm/i }).click();
  await expect(card.locator('.slot-confirmed-value')).toBeVisible();
}

/** The finalized sheet's value for a labeled entry. */
export function sheetEntry(page: Page, label: string) {
  return page.locator('.sheet-entry', { hasText: label }).locator('.sheet-value');
}

/** A compact sidebar sheet entry (dt text match within the wizard side). */
export function sideSheetEntry(page: Page, label: string) {
  return page
    .locator('.wizard-side .sheet-entry')
    .filter({ has: page.locator('dt', { hasText: new RegExp(`^${label}$`) }) })
    .locator('.sheet-value');
}
