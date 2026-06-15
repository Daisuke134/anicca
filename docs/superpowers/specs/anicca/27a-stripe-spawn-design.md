# 27a — A-stripe-spawn design (builder subsystem spec)

2026-06-16. Builder spec for WF-A subsystem **A-stripe-spawn** (spec27 §2 WF-A / spec26 A8d / Q12 / Q6).
Proven template = telemetry pipeline (`netlify/functions/telemetry.js` + `_lib/*` + node:test TDD + PR→main→LIVE).

## Goal (UX)
顧客が Stripe Checkout で月額サブスク決済 → webhook が **DO droplet を cloud-init で起動**(その人専用の cloud Anicca 個体)→ Supabase `owners` に {email, droplet_id, sub_id} を保存。
サブスク解約(`customer.subscription.deleted`)で droplet を destroy(課金停止=個体退役)。

## File / function (NEW files only — no shared-file edits)
| file | role |
|---|---|
| `apps/landing/netlify/functions/stripe-spawn-webhook.js` | handler: constructEvent → route by type → spawn/destroy |
| `apps/landing/netlify/functions/_lib/spawn-droplet.js` | DO API: createDroplet(cloud-init), destroyDroplet — injectable fetch |
| `apps/landing/netlify/functions/_lib/owners-store.js` | Supabase REST: upsertOwner, getOwnerBySub, markDestroyed, isEventSeen, markEventSeen — injectable fetch |
| `apps/landing/netlify/functions/_lib/cloud-init.js` | buildUserData(): Q6.command.sh の #cloud-config 文字列を生成 |
| `apps/landing/netlify/functions/_lib/__tests__/spawn-*.test.js` | node:test (handler / droplet / owners / cloud-init) |

## Behaviour contract
1. **method**: 非 POST → 405。
2. **signature**: `STRIPE_SPAWN_WEBHOOK_SECRET` で `constructEvent`。失敗 → 400。secret 必須(本番。dev fallback は telemetry 同様に置かない=偽署名拒否)。
3. **env 欠如**: `STRIPE_SECRET_KEY` / `DIGITALOCEAN_TOKEN` / `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` の必須欠如 → 500 `missing env`。
4. **idempotency**: `event.id` を `spawn_events` テーブルで dedupe。既見 → 200 `duplicate`(副作用ゼロ)。新規 → 副作用成功後に markEventSeen。
5. **`checkout.session.completed`**:
   - `session.customer_email`(or `customer_details.email`)+ `session.subscription`(sub_id)を読む。
   - `createDroplet({ owner_email, sub_id })` → DO API POST `/v2/droplets`(region sfo3, size s-2vcpu-2gb, image ubuntu-24-04-x64, ssh_keys=[DO_SSH_KEY_FP], user_data=cloud-init)。
   - `upsertOwner({ email, droplet_id, sub_id, status:"active" })`(on_conflict=sub_id)。
   - 200 `{ ok:true, droplet_id }`。
6. **`customer.subscription.deleted`**:
   - `sub_id = event.data.object.id` → `getOwnerBySub(sub_id)` → droplet_id 取得 → `destroyDroplet(droplet_id)`(DO API DELETE)→ `markDestroyed(sub_id)`(status="destroyed")。
   - owner 不在 → 200 `no owner`(冪等)。
7. **other event types**: 200 `ignored`。
8. **DO/Supabase 失敗**: throw → 500(Stripe が再送 → idempotency が二重起動を防ぐので markEventSeen は **副作用成功後** に置く)。

## Idempotency 順序(二重起動防止)
`isEventSeen(event.id)` → seen なら 200 即返し。未見 → spawn/destroy 実行 → **成功後に** `markEventSeen(event.id)`。
(spawn 中にクラッシュしたら markEventSeen されないので Stripe 再送で再試行できる。droplet 名は `anicca-<sub_id 末尾>` で一意化。第一防御は markEventSeen-after-success。)

## Env (Netlify)
`STRIPE_SECRET_KEY` / `STRIPE_SPAWN_WEBHOOK_SECRET` / `DIGITALOCEAN_TOKEN` / `DO_SSH_KEY_FP` / `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`。

## Supabase tables (REST, PostgREST)
- `owners(sub_id text pk, email text, droplet_id bigint, status text, created_at, updated_at)` — on_conflict=sub_id。
- `spawn_events(event_id text pk, seen_at)` — idempotency ledger。

## Verify (E2E, by verifier agent)
Stripe test `checkout.session.completed` event → droplet active(DO API GET status=active)→ `customer.subscription.deleted` → droplet destroyed(GET 404)。本番 curl: GET webhook=405、署名なし POST=400。

## TDD test matrix
| test | assert |
|---|---|
| non-POST | 405 |
| bad signature | 400 |
| missing env | 500 |
| duplicate event.id | 200 + droplet NOT created (副作用ゼロ) |
| checkout.session.completed | createDroplet called(正 user_data)+ upsertOwner called + 200 droplet_id |
| customer.subscription.deleted | destroyDroplet(droplet_id)+ markDestroyed + 200 |
| sub.deleted, owner 不在 | 200 no owner、destroy 未呼出 |
| other event type | 200 ignored |
| cloud-init buildUserData | #cloud-config 含む + owner_email 埋込 |
| markEventSeen は副作用成功後 | spawn throw 時 markEventSeen 未呼出 |
