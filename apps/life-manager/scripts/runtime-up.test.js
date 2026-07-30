"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {
  parseRuntimeCommand,
  validateComposeModel,
  runRuntimeUp,
  buildSchedulerHolderToken,
  marketingGenerationDueDate,
  listGenerationReceipts,
  listHonneJaShadowGenerationReceipts,
  listObservablePublicationReceipts,
  executeCapabilityJob,
  createScopedEnvironmentSecretProvider,
  createWorkerHandlers,
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

const ROOT = path.join(__dirname, "../../..");
const COMPOSE_PATH = path.join(ROOT, "deploy/local/compose.yaml");
const LEASE_MIGRATION = path.join(
  __dirname,
  "../migrations/20260729_runtime_scheduler_lease.sql",
);

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
    /LM_WORKER_CAPABILITIES: \$\{LM_WORKER_CAPABILITIES:-runtime\.noop\}/,
  );
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

test("the financial report worker keeps the real send path unless shadow is deliberately enabled", () => {
  const captured = [];
  const baseEnv = {
    LM_RUNTIME_TENANT_ID: "dais-local",
    SUPABASE_URL: "https://example.supabase.co",
    SUPABASE_SERVICE_ROLE_KEY: "service-role",
    LM_DATA_DIR: "/tmp/life-manager-data",
  };
  const registry = {
    hasCapability: () => false,
    getByCapability: () => ({ execute: async () => ({}) }),
  };

  createWorkerHandlers(baseEnv, ["report.financial.telegram"], {
    createRegistry({ servicesByAdapter }) {
      captured.push(servicesByAdapter["financial-report-telegram"]);
      return registry;
    },
  });
  // Any value other than the exact string "true" leaves the real sender wired.
  createWorkerHandlers(
    { ...baseEnv, LM_FINANCIAL_REPORT_SHADOW_ENABLED: "1" },
    ["report.financial.telegram"],
    {
      createRegistry({ servicesByAdapter }) {
        captured.push(servicesByAdapter["financial-report-telegram"]);
        return registry;
      },
    },
  );
  createWorkerHandlers(
    { ...baseEnv, LM_FINANCIAL_REPORT_SHADOW_ENABLED: "true" },
    ["report.financial.telegram"],
    {
      createRegistry({ servicesByAdapter }) {
        captured.push(servicesByAdapter["financial-report-telegram"]);
        return registry;
      },
    },
  );

  assert.equal(captured.length, 3);
  for (const services of captured.slice(0, 2)) {
    assert.equal(services.hold, undefined);
    assert.equal(services.appendHold, undefined);
    assert.equal(typeof services.secretProvider.get, "function");
  }
  assert.equal(captured[2].hold, true);
  assert.equal(typeof captured[2].appendHold, "function");
});
