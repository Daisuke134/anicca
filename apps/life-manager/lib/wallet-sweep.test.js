"use strict";
// AE-ZERO-START-1 §4.4 — the self-heal sweep that is the ONLY enqueue point for zero-start.
//
// `lm-onboard.js` cannot enqueue: the runtime queue lives in the local Postgres
// (`LM_RUNTIME_DATABASE_URL`), which a Netlify function has no path to. So a tenant is provisioned
// because this sweep noticed its `lm_users` row had no wallet columns. That makes three properties
// load-bearing.
//
//  - Idempotent. `job_id` and `effect_key` are both `zero-start:<uid>`, so sweeping every five minutes
//    can never produce a second zero-start message for a tenant.
//  - Bound to the adapter. The job this sweep enqueues must be exactly what buildZeroStartJob produces,
//    or the worker would claim a job whose contract check fails.
//  - Per-tenant isolated. One tenant's enqueue blowing up must not stop the rest of the sweep.

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  MAX_TENANTS_PER_SWEEP,
  listWalletSweepTenants,
  needsZeroStart,
  planWalletSweep,
  sweepWalletJobs,
} = require("./wallet-sweep.js");
const { buildZeroStartJob } = require("./zero-start-job-adapter.js");
const { buildWalletInflowJob } = require("./wallet-inflow-job-adapter.js");

const TOKEN_REF = "secret://telegram/bot-token";
const BASE_ADDRESS = "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF";
const SOLANA_ADDRESS = "FVen3X669xLzsi6N2V91DoiyzHzg1uAgqiT8jZ9nS96Z";
const NOW_MS = Date.parse("2026-07-30T10:00:00.000Z");

function provisioned(uid) {
  return {
    uid,
    agent_wallet_address: BASE_ADDRESS,
    agent_wallet_solana_address: SOLANA_ADDRESS,
    agent_wallet_key_ref: `secret://lm-agent-wallet/${uid}/base`,
    agent_wallet_solana_key_ref: `secret://lm-agent-wallet/${uid}/solana`,
    agent_wallet_created_at: "2026-07-30T09:00:00.000Z",
  };
}

function bare(uid) {
  return {
    uid,
    agent_wallet_address: null,
    agent_wallet_solana_address: null,
    agent_wallet_key_ref: null,
    agent_wallet_solana_key_ref: null,
    agent_wallet_created_at: null,
  };
}

function harness(rows, overrides = {}) {
  const enqueued = [];
  const deps = {
    nowMs: NOW_MS,
    telegramTokenRef: TOKEN_REF,
    async listTenants() {
      return rows;
    },
    async enqueueJob(input) {
      enqueued.push(input);
      if (typeof overrides.onEnqueue === "function") return overrides.onEnqueue(input);
      return { created: true, job: { ...input } };
    },
    ...overrides.deps,
  };
  return { deps, enqueued };
}

test("§11.5: needing a zero-start means no ANNOUNCEMENT, not missing wallet columns", () => {
  // The measured §9.2 defect: wallets are published BEFORE the chat check, so a failure after provisioning
  // left a real funded-capable address with the tenant never told — and `needsZeroStart` said false because
  // the columns were full. Announcement, not provisioning, is the thing that has to be true.
  const announced = new Set(["told"]);
  assert.equal(needsZeroStart(bare("tenant-a"), { announced }), true);
  assert.equal(needsZeroStart(provisioned("tenant-a"), { announced }), true, "provisioned but never told");
  assert.equal(needsZeroStart(provisioned("told"), { announced }), false);
  assert.equal(needsZeroStart(bare("told"), { announced }), false, "already told, nothing more to announce");
  // With no announcement record at all, every tenant needs one.
  assert.equal(needsZeroStart(provisioned("tenant-a")), true);
  assert.equal(needsZeroStart(null, { announced }), false);
});

test("a brand new tenant is swept into exactly the job the adapter defines", async () => {
  const h = harness([bare("tenant-a")]);
  const result = await sweepWalletJobs(h.deps);

  assert.equal(result.zero_start.length, 1);
  assert.deepEqual(result.zero_start[0], { uid: "tenant-a", job_id: "zero-start:tenant-a", created: true });
  // Nothing to watch yet: the addresses do not exist until the zero-start job runs.
  assert.equal(result.inflow.length, 0);

  // Bound to the adapter, field for field. A drift here would make the worker refuse the job.
  const expected = buildZeroStartJob({ tenantId: "tenant-a", telegramTokenRef: TOKEN_REF });
  assert.deepEqual(h.enqueued[0], {
    jobId: expected.job_id,
    tenantId: expected.tenant_id,
    loopId: expected.loop_id,
    capability: expected.capability,
    effectClass: expected.effect_class,
    effectKey: expected.effect_key,
    inputRefs: expected.input_refs,
    maxAttempts: expected.max_attempts,
  });
});

test("an already ANNOUNCED tenant is watched, not re-provisioned", async () => {
  // §11.5: full wallet columns are no longer the signal — a completed `started` receipt is.
  const h = harness([provisioned("tenant-a")], {
    deps: { readAnnouncedTenants: async () => new Set(["tenant-a"]) },
  });
  const result = await sweepWalletJobs(h.deps);

  assert.equal(result.zero_start.length, 0);
  assert.equal(result.inflow.length, 1);
  assert.equal(result.inflow[0].uid, "tenant-a");

  const expected = buildWalletInflowJob({ tenantId: "tenant-a", nowMs: NOW_MS });
  assert.equal(h.enqueued[0].capability, expected.capability);
  assert.equal(h.enqueued[0].jobId, expected.job_id);
  assert.equal(h.enqueued[0].effectClass, "none");
  assert.equal(h.enqueued[0].effectKey, null);
});

test("a half-provisioned tenant is both finished and watched", async () => {
  // The Base wallet exists and can already receive money, so it must be watched even while the Solana
  // rail is still missing — otherwise a real inflow would go unrecorded until provisioning completes.
  const half = { ...provisioned("tenant-a"), agent_wallet_solana_address: null, agent_wallet_solana_key_ref: null };
  const h = harness([half]);
  const result = await sweepWalletJobs(h.deps);

  assert.equal(result.zero_start.length, 1);
  assert.equal(result.inflow.length, 1);
});

test("the same sweep run twice creates nothing new", async () => {
  const seen = new Set();
  const h = harness([bare("tenant-a"), provisioned("tenant-b")], {
    onEnqueue(input) {
      const created = !seen.has(input.jobId);
      seen.add(input.jobId);
      return { created, job: { ...input } };
    },
  });
  const first = await sweepWalletJobs(h.deps);
  assert.equal(first.zero_start[0].created, true);

  const second = await sweepWalletJobs(h.deps);
  assert.equal(second.zero_start[0].created, false, "the stable job id must dedupe the second sweep");
  assert.equal(second.zero_start[0].uid, "tenant-a");
  // The inflow job is per-wake by design, so a later wake is a new job — but not for the same instant.
  assert.equal(second.inflow[0].created, false);
});

test("a sweep is bounded, so a large tenant table cannot become one enormous burst", async () => {
  const rows = Array.from({ length: MAX_TENANTS_PER_SWEEP + 40 }, (_, index) => bare(`tenant-${index}`));
  const h = harness(rows);
  const result = await sweepWalletJobs(h.deps);
  assert.equal(result.zero_start.length, MAX_TENANTS_PER_SWEEP);
  assert.equal(result.truncated, true);
  assert.equal(h.enqueued.length, MAX_TENANTS_PER_SWEEP);

  const small = harness(rows.slice(0, 3));
  assert.equal((await sweepWalletJobs(small.deps)).truncated, false);
});

test("one tenant's failure does not stop the sweep, and is reported rather than swallowed", async () => {
  const h = harness([bare("tenant-a"), bare("tenant-b"), bare("tenant-c")], {
    onEnqueue(input) {
      if (input.tenantId === "tenant-b") throw new Error("queue write refused");
      return { created: true, job: { ...input } };
    },
  });
  const result = await sweepWalletJobs(h.deps);

  assert.deepEqual(result.zero_start.map((entry) => entry.uid), ["tenant-a", "tenant-c"]);
  assert.equal(result.failed.length, 1);
  assert.equal(result.failed[0].uid, "tenant-b");
  assert.equal(result.failed[0].capability, "wallet.zero-start");
  assert.match(result.failed[0].error, /refused/);
});

test("a malformed tenant row is skipped, not turned into a malformed job", async () => {
  const h = harness([null, { uid: "" }, { uid: "../escape" }, bare("tenant-ok")]);
  const result = await sweepWalletJobs(h.deps);
  assert.deepEqual(result.zero_start.map((entry) => entry.uid), ["tenant-ok"]);
  assert.equal(result.skipped, 3);
});

test("the plan is a pure function of the rows, so it can be reasoned about without a queue", () => {
  const plan = planWalletSweep([bare("tenant-a"), provisioned("tenant-b")], {
    nowMs: NOW_MS,
    telegramTokenRef: TOKEN_REF,
    announced: new Set(["tenant-b"]),
  });
  assert.deepEqual(plan.zeroStart.map((job) => job.tenant_id), ["tenant-a"]);
  assert.deepEqual(plan.inflow.map((job) => job.tenant_id), ["tenant-b"]);
  assert.equal(plan.skipped, 0);
  assert.equal(plan.truncated, false);
});

test("the tenant read is bounded and asks for exactly the wallet columns", async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, status: 200, json: async () => [provisioned("tenant-a")] };
  };
  const rows = await listWalletSweepTenants({
    supaUrl: "https://db.example",
    supaKey: "service-role-test-only",
    fetchImpl,
  });
  assert.equal(rows.length, 1);
  assert.match(calls[0].url, /lm_users\?/);
  for (const column of [
    "uid",
    "agent_wallet_address",
    "agent_wallet_solana_address",
    "agent_wallet_key_ref",
    "agent_wallet_solana_key_ref",
    "agent_wallet_created_at",
  ]) {
    assert.ok(calls[0].url.includes(column), `${column} must be selected`);
  }
  // §9.3: bounding moved from a `limit=` clause to a paged Range header, so the read reaches tenant 501+.
  assert.equal(calls[0].options.headers.Range, "0-499");
  assert.equal(calls[0].options.headers["Range-Unit"], "items");
  assert.doesNotMatch(calls[0].url, /limit=/, "a limit clause would cap the read below the tenant count");
  assert.equal(calls.length, 1, "a short page ends the paging");
  // The sweep has no business reading anything else about a tenant.
  assert.ok(!calls[0].url.includes("phone"));
  assert.ok(!calls[0].url.includes("name"));

  await assert.rejects(
    () => listWalletSweepTenants({
      supaUrl: "https://db.example",
      supaKey: "k",
      fetchImpl: async () => ({ ok: false, status: 500, json: async () => ({}) }),
    }),
    /read failed/i,
  );
});

test("the sweep result carries nothing secret", async () => {
  const h = harness([bare("tenant-a"), provisioned("tenant-b")]);
  const result = await sweepWalletJobs(h.deps);
  const { assertNoSecret } = require("./earnings-ledger.js");
  assertNoSecret(result);
  const serialised = JSON.stringify(result);
  // The same anti-key shapes the migration's CHECK enforces (an 0x private key, a base58 secret key).
  // A bare 64-hex run is NOT one of them here: the inflow job id is a sha256 digest of tenant+instant.
  assert.doesNotMatch(serialised, /0[xX][0-9a-fA-F]{64}/);
  assert.doesNotMatch(serialised, /[1-9A-HJ-NP-Za-km-z]{80,}/);
  // And the sweep reports identity only — it never carries a key reference, let alone a key.
  assert.deepEqual(
    [...new Set(result.zero_start.concat(result.inflow).flatMap((entry) => Object.keys(entry)))].sort(),
    ["created", "job_id", "uid"],
  );
});

// §9.3 MAJOR-3 — hostile scale. The measured defect: 60 watchable tenants, and passes 1 and 2 planned the
// identical t001..t050 because the order was `uid.asc` with no cursor and `isWatchable` never goes false.
// Ten tenants were NEVER planned, so their inflows were never recorded — real money silently unbooked.

function watchableTenants(count) {
  return Array.from({ length: count }, (_, index) => provisioned(`t${String(index + 1).padStart(3, "0")}`));
}

test("§9.3: 60 tenants are ALL planned within two passes, none starved", async () => {
  const rows = watchableTenants(60);
  const watchedAt = new Map();
  const planned = [[], []];

  for (const pass of [0, 1]) {
    const h = harness(rows, {
      deps: {
        // Least-recently-watched, derived from completed watch receipts.
        async readInflowWatchedAt() {
          return new Map(watchedAt);
        },
      },
    });
    const result = await sweepWalletJobs({ ...h.deps, nowMs: NOW_MS + pass * 300_000 });
    for (const entry of result.inflow) {
      planned[pass].push(entry.uid);
      // Each planned tenant is now more recently watched than the ones that were not.
      watchedAt.set(entry.uid, new Date(NOW_MS + pass * 300_000).toISOString());
    }
  }

  assert.equal(planned[0].length, MAX_TENANTS_PER_SWEEP);
  assert.equal(planned[1].length, MAX_TENANTS_PER_SWEEP);
  const served = new Set([...planned[0], ...planned[1]]);
  assert.equal(served.size, 60, "every tenant must have been planned at least once across two passes");
  // The exact starvation the adversary measured: pass 2 must NOT be a repeat of pass 1.
  assert.notDeepEqual(planned[1], planned[0]);
  // And the ten that pass 1 could not reach must be first in line, not last.
  for (const uid of ["t051", "t052", "t060"]) {
    assert.ok(planned[1].includes(uid), `${uid} must be served on the very next pass`);
  }
});

test("§9.3: a never-watched tenant outranks one watched long ago", async () => {
  const rows = [provisioned("old"), provisioned("fresh"), provisioned("never")];
  const h = harness(rows, {
    deps: {
      async readInflowWatchedAt() {
        return new Map([
          ["old", "2026-07-01T00:00:00.000Z"],
          ["fresh", "2026-07-30T09:59:00.000Z"],
        ]);
      },
    },
  });
  const result = await sweepWalletJobs({ ...h.deps, limit: 2 });
  assert.deepEqual(result.inflow.map((entry) => entry.uid), ["never", "old"]);
});

test("§9.3: no tenant is served twice while another is still waiting", async () => {
  // Fairness across many passes, which is what "eventually served" has to mean in practice.
  const rows = watchableTenants(120);
  const watchedAt = new Map();
  const counts = new Map();
  for (let pass = 0; pass < 4; pass++) {
    const h = harness(rows, {
      deps: { async readInflowWatchedAt() { return new Map(watchedAt); } },
    });
    const result = await sweepWalletJobs({ ...h.deps, nowMs: NOW_MS + pass * 300_000 });
    for (const entry of result.inflow) {
      watchedAt.set(entry.uid, new Date(NOW_MS + pass * 300_000).toISOString());
      counts.set(entry.uid, (counts.get(entry.uid) || 0) + 1);
    }
  }
  assert.equal(counts.size, 120, "all 120 tenants served within four passes at 50 per pass");
  const spread = Math.max(...counts.values()) - Math.min(...counts.values());
  assert.ok(spread <= 1, `service counts must stay within one of each other, saw a spread of ${spread}`);
});

test("§9.3: the tenant read pages past the first 500 rows", async () => {
  // `limit=500` meant tenant 501 onward was never even READ, let alone planned.
  const total = 1100;
  const all = Array.from({ length: total }, (_, index) => provisioned(`p${String(index).padStart(5, "0")}`));
  const ranges = [];
  const fetchImpl = async (url, options) => {
    const range = String((options.headers || {}).Range || "");
    ranges.push(range);
    const [start, end] = range.split("-").map(Number);
    return { ok: true, status: 200, json: async () => all.slice(start, end + 1) };
  };
  const rows = await listWalletSweepTenants({
    supaUrl: "https://db.example",
    supaKey: "service-role-test-only",
    fetchImpl,
  });
  assert.equal(rows.length, total, "every tenant row must be read");
  assert.ok(ranges.length >= 3, `paging must actually page, saw ${ranges.length} request(s)`);
  assert.equal(ranges[0], "0-499");

  // Still bounded: a runaway table cannot be read without limit.
  const huge = Array.from({ length: 20_000 }, (_, index) => provisioned(`h${index}`));
  const bounded = await listWalletSweepTenants({
    supaUrl: "https://db.example",
    supaKey: "k",
    fetchImpl: async (url, options) => {
      const [start, end] = String((options.headers || {}).Range || "").split("-").map(Number);
      return { ok: true, status: 200, json: async () => huge.slice(start, end + 1) };
    },
  });
  assert.ok(bounded.length < huge.length, "the read must stay bounded");
  assert.equal(bounded.length % 500, 0);
});

// §11 — provisioning is unconditional, announcing is conditional, waiting is free.
//
// The schema forces this shape: probe-4 status re-activation preserving `attempt` is the ONLY reap
// PostgreSQL permits, and `max_attempts` is CHECK-capped at 20, so a job row has a lifetime budget of 20
// runs and can never be replaced. If waiting for a Telegram link burned that budget, a tenant who links on
// day 30 could never be told. So the gate is on RE-ACTIVATION, not on the enqueue.

function chatless(uid) {
  return { ...bare(uid), telegram_chat_id: null };
}

function withChat(uid, row) {
  return { ...(row || bare(uid)), telegram_chat_id: "555000111" };
}

// A stand-in for the runtime queue that enforces exactly the constraints the real schema does.
function queue() {
  const jobs = new Map();
  const announced = new Set();
  return {
    jobs,
    announced,
    async enqueueJob(input) {
      const existing = jobs.get(input.jobId);
      if (existing) return { created: false, job: { ...existing } };
      // A fresh row starts queued with a budget, exactly like lm_runtime_jobs defaults.
      jobs.set(input.jobId, { ...input, status: "queued", attempt: 0 });
      return { created: true, job: { ...jobs.get(input.jobId) } };
    },
    async reapZeroStartJob({ tenantId }) {
      const jobId = `zero-start:${tenantId}`;
      const row = jobs.get(jobId);
      if (!row) return { reaped: false, reason: "absent" };
      if (!["completed", "dead_letter"].includes(row.status)) return { reaped: false, reason: "active" };
      if (row.attempt >= row.maxAttempts) return { reaped: false, reason: "exhausted" };
      // probe-4: status back to queued, attempt UNTOUCHED (a reset collides with the receipt PK).
      row.status = "queued";
      return { reaped: true, reason: "reactivated" };
    },
    async readAnnouncedTenants() {
      return new Set(announced);
    },
    // Simulates a worker claiming and running the job.
    run(tenantId, outcome) {
      const row = jobs.get(`zero-start:${tenantId}`);
      if (!row || row.status !== "queued") return null;
      row.attempt += 1;
      row.status = "completed";
      if (outcome === "started") announced.add(tenantId);
      return row.attempt;
    },
  };
}

async function sweepWith(q, rows, extra = {}) {
  return sweepWalletJobs({
    nowMs: NOW_MS,
    telegramTokenRef: TOKEN_REF,
    listTenants: async () => rows,
    enqueueJob: q.enqueueJob,
    reapZeroStartJob: q.reapZeroStartJob,
    readAnnouncedTenants: q.readAnnouncedTenants,
    ...extra,
  });
}

test("§11.1: a chatless tenant IS still provisioned — AC5 does not depend on Telegram", async () => {
  const q = queue();
  const result = await sweepWith(q, [chatless("tenant-a")]);
  assert.equal(result.zero_start.length, 1, "wallet generation must not wait on a messaging channel");
  assert.equal(result.zero_start[0].created, true);
});

test("§11.3: a chatless tenant consumes exactly ONE attempt across many sweeps", async () => {
  // The whole point. If waiting burned attempts, 20 sweeps (100 minutes) would exhaust the row forever.
  const q = queue();
  const rows = [chatless("tenant-a")];
  await sweepWith(q, rows);
  assert.equal(q.run("tenant-a", "blocked_no_chat"), 1);

  const awaiting = [];
  for (let pass = 0; pass < 40; pass++) {
    const result = await sweepWith(q, rows);
    awaiting.push(...result.awaiting_chat);
  }
  const row = q.jobs.get("zero-start:tenant-a");
  assert.equal(row.attempt, 1, "40 further sweeps must not have spent a single extra attempt");
  assert.equal(row.status, "completed", "a tenant with no chat is left terminal, not requeued");
  // §11.6: reported as awaiting, which is NOT the same as failed.
  assert.equal(awaiting.length, 40);
  assert.equal(awaiting[0].uid, "tenant-a");
  assert.equal(awaiting[0].reason, "awaiting_chat_link");
});

test("§11.3: the same tenant IS announced once a chat is linked much later", async () => {
  const q = queue();
  await sweepWith(q, [chatless("tenant-a")]);
  q.run("tenant-a", "blocked_no_chat");
  for (let pass = 0; pass < 30; pass++) await sweepWith(q, [chatless("tenant-a")]);

  // Day 30: the tenant finally links Telegram.
  const linked = [withChat("tenant-a", provisioned("tenant-a"))];
  const result = await sweepWith(q, linked);
  assert.equal(result.reactivated.length, 1, "the blocking condition cleared, so the row is re-activated");
  assert.equal(result.reactivated[0].uid, "tenant-a");
  assert.equal(q.jobs.get("zero-start:tenant-a").status, "queued");

  assert.equal(q.run("tenant-a", "started"), 2, "announcing costs the second attempt, not the twenty-first");
  assert.equal(q.announced.has("tenant-a"), true);

  // And once announced, the tenant is never re-activated again.
  const after = await sweepWith(q, linked);
  assert.deepEqual(after.zero_start, []);
  assert.deepEqual(after.reactivated, []);
  assert.deepEqual(after.awaiting_chat, []);
});

test("§11.4: the MAJOR-5 race — a chat unlinked between the read and the run — heals", async () => {
  // The sweep saw a chat, so it enqueued; by the time the worker ran, the chat was gone and the job
  // completed blocked. Nothing may be stuck: the next sweep that sees a chat must re-activate it.
  const q = queue();
  await sweepWith(q, [withChat("tenant-a")]);
  q.run("tenant-a", "blocked_no_chat");
  assert.equal(q.jobs.get("zero-start:tenant-a").attempt, 1);

  const result = await sweepWith(q, [withChat("tenant-a", provisioned("tenant-a"))]);
  assert.equal(result.reactivated.length, 1);
  assert.equal(q.run("tenant-a", "started"), 2);
  assert.equal(q.announced.has("tenant-a"), true);
});

test("§11.4: a transient failure with a chat present heals on the next sweep", async () => {
  const q = queue();
  await sweepWith(q, [withChat("tenant-a")]);
  // RPC down / Telegram 5xx: the worker exhausts its retries and the row dead-letters.
  const row = q.jobs.get("zero-start:tenant-a");
  row.attempt = 3;
  row.status = "dead_letter";

  const result = await sweepWith(q, [withChat("tenant-a", provisioned("tenant-a"))]);
  assert.equal(result.reactivated.length, 1);
  assert.equal(q.jobs.get("zero-start:tenant-a").status, "queued");
  assert.equal(q.jobs.get("zero-start:tenant-a").attempt, 3, "attempt is preserved — a reset breaks the receipt PK");
});

test("§11.6: an exhausted row is REPORTED for operator attention, never silently dropped", async () => {
  const q = queue();
  await sweepWith(q, [withChat("tenant-a")]);
  const row = q.jobs.get("zero-start:tenant-a");
  row.attempt = 20;
  row.maxAttempts = 20;
  row.status = "dead_letter";

  const result = await sweepWith(q, [withChat("tenant-a", provisioned("tenant-a"))]);
  assert.deepEqual(result.reactivated, []);
  assert.equal(result.exhausted.length, 1);
  assert.equal(result.exhausted[0].uid, "tenant-a");
  assert.equal(result.exhausted[0].reason, "attempts_exhausted");
  // §11.6: awaiting-a-chat and out-of-budget must be distinguishable in the output. They are separate
  // buckets with separate reasons, so an operator can act on the second without wading through the first.
  assert.deepEqual(result.awaiting_chat, [], "this tenant HAS a chat — it is out of budget, not waiting");
  assert.notEqual(result.exhausted[0].reason, "awaiting_chat_link");
  assert.ok(Array.isArray(result.awaiting_chat) && Array.isArray(result.exhausted));
});

test("§11.3: a row still running or queued is never re-activated underneath the worker", async () => {
  const q = queue();
  await sweepWith(q, [withChat("tenant-a")]);
  assert.equal(q.jobs.get("zero-start:tenant-a").status, "queued");
  const result = await sweepWith(q, [withChat("tenant-a", provisioned("tenant-a"))]);
  assert.deepEqual(result.reactivated, [], "an active row must be left alone");
  assert.deepEqual(result.exhausted, []);

  q.jobs.get("zero-start:tenant-a").status = "running";
  const during = await sweepWith(q, [withChat("tenant-a", provisioned("tenant-a"))]);
  assert.deepEqual(during.reactivated, []);
});

test("§11: an announced tenant is never enqueued, re-activated, or reported again", async () => {
  const q = queue();
  q.announced.add("tenant-a");
  const result = await sweepWith(q, [withChat("tenant-a", provisioned("tenant-a"))]);
  assert.deepEqual(result.zero_start, []);
  assert.deepEqual(result.reactivated, []);
  assert.deepEqual(result.awaiting_chat, []);
  assert.deepEqual(result.exhausted, []);
  // The inflow watch keeps running for it, though — that is what it was provisioned for.
  assert.equal(result.inflow.length, 1);
});
