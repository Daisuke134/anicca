"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");


test("D0 wrapper generates issues before delegating to the existing launchd loop", () => {
  const source = fs.readFileSync(
    path.join(__dirname, "../scripts/life-manager-dev-d0.sh"),
    "utf8",
  );
  const worker = source.indexOf("feedback-to-issue.js");
  const existingD0 = source.indexOf("profitable-claude/skills/life-manager-dev/dev-pass.sh");
  assert.notEqual(worker, -1);
  assert.notEqual(existingD0, -1);
  assert.equal(worker < existingD0, true);
  assert.doesNotMatch(source, /(DATABASE_PUBLIC_URL|GH_TOKEN|GITHUB_TOKEN)=/);
});
