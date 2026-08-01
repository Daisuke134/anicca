"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  isFunderWeeklyReflectionDue,
  targetReflectionWeek,
  runFunderWeeklyReflection,
  materializeFunderReflectionForInvestorCandidates,
  requestGeminiFunderReflection,
} = require("./funder-weekly-reflection-runtime.js");

const SUNDAY_2014 = "2026-08-02T11:14:59.000Z";
const SUNDAY_2015 = "2026-08-02T11:15:00.000Z";

function snapshot(results = []) {
  return {
    exposures: [{
      exposure_id: "funder-outreach:alpha",
      candidate_id: "alpha",
      exposure_kind: "outreach",
      occurred_at: "2026-07-28T01:00:00.000Z",
      subject_sha256: "a".repeat(64),
      body_sha256: "b".repeat(64),
    }],
    results,
    candidates: ["alpha"],
  };
}

test("weekly reflection becomes due Sunday 20:15 JST exactly once per week", () => {
  assert.equal(isFunderWeeklyReflectionDue(SUNDAY_2014, "2026-07-20"), false);
  assert.equal(isFunderWeeklyReflectionDue(SUNDAY_2015, null), true);
  assert.equal(isFunderWeeklyReflectionDue("2026-08-02T14:59:59.000Z", null), true);
  assert.equal(isFunderWeeklyReflectionDue("2026-08-02T12:00:00.000Z", "2026-07-27"), false);
  assert.equal(isFunderWeeklyReflectionDue("2026-08-03T00:00:00.000Z", null), true);
  assert.equal(isFunderWeeklyReflectionDue("2026-08-03T00:00:00.000Z", "2026-07-27"), false);
});

test("zero outcomes skips the model and appends an insufficient-outcomes hold", async () => {
  let judged = 0;
  let appended;
  const result = await runFunderWeeklyReflection({
    tenantId: "dais-local",
    reflectedAt: "2026-08-02T12:00:00.000Z",
    latestWeekKey: null,
  }, {
    collectSnapshot: async () => snapshot(),
    judge: async () => { judged += 1; },
    append: async (value) => { appended = value; return { reflection_id: value.reflection_id, inserted: true }; },
  });
  assert.equal(judged, 0);
  assert.equal(appended.reason, "insufficient_outcomes");
  assert.equal(result.status, "recorded");
  assert.equal(result.decision, "hold");
});

test("learnable outcome requires agent judgment and never waits for a human", async () => {
  const resultRow = {
    result_id: "funder-result:meeting",
    exposure_id: "funder-outreach:alpha",
    candidate_id: "alpha",
    status: "meeting_requested",
    observed_at: "2026-07-31T02:00:00.000Z",
  };
  await assert.rejects(() => runFunderWeeklyReflection({
    tenantId: "dais-local", reflectedAt: "2026-08-02T12:00:00.000Z", latestWeekKey: null,
  }, {
    collectSnapshot: async () => snapshot([resultRow]),
    append: async () => { throw new Error("must not append"); },
  }), /agent provider/i);

  const output = await runFunderWeeklyReflection({
    tenantId: "dais-local", reflectedAt: "2026-08-02T12:00:00.000Z", latestWeekKey: null,
  }, {
    collectSnapshot: async () => snapshot([resultRow]),
    judge: async () => ({
      kind: "agent_judgment",
      decision: "change",
      summary: "The meeting request is a positive fit signal.",
      rationale: "Keep alpha first and lead with the workflow that produced the meeting.",
      used_result_ids: [resultRow.result_id],
      ranked_candidate_ids: ["alpha"],
      pitch_directives: [{
        candidate_id: "alpha",
        directive: "Lead with the verified workflow and ask for a 15-minute fit call.",
        outcome_result_ids: [resultRow.result_id],
      }],
    }),
    append: async (value) => ({ reflection_id: value.reflection_id, inserted: true }),
  });
  assert.equal(output.decision, "change");
});

test("not-due run is a deterministic no-op", async () => {
  const output = await runFunderWeeklyReflection({
    tenantId: "dais-local", reflectedAt: SUNDAY_2014, latestWeekKey: "2026-07-20",
  }, {
    collectSnapshot: async () => { throw new Error("must not read"); },
  });
  assert.deepEqual(output, {
    status: "skipped", reason: "not_due", week_key: "2026-07-20",
    week_end: "2026-07-26T11:15:00.000Z",
  });
});

test("downtime backlog advances one oldest missing week at a time", () => {
  assert.equal(targetReflectionWeek("2026-08-17T01:00:00.000Z", "2026-07-27").week_key, "2026-08-03");
  assert.equal(targetReflectionWeek("2026-08-17T01:00:00.000Z", "2026-08-03").week_key, "2026-08-10");
});

test("candidate materializer catches up every missing week with the exact planner IDs", async () => {
  const collected = [];
  const appended = [];
  const output = await materializeFunderReflectionForInvestorCandidates({
    tenantId: "dais-local",
    reflectedAt: "2026-08-17T01:00:00.000Z",
    candidateIds: ["alpha"],
  }, {
    query: async () => ({ rows: [{ week_key: "2026-07-27" }] }),
    collectSnapshot: async (request) => {
      collected.push(request);
      return { exposures: [], results: [], candidates: [...request.candidateIds] };
    },
    append: async (value) => {
      appended.push(value.week_key);
      return { reflection_id: value.reflection_id, inserted: true };
    },
  });
  assert.deepEqual(appended, ["2026-08-03", "2026-08-10"]);
  assert.deepEqual(collected.map((item) => item.candidateIds), [["alpha"], ["alpha"]]);
  assert.equal(output.status, "skipped");
  assert.equal(output.week_key, "2026-08-10");
});

test("backlog preserves a strategy change even when later missing weeks are holds", async () => {
  const decisions = [];
  let reads = 0;
  const resultRow = {
    result_id: "funder-result:late-meeting", exposure_id: "funder-outreach:alpha",
    candidate_id: "alpha", status: "meeting_requested", observed_at: "2026-08-01T02:00:00.000Z",
  };
  await materializeFunderReflectionForInvestorCandidates({
    tenantId: "dais-local", reflectedAt: "2026-08-17T01:00:00.000Z", candidateIds: ["alpha"],
  }, {
    query: async () => ({ rows: [{ week_key: "2026-07-27" }] }),
    collectSnapshot: async () => snapshot(reads++ === 0 ? [resultRow] : []),
    judge: async () => ({
      kind: "agent_judgment", decision: "change", summary: "A meeting was requested.",
      rationale: "Apply the verified workflow to the next pitch.",
      used_result_ids: [resultRow.result_id], ranked_candidate_ids: ["alpha"],
      pitch_directives: [{ candidate_id: "alpha", directive: "Lead with the verified workflow.",
        outcome_result_ids: [resultRow.result_id] }],
    }),
    append: async (value) => {
      decisions.push([value.week_key, value.decision]);
      return { reflection_id: value.reflection_id, inserted: true };
    },
  });
  assert.deepEqual(decisions, [["2026-08-03", "change"], ["2026-08-10", "hold"]]);
});

test("Gemini contract states the exact directive limits before deterministic validation", async () => {
  let requestBody;
  const response = await requestGeminiFunderReflection({ candidates: ["alpha"], results: [] }, {
    apiKey: "test-key",
    fetchImpl: async (_url, request) => {
      requestBody = JSON.parse(request.body);
      return { ok: true, json: async () => ({ candidates: [{ content: { parts: [{ text: "{}" }] } }] }) };
    },
  });
  assert.deepEqual(response, {});
  const prompt = requestBody.contents[0].parts[0].text;
  assert.match(prompt, /one line/i);
  assert.match(prompt, /24 whitespace-delimited words/i);
  assert.match(prompt, /240 characters/i);
});
