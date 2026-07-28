"use strict";

const DECISION_KEYS = Object.freeze([
  "action_kind",
  "browser_required",
  "explicit_request",
  "goal",
  "locale",
  "requires_kyc",
  "requires_login",
  "principal_kind",
  "reversible",
  "zero_cost",
]);

const RESERVED_MESSAGE = /^(?:\/|feedback\s*[:：]|フィードバック\s*[:：])/i;
const GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent";
const RESPONSE_SCHEMA = Object.freeze({
  type: "object",
  properties: {
    browser_required: { type: "boolean" },
    explicit_request: { type: "boolean" },
    reversible: { type: "boolean" },
    zero_cost: { type: "boolean" },
    requires_kyc: { type: "boolean" },
    requires_login: { type: "boolean" },
    principal_kind: { type: "string", enum: ["none", "agent_owned", "user_provided"] },
    action_kind: { type: "string" },
    goal: { type: "string" },
    locale: { type: "string", enum: ["en", "ja"] },
  },
  required: [...DECISION_KEYS],
});

function invalid() {
  throw new Error("browser decision schema invalid");
}

function validateBrowserDecision(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) invalid();
  if (Object.keys(value).sort().join(",") !== [...DECISION_KEYS].sort().join(",")) invalid();
  for (const key of [
    "browser_required",
    "explicit_request",
    "reversible",
    "zero_cost",
    "requires_kyc",
    "requires_login",
  ]) {
    if (typeof value[key] !== "boolean") invalid();
  }
  if (typeof value.action_kind !== "string" || !value.action_kind.trim() || value.action_kind.length > 100) invalid();
  if (typeof value.goal !== "string" || !value.goal.trim() || value.goal.length > 1000) invalid();
  if (!["en", "ja"].includes(value.locale)) invalid();
  if (!['none', 'agent_owned', 'user_provided'].includes(value.principal_kind)) invalid();
  if (value.requires_login === false && value.principal_kind !== "none") invalid();
  if (value.requires_login === true && !["agent_owned", "user_provided"].includes(value.principal_kind)) invalid();
  return Object.freeze({ ...value, goal: value.goal.trim(), action_kind: value.action_kind.trim() });
}

function rejectionReason(decision) {
  if (!decision.explicit_request || !decision.browser_required) return "not_explicitly_actionable";
  if (!decision.zero_cost) return "financial_or_paid_action";
  if (decision.requires_kyc) return "kyc_or_identity_gate";
  if (!decision.reversible) return "irreversible_action";
  return null;
}

async function inferBrowserDecision(text, opts = {}) {
  const apiKey = String(opts.apiKey || process.env.GEMINI_API_KEY || "").trim();
  const fetchImpl = opts.fetchImpl || globalThis.fetch;
  if (!apiKey || typeof fetchImpl !== "function") throw new Error("browser classifier unavailable");
  const prompt = [
    "Classify whether the Telegram message is an explicit request to perform an external browser task now.",
    "Return browser_required=true only if a website must be opened and interacted with.",
    "Explicit means the user directly asks for the action; wishes, ideas, thanks, questions, and background are false.",
    "reversible=true only when the action can be safely undone or abandoned.",
    "zero_cost=false for any payment, purchase, deposit, transfer, subscription charge, or financial commitment.",
    "requires_kyc=true for identity verification, government ID, regulated gig work, or financial onboarding.",
    "requires_login=true when the request explicitly depends on an existing authenticated account.",
    "Set principal_kind=none when requires_login=false; otherwise use agent_owned or user_provided for the login session owner.",
    "Normalize goal into an execution instruction of at most 1000 characters.",
    "Replace email addresses, phone numbers, account names, passwords, tokens, and credentials with role labels.",
    `Message: ${JSON.stringify(String(text || "").slice(0, 5000))}`,
  ].join("\n");
  const response = await fetchImpl(GEMINI, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-goog-api-key": apiKey,
    },
    body: JSON.stringify({
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig: {
        responseMimeType: "application/json",
        responseSchema: RESPONSE_SCHEMA,
        temperature: 0,
      },
    }),
    signal: AbortSignal.timeout(15_000),
  });
  if (!response || !response.ok) {
    throw new Error(`browser classifier failed (${response ? response.status : "no response"})`);
  }
  const body = await response.json();
  const raw = body?.candidates?.[0]?.content?.parts?.[0]?.text;
  let parsed;
  try { parsed = JSON.parse(raw || ""); } catch { throw new Error("browser classifier returned invalid JSON"); }
  return validateBrowserDecision(parsed);
}

async function classifyBrowserTask(text, deps = {}) {
  const input = String(text || "").trim();
  if (RESERVED_MESSAGE.test(input)) {
    return { accepted: false, reason: "reserved_message_shape" };
  }
  if (!input) {
    return { accepted: false, reason: "not_explicitly_actionable" };
  }
  const infer = deps.infer || ((value) => inferBrowserDecision(value, deps));
  const decision = validateBrowserDecision(await infer(input));
  const reason = rejectionReason(decision);
  if (reason) return { accepted: false, reason };
  return {
    accepted: true,
    reason: "explicit_reversible_zero_cost_browser_task",
    goal: decision.goal,
    actionKind: decision.action_kind,
    locale: decision.locale,
    requiresLogin: decision.requires_login,
    principalKind: decision.principal_kind,
  };
}

module.exports = {
  classifyBrowserTask,
  inferBrowserDecision,
  validateBrowserDecision,
};
