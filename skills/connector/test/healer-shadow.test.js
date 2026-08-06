"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { runHealerShadow } = require("../lib/healer-shadow.js");

const REPO_ROOT = path.resolve(__dirname, "../../..");

test("Healer converts one privacy-safe incident into one isolated Terra Superpowers revision without external-effect credentials", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "connector-healer-shadow-"));
  const stateDir = path.join(root, "state");
  const worktreeRoot = path.join(root, "worktrees");
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, "observer-incidents.jsonl"), `${JSON.stringify({
    schema_version: 1,
    wake_id: "wake:fixture",
    run_id: "run:fixture",
    stage: "native_pass",
    safe_action: "runtime_execute",
    expected_effect: "applied_bundle",
    observed_effect: "tool_failure",
    incident_class: "tool_failure",
    owner_generation: 1,
    code_commit: "52dfb3f2e",
    cursor: "connpass:2026-08-07:0:2",
    observed_at: "2026-08-06T16:00:00.000Z",
    fingerprint: `sha256:${"a".repeat(64)}`,
  })}\n`, { mode: 0o600 });
  const calls = [];
  try {
    const result = await runHealerShadow({
      repoRoot: REPO_ROOT,
      stateDir,
      worktreeRoot,
      now: () => new Date("2026-08-06T16:05:00.000Z"),
      env: {
        PATH: process.env.PATH,
        HOME: root,
        LM_CONNECTOR_TELEGRAM_TARGET: "must-not-leak",
        GOG_KEYRING_PASSWORD: "must-not-leak",
        GOOGLE_API_KEY_DIRECTIONS: "must-not-leak",
      },
      execute: async (command, args, options) => {
        calls.push({ command, args, options });
        if (command === "git" && args.includes("rev-parse")) return { status: 0, stdout: `${"b".repeat(40)}\n` };
        if (command === "git" && args.includes("ls-remote")) {
          return { status: 0, stdout: `${"b".repeat(40)}\trefs/heads/healer/connector-aaaaaaaaaaaa-r1\n` };
        }
        return { status: 0, stdout: command === "codex" ? '{"type":"thread.started","thread_id":"thread-1"}\n' : "" };
      },
    });

    assert.equal(result.status, "revision_created");
    assert.equal(calls.filter((call) => call.command === "codex").length, 1);
    const codex = calls.find((call) => call.command === "codex");
    assert.deepEqual(codex.args.slice(0, 8), [
      "exec", "--json", "--model", "gpt-5.6-terra",
      "--sandbox", "workspace-write", "-C", result.worktree,
    ]);
    assert.equal(codex.options.input.includes("systematic-debugging"), true);
    assert.equal(codex.options.input.includes("test-driven-development"), true);
    assert.equal(codex.options.input.includes("external event submit is forbidden"), true);
    assert.equal("LM_CONNECTOR_TELEGRAM_TARGET" in codex.options.env, false);
    assert.equal("GOG_KEYRING_PASSWORD" in codex.options.env, false);
    assert.equal("GOOGLE_API_KEY_DIRECTIONS" in codex.options.env, false);
    assert.equal(calls.some((call) => call.command === "git" && call.args.includes("status")), true);
    assert.equal(calls.some((call) => call.command === "git" && call.args.includes("ls-remote")), true);
    const revisions = fs.readFileSync(path.join(stateDir, "healer-revisions.jsonl"), "utf8")
      .trim().split("\n").map(JSON.parse);
    assert.equal(revisions.length, 1);
    assert.equal(revisions[0].fingerprint, `sha256:${"a".repeat(64)}`);
    assert.equal(revisions[0].status, "revision_created");

    const duplicate = await runHealerShadow({
      repoRoot: REPO_ROOT, stateDir, worktreeRoot,
      now: () => new Date("2026-08-06T16:06:00.000Z"), env: { PATH: process.env.PATH, HOME: root },
      execute: async () => { throw new Error("duplicate must execute nothing"); },
    });
    assert.equal(duplicate.status, "duplicate");
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("Healer records a failed Codex revision and stops at three revisions per 24 hours", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "connector-healer-cap-"));
  const stateDir = path.join(root, "state");
  const worktreeRoot = path.join(root, "worktrees");
  fs.mkdirSync(stateDir, { recursive: true });
  const incidents = ["a", "b", "c", "d"].map((suffix, index) => ({
    schema_version: 1,
    wake_id: `wake:cap-${index}`,
    run_id: `run:cap-${index}`,
    stage: "native_pass",
    safe_action: "runtime_execute",
    expected_effect: "applied_bundle",
    observed_effect: "tool_failure",
    incident_class: "tool_failure",
    owner_generation: 1,
    code_commit: "52dfb3f2e",
    cursor: `connpass:2026-08-07:${index}:2`,
    observed_at: "2026-08-06T16:00:00.000Z",
    fingerprint: `sha256:${suffix.repeat(64)}`,
  }));
  fs.writeFileSync(
    path.join(stateDir, "observer-incidents.jsonl"),
    `${incidents.map(JSON.stringify).join("\n")}\n`,
    { mode: 0o600 },
  );
  let codexCalls = 0;
  const options = {
    repoRoot: REPO_ROOT, stateDir, worktreeRoot,
    now: () => new Date("2026-08-06T16:05:00.000Z"),
    env: { PATH: process.env.PATH, HOME: root },
    execute: async (command) => {
      if (command === "codex") {
        codexCalls += 1;
        return { status: 1, stdout: '{"type":"error","message":"bounded failure"}\n' };
      }
      return { status: 0, stdout: "" };
    },
  };
  try {
    for (let index = 0; index < 3; index += 1) {
      const result = await runHealerShadow(options);
      assert.equal(result.status, "revision_failed");
    }
    const capped = await runHealerShadow(options);
    assert.equal(capped.status, "revision_cap");
    assert.equal(codexCalls, 3);
    const revisions = fs.readFileSync(path.join(stateDir, "healer-revisions.jsonl"), "utf8")
      .trim().split("\n").map(JSON.parse);
    assert.deepEqual(revisions.map((row) => row.status), [
      "revision_failed", "revision_failed", "revision_failed",
    ]);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("Healer records a bounded Codex timeout instead of losing the revision", async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "connector-healer-timeout-"));
  const stateDir = path.join(root, "state");
  fs.mkdirSync(stateDir, { recursive: true });
  fs.writeFileSync(path.join(stateDir, "observer-incidents.jsonl"), `${JSON.stringify({
    schema_version: 1, wake_id: "wake:timeout", run_id: "run:timeout",
    stage: "native_pass", safe_action: "runtime_execute", expected_effect: "applied_bundle",
    observed_effect: "timeout", incident_class: "timeout", owner_generation: 1,
    code_commit: "3618c3b6a", cursor: "connpass:2026-08-07:0:2",
    observed_at: "2026-08-07T01:00:00.000Z", fingerprint: `sha256:${"e".repeat(64)}`,
  })}\n`, { mode: 0o600 });
  try {
    const result = await runHealerShadow({
      repoRoot: REPO_ROOT, stateDir, worktreeRoot: path.join(root, "worktrees"),
      now: () => new Date("2026-08-07T01:05:00.000Z"),
      env: { PATH: process.env.PATH, HOME: root }, codexTimeoutMs: 1234,
      execute: async (command, _args, options) => {
        if (command === "codex") {
          assert.equal(options.timeoutMs, 1234);
          return { status: null, signal: "SIGTERM", errorCode: "ETIMEDOUT", stdout: "" };
        }
        return { status: 0, stdout: "" };
      },
    });
    assert.equal(result.status, "revision_timeout");
    const row = JSON.parse(fs.readFileSync(path.join(stateDir, "healer-revisions.jsonl"), "utf8").trim());
    assert.equal(row.status, "revision_timeout");
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});
