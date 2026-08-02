"use strict";

const { createHash, randomUUID } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const LOCK_DIR_NAME = "connector.lock";
const OWNER_FILE_NAME = "owner.json";
const HEARTBEAT_FILE_NAME = "heartbeat.json";
const TOKEN = /^[A-Za-z0-9._-]{16,200}$/;
const STAGE = /^[a-z][a-z0-9_]{0,79}$/;

function invalid(message) {
  throw new Error(`Connector native state ${message}`);
}

function stateRoot(value) {
  const root = path.resolve(String(value == null ? "" : value));
  if (!path.isAbsolute(root) || root === path.parse(root).root) invalid("directory invalid");
  return root;
}

function lockPaths(stateDir) {
  const root = stateRoot(stateDir);
  const lockDir = path.join(root, LOCK_DIR_NAME);
  return Object.freeze({
    root,
    lockDir,
    reclaimDir: path.join(root, `${LOCK_DIR_NAME}.reclaim`),
    ownerFile: path.join(lockDir, OWNER_FILE_NAME),
    heartbeatFile: path.join(root, HEARTBEAT_FILE_NAME),
  });
}

function ownerToken(value) {
  const token = String(value == null ? "" : value).trim();
  if (!TOKEN.test(token)) invalid("token invalid");
  return token;
}

function tokenHash(value) {
  return createHash("sha256").update(ownerToken(value), "utf8").digest("hex");
}

function processId(value) {
  const pid = Number(value);
  if (!Number.isSafeInteger(pid) || pid < 1 || pid > 4_294_967_295) invalid("pid invalid");
  return pid;
}

function instant(value) {
  const text = String(value == null ? "" : value).trim();
  const milliseconds = Date.parse(text);
  if (!Number.isFinite(milliseconds) || !/[zZ]|[+-]\d\d:\d\d$/.test(text)) invalid("time invalid");
  return new Date(milliseconds).toISOString();
}

function staleMilliseconds(value) {
  const milliseconds = Number(value);
  if (!Number.isSafeInteger(milliseconds) || milliseconds < 1 || milliseconds > 86_400_000) {
    invalid("stale interval invalid");
  }
  return milliseconds;
}

function stageName(value) {
  const stage = String(value == null ? "" : value).trim();
  if (!STAGE.test(stage)) invalid("stage invalid");
  return stage;
}

function atomicJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  const temporary = path.join(path.dirname(file), `.${path.basename(file)}.${process.pid}.${randomUUID()}.tmp`);
  fs.writeFileSync(temporary, `${JSON.stringify(value)}\n`, { encoding: "utf8", mode: 0o600, flag: "wx" });
  fs.renameSync(temporary, file);
}

function parseOwner(file) {
  let value;
  try { value = JSON.parse(fs.readFileSync(file, "utf8")); } catch { return null; }
  if (
    !value || typeof value !== "object" || Array.isArray(value)
    || Object.keys(value).sort().join(",") !== "acquired_at,heartbeat_at,pid,token_sha256"
    || !/^[0-9a-f]{64}$/.test(String(value.token_sha256 || ""))
  ) return null;
  try {
    return Object.freeze({
      pid: processId(value.pid),
      acquired_at: instant(value.acquired_at),
      heartbeat_at: instant(value.heartbeat_at),
      token_sha256: String(value.token_sha256),
    });
  } catch {
    return null;
  }
}

function defaultProcessAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return !(error && error.code === "ESRCH");
  }
}

function isStale(owner, now, staleMs) {
  return Date.parse(now) - Date.parse(owner.heartbeat_at) >= staleMs;
}

function sameOwner(left, right) {
  return Boolean(
    left && right
    && left.pid === right.pid
    && left.acquired_at === right.acquired_at
    && left.heartbeat_at === right.heartbeat_at
    && left.token_sha256 === right.token_sha256,
  );
}

function reclaimStaleLock(paths, expectedOwner, now, staleMs, isProcessAlive) {
  try {
    fs.mkdirSync(paths.reclaimDir, { mode: 0o700 });
  } catch (error) {
    if (error && error.code === "EEXIST") return false;
    throw error;
  }

  try {
    const currentOwner = parseOwner(paths.ownerFile);
    if (
      !sameOwner(currentOwner, expectedOwner)
      || !isStale(currentOwner, now, staleMs)
      || isProcessAlive(currentOwner.pid)
    ) return false;
    fs.rmSync(paths.lockDir, { recursive: true, force: true });
    return true;
  } finally {
    fs.rmSync(paths.reclaimDir, { recursive: true, force: true });
  }
}

function acquireLock(input = {}) {
  const paths = lockPaths(input.stateDir);
  const token = ownerToken(input.token);
  const pid = processId(input.pid);
  const now = instant(input.now);
  const staleMs = staleMilliseconds(input.staleMs);
  const isProcessAlive = typeof input.isProcessAlive === "function"
    ? input.isProcessAlive
    : defaultProcessAlive;
  fs.mkdirSync(paths.root, { recursive: true, mode: 0o700 });

  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      fs.mkdirSync(paths.lockDir, { mode: 0o700 });
      try {
        atomicJson(paths.ownerFile, {
          pid,
          acquired_at: now,
          heartbeat_at: now,
          token_sha256: tokenHash(token),
        });
      } catch (error) {
        fs.rmSync(paths.lockDir, { recursive: true, force: true });
        throw error;
      }
      return Object.freeze({ status: "acquired" });
    } catch (error) {
      if (!error || error.code !== "EEXIST") throw error;
    }

    const owner = parseOwner(paths.ownerFile);
    if (!owner || !isStale(owner, now, staleMs) || isProcessAlive(owner.pid)) {
      return Object.freeze({ status: "busy" });
    }
    if (!reclaimStaleLock(paths, owner, now, staleMs, isProcessAlive)) {
      return Object.freeze({ status: "busy" });
    }
  }
  return Object.freeze({ status: "busy" });
}

function heartbeat(input = {}) {
  const paths = lockPaths(input.stateDir);
  const token = ownerToken(input.token);
  const now = instant(input.now);
  const stage = stageName(input.stage);
  const owner = parseOwner(paths.ownerFile);
  if (!owner || owner.token_sha256 !== tokenHash(token)) {
    return Object.freeze({ status: "not_owner" });
  }
  atomicJson(paths.ownerFile, {
    pid: owner.pid,
    acquired_at: owner.acquired_at,
    heartbeat_at: now,
    token_sha256: owner.token_sha256,
  });
  atomicJson(paths.heartbeatFile, { observed_at: now, stage });
  return Object.freeze({ status: "updated" });
}

function releaseLock(input = {}) {
  const paths = lockPaths(input.stateDir);
  const token = ownerToken(input.token);
  const owner = parseOwner(paths.ownerFile);
  if (!owner || owner.token_sha256 !== tokenHash(token)) {
    return Object.freeze({ status: "not_owner" });
  }
  fs.rmSync(paths.lockDir, { recursive: true, force: true });
  return Object.freeze({ status: "released" });
}

function parseHeartbeat(file) {
  let value;
  try { value = JSON.parse(fs.readFileSync(file, "utf8")); } catch { return null; }
  if (
    !value || typeof value !== "object" || Array.isArray(value)
    || Object.keys(value).sort().join(",") !== "observed_at,stage"
  ) return null;
  try {
    return Object.freeze({ observed_at: instant(value.observed_at), stage: stageName(value.stage) });
  } catch {
    return null;
  }
}

function readHealth(input = {}) {
  const paths = lockPaths(input.stateDir);
  const now = instant(input.now);
  const staleMs = staleMilliseconds(input.staleMs);
  const owner = parseOwner(paths.ownerFile);
  const heartbeatState = parseHeartbeat(paths.heartbeatFile);
  const heartbeat = heartbeatState && !isStale({ heartbeat_at: heartbeatState.observed_at }, now, staleMs)
    ? { status: "fresh", stage: heartbeatState.stage }
    : { status: heartbeatState ? "stale" : "missing" };
  return Object.freeze({
    heartbeat: Object.freeze(heartbeat),
    lock: Object.freeze({ status: owner ? "held" : "idle" }),
  });
}

function continuationReason(value) {
  const reason = String(value == null ? "" : value).trim();
  if (!/^[a-z][a-z0-9_]{0,79}$/.test(reason)) invalid("continuation reason invalid");
  return reason;
}

function recordContinuation(input = {}) {
  const paths = lockPaths(input.stateDir);
  atomicJson(path.join(paths.root, "continuation.json"), {
    reason: continuationReason(input.reason),
    status: "pending",
  });
  return Object.freeze({ status: "recorded" });
}

function cliNow() {
  return new Date().toISOString();
}

function runCli(argv = process.argv.slice(2)) {
  const [command, stateDir, token, third, fourth] = argv;
  let result;
  if (command === "acquire") {
    result = acquireLock({
      stateDir,
      token,
      pid: third,
      staleMs: fourth,
      now: cliNow(),
    });
  } else if (command === "heartbeat") {
    result = heartbeat({ stateDir, token, stage: third, now: cliNow() });
  } else if (command === "release") {
    result = releaseLock({ stateDir, token });
  } else if (command === "health") {
    result = readHealth({ stateDir, now: cliNow(), staleMs: token });
  } else {
    invalid("command invalid");
  }
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

if (require.main === module) {
  try {
    runCli();
  } catch {
    process.stderr.write("Connector native state unavailable\n");
    process.exitCode = 2;
  }
}

module.exports = {
  acquireLock,
  heartbeat,
  readHealth,
  recordContinuation,
  releaseLock,
};
