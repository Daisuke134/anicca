"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {
  parseRuntimeCommand,
  validateComposeModel,
  runRuntimeUp,
  buildSchedulerHolderToken,
  executeCapabilityJob,
  createScopedEnvironmentSecretProvider,
} = require("./runtime-up.js");

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
