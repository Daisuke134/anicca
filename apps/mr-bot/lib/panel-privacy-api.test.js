"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { EXPECTED_COUNTS } = require("../eval/panel-privacy-contract.js");
const { runPanelPrivacyApiEval } = require("../eval/panel-privacy-harness.js");

test("PANEL-8h executes all 177 privacy assertions through real panel API responses", async () => {
  const result = await runPanelPrivacyApiEval();
  assert.deepEqual(result, {
    api: EXPECTED_COUNTS.api,
    recipes: 19,
    channels: 9,
  });
});
