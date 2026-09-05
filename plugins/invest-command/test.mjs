import assert from "node:assert/strict";
import plugin from "./index.js";

let command;
plugin.register({ registerCommand(value) { command = value; } });

assert.equal(command.name, "invest");
assert.deepEqual(command.channels, ["telegram"]);
assert.equal(command.requireAuth, true);
assert.equal(command.acceptsArgs, false);
const result = await command.handler();
assert.match(result.text, /^Investment Loop\n/);
assert.doesNotMatch(result.text, /Codex:::/);
console.log("invest command plugin: PASS");
