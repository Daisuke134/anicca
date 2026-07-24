// transport-gog.test.js — #74 slice4: the gog (local BYOK) adapter builds correct gog 0.17.0 argv,
// translates the Composio-dialect create/patch args, and getCalendar/getMail fail loud on bad env.
// Run: node --test apps/life-call/lib/transport/transport-gog.test.js
"use strict";
const { test } = require("node:test");
const assert = require("node:assert");
const { makeGogCalendar } = require("./calendar-gog.js");
const { makeGogMail } = require("./mail-gog.js");
const { getCalendar, getMail } = require("./index.js");

// capture argv passed to gog (the injected run strips the trailing --account here for clarity)
function recorder(returns) {
  const calls = [];
  const run = (args) => { calls.push(args); return typeof returns === "function" ? returns(args) : returns; };
  return { run, calls };
}
const ACCT = "me@example.com";

test("listEventsRaw → gog calendar events list with --from/--to/--max, returns array", async () => {
  const { run, calls } = recorder('[{"id":"e1","summary":"X"}]');
  const cal = makeGogCalendar({ account: ACCT, run });
  const items = await cal.listEventsRaw("ignored", { timeMin: "2026-06-21T00:00:00Z", timeMax: "2026-06-22T00:00:00Z", maxResults: 50 });
  assert.deepEqual(items, [{ id: "e1", summary: "X" }]);
  const a = calls[0];
  assert.deepEqual(a.slice(0, 4), ["calendar", "events", "list", "-j"]);
  assert.ok(a.includes("--from=2026-06-21T00:00:00Z"));   // glued --flag=value (argv-injection safe)
  assert.ok(a.includes("--to=2026-06-22T00:00:00Z"));
  assert.ok(a.includes("--max=50"));
});

test("listEventsRaw tolerates {events:[...]} and non-JSON (→ [])", async () => {
  assert.deepEqual(await makeGogCalendar({ account: ACCT, run: () => '{"events":[{"id":"e2"}]}' }).listEventsRaw("u", {}), [{ id: "e2" }]);
  assert.deepEqual(await makeGogCalendar({ account: ACCT, run: () => "not json" }).listEventsRaw("u", {}), []);
});

test("createEvent translates Composio dialect → gog --from/--to/--summary/--location", async () => {
  const { run, calls } = recorder("{}");
  const cal = makeGogCalendar({ account: ACCT, run });
  const r = await cal.createEvent("u", {
    summary: "[Travel] 🚆 A→B", start_datetime: "2026-06-21T05:00:00", event_duration_hour: 0,
    event_duration_minutes: 20, calendar_id: "primary", location: "東京駅", description: "auto",
  });
  assert.equal(r.successful, true);
  const a = calls[0];
  assert.deepEqual(a.slice(0, 3), ["calendar", "create", "primary"]);
  assert.ok(a.includes("--from=2026-06-21T05:00:00Z"));      // appended Z, glued
  assert.ok(a.includes("--to=2026-06-21T05:20:00Z"));        // +20 min
  assert.ok(a.includes("--summary=[Travel] 🚆 A→B"));
  assert.ok(a.includes("--location=東京駅"));
});

test("createEvent: bad start_datetime → {successful:false}, no run", async () => {
  const { run, calls } = recorder("{}");
  const r = await makeGogCalendar({ account: ACCT, run }).createEvent("u", { start_datetime: "garbage" });
  assert.equal(r.successful, false);
  assert.equal(calls.length, 0);
});

test("patchEvent → gog calendar update <cal> <eventId> --location", async () => {
  const { run, calls } = recorder("{}");
  const r = await makeGogCalendar({ account: ACCT, run }).patchEvent("u", { calendar_id: "primary", event_id: "e9", location: "渋谷" });
  assert.equal(r.successful, true);
  assert.deepEqual(calls[0].slice(0, 5), ["calendar", "update", "primary", "e9", "-j"]);
  assert.ok(calls[0].includes("--location=渋谷"));
});

test("patchEvent without event_id → false, no run", async () => {
  const { run, calls } = recorder("{}");
  assert.equal((await makeGogCalendar({ account: ACCT, run }).patchEvent("u", { location: "x" })).successful, false);
  assert.equal(calls.length, 0);
});

test("mail send → gog gmail send, true when {id} returned", async () => {
  const { run, calls } = recorder('{"id":"m1"}');
  const ok = await makeGogMail({ account: ACCT, run }).send("a@b.com", "Sub", "Body");
  assert.equal(ok, true);
  assert.deepEqual(calls[0].slice(0, 2), ["gmail", "send"]);
  assert.ok(calls[0].includes("--to=a@b.com"));
});

test("mail listInbox → search then get each, shaped {subject,body}", async () => {
  const run = (args) => {
    if (args[1] === "search") return '{"threads":[{"id":"t1","subject":"Re: where"}]}';
    if (args[1] === "get") return '{"headers":{"subject":"Re: where"},"body":"It is 渋谷"}';
    return "{}";
  };
  const items = await makeGogMail({ account: ACCT, run }).listInbox({ limit: 5 });
  assert.equal(items.length, 1);
  assert.equal(items[0].subject, "Re: where");
  assert.equal(items[0].body, "It is 渋谷");
});

test("argv-injection: flag-like positional calendar_id/event_id → rejected, no run", async () => {
  const { run, calls } = recorder("{}");
  const cal = makeGogCalendar({ account: ACCT, run });
  assert.equal((await cal.createEvent("u", { calendar_id: "--output=/etc/x", start_datetime: "2026-06-21T05:00:00", event_duration_minutes: 10 })).successful, false);
  assert.equal((await cal.patchEvent("u", { calendar_id: "primary", event_id: "--delete", location: "x" })).successful, false);
  assert.equal(calls.length, 0); // never reached gog
});
test("argv-injection: flag-like option VALUE is glued (--location=-x), not a separate flag", async () => {
  const { run, calls } = recorder("{}");
  await makeGogCalendar({ account: ACCT, run }).createEvent("u", {
    calendar_id: "primary", start_datetime: "2026-06-21T05:00:00", event_duration_minutes: 10, location: "--foo evil",
  });
  // location is a single token glued to its flag — gog can't parse "--foo" as a flag
  assert.ok(calls[0].includes("--location=--foo evil"));
  assert.ok(!calls[0].includes("--foo")); // no bare --foo token
});

test("no account → empty/false (never throws)", async () => {
  const cal = makeGogCalendar({ account: "" }), mail = makeGogMail({ account: "" });
  assert.deepEqual(await cal.listEventsRaw("u", {}), []);
  assert.equal((await cal.createEvent("u", {})).successful, false);
  assert.equal(await mail.send("a@b.com", "s", "b"), false);
  assert.deepEqual(await mail.listInbox({}), []);
});

test("getCalendar/getMail throw on unknown LIFE_TRANSPORT (no silent default)", () => {
  assert.throws(() => getCalendar({ kind: "telepathy" }), /Unknown LIFE_TRANSPORT/);
  assert.throws(() => getMail({ kind: "telepathy" }), /Unknown LIFE_TRANSPORT/);
  // valid kinds do not throw
  assert.equal(getCalendar({ kind: "gog", account: ACCT }).kind, "gog");
  assert.equal(getCalendar({ kind: "composio" }).kind, "composio");
});
