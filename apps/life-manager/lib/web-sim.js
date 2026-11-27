"use strict";

const crypto = require("node:crypto");
const { resolveWebUser } = require("./web-auth.js");

// The deployed Maritime tenant VM from anicca-ops
// files/maritime-per-user-sim-deploy-2026-11-27.md. Override with
// LM_MARITIME_SIM_AGENT_ID when the agent changes. The API key stays in
// MARITIME_API_KEY and is never sent to the browser.
const DEPLOYED_SIM_AGENT_ID = "0ed049f0-c91f-45f2-8901-2684de1a6760";
const SIM_PATH = "/api/lm-web/sim";
const WEB_UID_RE = /^lm_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const AGENT_ID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const API_KEY_RE = /^mk_[A-Za-z0-9_-]{4,}$/;
const SIM_DESIRED = ["confidence", "focus", "calm", "energy"];
const SIM_PAINS = ["stress", "anxiety", "sleep", "self_doubt"];
const SIM_FREQS = ["rarely", "weekly", "daily", "many_times_daily"];
// iOS onboarding (AffirmationGoalStepView / StrugglesStepView) stores these.
// per-user-sim.js rejects them. They are not renamed onto another enum.
const IOS_ONLY_DESIRED = new Set(["self_love", "letting_go"]);
const IOS_ONLY_PAINS = new Set(["procrastination"]);
const WINDOWS = new Set(["morning", "midday", "evening", "late"]);

function stringField(input, names) {
  for (const name of names) {
    const value = input[name];
    if (typeof value === "string") return value;
  }
  return "";
}

function painList(input) {
  const plural = input.pain_point_ids !== undefined ? input.pain_point_ids : input.painPointIds;
  if (Array.isArray(plural)) {
    if (plural.length < 1 || plural.length > 8) return null;
    if (plural.some((value) => typeof value !== "string" || value.length < 1 || value.length > 40)) return null;
    return plural;
  }
  const single = stringField(input, ["pain_point", "painPoint"]);
  return single ? [single] : null;
}

function localHour(timeZone, now) {
  if (typeof timeZone !== "string" || !timeZone || timeZone.length > 64 || timeZone !== timeZone.trim()) {
    return { error: "timezone_invalid" };
  }
  let formatted;
  try {
    formatted = new Intl.DateTimeFormat("en-US", {
      timeZone, hour: "numeric", hourCycle: "h23",
    }).format(now);
  } catch {
    return { error: "timezone_invalid" };
  }
  if (formatted === "24") formatted = "0";
  const hour = Number(formatted);
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) return { error: "timezone_invalid" };
  return { hour };
}

function mapOnboardingToSim(input, now = new Date()) {
  if (!input || typeof input !== "object" || Array.isArray(input)) return { ok: false, error: "invalid_answers" };
  const desired = stringField(input, ["desired_state", "desiredState"]);
  if (IOS_ONLY_DESIRED.has(desired)) return { ok: false, error: "desired_state_unmapped" };
  if (!SIM_DESIRED.includes(desired)) return { ok: false, error: "desired_state_invalid" };

  const pains = painList(input);
  if (!pains) return { ok: false, error: "pain_point_invalid" };
  const unknown = pains.filter((id) => !SIM_PAINS.includes(id) && !IOS_ONLY_PAINS.has(id));
  if (unknown.length) return { ok: false, error: "pain_point_invalid" };
  const unmappedPains = pains.filter((id) => IOS_ONLY_PAINS.has(id));
  const pain = pains.find((id) => SIM_PAINS.includes(id));
  if (!pain) return { ok: false, error: "pain_point_unmapped" };

  const frequency = stringField(input, ["struggle_frequency", "struggleFrequency"]);
  if (!SIM_FREQS.includes(frequency)) return { ok: false, error: "struggle_frequency_invalid" };

  const hour = localHour(input.timezone, now);
  if (hour.error) return { ok: false, error: hour.error };
  return {
    ok: true,
    profile: {
      desired_state: desired,
      pain_point: pain,
      struggle_frequency: frequency,
      local_hour: hour.hour,
    },
    unmapped: { pain_point_ids: unmappedPains },
  };
}

function chatBodyForSim(personId, profile) {
  return {
    message: "onboarding complete",
    sim: { person_id: personId, profile },
  };
}

function decisionFromChat(body) {
  const decision = body && body.simulation && body.simulation.decision;
  if (!decision || typeof decision !== "object") return null;
  const nudges = decision.nudges_per_day;
  const probability = decision.predicted_daily_response_probability;
  if (typeof decision.category !== "string" || decision.category.length > 40) return null;
  if (typeof decision.first_line !== "string" || !decision.first_line || decision.first_line.length > 240) return null;
  if (!WINDOWS.has(decision.delivery_window)) return null;
  if (typeof decision.delivery_at_local !== "string" || !/^\d{2}:\d{2}$/.test(decision.delivery_at_local)) return null;
  if (!Number.isInteger(nudges) || nudges < 1 || nudges > 3) return null;
  if (typeof probability !== "number" || !Number.isFinite(probability)) return null;
  return {
    category: decision.category,
    predicted_daily_response_probability: probability,
    nudges_per_day: nudges,
    delivery_window: decision.delivery_window,
    delivery_at_local: decision.delivery_at_local,
    first_line: decision.first_line,
  };
}

function send(res, status, body, extra = {}) {
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "referrer-policy": "no-referrer",
    "x-content-type-options": "nosniff",
    ...extra,
  });
  res.end(JSON.stringify(body));
  return res;
}

function originOf(value) {
  try {
    const parsed = new URL(String(value || ""));
    if (parsed.protocol !== "https:" && !(parsed.protocol === "http:" && ["localhost", "127.0.0.1"].includes(parsed.hostname))) return "";
    if (parsed.username || parsed.password) return "";
    return parsed.origin;
  } catch {
    return "";
  }
}

function csrfOk(req, user) {
  const received = Buffer.from(String(req.headers && req.headers["x-lm-web-csrf"] || ""));
  const expected = Buffer.from(String(user && user.csrf || ""));
  return received.length > 0 && received.length === expected.length && crypto.timingSafeEqual(received, expected);
}

async function readJson(req) {
  const mime = String(req.headers && req.headers["content-type"] || "");
  if (!/^application\/json(?:\s*;|$)/i.test(mime)) return { error: "invalid_body" };
  const chunks = [];
  let bytes = 0;
  for await (const chunk of req) {
    bytes += chunk.length;
    if (bytes > 8192) return { error: "invalid_body" };
    chunks.push(chunk);
  }
  try {
    const body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    if (!body || typeof body !== "object" || Array.isArray(body)) return { error: "invalid_body" };
    return { body };
  } catch {
    return { error: "invalid_body" };
  }
}

async function postSim(personId, profile, options) {
  const env = options.env || process.env;
  const apiKey = String(env.MARITIME_API_KEY || "");
  const agentId = String(env.LM_MARITIME_SIM_AGENT_ID || DEPLOYED_SIM_AGENT_ID);
  if (!API_KEY_RE.test(apiKey) || !AGENT_ID_RE.test(agentId)) return { ok: false, error: "sim_unavailable" };
  const fetchImpl = options.fetchImpl || globalThis.fetch;
  let response;
  try {
    response = await fetchImpl(`https://api.maritime.sh/api/agents/${agentId}/chat`, {
      method: "POST",
      redirect: "error",
      signal: AbortSignal.timeout(20000),
      headers: { Authorization: `Bearer ${apiKey}`, "content-type": "application/json" },
      body: JSON.stringify(chatBodyForSim(personId, profile)),
    });
  } catch {
    return { ok: false, error: "sim_unavailable" };
  }
  if (!response || response.ok !== true) return { ok: false, error: "sim_unavailable" };
  let payload;
  try { payload = await response.json(); } catch { return { ok: false, error: "sim_unavailable" }; }
  const decision = decisionFromChat(payload);
  if (!decision) return { ok: false, error: "sim_unavailable" };
  return { ok: true, decision };
}

async function handleWebSimRequest(req, res, options = {}) {
  const url = new URL(String(req.url || "/"), "http://life-manager.local");
  if (url.pathname !== SIM_PATH) return send(res, 404, { ok: false, error: "not_found" });
  if (req.method !== "POST") return send(res, 405, { ok: false, error: "method_not_allowed" }, { allow: "POST" });
  const origin = originOf(options.publicOrigin);
  if (!origin || req.headers?.origin !== origin) return send(res, 403, { ok: false, error: "origin_rejected" });
  let user = null;
  try { user = await (options.resolveWebUserImpl || resolveWebUser)(req, res, options); } catch { user = null; }
  if (!user || !WEB_UID_RE.test(String(user.uid || ""))) return send(res, 401, { ok: false, error: "unauthorized" });
  if (!csrfOk(req, user)) return send(res, 403, { ok: false, error: "csrf_rejected" });
  const parsed = await readJson(req);
  if (parsed.error) return send(res, 400, { ok: false, error: parsed.error });
  const mapped = mapOnboardingToSim(parsed.body, options.now ? options.now() : new Date());
  if (!mapped.ok) {
    const error = mapped.error.endsWith("_unmapped") ? "answers_unmapped" : mapped.error;
    return send(res, 200, { ok: false, error });
  }
  const result = await postSim(String(user.uid), mapped.profile, options);
  return send(res, 200, result.ok ? { ok: true, decision: result.decision } : { ok: false, error: "sim_unavailable" });
}

module.exports = {
  DEPLOYED_SIM_AGENT_ID,
  SIM_PATH,
  mapOnboardingToSim,
  chatBodyForSim,
  decisionFromChat,
  handleWebSimRequest,
};
