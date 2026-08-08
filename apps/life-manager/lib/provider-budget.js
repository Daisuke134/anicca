"use strict";

const crypto = require("node:crypto");

const DEFAULT_THRESHOLDS = Object.freeze({
  warningUsd: 0.5,
  degradedUsd: 1,
  stoppedUsd: 2,
  voiceUserCapUsd: 1,
  voiceGlobalCapUsd: 5,
});

function finiteUsd(value) {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : 0;
}

function countUnknown(value) {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? Math.floor(number) : 0;
}

function isVoiceOperation(provider, operation) {
  const p = String(provider || "").toLowerCase();
  const o = String(operation || "").toLowerCase();
  return p === "telnyx" || p === "gemini" || o.includes("voice") || o.includes("call") || o === "session";
}

function isClaimableProvider(provider) {
  // Transit is the explicitly free path. All other provider operations that
  // leave the process receive an idempotent projected-spend claim.
  return String(provider || "").toLowerCase() !== "transit";
}

function projectedFor(input = {}) {
  const explicit = Number(input.projectedUsd);
  if (Number.isFinite(explicit) && explicit > 0) return explicit;
  const provider = String(input.provider || "").toLowerCase();
  if (provider === "telnyx") return 0.05;
  if (provider === "gemini") return 0.023;
  if (provider === "google") return input.operation === "geocoding" ? 0.005 : 0.01;
  if (provider === "composio") return 0.01;
  if (provider === "resend") return 0.001;
  return 0;
}

function attemptRequestId(input = {}) {
  if (input.requestId != null && String(input.requestId).trim()) return String(input.requestId);
  return `${String(input.provider || "provider")}:${String(input.operation || "operation")}:${Date.now()}:${crypto.randomUUID()}`;
}

function thresholdsFor(input = {}, explicit) {
  return { ...DEFAULT_THRESHOLDS, ...(input.thresholds || {}), ...(explicit || {}) };
}

function evaluateProviderBudget(input = {}, explicitThresholds) {
  const thresholds = thresholdsFor(input, explicitThresholds);
  const measuredUsd = finiteUsd(input.measuredUsd);
  const estimatedUsd = finiteUsd(input.estimatedUsd);
  const totalUsd = Number((measuredUsd + estimatedUsd).toFixed(12));
  let state = "normal";
  if (totalUsd >= Number(thresholds.stoppedUsd)) state = "stopped";
  else if (totalUsd >= Number(thresholds.degradedUsd)) state = "degraded";
  else if (totalUsd >= Number(thresholds.warningUsd)) state = "warning";
  const reasons = [`state:${state}`];
  const unknownCount = countUnknown(input.unknownCount);
  if (unknownCount > 0) reasons.push(`unknown_billing:${unknownCount}`);
  if (state === "warning") reasons.push("daily_warning_threshold");
  if (state === "degraded") reasons.push("paid_fallback_threshold");
  if (state === "stopped") reasons.push("nonessential_work_stopped");
  return { state, totalUsd, measuredUsd, estimatedUsd, unknownCount, reasons };
}

function aggregateCostRows(rows, { voiceOnly = false } = {}) {
  let measuredUsd = 0;
  let estimatedUsd = 0;
  let unknownCount = 0;
  for (const row of Array.isArray(rows) ? rows : []) {
    if (voiceOnly && !isVoiceOperation(row && row.provider, row && row.operation)) continue;
    const status = row && row.actual_status == null ? null : String(row.actual_status);
    const actual = row && row.actual_billed_usd;
    const estimate = row && row.estimated_usd == null ? row.est_usd : row.estimated_usd;
    if (status === "known" && Number.isFinite(Number(actual)) && Number(actual) >= 0) measuredUsd += Number(actual);
    else if (status === "unknown" && estimate != null && estimate !== "" && Number.isFinite(Number(estimate)) && Number(estimate) >= 0) estimatedUsd += Number(estimate);
    else if (status === "known" || status === "unknown" || status == null) unknownCount++;
  }
  return { measuredUsd, estimatedUsd, unknownCount };
}

async function readDailySpend({ uid, nowMs = Date.now(), voiceOnly = false } = {}, deps = {}) {
  if (typeof deps.readDailySpend === "function") return deps.readDailySpend({ uid, nowMs, voiceOnly });
  const supaUrl = deps.supaUrl || process.env.SUPABASE_URL;
  const supaKey = deps.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey || typeof fetchImpl !== "function") throw new Error("budget ledger unavailable");
  const now = new Date(nowMs);
  const dayStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const nextDay = new Date(dayStart.getTime() + 86400000);
  const filters = [
    uid == null ? null : `uid=eq.${encodeURIComponent(uid)}`,
    `ts=gte.${encodeURIComponent(dayStart.toISOString())}`,
    `ts=lt.${encodeURIComponent(nextDay.toISOString())}`,
    "select=provider,operation,actual_status,actual_billed_usd,estimated_usd,est_usd,cost_classification",
  ].filter(Boolean).join("&");
  const voiceFilter = voiceOnly
    ? "&or=(provider.eq.telnyx,provider.eq.gemini,operation.ilike.*voice*,operation.ilike.*call*,operation.eq.session)"
    : "";
  const response = await fetchImpl(`${String(supaUrl).replace(/\/$/u, "")}/rest/v1/lm_api_cost?${filters}${voiceFilter}`, {
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}` },
  });
  if (!response || !response.ok) throw new Error(`budget ledger read failed (${response && response.status})`);
  return aggregateCostRows(await response.json().catch(() => []), { voiceOnly });
}

function isPaidFallback(provider, operation) {
  const p = String(provider || "").toLowerCase();
  const o = String(operation || "").toLowerCase();
  return o === "fallback" || o === "paid_fallback" || o.includes("google_fallback") || (p === "google" && o.includes("fallback"));
}

async function authorizeProviderOperation(input = {}, deps = {}) {
  if (input.cacheHit) return { allowed: true, reason: "cache_hit", state: "cache_hit", totalUsd: null };
  const thresholds = thresholdsFor(deps, input.thresholds);
  const requestId = attemptRequestId(input);
  const projectedUsd = projectedFor(input);
  const voice = isVoiceOperation(input.provider, input.operation);
  let spend;
  try {
    spend = await readDailySpend({ uid: input.uid, nowMs: input.nowMs }, deps);
  } catch (error) {
    return { allowed: false, reason: "budget_unavailable", state: "unknown", error: String(error && error.message ? error.message : error) };
  }
  const budget = evaluateProviderBudget({ ...spend, thresholds });
  const essential = input.essential === true;
  if (!essential && budget.state === "stopped") return { allowed: false, reason: "budget_stopped", ...budget };
  if (!essential && isPaidFallback(input.provider, input.operation) && (budget.state === "degraded" || budget.state === "stopped")) {
    return { allowed: false, reason: "paid_fallback_disabled", ...budget };
  }
  if (isVoiceOperation(input.provider, input.operation)) {
    const reader = deps.readVoiceSpend || (async ({ scope }) => readDailySpend({
      uid: scope === "user" ? input.uid : null, nowMs: input.nowMs, voiceOnly: true,
    }, deps));
    try {
      const userVoice = await reader({ scope: "user", uid: input.uid, nowMs: input.nowMs, voiceOnly: true });
      if (finiteUsd(userVoice.measuredUsd) + finiteUsd(userVoice.estimatedUsd) + projectedUsd >= Number(thresholds.voiceUserCapUsd)) {
        return { allowed: false, reason: "voice_user_cap", ...budget };
      }
      const globalVoice = await reader({ scope: "global", uid: null, nowMs: input.nowMs, voiceOnly: true });
      if (finiteUsd(globalVoice.measuredUsd) + finiteUsd(globalVoice.estimatedUsd) + projectedUsd >= Number(thresholds.voiceGlobalCapUsd)) {
        return { allowed: false, reason: "voice_global_cap", ...budget };
      }
    } catch (error) {
      return { allowed: false, reason: "budget_unavailable", state: "unknown", error: String(error && error.message ? error.message : error) };
    }
  }
  if (typeof deps.claimBudget === "function") {
    let claimed = false;
    try { claimed = await deps.claimBudget({ ...input, requestId, projectedUsd, budget }); } catch { claimed = false; }
    if (!claimed) return { allowed: false, reason: "budget_claim_failed", ...budget, requestId, projectedUsd };
  } else if (isClaimableProvider(input.provider) && (deps.supaUrl || process.env.SUPABASE_URL)) {
    const claim = await claimProviderBudget({
      ...input, requestId, projectedUsd, isVoice: voice,
      userVoiceCapUsd: thresholds.voiceUserCapUsd, globalVoiceCapUsd: thresholds.voiceGlobalCapUsd,
      dailyCapUsd: input.dailyCapUsd == null ? thresholds.stoppedUsd : input.dailyCapUsd,
      enforceDailyCap: input.enforceDailyCap !== false,
    }, deps);
    if (!claim.allowed) return { allowed: false, reason: claim.reason || "budget_claim_failed", ...budget, requestId, projectedUsd };
    if (claim.duplicate) return { allowed: true, reason: claim.reason || "budget_claim_duplicate", duplicate: true, ...budget, requestId, projectedUsd };
  }
  return { allowed: true, reason: budget.state === "warning" ? "budget_warning" : "allowed", ...budget, requestId, projectedUsd };
}

async function claimProviderBudget(input = {}, deps = {}) {
  const supaUrl = deps.supaUrl || process.env.SUPABASE_URL;
  const supaKey = deps.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey || !input.uid || !input.requestId || typeof fetchImpl !== "function") return { allowed: false, reason: "budget_claim_unavailable" };
  const day = new Date(input.nowMs == null ? Date.now() : input.nowMs).toISOString().slice(0, 10);
  let response;
  try {
    response = await fetchImpl(`${String(supaUrl).replace(/\/$/u, "")}/rest/v1/rpc/lm_claim_provider_budget`, {
    method: "POST",
    headers: {
      apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify({
      p_uid: String(input.uid), p_budget_day: day, p_provider: String(input.provider || "unknown"),
      p_operation: String(input.operation || "unknown"), p_request_id: String(input.requestId),
      p_projected_usd: finiteUsd(input.projectedUsd), p_is_voice: Boolean(input.isVoice),
      p_user_voice_cap: finiteUsd(input.userVoiceCapUsd), p_global_voice_cap: finiteUsd(input.globalVoiceCapUsd),
      p_daily_cap: finiteUsd(input.dailyCapUsd), p_enforce_daily_cap: input.enforceDailyCap !== false,
    }),
    });
  } catch (error) {
    return { allowed: false, reason: "budget_claim_unavailable", error: String(error && error.message ? error.message : error) };
  }
  // A uniqueness conflict is the replay receipt from another concurrent
  // worker. The SQL RPC itself returns the original claim as `duplicate=true`,
  // but Supabase/PostgREST can surface the same race as HTTP 409.
  if (!response || !response.ok) {
    if (response && Number(response.status) === 409) {
      return { allowed: true, reason: "budget_claim_duplicate", duplicate: true, requestId: input.requestId };
    }
    return { allowed: false, reason: "budget_claim_failed", status: response && response.status };
  }
  const raw = await response.json().catch(() => null);
  const result = Array.isArray(raw) ? raw[0] : raw;
  if (!result || result.allowed !== true) return { allowed: false, reason: result && result.reason ? String(result.reason) : "budget_claim_failed" };
  return { allowed: true, reason: result.duplicate ? "budget_claim_duplicate" : "budget_claimed", duplicate: Boolean(result.duplicate), requestId: result.request_id || input.requestId };
}

async function settleProviderVoice(input = {}, deps = {}) {
  const supaUrl = deps.supaUrl || process.env.SUPABASE_URL;
  const supaKey = deps.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey || !input.uid || !input.requestId || typeof fetchImpl !== "function") return false;
  const day = new Date(input.nowMs == null ? Date.now() : input.nowMs).toISOString().slice(0, 10);
  try {
    const response = await fetchImpl(`${String(supaUrl).replace(/\/$/u, "")}/rest/v1/rpc/lm_settle_provider_voice`, {
      method: "POST",
      headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json", Prefer: "return=representation" },
      body: JSON.stringify({
        p_uid: String(input.uid), p_budget_day: day, p_request_id: String(input.requestId),
        p_actual_usd: finiteUsd(input.actualBilledUsd),
        p_reservation_request_id: input.reservationRequestId == null ? null : String(input.reservationRequestId),
      }),
    });
    if (!response || !response.ok) return false;
    const raw = await response.json().catch(() => null);
    const result = Array.isArray(raw) ? raw[0] : raw;
    return Boolean(result && result.settled === true);
  } catch { return false; }
}

module.exports = {
  DEFAULT_THRESHOLDS,
  aggregateCostRows,
  evaluateProviderBudget,
  readDailySpend,
  authorizeProviderOperation,
  claimProviderBudget,
  settleProviderVoice,
};
