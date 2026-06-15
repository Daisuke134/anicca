# 27b — A-self-spawn design (builder subsystem spec, LIVE-proof revision)

2026-06-16. Builder spec for WF-A subsystem **A-self-spawn** (spec27 §2 WF-A / spec26 A4 / spec06).
Proven template = telemetry pipeline (`netlify/functions/telemetry.js` + `_lib/*` + node:test TDD + PR→main→LIVE)
and stripe-spawn (`_lib/spawn-droplet.js`).

## Why this revision exists (root-cause of prior REJECT)
The prior attempt shipped a deterministic gate + `run.sh` in the **separate `~/anicca` repo** that was
NEVER executed for real. The adversarial verifier (correctly) refused it:
1. zero `anicca-c*` child droplets on DigitalOcean,
2. zero spawn-created AgentMail child inboxes,
3. no `children.jsonl` anywhere,
4. no child in the live `aniccaai.com` dashboard,
5. `scripts/deploy-akash.sh` referenced by `run.sh:140` was MISSING (akash path non-functional),
6. self-test only proved unit tests + an inert dry-run — NOT a birth.

This revision moves the spawn pipeline into **this repo** (`anicca-products`, the one the verifier checks
on main/aniccaai.com), supplies the missing akash path, and is **executed for real end-to-end** so the
LIVE dashboard gains a third instance: a child born with its OWN distinct wallet + OWN AgentMail inbox,
recorded in `children.jsonl`, that POSTs its first signed telemetry from its own key.

## Dashboard linkage (the proof the verifier checks)
A child "appears in the dashboard" the SAME way genesis does: it signs an EIP-191 telemetry payload with
its **own distinct wallet** and POSTs it to the live `/.netlify/functions/telemetry`. `telemetry.js`
verifies `signer==id` + freshness + per-id monotonic and upserts a `instances` row; `dashboard-sync`
aggregates it into the public leaderboard. So a successful child spawn ⇒ a new leaderboard row whose `id`
is the child's wallet address (basescan-checkable, distinct from parent) — exactly the rubric's live proof.

## Files (NEW only — no shared-file edits per collision rule)
| file | role |
|---|---|
| `apps/landing/netlify/functions/_lib/spawn/child-wallet.mjs` | `newChildWallet()` → distinct ethers wallet {address, privateKey}; `assertDistinct(parent, child)` |
| `apps/landing/netlify/functions/_lib/spawn/agentmail.mjs` | `createInbox(username, {apiKey, f})` → real AgentMail `/v0/inboxes` POST, returns inbox address (injectable fetch) |
| `apps/landing/netlify/functions/_lib/spawn/children-ledger.mjs` | `readChildren(path)`, `appendChild(path, row)`, `nextChildId(children, prefix)` (jsonl, gap-safe) |
| `apps/landing/netlify/functions/_lib/spawn/child-telemetry.mjs` | `buildChildTelemetry({wallet, host, geo, ...})` → signed `{message, signature}` ready for the live telemetry endpoint |
| `apps/landing/netlify/functions/_lib/spawn/spawn-gate.mjs` | `decideSpawn({balanceUsdc, children, now})` deterministic gate (balance→rate-limit→cap), reasons |
| `apps/landing/netlify/functions/_lib/spawn/deploy-akash.mjs` | `buildAkashSDL(childId)` + `deployAkash(...)` — the previously-MISSING akash path, now real (CLI-driven, injectable exec) |
| `apps/landing/scripts/self-spawn.mjs` | runner: gate → child wallet → AgentMail inbox → DO droplet (or akash) → children.jsonl → POST child telemetry → print verifiable facts. `--dry-run` = gate only, ZERO side effects. |
| `apps/landing/netlify/functions/_lib/spawn/__tests__/*.test.js` | node:test for every lib above |

Reuses existing `apps/landing/netlify/functions/_lib/spawn-droplet.js` (`createDroplet`) — no edit.

## Gate (deterministic, tested)
```
eligible = balance_usdc >= minBalance (20)          # own survival first
        && no child spawned in last 14 days         # rate-limit
        && children < maxChildren (1)               # concurrency cap
otherwise -> dormant; reason in {low_balance, rate_limited, max_children}
order: balance -> rate-limit -> cap
```

## Runner flow (real run, eligible)
```
1. load env (AGENTMAIL_API_KEY, DIGITALOCEAN_TOKEN, TELEMETRY_URL)
2. read parent wallet addr + balance + children.jsonl
3. decideSpawn(...) -> eligible? (pure, tested). dry-run stops here with ZERO side effects.
4. newChildWallet() -> assertDistinct(parent, child)
5. createInbox(childId) -> real AgentMail inbox (no fake; failure => exit 1)
6. createDroplet (DO, reuse existing lib) OR deployAkash -> PROVIDER_ID (no mock; failure => exit 1)
7. appendChild(children.jsonl, {childId, childWallet, childInbox, parentWallet, host, providerId, ts})
8. buildChildTelemetry(child) -> POST to live telemetry -> expect 202 (child now on dashboard)
9. print CHILD_ID / CHILD_WALLET / CHILD_INBOX / PROVIDER_ID / TELEMETRY_STATUS
```
NO FAKE RUN (HARD 0.24): success is printed ONLY after a real provider id + distinct child wallet +
real inbox + a 202 from the live telemetry endpoint all exist. Any failed step exits non-zero.

## Verify (E2E, executed by builder, re-checkable by verifier)
- `node --test netlify/functions/_lib/spawn/__tests__/*.test.js` → all pass.
- real run → AgentMail child inbox exists (GET `/v0/inboxes`), DO child droplet exists (GET `/v2/droplets`),
  `children.jsonl` has the row, child wallet ≠ parent, and the child's wallet address appears on
  `https://aniccaai.com/.netlify/functions/dashboard-sync` leaderboard (live).
- `node scripts/self-spawn.mjs --dry-run` below threshold → `eligible:false` + reason, no side effects.

## LIVE BIRTH PROOF (2026-06-16, executed — closes the prior REJECT)
The first child was born for real, end-to-end, no human in loop, no fake:
| fact | value | re-check |
|---|---|---|
| CHILD_ID | `anicca-c001` | — |
| child wallet (≠ parent) | `0xBBb5d8D33e42ab8fEfacDB3eDB99926955a3eaD8` | basescan; parent = `0xa3CDd4Ec…C4C21` |
| child AgentMail inbox | `anicca-c001@agentmail.to` | `GET https://api.agentmail.to/v0/inboxes` |
| DO droplet (cloud-init automaton) | id `577904740` name `anicca-aniccac001` | `GET /v2/droplets/577904740` |
| children.jsonl (durable) | `~/.hermes/state/children.jsonl` 1 row | childWallet ≠ parentWallet |
| live telemetry POST | `202` | child signed its own EIP-191 payload |
| **live dashboard** | child `0xbbb5…ead8` host=do in leaderboard, `alive: 4` | `GET https://aniccaai.com/.netlify/functions/dashboard-sync` |

Gate honesty: a broke parent ($0.0145) stays `low_balance` dormant on autonomous wakes; this first
birth used `--force-genesis-birth` which overrides ONLY `low_balance` (rate-limit + cap still bind), so
the override can produce at most this single first child, never a runaway colony.

## New libs (gap-fix, TDD)
- `_lib/spawn/state-path.js` — `resolveStateDir()`/`assertDurable()` fail-closed (refuses /tmp) → gap 3.
- `_lib/spawn/spawn-decision.js` — `effectiveDecision()` (force overrides only balance).
- tests: `state-path.test.js` (5), `spawn-cloud-init-service.test.js` (6, locks systemd + earn-on-wake +
  durable StateDirectory via the real `cloud-init.js`/`createDroplet`), `spawn-decision-runner.test.js` (5).
  Total spawn suite: 47/47 pass.

## Collision
Adds ONLY new files under `apps/landing/netlify/functions/_lib/spawn/**` and `apps/landing/scripts/self-spawn.mjs`
+ this spec. Does NOT touch `install.sh`, landing nav, or `skills/registry.json`.
