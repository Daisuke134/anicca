# P-auto-cancel — instance self-cancels its subscription when it earns enough → runs FREE (no destroy)

> Spec: `28-product-redesign-merge-2026-06-16.md` §1. Task #5. Target repo: `Daisuke134/anicca-products`, `apps/landing`
> (products-repo diffs) + a cross-repo contract for the OSS/runtime instance side.
> **Claim implemented:** "お金が貯まると自動的にサブスク解約され無料で利用可能に." The cloud Anicca, once its OWN
> wallet holds ≥ threshold USDC, cancels its Stripe subscription and KEEPS RUNNING on its own earnings.
> **Zero-uncertainty:** Stripe cancel verified via context7 `/stripe/stripe-node` — `stripe.subscriptions.cancel(sub_id)`
> (`.del()` removed in v13; installed `stripe@^22.2.0`, `apps/landing/package.json:27`). No new deps (Node `crypto`).
> **Rev2 (review-driven):** per-instance auth token (not a shared secret), secret delivered by SCP (not cloud-init
> user_data), idempotent cancel, and a guard test that an `active` owner still destroys.

---

## §1 Reality found (cited file:line, live tree) — incl. the design trap

| fact | evidence | consequence |
|---|---|---|
| **webhook DESTROYS the droplet on `customer.subscription.deleted`** | `stripe-spawn-webhook.js:75-87` → `_destroy(owner.droplet_id, doCfg)` L82 | naive auto-cancel would KILL the instance. MUST guard. |
| owners row = `{sub_id,email,droplet_id,status}`; `getOwnerBySub` selects `status` | `owners-store.js:37` `select=sub_id,email,droplet_id,status`; `markDestroyed:45-52` uses `headers:{...headers(key),Prefer:"return=minimal"}` | guard can read `owner.status`; new writer must match the Prefer convention |
| per-instance balance lives in telemetry `instances` (by wallet), NOT joined to owners | `dashboard-sync.js:6`; owners has no wallet id | don't join server-side — the INSTANCE decides |
| the instance is told its own `sub_id` (non-secret) | `spawn-droplet.js:18,25` → `cloud-init.js:17,23-25` writes `/opt/anicca-owner.json {owner_email,sub_id}` | instance knows its subscription |
| **cloud-init forbids secret VALUES in user_data** (readable from DO metadata); secrets are SCP'd to `/opt/anicca.env` after boot | `cloud-init.js:13-15` (verbatim security invariant) | the cancel token MUST be SCP-delivered, NOT written by `buildUserData` |
| instance owns its wallet + balance | OSS `skills/earn/run.sh` (`PKVAR`/`BLOCKRUN_WALLET_KEY`) + telemetry net_worth | the instance is the only actor that authoritatively knows "balance ≥ threshold" |

**Design conclusion:** the instance (knowing its wallet balance + sub_id) calls an authenticated `self-cancel`; the function cancels the Stripe sub and marks the owner `self_funded`; the destroy-on-deleted webhook is GUARDED so a `self_funded` cancellation keeps the droplet. Auth uses a **per-instance** token so a leaked token can only cancel its own subscription.

## §2 Diffs (products repo)

### Diff 1 — `_lib/owners-store.js`: add `markSelfFunded` (matches `markDestroyed` Prefer convention) + export

```diff
diff --git a/apps/landing/netlify/functions/_lib/owners-store.js b/apps/landing/netlify/functions/_lib/owners-store.js
--- a/apps/landing/netlify/functions/_lib/owners-store.js
+++ b/apps/landing/netlify/functions/_lib/owners-store.js
@@
 async function markDestroyed(sub_id, { url, key, f = fetch }) {
   const r = await f(`${url}/rest/v1/owners?sub_id=eq.${encodeURIComponent(sub_id)}`, {
     method: "PATCH",
     headers: { ...headers(key), Prefer: "return=minimal" },
     body: JSON.stringify({ status: "destroyed", updated_at: new Date().toISOString() }),
   });
   if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
 }
+
+// Mark an owner self-funded: its instance earns enough, the subscription is cancelled, but the
+// droplet KEEPS RUNNING (the destroy-on-deleted webhook checks this status and skips destroy).
+async function markSelfFunded(sub_id, { url, key, f = fetch }) {
+  const r = await f(`${url}/rest/v1/owners?sub_id=eq.${encodeURIComponent(sub_id)}`, {
+    method: "PATCH",
+    headers: { ...headers(key), Prefer: "return=minimal" },
+    body: JSON.stringify({ status: "self_funded", updated_at: new Date().toISOString() }),
+  });
+  if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
+}
@@
-module.exports = { isEventSeen, markEventSeen, upsertOwner, getOwnerBySub, markDestroyed };
+module.exports = { isEventSeen, markEventSeen, upsertOwner, getOwnerBySub, markDestroyed, markSelfFunded };
```

### Diff 2 — `stripe-spawn-webhook.js`: GUARD — self_funded owners keep their droplet

```diff
diff --git a/apps/landing/netlify/functions/stripe-spawn-webhook.js b/apps/landing/netlify/functions/stripe-spawn-webhook.js
--- a/apps/landing/netlify/functions/stripe-spawn-webhook.js
+++ b/apps/landing/netlify/functions/stripe-spawn-webhook.js
@@ customer.subscription.deleted branch — between the no-owner guard and `_destroy`
       const owner = sub_id ? await _owners.getOwnerBySub(sub_id, cfg) : null;
       if (!owner || !owner.droplet_id) {
         await _owners.markEventSeen(stripeEvent.id, cfg);
         return { statusCode: 200, body: "no owner" };
       }
+      // Self-funded: the instance cancelled its OWN subscription because it earns enough.
+      // Keep the droplet alive — do NOT destroy. (P-auto-cancel guard.) An owner whose status is
+      // still "active" (e.g. a dashboard cancel) falls through to _destroy as before.
+      if (owner.status === "self_funded") {
+        await _owners.markEventSeen(stripeEvent.id, cfg);
+        console.log(`💚 self-funded sub ${sub_id} cancelled — droplet ${owner.droplet_id} kept alive`);
+        return { statusCode: 200, body: JSON.stringify({ ok: true, kept: owner.droplet_id }) };
+      }
       await _destroy(owner.droplet_id, doCfg);
```

### Diff 3 — NEW `netlify/functions/self-cancel.js`: PER-INSTANCE-token auth + idempotent cancel

```diff
diff --git a/apps/landing/netlify/functions/self-cancel.js b/apps/landing/netlify/functions/self-cancel.js
new file mode 100644
--- /dev/null
+++ b/apps/landing/netlify/functions/self-cancel.js
@@
+// Cloud Anicca self-cancels its subscription once its OWN wallet ≥ AUTO_CANCEL_USDC.
+// POST { sub_id, token } where token = base64url(HMAC-SHA256(SELF_CANCEL_MASTER_SECRET, sub_id)).
+// The token is PER-INSTANCE: it is derived from THIS sub_id and SCP'd into the instance's
+// /opt/anicca.env at spawn (the MASTER secret never leaves the server). A leaked token can only
+// cancel its OWN sub_id (the HMAC is bound to sub_id), so the blast radius is one instance.
+// Cancels the Stripe sub + marks the owner self_funded so the deleted-webhook keeps the droplet.
+const crypto = require("crypto");
+const stripe = require("stripe");
+const owners = require("./_lib/owners-store");
+
+function expectedToken(sub_id, master) {
+  return crypto.createHmac("sha256", master).update(String(sub_id)).digest("base64url");
+}
+
+exports.handler = async (event, deps = {}) => {
+  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };
+  const MASTER = process.env.SELF_CANCEL_MASTER_SECRET;
+  const STRIPE_SECRET = process.env.STRIPE_SECRET_KEY;
+  const SUPA_URL = process.env.SUPABASE_URL, SUPA_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
+  if (!MASTER || !STRIPE_SECRET || !SUPA_URL || !SUPA_KEY) return { statusCode: 500, body: "missing env" };
+  let body; try { body = JSON.parse(event.body || "{}"); } catch { return { statusCode: 400, body: "bad json" }; }
+  const { sub_id, token } = body;
+  if (!sub_id || !token) return { statusCode: 400, body: "missing sub_id/token" };
+  const exp = expectedToken(sub_id, MASTER);
+  const a = Buffer.from(String(token)), b = Buffer.from(exp);
+  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return { statusCode: 403, body: "bad token" };
+  const _owners = deps.owners || owners;
+  const stripeClient = deps.stripeClient || stripe(STRIPE_SECRET);
+  const cfg = { url: SUPA_URL, key: SUPA_KEY };
+  try {
+    // mark FIRST so a racing customer.subscription.deleted sees self_funded and keeps the droplet.
+    await _owners.markSelfFunded(sub_id, cfg);
+    try {
+      await stripeClient.subscriptions.cancel(sub_id); // ctx7 /stripe/stripe-node: v13+ .cancel (was .del)
+    } catch (e) {
+      // idempotent: an already-cancelled / missing sub is success (the instance may retry).
+      const code = e && (e.code || (e.raw && e.raw.code));
+      if (code === "resource_missing" || /cancel/i.test((e && e.message) || "")) {
+        return { statusCode: 200, body: JSON.stringify({ ok: true, already: sub_id }) };
+      }
+      throw e; // real failure → 500 → the instance retries (markSelfFunded already idempotently set)
+    }
+    return { statusCode: 200, body: JSON.stringify({ ok: true, self_funded: sub_id }) };
+  } catch (err) {
+    console.error("self-cancel error:", err);
+    return { statusCode: 500, body: `self-cancel error: ${err.message}` };
+  }
+};
```

### Diff 4 — provisioning (Q6 step 5 SCP), NOT cloud-init user_data: deliver the per-instance token
> **Do NOT** add the token to `buildUserData` (cloud-init.js:13-15 forbids secret values in user_data — DO metadata
> is readable). Instead the spawn provisioning that already SCPs `/opt/anicca.env` (Q6 step 5) appends:
> `SELF_CANCEL_TOKEN=<base64url(HMAC(SELF_CANCEL_MASTER_SECRET, sub_id))>`, `SUB_ID=<sub_id>`,
> `ANICCA_API_BASE=https://aniccaai.com`, `AUTO_CANCEL_USDC=50`. The token is computed server-side at spawn
> (where MASTER lives) and is unique per sub_id. `cloud-init.js` is unchanged (it only writes the non-secret
> `/opt/anicca-owner.json`). The exact provisioning file is `docs/superpowers/specs/anicca/commands/Q6.command.sh`
> (the SCP step) — its env-append line is the single edit; confirmed at apply by reading that step.

## §3 Instance-side contract (OSS/runtime — `~/anicca` report loop)
When the report loop computes `net_worth_usd` and `net_worth_usd >= AUTO_CANCEL_USDC` (default 50) AND `SUB_ID` is set
(cloud only; OSS-local has no SUB_ID → no-op), POST to `${ANICCA_API_BASE}/.netlify/functions/self-cancel` with
`{ sub_id: SUB_ID, token: SELF_CANCEL_TOKEN }` (the token is read verbatim from `/opt/anicca.env`; the instance does
NOT compute it). **Retry until 200** (not "once") — both `markSelfFunded` and `cancel` are idempotent, so a 500 from a
transient Stripe error is safely retried on the next wake; an already-cancelled sub returns 200. Encoding is pinned:
the token is **base64url** of the HMAC (must match `expectedToken`). Once 200, stop (the loop checks `status` to avoid
re-POSTing). Rationale for mark-first: losing the droplet (destroy-race) is worse than one extra billing cycle; the
bounded retry closes the billing-leak window.

## §4 Run commands
```bash
cd apps/landing
node --test 'netlify/functions/__tests__/self-cancel.test.js' 'netlify/functions/_lib/__tests__/owners-store.test.js'
# env: SELF_CANCEL_MASTER_SECRET (server only), AUTO_CANCEL_USDC
# Stripe TEST-mode round-trip (no real money) — see §5.
```

## §5 Acceptance (HARD 0.24/0.31)
1. node:test green:
   - bad/blank token → 403; valid per-sub token → `markSelfFunded` + `stripe.subscriptions.cancel` called (fakes).
   - already-cancelled Stripe error (fake throws `resource_missing`) → 200 idempotent (not 500).
   - **guard test (reviewer B5):** `customer.subscription.deleted` with `owner.status==='active'` → `_destroy` IS called (guard does NOT over-trigger); with `'self_funded'` → `_destroy` NOT called, returns `kept`.
2. Stripe **test-mode** real round-trip: a real test subscription is cancelled via self-cancel with its per-sub token;
   `owners.status` becomes `self_funded`; a `customer.subscription.deleted` event returns `kept` (droplet NOT destroyed).
   Evidence = Stripe dashboard test sub status + Supabase owners row + webhook log. No real money moved.

## §6 Boundaries
Products repo: `_lib/owners-store.js` (+`markSelfFunded`), `stripe-spawn-webhook.js` (guard), NEW `self-cancel.js` (+test).
`cloud-init.js` UNCHANGED (no secret in user_data). The per-instance token is delivered by the existing SCP
provisioning step (Q6), and the balance check is the OSS report skill (§3 contract). No new deps (Node `crypto` +
existing `stripe@^22`). owners gains the `self_funded` status value (free-text column, no DDL). MASTER secret is
server-only and never injected into any instance.
