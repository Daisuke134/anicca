"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { createMoneyPrinterSpecialist } = require("./money-printer-specialist.js");

const TENANT = "tenant-a";
const OPPORTUNITY_ID = "a".repeat(64);
const GOAL_REF = `intent-entry://${TENANT}/${OPPORTUNITY_ID}`;
const JOB_ID = `goal:${OPPORTUNITY_ID}`;

function response(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() { return body; },
  };
}

function expected(overrides = {}) {
  return {
    tenant_id: TENANT,
    job_id: JOB_ID,
    goal_ref: GOAL_REF,
    ...overrides,
  };
}

function opportunity(overrides = {}) {
  return {
    uid: TENANT,
    opportunity_id: OPPORTUNITY_ID,
    source_url: "https://public.example/opportunity",
    title: "Public bounded opportunity",
    goal_statement: "Research the public opportunity and prepare the feasible next work.",
    value_minor: "50000",
    currency: "JPY",
    status: "DISCOVERED",
    goal_ref: GOAL_REF,
    private_state: "must not reach the specialist prompt",
    ...overrides,
  };
}

test("specialist reads one tenant goal, runs bounded work, updates status, and returns its receipt", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-money-specialist-"));
  const requests = [];
  let runnerInput;
  const runAgentRunner = async (input) => {
    runnerInput = input;
    return {
      summary: { status: "success", selected_provider: "codex", selected_model: "gpt-5.6-terra" },
      value: { status: "completed", execution_id: "execution-money-1" },
    };
  };
  const specialist = createMoneyPrinterSpecialist({
    supaUrl: "https://supa.example/",
    supaKey: "service-secret",
    dataDir,
    repoRoot: "/repo",
    fetchImpl: async (url, init = {}) => {
      requests.push({ url: String(url), init });
      const parsed = new URL(url);
      if (init.method == null && parsed.pathname.endsWith("/lm_money_opportunities")) {
        return response([opportunity()]);
      }
      if (init.method === "PATCH" && parsed.pathname.endsWith("/lm_money_opportunities")) {
        return response([{ ...opportunity(), status: "QUALIFIED" }]);
      }
      throw new Error(`unexpected request ${url}`);
    },
    runAgentRunner,
  });

  const result = await specialist(expected());

  assert.deepEqual(result, {
    kind: "general_agent_work",
    status: "completed",
    tenant_id: TENANT,
    job_id: JOB_ID,
    goal_ref: GOAL_REF,
    execution_id: "execution-money-1",
    next_job_refs: [],
  });
  assert.equal(requests.length, 2);
  assert.equal(new URL(requests[0].url).searchParams.get("uid"), `eq.${TENANT}`);
  assert.equal(new URL(requests[0].url).searchParams.get("goal_ref"), `eq.${GOAL_REF}`);
  assert.match(new URL(requests[0].url).searchParams.get("select"), /source_url/);
  assert.match(new URL(requests[0].url).searchParams.get("select"), /goal_statement/);
  assert.equal(requests[1].init.method, "PATCH");
  assert.equal(JSON.parse(requests[1].init.body).status, "QUALIFIED");
  assert.match(requests[1].init.headers.Prefer, /return=representation/);
  assert.equal(new URL(requests[1].url).searchParams.get("uid"), `eq.${TENANT}`);
  assert.equal(new URL(requests[1].url).searchParams.get("goal_ref"), `eq.${GOAL_REF}`);
  assert.ok(runnerInput);
  assert.equal(runnerInput.taskClass, "repeatable-agent");
  assert.ok(runnerInput.timeoutMs <= 180_000);
  assert.equal(runnerInput.repoRoot, "/repo");
  assert.match(runnerInput.evidenceDir, new RegExp(`${dataDir}/evidence/money-printer/${OPPORTUNITY_ID}$`));
  assert.deepEqual(runnerInput.schema, {
    type: "object",
    additionalProperties: false,
    required: ["status", "execution_id"],
    properties: {
      status: { type: "string", const: "completed" },
      execution_id: { type: "string", minLength: 1, maxLength: 200 },
    },
  });
  assert.match(runnerInput.prompt, /Public bounded opportunity/);
  assert.match(runnerInput.prompt, /Research the public opportunity/);
  assert.match(runnerInput.prompt, /qualification|research stage/i);
  assert.match(runnerInput.prompt, /not delivery|never claim delivery/i);
  assert.doesNotMatch(runnerInput.prompt, /private_state|must not reach/);
});

test("specialist rejects scope, malformed model output, and failed opportunity readback", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-money-specialist-invalid-"));
  const base = {
    supaUrl: "https://supa.example",
    supaKey: "service-secret",
    dataDir,
    repoRoot: "/repo",
  };
  await assert.rejects(
    createMoneyPrinterSpecialist({
      ...base,
      readOpportunity: async () => ({ ...opportunity(), uid: "tenant-b" }),
      runAgentRunner: async () => ({ value: { status: "planned", execution_id: "execution-1" } }),
      updateOpportunity: async () => opportunity({ status: "QUALIFIED" }),
    })(expected()),
    /tenant|scope/i,
  );

  let updates = 0;
  await assert.rejects(
    createMoneyPrinterSpecialist({
      ...base,
      readOpportunity: async () => opportunity(),
      runAgentRunner: async () => ({ value: { status: "planned", execution_id: "execution-1" } }),
      updateOpportunity: async () => { updates += 1; return opportunity({ status: "QUALIFIED" }); },
    })(expected()),
    /status|receipt|specialist/i,
  );
  assert.equal(updates, 0);

  await assert.rejects(
    createMoneyPrinterSpecialist({
      ...base,
      readOpportunity: async () => opportunity(),
      runAgentRunner: async () => ({ value: { status: "completed", execution_id: "execution-1" } }),
      updateOpportunity: async () => opportunity({ status: "DISCOVERED" }),
    })(expected()),
    /readback|status/i,
  );
});
