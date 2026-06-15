# Anicca Telemetry Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each Anicca instance POSTs its own signed state (net worth, revenue, runway, model, host) every wake to a telemetry endpoint; the public /dashboard renders all instances in realtime — Aniccas never write the website.

**Architecture:** Next.js 14 App Router route `POST /api/telemetry` verifies an EIP-191 wallet signature (signer == instance id), enforces ts-freshness (60s) + per-id monotonic last_ts (replay/stale defense, spec25 G1), then upserts a row in Supabase Postgres `instances`. dashboard-sync (a Next route or build step, Dais-owned) reads `instances` → renders `public/dashboard.json`. The automaton's existing per-wake report hook (`/opt/anicca-report.sh`) is extended to POST the same data it already computes.

**Tech Stack:** Next.js 14, TypeScript, Supabase (`@supabase/supabase-js`), `viem` (EIP-191 `verifyMessage`/`recoverMessageAddress`), `vitest` (unit + E2E). Automaton side: bash + curl + python3 (already present).

**Scope:** This is ONE self-contained subsystem (the telemetry pipeline). Earn (A3), Stripe spawn (A8b), and the UI pages (A8c) are separate plans. This plan is unblocked (does not depend on earn landing) and delivers the "全個体収支を透明公開" success criterion + spec25 G1.

---

## File Structure
- Create `apps/landing/lib/telemetry/schema.ts` — the TelemetryPayload type + zod validator (one responsibility: the wire shape).
- Create `apps/landing/lib/telemetry/verify.ts` — pure signature + freshness + monotonic checks (no I/O; testable in isolation).
- Create `apps/landing/lib/telemetry/store.ts` — Supabase client + upsert/read (the only file that touches the DB).
- Create `apps/landing/app/api/telemetry/route.ts` — the POST handler (wires verify + store).
- Create `apps/landing/app/api/dashboard-sync/route.ts` — reads instances → writes dashboard.json shape (Dais-owned aggregation).
- Create `apps/landing/supabase/migrations/0001_instances.sql` — the table.
- Create tests under `apps/landing/lib/telemetry/__tests__/` and `apps/landing/app/api/telemetry/__tests__/`.
- Modify automaton report hook (`/opt/anicca-report.sh`, mirrored at `~/anicca/skills/report/anicca-report.sh`) to add the telemetry POST.
- Modify `apps/landing/package.json` — add deps + `test` script + vitest config.

---

## Task 1: Test tooling + deps

**Files:**
- Modify: `apps/landing/package.json`
- Create: `apps/landing/vitest.config.ts`

- [ ] **Step 1: Add deps + test script**

Run:
```bash
cd apps/landing && npm i @supabase/supabase-js viem zod && npm i -D vitest @vitest/coverage-v8 vite-tsconfig-paths
```
(`vite-tsconfig-paths` is REQUIRED — vitest does NOT read `tsconfig.json` `paths` by default; without it the `@/lib/...` imports in Tasks 5/6 throw "Failed to resolve import @/...". review-fix #1.)

- [ ] **Step 2: Add test script to package.json**

In `apps/landing/package.json` `"scripts"`, add:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 3: Create vitest config**

Create `apps/landing/vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config";
import tsconfigPaths from "vite-tsconfig-paths";
export default defineConfig({
  plugins: [tsconfigPaths()],   // resolves @/* from tsconfig (review-fix #1)
  test: { environment: "node", include: ["**/__tests__/**/*.test.ts"] },
});
```

- [ ] **Step 4: Verify vitest runs (no tests yet = exit 0 / "no tests")**

Run: `cd apps/landing && npx vitest run`
Expected: runs, "No test files found" (exit 0) — tooling works.

- [ ] **Step 5: Commit**

```bash
git add apps/landing/package.json apps/landing/vitest.config.ts apps/landing/package-lock.json
git commit -m "chore(landing): add vitest + supabase/viem/zod for telemetry"
```

---

## Task 2: Telemetry payload schema

**Files:**
- Create: `apps/landing/lib/telemetry/schema.ts`
- Test: `apps/landing/lib/telemetry/__tests__/schema.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { TelemetrySchema } from "../schema";

describe("TelemetrySchema", () => {
  const valid = {
    id: "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21",
    ts: 1781450000, host: "akash", geo: "US-west", model_live: "claude-opus-4-8",
    model_tier: "frontier", net_worth_usd: 12.4, revenue_mo_usd: 8.1,
    burn_day_usd: 0.42, runway_days: 29, status: "alive",
  };
  it("accepts a valid payload", () => {
    expect(TelemetrySchema.parse(valid)).toMatchObject({ id: valid.id });
  });
  it("rejects a bad wallet id", () => {
    expect(() => TelemetrySchema.parse({ ...valid, id: "nope" })).toThrow();
  });
  it("rejects negative runway", () => {
    expect(() => TelemetrySchema.parse({ ...valid, runway_days: -1 })).toThrow();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/landing && npx vitest run lib/telemetry/__tests__/schema.test.ts`
Expected: FAIL — cannot find module `../schema`.

- [ ] **Step 3: Write minimal implementation**

Create `apps/landing/lib/telemetry/schema.ts`:
```ts
import { z } from "zod";
export const TelemetrySchema = z.object({
  id: z.string().regex(/^0x[a-fA-F0-9]{40}$/),
  ts: z.number().int().positive(),
  host: z.string().min(1),
  geo: z.string().min(1),
  model_live: z.string().min(1),
  model_tier: z.enum(["frontier", "free"]),
  net_worth_usd: z.number().nonnegative(),
  revenue_mo_usd: z.number(),
  burn_day_usd: z.number().nonnegative(),
  runway_days: z.number().int().nonnegative(),
  status: z.enum(["alive", "critical", "dead"]),
});
export type TelemetryPayload = z.infer<typeof TelemetrySchema>;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/landing && npx vitest run lib/telemetry/__tests__/schema.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/landing/lib/telemetry/schema.ts apps/landing/lib/telemetry/__tests__/schema.test.ts
git commit -m "feat(telemetry): payload schema + validation"
```

---

## Task 3: Signature + freshness + monotonic verification (pure, spec25 G1)

**Files:**
- Create: `apps/landing/lib/telemetry/verify.ts`
- Test: `apps/landing/lib/telemetry/__tests__/verify.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { privateKeyToAccount } from "viem/accounts";
import { canonicalMessage, verifyTelemetry } from "../verify";

const pk = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"; // test key
const acct = privateKeyToAccount(pk);

// verifyTelemetry takes the VERBATIM signed message string (not a re-serialized object).
// The route never re-stringifies — this kills cross-language number-format divergence
// (JS "5" vs python "5.0", "1e-05" vs "0.00001") that would 401 every whole-number balance.
function obj(ts: number, over: Record<string, unknown> = {}) {
  return { id: acct.address.toLowerCase(), ts, host: "akash", geo: "US", model_live: "x", model_tier: "free",
    net_worth_usd: 1, revenue_mo_usd: 0, burn_day_usd: 0.1, runway_days: 10, status: "alive", ...over };
}

describe("verifyTelemetry (verbatim message)", () => {
  it("accepts a fresh, correctly-signed, monotonic message", async () => {
    const now = Math.floor(Date.now() / 1000); const msg = canonicalMessage(obj(now) as any);
    const sig = await acct.signMessage({ message: msg });
    const r = await verifyTelemetry(msg, sig, { now, lastTs: 0 });
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.payload.id).toBe(acct.address.toLowerCase());
  });
  it("accepts python-style whole-number floats (5.0 / 0.0) — the production bug class", async () => {
    // python round(5.0,4) → json.dumps emits "5.0"; verbatim verify must accept it (re-stringify would 401)
    const now = Math.floor(Date.now() / 1000);
    const msg = `{"id":"${acct.address.toLowerCase()}","ts":${now},"host":"akash","geo":"US","model_live":"x","model_tier":"free","net_worth_usd":5.0,"revenue_mo_usd":0.0,"burn_day_usd":0,"runway_days":10,"status":"alive"}`;
    const sig = await acct.signMessage({ message: msg });
    const r = await verifyTelemetry(msg, sig, { now, lastTs: 0 });
    expect(r.ok).toBe(true);
    if (r.ok) { expect(r.payload.net_worth_usd).toBe(5); expect(r.payload.revenue_mo_usd).toBe(0); }
  });
  it("rejects malformed json", async () => {
    const r = await verifyTelemetry("{not json", "0x00" as any, { now: 1, lastTs: 0 });
    expect(r.ok).toBe(false); if (!r.ok) expect(r.reason).toBe("bad_json");
  });
  it("rejects a schema violation", async () => {
    const msg = JSON.stringify({ id: "nope" });
    const sig = await acct.signMessage({ message: msg });
    const r = await verifyTelemetry(msg, sig, { now: 1, lastTs: 0 });
    expect(r.ok).toBe(false); if (!r.ok) expect(r.reason).toBe("schema");
  });
  it("rejects a wrong signer", async () => {
    const now = Math.floor(Date.now() / 1000);
    const msg = canonicalMessage(obj(now, { id: "0x000000000000000000000000000000000000dead" }) as any);
    const sig = await acct.signMessage({ message: msg }); // signed by acct, but id claims the dead addr
    const r = await verifyTelemetry(msg, sig, { now, lastTs: 0 });
    expect(r.ok).toBe(false); if (!r.ok) expect(r.reason).toBe("signer_mismatch");
  });
  it("rejects a stale ts (>60s old)", async () => {
    const now = Math.floor(Date.now() / 1000); const msg = canonicalMessage(obj(now - 120) as any);
    const sig = await acct.signMessage({ message: msg });
    const r = await verifyTelemetry(msg, sig, { now, lastTs: 0 });
    expect(r.ok).toBe(false); if (!r.ok) expect(r.reason).toBe("stale");
  });
  it("rejects a replay (ts <= lastTs)", async () => {
    const now = Math.floor(Date.now() / 1000); const msg = canonicalMessage(obj(now) as any);
    const sig = await acct.signMessage({ message: msg });
    const r = await verifyTelemetry(msg, sig, { now, lastTs: now });
    expect(r.ok).toBe(false); if (!r.ok) expect(r.reason).toBe("replay");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/landing && npx vitest run lib/telemetry/__tests__/verify.test.ts`
Expected: FAIL — cannot find module `../verify`.

- [ ] **Step 3: Write minimal implementation**

Create `apps/landing/lib/telemetry/verify.ts`:
```ts
import { recoverMessageAddress } from "viem";
import { TelemetrySchema, type TelemetryPayload } from "./schema";

// CLIENT-SIDE format helper only. The ROUTE/verifier never calls this on inbound data —
// it verifies the VERBATIM message bytes the client signed (see verifyTelemetry). Re-serializing
// a parsed payload would diverge across languages (JS JSON.stringify(5.0)==="5" but python
// json.dumps(5.0)==="5.0") and 401 every whole-number balance. So we sign+recover over raw bytes.
export function canonicalMessage(p: TelemetryPayload): string {
  return JSON.stringify({
    id: p.id, ts: p.ts, host: p.host, geo: p.geo, model_live: p.model_live,
    model_tier: p.model_tier, net_worth_usd: p.net_worth_usd, revenue_mo_usd: p.revenue_mo_usd,
    burn_day_usd: p.burn_day_usd, runway_days: p.runway_days, status: p.status,
  });
}

// Verifies the exact string the client signed. Parses it for schema + checks, but recovers the
// signer from `message` verbatim — no re-stringification anywhere in the trust path.
export async function verifyTelemetry(
  message: string, signature: `0x${string}`,
  ctx: { now: number; lastTs: number }
): Promise<{ ok: true; payload: TelemetryPayload } | { ok: false; reason: string }> {
  let raw: unknown;
  try { raw = JSON.parse(message); } catch { return { ok: false, reason: "bad_json" }; }
  const parsed = TelemetrySchema.safeParse(raw);
  if (!parsed.success) return { ok: false, reason: "schema" };
  const p = parsed.data;
  if (p.ts > ctx.now + 5) return { ok: false, reason: "future" };
  if (ctx.now - p.ts > 60) return { ok: false, reason: "stale" };
  if (p.ts <= ctx.lastTs) return { ok: false, reason: "replay" };
  let signer: string;
  try { signer = await recoverMessageAddress({ message, signature }); }
  catch { return { ok: false, reason: "bad_signature" }; }
  if (signer.toLowerCase() !== p.id.toLowerCase()) return { ok: false, reason: "signer_mismatch" };
  return { ok: true, payload: p };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/landing && npx vitest run lib/telemetry/__tests__/verify.test.ts`
Expected: PASS (7 tests — incl. python-style `5.0`/`0.0` acceptance + bad_json + schema).

- [ ] **Step 5: Commit**

```bash
git add apps/landing/lib/telemetry/verify.ts apps/landing/lib/telemetry/__tests__/verify.test.ts
git commit -m "feat(telemetry): EIP-191 sig + freshness + monotonic replay defense (spec25 G1)"
```

---

## Task 4: Supabase table + store

**Files:**
- Create: `apps/landing/supabase/migrations/0001_instances.sql`
- Create: `apps/landing/lib/telemetry/store.ts`
- Test: `apps/landing/lib/telemetry/__tests__/store.test.ts`

- [ ] **Step 1: Write the migration**

Create `apps/landing/supabase/migrations/0001_instances.sql`:
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
```

- [ ] **Step 2: Write the failing test (store with an injected client)**

```ts
import { describe, it, expect, vi } from "vitest";
import { getLastTs, upsertInstance } from "../store";

function fakeClient(row: any) {
  return {
    from: () => ({
      select: () => ({ eq: () => ({ maybeSingle: async () => ({ data: row }) }) }),
      upsert: async (v: any) => { row = v; return { error: null }; },
    }),
    _row: () => row,
  } as any;
}

describe("store", () => {
  it("getLastTs returns 0 when no row", async () => {
    expect(await getLastTs(fakeClient(null), "0xabc")).toBe(0);
  });
  it("getLastTs returns existing ts", async () => {
    expect(await getLastTs(fakeClient({ ts: 123 }), "0xabc")).toBe(123);
  });
  it("upsertInstance writes the row", async () => {
    const c = fakeClient(null);
    await upsertInstance(c, { id: "0xABC", ts: 5 } as any);
    expect(c._row().id).toBe("0xabc"); // lowercased
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd apps/landing && npx vitest run lib/telemetry/__tests__/store.test.ts`
Expected: FAIL — cannot find module `../store`.

- [ ] **Step 4: Write minimal implementation**

Create `apps/landing/lib/telemetry/store.ts`:
```ts
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type { TelemetryPayload } from "./schema";

export function telemetryClient(): SupabaseClient {
  return createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_KEY!);
}
export async function getLastTs(c: SupabaseClient, id: string): Promise<number> {
  const { data } = await c.from("instances").select("ts").eq("id", id.toLowerCase()).maybeSingle();
  return data?.ts ?? 0;
}
export async function upsertInstance(c: SupabaseClient, p: TelemetryPayload): Promise<void> {
  const { error } = await c.from("instances").upsert({ ...p, id: p.id.toLowerCase(), updated_at: new Date().toISOString() });
  if (error) throw new Error(error.message);
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd apps/landing && npx vitest run lib/telemetry/__tests__/store.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add apps/landing/supabase/migrations/0001_instances.sql apps/landing/lib/telemetry/store.ts apps/landing/lib/telemetry/__tests__/store.test.ts
git commit -m "feat(telemetry): instances table + Supabase store (lowercased id)"
```

---

## Task 5: POST /api/telemetry route

**Files:**
- Create: `apps/landing/app/api/telemetry/route.ts`
- Test: `apps/landing/app/api/telemetry/__tests__/route.test.ts`

- [ ] **Step 1: Write the failing test (inject store + now via module mock)**

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { privateKeyToAccount } from "viem/accounts";
import { canonicalMessage } from "@/lib/telemetry/verify";

const acct = privateKeyToAccount("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d");
let lastTs = 0; const upserted: any[] = [];
vi.mock("@/lib/telemetry/store", () => ({
  telemetryClient: () => ({}),
  getLastTs: async () => lastTs,
  upsertInstance: async (_c: any, p: any) => { upserted.push(p); lastTs = p.ts; },
}));
import { POST } from "../route";

// Body is { message: <verbatim signed string>, signature }. The route verifies the exact bytes.
function req(body: any) { return new Request("http://x/api/telemetry", { method: "POST", body: JSON.stringify(body) }); }
function objStr(over: Record<string, unknown> = {}) {
  const now = Math.floor(Date.now() / 1000);
  return canonicalMessage({ id: acct.address.toLowerCase(), ts: now, host: "akash", geo: "US", model_live: "x",
    model_tier: "free", net_worth_usd: 1, revenue_mo_usd: 0, burn_day_usd: 0.1, runway_days: 10, status: "alive", ...over } as any);
}

describe("POST /api/telemetry", () => {
  beforeEach(() => { lastTs = 0; upserted.length = 0; });
  it("202 on a valid signed fresh message", async () => {
    const message = objStr();
    const signature = await acct.signMessage({ message });
    const res = await POST(req({ message, signature }));
    expect(res.status).toBe(202); expect(upserted.length).toBe(1);
    expect(upserted[0].id).toBe(acct.address.toLowerCase());
  });
  it("401 on signer mismatch", async () => {
    const message = objStr({ id: "0x000000000000000000000000000000000000dead" });
    const signature = await acct.signMessage({ message }); // signed by acct, id claims dead addr
    const res = await POST(req({ message, signature }));
    expect(res.status).toBe(401);
  });
  it("400 on schema violation", async () => {
    const message = JSON.stringify({ id: "nope" });
    const signature = await acct.signMessage({ message });
    const res = await POST(req({ message, signature }));
    expect(res.status).toBe(400);
  });
  it("400 on missing message/signature", async () => {
    const res = await POST(req({ signature: "0x00" }));
    expect(res.status).toBe(400);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/landing && npx vitest run app/api/telemetry/__tests__/route.test.ts`
Expected: FAIL — cannot find module `../route`.

- [ ] **Step 3: Write minimal implementation**

Create `apps/landing/app/api/telemetry/route.ts`:
```ts
import { verifyTelemetry } from "@/lib/telemetry/verify";
import { telemetryClient, getLastTs, upsertInstance } from "@/lib/telemetry/store";

// 400-class reasons (caller error) vs 401-class (auth/replay). Keeps the signing-bytes contract
// (verify reads the verbatim message) — the route NEVER re-serializes the payload.
const BAD_REQUEST = new Set(["bad_json", "schema"]);

export async function POST(req: Request) {
  let body: any;
  try { body = await req.json(); } catch { return Response.json({ error: "bad_json" }, { status: 400 }); }
  const message = body?.message; const signature = body?.signature as `0x${string}`;
  if (typeof message !== "string" || typeof signature !== "string") {
    return Response.json({ error: "bad_request" }, { status: 400 });
  }
  // extract id (for the per-id monotonic lookup) without trusting it — verify binds it to the bytes
  let id: unknown;
  try { id = JSON.parse(message)?.id; } catch { return Response.json({ error: "bad_json" }, { status: 400 }); }
  if (typeof id !== "string") return Response.json({ error: "schema" }, { status: 400 });
  const c = telemetryClient();
  const lastTs = await getLastTs(c, id);
  const now = Math.floor(Date.now() / 1000);
  const v = await verifyTelemetry(message, signature, { now, lastTs });
  if (!v.ok) return Response.json({ error: v.reason }, { status: BAD_REQUEST.has(v.reason) ? 400 : 401 });
  await upsertInstance(c, v.payload);
  return Response.json({ ok: true }, { status: 202 });
}
```

(`@/` alias is guaranteed by Task 1's `vite-tsconfig-paths` plugin + `tsconfig.json` `paths` `@/*` → `./*`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/landing && npx vitest run app/api/telemetry/__tests__/route.test.ts`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/landing/app/api/telemetry
git commit -m "feat(telemetry): POST /api/telemetry (schema+sig+freshness+monotonic -> upsert)"
```

---

## Task 6: dashboard-sync route (instances -> dashboard.json shape)

**Files:**
- Create: `apps/landing/app/api/dashboard-sync/route.ts`
- Test: `apps/landing/app/api/dashboard-sync/__tests__/route.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { aggregate } from "../aggregate";

describe("aggregate", () => {
  const rows = [
    // self-funded: revenue/30 (0.33) >= burn (0.10), alive
    { id: "0x1", net_worth_usd: 100, revenue_mo_usd: 10, burn_day_usd: 0.1, runway_days: 30, status: "alive", host: "akash", model_tier: "frontier" },
    // NOT self-funded: revenue/30 (0.16) < burn (0.50), critical
    { id: "0x2", net_worth_usd: 50, revenue_mo_usd: 5, burn_day_usd: 0.5, runway_days: 2, status: "critical", host: "do", model_tier: "free" },
  ] as any;
  it("computes totals + leaderboard", () => {
    const d = aggregate(rows);
    expect(d.total_net_worth_usd).toBe(150);
    expect(d.alive).toBe(2);
    expect(d.leaderboard[0].id).toBe("0x1"); // net worth desc
  });
  it("self_funded_pct = % whose monthly revenue covers daily burn AND not dead (NOT a model proxy)", () => {
    expect(aggregate(rows).self_funded_pct).toBe(50); // only 0x1 covers its burn
  });
  it("frontier_pct is reported separately (it is NOT self-funding)", () => {
    expect(aggregate(rows).frontier_pct).toBe(50);
  });
  it("handles empty rows without div-by-zero", () => {
    const d = aggregate([]);
    expect(d.self_funded_pct).toBe(0); expect(d.frontier_pct).toBe(0); expect(d.alive).toBe(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/landing && npx vitest run app/api/dashboard-sync/__tests__/route.test.ts`
Expected: FAIL — cannot find module `../aggregate`.

- [ ] **Step 3: Write minimal implementation**

Create `apps/landing/app/api/dashboard-sync/aggregate.ts`:
```ts
export type Row = { id: string; net_worth_usd: number; revenue_mo_usd: number; burn_day_usd: number; runway_days: number; status: string; host: string; model_tier: string };
export function aggregate(rows: Row[]) {
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
```

Create `apps/landing/app/api/dashboard-sync/route.ts`:
```ts
import { telemetryClient } from "@/lib/telemetry/store";
import { aggregate } from "./aggregate";
export async function GET() {
  const c = telemetryClient();
  const { data } = await c.from("instances").select("*");
  return Response.json(aggregate((data ?? []) as any));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/landing && npx vitest run app/api/dashboard-sync/__tests__/route.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/landing/app/api/dashboard-sync
git commit -m "feat(telemetry): dashboard-sync aggregate (totals + leaderboard, real data only)"
```

---

## Task 7: Whole-number-float regression test (the prod-only 401 bug → RED test, review-fix #5)

**Files:**
- Test: `apps/landing/lib/telemetry/__tests__/golden.test.ts`

**Why this exists (review round 3, verified empirically):** a previous design re-serialized the parsed payload to recover the signer. But `JSON.stringify(5.0)==="5"` while python `json.dumps(5.0)==="5.0"` (and `1e-05` vs `0.00001`) — so the instant the genesis wallet held a whole-dollar balance or `REV=0.0`, python signed `...,"net_worth_usd":5.0,...` and the route re-stringified `...,"net_worth_usd":5,...` → different bytes → `recoverMessageAddress` returned a different signer → **401 on every whole-number balance**, passing all unit/smoke tests and failing only in production. Fix: verify the **verbatim** message bytes (Task 3). This test pins that the verbatim path accepts python's `5.0`/`0.0` output — turning the actual bug into a RED-then-GREEN regression.

- [ ] **Step 1: Write the regression test (the exact failure mode, verbatim-verified)**

```ts
import { describe, it, expect } from "vitest";
import { privateKeyToAccount } from "viem/accounts";
import { verifyTelemetry } from "../verify";

const acct = privateKeyToAccount("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d");

describe("whole-number float regression (prod-only 401 bug)", () => {
  it("verbatim verify accepts a python-style message with 5.0 / 0.0", async () => {
    const now = Math.floor(Date.now() / 1000);
    // EXACTLY what python json.dumps(...,separators=(',',':')) emits for whole-dollar balances:
    const msg = `{"id":"${acct.address.toLowerCase()}","ts":${now},"host":"akash","geo":"US","model_live":"auto","model_tier":"free","net_worth_usd":5.0,"revenue_mo_usd":0.0,"burn_day_usd":0,"runway_days":999,"status":"alive"}`;
    const sig = await acct.signMessage({ message: msg });
    const r = await verifyTelemetry(msg, sig, { now, lastTs: 0 });
    expect(r.ok).toBe(true);
  });
  it("PROOF the old design was broken: re-stringifying drops the .0 (would 401)", () => {
    // documents WHY we verify verbatim: parse→stringify is lossy for whole-number floats
    expect(JSON.stringify(JSON.parse('{"net_worth_usd":5.0,"revenue_mo_usd":0.0}')))
      .toBe('{"net_worth_usd":5,"revenue_mo_usd":0}'); // 5.0→5, 0.0→0 → different signed bytes
  });
});
```

- [ ] **Step 2: Run → PASS (verbatim verify is byte-faithful; the proof case documents the avoided bug)**

Run: `cd apps/landing && npx vitest run lib/telemetry/__tests__/golden.test.ts`
Expected: PASS (2 tests).

- [ ] **Step 3: Confirm python actually emits the trailing `.0` (run once — this is the real-world input)**

Run:
```bash
python3 -c "import json;print(json.dumps({'net_worth_usd':round(5.0,4),'revenue_mo_usd':round(0.0,4)},separators=(',',':')))"
```
Expected: prints `{"net_worth_usd":5.0,"revenue_mo_usd":0.0}` — proving the client really sends `5.0`/`0.0`, which the verbatim route accepts and a re-stringifying route would have rejected.

- [ ] **Step 4: Commit**

```bash
git add apps/landing/lib/telemetry/__tests__/golden.test.ts
git commit -m "test(telemetry): whole-number-float regression (verbatim verify accepts python 5.0/0.0)"
```

---

## Task 8: Automaton report hook POSTs signed telemetry (review-fix #2,#3)

**Files:**
- Create: `~/anicca/skills/report/anicca-report.sh` (canonical — does NOT exist yet; this is a CREATE)
- Mirror: deployed `/opt/anicca-report.sh` on droplet 147.182.225.255

- [ ] **Step 1: Confirm the wallet env var name actually on the box (don't assume)**

Run:
```bash
ssh root@147.182.225.255 'grep -oiE "^[A-Z_]*WALLET[A-Z_]*=" /opt/anicca.env'
```
Expected: prints the real var (e.g. `BLOCKRUN_WALLET_KEY=`). Use that exact name below as `$PKVAR`.

- [ ] **Step 2: Create the canonical report+telemetry script**

Create `~/anicca/skills/report/anicca-report.sh` (and scp to `/opt/anicca-report.sh`). `$W/$ETH/$USDC/$REV` are computed here (self-contained — does not rely on prior session's script). **Set `PKVAR` to the exact var name Step 1 printed** (default `BLOCKRUN_WALLET_KEY`); the heredoc reads it indirectly so no second edit is needed:
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
# burn_day_usd/runway_days/status are PLACEHOLDERS until the earn/burn meter lands (spec25 R4) — the
# route stores them as-is; /dashboard must label the runway/self-funded columns as estimated until then.
TS=$(date -u +%s)
MSG=$(python3 -c "import json;print(json.dumps({'id':'$(echo $W|tr A-F a-f)','ts':$TS,'host':'akash','geo':'US','model_live':'auto','model_tier':'free','net_worth_usd':$USDC,'revenue_mo_usd':$REV,'burn_day_usd':0,'runway_days':999,'status':'alive'},separators=(',',':')))")
SIG=$(MSG="$MSG" SIGNKEY="$SIGNKEY" python3 - <<'PY'
import os
from eth_account import Account; from eth_account.messages import encode_defunct
s = Account.sign_message(encode_defunct(text=os.environ["MSG"]), private_key=os.environ["SIGNKEY"]).signature.hex()
print(s if s.startswith("0x") else "0x"+s)        # viem recoverMessageAddress requires 0x prefix
PY
)
BODY=$(MSG="$MSG" SIG="$SIG" python3 -c "import json,os;print(json.dumps({'message':os.environ['MSG'],'signature':os.environ['SIG']}))")
curl -s --max-time 15 -X POST "https://aniccaai.com/api/telemetry" -H "Content-Type: application/json" \
  -d "$BODY" >/dev/null 2>&1
echo "report+telemetry $TS" >> /var/log/anicca-report.log
```
(The signed `MSG` is sent VERBATIM as the `message` field — the route recovers the signer from these exact bytes, so python's `5.0`/`0.0` whole-number output is accepted, not 401'd. The `id` is lowercased to match the route's `id.toLowerCase()`.)

- [ ] **Step 3: Commit canonical + scp to droplet**

```bash
cd ~/anicca && git add skills/report/anicca-report.sh && git commit -m "feat(report): per-wake email + signed telemetry POST" && git push
scp ~/anicca/skills/report/anicca-report.sh root@147.182.225.255:/opt/anicca-report.sh
ssh root@147.182.225.255 'chmod +x /opt/anicca-report.sh; pip install eth_account -q'
```

---

## Task 9: Deploy + smoke + real E2E (review-fix #4)

**Pre-req (ops, Dais infra — C1 carve-out):** Supabase project created; `SUPABASE_URL`+`SUPABASE_SERVICE_KEY` set in Netlify env; `instances` migration applied. Confirm before proceeding.

- [ ] **Step 1: Deploy the routes (push triggers Netlify)**

```bash
cd ~/anicca-project && git push   # netlify-deploy on apps/landing/** → aniccaai.com
```
Wait for the Netlify build to go green.

- [ ] **Step 2: SMOKE — locally-signed test payload → 202**

Run (signs with the test key, uses a WHOLE-DOLLAR balance `5.0` to actually exercise the prod bug class, hits the live route):
```bash
python3 - <<'PY'
import json,time,urllib.request
from eth_account import Account; from eth_account.messages import encode_defunct
acct=Account.from_key("0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d")
# round(5.0,4)=5.0 → json.dumps emits "5.0": the exact whole-number case that a re-stringifying route would 401
p={'id':acct.address.lower(),'ts':int(time.time()),'host':'test','geo':'US','model_live':'x','model_tier':'free','net_worth_usd':round(5.0,4),'revenue_mo_usd':round(0.0,4),'burn_day_usd':0,'runway_days':10,'status':'alive'}
msg=json.dumps(p,separators=(',',':'))           # this exact string is signed AND sent verbatim
s=Account.sign_message(encode_defunct(text=msg),private_key=acct.key).signature.hex()
sig=s if s.startswith("0x") else "0x"+s
body=json.dumps({'message':msg,'signature':sig}).encode()
req=urllib.request.Request("https://aniccaai.com/api/telemetry",data=body,headers={'Content-Type':'application/json'})
print("status", urllib.request.urlopen(req).status)
PY
```
Expected: `status 202` — and because it posts a whole-dollar `5.0`, a 202 here proves the verbatim-bytes contract works end-to-end (the bug round 3 found cannot recur). (If 401 → signing path mismatch. If 500 → Supabase env not set.)

- [ ] **Step 3: REAL E2E — genesis instance posts → dashboard reflects real net worth**

```bash
ssh root@147.182.225.255 'bash /opt/anicca-report.sh'
sleep 3
curl -s "https://aniccaai.com/api/dashboard-sync" | python3 -c "import json,sys;d=json.load(sys.stdin);ids=[r['id'] for r in d['leaderboard']];print('genesis present:', '0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21' in ids, 'total_net:', d['total_net_worth_usd'])"
```
Expected: `genesis present: True`, `total_net` = the genesis wallet's REAL on-chain USDC. **This is the genuine E2E: a live instance signed+POSTed → Supabase → dashboard-sync reflects real chain data. No mock.**

- [ ] **Step 4: Commit evidence note**

```bash
echo "E2E PASS $(date -u +%FT%TZ): genesis telemetry → dashboard-sync, net=<paste>" >> docs/superpowers/plans/2026-06-15-anicca-telemetry-pipeline.md
git add -A && git commit -m "test(telemetry): E2E PASS — live instance signed POST → dashboard reflects real net worth" && git push
```

---

## Self-Review
- **Spec coverage:** §2 telemetry (23) + G1 (25: Supabase, EIP-191, ts freshness, monotonic) + "透明公開" success criterion → Tasks 2–6. ✅ Replay/nonce (note1) = Task 3 stale/replay tests. ✅
- **Placeholders:** none — every step has runnable code/commands + expected output. `burn_day_usd/runway_days/status` in Task 8 are explicitly labeled estimates until the earn/burn meter lands (spec25 R4).
- **Type consistency:** `TelemetryPayload` (schema.ts) used across verify/store/route. `verifyTelemetry(message, signature, ctx)` takes the verbatim string and returns `{ok, payload}`; route stores `v.payload` (never re-serializes).
- **Signing-bytes contract (review round 3):** the route verifies the VERBATIM signed message, not a re-stringified object → no cross-language number-format divergence (`5`/`5.0`, `1e-05`/`0.00001`). Pinned by Task 3's whole-number test + Task 7 regression.
- **Gaps:** Supabase project + env (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`) provisioning is an ops prerequisite (Dais infra, C1 carve-out) — Task 9 pre-req, not code.
- **E2E:** Task 9 Step 3 = real genesis instance → signed POST → dashboard-sync reflects real on-chain net worth. Not a mock. Task 9 Step 2 smoke uses a whole-dollar `5.0` to prove the bug class is closed.

## Pre-req (ops, Dais infra)
Create a Supabase project; set `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` in the landing app env (Netlify) and `aniccaai.com` reachable. (C1 carve-out: this is Dais-owned funnel/infra.)
