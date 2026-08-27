"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const { classifyOwnership } = require("./marketing-ownership-audit.js");

const selected = ["ai.anicca.life-manager-honne-en", "ai.anicca.life-manager-honne-ja"];

test("ownership audit flags a loaded legacy marketing owner and keeps disabled legacy safe", () => {
  const result = classifyOwnership({ selectedLabels: selected, selectedStates: { [selected[0]]: { loaded: true, last_exit_code: 0 }, [selected[1]]: { loaded: true, last_exit_code: 0 } }, legacyRows: [{ label: "ai.anicca.marketing-owner-daily", loaded: true, last_exit_code: 0, program: "/Users/anicca/anicca/skills/earn/marketing-engine/report/owner_report_cli.py" }, { label: "ai.anicca.reelclaw-honne-en", loaded: false, last_exit_code: null, program: "/Users/anicca/profitable-claude/bin/launchd_run_and_report.sh" }], disabledOverrides: { "ai.anicca.reelclaw-honne-en": true } });
  assert.equal(result.status, "not_ready");
  assert.deepEqual(result.conflicts.map(({ label, reason }) => ({ label, reason })), [{ label: "ai.anicca.marketing-owner-daily", reason: "legacy_loaded" }]);
  assert.equal(result.selected_healthy, true);
});

test("ownership audit is ready only when every legacy candidate is unloaded or disabled", () => {
  const result = classifyOwnership({ selectedLabels: selected, selectedStates: { [selected[0]]: { loaded: true, last_exit_code: 0 }, [selected[1]]: { loaded: true, last_exit_code: 0 } }, legacyRows: [{ label: "ai.anicca.marketing-owner-daily", loaded: false, last_exit_code: 0, program: "/Users/anicca/anicca/skills/earn/marketing-engine/report/owner_report_cli.py" }], disabledOverrides: { "ai.anicca.marketing-owner-daily": true } });
  assert.equal(result.status, "ready");
  assert.equal(result.conflicts.length, 0);
  assert.equal(result.legacy_safe, true);
});

test("ownership audit source does not introduce legacy path tokens into LM runtime", () => {
  const source = fs.readFileSync(path.join(__dirname, "marketing-ownership-audit.js"), "utf8");
  assert.doesNotMatch(source, /profitable-claude|\.openclaw/);
});
