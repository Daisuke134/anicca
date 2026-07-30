// scripts/outbound-verify.test.js — the independent GREEN gate.
//
// The verifier's whole reason to exist: the pass runtime's own "verified" is a CLAIM. The verifier
// re-reads the artifact off disk and re-runs the evidence gate before a green day is awarded.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const { verifyPass } = require("./outbound-verify.js");
const { appendTrace, traceEntry } = require("../lib/outbound-runtime.js");

const tempHome = () => fs.mkdtempSync(path.join(os.tmpdir(), "outbound-verify-"));

function goodPng(size = 6000) {
  const bytes = Buffer.alloc(size, 0x11);
  bytes.set([0x89, 0x50, 0x4e, 0x47], 0);
  return bytes;
}

function claim({ target, artifactPath, ts, status = "verified", e3 } = {}) {
  return traceEntry({
    pack: "events",
    segment: "luma-lt-en",
    target,
    template_variant: "v1-baseline",
    result: {
      status,
      stage_reached: status === "verified" ? "LEARN" : "ACT",
      reason: status === "verified" ? null : "form_404",
      evidence: {
        e1: { kind: "http", status: 200 },
        e2: { path: artifactPath },
        e3: e3 || { url: "https://luma.com/abc123", head_status: 200 },
      },
      ts,
    },
  });
}

function writeArtifact(home, name, bytes = goodPng()) {
  const file = path.join(home, name);
  fs.writeFileSync(file, bytes);
  return file;
}

const TS = "2026-07-31T07:30:00.000Z";
const DATE = "2026-07-31";

test("a claim whose artifact really is on disk earns the green day", async () => {
  const home = tempHome();
  const artifact = writeArtifact(home, "a.png");
  appendTrace(home, "events", [claim({ target: "evt-a", artifactPath: artifact, ts: TS })]);
  const result = await verifyPass({ homeDir: home, pack: "events", date: DATE });
  assert.equal(result.claimed, 1);
  assert.equal(result.verified, 1);
  assert.deepEqual(result.rejected, []);
  assert.equal(result.green_days, 1);
  assert.equal(result.green, false);
});

// ---- THE ANTI-FAKE TEST -------------------------------------------------------------------
test("ANTI-FAKE: the pipeline claimed verified but the artifact is not on disk → no green day", async () => {
  const home = tempHome();
  const missing = path.join(home, "never-written.png");
  assert.equal(fs.existsSync(missing), false);
  appendTrace(home, "events", [claim({ target: "evt-ghost", artifactPath: missing, ts: TS })]);

  const result = await verifyPass({ homeDir: home, pack: "events", date: DATE });

  assert.equal(result.claimed, 1, "the trace did claim a success");
  assert.equal(result.verified, 0, "self-reported success must not count");
  assert.equal(result.green_days, 0, "a self-reported success must not advance the streak");
  assert.equal(result.green, false);
  assert.equal(result.rejected[0].target, "evt-ghost");
  assert.match(result.rejected[0].failures.join(","), /E2_ABSENT/);
});

test("ANTI-FAKE: a claim already standing on a 6-day streak is knocked back to 0", async () => {
  const home = tempHome();
  const { applyDay, writeStreak, streakStatePath } = await import(
    require("node:url").pathToFileURL(
      path.join(__dirname, "..", "..", "..", "runtime", "loop", "outbound", "streak.mjs"),
    ).href
  );
  let state = {};
  for (const date of ["2026-07-25", "2026-07-26", "2026-07-27", "2026-07-28", "2026-07-29", "2026-07-30"]) {
    state = applyDay(state, { pack: "events", date, verifiedCount: 1 });
  }
  assert.equal(state.events.green_days, 6);
  writeStreak(streakStatePath(home), state);

  appendTrace(home, "events", [claim({
    target: "evt-ghost", artifactPath: path.join(home, "nope.png"), ts: TS,
  })]);
  const result = await verifyPass({ homeDir: home, pack: "events", date: DATE });
  assert.equal(result.green_days, 0, "day 7 cannot be bought with an unverifiable claim");
});

test("a claim whose artifact was truncated below the byte floor is rejected", async () => {
  const home = tempHome();
  const artifact = writeArtifact(home, "small.png", goodPng(400));
  appendTrace(home, "events", [claim({ target: "evt-small", artifactPath: artifact, ts: TS })]);
  const result = await verifyPass({ homeDir: home, pack: "events", date: DATE });
  assert.equal(result.verified, 0);
  assert.match(result.rejected[0].failures.join(","), /E2_TOO_SMALL/);
});

test("a claim carrying a /join/complete/ URL is rejected on re-check", async () => {
  const home = tempHome();
  const artifact = writeArtifact(home, "b.png");
  appendTrace(home, "events", [claim({
    target: "evt-oneshot",
    artifactPath: artifact,
    ts: TS,
    e3: { url: "https://luma.com/join/complete/g-abc", head_status: 200 },
  })]);
  const result = await verifyPass({ homeDir: home, pack: "events", date: DATE });
  assert.equal(result.verified, 0);
  assert.match(result.rejected[0].failures.join(","), /E3_ONE_SHOT_URL/);
});

test("rows the pass already called failed are not counted as claims", async () => {
  const home = tempHome();
  const artifact = writeArtifact(home, "c.png");
  appendTrace(home, "events", [
    claim({ target: "evt-ok", artifactPath: artifact, ts: TS }),
    claim({ target: "evt-bad", artifactPath: artifact, ts: TS, status: "failed" }),
  ]);
  const result = await verifyPass({ homeDir: home, pack: "events", date: DATE });
  assert.equal(result.claimed, 1);
  assert.equal(result.verified, 1);
});

test("only the requested calendar day is scored", async () => {
  const home = tempHome();
  const artifact = writeArtifact(home, "d.png");
  appendTrace(home, "events", [
    claim({ target: "yesterday", artifactPath: artifact, ts: "2026-07-30T07:30:00.000Z" }),
    claim({ target: "today", artifactPath: artifact, ts: TS }),
  ]);
  const result = await verifyPass({ homeDir: home, pack: "events", date: DATE });
  assert.equal(result.claimed, 1);
});

test("a day with no trace rows at all resets green_days to 0", async () => {
  const home = tempHome();
  const artifact = writeArtifact(home, "e.png");
  appendTrace(home, "events", [claim({ target: "x", artifactPath: artifact, ts: "2026-07-30T07:30:00.000Z" })]);
  await verifyPass({ homeDir: home, pack: "events", date: "2026-07-30" });
  const result = await verifyPass({ homeDir: home, pack: "events", date: DATE });
  assert.equal(result.claimed, 0);
  assert.equal(result.verified, 0);
  assert.equal(result.green_days, 0);
});

test("the verifier touches the guardian heartbeat on every completed pass", async () => {
  const home = tempHome();
  const beat = path.join(home, ".local", "state", "life-manager", ".outbound-last-pass");
  assert.equal(fs.existsSync(beat), false);
  await verifyPass({ homeDir: home, pack: "events", date: DATE });
  assert.equal(fs.existsSync(beat), true);
});

test("the verifier persists the streak it computed", async () => {
  const home = tempHome();
  const artifact = writeArtifact(home, "f.png");
  appendTrace(home, "events", [claim({ target: "evt-a", artifactPath: artifact, ts: TS })]);
  await verifyPass({ homeDir: home, pack: "events", date: DATE });
  const saved = JSON.parse(fs.readFileSync(
    path.join(home, ".local", "state", "life-manager", "outbound", "streak.json"), "utf8",
  ));
  assert.equal(saved.events.green_days, 1);
  assert.equal(saved.events.history.at(-1).verified, 1);
});

test("seven independently re-verified days make the pack GREEN", async () => {
  const home = tempHome();
  const artifact = writeArtifact(home, "g.png");
  const days = [
    "2026-07-25", "2026-07-26", "2026-07-27", "2026-07-28",
    "2026-07-29", "2026-07-30", "2026-07-31",
  ];
  let last;
  for (const date of days) {
    appendTrace(home, "events", [claim({ target: `evt-${date}`, artifactPath: artifact, ts: `${date}T07:30:00.000Z` })]);
    last = await verifyPass({ homeDir: home, pack: "events", date });
  }
  assert.equal(last.green_days, 7);
  assert.equal(last.green, true);
});
