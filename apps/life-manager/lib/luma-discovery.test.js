"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  collectLumaInventory,
  discoverLumaTokyo,
  normalizeLumaCandidate,
} = require("./luma-discovery.js");

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
  });

  assert.equal(result.complete, true);
  assert.equal(result.rounds, 5);
  assert.deepEqual(result.candidates.map(({ title }) => title), [
    "AI Meetup",
    "Founder Night",
    "Night Run",
  ]);
});

test("normalizes reference-only event fields and does not apply a category filter", () => {
  assert.deepEqual(normalizeLumaCandidate(raw("night-run", "Night Run vol.6")), {
    provider: "luma",
    canonical_url: "https://luma.com/night-run",
    event_ref: "luma-event://event/night-run",
    title: "Night Run vol.6",
    date_label: "8月10日 月曜日",
    time_label: "19:00",
    discovery_text: "19:00 Night Run vol.6 Organizer Tokyo",
  });
});

test("rejects reserved pages, credential URLs, missing event titles, and oversized text", () => {
  assert.equal(normalizeLumaCandidate(raw("pricing", "Pricing")), null);
  assert.equal(normalizeLumaCandidate({
    ...raw("event-a", "AI Meetup"),
    href: "https://user:secret@luma.com/event-a",
  }), null);
  assert.equal(normalizeLumaCandidate(raw("event-a", "")), null);
  assert.equal(normalizeLumaCandidate(raw("event-a", "AI Meetup", {
    cardText: "x".repeat(4001),
  })), null);
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
  });

  assert.deepEqual(calls, [["withLumaPage", "https://luma.com/discover/tokyo"]]);
  assert.equal(rounds, 3);
  assert.equal(result.complete, true);
  assert.equal(result.candidates.length, 1);
});
