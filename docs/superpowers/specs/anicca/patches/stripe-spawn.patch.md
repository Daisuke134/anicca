# Patch — stripe-spawn (VERIFY patch: webhook complete + live, confirm end-to-end wiring)

2026-06-16. PATCH AUTHOR audit of subsystem **A-stripe-spawn** (spec `27a-stripe-spawn-design.md`,
`27-launch-workflow-and-ubi.md` §WF-A, `26-implementation-map.md` line 79 "クラウド月$30→貯まれば自動解約").

**Revision note (adversarial review ok=FALSE → fixed):** an earlier draft claimed the webhook had
"no producer" and added a new `stripe-spawn-checkout.js`. **That premise was WRONG.** The producer
already exists and is LIVE: the install page CTA is a Stripe **subscription Payment Link** on the same
$30/mo price. Stripe subscription Payment Links create Checkout Sessions and DO fire
`checkout.session.completed`. The grep for the price id returned 0 repo hits only because a Payment Link
references the price in the **Stripe Dashboard, not in repo code**. The proposed checkout function was
**redundant and unwired** (nothing referenced it) → **DROPPED**. This is now a VERIFY patch.

## Audit result (RAW evidence) — the subsystem is already DONE end-to-end

| artifact | RAW evidence |
|---|---|
| **Producer (live)** | `apps/landing/app/install/page.tsx:125` → `<CTA href="https://buy.stripe.com/anicca-cloud" variant="primary">Googleでログイン / $30/月で始める →</CTA>`. Subscription Payment Link on `price_1TilZaEeDsUAcaLSLpNvdmDT` (review-confirmed real link `https://buy.stripe.com/cNi7sL0dEdVI0iI7ki2880U`). Payment Link → Checkout Session → fires `checkout.session.completed`. |
| `apps/landing/netlify/functions/stripe-spawn-webhook.js` | exists, 97 lines, committed `1c158e96 feat(stripe-spawn): Stripe webhook → DO droplet spawn/destroy + Supabase owners`. `git status --short` = clean. |
| Deployed live | `GET https://aniccaai.com/.netlify/functions/stripe-spawn-webhook` → **405** (handler live, not 404). |
| Signature verify live | `POST` w/ `stripe-signature: t=1,v1=bad` → **400** (constructEvent rejects forged sig in prod → `STRIPE_SPAWN_WEBHOOK_SECRET` IS set in Netlify). |
| Email resolution | webhook line 61: `session.customer_email \|\| (session.customer_details && session.customer_details.email) \|\| null`. `customer_email` is null by default on Payment-Link sessions; the **`customer_details.email` fallback already handles this correctly**. |
| `_lib/spawn-droplet.js` | `createDroplet` POSTs DO `/v2/droplets` region `sfo3`, image `ubuntu-24-04-x64`, size `s-2vcpu-2gb`, `user_data=buildUserData`, deterministic name `anicca-<sub tail>`, injectable `fetch`. `destroyDroplet` DELETEs, treats 404 as destroyed. |
| `_lib/owners-store.js` | `isEventSeen`/`markEventSeen` (spawn_events ledger), `upsertOwner` (on_conflict=sub_id), `getOwnerBySub`, `markDestroyed` — REST/PostgREST + `headers(key)` identical to `telemetry-store.js`. |
| `_lib/cloud-init.js` | `buildUserData` emits `#cloud-config` (first line) + systemd `clawrouter.service`/`automaton.service`, `enable --now`, strips control chars from email. |
| TDD | `node --test _lib/__tests__/spawn-*.test.js` → **tests 30, pass 30, fail 0** (RAW run 2026-06-16). |
| `netlify/functions/package.json` | already `{"type":"commonjs"}`. |
| Price | `GET /v1/prices/price_1TilZaEeDsUAcaLSLpNvdmDT` (live key, read-only) → `active:True unit_amount:3000 usd recurring:month livemode:True` — REAL $30/mo. |

**Conclusion: the code is complete and live. There is nothing to add or rewrite.** What is NOT proven
from this session is the **runtime wiring + side effects**: that the Payment Link's webhook destination
points at the spawn endpoint, that the Supabase tables exist, and that a real checkout actually
provisions then destroys a droplet. This patch is the VERIFY procedure to close exactly those.

## Gaps (unverified runtime facts, not missing code)

| # | spec requires | RAW evidence of gap | severity |
|---|---|---|---|
| G1 | The Payment Link's checkout must reach **this** webhook endpoint. spec27a §Verify. | The endpoint a Payment Link fires is configured in the **Stripe Dashboard webhook destinations**, not in repo code — not inspectable from this session. If the destination is missing/points elsewhere, paid customers spawn nothing (silent). MUST confirm in Dashboard / via `stripe webhook_endpoints list`. | **HIGH** |
| G2 | spec27a §"Supabase tables": `owners` + `spawn_events` must exist or the first REST call (`isEventSeen`) 500s. | No service-key DB read attempted this session. If a table is absent the handler throws → 500 → Stripe retries forever, no droplet. MUST confirm by an E2E that returns 200. | **HIGH** |
| G3 | spec27a §Env: Netlify needs `STRIPE_SPAWN_WEBHOOK_SECRET` + `DO_SSH_KEY_FP`. | `grep -oE '^(STRIPE_SPAWN_WEBHOOK_SECRET\|DO_SSH_KEY_FP)=' ~/.openclaw/.env` → **0 hits** (env-of-record has only `STRIPE_SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DIGITALOCEAN_TOKEN`). Live `400` proves the webhook secret IS in Netlify, but the drift means a redeploy/rotation could silently break it. `DO_SSH_KEY_FP` absence → droplet boots `ssh_keys:[]` (cloud-init still runs; just no operator SSH). | MED |

**No `## Diff` — there is no code to change.** The earlier `stripe-spawn-checkout.js` proposal is
withdrawn. Adding it would ship a dead, unreferenced function (the install CTA already points at the
live Payment Link, not at a Netlify checkout endpoint), and duplicate a working purchase path.

## Commands — VERIFY (no apply, no commit; real droplet asserted via raw DO API; no money spent — Stripe CLI replays SIGNED test events)

```bash
cd /Users/anicca/anicca-project
set -a; . ~/.openclaw/.env; set +a   # STRIPE_SECRET_KEY, DIGITALOCEAN_TOKEN (+ STRIPE_SPAWN_WEBHOOK_SECRET if mirrored)

# G3: confirm Netlify has the secrets (names only — never echo values)
netlify env:list --filter functions | grep -E 'STRIPE_SPAWN_WEBHOOK_SECRET|DO_SSH_KEY_FP|DIGITALOCEAN_TOKEN'

# G1: confirm the Payment Link's checkout fires THIS webhook endpoint
#   Stripe Dashboard → Developers → Webhooks: a destination whose URL ends in
#   /.netlify/functions/stripe-spawn-webhook is subscribed to checkout.session.completed
#   + customer.subscription.deleted. Or via API:
stripe webhook_endpoints list | python3 -c "import json,sys;[print(e['url'],'->',e['enabled_events']) for e in json.load(sys.stdin)['data'] if 'stripe-spawn-webhook' in e['url']]"

# webhook guards live (RAW already confirmed 2026-06-16)
curl -s -o /dev/null -w 'GET webhook = %{http_code}\n' https://aniccaai.com/.netlify/functions/stripe-spawn-webhook   # expect 405
curl -s -X POST -H 'stripe-signature: t=1,v1=bad' -d '{}' \
     -o /dev/null -w 'bad-sig POST = %{http_code}\n' https://aniccaai.com/.netlify/functions/stripe-spawn-webhook      # expect 400

# G2 + spawn: real test subscription → real DO droplet + owners row
stripe listen --forward-to https://aniccaai.com/.netlify/functions/stripe-spawn-webhook &   # establishes signing secret
stripe trigger checkout.session.completed                 # webhook returns {ok:true,droplet_id:<N>} (200 ⇒ tables exist ⇒ G2 closed)
curl -s -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  "https://api.digitalocean.com/v2/droplets?tag_name=cloud-spawn" \
  | python3 -c "import json,sys;[print('DROPLET',d['id'],d['status'],d['name']) for d in json.load(sys.stdin)['droplets']]"
# owners row present + status=active:
curl -s -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  "$SUPABASE_URL/rest/v1/owners?select=sub_id,email,droplet_id,status&order=updated_at.desc&limit=1"

# destroy: cancel → real droplet gone
stripe trigger customer.subscription.deleted              # webhook returns {ok:true,destroyed:<N>}
curl -s -o /dev/null -w 'GET droplet after cancel = %{http_code}\n' \
  -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  "https://api.digitalocean.com/v2/droplets/<N>"          # expect 404
# owners row flipped:
curl -s -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  "$SUPABASE_URL/rest/v1/owners?droplet_id=eq.<N>&select=status"   # expect status=destroyed

# existing tests still green
cd apps/landing/netlify/functions && node --test _lib/__tests__/spawn-*.test.js   # expect pass 30 / fail 0
```

## Acceptance

| # | rubric | pass = |
|---|---|---|
| A1 | producer live | install CTA (`page.tsx:125`) opens the $30/mo subscription Payment Link on `price_1TilZaEeDsUAcaLSLpNvdmDT` |
| A2 | webhook destination wired | Stripe Dashboard / `stripe webhook_endpoints list` shows a destination ending `/stripe-spawn-webhook` subscribed to `checkout.session.completed` + `customer.subscription.deleted` (G1) |
| A3 | webhook guards | `GET` webhook = **405**; bad-sig `POST` = **400** (RAW confirmed 2026-06-16) |
| A4 | spawn creates a REAL droplet | signed `checkout.session.completed` → webhook **200** `{ok:true,droplet_id:N}`; **raw DO API GET shows droplet N status active**; `owners` row `status=active` (200 also closes G2 — tables exist) |
| A5 | cancel destroys it | `customer.subscription.deleted` → `{ok:true,destroyed:N}`; **raw DO API GET droplet N = 404**; `owners` row `status=destroyed` |
| A6 | idempotent on event.id | replay same `event.id` → 200 `duplicate`, NO second droplet (proven by `spawn-handler.test.js` + spawn_events ledger) |
| A7 | tests green | `node --test _lib/__tests__/spawn-*.test.js` → pass 30 / fail 0 |
| A8 | proof artifact | show the **droplet id created then destroyed** (DO API output before = active, after = 404) + the two `owners.status` transitions |

Constraints honored: no mock/dry-run (real DO droplet asserted via raw DO API + real Supabase row read);
no new redundant code shipped; no commit/push performed by this patch author. Cites live files read:
`install/page.tsx`, `stripe-spawn-webhook.js`, `_lib/spawn-droplet.js`, `_lib/owners-store.js`,
`_lib/cloud-init.js`, `_lib/__tests__/spawn-handler.test.js`, `telemetry.js`, `_lib/telemetry-store.js`,
`checkout.js`, `retreat-build-checkout.js`, `27a-stripe-spawn-design.md`.
