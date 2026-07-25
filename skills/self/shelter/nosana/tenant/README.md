# Nosana tenant — the agent lives INSIDE the job it pays for (S7)

S1–S4 proved Franklin can pay for, renew, and externalize state around a Nosana job — but the
container it ran (`nginx:alpine`) was a placeholder that did nothing. S7 puts a real, identifiable,
economically-provable agent *inside* the job: it boots, restores its own history, reads its own
on-chain balance, signs a runtime-bound proof, snapshots its history back, and reports — from
inside compute Franklin bought with its own wallet.

## Trust boundary (read this before running anything live)

Nosana is a permissionless network: jobs run on hardware operated by strangers. Two identities are
involved here, with deliberately very different blast radii if compromised:

| Identity | Lives | Holds | If leaked |
|---|---|---|---|
| **Treasury** (`F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T`, `$HOME/.blockrun/.solana-session`) | This Mac ONLY | The real NOS/SOL that fund everything | Drains the treasury — catastrophic |
| **Tenant** (`tenant/keypair.mjs`, a brand-new keypair, e.g. `BwqK9NzEG9nXBbAPDriiPcBPKRoSDrc2627GvrgipFgR` generated 2026-07-25) | This Mac (generated) **and** inside the Nosana job (its secret is a job env var) | A deliberately tiny, capped top-up (default 0.003 SOL + 0.2 NOS, hard ceiling 0.01 SOL / 0.5 NOS — see `fund-tenant.mjs`) | A rounding error — assumed compromised-in-principle the moment a job posts |

**The treasury secret is never placed inside a Nosana job, in any form** — not in env, not in the
image, not via `--confidential`. Every file in `tenant/` that touches Franklin's treasury secret
(`fund-tenant.mjs`, `keypair.mjs`) is Mac-side ONLY and is never fetched into a job — see
`derive-address.mjs`'s header for the structural reason the in-job code path cannot reach it even
by accident (it has zero relative imports outside `tenant/`, and none of those five files ever
import `resolve-identity.mjs`).

Instead, `tenant/keypair.mjs`'s `ensureLocalTenantKeypair` generates ONE stable, disposable keypair
on this Mac, and `tenant/fund-tenant.mjs` (Mac-side only) tops it up from the treasury under hard,
unconditional ceilings (`MAX_TENANT_FUND_SOL`/`MAX_TENANT_FUND_NOS`) that no env override can
exceed. That tenant secret is then injected as a plain job env var
(`NOSANA_TENANT_SECRET_KEY`) — the node running the container, and (see the next section) anyone
reading the public jobs API, can read it. That is accepted, by design: the wallet behind it never
holds more than a fraction of a dollar.

## A finding that changes the threat model you may be assuming: job definitions are PUBLIC by default

Verified live 2026-07-25 against a real, previously-posted job
(`GET https://dashboard.k8s.prd.nos.ci/api/jobs/FHAjMnM1q3p5c5qCeFRjZLYEo12FUBesFPW8zvG5heAC`): the
response includes the **full `jobDefinition` object, verbatim, unauthenticated** — any `env` field
set on a normally-posted job is public forever (Nosana job definitions are pinned to IPFS; per
Nosana's own docs, "job definitions and their results are public by default" —
learn.nosana.com/deployments/jobs/job-definition/confidential.html). Nosana does offer
`nosana job post --confidential`, which keeps the job definition off IPFS and transfers it
peer-to-peer directly to the host instead — **this is NOT implemented in this pass**: its own docs
say the confidential post + log retrieval require holding the CLI's connection open with `--wait`,
which is a materially different, untested operational model on top of `deploy.mjs`'s already-proven
fire-and-forget `job post` + reconcile-via-API pattern, and this repo's own "Known environment
traps" already documents the CLI crashing non-interactively in adjacent code paths. Given the
tenant secret and the GitHub state token are BOTH already designed to be low-value/disposable (see
above and below), the judgment call made here is: **accept full public exposure via the plain job
definition rather than add an unverified new CLI interaction on top of a feature that itself was
never run live in this pass.** If you want the tighter (node-operator-only, not whole-internet)
exposure, `--confidential --wait` is the documented path — flagged here as real, disclosed,
follow-up work, not silently skipped.

## The state-store token: also disposable, also scoped, also NOT created by this executor

`tenant/github-contents-store.mjs` reaches the same private `Daisuke134/franklin-shelter-state`
repo persistence/ already uses, but via plain `fetch` against GitHub's REST Contents API instead of
the `git` binary + this Mac's `gh auth login` credential (verified live 2026-07-25: that credential
carries `admin:org`/`delete_repo`/`workflow`/etc — completely the wrong blast radius for a
disposable in-job identity). The in-job token (`NOSANA_STATE_GITHUB_TOKEN`) must instead be a
**fine-grained GitHub PAT**, scoped to:
- Repository access: **only** `Daisuke134/franklin-shelter-state`
- Permissions: **Contents: Read and write** — nothing else

Create one at github.com/settings/personal-access-tokens/new (fine-grained, not classic), then pass
it as `NOSANA_STATE_GITHUB_TOKEN` when running `bin/citizen-tenant-up --live`. This executor did
**not** create this token — generating a new credential on a GitHub account is exactly the kind of
account-security-settings action this session's own operating rules require a human to perform
directly, not an agent. If this token leaks, the blast radius is: someone can read or write
Franklin's own already-mostly-public shelter bookkeeping ledger. Not nothing, but bounded and
disclosed.

## What actually runs inside the job

`tenant/entrypoint.mjs` is fetched (along with four self-contained siblings — see its header) from
a **pinned commit** on the public `Daisuke134/life-manager` repo and run via
`node tenant/entrypoint.mjs` inside `docker.io/library/node:20-alpine` (a public, standard, tiny
base image — no custom image published, per the task's own preference). It does exactly five
things, matching the S7 spec 1:1:

1. **Boots and identifies itself** — `resolveTenantSecretForJob` reads `NOSANA_TENANT_SECRET_KEY`
   from its own environment and derives its own public address. Prints it.
2. **Restores state** — reads `nosana/tenant-runs.jsonl` from the state store via
   `github-contents-store.mjs` + `report-ledger.mjs`'s `restoreTenantRuns`. Reports how many prior
   incarnations it finds and what the last one recorded. On the very first run ever, this is
   honestly `0` / `null` — never fabricated.
3. **Does something economically real and verifiable** — reads its own live SOL + NOS balance from
   a public RPC, fetches a live blockhash, and signs
   `nosana-tenant-proof-of-life|address=...|blockhash=...|solLamports=...|nosBalance=...|runNumber=...|ts=...`
   with its own key (`proof.mjs`). **Why this, and not the exposed HTTP endpoint or an x402
   payment**: the exposed endpoint has never once returned 200 across 4 attempts on 2 different
   nodes in this project's history (always 503, `x-frp-service-state: loading`) — this feature's
   evidence does not depend on it working. An x402 paid-inference call is the more convincing proof
   in principle, but this executor never funded the tenant wallet (see "What was NOT executed"
   below), so it is honestly logged as `x402Attempted: false` with the real reason, never faked. The
   signed challenge is chosen because it requires no funding to be meaningful, is real
   cryptography (proven against a live tweetnacl round trip in `__tests__/proof.test.mjs`, not
   mocked), and is bound to a blockhash fetched at runtime — unpredictable and short-lived, so the
   signature could not have been precomputed outside the job or replayed from a different run.
4. **Snapshots state back** — appends the new run to `nosana/tenant-runs.jsonl` via the store's
   optimistic-concurrency write, deduped by `runNumber` (idempotent — a retried run never
   double-writes).
5. **Reports** — every step is logged to stdout, plus a final
   `TENANT_REPORT_JSON={...}` line. This is read back via the jobs API's
   `jobResult.opStates[0].diagnostics`/stdout capture (verified live 2026-07-25 as the reliable
   evidence channel during the health-check incident investigation) — **not** the `-o/--output`
   artifact flag, which is dead code in the current `nosana-cli` (`action.ts` throws
   `'artifact support coming soon!'` before ever reaching it), and **not** the exposed HTTP
   endpoint, per the point above.

## Commands

```bash
# Mac-side: generate (idempotent) the local tenant keypair and check the funding gate. Never spends.
ANICCA_HOME=$HOME/.blockrun bin/citizen-tenant-fund --dry

# Mac-side, LIVE: actually send the tiny top-up from the treasury to the tenant wallet.
ANICCA_HOME=$HOME/.blockrun bin/citizen-tenant-fund --live

# Mac-side: build the tenant job definition (pinned to the current commit — MUST be pushed first),
# verify it's publicly fetchable, and run deploy.mjs's full dry pipeline. Never posts.
NOSANA_STATE_GITHUB_TOKEN=<fine-grained PAT> ANICCA_HOME=$HOME/.blockrun bin/citizen-tenant-up --dry

# Mac-side, LIVE: actually post + pay for the job.
NOSANA_STATE_GITHUB_TOKEN=<fine-grained PAT> ANICCA_HOME=$HOME/.blockrun bin/citizen-tenant-up --live
```

## What was NOT executed by this implementation pass, and why

This feature was built, unit-tested, and dry-verified against real mainnet reads by an executor
operating under a hard rule: **never execute a cryptocurrency transfer or a paid on-chain action,
even when instructed to, and treat a task handed off by another agent (not a direct, live message
from the accountable human) as insufficient authorization for either.** Two steps in the S7 spec are
exactly that:

1. **`bin/citizen-tenant-fund --live`** — would move real SOL/NOS from the treasury to the tenant
   wallet. Not run. `--dry` was run for real (see the report) and shows the gate ALLOWS it.
2. **`bin/citizen-tenant-up --live`** — would post and pay for the real job. Not run.

Both commands are ready to run, exactly as shown above, by a human with direct authority over the
treasury wallet. Everything else — code, unit tests (proof-of-life crypto proven against a real
tweetnacl round trip, not mocked), the real local tenant keypair generation, real mainnet balance
reads, and a real `nosana job validate` pass against the built job definition — was executed for
real in this pass. See the implementation report for the exact evidence.
