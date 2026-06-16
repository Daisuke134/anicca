# Patch — stripe-spawn (entry-point + ops gaps)

2026-06-16. PATCH AUTHOR audit of subsystem **A-stripe-spawn** (spec `27a-stripe-spawn-design.md`,
`27-launch-workflow-and-ubi.md` §WF-A, `26-implementation-map.md` line 79 "クラウド月$30→貯まれば自動解約").

## Audit result (RAW evidence)

The **webhook itself is already DONE, tested, and LIVE** — this patch does NOT rewrite it:

| artifact | RAW evidence |
|---|---|
| `apps/landing/netlify/functions/stripe-spawn-webhook.js` | exists, 97 lines, committed `1c158e96 feat(stripe-spawn): Stripe webhook → DO droplet spawn/destroy + Supabase owners`. `git status --short` = clean. |
| Deployed live | `GET https://aniccaai.com/.netlify/functions/stripe-spawn-webhook` → **405** (handler live, not 404). |
| Signature verify live | `POST` w/ `stripe-signature: t=1,v1=bad` → **400** (constructEvent rejects forged sig in prod). |
| `_lib/spawn-droplet.js` | `createDroplet` POSTs DO `/v2/droplets` region `sfo3`, image `ubuntu-24-04-x64`, size `s-2vcpu-2gb`, `user_data=buildUserData`, injectable `fetch` — matches telemetry-store pattern. `destroyDroplet` DELETEs, treats 404 as destroyed. |
| `_lib/owners-store.js` | `isEventSeen`/`markEventSeen` (spawn_events ledger), `upsertOwner` (on_conflict=sub_id), `getOwnerBySub`, `markDestroyed` — all REST/PostgREST + `headers(key)` identical to `telemetry-store.js`. |
| `_lib/cloud-init.js` | `buildUserData` emits `#cloud-config` (first line) + systemd `clawrouter.service`/`automaton.service`, `enable --now`, strips control chars from email. |
| TDD | `node --test _lib/__tests__/spawn-*.test.js` → **tests 30, pass 30, fail 0** (RAW run 2026-06-16). |
| `netlify/functions/package.json` | already `{"type":"commonjs"}` — present, no edit needed. |
| Price | `GET /v1/prices/price_1TilZaEeDsUAcaLSLpNvdmDT` (live key, read-only) → `active:True unit_amount:3000 usd recurring:month livemode:True` — REAL $30/mo. |

## Gaps

| # | spec requires | RAW live evidence of gap | severity |
|---|---|---|---|
| G1 | A customer must be able to **buy** the $30/mo spawn sub so `checkout.session.completed` ever fires. spec27 line 19 + spec26 line 79 ("クラウド月$30"). | `grep -rln "price_1TilZaEeDsUAcaLSLpNvdmDT" apps/landing/` → **0 hits**. No checkout function creates a `mode=subscription` session for this price. The webhook is a dead end with no producer → it can NEVER fire from a real customer. | **CRITICAL** |
| G2 | Webhook reads `session.customer_email` (line 61). Stripe only populates it when checkout collects/creates a customer email. | `checkout.js` proves the pattern needs `customer_creation:always`; a spawn checkout that omits email collection yields `customer_email=null` → `upsertOwner({email:null})`. | HIGH |
| G3 | spec27a §Env: Netlify needs `STRIPE_SPAWN_WEBHOOK_SECRET` + `DO_SSH_KEY_FP`. | `grep -oE '^(STRIPE_SPAWN_WEBHOOK_SECRET|DO_SSH_KEY_FP)=' ~/.openclaw/.env` → **0 hits** (only `STRIPE_SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DIGITALOCEAN_TOKEN` present). Live `400` on bad-sig proves the secret IS set in Netlify, but it is NOT mirrored in the env-of-record → re-deploy/rotation drift risk. `DO_SSH_KEY_FP` absence → droplet boots with `ssh_keys:[]` (no operator SSH, but cloud-init still runs). | MED |
| G4 | spec27a §"Supabase tables": `owners` + `spawn_events` must exist or every event 500s on the REST call. | Cannot confirm rows without service key in this session; the webhook's first DB call is `isEventSeen` → if the table is absent the handler throws → 500. Acceptance must assert the test event returns 200 (proves tables exist). | MED |

**This patch closes G1+G2 with new code** (a checkout producer, the one missing link), and documents G3/G4 as ops/verify steps. No edit to the already-LIVE webhook.

## Diff — NEW file `apps/landing/netlify/functions/stripe-spawn-checkout.js`

Produces the subscription session the webhook consumes. CJS `exports.handler`, raw Stripe REST via
`fetch` + `x-www-form-urlencoded` (exact pattern of the proven `checkout.js` / `retreat-build-checkout.js`).

```javascript
// Stripe Checkout Session creator for the $30/mo cloud-Anicca spawn subscription.
// Producer for stripe-spawn-webhook.js: a completed session here fires
// `checkout.session.completed` → webhook spawns the DO droplet.
// POST {} → { url } redirect to Stripe-hosted checkout. (No body needed; fixed price.)
//
// Required env (Netlify): STRIPE_SECRET_KEY (sk_live).
// Price: price_1TilZaEeDsUAcaLSLpNvdmDT — LIVE, $30.00/mo USD recurring (verified 2026-06-16).
const SPAWN_PRICE = "price_1TilZaEeDsUAcaLSLpNvdmDT";

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };

  const STRIPE_KEY = process.env.STRIPE_SECRET_KEY;
  if (!STRIPE_KEY) return { statusCode: 500, body: "missing config" };

  // Allow override of the price via env for staging/test without code change.
  const PRICE = process.env.STRIPE_SPAWN_PRICE_ID || SPAWN_PRICE;

  const ORIGIN = (event.headers && (event.headers.origin || event.headers.Origin)) || "https://aniccaai.com";

  // mode=subscription so customer.subscription.* lifecycle events fire (spawn/destroy).
  // customer_creation=always + customer_email collection so the webhook receives
  // session.customer_email (it reads customer_email || customer_details.email).
  const params = new URLSearchParams();
  params.append("mode", "subscription");
  params.append("line_items[0][price]", PRICE);
  params.append("line_items[0][quantity]", "1");
  params.append("success_url", `${ORIGIN}/spawn?success=1&session_id={CHECKOUT_SESSION_ID}`);
  params.append("cancel_url", `${ORIGIN}/spawn?canceled=1`);
  params.append("customer_creation", "always");
  params.append("billing_address_collection", "auto");
  params.append("metadata[product]", "cloud-spawn");
  params.append("subscription_data[metadata][product]", "cloud-spawn");

  let session;
  try {
    const r = await fetch("https://api.stripe.com/v1/checkout/sessions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${STRIPE_KEY}`,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });
    session = await r.json();
    if (!r.ok || !session || !session.url) {
      console.error("spawn checkout: stripe error", session);
      return { statusCode: 502, body: JSON.stringify({ error: "stripe failure", detail: session }) };
    }
  } catch (e) {
    return { statusCode: 502, body: JSON.stringify({ error: "stripe network", detail: String(e) }) };
  }

  return {
    statusCode: 200,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url: session.url, session_id: session.id }),
  };
};
```

## Diff — NEW file `apps/landing/netlify/functions/_lib/__tests__/spawn-checkout.test.js`

node:test, injectable via `global.fetch` swap (same style as the repo's existing handler tests; no network).

```javascript
const { test, beforeEach, afterEach } = require("node:test");
const assert = require("node:assert");
const { handler } = require("../../stripe-spawn-checkout");

const realFetch = global.fetch;
beforeEach(() => { process.env.STRIPE_SECRET_KEY = "sk_test"; });
afterEach(() => { global.fetch = realFetch; });

function ev(method = "POST") { return { httpMethod: method, headers: { origin: "https://aniccaai.com" } }; }

test("405 on non-POST", async () => {
  const res = await handler(ev("GET"));
  assert.strictEqual(res.statusCode, 405);
});

test("500 when STRIPE_SECRET_KEY missing", async () => {
  delete process.env.STRIPE_SECRET_KEY;
  const res = await handler(ev());
  assert.strictEqual(res.statusCode, 500);
  assert.strictEqual(res.body, "missing config");
});

test("POST creates a subscription session for the spawn price → 200 { url }", async () => {
  let captured;
  global.fetch = async (url, opts) => {
    captured = { url, body: opts.body };
    return { ok: true, json: async () => ({ id: "cs_test_1", url: "https://checkout.stripe.com/c/pay/cs_test_1" }) };
  };
  const res = await handler(ev());
  assert.strictEqual(res.statusCode, 200);
  assert.deepStrictEqual(JSON.parse(res.body), { url: "https://checkout.stripe.com/c/pay/cs_test_1", session_id: "cs_test_1" });
  assert.ok(captured.url.includes("/v1/checkout/sessions"));
  assert.ok(captured.body.includes("mode=subscription"));
  assert.ok(captured.body.includes("price_1TilZaEeDsUAcaLSLpNvdmDT"));
  assert.ok(captured.body.includes("customer_creation=always"));
});

test("env price override is honored", async () => {
  process.env.STRIPE_SPAWN_PRICE_ID = "price_override";
  let body;
  global.fetch = async (_u, o) => { body = o.body; return { ok: true, json: async () => ({ id: "cs", url: "https://x" }) }; };
  await handler(ev());
  assert.ok(body.includes("price_override"));
  delete process.env.STRIPE_SPAWN_PRICE_ID;
});

test("502 on stripe error", async () => {
  global.fetch = async () => ({ ok: false, json: async () => ({ error: { message: "no such price" } }) });
  const res = await handler(ev());
  assert.strictEqual(res.statusCode, 502);
});
```

No edit to `netlify/functions/package.json` — it is already `{"type":"commonjs"}` (verified).

## Commands

### Apply
```bash
cd /Users/anicca/anicca-project
git fetch && git checkout dev && git pull
git checkout -b feature/stripe-spawn-checkout
# create the two NEW files above verbatim:
#   apps/landing/netlify/functions/stripe-spawn-checkout.js
#   apps/landing/netlify/functions/_lib/__tests__/spawn-checkout.test.js
```

### Test (local, no network, no money)
```bash
cd apps/landing/netlify/functions
node --test _lib/__tests__/spawn-checkout.test.js          # expect: pass 5, fail 0
node --test _lib/__tests__/spawn-*.test.js                 # expect: pass 35, fail 0 (30 existing + 5 new)
```

### Ops gaps G3 (mirror secrets to env-of-record — names only, never echo values)
```bash
# Confirm Netlify already has them (live 400 on bad-sig proves STRIPE_SPAWN_WEBHOOK_SECRET set):
netlify env:list --filter functions | grep -E 'STRIPE_SPAWN_WEBHOOK_SECRET|DO_SSH_KEY_FP'
# If DO_SSH_KEY_FP absent, set so operator SSH works (fingerprint from DO account):
#   netlify env:set DO_SSH_KEY_FP "<fp>"
```

### Deploy (PR → main → Netlify functions)
```bash
git add apps/landing/netlify/functions/stripe-spawn-checkout.js \
        apps/landing/netlify/functions/_lib/__tests__/spawn-checkout.test.js
git commit -m "feat(stripe-spawn): $30/mo subscription checkout producer for spawn webhook"
git push -u origin feature/stripe-spawn-checkout
gh pr create --base dev --title "stripe-spawn checkout producer" --body "Closes G1/G2: webhook had no producer"
# after dev verify → PR dev→main → Netlify auto-deploys functions on main push.
```

### VERIFY (E2E — real droplet created then destroyed; NO money via Stripe CLI test events)
```bash
set -a; . ~/.openclaw/.env; set +a   # STRIPE_SECRET_KEY, STRIPE_SPAWN_WEBHOOK_SECRET, DIGITALOCEAN_TOKEN

# 1) producer live
curl -s -X POST https://aniccaai.com/.netlify/functions/stripe-spawn-checkout | python3 -c "import json,sys;print('checkout url:',json.load(sys.stdin)['url'][:48])"

# 2) webhook guards live
curl -s -o /dev/null -w 'GET webhook = %{http_code}\n' https://aniccaai.com/.netlify/functions/stripe-spawn-webhook   # 405
curl -s -X POST -H 'stripe-signature: t=1,v1=bad' -d '{}' \
     -o /dev/null -w 'bad-sig POST = %{http_code}\n' https://aniccaai.com/.netlify/functions/stripe-spawn-webhook      # 400

# 3) spawn → real DO droplet (Stripe CLI replays a SIGNED test event to the live webhook)
stripe listen --forward-to https://aniccaai.com/.netlify/functions/stripe-spawn-webhook &   # registers signing secret
stripe trigger checkout.session.completed                 # webhook returns {ok:true,droplet_id:<N>}
# confirm REAL droplet from raw DO API:
curl -s -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  "https://api.digitalocean.com/v2/droplets?tag_name=cloud-spawn" \
  | python3 -c "import json,sys;[print('DROPLET',d['id'],d['status'],d['name']) for d in json.load(sys.stdin)['droplets']]"

# 4) destroy → real droplet gone
stripe trigger customer.subscription.deleted              # webhook returns {ok:true,destroyed:<N>}
curl -s -o /dev/null -w 'GET droplet after cancel = %{http_code}\n' \
  -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  "https://api.digitalocean.com/v2/droplets/<N>"          # 404
```

## Acceptance

| # | rubric | pass = |
|---|---|---|
| A1 | producer exists & live | `POST /stripe-spawn-checkout` → 200 with a `checkout.stripe.com` `url` for `price_1TilZaEeDsUAcaLSLpNvdmDT`, `mode=subscription` |
| A2 | webhook guards | `GET` webhook = **405**; bad-sig `POST` = **400** (RAW already confirmed 2026-06-16) |
| A3 | spawn creates a REAL droplet | signed `checkout.session.completed` → webhook `{ok:true,droplet_id:N}`; **raw DO API GET shows droplet N `status` active** + `owners` row `status=active` |
| A4 | cancel destroys it | `customer.subscription.deleted` → `{ok:true,destroyed:N}`; **raw DO API GET droplet N = 404**; `owners` row `status=destroyed` |
| A5 | idempotent on event.id | replay same `event.id` → 200 `duplicate`, NO second droplet (proven by `spawn-handler.test.js` + spawn_events ledger) |
| A6 | tests green | `node --test _lib/__tests__/spawn-*.test.js` → pass 35 / fail 0 |
| A7 | proof artifact | show the **droplet id created then destroyed** (DO API output before = active, after = 404) |

Constraints honored: no mock/dry-run (real DO droplet asserted via raw DO API); no commit/push performed by this patch author; cites live files read (`stripe-spawn-webhook.js`, `_lib/spawn-droplet.js`, `_lib/owners-store.js`, `_lib/cloud-init.js`, `telemetry.js`, `_lib/telemetry-store.js`, `checkout.js`, `retreat-build-checkout.js`, `27a-stripe-spawn-design.md`).
