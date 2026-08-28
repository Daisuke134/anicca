"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { createSecretProvider } = require("./secret-provider.js");
const { enqueueHostedGoal } = require("./hosted-goal-ingress.js");

const NOW_MS = Date.parse("2026-08-28T13:40:00Z");

function goal(overrides = {}) {
  return {
    id: "hosted-goal-1",
    uid: "tenant-a",
    kind: "explicit_goal",
    statement: "Make money from one truthful paid opportunity",
    provenance: {
      source: "telegram_reply",
      evidence: "private-provider-message",
      observedAt: "2026-08-28T13:39:00Z",
    },
    confidenceTier: "explicit",
    confidence: 1,
    expiresAt: null,
    status: "active",
    supersedes: null,
    ...overrides,
  };
}

function fixture(overrides = {}) {
  const jobs = new Map();
  const calls = [];
  const vault = {
    async get() { throw new Error("ingress must not read secret values"); },
    async health() { return overrides.vaultHealth || { ok: true }; },
  };
  return {
    calls,
    jobs,
    deps: {
      async loadTenant(tenantId) {
        calls.push(["tenant", tenantId]);
        return overrides.tenant || {
          uid: "tenant-a",
          telegram_chat_id: "chat-a",
          phone: "+810000000000",
          paid: true,
        };
      },
      secretProvider: createSecretProvider({ mode: "cloud", vault }),
      async enqueueJob(input) {
        calls.push(["enqueue", input]);
        const key = `${input.tenantId}:${input.jobId}`;
        const created = !jobs.has(key);
        jobs.set(key, input);
        return { created };
      },
    },
  };
}

test("paid authenticated tenant enqueues one reference-only goal and replay is zero", async () => {
  const f = fixture();
  const input = {
    scope: { authenticated: true, tenantId: "tenant-a", chatId: "chat-a" },
    goal: goal(),
    nowMs: NOW_MS,
  };

  const first = await enqueueHostedGoal(input, f.deps);
  const replay = await enqueueHostedGoal(input, f.deps);

  assert.deepEqual(first, {
    created: true,
    tenant_id: "tenant-a",
    job_id: "goal:hosted-goal-1",
    job_ref: "runtime-job://tenant-a/goal%3Ahosted-goal-1",
    vault_provider: "vault",
  });
  assert.deepEqual(replay, { ...first, created: false });
  assert.equal(f.jobs.size, 1);
  const queued = [...f.jobs.values()][0];
  assert.deepEqual(queued, {
    jobId: "goal:hosted-goal-1",
    tenantId: "tenant-a",
    loopId: "life-manager.manager",
    capability: "general-agent.work",
    effectClass: "none",
    effectKey: null,
    inputRefs: { goal_ref: "intent-entry://tenant-a/hosted-goal-1" },
    maxAttempts: 1,
  });
  assert.doesNotMatch(JSON.stringify([first, replay, queued]), /Make money|private-provider|chat-a|\+8100|secret/i);
});

test("unauthenticated unpaid cross-tenant and unhealthy-vault requests enqueue zero", async () => {
  const cases = [
    { input: { scope: { authenticated: false, tenantId: "tenant-a", chatId: "chat-a" }, goal: goal(), nowMs: NOW_MS } },
    { input: { scope: { authenticated: true, tenantId: "tenant-a", chatId: "chat-a" }, goal: goal(), nowMs: NOW_MS }, tenant: { uid: "tenant-a", telegram_chat_id: "chat-a", paid: false } },
    { input: { scope: { authenticated: true, tenantId: "tenant-a", chatId: "chat-b" }, goal: goal(), nowMs: NOW_MS } },
    { input: { scope: { authenticated: true, tenantId: "tenant-a", chatId: "chat-a" }, goal: goal({ uid: "tenant-b" }), nowMs: NOW_MS } },
    { input: { scope: { authenticated: true, tenantId: "tenant-a", chatId: "chat-a" }, goal: goal(), nowMs: NOW_MS }, vaultHealth: { ok: false } },
  ];

  for (const item of cases) {
    const f = fixture(item);
    await assert.rejects(enqueueHostedGoal(item.input, f.deps), /authenticated|scope|entitlement|vault/i);
    assert.equal(f.calls.filter(([kind]) => kind === "enqueue").length, 0);
    assert.equal(f.jobs.size, 0);
  }
});
