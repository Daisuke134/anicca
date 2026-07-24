"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");

test("daily launchd contract points at the bounded daily runner, not D0 directly", () => {
  const plist = fs.readFileSync(
    path.join(root, "launchd/ai.anicca.life-manager-dev.plist.template"),
    "utf8",
  );
  assert.match(plist, /StartCalendarInterval/);
  assert.match(plist, /<key>Hour<\/key>\s*<integer>4<\/integer>/);
  assert.match(plist, /<key>Minute<\/key>\s*<integer>10<\/integer>/);
  assert.match(plist, /life-manager-dev-daily\.js/);
  assert.doesNotMatch(plist, /life-manager-dev-d0\.sh/);
});

test("D0 emits only a closed machine result for every terminal path", () => {
  const source = fs.readFileSync(path.join(root, "scripts/life-manager-dev-d0.sh"), "utf8");
  assert.match(source, /LM_DEV_RESULT_PATH/);
  assert.match(source, /write_result/);
  assert.match(source, /no_unattempted_open_issue/);
  assert.match(source, /pr_created/);
  assert.doesNotMatch(source, /raw_provider_error.*LM_DEV_RESULT_PATH/);
});
