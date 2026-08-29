"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { createHash } = require("node:crypto");
const {
  parseRuntimeCommand,
  validateComposeModel,
  runRuntimeUp,
  buildSchedulerHolderToken,
  marketingGenerationDueDate,
  listGenerationReceipts,
  listHonneJaShadowGenerationReceipts,
  listMarketingVideoPublicationReceipts,
  listObservablePublicationReceipts,
  executeCapabilityJob,
  createScopedEnvironmentSecretProvider,
  createWorkerHandlers,
  observeWorkerPoll,
} = require("./runtime-up.js");
const {
  buildMarketingObservationJob,
} = require("../lib/marketing-observation-adapter.js");
const {
  buildMarketingVideoGenerationJob,
} = require("../lib/marketing-video-generation-adapter.js");
const {
  importContentObject,
} = require("../lib/content-object-store.js");
const {
  verifyOutboundEvidence,
} = require("../lib/outbound-evidence.js");
const {
  buildVerifiedOutboundReceipt,
} = require("../lib/outbound-success.js");

const ROOT = path.join(__dirname, "../../..");
const COMPOSE_PATH = path.join(ROOT, "deploy/local/compose.yaml");
const MONEY_TENANT = "tenant-a";
const MONEY_OPPORTUNITY_ID = "a".repeat(64);
const MONEY_GOAL_REF = `intent-entry://${MONEY_TENANT}/${MONEY_OPPORTUNITY_ID}`;
const MONEY_JOB_ID = `goal:${MONEY_OPPORTUNITY_ID}`;
const LEASE_MIGRATION = path.join(
  __dirname,
  "../migrations/20260729_runtime_scheduler_lease.sql",
);

test("active capability work refreshes worker liveness without starting a second claim", () => {
  const state = { lastPollAt: "2026-08-01T00:00:00.000Z" };
  assert.equal(observeWorkerPoll(state, true, () => "2026-08-01T00:01:00.000Z"), false);
  assert.equal(state.lastPollAt, "2026-08-01T00:01:00.000Z");
  assert.equal(observeWorkerPoll(state, false, () => "2026-08-01T00:02:00.000Z"), true);
  assert.equal(state.lastPollAt, "2026-08-01T00:02:00.000Z");
});

function healthyService(environment = {}) {
  return {
    environment,
    healthcheck: { test: ["CMD", "true"] },
  };
}

function validModel() {
  return {
    services: {
      postgres: {
        ...healthyService(),
        volumes: ["postgres-data:/var/lib/postgresql/data"],
      },
      "object-store": {
        ...healthyService(),
        volumes: ["object-data:/data"],
      },
      migrate: {
        environment: {},
        depends_on: { postgres: { condition: "service_healthy" } },
      },
      "runtime-init": {
        environment: {},
        depends_on: { migrate: { condition: "service_completed_successfully" } },
      },
      api: healthyService({
        LM_DEPLOYMENT_ROLE: "api",
        LIFE_RUN_LOOPS: "false",
      }),
      scheduler: healthyService({
        LM_DEPLOYMENT_ROLE: "scheduler",
        LM_SCHEDULER_OWNER: "local-primary",
        LIFE_RUN_LOOPS: "true",
      }),
      worker: healthyService({
        LM_DEPLOYMENT_ROLE: "worker",
        LIFE_RUN_LOOPS: "false",
      }),
    },
    volumes: {
      "postgres-data": {},
      "object-data": {},
      "runtime-data": {},
    },
  };
}

async function verifiedOutboundReceipt(job) {
  const bytes = Buffer.alloc(5000, 0x61);
  Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(bytes);
  const digest = createHash("sha256").update(bytes).digest("hex");
  const evidence = await verifyOutboundEvidence({
    tenantId: job.tenant_id,
    attemptRef: `runtime-attempt://${job.tenant_id}/${job.job_id}/${job.attempt}`,
    externalReceiptRef: `provider-receipt://${job.tenant_id}/receipt-1`,
    artifactRef: `object://sha256/${digest}`,
    canonicalUrl: "https://lu.ma/tokyo-agent-night",
  }, {
    readExternalReceipt: async () => ({
      kind: "provider_response",
      provider_id: "receipt-1",
      observed_at: "2026-08-01T09:00:00.000Z",
    }),
    readArtifact: async () => bytes,
    fetchImpl: async () => ({ status: 200 }),
  });
  return buildVerifiedOutboundReceipt({
    tenantId: job.tenant_id,
    jobId: job.job_id,
    attempt: job.attempt,
    verifiedAt: "2026-08-01T09:00:01.000Z",
  }, evidence);
}

test("runtime command accepts only the explicit local up contract", () => {
  assert.deepEqual(
    parseRuntimeCommand(["runtime", "up", "--mode", "local"]),
    { command: "up", mode: "local" },
  );
  assert.throws(
    () => parseRuntimeCommand(["runtime", "up", "--mode", "cloud"]),
    /local/i,
  );
  assert.throws(() => parseRuntimeCommand(["up"]), /usage/i);
});

test("Railway start command routes the worker role to internal-worker", () => {
  const railway = fs.readFileSync(path.join(ROOT, "apps/life-manager/railway.toml"), "utf8");
  const match = railway.match(/^startCommand = "((?:\\.|[^"])*)"$/m);
  assert.ok(match, "railway.toml must define a startCommand");
  assert.equal(
    match[1].replace(/\\"/g, '"'),
    'if [ "$LM_DEPLOYMENT_ROLE" = "worker" ]; then exec node scripts/runtime-up.js internal-worker; else exec node server.js; fi',
  );
});

test("coverage worker capability receives the assembled Connector refresh services", () => {
  const connectorCoverageServices = Object.freeze({
    coverageStore: { read: async () => {}, save: async () => {} },
    refreshCoverage: async () => {},
  });
  let observedServices;
  const handlers = createWorkerHandlers({}, ["connector.coverage.refresh"], {
    connectorCoverageServices,
    createRegistry({ servicesByAdapter }) {
      observedServices = servicesByAdapter["connector-coverage-refresh"];
      return {
        hasCapability(capability) { return capability === "connector.coverage.refresh"; },
        getByCapability() { return { execute: async () => "coverage-executed" }; },
      };
    },
  });

  assert.equal(observedServices, connectorCoverageServices);
  assert.equal(typeof handlers["connector.coverage.refresh"], "function");
});

test("general money worker wires its injected bounded specialist through the registry", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-runtime-money-specialist-"));
  const specialist = async (expected) => ({
    kind: "general_agent_work",
    status: "completed",
    tenant_id: expected.tenant_id,
    job_id: expected.job_id,
    goal_ref: expected.goal_ref,
    execution_id: "execution-runtime-1",
    next_job_refs: [],
  });
  let services;
  const handlers = createWorkerHandlers({
    SUPABASE_URL: "https://supa.example",
    SUPABASE_SERVICE_ROLE_KEY: "service-secret",
    LM_DATA_DIR: dataDir,
  }, ["general-agent.work"], {
    moneyPrinterSpecialist: specialist,
    createRegistry({ servicesByAdapter }) {
      services = servicesByAdapter["general-agent-work"];
      return {
        hasCapability: (capability) => capability === "general-agent.work",
        getByCapability: () => ({
          execute: async (job) => ({
            receipt: await services.runBoundedSpecialist({
              tenant_id: job.tenant_id,
              job_id: job.job_id,
              goal_ref: job.input_refs.goal_ref,
            }),
          }),
        }),
      };
    },
  });
  const job = {
    tenant_id: MONEY_TENANT,
    job_id: MONEY_JOB_ID,
    loop_id: "life-manager.manager",
    capability: "general-agent.work",
    effect_class: "none",
    effect_key: null,
    input_refs: { goal_ref: MONEY_GOAL_REF },
    max_attempts: 1,
  };

  assert.equal(services.runBoundedSpecialist, specialist);
  assert.deepEqual(await handlers["general-agent.work"](job), {
    receipt: await specialist({
      tenant_id: MONEY_TENANT,
      job_id: MONEY_JOB_ID,
      goal_ref: MONEY_GOAL_REF,
    }),
  });
});

test("production general money worker fails before query, factory, registry, or effects without Gemini", () => {
  const calls = [];
  assert.throws(() => createWorkerHandlers({
    LM_DATA_DIR: fs.mkdtempSync(path.join(os.tmpdir(), "lm-runtime-money-missing-gemini-")),
  }, ["general-agent.work"], {
    async query() { calls.push("query"); return { rows: [] }; },
    createMoneyPrinterSpecialist() { calls.push("factory"); return async () => {}; },
    createRegistry() { calls.push("registry"); return { hasCapability: () => false }; },
  }), /GEMINI_API_KEY is required/);
  assert.deepEqual(calls, []);
});

test("general money worker permits an explicit runner without Gemini", () => {
  const runner = async () => ({ value: { status: "completed", execution_id: "test-runner" } });
  let options;
  createWorkerHandlers({
    LM_DATA_DIR: fs.mkdtempSync(path.join(os.tmpdir(), "lm-runtime-money-explicit-runner-")),
  }, ["general-agent.work"], {
    readOpportunity: async () => ({}),
    updateOpportunity: async () => ({}),
    runAgentRunner: runner,
    createMoneyPrinterSpecialist(input) { options = input; return async () => {}; },
    createRegistry() { return { hasCapability: () => false }; },
  });
  assert.equal(options.runAgentRunner, runner);
});

test("production general money worker resolves LM_REPO_ROOT and rejects filesystem root", () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-runtime-money-repo-root-"));
  let options;
  const dependencies = {
    readOpportunity: async () => ({}),
    updateOpportunity: async () => ({}),
    createMoneyPrinterSpecialist(input) { options = input; return async () => {}; },
    createRegistry() { return { hasCapability: () => false }; },
  };
  createWorkerHandlers({
    LM_DATA_DIR: dataDir,
    GEMINI_API_KEY: "gemini-secret-key",
    LM_REPO_ROOT: "/app",
  }, ["general-agent.work"], dependencies);
  assert.equal(options.repoRoot, "/app");

  assert.throws(() => createWorkerHandlers({
    LM_DATA_DIR: dataDir,
    GEMINI_API_KEY: "gemini-secret-key",
    LM_REPO_ROOT: "/",
  }, ["general-agent.work"], {
    readOpportunity: async () => ({}),
    updateOpportunity: async () => ({}),
    createRegistry() { return { hasCapability: () => false }; },
  }), /repo root invalid/);
});

test("production general money worker injects Railway opportunity functions without Supabase", async () => {
  const dataDir = fs.mkdtempSync(path.join(os.tmpdir(), "lm-runtime-money-cloud-"));
  const geminiKey = "gemini-secret-key";
  let options;
  const specialist = async () => ({
    kind: "general_agent_work",
    status: "completed",
    tenant_id: MONEY_TENANT,
    job_id: MONEY_JOB_ID,
    goal_ref: MONEY_GOAL_REF,
    execution_id: "execution-runtime-cloud-1",
    next_job_refs: [],
  });
  const handlers = createWorkerHandlers({
    LM_DATA_DIR: dataDir,
    GEMINI_API_KEY: geminiKey,
  }, ["general-agent.work"], {
    async query(sql) {
      if (sql.includes("WITH updated AS")) {
        return { rows: [{
          uid: MONEY_TENANT, opportunity_id: MONEY_OPPORTUNITY_ID, goal_ref: MONEY_GOAL_REF,
          source_url: "https://public.example/opportunity", title: "Public opportunity",
          goal_statement: "Complete it.", value_minor: "50000", currency: "JPY", status: "QUALIFIED",
        }] };
      }
      return { rows: [{
        uid: MONEY_TENANT, opportunity_id: MONEY_OPPORTUNITY_ID, goal_ref: MONEY_GOAL_REF,
        source_url: "https://public.example/opportunity", title: "Public opportunity",
        goal_statement: "Complete it.", value_minor: "50000", currency: "JPY", status: "DISCOVERED",
      }] };
    },
    createMoneyPrinterSpecialist(input) {
      options = input;
      return specialist;
    },
    createRegistry({ servicesByAdapter }) {
      const services = servicesByAdapter["general-agent-work"];
      return {
        hasCapability: (capability) => capability === "general-agent.work",
        getByCapability: () => ({
          execute: async (job) => ({
            receipt: await services.runBoundedSpecialist({
              tenant_id: job.tenant_id,
              job_id: job.job_id,
              goal_ref: job.input_refs.goal_ref,
            }),
          }),
        }),
      };
    },
  });

  assert.equal(options.geminiKey, geminiKey);
  assert.equal(options.supaUrl, undefined);
  assert.equal(options.supaKey, undefined);
  assert.equal(typeof options.readOpportunity, "function");
  assert.equal(typeof options.updateOpportunity, "function");
  assert.equal((await options.readOpportunity({
    tenant_id: MONEY_TENANT, opportunity_id: MONEY_OPPORTUNITY_ID, goal_ref: MONEY_GOAL_REF,
  })).status, "DISCOVERED");
  assert.equal((await options.updateOpportunity({
    tenant_id: MONEY_TENANT, opportunity_id: MONEY_OPPORTUNITY_ID, goal_ref: MONEY_GOAL_REF,
  }, "QUALIFIED")).status, "QUALIFIED");
  assert.doesNotMatch(JSON.stringify(await handlers["general-agent.work"]({
    tenant_id: MONEY_TENANT,
    job_id: MONEY_JOB_ID,
    capability: "general-agent.work",
    input_refs: { goal_ref: MONEY_GOAL_REF },
  })), new RegExp(geminiKey));
});

test("coverage worker assembles production services from its query and connect boundaries", () => {
  const query = async () => {};
  const connect = async () => {};
  const assembled = { coverageStore: {}, refreshCoverage: async () => {} };
  let observedRuntime;
  let observedServices;
  createWorkerHandlers({ LM_RUNTIME_TENANT_ID: "dais-local" }, ["connector.coverage.refresh"], {
    query,
    connect,
    createConnectorCoverageRuntimeServices(env, runtime) {
      assert.equal(env.LM_RUNTIME_TENANT_ID, "dais-local");
      observedRuntime = runtime;
      return assembled;
    },
    createRegistry({ servicesByAdapter }) {
      observedServices = servicesByAdapter["connector-coverage-refresh"];
      return {
        hasCapability() { return true; },
        getByCapability() { return { execute: async () => ({ receipt: {} }) }; },
      };
    },
  });
  assert.deepEqual(observedRuntime, { query, connect });
  assert.equal(observedServices, assembled);
});

test("compose topology has durable stores, health checks, distinct roles, and one scheduler owner", () => {
  assert.deepEqual(validateComposeModel(validModel()), {
    schedulerService: "scheduler",
    schedulerOwner: "local-primary",
    workerServices: ["worker"],
  });

  const duplicate = validModel();
  duplicate.services["scheduler-copy"] = healthyService({
    LM_DEPLOYMENT_ROLE: "scheduler",
    LM_SCHEDULER_OWNER: "local-copy",
    LIFE_RUN_LOOPS: "true",
  });
  assert.throws(() => validateComposeModel(duplicate), /exactly one scheduler/i);

  const noVolume = validModel();
  delete noVolume.volumes["object-data"];
  assert.throws(() => validateComposeModel(noVolume), /object-data/i);
});

test("committed local compose is self-contained and never references a legacy runtime", () => {
  const compose = fs.readFileSync(COMPOSE_PATH, "utf8");
  for (const service of [
    "postgres",
    "object-store",
    "migrate",
    "runtime-init",
    "api",
    "scheduler",
    "marketing-liveness",
    "worker",
  ]) {
    assert.match(compose, new RegExp(`^  ${service}:`, "m"));
  }
  assert.match(compose, /healthcheck:/);
  assert.match(compose, /condition: service_healthy/);
  assert.match(compose, /condition: service_completed_successfully/);
  assert.match(compose, /^  postgres-data:/m);
  assert.match(compose, /^  object-data:/m);
  assert.match(compose, /^  runtime-data:/m);
  assert.match(compose, /LM_SCHEDULER_OWNER: local-primary/);
  assert.match(compose, /LM_RUNTIME_TENANT_ID: \$\{LM_RUNTIME_TENANT_ID:-\}/);
  assert.match(
    compose,
    /\$\{LM_LOCAL_WORKER_HEALTH_PORT:-18790\}:8790/,
  );
  assert.match(
    compose,
    /LM_FINANCIAL_REPORT_POLL_MS: \$\{LM_FINANCIAL_REPORT_POLL_MS:-300000\}/,
  );
  assert.match(
    compose,
    /LM_MARKETING_PUBLICATION_CHAIN_ENABLED: \$\{LM_MARKETING_PUBLICATION_CHAIN_ENABLED:-false\}/,
  );
  assert.match(
    compose,
    /LM_MARKETING_PUBLICATION_CHAIN_AFTER: \$\{LM_MARKETING_PUBLICATION_CHAIN_AFTER:-\}/,
  );
  assert.match(
    compose,
    /LM_MARKETING_OBSERVATION_ENABLED: \$\{LM_MARKETING_OBSERVATION_ENABLED:-false\}/,
  );
  assert.match(
    compose,
    /LM_MARKETING_OBSERVATION_PRODUCT_ID: \$\{LM_MARKETING_OBSERVATION_PRODUCT_ID:-\}/,
  );
  assert.match(
    compose,
    /LM_WORKER_CAPABILITIES: \$\{LM_WORKER_CAPABILITIES:-runtime\.noop,marketing\.liveness\.telegram,general-agent\.work\}/,
  );
  assert.match(compose, /command: \["node", "scripts\/runtime-up\.js", "internal-liveness"\]/);
  assert.match(compose, /LM_MARKETING_LIVENESS_LANES_JSON: \$\{LM_MARKETING_LIVENESS_LANES_JSON:-\[\]\}/);
  assert.match(compose, /LM_TELEGRAM_ALERT_CHAT_ID: \$\{LM_TELEGRAM_ALERT_CHAT_ID:-\}/);
  assert.match(compose, /^  worker:\n(?:.*\n){0,4}    build: \*runtime-build/m);
  assert.match(compose, /LM_TELEGRAM_BOT_TOKEN: \$\{LM_TELEGRAM_BOT_TOKEN:-\}/);
  assert.doesNotMatch(
    compose,
    /\.openclaw|profitable-claude|life-manager-v0|\/Users\/anicca/i,
  );
});

test("scheduler lease uses row ownership and atomic conflict handling without advisory locks", () => {
  const sql = fs.readFileSync(LEASE_MIGRATION, "utf8");
  assert.match(sql, /CREATE TABLE IF NOT EXISTS public\.lm_runtime_scheduler_leases/i);
  assert.match(sql, /scheduler_key text PRIMARY KEY|PRIMARY KEY \(scheduler_key\)/i);
  assert.match(sql, /ON CONFLICT \(scheduler_key\) DO UPDATE/i);
  assert.match(sql, /lease_expires_at <= clock_timestamp\(\)/i);
  assert.match(sql, /RETURNING/i);
  assert.doesNotMatch(sql, /advisory_(?:lock|xact_lock)/i);
});

test("runtime up validates docker compose JSON before starting the stack", () => {
  const calls = [];
  const spawnSync = (command, args) => {
    calls.push({ command, args });
    if (args.includes("config")) {
      return {
        status: 0,
        stdout: JSON.stringify(validModel()),
        stderr: "",
      };
    }
    return { status: 0, stdout: "", stderr: "" };
  };
  const result = runRuntimeUp({
    argv: ["runtime", "up", "--mode", "local"],
    spawnSync,
    repoRoot: ROOT,
  });

  assert.equal(result.ok, true);
  assert.equal(result.schedulerOwner, "local-primary");
  assert.deepEqual(calls.map(({ command }) => command), ["docker", "docker"]);
  assert.deepEqual(calls[0].args.slice(-3), ["config", "--format", "json"]);
  assert.deepEqual(calls[1].args.slice(-4), ["up", "-d", "--build", "--wait"]);
});

test("scheduler holder token changes on every process start even in the same container", () => {
  const ids = ["start-a", "start-b"];
  const randomUUID = () => ids.shift();
  assert.equal(
    buildSchedulerHolderToken("local-primary", "same-container", randomUUID),
    "local-primary:same-container:start-a",
  );
  assert.equal(
    buildSchedulerHolderToken("local-primary", "same-container", randomUUID),
    "local-primary:same-container:start-b",
  );
});

test("daily marketing generation becomes due at 10:15 JST and never before", () => {
  assert.equal(
    marketingGenerationDueDate(Date.parse("2026-07-30T01:14:59.000Z")),
    null,
  );
  assert.equal(
    marketingGenerationDueDate(Date.parse("2026-07-30T01:15:00.000Z")),
    "2026-07-30",
  );
  assert.equal(
    marketingGenerationDueDate(Date.parse("2026-07-30T14:59:00.000Z")),
    "2026-07-30",
  );
});

test("publication chain scans only one tenant and an explicit non-backfill window", async () => {
  const calls = [];
  const pool = {
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [{ receipt: { kind: "marketing_daily_generation" } }] };
    },
  };
  const rows = await listGenerationReceipts(pool, {
    tenantId: "tenant-a",
    after: "2026-08-01T00:00:00.000Z",
  });

  assert.deepEqual(rows, [{ kind: "marketing_daily_generation" }]);
  assert.match(calls[0].sql, /j\.tenant_id = \$1/);
  assert.match(calls[0].sql, /r\.outcome = 'completed'/);
  assert.match(calls[0].sql, /r\.created_at >= \$2::timestamptz/);
  assert.match(calls[0].sql, /LIMIT 100/);
  assert.deepEqual(calls[0].params, [
    "tenant-a",
    "2026-08-01T00:00:00.000Z",
  ]);
});

test("observation chain scans only observable publication receipts in one tenant window", async () => {
  const calls = [];
  const pool = {
    async query(sql, params) {
      calls.push({ sql, params });
      return {
        rows: [{
          job_id: `marketing-daily:${"c".repeat(64)}`,
          receipt: { kind: "marketing_daily_distribution" },
        }],
      };
    },
  };
  const rows = await listObservablePublicationReceipts(pool, {
    tenantId: "tenant-a",
    after: "2026-08-01T00:00:00.000Z",
  });

  assert.equal(rows.length, 1);
  assert.match(calls[0].sql, /j\.tenant_id = \$1/);
  assert.match(
    calls[0].sql,
    /j\.capability = 'marketing\.life-manager\.daily\.publish'/,
  );
  assert.match(calls[0].sql, /r\.outcome = 'completed'/);
  assert.match(calls[0].sql, /provider_post_id/);
  assert.match(calls[0].sql, /provider_route/);
  assert.match(calls[0].sql, /r\.created_at >= \$2::timestamptz/);
  assert.match(calls[0].sql, /ORDER BY r\.created_at DESC/);
  assert.deepEqual(calls[0].params, [
    "tenant-a",
    "2026-08-01T00:00:00.000Z",
  ]);
});

test("honne JA shadow scan is scoped to one tenant/product/format/locale and an explicit window", async () => {
  const calls = [];
  const pool = {
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [{ receipt: { kind: "marketing_video_artifact" } }] };
    },
  };
  const rows = await listHonneJaShadowGenerationReceipts(pool, {
    tenantId: "tenant-a",
    productId: "honne-ai",
    formatId: "reelclaw",
    locale: "ja",
    after: "2026-07-30T00:00:00.000Z",
  });

  assert.deepEqual(rows, [{ kind: "marketing_video_artifact" }]);
  assert.match(calls[0].sql, /j\.tenant_id = \$1/);
  assert.match(calls[0].sql, /j\.capability = 'marketing\.video\.generate'/);
  assert.match(calls[0].sql, /r\.outcome = 'completed'/);
  assert.match(calls[0].sql, /r\.receipt->>'status' = 'ready'/);
  assert.match(calls[0].sql, /r\.created_at >= \$2::timestamptz/);
  assert.deepEqual(calls[0].params, [
    "tenant-a",
    "2026-07-30T00:00:00.000Z",
    "honne-ai",
    "reelclaw",
    "ja",
  ]);

  await assert.rejects(
    listHonneJaShadowGenerationReceipts(pool, {
      tenantId: "tenant-a",
      productId: "honne-ai",
      formatId: "reelclaw",
      locale: "ja",
      after: "not-a-boundary",
    }),
    /honne JA shadow scan boundary is invalid/,
  );
  await assert.rejects(
    listHonneJaShadowGenerationReceipts(pool, {
      tenantId: "tenant-a",
      productId: "",
      formatId: "reelclaw",
      locale: "ja",
      after: "2026-07-30T00:00:00.000Z",
    }),
    /honne JA shadow scan boundary is invalid/,
  );
});

test("marketing liveness receipt scan ranks per lane so unrelated volume cannot create a false miss", async () => {
  const calls = [];
  const rows = [{ receipt: { product_id: "honne-ai", locale: "en", platform: "tiktok" } }];
  const result = await listMarketingVideoPublicationReceipts({
    async query(sql, params) { calls.push({ sql, params }); return { rows }; },
  }, "tenant-a", "2026-08-20T00:00:00.000Z", [
    { product: "honne-ai", locale: "en", platform: "tiktok" },
    { product: "anicca", locale: "ja", platform: "tiktok" },
  ]);
  assert.deepEqual(result, rows.map(({ receipt }) => receipt));
  assert.match(calls[0].sql, /row_number\(\) OVER[\s\S]*PARTITION BY[\s\S]*lane_rank <= 100/i);
  assert.match(calls[0].sql, /jsonb_to_recordset\(\$3::jsonb\)/i);
  assert.doesNotMatch(calls[0].sql, /LIMIT 1000/i);
  assert.deepEqual(JSON.parse(calls[0].params[2]), [
    { product: "honne-ai", locale: "en", platform: "tiktok" },
    { product: "anicca", locale: "ja", platform: "tiktok" },
  ]);
});

test("capability worker completes a registered financial report with only its safe receipt", async () => {
  const calls = [];
  const job = {
    tenant_id: "tenant-a",
    job_id: "job-a",
    attempt: 1,
    capability: "report.financial.telegram",
    effect_class: "message",
  };
  await executeCapabilityJob(job, {
    workerId: "worker-a",
    handlers: {
      "report.financial.telegram": async () => ({
        receipt: {
          kind: "telegram_financial_report",
          message_id: 44,
          snapshot_hash: "a".repeat(64),
        },
      }),
    },
    completeJob: async (input) => calls.push({ kind: "complete", input }),
    failJob: async (input) => calls.push({ kind: "fail", input }),
  });

  assert.equal(calls.length, 1);
  assert.equal(calls[0].kind, "complete");
  assert.deepEqual(calls[0].input.receipt, {
    kind: "telegram_financial_report",
    message_id: 44,
    snapshot_hash: "a".repeat(64),
  });
});

test("marketing liveness worker resolves only Life Manager Telegram refs and uses fake transport", async () => {
  const sent = [];
  const handlers = createWorkerHandlers({
    LM_RUNTIME_TENANT_ID: "tenant-a",
    LM_TELEGRAM_BOT_TOKEN: "fake-token",
    LM_TELEGRAM_ALERT_CHAT_ID: "fake-chat",
  }, ["marketing.liveness.telegram"], {
    createRegistry({ servicesByAdapter }) {
      const services = servicesByAdapter["marketing-liveness-telegram"];
      return {
        hasCapability: () => true,
        getByCapability: () => ({
          execute: async (job) => {
            const token = await services.secretProvider.get(job.tenant_id, job.input_refs.telegram_token_ref);
            const chat = await services.chatProvider.get(job.tenant_id, job.input_refs.telegram_chat_ref);
            sent.push({ token, chat });
            return { receipt: { kind: "fake_marketing_liveness" } };
          },
        }),
      };
    },
  });
  const job = {
    tenant_id: "tenant-a",
    capability: "marketing.liveness.telegram",
    input_refs: {
      telegram_token_ref: "secret://telegram/bot-token",
      telegram_chat_ref: "telegram-chat://owner",
    },
  };
  await handlers["marketing.liveness.telegram"](job);
  assert.deepEqual(sent, [{ token: "fake-token", chat: "fake-chat" }]);
  await assert.rejects(() => handlers["marketing.liveness.telegram"]({
    ...job, tenant_id: "other-tenant",
  }), /secret scope mismatch/i);
});

test("a registered no-effect capability executes its adapter instead of becoming a runtime noop", async () => {
  const calls = [];
  await executeCapabilityJob({
    tenant_id: "tenant-a",
    job_id: "generation-a",
    attempt: 1,
    capability: "marketing.life-manager.daily.generate",
    effect_class: "none",
  }, {
    workerId: "worker-a",
    handlers: {
      "marketing.life-manager.daily.generate": async () => ({
        receipt: { kind: "marketing_daily_generation", status: "rendered" },
      }),
    },
    completeJob: async (input) => calls.push({ kind: "complete", input }),
    failJob: async (input) => calls.push({ kind: "fail", input }),
  });

  assert.equal(calls.length, 1);
  assert.equal(calls[0].kind, "complete");
  assert.equal(calls[0].input.receipt.kind, "marketing_daily_generation");
});

test("coverage worker persists a bounded stage code without raw provider errors", async () => {
  const calls = [];
  const error = new Error("Connector coverage refresh unavailable");
  error.code = "CONNECTOR_COVERAGE_INVENTORY_FAILED";
  await executeCapabilityJob({
    tenant_id: "dais-local",
    job_id: `connector-coverage:${"c".repeat(64)}`,
    attempt: 1,
    capability: "connector.coverage.refresh",
    effect_class: "none",
  }, {
    workerId: "connector-local",
    handlers: { "connector.coverage.refresh": async () => { throw error; } },
    completeJob: async (input) => calls.push({ kind: "complete", input }),
    failJob: async (input) => calls.push({ kind: "fail", input }),
  });
  assert.deepEqual(calls.map(({ kind }) => kind), ["fail"]);
  assert.equal(calls[0].input.errorCode, "CONNECTOR_COVERAGE_INVENTORY_FAILED");
  assert.equal(calls[0].input.unknownEffect, false);
});

test("outbound Luma worker persists only an allowlisted provider state code", async () => {
  for (const [providerCode, expectedCode, unknownEffect] of [
    ["LUMA_LOGIN_REQUIRED", "LUMA_LOGIN_REQUIRED", false],
    ["LUMA_RSVP_UNAVAILABLE", "LUMA_RSVP_UNAVAILABLE", false],
    ["LUMA_EFFECT_UNKNOWN", "LUMA_EFFECT_UNKNOWN", true],
    ["LUMA_PRIVATE_PROVIDER_DETAIL", "CAPABILITY_EXECUTION_FAILED", false],
  ]) {
    const calls = [];
    const error = new Error("private page text");
    error.code = providerCode;
    error.unknownEffect = unknownEffect;
    await executeCapabilityJob({
      tenant_id: "dais-local",
      job_id: `outbound-event:${"d".repeat(64)}`,
      attempt: 1,
      capability: "outbound.event.apply",
      effect_class: "publish",
    }, {
      workerId: "connector-local",
      handlers: { "outbound.event.apply": async () => { throw error; } },
      completeJob: async (input) => calls.push({ kind: "complete", input }),
      failJob: async (input) => calls.push({ kind: "fail", input }),
    });
    assert.deepEqual(calls.map(({ kind }) => kind), ["fail"]);
    assert.equal(calls[0].input.errorCode, expectedCode);
    assert.equal(calls[0].input.unknownEffect, unknownEffect);
    assert.doesNotMatch(JSON.stringify(calls), /private page text/);
  }
});

test("external-effect execution heartbeats its lease before recording completion", async () => {
  const calls = [];
  let scheduledHeartbeat;
  const job = {
    tenant_id: "dais",
    job_id: `outbound-event:${"d".repeat(64)}`,
    attempt: 1,
    capability: "outbound.event.apply",
    effect_class: "publish",
  };
  const receipt = await verifiedOutboundReceipt(job);
  await executeCapabilityJob(job, {
    workerId: "connector-local",
    handlers: {
      "outbound.event.apply": async () => {
        await scheduledHeartbeat();
        return { receipt };
      },
    },
    heartbeatJob: async (input) => calls.push({ kind: "heartbeat", input }),
    completeJob: async (input) => calls.push({ kind: "complete", input }),
    failJob: async (input) => calls.push({ kind: "fail", input }),
    leaseSeconds: 90,
    setIntervalFn(callback) {
      scheduledHeartbeat = callback;
      return "heartbeat-timer";
    },
    clearIntervalFn(timer) {
      calls.push({ kind: "clear", timer });
    },
  });

  assert.deepEqual(calls.map(({ kind }) => kind), ["heartbeat", "clear", "complete"]);
  assert.deepEqual(calls[0].input, {
    tenantId: "dais",
    jobId: `outbound-event:${"d".repeat(64)}`,
    attempt: 1,
    workerId: "connector-local",
    leaseSeconds: 90,
  });
});

test("outbound handlerのbare successはcompletedにせずunknown effectへ落とす", async () => {
  const calls = [];
  await executeCapabilityJob({
    tenant_id: "dais",
    job_id: `outbound-event:${"1".repeat(64)}`,
    attempt: 1,
    capability: "outbound.event.apply",
    effect_class: "publish",
  }, {
    workerId: "connector-local",
    handlers: {
      "outbound.event.apply": async () => ({
        receipt: { status: "success" },
      }),
    },
    completeJob: async (input) => calls.push({ kind: "complete", input }),
    failJob: async (input) => calls.push({ kind: "fail", input }),
  });
  assert.deepEqual(calls.map(({ kind }) => kind), ["fail"]);
  assert.equal(calls[0].input.errorCode, "CAPABILITY_EXECUTION_FAILED");
  assert.equal(calls[0].input.unknownEffect, true);
});

test("a lost heartbeat fails an external-effect attempt as unknown", async () => {
  const calls = [];
  let scheduledHeartbeat;
  await executeCapabilityJob({
    tenant_id: "dais",
    job_id: `outbound-event:${"e".repeat(64)}`,
    attempt: 1,
    capability: "outbound.event.apply",
    effect_class: "publish",
  }, {
    workerId: "connector-local",
    handlers: {
      "outbound.event.apply": async () => {
        await scheduledHeartbeat();
        return { receipt: { kind: "event_application", status: "submitted" } };
      },
    },
    heartbeatJob: async () => {
      throw new Error("runtime heartbeat lost lease");
    },
    completeJob: async (input) => calls.push({ kind: "complete", input }),
    failJob: async (input) => calls.push({ kind: "fail", input }),
    leaseSeconds: 90,
    setIntervalFn(callback) {
      scheduledHeartbeat = callback;
      return "heartbeat-timer";
    },
    clearIntervalFn(timer) {
      calls.push({ kind: "clear", timer });
    },
  });

  assert.deepEqual(calls.map(({ kind }) => kind), ["clear", "fail"]);
  assert.equal(calls[1].input.errorCode, "CAPABILITY_HEARTBEAT_FAILED");
  assert.equal(calls[1].input.unknownEffect, true);
});

test("adapter failure cannot make a simultaneous lost heartbeat retryable", async () => {
  const calls = [];
  let scheduledHeartbeat;
  await executeCapabilityJob({
    tenant_id: "dais",
    job_id: `outbound-event:${"f".repeat(64)}`,
    attempt: 1,
    capability: "outbound.event.apply",
    effect_class: "publish",
  }, {
    workerId: "connector-local",
    handlers: {
      "outbound.event.apply": async () => {
        await scheduledHeartbeat();
        throw new Error("browser result unavailable");
      },
    },
    heartbeatJob: async () => {
      throw new Error("runtime heartbeat lost lease");
    },
    completeJob: async (input) => calls.push({ kind: "complete", input }),
    failJob: async (input) => calls.push({ kind: "fail", input }),
    leaseSeconds: 90,
    setIntervalFn(callback) {
      scheduledHeartbeat = callback;
      return "heartbeat-timer";
    },
    clearIntervalFn() {},
  });

  assert.deepEqual(calls.map(({ kind }) => kind), ["fail"]);
  assert.equal(calls[0].input.errorCode, "CAPABILITY_HEARTBEAT_FAILED");
  assert.equal(calls[0].input.unknownEffect, true);
});

test("environment secret provider is tenant-scoped and resolves only declared refs", async () => {
  const provider = createScopedEnvironmentSecretProvider({
    LM_RUNTIME_TENANT_ID: "tenant-a",
    LM_TELEGRAM_BOT_TOKEN: "private-token",
  });

  assert.equal(
    await provider.get("tenant-a", "secret://telegram/bot-token"),
    "private-token",
  );
  await assert.rejects(
    provider.get("tenant-b", "secret://telegram/bot-token"),
    /tenant/i,
  );
  await assert.rejects(
    provider.get("tenant-a", "secret://telegram/raw-token"),
    /reference/i,
  );
});

test("worker handlers are routed through the configured loop adapter registry", async () => {
  const calls = [];
  const handlers = createWorkerHandlers(
    { LM_RUNTIME_TENANT_ID: "tenant-a" },
    ["fixture.execute"],
    {
      createRegistry({ servicesByAdapter }) {
        calls.push({ kind: "registry", servicesByAdapter });
        return {
          hasCapability: (capability) => capability === "fixture.execute",
          getByCapability: () => ({
            execute: async (job) => {
              calls.push({ kind: "execute", job });
              return { receipt: { kind: "fixture" } };
            },
          }),
        };
      },
    },
  );

  assert.equal(typeof handlers["fixture.execute"], "function");
  assert.deepEqual(
    await handlers["fixture.execute"]({ job_id: "job-a" }),
    { receipt: { kind: "fixture" } },
  );
  assert.equal(calls[0].kind, "registry");
  assert.deepEqual(calls[1], {
    kind: "execute",
    job: { job_id: "job-a" },
  });
});

test("outbound event worker wires the Luma browser provider and tenant evidence readers", async () => {
  const provider = {
    async inspectRegistration() {},
    async submitRegistration() {},
  };
  const evidenceStore = {
    async readExternalReceipt() {},
    async readArtifact() {},
  };
  const fetchImpl = async () => {};
  const now = () => "2026-08-01T10:00:00.000Z";
  let services;
  const handlers = createWorkerHandlers({
    LM_RUNTIME_TENANT_ID: "tenant-a",
    LM_DATA_DIR: "/var/lib/life-manager/data",
  }, ["outbound.event.apply"], {
    lumaProvider: provider,
    lumaEvidenceStore: evidenceStore,
    fetchImpl,
    now,
    createRegistry({ servicesByAdapter }) {
      services = servicesByAdapter["outbound-luma-rsvp"];
      return {
        hasCapability: (capability) => capability === "outbound.event.apply",
        getByCapability: () => ({
          execute: async () => ({ receipt: { kind: "fixture" } }),
        }),
      };
    },
  });

  assert.equal(typeof handlers["outbound.event.apply"], "function");
  assert.equal(services.provider, provider);
  assert.equal(services.readExternalReceipt, evidenceStore.readExternalReceipt);
  assert.equal(services.readArtifact, evidenceStore.readArtifact);
  assert.equal(services.fetchImpl, fetchImpl);
  assert.equal(services.now, now);
});

test("outbound event worker obtains its provider from the canonical events pack", () => {
  const dailyDriver = { withLumaPage: async () => {} };
  const auth = { ensureAuthenticated: async () => ({ status: "authenticated" }) };
  const provider = { inspectRegistration: async () => {}, submitRegistration: async () => {} };
  let composition;
  let services;
  const readLumaFormProfile = () => ({ form_answers: {} });
  createWorkerHandlers({
    LM_RUNTIME_TENANT_ID: "tenant-a",
    LM_DATA_DIR: "/var/lib/life-manager/data",
  }, ["outbound.event.apply"], {
    lumaDailyDriver: dailyDriver,
    lumaAuth: auth,
    lumaEvidenceStore: {
      record: async () => {},
      readExternalReceipt: async () => {},
      readArtifact: async () => {},
    },
    createConnectorEventsPack(input) {
      composition = input;
      return { provider };
    },
    readLumaFormProfile,
    createRegistry({ servicesByAdapter }) {
      services = servicesByAdapter["outbound-luma-rsvp"];
      return { hasCapability: () => false };
    },
  });
  assert.equal(composition.dailyDriver, dailyDriver);
  assert.equal(composition.auth, auth);
  assert.equal(composition.readLumaFormProfile, readLumaFormProfile);
  assert.equal(services.provider, provider);
});

test("outbound event worker lazily reads its private Luma form profile from the durable data root", () => {
  let reader;
  const calls = [];
  createWorkerHandlers({
    LM_RUNTIME_TENANT_ID: "tenant-a",
    LM_DATA_DIR: "/var/lib/life-manager/data",
  }, ["outbound.event.apply"], {
    lumaDailyDriver: { withLumaPage: async () => {} },
    lumaAuth: { ensureAuthenticated: async () => ({ status: "authenticated" }) },
    lumaEvidenceStore: {
      record: async () => {}, readExternalReceipt: async () => {}, readArtifact: async () => {},
    },
    readPrivateLumaFormProfile(input) {
      calls.push(input);
      return { form_answers: {} };
    },
    createConnectorEventsPack(input) {
      reader = input.readLumaFormProfile;
      return { provider: { inspectRegistration: async () => {}, submitRegistration: async () => {} } };
    },
    createRegistry() { return { hasCapability: () => false }; },
  });

  assert.equal(calls.length, 0);
  assert.deepEqual(reader(), { form_answers: {} });
  assert.deepEqual(calls, [{ path: "/var/lib/life-manager/data/private/connector-luma-form-profile.json" }]);
});

test("marketing observation worker reads one tenant receipt and preserves empty analytics as unavailable", async () => {
  const publicationJobId = `marketing-daily:${"a".repeat(64)}`;
  const calls = [];
  const handlers = createWorkerHandlers(
    {
      LM_RUNTIME_TENANT_ID: "tenant-a",
      LM_POSTIZ_API_KEY: "private-postiz-token",
    },
    ["marketing.observation.collect"],
    {
      async query(sql, params) {
        calls.push({ kind: "query", sql, params });
        return {
          rows: [{
            receipt: {
              schema_version: 1,
              kind: "marketing_daily_distribution",
              status: "published",
              creative_id: "B01",
              platform: "tiktok",
              video_sha256: "b".repeat(64),
              caption_sha256: "c".repeat(64),
              public_url: "https://www.tiktok.com/@life_manager/video/7999999999999999999",
              provider_post_id: "postiz-post-B01",
              provider_route: "postiz",
              provider_reconciled: false,
              published_at: "2026-07-29T12:00:00.000Z",
            },
          }],
        };
      },
      async fetchImpl(url, options) {
        calls.push({
          kind: "fetch",
          url,
          authorizationPresent: options.headers.Authorization.length > 0,
        });
        return {
          ok: true,
          async json() {
            return [];
          },
        };
      },
      now: () => "2026-07-29T14:01:00.000Z",
    },
  );
  const execution = await handlers["marketing.observation.collect"](
    buildMarketingObservationJob({
      tenantId: "tenant-a",
      productId: "life-manager",
      publicationJobId,
      window: "2h",
    }),
  );

  assert.equal(execution.receipt.status, "insufficient");
  assert.equal(execution.receipt.metrics.platform.views.value, null);
  assert.equal(execution.receipt.metrics.product.installs.value, null);
  assert.equal(calls.filter((call) => call.kind === "query").length, 1);
  assert.equal(calls.filter((call) => call.kind === "fetch").length, 1);
  assert.match(calls.find((call) => call.kind === "fetch").url, /analytics\/post\/postiz-post-B01/);
  assert.equal(calls.find((call) => call.kind === "fetch").authorizationPresent, true);
  assert.doesNotMatch(JSON.stringify(execution), /private-postiz-token/);
});

test("marketing video worker selects from tenant-scoped durable history and Life Manager objects", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-runtime-video-"));
  const objectDir = path.join(root, "objects");
  const packPath = path.join(root, "pack.json");
  const mediaPath = path.join(root, "v1.mp4");
  fs.writeFileSync(packPath, `${JSON.stringify({
    schema_version: 1,
    product_id: "honne-ai",
    format_id: "reelclaw",
    form: "relationship-confession",
    locale: "ja",
    title: "Honne",
    hashtags: [],
    hooks: [
      { id: "HJA-001", text: "first", status: "active", prior_used_at: null },
    ],
  })}\n`);
  fs.writeFileSync(mediaPath, Buffer.from("0000ftyp-video"));
  const pack = importContentObject(packPath, { objectDir });
  const media = importContentObject(mediaPath, { objectDir });
  const calls = [];
  const handlers = createWorkerHandlers({
    LM_RUNTIME_TENANT_ID: "tenant-a",
    LM_DATA_DIR: root,
  }, ["marketing.video.generate"], {
    async query(sql, params) {
      calls.push({ sql, params });
      return { rows: [] };
    },
    now: () => "2026-07-30T12:30:01.000Z",
  });
  const execution = await handlers["marketing.video.generate"](
    buildMarketingVideoGenerationJob({
      tenantId: "tenant-a",
      productId: "honne-ai",
      formatId: "reelclaw",
      locale: "ja",
      slot: "2026-07-30T12:30:00.000Z",
      packRef: pack.ref,
      mediaRefs: [media.ref],
    }),
  );

  assert.equal(execution.receipt.kind, "marketing_video_artifact");
  assert.equal(execution.receipt.hook_id, "HJA-001");
  assert.equal(calls.length, 1);
  assert.match(calls[0].sql, /tenant_id = \$1/);
  assert.match(calls[0].sql, /capability = 'marketing\.video\.generate'/);
  assert.match(calls[0].sql, /receipt->>'product_id' = \$2/);
  assert.deepEqual(calls[0].params, [
    "tenant-a",
    "honne-ai",
    "reelclaw",
    "ja",
  ]);
});

test("marketing video publication worker wires the Honne EN profile and TikTok integration scopes", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "lm-runtime-publish-"));
  let services;
  const handlers = createWorkerHandlers({
    LM_RUNTIME_TENANT_ID: "tenant-a",
    LM_DATA_DIR: root,
    LM_HONNE_EN_INSTAGRAM_PROFILE_REF: "profile://instagram/honne_reveal",
    LM_HONNE_EN_TIKTOK_INTEGRATION_REF: "integration://postiz/tiktok/cmoig11ew001zlv0yk6vqo1us",
    LM_INSTAGRAM_HANDLE: "honne_reveal",
    LM_INSTAGRAM_ACCOUNTS_PATH: path.join(root, "accounts.json"),
    LM_INSTAGRAM_SETTINGS_PATH: path.join(root, "settings.json"),
    LM_INSTAGRAM_CREDENTIALS_PATH: path.join(root, "credentials.json"),
    LM_INSTAGRAM_PROFILE_STATE_DIR: path.join(root, "profile"),
    LM_TIKTOK_INTEGRATION: "provider-integration-value",
  }, ["marketing.video.publish"], {
    createRegistry({ servicesByAdapter }) {
      services = servicesByAdapter["marketing-video-publication"];
      return {
        hasCapability: (capability) => capability === "marketing.video.publish",
        getByCapability: () => ({ execute: async () => ({ receipt: { kind: "fixture" } }) }),
      };
    },
  });
  assert.equal(typeof handlers["marketing.video.publish"], "function");
  assert.equal(typeof services.profileProvider.get, "function");
  assert.equal(typeof services.integrationProvider.get, "function");
  assert.equal(typeof services.secretProvider.get, "function");
});
