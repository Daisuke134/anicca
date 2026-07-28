"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  classifyBrowserTask,
  inferBrowserDecision,
  validateBrowserDecision,
} = require("./browser-task-classifier.js");

function decision(overrides = {}) {
  return {
    browser_required: true,
    explicit_request: true,
    reversible: true,
    zero_cost: true,
    requires_kyc: false,
    requires_login: false,
    action_kind: "registration",
    goal: "Find a free public online AI event and register contact@aniccaai.com",
    locale: "en",
    ...overrides,
  };
}

test("an ordinary natural-language delegated browser request is accepted without a slash command", async () => {
  const seen = [];
  const result = await classifyBrowserTask(
    "Find a free public online AI event and register contact@aniccaai.com for it.",
    {
      infer: async (input) => {
        seen.push(input);
        return decision();
      },
    },
  );

  assert.equal(seen.length, 1);
  assert.equal(result.accepted, true);
  assert.equal(result.goal, "Find a free public online AI event and register contact@aniccaai.com");
  assert.equal(result.reason, "explicit_reversible_zero_cost_browser_task");
});

test("conversation, feedback syntax, and settings commands never become browser jobs", async () => {
  let inferenceCalls = 0;
  const infer = async (input) => {
    inferenceCalls += 1;
    return input.startsWith("Thanks")
      ? decision({ explicit_request: false, browser_required: false })
      : decision();
  };

  assert.deepEqual(await classifyBrowserTask("Thanks, that sounds good", { infer }), {
    accepted: false,
    reason: "not_explicitly_actionable",
  });
  assert.deepEqual(await classifyBrowserTask("feedback: the panel is slow", { infer }), {
    accepted: false,
    reason: "reserved_message_shape",
  });
  assert.deepEqual(await classifyBrowserTask("/panel", { infer }), {
    accepted: false,
    reason: "reserved_message_shape",
  });
  assert.equal(inferenceCalls, 1, "only unreserved natural language reaches the model");
});

test("financial outflow, KYC, irreversible action, and model schema drift fail closed", async () => {
  const cases = [
    [decision({ zero_cost: false }), "financial_or_paid_action"],
    [decision({ requires_kyc: true }), "kyc_or_identity_gate"],
    [decision({ reversible: false }), "irreversible_action"],
    [decision({ explicit_request: false }), "not_explicitly_actionable"],
  ];
  for (const [modelResult, reason] of cases) {
    const actual = await classifyBrowserTask("Please do the thing", {
      infer: async () => modelResult,
    });
    assert.deepEqual(actual, { accepted: false, reason });
  }

  assert.throws(
    () => validateBrowserDecision({ ...decision(), surprise: "field" }),
    /browser decision schema/i,
  );
  assert.throws(
    () => validateBrowserDecision({ ...decision(), goal: "" }),
    /browser decision schema/i,
  );
});

test("the production classifier asks Gemini for strict JSON without putting its key in the URL", async () => {
  const seen = [];
  const fetchImpl = async (url, init) => {
    seen.push({ url: String(url), init });
    return {
      ok: true,
      status: 200,
      async json() {
        return {
          candidates: [{
            content: { parts: [{ text: JSON.stringify(decision()) }] },
          }],
        };
      },
    };
  };
  assert.deepEqual(
    await inferBrowserDecision("Please register me", { apiKey: "secret-key", fetchImpl }),
    decision(),
  );
  assert.match(seen[0].url, /gemini-2\.5-flash:generateContent$/);
  assert.doesNotMatch(seen[0].url, /secret-key/);
  assert.equal(seen[0].init.headers["x-goog-api-key"], "secret-key");
  const body = JSON.parse(seen[0].init.body);
  assert.equal(body.generationConfig.responseMimeType, "application/json");
  assert.deepEqual(body.generationConfig.responseSchema.required.sort(), [
    "action_kind",
    "browser_required",
    "explicit_request",
    "goal",
    "locale",
    "requires_kyc",
    "requires_login",
    "reversible",
    "zero_cost",
  ].sort());
});
