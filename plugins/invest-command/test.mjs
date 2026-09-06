import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import plugin from "./index.js";
import chat from "../../apps/life-manager/lib/investment-chat.js";

let command;
plugin.register({ registerCommand(value) { command = value; } });

assert.equal(command.name, "invest");
assert.deepEqual(command.nativeNames, { default: "invest" });
assert.deepEqual(command.channels, ["telegram"]);
assert.equal(command.requireAuth, true);
assert.equal(command.acceptsArgs, false);
const stateRoot = await mkdtemp(join(tmpdir(), "invest-command-"));
process.env.LIFE_MANAGER_STATE_ROOT = stateRoot;
let result = await command.handler();
assert.match(result.text, /^Investment Loop\n/);
assert.equal(result.presentation.blocks[0].buttons[0].url, "https://app.alpaca.markets/signup");
assert.doesNotMatch(result.text, /Codex:::/);

const loopState = join(stateRoot, "alpaca-investment");
await mkdir(loopState);
await writeFile(join(loopState, "account-status.json"), "null");
result = await command.handler();
assert.match(result.text, /ライブ注文は出しません/);

await writeFile(join(loopState, "account-status.json"), JSON.stringify({ application_status: "in_review" }));
for (const invalid of ["null", "[]", '"text"', "1", "true"]) {
  await writeFile(join(loopState, "observation-latest.json"), invalid);
  await writeFile(join(loopState, "allocation-latest.json"), invalid);
  result = await command.handler();
  assert.match(result.text, /最新状態をまだ読み取れません/);
  assert.doesNotMatch(result.text, /取引候補あり/);
}
await writeFile(join(loopState, "observation-latest.json"), JSON.stringify({ account: { equity: "99996.76", cash: "99996.76" } }));
await writeFile(join(loopState, "allocation-latest.json"), JSON.stringify({ approved: false, reason: "No fresh edge." }));
result = await command.handler();
assert.deepEqual(result, chat.buildInvestmentReply({
  lifecycle: "in_review",
  account: { equity: "99996.76", cash: "99996.76" },
  decision: { approved: false, reason: "No fresh edge." },
}));
assert.match(result.text, /審査中/);
assert.match(result.text, /No fresh edge\./);
console.log("invest command plugin: PASS");
