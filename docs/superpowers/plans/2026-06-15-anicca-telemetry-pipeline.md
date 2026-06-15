# Anicca Telemetry Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each Anicca instance POSTs its own signed state (net worth, revenue, runway, model, host) every wake to a telemetry endpoint; the public /dashboard renders all instances in realtime — Aniccas never write the website.

**Architecture (CORRECTED — round-4, verified against the live repo):** `apps/landing` is a **static Next.js export** (`next.config.mjs` → `output: 'export'`). App Router route handlers (`app/api/*/route.ts`) **do NOT run** on aniccaai.com — the real server-side runtime is **Netlify Functions** (`apps/landing/netlify/functions/*.js`, CommonJS `exports.handler`, invoked at `/.netlify/functions/<name>`). Supabase is reached via its **REST API** (`fetch(${SUPABASE_URL}/rest/v1/<table>)` with `apikey` + `Bearer SERVICE_ROLE_KEY`) — `@supabase/supabase-js` is not a dependency. A Supabase project **already exists** (`https://cycgdwndgfgdbnndithc.supabase.co`, `SUPABASE_SERVICE_ROLE_KEY` already in Netlify env, used by `fashion_orders`); we add one `instances` table to it. EIP-191 signature recovery uses **`ethers` v6** (`verifyMessage`) — dual CJS/ESM so a CommonJS function can `require('ethers')` (viem is ESM-only and is not installed). Tests use **`node:test`** (Node 20 built-in, zero new test-runner dependency). The automaton's existing per-wake report hook is extended to POST the same data it already computes.

**Why the rewrite:** rounds 1–3 reviewed the plan in the abstract and verified the EIP-191 crypto end-to-end, but assumed an App-Router/viem/zod/supabase-js/vitest stack that this repo does not deploy. `search → run → verify` (CLAUDE.md 0.25) caught it before any execution. The verbatim-message signing contract from round 3 is preserved (the function verifies the exact bytes the client signed — no re-serialization — so python `json.dumps` whole-number `5.0`/`0.0` is accepted, never 401'd).

**Tech Stack:** Netlify Functions (Node 20, CommonJS), `ethers` v6 (EIP-191 `verifyMessage`), Supabase REST (PostgREST upsert), `node:test`. Automaton side: bash + curl + python3 + `eth_account` (already present).

**Scope:** ONE self-contained subsystem (the telemetry pipeline). Earn (A3), Stripe spawn (A8b), UI pages (A8c) are separate plans. Unblocked (does not depend on earn landing); delivers the "全個体収支を透明公開" success criterion + spec25 G1.

---

## File Structure
- Create `apps/landing/netlify/functions/_lib/telemetry-schema.js` — hand-rolled wire-shape validator (repo style; zod is not a dep). One responsibility: validate the payload object.
- Create `apps/landing/netlify/functions/_lib/telemetry-verify.js` — `canonicalMessage` (client-side helper) + `verifyTelemetry(message, signature, ctx)` (pure: parse + schema + freshness + monotonic + EIP-191 recover over the **verbatim** message). No I/O.
- Create `apps/landing/netlify/functions/_lib/telemetry-store.js` — `getLastTs` + `upsertInstance` via Supabase REST `fetch` (injectable `f` for tests). The only file that touches the DB.
- Create `apps/landing/netlify/functions/_lib/telemetry-aggregate.js` — `aggregate(rows)` → dashboard shape (pure).
- Create `apps/landing/netlify/functions/telemetry.js` — POST handler (wires verify + store).
- Create `apps/landing/netlify/functions/dashboard-sync.js` — GET handler (reads instances → aggregate).
- Create `apps/landing/netlify/functions/_lib/__tests__/*.test.js` — node:test for every module + both handlers.
- Create `apps/landing/supabase/instances.sql` — the table (applied to the EXISTING project, ops step).
- Modify `apps/landing/package.json` — add `ethers` dep + a `test:telemetry` script.
- Create `~/anicca/skills/report/anicca-report.sh` (canonical; mirrored to `/opt/anicca-report.sh` on the droplet) — per-wake email + signed telemetry POST.

---

## Task 1: Deps + test script

**Files:**
- Modify: `apps/landing/package.json`

- [ ] **Step 1: Add the ethers runtime dep (needed by verify + by the signing in tests)**

Run:
```bash
cd apps/landing && npm i ethers@^6
```
(`ethers` v6 ships dual CJS/ESM, so the CommonJS Netlify Functions can `require('ethers')`. viem is ESM-only and would break `require` — do NOT use it here.)

- [ ] **Step 2: Add a test script to package.json**

In `apps/landing/package.json` `"scripts"`, add:
```json
"test:telemetry": "node --test netlify/functions/_lib/__tests__/"
```
(Node 20's built-in runner recurses the given directory and runs every `*.test.js`. No vitest/jest dependency.)

- [ ] **Step 3: Verify the runner works (no tests yet)**

Run: `cd apps/landing && mkdir -p netlify/functions/_lib/__tests__ && node --test netlify/functions/_lib/__tests__/`
Expected: exits 0 with "tests 0" (runner works, nothing to run yet).

- [ ] **Step 4: Commit**

```bash
cd ~/anicca-project && git add apps/landing/package.json apps/landing/package-lock.json
git commit -m "chore(landing): add ethers v6 for telemetry EIP-191 verify + node:test script"
```

---

## Task 2: Payload schema (hand-rolled validator)

**Files:**
- Create: `apps/landing/netlify/functions/_lib/telemetry-schema.js`
- Test: `apps/landing/netlify/functions/_lib/__tests__/schema.test.js`

- [ ] **Step 1: Write the failing test**

Create `apps/landing/netlify/functions/_lib/__tests__/schema.test.js`:
```js
const { test } = require("node:test");
const assert = require("node:assert");
const { validate } = require("../telemetry-schema");

const valid = { id: "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21", ts: 1781450000, host: "akash",
  geo: "US", model_live: "auto", model_tier: "free", net_worth_usd: 0.0059, revenue_mo_usd: 0,
  burn_day_usd: 0, runway_days: 999, status: "alive" };

test("accepts a valid payload", () => {
  const r = validate(valid);
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.payload.id, valid.id);
});
test("rejects a bad wallet id", () => {
  assert.strictEqual(validate({ ...valid, id: "nope" }).ok, false);
});
test("rejects negative runway", () => {
  assert.strictEqual(validate({ ...valid, runway_days: -1 }).ok, false);
});
test("rejects a bad model_tier", () => {
  assert.strictEqual(validate({ ...valid, model_tier: "gpt" }).ok, false);
});
test("rejects null", () => {
  assert.strictEqual(validate(null).ok, false);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/landing && node --test netlify/functions/_lib/__tests__/schema.test.js`
Expected: FAIL — `Cannot find module '../telemetry-schema'`.

- [ ] **Step 3: Write the implementation**

Create `apps/landing/netlify/functions/_lib/telemetry-schema.js`:
```js
// Hand-rolled validator (matches repo style — fashion webhook validates inline; zod is not a dep).
// Returns { ok:true, payload } or { ok:false, reason:"schema" }.
function validate(o) {
  if (o === null || typeof o !== "object") return { ok: false, reason: "schema" };
  if (typeof o.id !== "string" || !/^0x[a-fA-F0-9]{40}$/.test(o.id)) return { ok: false, reason: "schema" };
  if (!Number.isInteger(o.ts) || o.ts <= 0) return { ok: false, reason: "schema" };
  for (const k of ["host", "geo", "model_live"]) {
    if (typeof o[k] !== "string" || o[k].length === 0) return { ok: false, reason: "schema" };
  }
  if (o.model_tier !== "frontier" && o.model_tier !== "free") return { ok: false, reason: "schema" };
  if (typeof o.net_worth_usd !== "number" || o.net_worth_usd < 0) return { ok: false, reason: "schema" };
  if (typeof o.revenue_mo_usd !== "number") return { ok: false, reason: "schema" };
  if (typeof o.burn_day_usd !== "number" || o.burn_day_usd < 0) return { ok: false, reason: "schema" };
  if (!Number.isInteger(o.runway_days) || o.runway_days < 0) return { ok: false, reason: "schema" };
  if (!["alive", "critical", "dead"].includes(o.status)) return { ok: false, reason: "schema" };
  return { ok: true, payload: o };
}
module.exports = { validate };
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd apps/landing && node --test netlify/functions/_lib/__tests__/schema.test.js`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
cd ~/anicca-project && git add apps/landing/netlify/functions/_lib/telemetry-schema.js apps/landing/netlify/functions/_lib/__tests__/schema.test.js
git commit -m "feat(telemetry): payload validator (hand-rolled, no zod dep)"
```

---

## Task 3: Verify — verbatim EIP-191 + freshness + monotonic (pure, spec25 G1)

**Files:**
- Create: `apps/landing/netlify/functions/_lib/telemetry-verify.js`
- Test: `apps/landing/netlify/functions/_lib/__tests__/verify.test.js`

The function verifies the **verbatim** message string the client signed (no re-serialization), so cross-language number formatting (`5` vs `5.0`, `1e-05` vs `0.00001`) never reaches `verifyMessage`. ethers v6 `verifyMessage(str, sig)` applies the same EIP-191 personal-sign prefix as python `eth_account.encode_defunct(text=...)` and viem `recoverMessageAddress` → cross-language compatible.

- [ ] **Step 1: Write the failing test**

Create `apps/landing/netlify/functions/_lib/__tests__/verify.test.js`:
```js
const { test } = require("node:test");
const assert = require("node:assert");
const { Wallet } = require("ethers");
const { canonicalMessage, verifyTelemetry } = require("../telemetry-verify");

const pk = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"; // test key
const w = new Wallet(pk);
const addr = w.address.toLowerCase();

function obj(ts, over = {}) {
  return { id: addr, ts, host: "akash", geo: "US", model_live: "x", model_tier: "free",
    net_worth_usd: 1, revenue_mo_usd: 0, burn_day_usd: 0.1, runway_days: 10, status: "alive", ...over };
}

test("accepts a fresh, correctly-signed, monotonic message", async () => {
  const now = Math.floor(Date.now() / 1000); const msg = canonicalMessage(obj(now));
  const sig = await w.signMessage(msg);
  const r = verifyTelemetry(msg, sig, { now, lastTs: 0 });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.payload.id, addr);
});

test("accepts python-style whole-number floats (5.0 / 0.0) — the prod bug class", async () => {
  const now = Math.floor(Date.now() / 1000);
  // EXACTLY what python json.dumps(...,separators=(',',':')) emits for whole-dollar balances:
  const msg = `{"id":"${addr}","ts":${now},"host":"akash","geo":"US","model_live":"x","model_tier":"free","net_worth_usd":5.0,"revenue_mo_usd":0.0,"burn_day_usd":0,"runway_days":10,"status":"alive"}`;
  const sig = await w.signMessage(msg);
  const r = verifyTelemetry(msg, sig, { now, lastTs: 0 });
  assert.strictEqual(r.ok, true);
  assert.strictEqual(r.payload.net_worth_usd, 5);
  assert.strictEqual(r.payload.revenue_mo_usd, 0);
});

test("rejects malformed json", () => {
  const r = verifyTelemetry("{not json", "0x00", { now: 1, lastTs: 0 });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, "bad_json");
});

test("rejects a schema violation", async () => {
  const msg = JSON.stringify({ id: "nope" });
  const sig = await w.signMessage(msg);
  const r = verifyTelemetry(msg, sig, { now: 1, lastTs: 0 });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, "schema");
});

test("rejects a wrong signer", async () => {
  const now = Math.floor(Date.now() / 1000);
  const msg = canonicalMessage(obj(now, { id: "0x000000000000000000000000000000000000dead" }));
  const sig = await w.signMessage(msg); // signed by w, but id claims the dead addr
  const r = verifyTelemetry(msg, sig, { now, lastTs: 0 });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, "signer_mismatch");
});

test("rejects a bad signature", () => {
  const now = Math.floor(Date.now() / 1000); const msg = canonicalMessage(obj(now));
  const r = verifyTelemetry(msg, "0xdeadbeef", { now, lastTs: 0 });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, "bad_signature");
});

test("rejects a stale ts (>60s old)", async () => {
  const now = Math.floor(Date.now() / 1000); const msg = canonicalMessage(obj(now - 120));
  const sig = await w.signMessage(msg);
  const r = verifyTelemetry(msg, sig, { now, lastTs: 0 });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, "stale");
});

test("rejects a replay (ts <= lastTs)", async () => {
  const now = Math.floor(Date.now() / 1000); const msg = canonicalMessage(obj(now));
  const sig = await w.signMessage(msg);
  const r = verifyTelemetry(msg, sig, { now, lastTs: now });
  assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, "replay");
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/landing && node --test netlify/functions/_lib/__tests__/verify.test.js`
Expected: FAIL — `Cannot find module '../telemetry-verify'`.

- [ ] **Step 3: Write the implementation**

Create `apps/landing/netlify/functions/_lib/telemetry-verify.js`:
```js
const { verifyMessage } = require("ethers");
const { validate } = require("./telemetry-schema");

// CLIENT-SIDE format helper only. The verifier NEVER calls this on inbound data — it recovers the
// signer from the verbatim `message` bytes. Re-serializing would diverge across languages
// (JS JSON.stringify(5.0)==="5" but python json.dumps(5.0)==="5.0") and 401 every whole-number balance.
function canonicalMessage(p) {
  return JSON.stringify({
    id: p.id, ts: p.ts, host: p.host, geo: p.geo, model_live: p.model_live,
    model_tier: p.model_tier, net_worth_usd: p.net_worth_usd, revenue_mo_usd: p.revenue_mo_usd,
    burn_day_usd: p.burn_day_usd, runway_days: p.runway_days, status: p.status,
  });
}

// Verifies the exact string the client signed. Parses it for schema + checks, but recovers the
// signer from `message` verbatim. ethers verifyMessage is synchronous in v6.
function verifyTelemetry(message, signature, ctx) {
  let raw;
  try { raw = JSON.parse(message); } catch { return { ok: false, reason: "bad_json" }; }
  const v = validate(raw);
  if (!v.ok) return v;
  const p = v.payload;
  if (p.ts > ctx.now + 5) return { ok: false, reason: "future" };
  if (ctx.now - p.ts > 60) return { ok: false, reason: "stale" };
  if (p.ts <= ctx.lastTs) return { ok: false, reason: "replay" };
  let signer;
  try { signer = verifyMessage(message, signature); } catch { return { ok: false, reason: "bad_signature" }; }
  if (signer.toLowerCase() !== p.id.toLowerCase()) return { ok: false, reason: "signer_mismatch" };
  return { ok: true, payload: p };
}

module.exports = { canonicalMessage, verifyTelemetry };
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd apps/landing && node --test netlify/functions/_lib/__tests__/verify.test.js`
Expected: PASS (8 tests — incl. python-style `5.0`/`0.0` acceptance).

- [ ] **Step 5: Commit**

```bash
cd ~/anicca-project && git add apps/landing/netlify/functions/_lib/telemetry-verify.js apps/landing/netlify/functions/_lib/__tests__/verify.test.js
git commit -m "feat(telemetry): verbatim EIP-191 verify + freshness + monotonic replay defense (ethers, spec25 G1)"
```

---

## Task 4: Supabase store (REST) + table

**Files:**
- Create: `apps/landing/netlify/functions/_lib/telemetry-store.js`
- Create: `apps/landing/supabase/instances.sql`
- Test: `apps/landing/netlify/functions/_lib/__tests__/store.test.js`

- [ ] **Step 1: Write the table DDL**

Create `apps/landing/supabase/instances.sql`:
```sql
create table if not exists instances (
  id text primary key,                -- wallet address (lowercase)
  ts bigint not null,                 -- last accepted unix ts (monotonic)
  host text not null, geo text not null,
  model_live text not null, model_tier text not null,
  net_worth_usd double precision not null, revenue_mo_usd double precision not null,
  burn_day_usd double precision not null, runway_days int not null,
  status text not null, updated_at timestamptz not null default now()
);
-- RLS: service-role key bypasses RLS, so no policy needed for the function. Keep RLS enabled
-- so the anon key cannot read/write directly.
alter table instances enable row level security;
```

- [ ] **Step 2: Write the failing test (inject a fake fetch)**

Create `apps/landing/netlify/functions/_lib/__tests__/store.test.js`:
```js
const { test } = require("node:test");
const assert = require("node:assert");
const { getLastTs, upsertInstance } = require("../telemetry-store");

const cfg = { url: "https://x.supabase.co", key: "svc" };

test("getLastTs returns 0 when no row", async () => {
  const f = async () => ({ ok: true, json: async () => [] });
  assert.strictEqual(await getLastTs("0xABC", { ...cfg, f }), 0);
});
test("getLastTs returns the existing ts and queries lowercased id", async () => {
  let calledUrl = "";
  const f = async (u) => { calledUrl = u; return { ok: true, json: async () => [{ ts: 123 }] }; };
  assert.strictEqual(await getLastTs("0xABC", { ...cfg, f }), 123);
  assert.ok(calledUrl.includes("id=eq.0xabc"));
});
test("upsertInstance POSTs a lowercased row with merge-duplicates", async () => {
  let opts = null, url = "";
  const f = async (u, o) => { url = u; opts = o; return { ok: true, text: async () => "" }; };
  await upsertInstance({ id: "0xABC", ts: 5, net_worth_usd: 5 }, { ...cfg, f });
  const sent = JSON.parse(opts.body);
  assert.strictEqual(sent.id, "0xabc");                 // lowercased
  assert.ok(opts.headers.Prefer.includes("merge-duplicates"));
  assert.ok(url.includes("on_conflict=id"));
});
test("upsertInstance throws on a non-ok response", async () => {
  const f = async () => ({ ok: false, status: 409, text: async () => "conflict" });
  await assert.rejects(() => upsertInstance({ id: "0xabc", ts: 1 }, { ...cfg, f }), /supabase 409/);
});
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd apps/landing && node --test netlify/functions/_lib/__tests__/store.test.js`
Expected: FAIL — `Cannot find module '../telemetry-store'`.

- [ ] **Step 4: Write the implementation**

Create `apps/landing/netlify/functions/_lib/telemetry-store.js`:
```js
// Supabase via REST (PostgREST) — same pattern as netlify/functions/stripe-fashion-webhook.js.
// `f` is injectable for tests; defaults to the platform fetch (Node 20 global).
function headers(key) {
  return { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json" };
}

async function getLastTs(id, { url, key, f = fetch }) {
  const r = await f(`${url}/rest/v1/instances?id=eq.${id.toLowerCase()}&select=ts`, { headers: headers(key) });
  if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
  const rows = await r.json();
  return Array.isArray(rows) && rows[0] ? rows[0].ts : 0;
}

async function upsertInstance(p, { url, key, f = fetch }) {
  const r = await f(`${url}/rest/v1/instances?on_conflict=id`, {
    method: "POST",
    headers: { ...headers(key), Prefer: "resolution=merge-duplicates,return=minimal" },
    body: JSON.stringify({ ...p, id: p.id.toLowerCase(), updated_at: new Date().toISOString() }),
  });
  if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
}

module.exports = { getLastTs, upsertInstance };
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd apps/landing && node --test netlify/functions/_lib/__tests__/store.test.js`
Expected: PASS (4 tests).

- [ ] **Step 6: Apply the table to the EXISTING Supabase project (ops step, Dais infra — C1 carve-out)**

The project already exists (`https://cycgdwndgfgdbnndithc.supabase.co`). Run `apps/landing/supabase/instances.sql` in that project's **SQL editor** (or via `psql "$SUPABASE_DB_URL" -f apps/landing/supabase/instances.sql`). `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` are already set in Netlify env (used by `fashion_orders`) — no new secret needed. Confirm the table exists:
```bash
curl -s "$SUPABASE_URL/rest/v1/instances?select=id&limit=1" -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
```
Expected: `[]` (empty array = table exists, no rows yet). A 404/relation-error means the DDL was not applied.

- [ ] **Step 7: Commit**

```bash
cd ~/anicca-project && git add apps/landing/netlify/functions/_lib/telemetry-store.js apps/landing/supabase/instances.sql apps/landing/netlify/functions/_lib/__tests__/store.test.js
git commit -m "feat(telemetry): Supabase REST store (lowercased id, PostgREST upsert) + instances table"
```

---

## Task 5: telemetry function (POST handler)

**Files:**
- Create: `apps/landing/netlify/functions/telemetry.js`
- Test: `apps/landing/netlify/functions/_lib/__tests__/handler-telemetry.test.js`

- [ ] **Step 1: Write the failing test (stub global fetch for the store)**

Create `apps/landing/netlify/functions/_lib/__tests__/handler-telemetry.test.js`:
```js
const { test, beforeEach } = require("node:test");
const assert = require("node:assert");
const { Wallet } = require("ethers");
const { canonicalMessage } = require("../telemetry-verify");
const { handler } = require("../../telemetry");

const w = new Wallet("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d");
const addr = w.address.toLowerCase();

let lastTs, upserts, origFetch;
beforeEach(() => {
  lastTs = 0; upserts = [];
  process.env.SUPABASE_URL = "https://x.supabase.co";
  process.env.SUPABASE_SERVICE_ROLE_KEY = "svc";
  origFetch = global.fetch;
  global.fetch = async (url, opts) => {
    if (!opts || opts.method !== "POST") return { ok: true, json: async () => (lastTs ? [{ ts: lastTs }] : []) };
    const row = JSON.parse(opts.body); upserts.push(row); lastTs = row.ts;
    return { ok: true, text: async () => "" };
  };
});

function ev(body) { return { httpMethod: "POST", body: JSON.stringify(body), headers: {} }; }
function objStr(over = {}) {
  const now = Math.floor(Date.now() / 1000);
  return canonicalMessage({ id: addr, ts: now, host: "akash", geo: "US", model_live: "x",
    model_tier: "free", net_worth_usd: 1, revenue_mo_usd: 0, burn_day_usd: 0.1, runway_days: 10, status: "alive", ...over });
}

test("202 on a valid signed fresh message", async () => {
  const message = objStr(); const signature = await w.signMessage(message);
  const res = await handler(ev({ message, signature }));
  assert.strictEqual(res.statusCode, 202);
  assert.strictEqual(upserts.length, 1);
  assert.strictEqual(upserts[0].id, addr);
  global.fetch = origFetch;
});
test("401 on signer mismatch", async () => {
  const message = objStr({ id: "0x000000000000000000000000000000000000dead" });
  const signature = await w.signMessage(message); // signed by w, id claims dead addr
  const res = await handler(ev({ message, signature }));
  assert.strictEqual(res.statusCode, 401);
  global.fetch = origFetch;
});
test("400 on schema violation", async () => {
  const message = JSON.stringify({ id: "nope" }); const signature = await w.signMessage(message);
  const res = await handler(ev({ message, signature }));
  assert.strictEqual(res.statusCode, 400);
  global.fetch = origFetch;
});
test("400 on missing message/signature", async () => {
  const res = await handler(ev({ signature: "0x00" }));
  assert.strictEqual(res.statusCode, 400);
  global.fetch = origFetch;
});
test("405 on non-POST", async () => {
  const res = await handler({ httpMethod: "GET", headers: {} });
  assert.strictEqual(res.statusCode, 405);
  global.fetch = origFetch;
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/landing && node --test netlify/functions/_lib/__tests__/handler-telemetry.test.js`
Expected: FAIL — `Cannot find module '../../telemetry'`.

- [ ] **Step 3: Write the implementation**

Create `apps/landing/netlify/functions/telemetry.js`:
```js
const { verifyTelemetry } = require("./_lib/telemetry-verify");
const { getLastTs, upsertInstance } = require("./_lib/telemetry-store");

// 400-class (caller error) vs 401-class (auth/replay). The handler NEVER re-serializes the payload —
// verifyTelemetry reads the verbatim signed `message` (round-3 signing-bytes contract).
const BAD_REQUEST = new Set(["bad_json", "schema"]);

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };
  const url = process.env.SUPABASE_URL, key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return { statusCode: 500, body: "missing supabase env" };

  let body;
  try { body = JSON.parse(event.body || ""); } catch { return { statusCode: 400, body: "bad_json" }; }
  const message = body.message, signature = body.signature;
  if (typeof message !== "string" || typeof signature !== "string") {
    return { statusCode: 400, body: "bad_request" };
  }
  // extract id (for the per-id monotonic lookup) without trusting it — verify binds it to the bytes
  let id;
  try { id = JSON.parse(message).id; } catch { return { statusCode: 400, body: "bad_json" }; }
  if (typeof id !== "string") return { statusCode: 400, body: "schema" };

  const cfg = { url, key };
  const lastTs = await getLastTs(id, cfg);
  const now = Math.floor(Date.now() / 1000);
  const v = verifyTelemetry(message, signature, { now, lastTs });
  if (!v.ok) return { statusCode: BAD_REQUEST.has(v.reason) ? 400 : 401, body: v.reason };
  await upsertInstance(v.payload, cfg);
  return { statusCode: 202, body: JSON.stringify({ ok: true }) };
};
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd apps/landing && node --test netlify/functions/_lib/__tests__/handler-telemetry.test.js`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
cd ~/anicca-project && git add apps/landing/netlify/functions/telemetry.js apps/landing/netlify/functions/_lib/__tests__/handler-telemetry.test.js
git commit -m "feat(telemetry): POST /.netlify/functions/telemetry (verify verbatim -> Supabase upsert)"
```

---

## Task 6: dashboard-sync function (aggregate)

**Files:**
- Create: `apps/landing/netlify/functions/_lib/telemetry-aggregate.js`
- Create: `apps/landing/netlify/functions/dashboard-sync.js`
- Test: `apps/landing/netlify/functions/_lib/__tests__/aggregate.test.js`

- [ ] **Step 1: Write the failing test**

Create `apps/landing/netlify/functions/_lib/__tests__/aggregate.test.js`:
```js
const { test } = require("node:test");
const assert = require("node:assert");
const { aggregate } = require("../telemetry-aggregate");

const rows = [
  // self-funded: revenue/30 (0.33) >= burn (0.10), alive
  { id: "0x1", net_worth_usd: 100, revenue_mo_usd: 10, burn_day_usd: 0.1, runway_days: 30, status: "alive", host: "akash", model_tier: "frontier" },
  // NOT self-funded: revenue/30 (0.16) < burn (0.50), critical
  { id: "0x2", net_worth_usd: 50, revenue_mo_usd: 5, burn_day_usd: 0.5, runway_days: 2, status: "critical", host: "do", model_tier: "free" },
];

test("computes totals + leaderboard (net worth desc)", () => {
  const d = aggregate(rows);
  assert.strictEqual(d.total_net_worth_usd, 150);
  assert.strictEqual(d.alive, 2);
  assert.strictEqual(d.leaderboard[0].id, "0x1");
});
test("self_funded_pct = % whose monthly revenue covers daily burn AND not dead (NOT a model proxy)", () => {
  assert.strictEqual(aggregate(rows).self_funded_pct, 50); // only 0x1 covers its burn
});
test("frontier_pct is reported separately (frontier is NOT self-funding)", () => {
  assert.strictEqual(aggregate(rows).frontier_pct, 50);
});
test("handles empty rows without div-by-zero", () => {
  const d = aggregate([]);
  assert.strictEqual(d.self_funded_pct, 0);
  assert.strictEqual(d.frontier_pct, 0);
  assert.strictEqual(d.alive, 0);
  assert.strictEqual(d.total_net_worth_usd, 0);
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/landing && node --test netlify/functions/_lib/__tests__/aggregate.test.js`
Expected: FAIL — `Cannot find module '../telemetry-aggregate'`.

- [ ] **Step 3: Write the implementation**

Create `apps/landing/netlify/functions/_lib/telemetry-aggregate.js`:
```js
function aggregate(rows) {
  const total_net_worth_usd = rows.reduce((s, r) => s + r.net_worth_usd, 0);
  const earned_mo_usd = rows.reduce((s, r) => s + r.revenue_mo_usd, 0);
  const alive = rows.filter((r) => r.status !== "dead").length;
  // self-funded = monthly revenue covers daily burn AND not dead (real economic test, NOT a model proxy)
  const selfFunded = rows.filter((r) => r.status !== "dead" && r.revenue_mo_usd / 30 >= r.burn_day_usd).length;
  const frontier = rows.filter((r) => r.model_tier === "frontier").length;
  const self_funded_pct = rows.length ? Math.round((selfFunded / rows.length) * 100) : 0;
  const frontier_pct = rows.length ? Math.round((frontier / rows.length) * 100) : 0;
  const leaderboard = [...rows].sort((a, b) => b.net_worth_usd - a.net_worth_usd);
  return { total_net_worth_usd, earned_mo_usd, alive, self_funded_pct, frontier_pct, leaderboard, updated_at: new Date().toISOString() };
}
module.exports = { aggregate };
```

Create `apps/landing/netlify/functions/dashboard-sync.js`:
```js
const { aggregate } = require("./_lib/telemetry-aggregate");

exports.handler = async () => {
  const url = process.env.SUPABASE_URL, key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return { statusCode: 500, body: "missing supabase env" };
  const r = await fetch(`${url}/rest/v1/instances?select=*`, {
    headers: { apikey: key, Authorization: `Bearer ${key}` },
  });
  if (!r.ok) return { statusCode: 502, body: `supabase ${r.status}` };
  const rows = await r.json();
  return {
    statusCode: 200,
    headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=15" },
    body: JSON.stringify(aggregate(Array.isArray(rows) ? rows : [])),
  };
};
```
(The /dashboard page fetches `/.netlify/functions/dashboard-sync` live; a Dais-owned build step may also snapshot it to `public/dashboard.json`. Rendering the page is a separate plan — this provides the real-data source.)

- [ ] **Step 4: Run to verify it passes**

Run: `cd apps/landing && node --test netlify/functions/_lib/__tests__/aggregate.test.js`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
cd ~/anicca-project && git add apps/landing/netlify/functions/_lib/telemetry-aggregate.js apps/landing/netlify/functions/dashboard-sync.js apps/landing/netlify/functions/_lib/__tests__/aggregate.test.js
git commit -m "feat(telemetry): dashboard-sync function (totals + leaderboard, real data only)"
```

---

## Task 7: Cross-language signing proof (python ↔ ethers, the whole-number bug class)

**Files:**
- Test: `apps/landing/netlify/functions/_lib/__tests__/cross-lang.test.js`

**Why (review rounds 3+4, verified empirically):** the old design re-serialized the parsed payload to recover the signer, but `JSON.stringify(5.0)==="5"` while python `json.dumps(5.0)==="5.0"` → 401 on every whole-dollar balance, passing all unit/smoke tests and failing only in prod. The fix verifies the **verbatim** bytes. This test proves a real **python-signed** message (with `5.0`/`0.0`) verifies in **ethers**, and documents why re-serialization was lossy.

- [ ] **Step 1: Write the test — ethers verifies a python-produced signature over a whole-number message**

This signs in python and verifies in node, so the cross-language contract is the actual unit under test. It shells out to python (which has `eth_account`, per the automaton box / Task 8). Create `apps/landing/netlify/functions/_lib/__tests__/cross-lang.test.js`:
```js
const { test } = require("node:test");
const assert = require("node:assert");
const { execFileSync } = require("node:child_process");
const { verifyTelemetry } = require("../telemetry-verify");

test("ethers verifies a python eth_account signature over a 5.0/0.0 message", () => {
  // python emits the verbatim message AND signs it; we verify with our function.
  const py = `
import json, time
from eth_account import Account
from eth_account.messages import encode_defunct
acct = Account.from_key("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d")
ts = int(time.time())
p = {"id": acct.address.lower(), "ts": ts, "host":"akash","geo":"US","model_live":"auto",
     "model_tier":"free","net_worth_usd": round(5.0,4), "revenue_mo_usd": round(0.0,4),
     "burn_day_usd":0, "runway_days":999, "status":"alive"}
msg = json.dumps(p, separators=(",",":"))            # emits "5.0"/"0.0"
s = Account.sign_message(encode_defunct(text=msg), private_key=acct.key).signature.hex()
sig = s if s.startswith("0x") else "0x"+s
print(json.dumps({"message": msg, "signature": sig, "ts": ts}))
`;
  let out;
  try { out = execFileSync("python3", ["-c", py], { encoding: "utf8" }); }
  catch (e) { console.log("SKIP: python3/eth_account unavailable —", e.message); return; }
  const { message, signature, ts } = JSON.parse(out);
  assert.ok(message.includes('"net_worth_usd":5.0'), "python must emit 5.0 (the bug input)");
  const r = verifyTelemetry(message, signature, { now: ts, lastTs: 0 });
  assert.strictEqual(r.ok, true);             // ethers recovers the signer from python's verbatim 5.0 message
  assert.strictEqual(r.payload.net_worth_usd, 5);
});

test("PROOF the old design was broken: re-stringifying drops the .0 (would 401)", () => {
  assert.strictEqual(
    JSON.stringify(JSON.parse('{"net_worth_usd":5.0,"revenue_mo_usd":0.0}')),
    '{"net_worth_usd":5,"revenue_mo_usd":0}'   // 5.0->5, 0.0->0 => different signed bytes
  );
});
```

- [ ] **Step 2: Run**

Run: `cd apps/landing && node --test netlify/functions/_lib/__tests__/cross-lang.test.js`
Expected: PASS (2 tests). The first proves python `eth_account` ↔ node `ethers` agree on the verbatim `5.0` message; if `python3`/`eth_account` is missing locally it SKIPs (the real cross-language proof also runs in Task 9 Step 3 against the live function).

- [ ] **Step 3: Commit**

```bash
cd ~/anicca-project && git add apps/landing/netlify/functions/_lib/__tests__/cross-lang.test.js
git commit -m "test(telemetry): python eth_account <-> ethers verbatim 5.0/0.0 cross-language proof"
```

---

## Task 8: Automaton report hook — per-wake email + signed telemetry POST

**Files:**
- Create: `~/anicca/skills/report/anicca-report.sh` (canonical — does NOT exist yet; this is a CREATE)
- Mirror: deployed `/opt/anicca-report.sh` on droplet 147.182.225.255

- [ ] **Step 1: Confirm the wallet env var name actually on the box (don't assume)**

Run:
```bash
ssh root@147.182.225.255 'grep -oiE "^[A-Z_]*WALLET[A-Z_]*=" /opt/anicca.env'
```
Expected: prints the real var (e.g. `BLOCKRUN_WALLET_KEY=`). Set `PKVAR` below to that exact name.

- [ ] **Step 2: Create the canonical report+telemetry script**

Create `~/anicca/skills/report/anicca-report.sh` (and scp to `/opt/anicca-report.sh`). Self-contained — computes `$W/$ETH/$USDC/$REV` itself. It POSTs to the Netlify function at `/.netlify/functions/telemetry`. `burn_day_usd/runway_days/status` are PLACEHOLDERS until the earn/burn meter lands (spec25 R4) — the function stores them as-is; /dashboard must label runway/self-funded as estimated until then:
```bash
#!/usr/bin/env bash
set -u
. /opt/anicca.env
PKVAR=BLOCKRUN_WALLET_KEY                 # <-- replace with the exact name Step 1 printed, if different
SIGNKEY="${!PKVAR}"                       # indirect expansion: value of the var named by $PKVAR
W=0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21
LOG=/var/log/anicca-daemon.log
DID="${1:-$(grep -oE "\[TOOL\] [a-z_]+" "$LOG" 2>/dev/null | tail -5 | sed "s/\[TOOL\] //" | tr "\n" "," | sed "s/,$//")}"; DID="${DID:-monitoring}"
NEXT="${2:-continue earning + self-improve}"
rpc(){ curl -s --max-time 10 https://mainnet.base.org -X POST -H "Content-Type: application/json" --data "$1" | python3 -c "import json,sys;print(json.load(sys.stdin).get('result','0x0'))"; }
ETH=$(python3 -c "print(round(int('$(rpc "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getBalance\",\"params\":[\"$W\",\"latest\"]}")',16)/1e18,6))")
USDC=$(python3 -c "print(round(int('$(rpc "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913\",\"data\":\"0x70a08231000000000000000000000000a3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21\"},\"latest\"]}")',16)/1e6,4))")
DAY=$(date -u +%Y%m%d); BASE=/var/lib/anicca/baseline-$DAY; mkdir -p /var/lib/anicca; [ -f "$BASE" ] || echo "$USDC" > "$BASE"
REV=$(python3 -c "print(round($USDC - $(cat "$BASE"),4))")
# --- email (AgentMail) ---
curl -s --max-time 20 -X POST "https://api.agentmail.to/v0/inboxes/anicca-genesis@agentmail.to/messages/send" \
  -H "Authorization: Bearer $AGENTMAIL_API_KEY" -H "Content-Type: application/json" \
  -d "$(python3 -c "import json;print(json.dumps({'to':['keiodaisuke@gmail.com','contact@aniccaai.com'],'subject':f'Anicca wake net \$$USDC','text':f'NET WORTH \$$USDC USDC (+$ETH ETH)\nREVENUE TODAY \$$REV\nDID $DID\nNEXT $NEXT'}))")" >/dev/null 2>&1
# --- telemetry: sign the VERBATIM message string and POST it as {message,signature} ---
TS=$(date -u +%s)
MSG=$(python3 -c "import json;print(json.dumps({'id':'$(echo $W|tr A-F a-f)','ts':$TS,'host':'akash','geo':'US','model_live':'auto','model_tier':'free','net_worth_usd':$USDC,'revenue_mo_usd':$REV,'burn_day_usd':0,'runway_days':999,'status':'alive'},separators=(',',':')))")
SIG=$(MSG="$MSG" SIGNKEY="$SIGNKEY" python3 - <<'PY'
import os
from eth_account import Account
from eth_account.messages import encode_defunct
s = Account.sign_message(encode_defunct(text=os.environ["MSG"]), private_key=os.environ["SIGNKEY"]).signature.hex()
print(s if s.startswith("0x") else "0x"+s)        # ethers verifyMessage requires 0x prefix
PY
)
BODY=$(MSG="$MSG" SIG="$SIG" python3 -c "import json,os;print(json.dumps({'message':os.environ['MSG'],'signature':os.environ['SIG']}))")
curl -s --max-time 15 -X POST "https://aniccaai.com/.netlify/functions/telemetry" -H "Content-Type: application/json" \
  -d "$BODY" >/dev/null 2>&1
echo "report+telemetry $TS" >> /var/log/anicca-report.log
```
(The signed `MSG` is sent VERBATIM as `message`; the function recovers the signer from these exact bytes, so python's `5.0`/`0.0` whole-number output is accepted, not 401'd. `id` is lowercased to match the store's `id.toLowerCase()`.)

- [ ] **Step 3: Commit canonical + scp to droplet**

```bash
cd ~/anicca && git add skills/report/anicca-report.sh && git commit -m "feat(report): per-wake email + signed telemetry POST (Netlify function)" && git push
scp ~/anicca/skills/report/anicca-report.sh root@147.182.225.255:/opt/anicca-report.sh
ssh root@147.182.225.255 'chmod +x /opt/anicca-report.sh; pip install -q eth_account'
```

---

## Task 9: Deploy + smoke + real E2E

**Pre-req (ops, Dais infra — C1 carve-out):** `instances` table applied to the existing Supabase project (Task 4 Step 6); `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` already in Netlify env (confirmed used by `fashion_orders`). Confirm before proceeding.

- [ ] **Step 1: Deploy the functions (push triggers Netlify)**

```bash
cd ~/anicca-project && git push   # netlify-deploy GHA on apps/landing/** -> aniccaai.com
```
Wait for the Netlify build to go green. (Functions in `apps/landing/netlify/functions/` are auto-bundled by Netlify with esbuild; `ethers` is bundled from `node_modules`.)

- [ ] **Step 2: SMOKE — locally-signed WHOLE-DOLLAR `5.0` payload → 202**

Run (signs with the test key, posts a whole-dollar `5.0` to exercise the prod bug class, hits the live function):
```bash
python3 - <<'PY'
import json,time,urllib.request
from eth_account import Account
from eth_account.messages import encode_defunct
acct=Account.from_key("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d")
p={'id':acct.address.lower(),'ts':int(time.time()),'host':'test','geo':'US','model_live':'x','model_tier':'free','net_worth_usd':round(5.0,4),'revenue_mo_usd':round(0.0,4),'burn_day_usd':0,'runway_days':10,'status':'alive'}
msg=json.dumps(p,separators=(',',':'))           # signed AND sent verbatim; emits "5.0"/"0.0"
s=Account.sign_message(encode_defunct(text=msg),private_key=acct.key).signature.hex()
sig=s if s.startswith("0x") else "0x"+s
body=json.dumps({'message':msg,'signature':sig}).encode()
req=urllib.request.Request("https://aniccaai.com/.netlify/functions/telemetry",data=body,headers={'Content-Type':'application/json'})
print("status", urllib.request.urlopen(req).status)
PY
```
Expected: `status 202` — a 202 on a whole-dollar `5.0` proves the verbatim-bytes contract works end-to-end (the round-3 bug cannot recur). (401 → signing path mismatch. 500 → Supabase env not set on Netlify. 404 → function not deployed / wrong path.)

- [ ] **Step 3: REAL E2E — genesis instance posts → dashboard-sync reflects real on-chain net worth**

```bash
ssh root@147.182.225.255 'bash /opt/anicca-report.sh'
sleep 3
curl -s "https://aniccaai.com/.netlify/functions/dashboard-sync" | python3 -c "import json,sys;d=json.load(sys.stdin);ids=[r['id'] for r in d['leaderboard']];print('genesis present:', '0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21' in ids, 'total_net:', d['total_net_worth_usd'])"
```
Expected: `genesis present: True`, `total_net` = the genesis wallet's REAL on-chain USDC. **Genuine E2E: a live instance signed+POSTed → Supabase → dashboard-sync reflects real chain data. No mock.**

- [ ] **Step 4: Commit evidence note**

```bash
cd ~/anicca-project
echo "E2E PASS $(date -u +%FT%TZ): genesis telemetry -> dashboard-sync, net=<paste>" >> docs/superpowers/plans/2026-06-15-anicca-telemetry-pipeline.md
git add -A && git commit -m "test(telemetry): E2E PASS — live instance signed POST -> dashboard reflects real net worth" && git push
```

---

## Self-Review
- **Spec coverage:** §2 telemetry (spec23) + G1 (spec25: Supabase, EIP-191, ts freshness 60s, per-id monotonic) + "全個体収支を透明公開" → Tasks 2–6. Replay/nonce (note1) = Task 3 stale/replay tests. ✅
- **Deployment reality (round 4):** static export → no App Router routes; everything is a Netlify Function (CJS `exports.handler`, `/.netlify/functions/<name>`), Supabase via REST `fetch`, `ethers` (CJS-safe) not viem, `node:test` not vitest, EXISTING Supabase project (only add `instances`). Verified against `next.config.mjs`, `netlify/functions/stripe-fashion-webhook.js`, `package.json`, and a live lib-availability check.
- **Signing-bytes contract (round 3, preserved):** the function verifies the VERBATIM signed message — no re-serialization → no cross-language number-format divergence (`5`/`5.0`, `1e-05`/`0.00001`). Pinned by Task 3 whole-number test + Task 7 python↔ethers proof.
- **Placeholders:** none — every step has runnable code/commands + expected output. `burn_day_usd/runway_days/status` in Task 8 are explicitly labeled estimates until the earn/burn meter lands (spec25 R4).
- **Type consistency:** `validate` → `{ok,payload}` reused by `verifyTelemetry`; store/handler/aggregate field names match the `instances` columns; handler stores `v.payload` (never re-serializes).
- **Gaps:** applying `instances.sql` to the existing Supabase project is the one ops step (Task 4 Step 6, Dais infra, C1 carve-out). `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` already exist in Netlify env.
- **E2E:** Task 9 Step 3 = real genesis instance → signed POST → dashboard-sync reflects real on-chain net worth. Not a mock. Step 2 smoke uses a whole-dollar `5.0` to prove the bug class is closed.
