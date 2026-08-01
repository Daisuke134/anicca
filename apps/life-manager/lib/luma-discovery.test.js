"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  collectLumaInventory,
  buildLumaDailyInventory,
  discoverLumaTokyo,
  normalizeLumaCandidate,
} = require("./luma-discovery.js");

const NOW = "2026-08-01T15:30:00.000Z"; // 2026-08-02 JST

function raw(slug, title, overrides = {}) {
  return {
    href: `https://luma.com/${slug}`,
    title,
    cardText: `19:00 ${title} Organizer Tokyo`,
    timelineText: `8月10日 月曜日 19:00 ${title} Organizer Tokyo`,
    ...overrides,
  };
}

test("accumulates event cards that disappear from a virtualized timeline", async () => {
  const snapshots = [
    [raw("event-a", "AI Meetup"), raw("event-b", "Founder Night")],
    [raw("event-b", "Founder Night"), raw("event-c", "Night Run")],
    [raw("event-c", "Night Run")],
    [raw("event-c", "Night Run")],
    [raw("event-c", "Night Run")],
  ];
  let index = 0;
  const result = await collectLumaInventory({
    readSnapshot: async () => snapshots[Math.min(index, snapshots.length - 1)],
    advance: async () => {
      index += 1;
      return { atEnd: index >= 2, scrollHeight: 5000 };
    },
    maxRounds: 10,
    stableEndRounds: 3,
    now: NOW,
  });

  assert.equal(result.complete, true);
  assert.equal(result.rounds, 5);
  assert.deepEqual(result.candidates.map(({ title }) => title), [
    "AI Meetup",
    "Founder Night",
    "Night Run",
  ]);
});

test("今日/明日/月日をTokyo ISO dateへ解決しcategory filterを適用しない", () => {
  assert.deepEqual(normalizeLumaCandidate(raw("night-run", "Night Run vol.6"), { now: NOW }), {
    provider: "luma",
    canonical_url: "https://luma.com/night-run",
    event_ref: "luma-event://event/night-run",
    title: "Night Run vol.6",
    date_label: "8月10日 月曜日",
    event_date: "2026-08-10",
    time_label: "19:00",
    discovery_text: "19:00 Night Run vol.6 Organizer Tokyo",
    attendance_mode: "in_person",
    location_scope: "tokyo",
  });
  assert.equal(normalizeLumaCandidate(raw("today", "Today", { timelineText: "今日 日曜日" }), { now: NOW }).event_date, "2026-08-02");
  assert.equal(normalizeLumaCandidate(raw("tomorrow", "Tomorrow", { timelineText: "明日 月曜日" }), { now: NOW }).event_date, "2026-08-03");
  assert.equal(normalizeLumaCandidate(raw("new-year", "New Year", { timelineText: "1月2日 金曜日" }), { now: "2026-12-31T15:30:00Z" }).event_date, "2027-01-02");
});

test("rejects reserved pages, credential URLs, missing event titles, and oversized text", () => {
  assert.equal(normalizeLumaCandidate(raw("pricing", "Pricing"), { now: NOW }), null);
  assert.equal(normalizeLumaCandidate({
    ...raw("event-a", "AI Meetup"),
    href: "https://user:secret@luma.com/event-a",
  }, { now: NOW }), null);
  assert.equal(normalizeLumaCandidate(raw("event-a", ""), { now: NOW }), null);
  assert.equal(normalizeLumaCandidate(raw("event-a", "AI Meetup", {
    cardText: "x".repeat(4001),
  }), { now: NOW }), null);
});

test("fails closed when the virtualized inventory end cannot be proven", async () => {
  let round = 0;
  await assert.rejects(
    collectLumaInventory({
      readSnapshot: async () => [raw(`event-${round}`, `Event ${round}`)],
      advance: async () => {
        round += 1;
        return { atEnd: false, scrollHeight: 1000 + round };
      },
      maxRounds: 3,
      stableEndRounds: 2,
      now: NOW,
    }),
    /inventory end unproven/i,
  );
});

test("Tokyo discovery uses the shared daily-driver page and the exhaustive collector", async () => {
  const calls = [];
  const page = { id: "owned-page" };
  const dailyDriver = {
    async withLumaPage(url, task) {
      calls.push(["withLumaPage", url]);
      return task(page);
    },
  };
  let rounds = 0;
  const result = await discoverLumaTokyo({
    dailyDriver,
    readSnapshot: async (seenPage) => {
      assert.equal(seenPage, page);
      return [raw("event-a", "AI Meetup")];
    },
    advance: async (seenPage) => {
      assert.equal(seenPage, page);
      rounds += 1;
      return { atEnd: true, scrollHeight: 4000 };
    },
    stableEndRounds: 2,
    now: NOW,
  });

  assert.deepEqual(calls, [["withLumaPage", "https://luma.com/tokyo?k=p"]]);
  assert.equal(rounds, 3);
  assert.equal(result.complete, true);
  assert.equal(result.candidates.length, 1);
});

test("global end proofからrolling 21日の全日を0件日も含めcompleteにする", async () => {
  const inventory = await collectLumaInventory({
    readSnapshot: async () => [
      raw("today-a", "Today A", { timelineText: "今日 日曜日" }),
      raw("future-a", "Future A", { timelineText: "8月10日 月曜日" }),
      raw("outside", "Outside", { timelineText: "9月1日 火曜日" }),
    ],
    advance: async () => ({ atEnd: true, scrollHeight: 5000 }),
    stableEndRounds: 2,
    now: NOW,
  });
  const coverage = {
    window_start: "2026-08-02", window_end: "2026-08-22",
    days: Array.from({ length: 21 }, (_, index) => ({ date: new Date(Date.UTC(2026, 7, 2 + index)).toISOString().slice(0, 10) })),
  };
  const daily = buildLumaDailyInventory(inventory, coverage);
  assert.equal(daily.days.length, 21);
  assert.equal(daily.days.every(({ complete }) => complete), true);
  assert.equal(daily.days[0].candidate_count, 1);
  assert.equal(daily.days[8].candidate_count, 1);
  assert.equal(daily.days[1].candidate_count, 0);
  assert.equal(daily.in_window_candidate_count, 2);
  assert.equal(daily.out_of_window_candidate_count, 1);
});

test("global end未証明、21日でないcoverage、日付未解決eventをcompleteにしない", () => {
  const coverage = { window_start: "2026-08-02", window_end: "2026-08-22", days: [{ date: "2026-08-02" }] };
  assert.throws(() => buildLumaDailyInventory({ complete: false, rounds: 1, candidates: [] }, coverage), /incomplete/i);
  assert.throws(() => buildLumaDailyInventory({ complete: true, rounds: 3, candidates: [] }, coverage), /coverage/i);
  const days = Array.from({ length: 21 }, (_, index) => ({ date: new Date(Date.UTC(2026, 7, 2 + index)).toISOString().slice(0, 10) }));
  assert.throws(() => buildLumaDailyInventory({ complete: true, rounds: 3, candidates: [{ event_date: "" }] }, { window_start: days[0].date, window_end: days.at(-1).date, days }), /date/i);
});
