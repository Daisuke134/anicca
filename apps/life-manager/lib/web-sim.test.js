"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { createMaritimeManagerServer } = require("../maritime/server.js");
const { validateProfile } = require("../maritime/sim/per-user-sim.js");
const {
  mapOnboardingToSim,
  chatBodyForSim,
  handleWebSimRequest,
  DEPLOYED_SIM_AGENT_ID,
} = require("./web-sim.js");

const UID = "lm_123e4567-e89b-12d3-a456-426614174000";
const NOW = new Date("2026-11-27T00:30:00.000Z");

function userShapedAnswers(overrides = {}) {
  return {
    desired_state: "focus",
    pain_point_ids: ["procrastination", "stress"],
    struggle_frequency: "weekly",
    timezone: "Asia/Tokyo",
    person_id: "lm_client_must_not_win",
    ...overrides,
  };
}

test("a user-shaped onboarding answer maps to a sim payload the chat endpoint accepts", async () => {
  const mapped = mapOnboardingToSim(userShapedAnswers(), NOW);
  assert.equal(mapped.ok, true);
  assert.deepEqual(mapped.profile, {
    desired_state: "focus",
    pain_point: "stress",
    struggle_frequency: "weekly",
    local_hour: 9,
  });
  assert.deepEqual(mapped.unmapped.pain_point_ids, ["procrastination"]);
  assert.equal(validateProfile(mapped.profile).error, undefined);

  const server = createMaritimeManagerServer({
    config: {
      tenantId: "lm_4e7aeea7-b38d-4959-80aa-060c293c77af",
      releaseSha: "a".repeat(40),
      modelReady: true,
    },
    relayWake: async () => ({ accepted: true }),
    simLedger: { append: false },
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const port = server.address().port;
    const payload = chatBodyForSim(UID, mapped.profile);
    const accepted = await fetch(`http://127.0.0.1:${port}/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    assert.equal(accepted.status, 200);
    const body = await accepted.json();
    assert.equal(body.simulation.decision.category, "focus");
    assert.equal(body.simulation.decision.first_line, "One sentence naming the single next action.");
    assert.equal(body.simulation.decision.delivery_window, "morning");
    assert.equal(body.simulation.decision.delivery_at_local, "07:30");
    assert.equal(body.simulation.decision.nudges_per_day, 1);
    assert.equal(body.simulation.input.local_hour, 9);
    assert.equal(body.simulation.person_id, UID);

    const raw = chatBodyForSim(UID, {
      desired_state: "self_love",
      pain_point: "procrastination",
      struggle_frequency: "weekly",
      local_hour: 9,
    });
    const rejected = await fetch(`http://127.0.0.1:${port}/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(raw),
    });
    assert.equal(rejected.status, 400);
    assert.equal((await rejected.json()).errorClass, "sim_profile_invalid");
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

test("iOS-only desired states and pains fail closed instead of being renamed into a sim enum", () => {
  const love = mapOnboardingToSim(userShapedAnswers({ desired_state: "self_love" }), NOW);
  assert.equal(love.ok, false);
  assert.equal(love.error, "desired_state_unmapped");
  const letting = mapOnboardingToSim(userShapedAnswers({ desired_state: "letting_go" }), NOW);
  assert.equal(letting.ok, false);
  assert.equal(letting.error, "desired_state_unmapped");
  const delay = mapOnboardingToSim(userShapedAnswers({ pain_point_ids: ["procrastination"] }), NOW);
  assert.equal(delay.ok, false);
  assert.equal(delay.error, "pain_point_unmapped");
});

test("the web proxy sends the signed-in uid and keeps the Maritime key off the response", async () => {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    return {
      ok: true,
      json: async () => ({
        response: "ok",
        simulation: {
          decision: {
            category: "focus",
            predicted_daily_response_probability: 0.447,
            nudges_per_day: 1,
            delivery_window: "morning",
            delivery_at_local: "07:30",
            first_line: "One sentence naming the single next action.",
          },
        },
      }),
    };
  };
  const result = await handleWebSimRequest(request(userShapedAnswers()), responseCapture(), {
    resolveWebUserImpl: async () => ({ uid: UID, csrf: "csrf-token" }),
    publicOrigin: "https://life.example",
    env: { MARITIME_API_KEY: "mk_test_only", LM_MARITIME_SIM_AGENT_ID: DEPLOYED_SIM_AGENT_ID },
    fetchImpl,
    now: () => NOW,
  });
  assert.equal(result.status, 200);
  assert.equal(result.body.ok, true);
  assert.equal(result.body.decision.first_line, "One sentence naming the single next action.");
  assert.equal(result.body.decision.delivery_at_local, "07:30");
  assert.equal(JSON.stringify(result.body).includes("mk_test_only"), false);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `https://api.maritime.sh/api/agents/${DEPLOYED_SIM_AGENT_ID}/chat`);
  assert.equal(calls[0].init.headers.Authorization, "Bearer mk_test_only");
  const sent = JSON.parse(calls[0].init.body);
  assert.equal(sent.sim.person_id, UID);
  assert.equal(sent.sim.profile.pain_point, "stress");
  assert.equal(sent.sim.profile.local_hour, 9);
});

test("a Maritime error stays a soft ok:false and does not call the provider for an unmapped answer", async () => {
  let calls = 0;
  const fetchImpl = async () => {
    calls += 1;
    return { ok: false, status: 500, json: async () => ({ error: "secret-upstream" }) };
  };
  const failed = await handleWebSimRequest(request(userShapedAnswers()), responseCapture(), {
    resolveWebUserImpl: async () => ({ uid: UID, csrf: "csrf-token" }),
    publicOrigin: "https://life.example",
    env: { MARITIME_API_KEY: "mk_test_only" },
    fetchImpl,
    now: () => NOW,
  });
  assert.equal(failed.status, 200);
  assert.deepEqual(failed.body, { ok: false, error: "sim_unavailable" });
  assert.equal(JSON.stringify(failed.body).includes("secret-upstream"), false);

  calls = 0;
  const unmapped = await handleWebSimRequest(request(userShapedAnswers({ desired_state: "self_love" })), responseCapture(), {
    resolveWebUserImpl: async () => ({ uid: UID, csrf: "csrf-token" }),
    publicOrigin: "https://life.example",
    env: { MARITIME_API_KEY: "mk_test_only" },
    fetchImpl,
    now: () => NOW,
  });
  assert.equal(unmapped.status, 200);
  assert.equal(unmapped.body.ok, false);
  assert.equal(unmapped.body.error, "answers_unmapped");
  assert.equal(calls, 0);
});

function request(body) {
  return {
    method: "POST",
    url: "/api/lm-web/sim",
    headers: {
      origin: "https://life.example",
      "content-type": "application/json",
      "x-lm-web-csrf": "csrf-token",
    },
    async *[Symbol.asyncIterator]() {
      yield Buffer.from(JSON.stringify(body));
    },
  };
}

function responseCapture() {
  return {
    status: 0,
    body: null,
    writeHead(status) { this.status = status; },
    end(payload) { this.body = JSON.parse(payload); },
  };
}
