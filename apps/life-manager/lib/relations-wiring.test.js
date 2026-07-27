"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "../scheduler.js"), "utf8");

test("scheduler defaults to the real relations runtime behind an on-by-default gate", () => {
  assert.match(source, /require\("\.\/lib\/relations-runtime\.js"\)/);
  assert.match(source, /deps\.relations \|\| relationsUserOnce/);
  assert.match(source, /function relationsEnabled/);
  assert.match(source, /LM_RELATIONS_ENABLED/);
});

test("scheduler passes calendar, timezone context, active events, and location state", () => {
  assert.match(source, /gmailAccountId: u\.gmail_account_id/);
  assert.match(source, /events: inProgressEvents\(events\)/);
  assert.match(source, /getLocationState: deps\.getLocationState/);
});
