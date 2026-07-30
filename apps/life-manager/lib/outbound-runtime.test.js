// lib/outbound-runtime.test.js — the node-side pass runtime: trace ledger, streak, Telegram.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const {
  runOutboundPass,
  sendOutboundReport,
  appendTrace,
  readTrace,
  traceEntry,
  renderOutboundReport,
} = require("./outbound-runtime.js");
const { validatePackConfig } = require("./outbound-config.js");

const tempHome = () => fs.mkdtempSync(path.join(os.tmpdir(), "outbound-runtime-"));

function goodPng(size = 6000) {
  const bytes = Buffer.alloc(size, 0x11);
  bytes.set([0x89, 0x50, 0x4e, 0x47], 0);
  return bytes;
}

function config(overrides = {}) {
  return validatePackConfig({
    pack: "events",
    enabled: true,
    daily_cap: 5,
    denylist: [],
    segments: ["luma-lt-en"],
    ...overrides,
  });
}

function verifiedEvidence(artifactPath) {
  return {
    e1: { kind: "http", status: 200 },
    e2: { path: artifactPath, bytes: goodPng() },
    e3: { url: "https://luma.com/abc123", head_status: 200 },
  };
}

function stagesThatSucceed(candidates, artifactPath) {
  const ok = async () => ({ ok: true });
  return {
    discover: async () => ({ ok: true, candidates }),
    qualify: ok,
    act: ok,
    evidence: async () => ({ ok: true, evidence: verifiedEvidence(artifactPath) }),
    track: ok,
    learn: ok,
  };
}

const NOW = Date.parse("2026-07-31T07:30:00Z");

// ---------------------------------------------------------------- Telegram honesty

test("Telegram with no token degrades to skipped instead of throwing", async () => {
  const result = await sendOutboundReport({
    token: "", chatId: "123", pack: "events", results: [],
    sendMessage: async () => { throw new Error("must not be called"); },
  });
  assert.deepEqual(result, { status: "skipped", reason: "telegram_unbound" });
});

test("Telegram with no chat id degrades to skipped instead of throwing", async () => {
  const result = await sendOutboundReport({
    token: "bot-token", chatId: null, pack: "events", results: [],
    sendMessage: async () => { throw new Error("must not be called"); },
  });
  assert.deepEqual(result, { status: "skipped", reason: "telegram_unbound" });
});

test("Telegram rejection is reported as failed, never as success", async () => {
  const result = await sendOutboundReport({
    token: "bot-token", chatId: "123", pack: "events", results: [],
    sendMessage: async () => ({ ok: false, description: "chat not found" }),
  });
  assert.equal(result.status, "failed");
  assert.match(result.reason, /chat not found/);
});

test("a thrown Telegram transport error is caught and surfaced honestly", async () => {
  const result = await sendOutboundReport({
    token: "bot-token", chatId: "123", pack: "events", results: [],
    sendMessage: async () => { throw new Error("socket hang up"); },
  });
  assert.equal(result.status, "failed");
  assert.match(result.reason, /socket hang up/);
});

test("a successful Telegram send returns the real message id", async () => {
  const sent = [];
  const result = await sendOutboundReport({
    token: "bot-token",
    chatId: "123",
    pack: "events",
    results: [{ target: "a", status: "verified", stage_reached: "LEARN", reason: null }],
    sendMessage: async (token, chatId, text) => {
      sent.push({ token, chatId, text });
      return { ok: true, result: { message_id: 4242 } };
    },
  });
  assert.deepEqual(result, { status: "sent", telegram_message_id: 4242 });
  assert.equal(sent[0].chatId, "123");
  assert.match(sent[0].text, /events/);
});

test("the report names each failure reason so a dead loop cannot look healthy", () => {
  const text = renderOutboundReport("events", [
    { target: "a", status: "verified", stage_reached: "LEARN", reason: null },
    { target: "b", status: "failed", stage_reached: "EVIDENCE", reason: "E2_ABSENT" },
    { target: null, status: "failed", stage_reached: "DISCOVER", reason: "source_login_expired" },
  ]);
  assert.match(text, /verified 1/);
  assert.match(text, /failed 2/);
  assert.match(text, /EVIDENCE/);
  assert.match(text, /E2_ABSENT/);
  assert.match(text, /source_login_expired/);
});

// ---------------------------------------------------------------- trace ledger

test("trace entries carry exactly the spec §6 fields", () => {
  const entry = traceEntry({
    pack: "events",
    segment: "luma-lt-en",
    target: { id: "evt-1", name: "AI Tokyo" },
    template_variant: "v1-baseline",
    result: {
      status: "verified", stage_reached: "LEARN", reason: null,
      evidence: verifiedEvidence("/tmp/a.png"), ts: "2026-07-31T07:30:00.000Z",
    },
  });
  assert.deepEqual(Object.keys(entry).sort(), [
    "evidence", "outcome", "outcome_at", "pack", "reply_text",
    "segment", "sent_at", "stage_reached", "target", "template_variant", "ts",
  ]);
  assert.equal(entry.outcome, "verified");
  assert.equal(entry.target, "evt-1");
  assert.equal(entry.reply_text, null);
});

test("trace entries never persist raw artifact bytes into the ledger", () => {
  const entry = traceEntry({
    pack: "events", segment: "s", target: "t", template_variant: "v1-baseline",
    result: {
      status: "verified", stage_reached: "LEARN", reason: null,
      evidence: verifiedEvidence("/tmp/a.png"), ts: "2026-07-31T07:30:00.000Z",
    },
  });
  assert.equal(entry.evidence.e2.path, "/tmp/a.png");
  assert.equal(entry.evidence.e2.bytes, undefined);
  assert.equal(JSON.stringify(entry).length < 2000, true);
});

test("appendTrace writes one JSON object per line and readTrace round-trips it", () => {
  const home = tempHome();
  const rows = [
    traceEntry({
      pack: "events", segment: "s", target: "a", template_variant: "v1",
      result: { status: "verified", stage_reached: "LEARN", reason: null, evidence: null, ts: "2026-07-31T07:30:00.000Z" },
    }),
    traceEntry({
      pack: "events", segment: "s", target: "b", template_variant: "v1",
      result: { status: "failed", stage_reached: "ACT", reason: "form_404", evidence: null, ts: "2026-07-31T07:31:00.000Z" },
    }),
  ];
  const file = appendTrace(home, "events", rows);
  assert.equal(file, path.join(home, ".local", "state", "life-manager", "outbound", "trace-events.jsonl"));
  const raw = fs.readFileSync(file, "utf8").trim().split("\n");
  assert.equal(raw.length, 2);
  raw.forEach((line) => assert.doesNotThrow(() => JSON.parse(line)));
  appendTrace(home, "events", rows);
  assert.equal(readTrace(home, "events").length, 4, "appendTrace must append, never truncate");
});

test("the trace ledger lives outside the repo, under the canonical data root", () => {
  const home = tempHome();
  const file = appendTrace(home, "funders", []);
  assert.match(file, /\.local\/state\/life-manager\/outbound\/trace-funders\.jsonl$/);
  assert.equal(file.includes("life-manager-main"), false);
});

// ---------------------------------------------------------------- the pass

test("a completed pass writes the trace, records the claim, touches the heartbeat", async () => {
  const home = tempHome();
  const artifact = path.join(home, "receipt.png");
  fs.writeFileSync(artifact, goodPng());
  const pass = await runOutboundPass({
    pack: "events",
    config: config(),
    stages: stagesThatSucceed(["evt-1", "evt-2"], artifact),
    homeDir: home,
    nowMs: NOW,
    telegram: { token: "", chatId: "" },
  });
  assert.equal(pass.status, "completed");
  assert.equal(pass.results.length, 2);
  assert.equal(pass.results.every((r) => r.status === "verified"), true);
  assert.equal(readTrace(home, "events").length, 2);
  assert.equal(fs.existsSync(path.join(home, ".local", "state", "life-manager", ".outbound-last-pass")), true);
  assert.deepEqual(pass.telegram, { status: "skipped", reason: "telegram_unbound" });
});

test("a pass cannot advance green_days from its own claim", async () => {
  const home = tempHome();
  const artifact = path.join(home, "receipt.png");
  fs.writeFileSync(artifact, goodPng());
  const pass = await runOutboundPass({
    pack: "events",
    config: config(),
    stages: stagesThatSucceed(["evt-1"], artifact),
    homeDir: home,
    nowMs: NOW,
    telegram: { token: "", chatId: "" },
  });
  assert.equal(pass.streak.events.green_days, 0, "only the independent verifier may award a green day");
  assert.deepEqual(pass.streak.events.last_claim, { date: "2026-07-31", claimed: 1 });
});

test("a disabled pack skips without touching the trace, but still heartbeats", async () => {
  const home = tempHome();
  const pass = await runOutboundPass({
    pack: "jobs",
    config: config({ pack: "jobs", enabled: false }),
    stages: stagesThatSucceed(["job-1"], "/nope.png"),
    homeDir: home,
    nowMs: NOW,
    telegram: { token: "", chatId: "" },
  });
  assert.equal(pass.status, "skipped");
  assert.equal(pass.reason, "pack_disabled");
  assert.equal(readTrace(home, "jobs").length, 0);
  assert.equal(fs.existsSync(path.join(home, ".local", "state", "life-manager", ".outbound-last-pass")), true);
});

test("daily_cap bounds how many candidates a single pass acts on", async () => {
  const home = tempHome();
  const artifact = path.join(home, "receipt.png");
  fs.writeFileSync(artifact, goodPng());
  const acted = [];
  const base = stagesThatSucceed(["a", "b", "c", "d", "e", "f", "g"], artifact);
  const pass = await runOutboundPass({
    pack: "events",
    config: config({ daily_cap: 3 }),
    stages: { ...base, act: async ({ target }) => { acted.push(target); return { ok: true }; } },
    homeDir: home,
    nowMs: NOW,
    telegram: { token: "", chatId: "" },
  });
  assert.deepEqual(acted, ["a", "b", "c"]);
  assert.equal(pass.results.length, 3);
});

test("a denylisted candidate is blocked deterministically before QUALIFY judges it", async () => {
  const home = tempHome();
  const artifact = path.join(home, "receipt.png");
  fs.writeFileSync(artifact, goodPng());
  const judged = [];
  const base = stagesThatSucceed(
    [{ name: "Antler Japan" }, { name: "MUFG Innovation Partners" }],
    artifact,
  );
  const pass = await runOutboundPass({
    pack: "funders",
    config: config({ pack: "funders", denylist: ["MUFG", "三菱UFJ"] }),
    stages: { ...base, qualify: async ({ target }) => { judged.push(target.name); return { ok: true }; } },
    homeDir: home,
    nowMs: NOW,
    telegram: { token: "", chatId: "" },
  });
  assert.deepEqual(judged, ["Antler Japan"], "the model must never be asked about a denylisted target");
  const blocked = pass.results.find((r) => r.status === "failed");
  assert.equal(blocked.stage_reached, "QUALIFY");
  assert.equal(blocked.reason, "denylisted:MUFG");
});

test("the pass reports a stage that refuses (NOT_IMPLEMENTED) as failed, not as success", async () => {
  const home = tempHome();
  const { discoverEvents } = require("./providers/luma.js");
  const base = stagesThatSucceed([], "/nope.png");
  const pass = await runOutboundPass({
    pack: "events",
    config: config(),
    stages: { ...base, discover: discoverEvents },
    homeDir: home,
    nowMs: NOW,
    telegram: { token: "", chatId: "" },
  });
  assert.equal(pass.status, "completed");
  assert.equal(pass.results[0].status, "failed");
  assert.match(pass.results[0].reason, /discover_threw: NOT_IMPLEMENTED: luma\.discoverEvents/);
  assert.equal(readTrace(home, "events")[0].outcome, "failed");
});

test("runOutboundPass validates its pack name rather than writing a trace-undefined.jsonl", async () => {
  const home = tempHome();
  await assert.rejects(
    () => runOutboundPass({
      pack: "connpass", config: config(), stages: stagesThatSucceed([], "/x.png"),
      homeDir: home, nowMs: NOW, telegram: {},
    }),
    /pack must be one of events, funders, jobs/,
  );
});
