// lib/outbound-pipeline.test.js — the 6-stage pipeline (spec §3.1).
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const PIPELINE_URL = pathToFileURL(
  path.join(__dirname, "..", "..", "..", "runtime", "loop", "outbound", "pipeline.mjs"),
).href;

const loadPipeline = () => import(PIPELINE_URL);

const ok = (data) => async () => ({ ok: true, ...(data || {}) });

function recordingStages(calls, overrides = {}) {
  const stage = (name, impl) => async (context) => {
    calls.push(name);
    return impl ? impl(context) : { ok: true };
  };
  return {
    discover: stage("DISCOVER", overrides.discover || (async () => ({ ok: true, candidates: ["target-a"] }))),
    qualify: stage("QUALIFY", overrides.qualify),
    act: stage("ACT", overrides.act),
    evidence: stage("EVIDENCE", overrides.evidence),
    track: stage("TRACK", overrides.track),
    learn: stage("LEARN", overrides.learn),
  };
}

test("pipeline runs the six stages in order and reports verified", async () => {
  const { runPipeline, STAGES } = await loadPipeline();
  assert.deepEqual([...STAGES], ["DISCOVER", "QUALIFY", "ACT", "EVIDENCE", "TRACK", "LEARN"]);
  const calls = [];
  const result = await runPipeline({
    pack: "events",
    stages: recordingStages(calls),
    nowMs: Date.parse("2026-07-31T07:30:00Z"),
  });
  assert.deepEqual(calls, ["DISCOVER", "QUALIFY", "ACT", "EVIDENCE", "TRACK", "LEARN"]);
  assert.equal(result.results.length, 1);
  const [first] = result.results;
  assert.equal(first.pack, "events");
  assert.equal(first.target, "target-a");
  assert.equal(first.stage_reached, "LEARN");
  assert.equal(first.status, "verified");
  assert.equal(first.reason, null);
  assert.equal(first.ts, "2026-07-31T07:30:00.000Z");
});

test("pipeline stops at the first failing stage and never runs the rest", async () => {
  const { runPipeline } = await loadPipeline();
  const calls = [];
  const result = await runPipeline({
    pack: "funders",
    stages: recordingStages(calls, {
      act: async () => ({ ok: false, reason: "form_rejected_the_submission" }),
    }),
    nowMs: 0,
  });
  assert.deepEqual(calls, ["DISCOVER", "QUALIFY", "ACT"]);
  const [first] = result.results;
  assert.equal(first.stage_reached, "ACT");
  assert.equal(first.status, "failed");
  assert.equal(first.reason, "form_rejected_the_submission");
});

test("pipeline stops when the evidence gate refuses, even though ACT claimed success", async () => {
  const { runPipeline } = await loadPipeline();
  const calls = [];
  const result = await runPipeline({
    pack: "events",
    stages: recordingStages(calls, {
      act: ok({ data: { submitted: true } }),
      evidence: async () => ({ ok: false, reason: "E2_ABSENT" }),
    }),
    nowMs: 0,
  });
  assert.deepEqual(calls, ["DISCOVER", "QUALIFY", "ACT", "EVIDENCE"]);
  assert.equal(result.results[0].status, "failed");
  assert.equal(result.results[0].reason, "E2_ABSENT");
  assert.equal(result.results[0].stage_reached, "EVIDENCE");
});

test("a failing DISCOVER produces one candidate-less failed result", async () => {
  const { runPipeline } = await loadPipeline();
  const calls = [];
  const result = await runPipeline({
    pack: "jobs",
    stages: recordingStages(calls, {
      discover: async () => ({ ok: false, reason: "source_login_expired" }),
    }),
    nowMs: 0,
  });
  assert.deepEqual(calls, ["DISCOVER"]);
  assert.deepEqual(result.results, [{
    pack: "jobs",
    target: null,
    stage_reached: "DISCOVER",
    status: "failed",
    reason: "source_login_expired",
    evidence: null,
    ts: "1970-01-01T00:00:00.000Z",
  }]);
});

test("a stage that throws becomes a failed result, not an unhandled rejection", async () => {
  const { runPipeline } = await loadPipeline();
  const calls = [];
  const result = await runPipeline({
    pack: "events",
    stages: recordingStages(calls, {
      qualify: async () => { throw new Error("llm timed out"); },
    }),
    nowMs: 0,
  });
  assert.equal(result.results[0].status, "failed");
  assert.equal(result.results[0].stage_reached, "QUALIFY");
  assert.match(result.results[0].reason, /qualify_threw: llm timed out/);
});

test("each candidate is judged independently; one failure does not sink the others", async () => {
  const { runPipeline } = await loadPipeline();
  const result = await runPipeline({
    pack: "events",
    stages: {
      discover: async () => ({ ok: true, candidates: ["a", "b", "c"] }),
      qualify: async ({ target }) => (target === "b"
        ? { ok: false, reason: "denylisted_operator" }
        : { ok: true }),
      act: ok(),
      evidence: async ({ target }) => ({ ok: true, evidence: { e1: { kind: "ticket", ticket_id: target } } }),
      track: ok(),
      learn: ok(),
    },
    nowMs: 0,
  });
  assert.deepEqual(result.results.map((r) => r.status), ["verified", "failed", "verified"]);
  assert.deepEqual(result.results.map((r) => r.stage_reached), ["LEARN", "QUALIFY", "LEARN"]);
  assert.deepEqual(result.results[0].evidence, { e1: { kind: "ticket", ticket_id: "a" } });
  assert.equal(result.results[1].evidence, null);
});

test("pipeline refuses to run with a stage missing rather than silently skipping it", async () => {
  const { runPipeline } = await loadPipeline();
  await assert.rejects(
    () => runPipeline({ pack: "events", stages: { discover: ok({ candidates: [] }) }, nowMs: 0 }),
    /outbound pipeline is missing the QUALIFY stage/,
  );
});

test("pipeline does not mutate the stage map or the candidate list it was given", async () => {
  const { runPipeline } = await loadPipeline();
  const candidates = ["a"];
  const stages = {
    discover: async () => ({ ok: true, candidates }),
    qualify: ok(),
    act: ok(),
    evidence: ok(),
    track: ok(),
    learn: ok(),
  };
  const before = Object.keys(stages).join(",");
  await runPipeline({ pack: "events", stages, nowMs: 0 });
  assert.equal(Object.keys(stages).join(","), before);
  assert.deepEqual(candidates, ["a"]);
});

test("pipeline reports zero results when DISCOVER honestly finds nothing", async () => {
  const { runPipeline } = await loadPipeline();
  const result = await runPipeline({
    pack: "events",
    stages: {
      discover: async () => ({ ok: true, candidates: [] }),
      qualify: ok(), act: ok(), evidence: ok(), track: ok(), learn: ok(),
    },
    nowMs: 0,
  });
  assert.deepEqual(result.results, []);
  assert.equal(result.pack, "events");
});
