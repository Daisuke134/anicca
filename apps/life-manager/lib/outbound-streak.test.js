// lib/outbound-streak.test.js — the GREEN gate's day arithmetic (spec #1 done condition).
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const STREAK_URL = pathToFileURL(
  path.join(__dirname, "..", "..", "..", "runtime", "loop", "outbound", "streak.mjs"),
).href;

const loadStreak = () => import(STREAK_URL);

function tempHome() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "outbound-streak-"));
}

// The design doc says ~/.openclaw; that root is rejected repo-wide (scan-legacy-paths.js), so
// the engine uses the canonical portable root instead. See streak.mjs PATH NOTE.
test("streak paths live under the canonical data root, never inside the repo", async () => {
  const { streakStatePath, heartbeatPath, traceLedgerPath, dataRoot } = await loadStreak();
  assert.equal(dataRoot("/home/x"), "/home/x/.local/state/life-manager");
  assert.equal(dataRoot("/home/x", { LM_DATA_DIR: "/srv/lm" }), "/srv/lm");
  assert.equal(streakStatePath("/home/x"), "/home/x/.local/state/life-manager/outbound/streak.json");
  assert.equal(heartbeatPath("/home/x"), "/home/x/.local/state/life-manager/.outbound-last-pass");
  assert.equal(traceLedgerPath("/home/x", "events"), "/home/x/.local/state/life-manager/outbound/trace-events.jsonl");
});

test("streak increments once per calendar day", async () => {
  const { applyDay } = await loadStreak();
  let state = {};
  state = applyDay(state, { pack: "events", date: "2026-07-29", verifiedCount: 2 });
  assert.equal(state.events.green_days, 1);
  assert.equal(state.events.last_green_date, "2026-07-29");
  state = applyDay(state, { pack: "events", date: "2026-07-30", verifiedCount: 1 });
  assert.equal(state.events.green_days, 2);
});

test("a second pass on the same day cannot advance the streak twice", async () => {
  const { applyDay } = await loadStreak();
  let state = applyDay({}, { pack: "events", date: "2026-07-29", verifiedCount: 1 });
  state = applyDay(state, { pack: "events", date: "2026-07-29", verifiedCount: 9 });
  assert.equal(state.events.green_days, 1);
  assert.equal(state.events.history.length, 1);
});

test("a day with zero verified results resets green_days to 0", async () => {
  const { applyDay } = await loadStreak();
  let state = {};
  for (const date of ["2026-07-25", "2026-07-26", "2026-07-27"]) {
    state = applyDay(state, { pack: "events", date, verifiedCount: 1 });
  }
  assert.equal(state.events.green_days, 3);
  state = applyDay(state, { pack: "events", date: "2026-07-28", verifiedCount: 0 });
  assert.equal(state.events.green_days, 0);
  assert.equal(state.events.history.at(-1).verified, 0);
});

test("a gap day restarts the streak at 1 rather than pretending it continued", async () => {
  const { applyDay } = await loadStreak();
  let state = applyDay({}, { pack: "events", date: "2026-07-25", verifiedCount: 1 });
  state = applyDay(state, { pack: "events", date: "2026-07-25", verifiedCount: 1 });
  state = applyDay(state, { pack: "events", date: "2026-07-28", verifiedCount: 1 });
  assert.equal(state.events.green_days, 1);
});

test("7 consecutive green days makes the pack GREEN, 6 does not", async () => {
  const { applyDay, isGreen, GREEN_DAYS } = await loadStreak();
  assert.equal(GREEN_DAYS, 7);
  let state = {};
  const days = [
    "2026-07-25", "2026-07-26", "2026-07-27", "2026-07-28",
    "2026-07-29", "2026-07-30", "2026-07-31",
  ];
  days.slice(0, 6).forEach((date) => { state = applyDay(state, { pack: "events", date, verifiedCount: 1 }); });
  assert.equal(state.events.green_days, 6);
  assert.equal(isGreen(state, "events"), false);
  state = applyDay(state, { pack: "events", date: days[6], verifiedCount: 1 });
  assert.equal(state.events.green_days, 7);
  assert.equal(isGreen(state, "events"), true);
});

test("packs keep independent streaks", async () => {
  const { applyDay, isGreen } = await loadStreak();
  let state = applyDay({}, { pack: "events", date: "2026-07-30", verifiedCount: 1 });
  state = applyDay(state, { pack: "funders", date: "2026-07-30", verifiedCount: 0 });
  assert.equal(state.events.green_days, 1);
  assert.equal(state.funders.green_days, 0);
  assert.equal(isGreen(state, "jobs"), false);
});

test("applyDay never mutates the state it was handed", async () => {
  const { applyDay } = await loadStreak();
  const before = applyDay({}, { pack: "events", date: "2026-07-30", verifiedCount: 1 });
  const snapshot = JSON.stringify(before);
  applyDay(before, { pack: "events", date: "2026-07-31", verifiedCount: 1 });
  assert.equal(JSON.stringify(before), snapshot);
});

test("applyDay rejects a malformed date instead of silently inventing one", async () => {
  const { applyDay } = await loadStreak();
  assert.throws(() => applyDay({}, { pack: "events", date: "31/07/2026", verifiedCount: 1 }),
    /outbound streak needs an ISO YYYY-MM-DD date/);
  assert.throws(() => applyDay({}, { pack: "", date: "2026-07-31", verifiedCount: 1 }),
    /outbound streak needs a pack name/);
});

test("history is capped so the state file cannot grow without bound", async () => {
  const { applyDay, HISTORY_LIMIT } = await loadStreak();
  let state = {};
  for (let day = 0; day < HISTORY_LIMIT + 10; day += 1) {
    const date = new Date(Date.UTC(2026, 0, 1) + day * 86400000).toISOString().slice(0, 10);
    state = applyDay(state, { pack: "events", date, verifiedCount: 1 });
  }
  assert.equal(state.events.history.length, HISTORY_LIMIT);
});

test("applyClaim records what the pass claimed but cannot move green_days", async () => {
  const { applyClaim, applyDay } = await loadStreak();
  let state = applyDay({}, { pack: "events", date: "2026-07-30", verifiedCount: 1 });
  assert.equal(state.events.green_days, 1);
  state = applyClaim(state, { pack: "events", date: "2026-07-31", claimedCount: 12 });
  assert.equal(state.events.green_days, 1, "a self-reported claim must not advance the streak");
  assert.equal(state.events.last_green_date, "2026-07-30");
  assert.deepEqual(state.events.last_claim, { date: "2026-07-31", claimed: 12 });
  assert.equal(state.events.history.length, 1, "a claim is not a history entry");
});

test("applyClaim on a fresh pack leaves it ungreen at zero", async () => {
  const { applyClaim, isGreen } = await loadStreak();
  const state = applyClaim({}, { pack: "funders", date: "2026-07-31", claimedCount: 5 });
  assert.equal(state.funders.green_days, 0);
  assert.equal(isGreen(state, "funders"), false);
});

test("readStreak returns an empty object when no state file exists yet", async () => {
  const { readStreak, streakStatePath } = await loadStreak();
  const home = tempHome();
  assert.deepEqual(readStreak(streakStatePath(home)), {});
});

test("writeStreak then readStreak round-trips, and touchHeartbeat creates the guardian file", async () => {
  const { applyDay, readStreak, writeStreak, streakStatePath, heartbeatPath, touchHeartbeat } = await loadStreak();
  const home = tempHome();
  const statePath = streakStatePath(home);
  const state = applyDay({}, { pack: "events", date: "2026-07-31", verifiedCount: 3 });
  writeStreak(statePath, state);
  assert.deepEqual(readStreak(statePath), state);

  const beat = heartbeatPath(home);
  assert.equal(fs.existsSync(beat), false);
  touchHeartbeat(beat);
  assert.equal(fs.existsSync(beat), true);
  const first = fs.statSync(beat).mtimeMs;
  touchHeartbeat(beat, new Date(first + 60_000));
  assert.ok(fs.statSync(beat).mtimeMs > first);
});

test("readStreak refuses to guess when the state file is corrupt", async () => {
  const { readStreak, streakStatePath } = await loadStreak();
  const home = tempHome();
  const statePath = streakStatePath(home);
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, "{ this is not json", "utf8");
  assert.throws(() => readStreak(statePath), /outbound streak state is not valid JSON/);
});
