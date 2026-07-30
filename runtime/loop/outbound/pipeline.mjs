// runtime/loop/outbound/pipeline.mjs — the single 6-stage outbound pipeline (spec §3.1).
//
//   DISCOVER → QUALIFY → ACT → EVIDENCE → TRACK → LEARN
//
// There are not three agents. There is ONE engine and three config packs (events / funders /
// jobs). Every stage is an injected async function, so a pack supplies real providers and a test
// supplies fakes — the ordering, the stop-on-first-failure rule and the result shape are the only
// things this file owns.
//
// PURE LOGIC ONLY. No fetch, no fs, no clock (the caller passes nowMs), no logging. Everything
// that touches the world lives in the injected stages.
//
// Stage contract:
//   DISCOVER  async ({pack, config})                 -> {ok, candidates: [...], reason?}
//   others    async ({pack, config, target, prior})  -> {ok, reason?, data?, evidence?}
//
// Result per candidate (spec §3.1 / §6):
//   {pack, target, stage_reached, status: "verified"|"failed", reason, evidence, ts}

export const STAGES = Object.freeze(["DISCOVER", "QUALIFY", "ACT", "EVIDENCE", "TRACK", "LEARN"]);

const CANDIDATE_STAGES = Object.freeze(STAGES.slice(1));

const stageKey = (stage) => stage.toLowerCase();

function assertStages(stages) {
  const map = stages && typeof stages === "object" ? stages : {};
  for (const stage of STAGES) {
    if (typeof map[stageKey(stage)] !== "function") {
      throw new Error(`outbound pipeline is missing the ${stage} stage`);
    }
  }
  return map;
}

function result({ pack, target, stage, status, reason, evidence, ts }) {
  return Object.freeze({
    pack,
    target,
    stage_reached: stage,
    status,
    reason: reason == null ? null : String(reason),
    evidence: evidence == null ? null : evidence,
    ts,
  });
}

async function runCandidate({ pack, config, target, stages, ts }) {
  // `prior` accumulates each stage's data immutably so later stages can read earlier output
  // without any stage being able to reach back and edit what already happened.
  let prior = Object.freeze({});
  let evidence = null;
  for (const stage of CANDIDATE_STAGES) {
    let outcome;
    try {
      outcome = await stages[stageKey(stage)](Object.freeze({ pack, config, target, prior, stage }));
    } catch (error) {
      const message = error && error.message ? error.message : String(error);
      return result({
        pack, target, stage, status: "failed", reason: `${stageKey(stage)}_threw: ${message}`, evidence, ts,
      });
    }
    if (outcome && outcome.evidence != null) evidence = outcome.evidence;
    if (!outcome || outcome.ok !== true) {
      return result({
        pack,
        target,
        stage,
        status: "failed",
        reason: (outcome && outcome.reason) || `${stageKey(stage)}_returned_no_ok`,
        evidence,
        ts,
      });
    }
    prior = Object.freeze({ ...prior, [stageKey(stage)]: outcome.data == null ? null : outcome.data });
  }
  return result({
    pack, target, stage: STAGES[STAGES.length - 1], status: "verified", reason: null, evidence, ts,
  });
}

/**
 * Run one outbound pass for one pack.
 * @param {{pack: string, config?: object, stages: object, nowMs: number}} request
 * @returns {Promise<{pack: string, ts: string, results: ReadonlyArray<object>}>}
 */
export async function runPipeline(request = {}) {
  const pack = String(request.pack == null ? "" : request.pack);
  if (!pack) throw new Error("outbound pipeline needs a pack name");
  const nowMs = Number(request.nowMs);
  if (!Number.isFinite(nowMs)) throw new Error("outbound pipeline needs nowMs as an instant");
  const ts = new Date(nowMs).toISOString();
  const config = request.config == null ? {} : request.config;
  const stages = assertStages(request.stages);

  let discovered;
  try {
    discovered = await stages.discover(Object.freeze({ pack, config, stage: "DISCOVER" }));
  } catch (error) {
    const message = error && error.message ? error.message : String(error);
    return Object.freeze({
      pack,
      ts,
      results: Object.freeze([result({
        pack, target: null, stage: "DISCOVER", status: "failed", reason: `discover_threw: ${message}`, evidence: null, ts,
      })]),
    });
  }
  if (!discovered || discovered.ok !== true) {
    return Object.freeze({
      pack,
      ts,
      results: Object.freeze([result({
        pack,
        target: null,
        stage: "DISCOVER",
        status: "failed",
        reason: (discovered && discovered.reason) || "discover_returned_no_ok",
        evidence: null,
        ts,
      })]),
    });
  }

  const candidates = Array.isArray(discovered.candidates) ? [...discovered.candidates] : [];
  const results = [];
  for (const target of candidates) {
    results.push(await runCandidate({ pack, config, target, stages, ts }));
  }
  return Object.freeze({ pack, ts, results: Object.freeze(results) });
}
