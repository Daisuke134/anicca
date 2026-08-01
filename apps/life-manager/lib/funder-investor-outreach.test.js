"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { createHash } = require("node:crypto");

const {
  buildInvestorOutreachPlan,
  reserveInvestorOutreachPlan,
} = require("./funder-investor-outreach.js");
const { deliverFunderOutreachBatch } = require("./funder-outreach-gmail.js");
const { appendFunderOutreachReceipt } = require("./funder-outreach-store.js");

const sha = (value) => createHash("sha256").update(value, "utf8").digest("hex");
const FACTS = "Anicca is a self-funding autonomous AI entity.\nAnicca is based in Tokyo.";
const SOURCE = [
  "Scion Ventures is a San Francisco seed and pre-seed firm investing in AI and robotics.",
  "We invest at pre-seed and seed in AI, applied AI, agentic systems, robotics, computer vision, and embodied intelligence.",
  "Pitch Us. Every submission is read by a partner.",
  "hello@scion-ventures.co",
].join("\n");

const provider = Object.freeze({
  snapshot: () => ({ schema_version: 1, root_ref: "application-kit://current",
    company_facts_ref: "application-kit://KIT.md", answer_count: 20, asset_count: 6, kit_digest: sha(FACTS) }),
  readCompanyFacts: () => FACTS,
});

function candidate(overrides = {}) {
  const body = [
    "Hi Scion team,",
    "",
    "Your focus on agentic systems stood out. Anicca is a self-funding autonomous AI entity based in Tokyo.",
    "Would a 15-minute fit check next week be useful?",
    "",
    "— Dais",
    "https://aniccaai.com",
  ].join("\n");
  return {
    candidateId: "scion-ventures",
    funderName: "Scion Ventures",
    email: "hello@scion-ventures.co",
    rank: 1,
    sourceUrl: "https://scion-ventures.co/",
    sourceObservedAt: "2026-08-01T21:41:35Z",
    sourceExcerpt: SOURCE,
    sourceDigest: sha(SOURCE),
    assessment: {
      kind: "agent_judgment",
      investor_kind: "vc",
      thesis_match: true,
      summary: "Pre-seed VC explicitly investing in agentic systems; Anicca is an agentic AI company.",
      target_evidence_quotes: [
        "Scion Ventures is a San Francisco seed and pre-seed firm investing in AI and robotics.",
        "We invest at pre-seed and seed in AI, applied AI, agentic systems, robotics, computer vision, and embodied intelligence.",
      ],
      message_claims: [
        {
          claim: "Your focus on agentic systems stood out.",
          evidence_source: "target",
          evidence_quote: "We invest at pre-seed and seed in AI, applied AI, agentic systems, robotics, computer vision, and embodied intelligence.",
        },
        {
          claim: "Anicca is a self-funding autonomous AI entity",
          evidence_source: "company",
          evidence_quote: "Anicca is a self-funding autonomous AI entity.",
        },
        {
          claim: "based in Tokyo",
          evidence_source: "company",
          evidence_quote: "Anicca is based in Tokyo.",
        },
      ],
    },
    subject: "Anicca × Scion Ventures",
    body,
    ...overrides,
  };
}

const rows = (count) => Array.from({ length: count }, (_, index) => ({
  recipient_sha256: sha(`sent-${index}@example.com`),
  same_day: true,
}));

async function plan(overrides = {}, query = async () => ({ rows: rows(3) })) {
  return buildInvestorOutreachPlan({
    tenantId: "dais-local",
    tokyoDate: "2026-08-02",
    observedAt: "2026-08-01T21:45:00Z",
    dailyTarget: 4,
    candidates: [candidate()],
    applicationKitProvider: provider,
    ...overrides,
  }, {
    query,
  });
}

test("same-day total 3 selects one evidence-bound VC message for target 4", async () => {
  const result = await plan();
  assert.equal(result.schema_version, 2);
  assert.equal(result.existing_count, 3);
  assert.equal(result.messages.length, 1);
  assert.equal(result.projected_total, 4);
  assert.equal(result.messages[0].investor_kind, "vc");
  assert.match(result.messages[0].thesis_evidence_sha256, /^[0-9a-f]{64}$/);
  assert.match(result.messages[0].company_evidence_sha256, /^[0-9a-f]{64}$/);
  assert.match(result.messages[0].personalization_sha256, /^[0-9a-f]{64}$/);
});

test("day count five produces honest no-op and never exceeds the total cap", async () => {
  const alreadySent = [{ recipient_sha256: sha(candidate().email), same_day: true }, ...rows(4)];
  const result = await plan({ dailyTarget: 5 }, async () => ({ rows: alreadySent }));
  assert.equal(result.messages.length, 0);
  assert.equal(result.projected_total, 5);
});

test("accelerator, thesis mismatch, fake quotes, and unbound personalization fail closed", async () => {
  const accelerator = candidate(); accelerator.assessment.investor_kind = "accelerator";
  await assert.rejects(() => plan({ candidates: [accelerator] }), /investor outreach/i);
  const mismatch = candidate(); mismatch.assessment.thesis_match = false;
  await assert.rejects(() => plan({ candidates: [mismatch] }), /investor outreach/i);
  const fakeTarget = candidate(); fakeTarget.assessment.target_evidence_quotes[0] = "Not on the official page";
  await assert.rejects(() => plan({ candidates: [fakeTarget] }), /investor outreach/i);
  const fakeCompany = candidate(); fakeCompany.assessment.message_claims[1].evidence_quote = "Invented traction";
  await assert.rejects(() => plan({ candidates: [fakeCompany] }), /investor outreach/i);
  const unbound = candidate(); unbound.body = unbound.body.replace("Your focus on agentic systems stood out.", "Hello.");
  await assert.rejects(() => plan({ candidates: [unbound] }), /investor outreach/i);
});

test("recipient dedup and stale source fail closed", async () => {
  await assert.rejects(() => buildInvestorOutreachPlan({
    tenantId: "dais-local", tokyoDate: "2026-08-02", observedAt: "2026-08-01T21:45:00Z",
    dailyTarget: 4, candidates: [candidate()], applicationKitProvider: provider,
  }, { query: async () => ({ rows: [{ recipient_sha256: sha(candidate().email), same_day: false }, ...rows(3) ] }) }), /investor outreach/i);
  const stale = candidate({ sourceObservedAt: "2026-07-30T00:00:00Z" });
  await assert.rejects(() => plan({ candidates: [stale] }), /investor outreach/i);
});

test("company facts require the exact current kit identity and a stable before/after snapshot", async () => {
  const wrongRef = { ...provider, snapshot: () => ({ ...provider.snapshot(), company_facts_ref: "application-kit://other" }) };
  await assert.rejects(() => plan({ applicationKitProvider: wrongRef }), /investor outreach/i);
  let reads = 0;
  const drifting = { ...provider, snapshot: () => ({ ...provider.snapshot(), kit_digest: sha(`${FACTS}:${reads++}`) }) };
  await assert.rejects(() => plan({ applicationKitProvider: drifting }), /investor outreach/i);
});

test("reservation is required before a one-message schema v2 delivery", async () => {
  const result = await plan();
  await assert.rejects(() => deliverFunderOutreachBatch(result, { send: async () => ({}) }), /reservation/i);
  await assert.rejects(() => reserveInvestorOutreachPlan(JSON.parse(JSON.stringify(result)), {
    query: async () => { throw new Error("must not query"); },
  }), /investor outreach/i);
  const reserved = await reserveInvestorOutreachPlan(result, { query: async (_sql, params) => ({
    rows: [{ outreach_id: params[2], daily_slot: 4, reserved_at: "2026-08-01T21:46:00Z" }],
  }) });
  await assert.rejects(() => deliverFunderOutreachBatch(JSON.parse(JSON.stringify(reserved)), {
    send: async () => { throw new Error("must not send"); },
  }), /reservation/i);
  let downgradeSends = 0;
  const downgraded = {
    ...JSON.parse(JSON.stringify(result)),
    schema_version: 1,
    daily_target: 3,
    messages: [result.messages[0], result.messages[0], result.messages[0]],
  };
  await assert.rejects(() => deliverFunderOutreachBatch(downgraded, {
    send: async () => { downgradeSends += 1; return {}; },
  }), /delivery invalid/i);
  assert.equal(downgradeSends, 0);
  const receipts = await deliverFunderOutreachBatch(reserved, {
    send: async () => ({ message_id: "19fbe00000000019", thread_id: "19fbe00000000019" }),
    observedAt: () => "2026-08-01T21:47:00Z",
  });
  assert.equal(receipts.length, 1);
  assert.equal(receipts[0].daily_slot, 4);
  assert.equal(receipts[0].investor_kind, "vc");
});

test("investor receipt store writes proof and daily slot append-only", async () => {
  const result = await plan();
  const reserved = await reserveInvestorOutreachPlan(result, { query: async (_sql, params) => ({
    rows: [{ outreach_id: params[2], daily_slot: 4, reserved_at: "2026-08-01T21:46:00Z" }],
  }) });
  const [receipt] = await deliverFunderOutreachBatch(reserved, {
    send: async () => ({ message_id: "19fbe00000000019", thread_id: "19fbe00000000019" }),
    observedAt: () => "2026-08-01T21:47:00Z",
  });
  const calls = [];
  await appendFunderOutreachReceipt(receipt, { query: async (sql, params) => {
    calls.push({ sql, params });
    return { rows: [{ outreach_id: receipt.outreach_id, inserted: true }] };
  } });
  assert.match(calls[0].sql, /investor_kind/i);
  assert.match(calls[0].sql, /daily_slot/i);
  assert.doesNotMatch(calls[0].sql, /UPDATE/i);
  const stripped = { ...receipt, schema_version: 1 };
  delete stripped.investor_kind;
  delete stripped.thesis_evidence_sha256;
  delete stripped.company_evidence_sha256;
  delete stripped.personalization_sha256;
  delete stripped.daily_slot;
  const strippedCalls = [];
  await assert.rejects(() => appendFunderOutreachReceipt(stripped, {
    query: async (sql) => { strippedCalls.push(sql); return { rows: [] }; },
  }), /store conflict/i);
  assert.match(strippedCalls[0], /investor_kind IS NULL/i);
});
