# Nosana tenant — the agent lives INSIDE the job it pays for (S7)

S1–S4 proved Franklin can pay for, renew, and externalize state around a Nosana job — but the
container it ran (`nginx:alpine`) was a placeholder that did nothing. S7 puts a real,
economically-provable agent *inside* the job: it boots, reads Franklin's own public history and
balance, recomputes its runway with the SAME code the Mac uses, signs a runtime-bound proof, and
reports — from inside compute Franklin bought with its own wallet.

**This is the SECOND pass.** The first pass put a funded, persistent tenant identity and a GitHub
token inside the job's env. Both were reachable — that was the ACCEPTED design at the time — but a
follow-up finding (below) showed the actual blast radius was far worse than "reachable by the node
operator": it was permanent, public, worldwide broadcast. The redesign below carries **zero
secrets of any kind**. If you are looking for the funded-tenant-in-the-job design, it is gone; the
Mac-side pieces of it (`fund-tenant.mjs`, `keypair.mjs`) are kept, unused by the current job, as
building blocks for a possible future delegated-spend design (see the bottom section).

## The finding that forced the redesign: job definitions go to public IPFS, permanently

Verified live 2026-07-25, independently, twice:

1. `GET https://dashboard.k8s.prd.nos.ci/api/jobs/<address>` returns the **full `jobDefinition`
   object, verbatim, unauthenticated** for any job, including any `env` field it carried.
2. That same job definition is **also pinned to public IPFS**. A real job's record carries
   `ipfsJob: <CID>`, and fetching that CID directly from `ipfs.io` — no auth, no API key — returns
   the identical job definition.

Nosana's own docs say it plainly: "job definitions and their results are public by default"
(learn.nosana.com/deployments/jobs/job-definition/confidential.html). So the first pass's design —
a funded tenant secret key + a GitHub token as plain job env vars — was not "readable by the node
operator who happens to run the job." It was **published to a permanent, world-readable, content-
addressed store the moment the job posted, with no way to ever take it back.** That is a materially
worse and categorically different risk than the one the first pass's README accepted, and the
right response is to carry no secret at all, not to accept a bigger blast radius.

`nosana job post --confidential` exists and keeps the definition off IPFS, transferring it
peer-to-peer instead — but its own docs describe a `--wait`-held-open-connection delivery/log
model, materially different from `deploy.mjs`'s proven fire-and-forget post + reconcile-via-API
pattern, and untested here. It also would not have helped the treasury key specifically — a
confidential job's definition still reaches the executing node in the clear, so it only narrows
exposure from "the whole internet, forever" to "the node operator, for the run" — real, but not
worth the untested-CLI-path risk once the actual design carries no secret to protect in the first
place.

## The redesign: zero secrets, one ephemeral identity, all public reads

| Piece | First pass | This pass |
|---|---|---|
| In-job identity | A **funded**, persistent tenant keypair, secret in job env | A **fresh, unfunded, ephemeral** keypair, generated inside the container every run — nothing to leak |
| State restore | `nosana/tenant-runs.jsonl` in the private `franklin-shelter-state` repo, via a GitHub token in job env | Franklin's own **public** job history, via the same unauthenticated jobs API this skill already trusts (`GET .../api/jobs?payer=<treasuryAddress>`) — `NOSANA_TREASURY_ADDRESS` (a public key) is the only env var carried |
| Economic proof | Sign a challenge over the tenant's own (unfunded) balance | Sign a challenge over **Franklin's real treasury balance + a runway recomputed with the literal, unmodified `../renew/survival-drive.mjs`** — the same file `../renew/executor.mjs` runs on the Mac |
| Snapshot-back | Write a new row to the private repo via the GitHub token | **Dropped.** No credential to write with, by design — see "What this does not do" below |
| Delivery | 5 source files fetched individually + `npm install` at container start | **1 bundled artifact** (`tenant/entrypoint.bundle.mjs`, built by `tenant/build-bundle.mjs` via esbuild) — zero npm install, since this repo has never verified npm-registry egress from a Nosana node |

### Why an ephemeral, unfunded identity still proves something

Generating a fresh ed25519 keypair and signing with it inside the container proves the container
**executed real code** — it cannot prove custody of anything valuable, because there is nothing
valuable to hold custody of. That is the honest, narrower claim this pass makes for "boots and
identifies itself." It does NOT prove the same claim the first pass's funded tenant made (an
identity that persists and accumulates its own history) — see "What this does not do."

### Why the economic proof is a REAL match with Mac-side code, not just "plausible"

`tenant/entrypoint.mjs`'s `resolveNosPerHour` mirrors `../renew/executor.mjs`'s own survival-drive
branch (lines ~258-272) exactly: an active job's own locked-in `price` when one exists, otherwise a
live cheapest-GPU-market estimate. It then calls `computeRunwayHours`/`formatRunway` from
`../renew/survival-drive.mjs` — the literal file, bundled in, not a copy. Verified live 2026-07-25,
side by side, at the same moment:

```
$ ANICCA_HOME=$HOME/.blockrun node bin/citizen-rent --dry
[citizen-rent] balances: 0.026066471 SOL, 2.495705 NOS
[citizen-rent] survival drive: runway 0d 13.2h at 0.188945 NOS/hr — warning (...)

$ NOSANA_TREASURY_ADDRESS=F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T \
    node skills/self/shelter/nosana/tenant/entrypoint.bundle.mjs
[tenant] treasury balances: 0.026066471 SOL, 2.495705 NOS
[tenant] survival drive (reusing the literal ../renew/survival-drive.mjs): runway 0d 13.2h at
0.188945 NOS/hr — rate source: market-fallback:7AtiXMSH6R1jjBxrcYjehCkkSF7zvYWte63gwEDBcGHq
```

Identical balances, identical rate, identical runway, identical market — because it is the same
code reading the same real chain state, not a coincidence.

### What this does NOT do (read before treating this as more than it is)

- **Does not prove custody of a funded key.** The ephemeral identity is never funded. If you need
  "an agent inside a job can hold and move real money," this design does not demonstrate it — see
  "A path not taken, with evidence" below for what would.
- **Does not remember its own run count.** No snapshot-back means each incarnation is blind to
  prior incarnations of ITSELF (though not blind to Franklin's own real history, which it reads
  fresh from public chain state every time). An accepted, disclosed loss — the coordinator's own
  instruction was explicit that this is an acceptable trade for carrying no write credential.
- **Does not exercise x402 or any payment.** Not attempted in either pass.

## A path not taken, with evidence: delegated, capped spend via SPL Token's native delegate

Solana's SPL Token program has a real, native primitive for exactly "let an untrusted key spend up
to a hard cap, never more, even if it is fully compromised": the `Approve`/`ApproveChecked`
instruction. Quoted directly from Solana's own cookbook (solana.com/developers/cookbook/tokens/
approve-token-delegate, fetched live 2026-07-25):

> "Approving a delegate allows another address to transfer or burn a limited amount of tokens from
> a token account on behalf of the token account owner." … "the account stores one current
> delegate and one delegated amount at a time."

Concretely: the treasury (owner) could `approve` a short-lived delegate keypair for, say, 0.05 NOS.
That delegate — even placed inside a publicly-readable job, even fully leaked — could never move
more than the approved amount; the SPL Token program enforces the ceiling on-chain, not this code.
This is a genuinely stronger claim than the runway-match proof this pass ships ("the container can
trigger a real, capped payment" vs. "the container can read and reason about real money"). **Not
implemented here**, for two reasons: (1) it requires the TREASURY to sign a real `approve`
transaction — itself a real on-chain financial-authorization action outside this executor's
authority to perform; and (2) it is a meaningfully bigger, separately-verifiable piece of work
(delegate lifecycle, revoke logic, confirming a delegate transfer really cannot exceed the
approval even under adversarial conditions) that deserves its own pass rather than being squeezed
into this one. `tenant/fund-tenant.mjs` and `tenant/keypair.mjs` (kept, unused by the current job)
are exactly the Mac-side building blocks — key generation and a capped treasury transfer — this
future design would extend.

## What actually runs inside the job

`tenant/entrypoint.mjs` is bundled (via `tenant/build-bundle.mjs`, esbuild, at build time on this
Mac) together with `./proof.mjs`, `./public-job-state.mjs`, the literal `../renew/survival-drive.mjs`,
and `../market.mjs` (+ its own `../../spawn/lib/cloud-target.mjs` dependency) into ONE
dependency-free file, fetched from a **pinned commit** on the public `Daisuke134/life-manager` repo
and run via `node /tmp/entrypoint.bundle.mjs` inside `docker.io/library/node:20-alpine` (a public,
standard, tiny base image — no custom image published). Four things happen, in order:

1. **Boots and identifies itself** — generates a fresh ephemeral keypair, prints its address.
2. **Restores state** — Franklin's real public job history via the public jobs API, filtered by
   `NOSANA_TREASURY_ADDRESS` (a public key — the only env var this job carries besides the bundle
   URL).
3. **Does something economically real and verifiable** — reads Franklin's real treasury balance
   from public RPC, recomputes NOS/hour + runway with the literal `survival-drive.mjs`, fetches a
   live blockhash, and signs a challenge over all of it (`proof.mjs`) — unfakeable from outside the
   job because the blockhash did not exist before the job ran.
4. **Reports** — logs every step to stdout plus a final `TENANT_REPORT_JSON={...}` line, read back
   via the jobs API's `jobResult.opStates[0]` diagnostics (verified live 2026-07-25 as the reliable
   evidence channel during the earlier health-check incident) — **not** the exposed HTTP endpoint
   (never once returned 200 in four attempts across two nodes) and **not** the dead `-o/--output`
   artifact flag (`action.ts` throws `'artifact support coming soon!'` before reaching it).

## The npm-install risk, fixed by bundling

The first pass's container ran `npm install @solana/web3.js bs58 tweetnacl` at startup — a
dependency this repo has **never actually verified works** from inside a Nosana job container
(every other proven network call this project makes from inside a job is Solana RPC / the Nosana
jobs API — never the npm registry). `tenant/build-bundle.mjs` eliminates this risk entirely:
esbuild inlines all three packages plus this repo's own reused modules into one ~1.5MB
dependency-free `.mjs` file. The container's ONLY network calls are: one `fetch` for its own code,
then Solana RPC + the Nosana jobs API — calls this feature needs regardless. Rebuild + commit +
push the bundle whenever `entrypoint.mjs` or anything it imports changes:

```bash
node skills/self/shelter/nosana/tenant/build-bundle.mjs
git add -A && git commit -m "..." && git push canonical <branch>
```

A real regression was caught building this: the bundle's CLI-detection guard
(`path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)`) silently never matched when
invoked through a path containing a symlink Node's loader resolves but `path.resolve` does not
(macOS's `/var` → `/private/var`) — the script would have loaded, done nothing, and exited 0 with
zero output, indistinguishable from a job that "worked" by never actually running. Fixed by
realpath'ing both sides before comparing (see `entrypoint.mjs`'s CLI-guard comment) and caught by
actually executing the bundled artifact standalone, not just unit-testing the source.

## Commands

```bash
# Mac-side: verify the bundled entrypoint runs standalone (no network). Regular local test.
node skills/self/shelter/nosana/tenant/build-bundle.mjs
NOSANA_TREASURY_ADDRESS=F5SYUC4f5QULbEgSYb1DFCBfi74AnWE3ZaXAhqXwhZ5T \
  node skills/self/shelter/nosana/tenant/entrypoint.bundle.mjs

# Mac-side: resolve Franklin's treasury address, verify the bundle is publicly fetchable at the
# current (already-pushed) commit, build the job definition, run deploy.mjs's dry pipeline.
ANICCA_HOME=$HOME/.blockrun bin/citizen-tenant-up --dry

# Mac-side, LIVE: actually post + pay for the job. Carries NO secret of any kind.
ANICCA_HOME=$HOME/.blockrun bin/citizen-tenant-up --live
```

`bin/citizen-tenant-fund` (Mac-side, capped treasury→tenant transfer) and the persistent
`tenant/keypair.mjs` still exist and are still tested, but the current job design does not call
them — kept for the delegated-spend design above.

## What was NOT executed by this implementation pass, and why

This feature was built, unit-tested, and dry-verified against real mainnet reads by an executor
operating under a hard rule: never execute a cryptocurrency transfer or a paid on-chain action,
even when instructed to. The coordinator of this work independently verified the IPFS finding
above, is executing every live on-chain action for this feature themselves (the Jupiter swap, job
posts, and extends behind the real balances this README quotes were all run by them, not this
executor), and asked specifically for a design requiring no secret so they could run `--live`
directly. That live run — the real posted job's address, its jobs-API record, and its real
container diagnostics — is not in this repo yet; see the implementation report for the exact `--dry`
output handed off and the exact command to run it live.
