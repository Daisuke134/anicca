// node:test — the loop must expose the x402 lifecycle actions already implemented by earn/run.sh.
// A stale empty-args-only prompt made every natural wake choose ensure forever.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { buildSystemPrompt, buildUserMessage, getToolDefinitions } from "../prompt.mjs";

const ctx = {
  walletAddress: "0xabc",
  balanceUsdc: 4.5,
  tier: "funded",
  model: "auto",
  wakeId: "W1",
  recentLedgerLines: [],
  recentSlots: [],
  activeSkillSlots: ["x402_sell"],
  skillCatalog: {},
};

for (const [name, text] of [
  ["system prompt", () => buildSystemPrompt(ctx, ctx.activeSkillSlots)],
  ["user prompt", () => buildUserMessage(ctx)],
  ["tool description", () => getToolDefinitions(["x402_sell"])[0].function.description],
]) {
  test(`${name} exposes every x402 lifecycle action`, () => {
    const value = text();
    assert.match(value, /args\.action|\{"action"|\{action:/i, "describes the action argument");
    for (const action of ["ensure", "review", "improve", "update"]) {
      assert.match(value, new RegExp(`\\b${action}\\b`, "i"), action);
    }
    assert.doesNotMatch(value, /x402_sell\s*(?:→|—).*args ignored/is);
    assert.doesNotMatch(value, /only correct x402_sell call is the empty-args call/is);
  });
}

test("Claude-provider shape prompt no longer pins x402_sell to empty args", async () => {
  const brain = await readFile(new URL("../brain.mjs", import.meta.url), "utf8");
  assert.doesNotMatch(brain, /only correct x402_sell call is the empty-args call/is);
  assert.match(brain, /args\.action/i);
  for (const action of ["ensure", "review", "improve", "update"]) {
    assert.match(brain, new RegExp(`\\b${action}\\b`, "i"), action);
  }
});

test("x402-only wake never tells the model to call unavailable capital slots", () => {
  const value = buildUserMessage({
    ...ctx,
    balanceUsdc: 4.5,
    reserveUsdc: 5,
    activeSkillSlots: ["report", "cook", "x402_sell"],
  });
  assert.match(value, /x402_sell/);
  assert.match(value, /zero-capital/i);
  for (const unavailable of ["hl_trade", "token_launch", "yield", "self/issue-dev"]) {
    assert.doesNotMatch(value, new RegExp(unavailable.replace("/", "\\/"), "i"), unavailable);
  }
  assert.doesNotMatch(value, /close a profitable HL|withdraw idle yield/i);
});
