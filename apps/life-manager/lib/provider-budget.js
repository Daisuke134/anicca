"use strict";

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

function aggregateCostRows(rows) {
  let measuredUsd = 0;
  let estimatedUsd = 0;
  let unknownCount = 0;
  for (const row of Array.isArray(rows) ? rows : []) {
    const status = row && row.actual_status == null ? null : String(row.actual_status);
    const actual = row && row.actual_billed_usd;
    const estimate = row && row.estimated_usd == null ? row.est_usd : row.estimated_usd;
    if (status === "measured" && Number.isFinite(Number(actual)) && Number(actual) >= 0) measuredUsd += Number(actual);
    else if (Number.isFinite(Number(estimate)) && Number(estimate) >= 0) estimatedUsd += Number(estimate);
    else if (status === "unknown" || (status == null && !Number.isFinite(Number(estimate)))) unknownCount++;
  }
  return { measuredUsd, estimatedUsd, unknownCount };
}

async function readDailySpend({ uid, nowMs = Date.now() } = {}, deps = {}) {
  if (typeof deps.readDailySpend === "function") return deps.readDailySpend({ uid, nowMs });
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
    "select=actual_status,actual_billed_usd,estimated_usd,est_usd",
  ].filter(Boolean).join("&");
  const response = await fetchImpl(`${String(supaUrl).replace(/\/$/u, "")}/rest/v1/lm_api_cost?${filters}`, {
    headers: { apikey: supaKey, Authorization: `Bearer ${supaKey}` },
  });
  if (!response || !response.ok) throw new Error(`budget ledger read failed (${response && response.status})`);
  return aggregateCostRows(await response.json().catch(() => []));
}

function isVoiceOperation(provider, operation) {
  const p = String(provider || "").toLowerCase();
  const o = String(operation || "").toLowerCase();
  return p === "telnyx" || p === "gemini" || o.includes("voice") || o.includes("call") || o === "session";
}

function isPaidFallback(provider, operation) {
  const p = String(provider || "").toLowerCase();
  const o = String(operation || "").toLowerCase();
  return o === "fallback" || o === "paid_fallback" || o.includes("google_fallback") || (p === "google" && o.includes("fallback"));
}

async function authorizeProviderOperation(input = {}, deps = {}) {
  if (input.cacheHit) return { allowed: true, reason: "cache_hit", state: "cache_hit", totalUsd: null };
  const thresholds = thresholdsFor(deps, input.thresholds);
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
    const projectedUsd = finiteUsd(input.projectedUsd);
    const reader = deps.readVoiceSpend || (async ({ scope }) => readDailySpend({ uid: scope === "user" ? input.uid : null, nowMs: input.nowMs }, deps));
    try {
      const userVoice = await reader({ scope: "user", uid: input.uid, nowMs: input.nowMs });
      if (finiteUsd(userVoice.measuredUsd) + finiteUsd(userVoice.estimatedUsd) + projectedUsd >= Number(thresholds.voiceUserCapUsd)) {
        return { allowed: false, reason: "voice_user_cap", ...budget };
      }
      const globalVoice = await reader({ scope: "global", uid: null, nowMs: input.nowMs });
      if (finiteUsd(globalVoice.measuredUsd) + finiteUsd(globalVoice.estimatedUsd) + projectedUsd >= Number(thresholds.voiceGlobalCapUsd)) {
        return { allowed: false, reason: "voice_global_cap", ...budget };
      }
    } catch (error) {
      return { allowed: false, reason: "budget_unavailable", state: "unknown", error: String(error && error.message ? error.message : error) };
    }
  }
  if (typeof deps.claimBudget === "function") {
    let claimed = false;
    try { claimed = await deps.claimBudget({ ...input, budget }); } catch { claimed = false; }
    if (!claimed) return { allowed: false, reason: "budget_claim_failed", ...budget };
  }
  return { allowed: true, reason: budget.state === "warning" ? "budget_warning" : "allowed", ...budget };
}

async function claimProviderBudget(input = {}, deps = {}) {
  const supaUrl = deps.supaUrl || process.env.SUPABASE_URL;
  const supaKey = deps.supaKey || process.env.SUPABASE_SERVICE_ROLE_KEY;
  const fetchImpl = deps.fetchImpl || globalThis.fetch;
  if (!supaUrl || !supaKey || !input.uid || !input.requestId || typeof fetchImpl !== "function") return false;
  const day = new Date(input.nowMs == null ? Date.now() : input.nowMs).toISOString().slice(0, 10);
  const response = await fetchImpl(`${String(supaUrl).replace(/\/$/u, "")}/rest/v1/lm_provider_budget_claims`, {
    method: "POST",
    headers: {
      apikey: supaKey, Authorization: `Bearer ${supaKey}`, "Content-Type": "application/json",
      Prefer: "resolution=ignore-duplicates,return=minimal",
    },
    body: JSON.stringify({
      uid: String(input.uid), budget_day: day, provider: String(input.provider || "unknown"),
      operation: String(input.operation || "unknown"), request_id: String(input.requestId),
      projected_usd: finiteUsd(input.projectedUsd),
    }),
  });
  return Boolean(response && (response.status === 201 || response.status === 200));
}

module.exports = {
  DEFAULT_THRESHOLDS,
  aggregateCostRows,
  evaluateProviderBudget,
  readDailySpend,
  authorizeProviderOperation,
  claimProviderBudget,
};
