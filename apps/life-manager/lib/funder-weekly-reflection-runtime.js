"use strict";

const {
  latestCompletedTokyoReflectionWeek,
  buildFunderWeeklyReflection,
} = require("./funder-weekly-reflection.js");

const LEARNABLE = new Set([
  "reply_received", "rejected", "meeting_requested", "offer_received", "funded",
]);
const GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent";

function targetReflectionWeek(value, latestWeekKey) {
  const ms = Date.parse(String(value || ""));
  if (!Number.isFinite(ms)) throw new Error("funder weekly reflection runtime invalid");
  const completed = latestCompletedTokyoReflectionWeek(new Date(ms).toISOString());
  if (!latestWeekKey) return completed;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(latestWeekKey)) {
    throw new Error("funder weekly reflection runtime invalid");
  }
  const nextStart = Date.parse(`${latestWeekKey}T00:00:00+09:00`) + (7 * 86_400_000);
  const next = require("./funder-weekly-reflection.js").tokyoReflectionWeek(
    new Date(nextStart).toISOString(),
  );
  return Date.parse(next.week_end) <= ms ? next : completed;
}

function isFunderWeeklyReflectionDue(value, latestWeekKey) {
  const ms = Date.parse(String(value || ""));
  if (!Number.isFinite(ms)) throw new Error("funder weekly reflection runtime invalid");
  const week = targetReflectionWeek(new Date(ms).toISOString(), latestWeekKey);
  return ms >= Date.parse(week.week_end) && latestWeekKey !== week.week_key;
}

async function runFunderWeeklyReflection(input = {}, dependencies = {}) {
  const tenantId = String(input.tenantId || "").trim();
  const reflectedAt = new Date(Date.parse(String(input.reflectedAt || ""))).toISOString();
  const week = targetReflectionWeek(reflectedAt, input.latestWeekKey || null);
  if (!tenantId) throw new Error("funder weekly reflection runtime invalid");
  if (input.force !== true && !isFunderWeeklyReflectionDue(reflectedAt, input.latestWeekKey || null)) {
    return Object.freeze({ status: "skipped", reason: "not_due", week_key: week.week_key,
      week_end: week.week_end });
  }
  if (typeof dependencies.collectSnapshot !== "function"
    || typeof dependencies.append !== "function") {
    throw new Error("funder weekly reflection runtime dependencies invalid");
  }
  const snapshot = await dependencies.collectSnapshot({
    tenantId,
    ...week,
    ...(Array.isArray(input.candidateIds) ? { candidateIds: input.candidateIds } : {}),
  });
  if (!snapshot || !Array.isArray(snapshot.exposures) || !Array.isArray(snapshot.results)
    || !Array.isArray(snapshot.candidates)) {
    throw new Error("funder weekly reflection snapshot invalid");
  }
  const learnable = snapshot.results.filter((item) => LEARNABLE.has(item.status));
  let judgment;
  if (learnable.length > 0) {
    if (snapshot.candidates.length < 1) {
      throw new Error("funder weekly reflection current planner candidates unavailable");
    }
    if (typeof dependencies.judge !== "function") {
      throw new Error("funder weekly reflection agent provider unavailable");
    }
    judgment = await dependencies.judge(Object.freeze({
      schema_version: 1,
      tenant_id: tenantId,
      week_key: week.week_key,
      week_start: week.week_start,
      week_end: week.week_end,
      exposures: snapshot.exposures,
      results: learnable,
      candidates: snapshot.candidates,
    }));
  }
  const reflection = buildFunderWeeklyReflection({
    tenantId,
    reflectedAt,
    week,
    exposures: snapshot.exposures,
    results: snapshot.results,
    candidates: snapshot.candidates,
    ...(judgment === undefined ? {} : { judgment }),
  });
  const stored = await dependencies.append(reflection);
  if (!stored || stored.reflection_id !== reflection.reflection_id
    || typeof stored.inserted !== "boolean") {
    throw new Error("funder weekly reflection append receipt invalid");
  }
  return Object.freeze({
    status: stored.inserted ? "recorded" : "duplicate",
    reflection_id: reflection.reflection_id,
    week_key: reflection.week_key,
    week_end: reflection.week_end,
    decision: reflection.decision,
    reason: reflection.reason,
    outcome_count: reflection.outcome_result_ids.length,
  });
}

async function materializeFunderReflectionForInvestorCandidates(input = {}, dependencies = {}) {
  if (typeof dependencies.query !== "function" || typeof dependencies.collectSnapshot !== "function"
    || typeof dependencies.append !== "function") {
    throw new Error("funder weekly reflection materializer invalid");
  }
  const latest = await dependencies.query(`
    SELECT week_key::text FROM public.lm_funder_weekly_reflection_ledger
    WHERE tenant_id=$1 ORDER BY week_key DESC LIMIT 1
  `, [input.tenantId]);
  if (!latest || !Array.isArray(latest.rows) || latest.rows.length > 1) {
    throw new Error("funder weekly reflection materializer invalid");
  }
  let latestWeekKey = latest.rows[0] ? latest.rows[0].week_key : null;
  let output;
  for (let index = 0; index < 520; index += 1) {
    output = await runFunderWeeklyReflection({
      tenantId: input.tenantId,
      reflectedAt: input.reflectedAt,
      latestWeekKey,
      candidateIds: input.candidateIds,
    }, dependencies);
    if (output.status === "skipped") return output;
    latestWeekKey = output.week_key;
  }
  throw new Error("funder weekly reflection backlog exceeds safety limit");
}

function createFunderReflectionMaterializer(options = {}) {
  if (typeof options.query !== "function") {
    throw new Error("funder weekly reflection materializer invalid");
  }
  const { collectFunderWeeklyReflectionSnapshot } = require("./funder-weekly-reflection-snapshot.js");
  const { appendFunderWeeklyReflection } = require("./funder-weekly-reflection-store.js");
  return (input) => materializeFunderReflectionForInvestorCandidates(input, {
    query: options.query,
    collectSnapshot: (request) => collectFunderWeeklyReflectionSnapshot(request, { query: options.query }),
    judge: (snapshot) => requestGeminiFunderReflection(snapshot, {
      apiKey: options.apiKey,
      fetchImpl: options.fetchImpl,
    }),
    append: (value) => appendFunderWeeklyReflection(value, { query: options.query }),
  });
}

async function requestGeminiFunderReflection(snapshot, options = {}) {
  const apiKey = String(options.apiKey || "").trim();
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  if (!apiKey || typeof fetchImpl !== "function") {
    throw new Error("funder weekly reflection agent provider unavailable");
  }
  const response = await fetchImpl(GEMINI, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-goog-api-key": apiKey },
    body: JSON.stringify({
      contents: [{ role: "user", parts: [{ text: [
        "You are the Life Manager fundraising reflection agent.",
        "Return JSON only. The results array contains only learnable reply/meeting/rejection/offer/funded outcomes.",
        "Use every result_id in that array exactly once in used_result_ids; do not add confirmation or delivery IDs.",
        "Decide hold or change. For change, rank every candidate exactly once and give every candidate",
        "one exact natural English sentence that must be copied into its next pitch, grounded in one or more result IDs.",
        "Every directive must be one line, no more than 24 whitespace-delimited words, and no more than 240 characters.",
        "Never infer an outcome absent from the typed snapshot.",
        JSON.stringify(snapshot),
      ].join("\n") }] }],
      generationConfig: { responseMimeType: "application/json", temperature: 0 },
    }),
    signal: AbortSignal.timeout(30_000),
  });
  if (!response || response.ok !== true) throw new Error("funder weekly reflection agent provider failed");
  const payload = await response.json();
  const text = payload && payload.candidates && payload.candidates[0]
    && payload.candidates[0].content && payload.candidates[0].content.parts
    && payload.candidates[0].content.parts[0] && payload.candidates[0].content.parts[0].text;
  try { return JSON.parse(String(text || "")); } catch {
    throw new Error("funder weekly reflection agent response invalid");
  }
}

module.exports = {
  isFunderWeeklyReflectionDue,
  targetReflectionWeek,
  runFunderWeeklyReflection,
  requestGeminiFunderReflection,
  materializeFunderReflectionForInvestorCandidates,
  createFunderReflectionMaterializer,
};
