# Nosana deploy executor (S1)

Franklin (an AI agent) rents its own GPU compute on Nosana and pays for it with **its own
Solana wallet** — zero human in the loop. This is S1 of the "agent financial independence" goal:
prove the payment rail works before building the self-renewing rent loop (S3) or externalizing
state (S4, `persistence/`) on top of it.

## The two Nosana payment rails, and why only one is used here

Nosana supports two ways to pay for a job:

1. **Wallet rail (used here, the only rail this executor will ever use).** The poster signs and
   broadcasts a Solana transaction from their own keypair, paying NOS directly out of their own
   token account. This is real, self-custodied money leaving a wallet Franklin controls.
2. **Credits rail (`nosana job post --api <key>` / `NOSANA_API_KEY`) — forbidden here.** Nosana
   credits are purchased with a card via Stripe on nosana.io — i.e. a human funds the account.
   Paying with credits would make Franklin's "compute rent" a line item on someone's credit card,
   not an expense Franklin covers from its own economic activity. That defeats the entire point
   of this goal (financial independence with no human in the loop), so `deploy.mjs` actively
   **refuses** to use it: if `NOSANA_API_KEY` (or `NOS_API_KEY`) is present in the environment, it
   is logged as deliberately ignored and never passed to the CLI's `--api` flag.

Franklin's identity for this rail is resolved once, canonically, via
`skills/earn/lib/resolve-identity.mjs`'s `resolveSolanaSecret` — the exact same secret every other
earn/spend engine in this repo already uses (Franklin's home is `$HOME/.blockrun`, secret at
`$HOME/.blockrun/.solana-session`). `keypair.mjs` derives the `nosana` CLI's required 64-byte
JSON-array keypair file from that secret at runtime into
`$ANICCA_HOME/.automaton/nosana_key.json` (mode 0600, parent dir 0700) — it is never a new or
second wallet, and the secret is never logged.

## Commands

```bash
# Dry run (DEFAULT — never spends, never posts). Resolves identity, prices the cheapest live GPU
# market, builds+validates a job definition, and runs the balance+cap gate, then stops.
ANICCA_HOME=$HOME/.blockrun bin/citizen-up
ANICCA_HOME=$HOME/.blockrun bin/citizen-up --dry   # equivalent, explicit

# Live run — the ONLY way this ever actually spends NOS and posts on-chain.
ANICCA_HOME=$HOME/.blockrun bin/citizen-up --live

# Help
bin/citizen-up --help
```

Env overrides (all optional): `NOSANA_JOB_IMAGE`, `NOSANA_JOB_EXPOSE_PORT`,
`NOSANA_JOB_DURATION_MINUTES` (default 15), `NOSANA_MAX_SPEND_USD` (default `0.50`, the hard cap
on any single job's estimated cost), `NOSANA_RPC_URL` / `SOLANA_RPC_URL`, `NOSANA_NETWORK`
(default `mainnet`).

## Module map

| File | Role |
|---|---|
| `keypair.mjs` | Resolves Franklin's secret, derives its address, materializes the CLI keypair file. Never logs secret material. |
| `market.mjs` | Fetches the live Nosana market price list and NOS/USD price; pure `selectCheapestMarket` / `estimateJobCost`. Wires (but does not modify) `skills/self/spawn/lib/cloud-target.mjs`'s generic, deliberately-unwired `fetchNosUsdPrice`. |
| `job-definition.mjs` | Pure builder + structural validator for a schema-0.1 `container` job definition exposing one long-running service. |
| `spend-gate.mjs` | Pure money-safety gate: per-job/daily/cumulative USD caps (mirrors `skills/earn/funding/lib/caps.py`'s semantics) plus NOS/SOL balance sufficiency. |
| `deploy.mjs` | Orchestrates the above, shells out to the real `nosana` CLI, records settled cost to `shelter-cost-ledger.js`. |
| `funding/acquire-nos.mjs` | S2: Franklin swaps its own SOL for NOS via Jupiter, zero human step. |
| `renew/` | S3: the self-renewal path (extends the live job before expiry, or reposts if none is alive) + the survival-drive runway signal. See `renew/README.md` for the full rail comparison. |
| `persistence/` | S4: externalizes the wallet manifest (addresses only) + every ledger above to a durable remote store, so a rebuilt job restores the same identity/ledgers a torn-down one had. See `persistence/README.md`. |
| `bin/citizen-up` (repo root) | Thin CLI entrypoint — no business logic, just argv parsing and wiring real defaults into `deployNosanaJob`. |
| `bin/citizen-rent` (repo root) | Thin CLI entrypoint for S3 — wires real defaults into `renew/executor.mjs`'s `renewShelter`. |
| `bin/citizen-state` (repo root) | Thin CLI entrypoint for S4 — wires real defaults into `persistence/{snapshot,restore}.mjs`. |

## Money-safety notes

- **Fail closed everywhere.** A price-fetch failure, an unresolvable identity, or no eligible
  market all *throw* rather than silently proceeding with a zero/free assumption.
- **At-most-once.** A live run writes an intent record (`nosana-deploy-intents.jsonl` under
  `resolveStateDir()`) *before* posting, then reconciles the real outcome by reading job state via
  `nosana job list --poster <address> --market <market> --time-start <ts>` (verified against
  `@nosana/cli`'s own source: this indexer-backed command returns each job's real `address`,
  `state`, `market`, and `timeStart`). If the post's stdout can't be confidently parsed AND
  reconciliation can't confirm a job, the run throws `post-unknown` rather than retrying —
  a human (or a future S3 reconciliation pass) must resolve it by hand.
- **Cap unification is follow-up work, not done here.** `spend-gate.mjs` re-expresses
  `caps.py`'s per-transfer/daily/cumulative + tx-hash-dedupe semantics in JS because this
  executor is JS and `caps.py` is Python (shelling out to Python from here was explicitly ruled
  out). The two cap engines currently live side by side; merging them into one implementation
  shared across languages (e.g. a small spec both wrap, or moving the Nosana spend into the same
  ledger `caps.py` already reads) is real, valuable follow-up work, not attempted in S1.

## Known gap: unverified `nosana job post` JSON shape

This session never ran `--live` (by explicit instruction — a real post is a human call, not an
executor call). `nosana job post --format json`'s exact stdout shape for the posted job's address
was therefore never observed directly; reading `@nosana/cli`'s own source
(`dist/src/providers/utils/ouput-formatter/json/JsonOutputEventHandlers.js`) shows its JSON
formatter accumulates fields like `job_posting`/`service_url` but **never explicitly sets a plain
`response.job` address field** — so `deploy.mjs`'s `parseJobAddressFromPostOutput` is a
best-effort guess over a few plausible shapes, and is **never trusted alone**: every post is
followed by `reconcileNosanaJob`, which re-reads real state via `job list` (a call whose JSON
shape *was* verified directly from source — `dist/src/cli/job/list/action.js` prints
`JSON.stringify(jobs, null, 2)` where each `job` has `.address`/`.state`/`.market`/`.timeStart`).
If the very first real `--live` run's stdout doesn't match any of the guessed shapes, the
reconciliation step is what actually finds the job — this is the highest-risk unverified
assumption in this deliverable (see the implementation report for detail).

## `@nosana/kit`: now a real dependency, used by S3 (renewal), not yet by S1 (this file's post path)

S3 (`renew/`, see `renew/README.md`) added `@nosana/kit@^2.7.0` to `package.json` — the vendor CLI
cannot renew a job at all (`nosana job extend` crashes; see `renew/README.md`), so the self-renewal
path had to use `@nosana/kit`'s `client.jobs.extend()`, the verified wallet-only on-chain rail
(**not** `client.api.jobs.extend`, which is the credits/Stripe rail — see `renew/README.md` for the
full comparison with quoted evidence). `deploy.mjs`'s own post path above still shells out to the
CLI unchanged — migrating it to `@nosana/kit` (closing the "unverified JSON shape" gap above by
construction) remains real, valuable follow-up work, now genuinely lower-cost since the dependency
is already present.
