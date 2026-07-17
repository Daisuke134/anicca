// lib/user-selector.test.js — C4 RED. The wake user-selection filter must include BOTH Composio and
// Pipedream-provisioned users, at BOTH selection sites (batch scan scheduler.js:42 AND getUserByUid
// refetch scheduler.js:280), else a Pipedream user is picked in the batch but re-excluded on refetch.
// Extract the filter into ONE pure function so both sites share it (SSOT).
"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { calendarProviderFilter, WAKE_CALENDAR_PROVIDERS } = require("./user-selector.js"); // missing → RED

test("providers include composio_gcal AND pipedream_gcal", () => {
  assert.ok(WAKE_CALENDAR_PROVIDERS.includes("composio_gcal"));
  assert.ok(WAKE_CALENDAR_PROVIDERS.includes("pipedream_gcal"));
});

test("calendarProviderFilter: PostgREST in.() over both providers, not eq.composio_gcal", () => {
  const f = calendarProviderFilter();
  assert.equal(f, "calendar_provider=in.(composio_gcal,pipedream_gcal)");
  assert.equal(f.includes("eq.composio_gcal"), false); // the old exclusive filter is gone
});

test("scheduler.js uses the shared filter at BOTH sites (exactly 2), no lingering eq.composio_gcal — FIND-007", () => {
  const src = fs.readFileSync(path.join(__dirname, "../scheduler.js"), "utf8");
  // no hardcoded exclusive filter remains anywhere
  assert.equal((src.match(/calendar_provider=eq\.composio_gcal/g) || []).length, 0);
  // the shared helper is INTERPOLATED (inside a template literal) at BOTH selection sites → exactly 2
  const uses = (src.match(/\$\{calendarProviderFilter\(\)\}/g) || []).length;
  assert.equal(uses, 2, `expected calendarProviderFilter() at both selector sites, found ${uses}`);
  // and it is imported
  assert.ok(/require\(["']\.\/lib\/user-selector\.js["']\)/.test(src));
});
