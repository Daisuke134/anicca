# P-auto-cancel — instance self-cancels its subscription when it earns enough → runs FREE (no destroy)

> Spec: `28-product-redesign-merge-2026-06-16.md` §1. Task #5. Target repo: `Daisuke134/anicca-products`, `apps/landing`
> (products-repo diffs) + a cross-repo contract for the OSS/runtime instance side.
> **Claim implemented:** "お金が貯まると自動的にサブスク解約され無料で利用可能に." The cloud Anicca, once its OWN
> wallet holds ≥ threshold USDC, cancels its Stripe subscription and KEEPS RUNNING on its own earnings.
> **Zero-uncertainty:** Stripe cancel verified via context7 `/stripe/stripe-node` — `stripe.subscriptions.cancel(sub_id)`
> (the `.del()` method was removed in v13.0.0; `.cancel()` is the replacement, same effect). No new deps.

---

## §1 Reality found (cited file:line, live tree) — incl. the design trap

| fact | evidence | consequence |
|---|---|---|
| **webhook DESTROYS the droplet on `customer.subscription.deleted`** | `stripe-spawn-webhook.js:75-87` → `_destroy(owner.droplet_id, doCfg)` | naive auto-cancel would KILL the instance — the opposite of "runs free". MUST guard. |
| owners row = `{sub_id,email,droplet_id,status}`, status today ∈ active/destroyed | `_lib/owners-store.js:27-54` (`upsertOwner`, `getOwnerBySub` selects `status`, `markDestroyed`) | extend status with `self_funded` + add `markSelfFunded` |
| per-instance balance lives in the **telemetry `instances`** table (by wallet id), NOT joined to owners | `dashboard-sync.js:6` reads `instances`; owners has no wallet/instance id | owner→balance join is NOT wired → don't try to join server-side |
| the instance ALREADY can be told its own `sub_id` | `spawn-droplet.js:18,25` `createDroplet({owner_email,sub_id})` → `buildUserData({owner_email,sub_id})` | the instance knows its subscription → it can self-cancel; no join needed |
| the instance owns its wallet + balance | OSS `runtime/compute-proxy/proxy.mjs` wallet + telemetry net_worth report | the instance is the ONLY actor that authoritatively knows "balance ≥ threshold" |

**Design conclusion:** the cancel decision belongs to **the instance** (it alone knows its wallet balance and its sub_id), not a server-side balance join. The instance, when its wallet ≥ `AUTO_CANCEL_USDC`, calls a new authenticated `self-cancel` function; the function cancels the Stripe sub and marks the owner `self_funded`; the existing destroy-on-deleted webhook is GUARDED so a `self_funded` cancellation keeps the droplet alive.

## §2 Diffs (products repo)

### Diff 1 — `_lib/owners-store.js`: add `markSelfFunded` + export

```diff
diff --git a/apps/landing/netlify/functions/_lib/owners-store.js b/apps/landing/netlify/functions/_lib/owners-store.js
--- a/apps/landing/netlify/functions/_lib/owners-store.js
+++ b/apps/landing/netlify/functions/_lib/owners-store.js
@@
 async function markDestroyed(sub_id, { url, key, f = fetch }) {
   const r = await f(`${url}/rest/v1/owners?sub_id=eq.${encodeURIComponent(sub_id)}`, {
     method: "PATCH", headers: headers(key),
     body: JSON.stringify({ status: "destroyed", updated_at: new Date().toISOString() }),
   });
   if (!r.ok) throw new Error(`supabase ${r.status} ${await r.text()}`);
 }
+
+// Mark an owner self-funded: its instance earns enough, the subscription is cancelled, but the
+// droplet KEEPS RUNNING (the destroy-on-deleted webhook checks this status and skips destroy).
+async function markSelfFunded(sub_id, { url, key, f = fetch }) {
+  const r = await f(`${url}/rest/v1/owners?sub_id=eq.${encodeURIComponent(sub_id)}`, {
+    method: "PATCH", headers: headers(key),
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
@@ customer.subscription.deleted branch
       const owner = sub_id ? await _owners.getOwnerBySub(sub_id, cfg) : null;
       if (!owner || !owner.droplet_id) {
         await _owners.markEventSeen(stripeEvent.id, cfg);
         return { statusCode: 200, body: "no owner" };
       }
+      // Self-funded: the instance cancelled its OWN subscription because it earns enough.
+      // Keep the droplet alive — do NOT destroy. (P-auto-cancel guard.)
+      if (owner.status === "self_funded") {
+        await _owners.markEventSeen(stripeEvent.id, cfg);
+        console.log(`💚 self-funded sub ${sub_id} cancelled — droplet ${owner.droplet_id} kept alive`);
+        return { statusCode: 200, body: JSON.stringify({ ok: true, kept: owner.droplet_id }) };
+      }
       await _destroy(owner.droplet_id, doCfg);
```

### Diff 3 — NEW `netlify/functions/self-cancel.js`: instance-authenticated cancel

```diff
diff --git a/apps/landing/netlify/functions/self-cancel.js b/apps/landing/netlify/functions/self-cancel.js
new file mode 100644
--- /dev/null
+++ b/apps/landing/netlify/functions/self-cancel.js
@@
+// Cloud Anicca self-cancels its subscription once its OWN wallet ≥ AUTO_CANCEL_USDC.
+// POST { sub_id, sig } where sig = HMAC-SHA256(SELF_CANCEL_SECRET, sub_id) (the secret is injected
+// into the instance via cloud-init, so only a real instance can call this for its own sub_id).
+// Cancels the Stripe sub + marks the owner self_funded so the deleted-webhook keeps the droplet.
+const crypto = require("crypto");
+const stripe = require("stripe");
+const owners = require("./_lib/owners-store");
+
+exports.handler = async (event, deps = {}) => {
+  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };
+  const SECRET = process.env.SELF_CANCEL_SECRET;
+  const STRIPE_SECRET = process.env.STRIPE_SECRET_KEY;
+  const SUPA_URL = process.env.SUPABASE_URL, SUPA_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
+  if (!SECRET || !STRIPE_SECRET || !SUPA_URL || !SUPA_KEY) return { statusCode: 500, body: "missing env" };
+  let body; try { body = JSON.parse(event.body || "{}"); } catch { return { statusCode: 400, body: "bad json" }; }
+  const { sub_id, sig } = body;
+  if (!sub_id || !sig) return { statusCode: 400, body: "missing sub_id/sig" };
+  const expected = crypto.createHmac("sha256", SECRET).update(String(sub_id)).digest("base64url");
+  const a = Buffer.from(String(sig)), b = Buffer.from(expected);
+  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return { statusCode: 403, body: "bad sig" };
+  const _owners = deps.owners || owners;
+  const stripeClient = deps.stripeClient || stripe(STRIPE_SECRET);
+  const cfg = { url: SUPA_URL, key: SUPA_KEY };
+  try {
+    await _owners.markSelfFunded(sub_id, cfg);          // mark FIRST so the deleted-webhook guard sees it
+    await stripeClient.subscriptions.cancel(sub_id);    // ctx7 /stripe/stripe-node: .cancel (was .del pre-v13)
+    return { statusCode: 200, body: JSON.stringify({ ok: true, self_funded: sub_id }) };
+  } catch (err) {
+    console.error("self-cancel error:", err);
+    return { statusCode: 500, body: `self-cancel error: ${err.message}` };
+  }
+};
```

### Diff 4 — `_lib/cloud-init.js`: inject `SELF_CANCEL_SECRET` + `sub_id` into the instance env

> `buildUserData({owner_email, sub_id})` already receives `sub_id` (`spawn-droplet.js:25`). Add the env writes so
> the instance can authenticate the self-cancel. Exact lines confirmed at apply with `grep -n "sub_id\|env\|cat >" apps/landing/netlify/functions/_lib/cloud-init.js`; the addition writes `SUB_ID=<sub_id>` and `SELF_CANCEL_SECRET=<process.env.SELF_CANCEL_SECRET>` + `ANICCA_API_BASE=https://aniccaai.com` into the droplet's `/opt/anicca.env`.

## §3 Instance-side contract (OSS/runtime — `~/anicca` report loop, separate patch slot)
When the instance's report loop computes `net_worth_usd` (already reported to telemetry), if `net_worth_usd >= AUTO_CANCEL_USDC` (default 50) and it has a `SUB_ID` (cloud only; OSS-local has none → no-op), POST once to `${ANICCA_API_BASE}/.netlify/functions/self-cancel` with `{ sub_id: SUB_ID, sig: HMAC(SELF_CANCEL_SECRET, SUB_ID) }`. Idempotent: a `self_funded` owner's second call still 200s (Stripe cancel of an already-cancelled sub is tolerated/caught). This is wired in the OSS report skill and verified there; this patch ships the products-repo endpoint + guard it calls.

## §4 Run commands
```bash
cd apps/landing
node --test 'netlify/functions/_lib/__tests__/owners-store.test.js'   # + a self-cancel.test.js (sig 403, happy path with fake stripe+owners)
# env: SELF_CANCEL_SECRET (shared with cloud-init), AUTO_CANCEL_USDC
# Stripe TEST-mode round-trip (no real money):
#  create a test sub -> POST self-cancel with a valid sig -> assert sub cancelled + owners.status=self_funded
#  -> fire a customer.subscription.deleted test webhook -> assert droplet NOT destroyed (guard hit)
```

## §5 Acceptance (HARD 0.24/0.31)
1. node:test green: bad sig → 403; valid sig → markSelfFunded called + stripe.subscriptions.cancel called (fakes).
2. Stripe **test-mode** real round-trip: a real test subscription is cancelled via self-cancel; `owners.status` becomes `self_funded`; a `customer.subscription.deleted` event to the webhook returns `kept` (droplet NOT destroyed). Evidence = Stripe dashboard test sub status + Supabase owners row + webhook log.
3. No real money moved (test mode only for verification).

## §6 Boundaries
Products repo: `_lib/owners-store.js`, `stripe-spawn-webhook.js`, NEW `self-cancel.js` (+ test), `_lib/cloud-init.js` env add. No new deps (Node `crypto` + existing `stripe`). owners table gains the `self_funded` status value (no DDL — status is a free-text column). Instance-side balance check = OSS report skill (cross-repo contract above), not this patch's code.
