# BROWSER-AUTH-1 production evidence

## Verdict

**Incomplete — mandatory review fix round 1/5 is current.** The prior
SauceDemo fixture does not satisfy the agent-owned-account requirement, and the
earlier evidence window included a local-browser preflight. None of the
historical results below closes BROWSER-AUTH-1.

Completion now requires one entirely new cloud-only evidence window that
re-runs production schema/key readback, two-tenant isolation, an actual
provider login using runtime-only `LM_AGENT_BROWSER_EMAIL`, authenticated
provider readback before and after a same-SHA `life-call` restart, expiration
handoff, Telegram delivery, secret scans, Steel live-session count zero, and
unchanged Mac loops. Finite expired cookies must also be removed before
seal/compare, and `readBrowserJob` must expose
`telegram_result_message_id`.

This evidence does not claim that one cookie works on every provider or that
Life Manager bypasses CAPTCHA, OTP, KYC, payment, or provider risk controls.

## Mandatory review fix round 1/5

| Check | Fresh result |
|---|---|
| RED | `54` focused tests: `3` expected failures (finite expired cookie in scoped/store handoff; missing Telegram result projection) |
| GREEN | same focused command: `54/54 PASS` |
| Full Life Manager suite | `1572/1572 PASS` |
| Deterministic eval | calendar=`21/21`, late=`12/12`, context=`12/12`, score=`27/27`, intent=`18/18`, mental=`15/15`, physical=`19/19`, relations=`10/10` |
| Panel privacy eval | api=`177`, browser=`63`, recipes=`19`, channels=`9` |
| SSOT | BROWSER-AUTH-1=`current/incomplete`; BROWSER-MATRIX-1=`pending` |

The production change removes only cookies with a finite positive expiration
at or before the current time. Future and session cookies remain. The filter is
applied before exported context reaches durable storage; the store also applies
it before sealing and on defensive open. `readBrowserJob` now projects the
durable `telegram_result_message_id`.

## Production release and schema

| Evidence | Value |
|---|---|
| Final merge | `10d58ed1ce8099cee0f3de45fb4fdb693f29ef77` |
| Final PR | `#1255` |
| Railway deployment after same-SHA restart | `67abf2da-5a54-48f8-a7e4-3bb968aa1766` |
| Railway state | `SUCCESS`, exact commit match |
| Runtime encryption key | configured=`true`, decoded bytes=`32`; value never printed |
| Auth table | exists=`true`, expected columns=`true` (`13/13`) |
| Isolation | primary key=`1`, RLS=`true`, policies=`0`, anon/authenticated grants=`0`; owner-only access |
| Stored plaintext | context values=`0`; only ciphertext, IV, tag, hash, version, timestamps, and state are queryable |
| Focused browser-auth tests | `117/117 PASS` |
| Full Life Manager suite | `1572/1572 PASS` |
| Deterministic eval | calendar=`21/21`, late=`12/12`, context=`12/12`, score=`27/27`, intent=`18/18`, mental=`15/15`, physical=`19/19`, relations=`10/10` |
| Panel privacy eval | api=`177`, browser=`63`, recipes=`19`, channels=`9` |
| Warning / diff checks | warning lines=`0`, `git diff --check`=`PASS` |
| Secret tools on final patch | Gitleaks=`0`; TruffleHog verified=`0`, unverified=`1` (the exact public Railway deployment UUID, not a credential) |

The implementation landed through PRs `#1248`, `#1249`, `#1254`, and `#1255`.
The final release also rejects unsafe/cross-origin readbacks, literal IP hosts,
model-only success claims, visible login/risk UI, and semantically ambiguous
numeric input grids.

## Two-tenant isolation proof

Two synthetic tenant IDs used the same public origin, separate opaque markers,
and the production encrypted store. No raw marker is recorded here.

| Tenant | Context SHA-256 | Seed Steel | Restore Steel | Final row |
|---|---|---|---|---|
| A | `2d643d335f896cf687bee8aa80f8c589df1531332bb6b33bed6b16c4e9cad55b` | `a4ffe736-8286-428d-862a-6b39e427085c` | `99a0dabb-714f-4d33-9f40-c872860801bb` | `invalidated` |
| B | `f962c2988d7f78c3e9f88442ed61568e4a92a7772957b705c5c5346628474440` | `234e16bd-cc72-4a85-b950-3f7b0dac0cc6` | `71defe5b-f408-4dc4-b1cd-caf96895a14d` | `invalidated` |

Each restore returned only its own opaque marker. Wrong tenant, wrong origin,
and wrong principal lookups each returned no context. The hashes differ, all
four Steel sessions were released, and both synthetic rows are inactive.

## Real provider boundary: Luma

BROWSER-GEN-1 already proved a real external registration:

| Evidence | Value |
|---|---|
| Registration job | `73d313c0-2574-49d2-8aad-e40665db0cdb` |
| Steel session | `ac1fabf6-eada-48d2-a0ee-e9145504a989` |
| Provider readback | Luma `You’re In` |
| Telegram evidence | `350` |
| PNG SHA-256 | `0a72dec21b1d831299a1c8760e5d2658013bd7a91deae26b0e2bc430447c1c1f` |
| Steel release | `true` |

Luma then exposed the honest portability boundary. Restored cloud jobs
`b24254dd-d797-454a-97e8-194220c9aa77` and
`9d7e872e-512b-494b-9fdd-2cf19575e21c` loaded and re-saved the Luma context,
released Steel sessions `67cc5c22-0cf9-4d2a-813f-13cb4bbf4f32` and
`9565cf97-a967-4c7c-86b7-565a2c45cd90`, and sent Telegram evidence `383` and
`386`; provider status remained registration-pending because management access
was email-gated. Life Manager did not relabel that as authenticated success.
This is a provider-policy limitation, not a transport/session-store failure.

## Historical fixture (not completion evidence): SauceDemo

SauceDemo is a public client-side authentication fixture whose credentials are
published by the provider page. They were parsed at runtime and were never
written to the repository, helper, trace, receipt, Telegram text, or this file.

### Login and immediate fresh-session restore

| Evidence | Login/save | Immediate restore |
|---|---|---|
| Steel session | `ee967051-c636-49df-b0de-c198af27b336` | `749486eb-7980-451e-95c7-6b83cb81a1b7` |
| Provider marker | `Products` | `Products` |
| Context SHA-256 | `9cb0a50d29ba508aada1461da24722b0755bd6434da9a1bdcc5f24bdf65bb6cc` | same |
| Cookie scope | count=`1`, domain exactly `www.saucedemo.com` | imported count=`1`, exact domain |
| Browser storage scope | only `https://www.saucedemo.com` | same |
| Released | `true` | `true` |

### Same-SHA restart and durable authenticated read

The deployment restarted on the same merge SHA before this job. The process was
new and the Steel session ID differed from both login and immediate restore.

| Evidence | Value |
|---|---|
| Durable job | `29ed4b4d-ceae-43d6-a5ef-0c48773d6ee6` |
| Steel session | `552d30ed-1bb0-4624-8cf4-d8a331796df1` |
| Durable status | `completed` |
| Provider receipt | `authenticated`, confirmed=`true`, handoff=`false` |
| Auth trace | loaded=`true`, saved=`true`, invalidated=`false` |
| Telegram text / photo | `398` / `399` |
| Evidence SHA-256 | `25b425a9a903d46969824cfe26497d5150d790e31aabef9b265369d1f75db19d` |
| Steel release | `true` |

The first read helper displayed a false `null` for the Telegram text ID because
`readBrowserJob` does not project `telegram_result_message_id`. Direct database
readback and the live Bot API response both confirm text ID `398`; no delivery
was lost.

### Exact-row expiration and honest handoff

| Evidence | Value |
|---|---|
| Expired exact row | `true` |
| Durable job | `23cbf8bf-ed9b-4f9e-a162-eeb643289a00` |
| Steel session | `62e8aa08-1dde-4345-9d61-049ac19c3974` |
| Durable/provider status | `handoff_required` / `login_required` |
| Provider confirmation | `false` |
| Handoff reason | `login` |
| Auth trace | loaded=`false`, saved=`false`, invalidated=`true` |
| Final auth row | `invalidated` |
| Telegram text / photo | `400` / `401` |
| Evidence SHA-256 | `d5cef6c2b5988fa1e83713259d3e27ae45bffffc059be98f1baffdf65505d46f` |
| Steel release | `true` |

No success receipt or duplicate side effect was emitted.

## Secret and evidence-content audit

The scan inventory included the runtime browser email, runtime password,
session-encryption key, database URL, Telegram token/webhook secret, AgentMail
key/inbox, Railway/GitHub/provider tokens, decrypted runtime cookie/storage
values, and seed/private-key markers. Only counts and booleans were emitted.

| Surface | Runtime exact values | Email | Password | Token/key | DB URL | Raw cookie/storage | Seed/private key |
|---|---:|---:|---:|---:|---:|---:|---:|
| Positive receipt | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Positive trace | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Positive Telegram text metadata | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Negative receipt | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Negative trace | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Negative Telegram text metadata | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Current production log window (`576` bytes) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Auth branch + current docs (`235615` bytes; decrypted runtime values=`3`) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Telegram photo/evidence content (exact runtime-value inventory) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

The public SauceDemo page publishes a demo credential. It is not a Life Manager
runtime secret and is intentionally not copied into this evidence. Repository
and branch scans use the exact runtime inventory to distinguish secrets from
synthetic test strings.

## No-local-browser window and release cleanup

The fresh evidence window after the AgentMail/account reconnaissance used only:

```text
production life-call container
  → steel-browser.railway.internal:8080
  → provider
  → Telegram
```

Task execution audit in that fresh window found local Mac
Chrome/CloakBrowser/Playwright/CDP launches, navigation, profile writes, or
side effects=`0`. The runtime-only verification helper was streamed over
`railway ssh`, deleted locally, and never committed.

Earlier, outside this reset evidence window, one isolated read-only Zoho
CloakBrowser preflight occurred while evaluating the agent-owned email path.
It ended `closed=true`, `mutation=false`. Therefore this document claims zero
local browser use only for the fresh post-AgentMail production proof window,
not for all historical investigation.

Final Steel inventory contained live=`0`; both accepted proof sessions report
`released`. The remaining `idle` singleton is the OSS Steel service's own
single-slot state, not a live browser session.

## Deferred minor

Filter exported cookies whose finite `expires` timestamp is already in the past
before sealing or comparing context counts. Chromium already drops them on
import. The observed dropped item was an expired non-auth analytics cookie, not
the provider's authentication cookie, so this does not weaken the authenticated
readback proof. Track it in final review; do not misstate it as complete.

## Boundary and next cursor

BROWSER-AUTH-1 proves encrypted tenant isolation, fresh-session restoration,
same-SHA restart continuity, explicit provider-boundary honesty, exact-row
expiration, Telegram evidence, and session release. It does not prove the
three-intent/general-provider matrix or recovery idempotency.

The next Life Manager browser cursor is `BROWSER-MATRIX-1`.
