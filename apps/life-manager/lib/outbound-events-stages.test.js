// lib/outbound-events-stages.test.js — the events pack's wiring, with a fake Luma provider.
//
// The provider's own behaviour is tested against real captures in lib/outbound-luma.test.js. What
// is under test HERE is the division of labour:
//   * ACT never grades itself — it returns raw material and ok=true only means "the attempt ran";
//   * EVIDENCE is the only stage that can produce a verified result, and it produces it by calling
//     the real runtime/loop/outbound/evidence.mjs, not a copy;
//   * a receipt that looks like a triumph but lacks one evidence limb still fails.
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const luma = require("./providers/luma.js");
const { buildStages, readIdentity, nameFor, discoverOptions } = require("./outbound-events-stages.js");

const PIPELINE = pathToFileURL(
  path.join(__dirname, "..", "..", "..", "runtime", "loop", "outbound", "pipeline.mjs"),
).href;

function pngBytes(size = 6000) {
  const buffer = Buffer.alloc(size, 0x20);
  Buffer.from([0x89, 0x50, 0x4e, 0x47]).copy(buffer, 0);
  return buffer;
}

const TARGET = Object.freeze({
  id: "evt-fake",
  slug: "abcdefg",
  url: "https://luma.com/abcdefg",
  name: "A free in-person Tokyo event",
  startsAt: "2026-08-04T10:00:00.000Z",
  timezone: "Asia/Tokyo",
  locationType: "offline",
  region: "Tokyo",
  countryCode: "JP",
  availability: "open",
  categories: ["AI"],
  hydrated: true,
  ticketTypes: [{ apiId: "ttype-1", name: "会場参加", type: "free", cents: null, minCents: null, requireApproval: false, isHidden: false }],
});

const RECEIPT = Object.freeze({
  requestedUrl: TARGET.url,
  canonicalUrl: TARGET.url,
  artifactPath: "/tmp/outbound-events-stages.test.png",
  guestKey: "g-TESTKEY",
  venue: "Somewhere in Meguro",
  startsAt: TARGET.startsAt,
  httpEvidence: { kind: "http", url: "https://api.lu.ma/event/independent/register", status: 201 },
  observed: { finalUrl: `${TARGET.url}?tk=A1b2C3`, tk: "A1b2C3", signals: ["tk_token", "register_2xx"] },
});

function fakeLuma(overrides = {}) {
  return {
    screenEvent: luma.screenEvent,
    buildEvidence: luma.buildEvidence,
    discoverEvents: async () => ({ ok: true, candidates: [TARGET], rejected: [] }),
    rsvp: async () => RECEIPT,
    headStatus: async () => 200,
    ...overrides,
  };
}

const deps = (overrides = {}) => ({
  luma: fakeLuma(overrides.luma),
  env: {},
  identity: { name: "Test Operator", email: "operator@example.com" },
  cdpUrl: "http://127.0.0.1:0",
  artifactDir: "/tmp",
  readFile: () => pngBytes(),
  ...overrides.deps,
});

const CONFIG = Object.freeze({ pack: "events", city: "tokyo", regions: ["Tokyo"], auto_rsvp: true, daily_cap: 5 });

// ───────────────────────────────────────────────────────────────────────── configuration

test("discoverOptions is derived from the pack config, with no hardcoded city", () => {
  assert.deepEqual(discoverOptions({ city: "osaka", regions: ["Osaka"], hydrate_limit: 3 }), {
    city: "osaka", regions: ["Osaka"], hydrateLimit: 3,
  });
  assert.equal(discoverOptions({}).city, "tokyo");
});

test("the RSVP identity comes from the environment, never from the committed config", () => {
  const identity = readIdentity({
    LM_OUTBOUND_NAME: "Daisuke Narita",
    LM_OUTBOUND_NAME_JA: "成田大祐",
    LM_OUTBOUND_EMAIL: "operator@example.com",
    LM_OUTBOUND_PHONE: "0000000000",
  });
  assert.equal(identity.name, "Daisuke Narita");
  assert.equal(identity.email, "operator@example.com");
  assert.equal(identity.phone, "0000000000");
  assert.deepEqual(readIdentity({}), { name: "", email: "" });
});

test("a Japan-local event gets the Japanese form of the name when one is configured", () => {
  const identity = { name: "Daisuke Narita", localName: "成田大祐" };
  assert.equal(nameFor({ timezone: "Asia/Tokyo" }, identity), "成田大祐");
  assert.equal(nameFor({ timezone: "America/Los_Angeles" }, identity), "Daisuke Narita");
  assert.equal(nameFor({ timezone: "Asia/Tokyo" }, { name: "Daisuke Narita" }), "Daisuke Narita");
});

// ───────────────────────────────────────────────────────────────────────── stage behaviour

test("DISCOVER passes the provider's candidates through and keeps the rejections", async () => {
  const stages = buildStages(deps());
  const outcome = await stages.discover({ config: CONFIG });
  assert.equal(outcome.ok, true);
  assert.equal(outcome.candidates.length, 1);
});

test("DISCOVER reports the provider's own failure reason rather than inventing one", async () => {
  const stages = buildStages(deps({ luma: { discoverEvents: async () => ({ ok: false, reason: "luma_discover_failed: 503" }) } }));
  const outcome = await stages.discover({ config: CONFIG });
  assert.equal(outcome.ok, false);
  assert.match(outcome.reason, /503/);
});

test("QUALIFY re-screens the target instead of trusting DISCOVER", async () => {
  const stages = buildStages(deps());
  const soldOut = { ...TARGET, availability: "sold-out" };
  const outcome = await stages.qualify({ config: CONFIG, target: soldOut });
  assert.equal(outcome.ok, false);
  assert.match(outcome.reason, /screened_out:.*NOT_OPEN/);
});

test("QUALIFY stops honestly while the model's judgment is not wired", async () => {
  const stages = buildStages(deps());
  const outcome = await stages.qualify({ config: { ...CONFIG, auto_rsvp: false }, target: TARGET });
  assert.equal(outcome.ok, false);
  assert.equal(outcome.reason, "auto_rsvp_disabled_pending_model_qualify");
});

test("ACT refuses without a leased CDP endpoint or an identity", async () => {
  const noCdp = buildStages(deps({ deps: { cdpUrl: "" } }));
  assert.deepEqual(await noCdp.act({ target: TARGET, prior: {} }), {
    ok: false, reason: "no_leased_cdp_url (browser-guard.sh acquire)",
  });
  const noIdentity = buildStages(deps({ deps: { identity: { name: "", email: "" } } }));
  assert.deepEqual(await noIdentity.act({ target: TARGET, prior: {} }), {
    ok: false, reason: "no_rsvp_identity_in_env",
  });
});

test("★ ACT returns raw material and refuses to grade itself ★", async () => {
  const stages = buildStages(deps());
  const outcome = await stages.act({ target: TARGET, prior: {} });
  assert.equal(outcome.ok, true, "ok=true means the attempt ran to completion");
  const receipt = outcome.data.receipt;
  // Nothing in the receipt says "verified" / "success" / "registered". The gate says that.
  assert.equal(Object.prototype.hasOwnProperty.call(receipt, "verified"), false);
  assert.equal(Object.prototype.hasOwnProperty.call(receipt, "success"), false);
  assert.equal(outcome.evidence, undefined);
});

test("ACT passes the chosen ticket name through so an online seat is never booked by default", async () => {
  const seen = [];
  const stages = buildStages(deps({ luma: { rsvp: async (url, identity, opts) => { seen.push(opts); return RECEIPT; } } }));
  const qualified = await stages.qualify({ config: CONFIG, target: TARGET });
  await stages.act({ target: TARGET, prior: { qualify: qualified.data } });
  assert.equal(seen[0].ticketName, "会場参加");
});

test("EVIDENCE verifies through the real gate and passes when all three limbs are real", async () => {
  const stages = buildStages(deps());
  const outcome = await stages.evidence({ prior: { act: { receipt: RECEIPT } } });
  assert.equal(outcome.ok, true, outcome.reason);
  assert.equal(outcome.evidence.e1.status, 201);
  assert.equal(outcome.evidence.e3.head_status, 200);
  // The ledger keeps the artifact PATH, never the bytes: the verifier re-reads the file.
  assert.equal(outcome.evidence.e2.path, RECEIPT.artifactPath);
  assert.equal("bytes" in outcome.evidence.e2, false);
});

test("★ EVIDENCE fails when the screenshot is missing, however convincing the receipt ★", async () => {
  const stages = buildStages(deps({ deps: { readFile: () => { throw new Error("ENOENT"); } } }));
  const outcome = await stages.evidence({ prior: { act: { receipt: RECEIPT } } });
  assert.equal(outcome.ok, false);
  assert.match(outcome.reason, /evidence_gate:.*E2_ABSENT/);
});

test("EVIDENCE fails when the canonical URL does not answer 200", async () => {
  const stages = buildStages(deps({ luma: { headStatus: async () => 404 } }));
  const outcome = await stages.evidence({ prior: { act: { receipt: RECEIPT } } });
  assert.equal(outcome.ok, false);
  assert.match(outcome.reason, /E3_HEAD_NOT_200/);
});

test("TRACK and LEARN say they are not wired instead of returning a hollow success", async () => {
  const stages = buildStages(deps());
  assert.deepEqual(await stages.track(), { ok: false, reason: "track_not_wired_for_events" });
  assert.deepEqual(await stages.learn(), { ok: false, reason: "learn_not_wired_for_events" });
});

// ───────────────────────────────────────────────────────────────────────── end to end

test("through the real pipeline, a complete RSVP reaches TRACK and stops there honestly", async () => {
  const { runPipeline } = await import(PIPELINE);
  const pass = await runPipeline({ pack: "events", config: CONFIG, stages: buildStages(deps()), nowMs: 0 });
  const [result] = pass.results;
  assert.equal(result.status, "failed");
  assert.equal(result.stage_reached, "TRACK");
  assert.equal(result.reason, "track_not_wired_for_events");
  // …but the evidence gathered before that stop is real and was accepted by the gate.
  assert.equal(result.evidence.e1.status, 201);
});

test("through the real pipeline, a missing artifact stops the candidate at EVIDENCE", async () => {
  const { runPipeline } = await import(PIPELINE);
  const stages = buildStages(deps({ deps: { readFile: () => { throw new Error("ENOENT"); } } }));
  const pass = await runPipeline({ pack: "events", config: CONFIG, stages, nowMs: 0 });
  const [result] = pass.results;
  assert.equal(result.status, "failed");
  assert.equal(result.stage_reached, "EVIDENCE");
  assert.match(result.reason, /E2_ABSENT/);
});
