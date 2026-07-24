"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { EXPECTED_COUNTS } = require("../eval/panel-privacy-contract.js");
const { runPanelPrivacyEval } = require("../eval/panel-privacy-harness.js");

test("PANEL-8h executes the focused API and emitted-browser privacy contract", async () => {
  const result = await runPanelPrivacyEval();
  assert.deepEqual(
    { api: result.api, browser: result.browser },
    EXPECTED_COUNTS,
  );
});
