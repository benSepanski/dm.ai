// Playwright smoke playtest for the dm.ai UI. Drives the real app in a
// headless browser the same way an agent (or DM) would: create a world and
// session through the new-session form, send a DM chat message, and wait
// for the AI co-DM's reply to render. Exits non-zero on any failure.
//
// Prerequisites: the stack is up (scripts/playtest.sh start) and the
// `playwright` package is resolvable (run via `scripts/playtest.sh smoke`,
// which points NODE_PATH at the global npm root).
//
// Screenshots of every step land in .playtest/shots/.
const path = require("path");
const { chromium } = require("playwright");

const UI_URL = process.env.PLAYTEST_UI_URL ?? "http://localhost:5173";
const SHOTS = path.join(__dirname, "..", ".playtest", "shots");
const AI_REPLY_TIMEOUT_MS = 150_000; // claude CLI calls can take a while

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(30_000);

  await page.goto(UI_URL);
  await page.screenshot({ path: path.join(SHOTS, "01-new-session.png") });

  // New-session form: world name, session name, start.
  const stamp = new Date().toISOString();
  await page.locator("input").nth(0).fill(`Smoke World ${stamp}`);
  await page.locator("input").nth(1).fill(`Smoke Session ${stamp}`);
  await page.getByRole("button", { name: "Start Session" }).click();
  await page.waitForURL("**/session/**");
  console.log("session:", page.url());
  await page.screenshot({ path: path.join(SHOTS, "02-dashboard.png") });

  // Send a DM message through the chat input.
  const chatInput = page.getByTestId("chat-input");
  await chatInput.fill(
    "The party arrives at a quiet roadside shrine at dusk. Describe the scene in two sentences."
  );
  await chatInput.press("Enter");
  await page.getByTestId("chat-message").and(page.locator('[data-role="dm"]')).first().waitFor();
  await page.screenshot({ path: path.join(SHOTS, "03-dm-message.png") });

  // Wait for the AI co-DM's reply to arrive over the WebSocket and render.
  const aiMessage = page.getByTestId("chat-message").and(page.locator('[data-role="ai"]'));
  await aiMessage.first().waitFor({ timeout: AI_REPLY_TIMEOUT_MS });
  const reply = await aiMessage.first().innerText();
  console.log("ai reply:", reply.split("\n").slice(1).join(" ").slice(0, 300));
  await page.screenshot({ path: path.join(SHOTS, "04-ai-reply.png") });

  await browser.close();
  console.log("SMOKE_PASS");
}

main().catch((err) => {
  console.error("SMOKE_FAIL", err);
  process.exit(1);
});
