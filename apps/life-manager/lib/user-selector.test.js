// lib/user-selector.test.js — C4 RED. The wake user-selection filter must include BOTH Composio and
// Pipedream-provisioned users, at BOTH selection sites (batch scan scheduler.js:42 AND getUserByUid
// refetch scheduler.js:280), else a Pipedream user is picked in the batch but re-excluded on refetch.
// Extract the filter into ONE pure function so both sites share it (SSOT).
"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const { calendarProviderFilter, schedulerCohortFilter, isCallablePhone, WAKE_CALENDAR_PROVIDERS } = require("./user-selector.js");

const CLOCK = Date.parse("2026-08-28T12:00:00.000Z");
const CLOCK_ISO = encodeURIComponent(new Date(CLOCK).toISOString());

test("providers include composio_gcal AND pipedream_gcal", () => {
  assert.ok(WAKE_CALENDAR_PROVIDERS.includes("composio_gcal"));
  assert.ok(WAKE_CALENDAR_PROVIDERS.includes("pipedream_gcal"));
});

test("isCallablePhone accepts only stored E.164 strings", () => {
  for (const value of ["+819012345678", "+14155552671"]) assert.equal(isCallablePhone(value), true, value);
  for (const value of [null, undefined, "", "  +819012345678", "+81 (90) 1234-5678", "819012345678", 819012345678, "+123"]) {
    assert.equal(isCallablePhone(value), false, String(value));
  }
});

test("calendarProviderFilter: PostgREST in.() over both providers, not eq.composio_gcal", () => {
  const f = calendarProviderFilter();
  assert.equal(f, "calendar_provider=in.(composio_gcal,pipedream_gcal)");
  assert.equal(f.includes("eq.composio_gcal"), false); // the old exclusive filter is gone
});

test("scheduler cohort is paid OR trial-active at the exact server clock", () => {
  assert.equal(
    schedulerCohortFilter({}, CLOCK),
    `or=(paid.is.true,trial_expires_at.gt.${CLOCK_ISO})&calendar_provider=in.(composio_gcal,pipedream_gcal)`,
  );
});

test("active comp removes only the entitlement predicate", () => {
  assert.equal(
    schedulerCohortFilter({ LM_COMP_UNTIL: "2026-08-28T12:01:00.000Z" }, CLOCK),
    "calendar_provider=in.(composio_gcal,pipedream_gcal)",
  );
});

test("invalid scheduler clock falls back to Date.now", () => {
  const previousNow = Date.now;
  Date.now = () => CLOCK;
  try {
    assert.equal(
      schedulerCohortFilter({}, Number.NaN),
      `or=(paid.is.true,trial_expires_at.gt.${CLOCK_ISO})&calendar_provider=in.(composio_gcal,pipedream_gcal)`,
    );
  } finally {
    Date.now = previousNow;
  }
});

// ── Demo comp window ──────────────────────────────────────────────────────────
// An unpaid row is invisible to the scheduler entitlement filter, so a comped demo user would get
// zero wakes/travel/asks. While LM_COMP_UNTIL is in the future the entitlement predicate drops out
// of the query; the instant it expires the filter is byte-for-byte what it always was.
const COMP_UNTIL = "2026-07-27T12:00:00.000Z";
const COMP_UNTIL_MS = Date.parse(COMP_UNTIL);
const baselineAt = (nowMs) => `or=(paid.is.true,trial_expires_at.gt.${encodeURIComponent(new Date(nowMs).toISOString())})&calendar_provider=in.(composio_gcal,pipedream_gcal)`;

test("comp active → the entitlement predicate is dropped, everything else identical", () => {
  assert.equal(
    schedulerCohortFilter({ LM_COMP_UNTIL: COMP_UNTIL }, COMP_UNTIL_MS - 1),
    "calendar_provider=in.(composio_gcal,pipedream_gcal)",
  );
});

test("comp expired / invalid / absent → byte-for-byte the current filter", () => {
  assert.equal(schedulerCohortFilter({ LM_COMP_UNTIL: COMP_UNTIL }, COMP_UNTIL_MS), baselineAt(COMP_UNTIL_MS));
  assert.equal(schedulerCohortFilter({ LM_COMP_UNTIL: COMP_UNTIL }, COMP_UNTIL_MS + 60000), baselineAt(COMP_UNTIL_MS + 60000));
  assert.equal(schedulerCohortFilter({ LM_COMP_UNTIL: "someday" }, COMP_UNTIL_MS - 1), baselineAt(COMP_UNTIL_MS - 1));
  assert.equal(schedulerCohortFilter({}, COMP_UNTIL_MS - 1), baselineAt(COMP_UNTIL_MS - 1));
});

test("no-arg call reads process.env, so scheduler.js/daily-preflight.js need no plumbing", () => {
  const previous = process.env.LM_COMP_UNTIL;
  try {
    delete process.env.LM_COMP_UNTIL;
    const absent = schedulerCohortFilter();
    assert.equal(absent.startsWith("or=(paid.is.true,trial_expires_at.gt."), true);
    assert.equal(absent.endsWith("&calendar_provider=in.(composio_gcal,pipedream_gcal)"), true);
    process.env.LM_COMP_UNTIL = new Date(Date.now() + 3600000).toISOString();
    assert.equal(schedulerCohortFilter().includes("paid=is.true"), false);
    process.env.LM_COMP_UNTIL = new Date(Date.now() - 1000).toISOString();
    const expired = schedulerCohortFilter();
    assert.equal(expired.startsWith("or=(paid.is.true,trial_expires_at.gt."), true);
    assert.equal(expired.endsWith("&calendar_provider=in.(composio_gcal,pipedream_gcal)"), true);
  } finally {
    if (previous === undefined) delete process.env.LM_COMP_UNTIL; else process.env.LM_COMP_UNTIL = previous;
  }
});

test("scheduler.js uses the shared filter at BOTH sites (exactly 2), no lingering eq.composio_gcal — FIND-007", () => {
  const src = fs.readFileSync(path.join(__dirname, "../scheduler.js"), "utf8");
  // no hardcoded exclusive filter remains anywhere
  assert.equal((src.match(/calendar_provider=eq\.composio_gcal/g) || []).length, 0);
  // the shared helper is INTERPOLATED (inside a template literal) at BOTH selection sites → exactly 2
  const uses = (src.match(/\$\{schedulerCohortFilter\(\)\}/g) || []).length;
  assert.equal(uses, 2, `expected schedulerCohortFilter() at both selector sites, found ${uses}`);
  // and it is imported
  assert.ok(/require\(["']\.\/lib\/user-selector\.js["']\)/.test(src));
});
test("scheduler batch and uid selectors execute the same shared cohort contract", async () => {
  const oldUrl = process.env.SUPABASE_URL;
  const oldKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const oldFetch = global.fetch;
  process.env.SUPABASE_URL = "https://example.test";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "synthetic-key";
  const urls = [];
  global.fetch = async (url) => {
    urls.push(String(url));
    return { ok: true, json: async () => [{ uid: "synthetic-user", phone: null, paid: true, calendar_provider: "composio_gcal" }] };
  };
  try {
    const { listPaidUsers, getUserByUid } = require("../scheduler.js");
    const listed = await listPaidUsers();
    const reloaded = await getUserByUid("synthetic-user");
    assert.equal(listed[0].phone, null, "cohort includes paid phone-less users for reminder/travel organs");
    assert.equal(reloaded.phone, null, "uid reload preserves phone-less cohort membership");
  } finally {
    global.fetch = oldFetch;
    if (oldUrl === undefined) delete process.env.SUPABASE_URL; else process.env.SUPABASE_URL = oldUrl;
    if (oldKey === undefined) delete process.env.SUPABASE_SERVICE_ROLE_KEY; else process.env.SUPABASE_SERVICE_ROLE_KEY = oldKey;
  }
  assert.equal(urls.length, 4);
  const cohortUrls = urls.filter(value => new URL(value).pathname.endsWith("/lm_users"));
  assert.equal(cohortUrls.length, 2);
  for (const value of cohortUrls) {
    const url = new URL(value);
    assert.equal(url.searchParams.get("phone"), null, "phone is optional for reminder/travel cohort");
    assert.equal(url.searchParams.get("paid"), null);
    assert.equal(url.searchParams.get("or").startsWith("(paid.is.true,trial_expires_at.gt."), true);
    assert.equal(url.searchParams.get("calendar_provider"), "in.(composio_gcal,pipedream_gcal)");
  }
  assert.equal(urls.filter(value => new URL(value).pathname.endsWith("/lm_panel_preferences")).length, 2);
});
