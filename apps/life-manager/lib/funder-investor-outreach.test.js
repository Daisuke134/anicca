"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const { createHash } = require("node:crypto");

const {
  buildInvestorOutreachPlan,
  buildAutonomousInvestorOutreachPlan,
  reserveInvestorOutreachPlan,
} = require("./funder-investor-outreach.js");
const { deliverFunderOutreachBatch } = require("./funder-outreach-gmail.js");
const { appendFunderOutreachReceipt } = require("./funder-outreach-store.js");
const { buildFunderWeeklyReflection } = require("./funder-weekly-reflection.js");

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
    ensureWeeklyReflection: async () => ({ status: "skipped", reason: "not_due", week_key: "2026-07-27" }),
    loadLatestReflection: async () => null,
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

test("production planner wires candidate materialization before the inclusive reflection load", async () => {
  const calls = [];
  const result = await buildAutonomousInvestorOutreachPlan({
    tenantId: "dais-local", tokyoDate: "2026-08-03", observedAt: "2026-08-03T01:00:00.000Z",
    dailyTarget: 4, candidates: [candidate({ sourceObservedAt: "2026-08-03T00:30:00.000Z" })],
    applicationKitProvider: provider,
  }, { query: async (sql) => {
    calls.push(sql);
    if (/SELECT recipient_sha256/.test(sql)) return { rows: rows(3) };
    if (/SELECT week_key::text/.test(sql)) return { rows: [{ week_key: "2026-07-27" }] };
    if (/SELECT 1 AS schema_version/.test(sql)) return { rows: [] };
    throw new Error(`unexpected query: ${sql}`);
  } });
  assert.equal(result.messages.length, 1);
  assert.ok(calls.findIndex((sql) => /SELECT week_key::text/.test(sql))
    < calls.findIndex((sql) => /SELECT 1 AS schema_version/.test(sql)));
  assert.match(calls.find((sql) => /SELECT 1 AS schema_version/.test(sql)), /reflected_at <=/);
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
  }, {
    query: async () => ({ rows: [{ recipient_sha256: sha(candidate().email), same_day: false }, ...rows(3) ] }),
    ensureWeeklyReflection: async () => ({ status: "skipped", week_key: "2026-07-27" }),
    loadLatestReflection: async () => null,
  }), /investor outreach/i);
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

function changedReflection() {
  return buildFunderWeeklyReflection({
    tenantId: "dais-local",
    reflectedAt: "2026-08-02T12:00:00.000Z",
    exposures: [{
      exposure_id: "funder-outreach:prior",
      candidate_id: "prior-target",
      exposure_kind: "outreach",
      occurred_at: "2026-07-28T01:00:00.000Z",
      subject_sha256: "a".repeat(64),
      body_sha256: "b".repeat(64),
    }],
    results: [{
      result_id: "funder-result:meeting",
      exposure_id: "funder-outreach:prior",
      candidate_id: "prior-target",
      status: "meeting_requested",
      observed_at: "2026-07-31T02:00:00.000Z",
    }],
    candidates: ["scion-ventures"],
    judgment: {
      kind: "agent_judgment",
      decision: "change",
      summary: "The workflow-specific pitch produced a meeting request.",
      rationale: "Keep Scion first and carry the exact workflow sentence into the next pitch.",
      used_result_ids: ["funder-result:meeting"],
      ranked_candidate_ids: ["scion-ventures"],
      pitch_directives: [{
        candidate_id: "scion-ventures",
        directive: "Our autonomous workflow already runs verified work loops for users.",
        outcome_result_ids: ["funder-result:meeting"],
      }],
    },
  });
}

test("verified weekly revision is enforced in the next target rank and pitch body", async () => {
  const reflection = changedReflection();
  const item = candidate({
    sourceObservedAt: "2026-08-03T00:30:00.000Z",
  });
  const order = [];
  const result = await buildInvestorOutreachPlan({
    tenantId: "dais-local",
    tokyoDate: "2026-08-03",
    observedAt: "2026-08-03T01:00:00.000Z",
    dailyTarget: 3,
    candidates: [item],
    applicationKitProvider: provider,
  }, {
    query: async () => ({ rows: rows(2) }),
    ensureWeeklyReflection: async (request) => {
      order.push("materialize");
      assert.deepEqual(request.candidateIds, ["scion-ventures"]);
      return { status: "recorded", week_key: "2026-07-27" };
    },
    loadLatestReflection: async () => { order.push("load"); return reflection; },
  });
  assert.deepEqual(order, ["materialize", "load"]);
  assert.equal(result.reflection_id, reflection.reflection_id);
  assert.equal(result.messages[0].reflection_id, reflection.reflection_id);
  assert.equal(result.messages[0].ranking_position, 1);
  assert.equal(result.messages[0].pitch_directive_sha256, sha(reflection.pitch_directives[0].directive));
  assert.match(result.messages[0].body, new RegExp(reflection.pitch_directives[0].directive));
});

test("planner fails closed when weekly materialization has no verified completion receipt", async () => {
  await assert.rejects(() => buildInvestorOutreachPlan({
    tenantId: "dais-local", tokyoDate: "2026-08-02", observedAt: "2026-08-01T21:45:00Z",
    dailyTarget: 4, candidates: [candidate()], applicationKitProvider: provider,
  }, {
    query: async () => ({ rows: rows(3) }),
    ensureWeeklyReflection: async () => ({ status: "pending_human", week_key: "2026-07-27" }),
    loadLatestReflection: async () => { throw new Error("must not load"); },
  }), /investor outreach/i);
});

test("plain-object reflection forgery is rejected before outreach", async () => {
  const forged = JSON.parse(JSON.stringify(changedReflection()));
  await assert.rejects(() => buildInvestorOutreachPlan({
    tenantId: "dais-local", tokyoDate: "2026-08-03", observedAt: "2026-08-03T01:00:00.000Z",
    dailyTarget: 3, candidates: [candidate({ sourceObservedAt: "2026-08-03T00:30:00.000Z" })],
    applicationKitProvider: provider,
  }, {
    query: async () => ({ rows: rows(2) }),
    ensureWeeklyReflection: async () => ({ status: "duplicate", week_key: "2026-07-27" }),
    loadLatestReflection: async () => forged,
  }), /investor outreach/i);
});

test("reflection application survives reservation and delivery into an append-only linked receipt", async () => {
  const reflection = changedReflection();
  const directive = reflection.pitch_directives[0].directive;
  const item = candidate({
    sourceObservedAt: "2026-08-03T00:30:00.000Z",
    body: candidate().body.replace("Would a 15-minute fit check next week be useful?", `${directive} Would a 15-minute fit check next week be useful?`),
    reflectionApplication: {
      reflection_id: reflection.reflection_id,
      ranking_position: 1,
      pitch_directive: directive,
      outcome_result_ids: ["funder-result:meeting"],
    },
  });
  const built = await buildInvestorOutreachPlan({
    tenantId: "dais-local", tokyoDate: "2026-08-03", observedAt: "2026-08-03T01:00:00.000Z",
    dailyTarget: 3, candidates: [item], applicationKitProvider: provider,
  }, {
    query: async () => ({ rows: rows(2) }),
    ensureWeeklyReflection: async () => ({ status: "duplicate", week_key: "2026-07-27" }),
    loadLatestReflection: async () => reflection,
  });
  const reserved = await reserveInvestorOutreachPlan(built, { query: async (_sql, params) => ({
    rows: [{ outreach_id: params[2], daily_slot: 3, reserved_at: "2026-08-03T01:01:00.000Z" }],
  }) });
  const [receipt] = await deliverFunderOutreachBatch(reserved, {
    send: async () => ({ message_id: "19fbe00000000020", thread_id: "19fbe00000000020" }),
    observedAt: () => "2026-08-03T01:02:00.000Z",
  });
  assert.equal(receipt.reflection_id, reflection.reflection_id);
  assert.equal(receipt.ranking_position, 1);
  assert.equal(receipt.pitch_directive_sha256, sha(directive));
  const calls = [];
  await appendFunderOutreachReceipt(receipt, { query: async (sql) => {
    calls.push(sql);
    return { rows: [{ outreach_id: receipt.outreach_id, inserted: true }] };
  } });
  assert.match(calls[0], /lm_funder_outreach_reflection_application/i);
  assert.doesNotMatch(calls[0], /UPDATE/i);
  await assert.rejects(() => appendFunderOutreachReceipt(JSON.parse(JSON.stringify(receipt)), {
    query: async () => { throw new Error("must not query"); },
  }), /store invalid/i);
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

test("a reserved plan expires before the next weekly cutoff and sends nothing", async () => {
  const result = await plan();
  assert.equal(result.strategy_valid_until, "2026-08-02T11:10:00.000Z");
  const reserved = await reserveInvestorOutreachPlan(result, { query: async (_sql, params) => ({
    rows: [{ outreach_id: params[2], daily_slot: 4, reserved_at: "2026-08-02T11:09:00Z" }],
  }) });
  let sends = 0;
  await assert.rejects(() => deliverFunderOutreachBatch(reserved, {
    send: async () => { sends += 1; return {}; },
    observedAt: () => "2026-08-02T11:10:00.000Z",
  }), /strategy expired/i);
  assert.equal(sends, 0);
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
  await assert.rejects(() => appendFunderOutreachReceipt(JSON.parse(JSON.stringify(receipt)), {
    query: async () => { throw new Error("must not query"); },
  }), /store invalid/i);
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
