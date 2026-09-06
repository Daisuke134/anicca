import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import plugin from "./index.js";
import chat from "../../apps/life-manager/lib/investment-chat.js";

const commands = new Map();
plugin.register({ registerCommand(value) { commands.set(value.name, value); } });
const command = commands.get("invest");

assert.equal(command.name, "invest");
assert.deepEqual(command.nativeNames, { default: "invest" });
assert.deepEqual(command.channels, ["telegram"]);
assert.equal(command.requireAuth, true);
assert.equal(command.acceptsArgs, true);
assert.deepEqual([...commands.keys()], ["invest", "why", "risk", "pause", "resume"]);
for (const value of commands.values()) assert.equal(value.requireAuth, true);
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

result = await command.handler({ args: "pause" });
assert.match(result.text, /一時停止中/);
const firstRevision = JSON.parse(await readFile(join(loopState, "control.json"), "utf8")).revision;
result = await command.handler({ args: "pause" });
assert.equal(JSON.parse(await readFile(join(loopState, "control.json"), "utf8")).revision, firstRevision);
result = await commands.get("why").handler();
assert.match(result.text, /No fresh edge\./);
await writeFile(join(loopState, "risk-latest.json"), JSON.stringify({
  realized_pnl_ny_day_usd: "-1", unrealized_pnl_usd: "-2", cash_flow_ny_day_usd: "3",
}));
result = await commands.get("risk").handler();
assert.match(result.text, /総投資 \$100/);
assert.match(result.text, /確定損益 \$-1/);
result = await commands.get("resume").handler();
assert.match(result.text, /稼働中/);
result = await command.handler({ args: "kill" });
assert.match(result.text, /停止済み/);
result = await command.handler({ args: "resume" });
assert.match(result.text, /停止済み/);
assert.equal(JSON.parse(await readFile(join(loopState, "control.json"), "utf8")).revision, 3);
result = await command.handler({ args: "live" });
assert.match(result.text, /使い方/);
console.log("invest command plugin: PASS");
