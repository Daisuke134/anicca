#!/usr/bin/env node
"use strict";

const path = require("node:path");
const http = require("node:http");
const os = require("node:os");
const { randomUUID } = require("node:crypto");
const { spawn, spawnSync: realSpawnSync } = require("node:child_process");

const REQUIRED_SERVICES = [
  "postgres",
  "object-store",
  "migrate",
  "api",
  "scheduler",
  "worker",
];

function parseRuntimeCommand(argv) {
  if (
    !Array.isArray(argv)
    || argv[0] !== "runtime"
    || argv[1] !== "up"
    || argv[2] !== "--mode"
  ) {
    throw new Error("usage: life-manager runtime up --mode local");
  }
  if (argv[3] !== "local" || argv.length !== 4) {
    throw new Error("runtime up currently supports local mode only");
  }
  return { command: "up", mode: "local" };
}

function environmentObject(environment) {
  if (!environment) return {};
  if (!Array.isArray(environment)) return environment;
  return Object.fromEntries(environment.map((entry) => {
    const separator = String(entry).indexOf("=");
    return separator < 0
      ? [String(entry), ""]
      : [String(entry).slice(0, separator), String(entry).slice(separator + 1)];
  }));
}

function validateComposeModel(model) {
  if (!model || !model.services || !model.volumes) {
    throw new Error("local compose model is incomplete");
  }
  for (const service of REQUIRED_SERVICES) {
    if (!model.services[service]) throw new Error(`local compose missing ${service}`);
  }
  for (const service of ["postgres", "object-store", "api", "scheduler", "worker"]) {
    if (!model.services[service].healthcheck) {
      throw new Error(`local compose ${service} healthcheck missing`);
    }
  }
  for (const volume of ["postgres-data", "object-data", "runtime-data"]) {
    if (!Object.prototype.hasOwnProperty.call(model.volumes, volume)) {
      throw new Error(`local compose ${volume} volume missing`);
    }
  }
  const roles = Object.entries(model.services).map(([name, service]) => ({
    name,
    env: environmentObject(service.environment),
  }));
  const schedulers = roles.filter(({ env }) => env.LM_DEPLOYMENT_ROLE === "scheduler");
  if (schedulers.length !== 1) {
    throw new Error("local compose must have exactly one scheduler service");
  }
  const schedulerOwner = String(schedulers[0].env.LM_SCHEDULER_OWNER || "").trim();
  if (!schedulerOwner) throw new Error("local compose scheduler owner missing");
  const workerServices = roles
    .filter(({ env }) => env.LM_DEPLOYMENT_ROLE === "worker")
    .map(({ name }) => name);
  if (workerServices.length < 1) throw new Error("local compose worker missing");
  const api = roles.find(({ env }) => env.LM_DEPLOYMENT_ROLE === "api");
  if (!api) throw new Error("local compose api role missing");
  if (String(api.env.LIFE_RUN_LOOPS) !== "false") {
    throw new Error("local compose api must disable scheduler loops");
  }
  if (String(schedulers[0].env.LIFE_RUN_LOOPS) !== "true") {
    throw new Error("local compose scheduler must enable loops");
  }
  return {
    schedulerService: schedulers[0].name,
    schedulerOwner,
    workerServices,
  };
}

function execute(spawnSync, command, args, cwd) {
  const result = spawnSync(command, args, {
    cwd,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
    maxBuffer: 20 * 1024 * 1024,
  });
  if (!result || result.status !== 0) {
    const detail = String((result && result.stderr) || "").trim();
    throw new Error(detail || `${command} failed`);
  }
  return String(result.stdout || "");
}

function runRuntimeUp(options = {}) {
  parseRuntimeCommand(options.argv || []);
  const repoRoot = path.resolve(options.repoRoot || path.join(__dirname, "../../.."));
  const composePath = path.join(repoRoot, "deploy/local/compose.yaml");
  const spawnSync = options.spawnSync || realSpawnSync;
  const base = ["compose", "-f", composePath];
  const rendered = execute(
    spawnSync,
    "docker",
    [...base, "config", "--format", "json"],
    repoRoot,
  );
  let model;
  try {
    model = JSON.parse(rendered);
  } catch {
    throw new Error("docker compose returned invalid JSON");
  }
  const topology = validateComposeModel(model);
  execute(
    spawnSync,
    "docker",
    [...base, "up", "-d", "--build", "--wait"],
    repoRoot,
  );
  return { ok: true, mode: "local", ...topology };
}

function requiredEnv(env, name) {
  const value = String(env[name] || "").trim();
  if (!value) throw new Error(`${name} is required`);
  return value;
}

function buildSchedulerHolderToken(
  ownerId,
  hostname = os.hostname(),
  uuidFactory = randomUUID,
) {
  return `${ownerId}:${hostname}:${uuidFactory()}`;
}

function createHealthServer(port, state) {
  const server = http.createServer((request, response) => {
    if (request.url !== "/health") {
      response.writeHead(404).end("not found");
      return;
    }
    const ok = state.ready === true && state.error == null;
    response.writeHead(ok ? 200 : 503, { "content-type": "application/json" });
    response.end(JSON.stringify({
      ok,
      role: state.role,
      worker_id: state.workerId,
      capabilities: state.capabilities,
      last_poll_at: state.lastPollAt,
    }));
  });
  server.listen(port, "0.0.0.0");
  return server;
}

async function runCapabilityWorker(env = process.env) {
  const { Pool } = require("pg");
  const {
    claimJobs,
    completeJob,
    failJob,
  } = require("../lib/runtime-job-store.js");
  const connectionString = requiredEnv(env, "LM_RUNTIME_DATABASE_URL");
  const capabilities = requiredEnv(env, "LM_WORKER_CAPABILITIES")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  if (capabilities.length < 1) throw new Error("LM_WORKER_CAPABILITIES is empty");
  const workerId = String(env.LM_WORKER_ID || os.hostname()).trim();
  const pool = new Pool({ connectionString, max: 2 });
  const opts = { query: pool.query.bind(pool) };
  const state = {
    role: "worker",
    workerId,
    capabilities,
    ready: false,
    error: null,
    lastPollAt: null,
  };
  const health = createHealthServer(Number(env.LM_WORKER_HEALTH_PORT || 8790), state);
  let active = false;

  async function tick() {
    if (active) return;
    active = true;
    try {
      await pool.query("SELECT 1");
      const jobs = await claimJobs({
        workerId,
        capabilities,
        limit: 1,
        leaseSeconds: 60,
      }, opts);
      for (const job of jobs) {
        if (job.effect_class === "none") {
          await completeJob({
            tenantId: job.tenant_id,
            jobId: job.job_id,
            attempt: job.attempt,
            workerId,
            receipt: {
              kind: "runtime_noop",
              worker_id: workerId,
              completed_at: new Date().toISOString(),
            },
          }, opts);
        } else {
          await failJob({
            tenantId: job.tenant_id,
            jobId: job.job_id,
            attempt: job.attempt,
            workerId,
            errorCode: "CAPABILITY_ADAPTER_UNAVAILABLE",
            unknownEffect: true,
          }, opts);
        }
      }
      state.ready = true;
      state.error = null;
      state.lastPollAt = new Date().toISOString();
    } catch (error) {
      state.error = error;
    } finally {
      active = false;
    }
  }

  await tick();
  const timer = setInterval(tick, Number(env.LM_WORKER_POLL_MS || 1000));
  const stop = async () => {
    clearInterval(timer);
    health.close();
    await pool.end();
  };
  process.once("SIGTERM", () => stop().finally(() => process.exit(0)));
  process.once("SIGINT", () => stop().finally(() => process.exit(0)));
}

async function runSchedulerOwner(env = process.env) {
  const { Pool } = require("pg");
  const connectionString = requiredEnv(env, "LM_RUNTIME_DATABASE_URL");
  const schedulerKey = String(env.LM_SCHEDULER_LEASE_KEY || "primary").trim();
  const ownerId = requiredEnv(env, "LM_SCHEDULER_OWNER");
  const holderToken = buildSchedulerHolderToken(ownerId);
  const leaseSeconds = Number(env.LM_SCHEDULER_LEASE_SECONDS || 30);
  const pool = new Pool({ connectionString, max: 1 });
  const claim = await pool.query(
    "SELECT * FROM public.claim_lm_runtime_scheduler_owner($1, $2, $3, $4)",
    [schedulerKey, ownerId, holderToken, leaseSeconds],
  );
  if (claim.rows.length !== 1) {
    await pool.end();
    throw new Error("scheduler owner lease is already held");
  }

  const child = spawn(process.execPath, ["server.js"], {
    cwd: path.join(__dirname, ".."),
    env: {
      ...env,
      LM_DEPLOYMENT_ROLE: "scheduler",
      LM_SCHEDULER_OWNER: ownerId,
      LIFE_RUN_LOOPS: "true",
    },
    stdio: "inherit",
  });
  let stopping = false;
  const renew = setInterval(async () => {
    try {
      const heartbeat = await pool.query(
        "SELECT * FROM public.heartbeat_lm_runtime_scheduler_owner($1, $2, $3)",
        [schedulerKey, holderToken, leaseSeconds],
      );
      if (heartbeat.rows.length !== 1 && !stopping) child.kill("SIGTERM");
    } catch {
      if (!stopping) child.kill("SIGTERM");
    }
  }, Math.max(1000, Math.floor(leaseSeconds * 1000 / 3)));

  const stop = async (signal) => {
    if (stopping) return;
    stopping = true;
    clearInterval(renew);
    if (!child.killed) child.kill(signal || "SIGTERM");
    try {
      await pool.query(
        "SELECT public.release_lm_runtime_scheduler_owner($1, $2)",
        [schedulerKey, holderToken],
      );
    } finally {
      await pool.end();
    }
  };
  process.once("SIGTERM", () => stop("SIGTERM"));
  process.once("SIGINT", () => stop("SIGINT"));
  child.once("exit", (code, signal) => {
    stop(signal || "SIGTERM").finally(() => {
      process.exitCode = Number.isInteger(code) ? code : 1;
    });
  });
}

async function main(argv = process.argv.slice(2)) {
  if (argv[0] === "internal-worker") return runCapabilityWorker();
  if (argv[0] === "internal-scheduler") return runSchedulerOwner();
  const result = runRuntimeUp({ argv });
  process.stdout.write(`${JSON.stringify(result)}\n`);
  return result;
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  parseRuntimeCommand,
  validateComposeModel,
  runRuntimeUp,
  buildSchedulerHolderToken,
  runCapabilityWorker,
  runSchedulerOwner,
};
