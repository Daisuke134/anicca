---
name: self/spawn-child
description: Akash self-spawn READINESS gate — deterministic check of whether this instance's Akash wallet holds enough AKT to fund a child's birth, plus the image-independent SDL template and documented funding route. Preparation only; firing (funding + deployment create) is deferred until you have actually earned enough.
metadata:
  track: A
  spec: colony spec §17-2 STEP5 / §20.1 / §20.2 / §21 / §21.1 STEP5 (2026-07-05)
  entrypoint: run.sh
  parallel_safe: true
  requires:
    bins: [bash, jq, node, curl, provider-services]
    env_optional: [AKASH_KEY_NAME, AKASH_KEYRING_BACKEND, AKASH_NODE, AKASH_CHAIN_ID, ANICCA_STATE_DIR]
---

# self/spawn-child

## Why this exists (read this before touching anything)
Every instance in this colony already has the general "birth a child" skill: `../spawn/run.sh`
(registry-live) generates a child wallet + AgentMail inbox, provisions a host (DigitalOcean or Akash),
and registers the child on the public dashboard. That skill is complete and does not need re-building.

What it does NOT do is answer one Akash-specific question that spec §20.1/§20.2 (2026-07-05, real
sandbox + real wallet) surfaced: **Akash's deployment escrow is denominated in `uact`, not `uakt`**
(AEP-76). `uact` comes from minting AKT into ACT via `../spawn/scripts/akt-treasury.sh`, and that mint
needs real AKT on hand first. On 2026-07-05 the live spawn wallet (`akash1ms7…`, key `anicca-akash`)
held only ~1.86 AKT against a real ~23+ AKT shortfall — verified by an actual on-chain query, not a
guess. Dais's explicit call that day (§21): **defer firing** — don't spend the colony's only spare
capital (Franklin's SOL→USDC) on an Akash mint today; instead **prepare the capability so a future,
richer instance can trigger it itself** (§21.1 STEP 5: "自己spawn capability... 発火は資金できてから").

This skill is that preparation. It is a narrow, read-only gate that sits in front of the Akash leg of
`../spawn/run.sh --host=akash`, plus a corrected SDL template. It never moves money.

## What this skill is NOT
- It is **not** a rewrite of `../spawn` (wallet-gen, AgentMail, telemetry, dashboard registration all
  stay there — reuse them, don't duplicate them).
- It is **not** allowed to execute a swap, a mint, a transfer, or `deployment create`. `run.sh` only ever
  runs `provider-services keys show` and `provider-services query bank balances` — both read-only.
- It does **not** decide *whether* the colony should spawn a child today, or *when* is the right moment
  beyond "funded." That is a judgment call for whichever agent invokes this skill — see below.

## When to consider running this (a heuristic, not a rule to hardcode)
Run it whenever you are evaluating whether to grow the colony via Akash and want a fast, honest answer
to "do I actually have enough AKT right now, and if not, how far off am I." Good moments: after a payday
that meaningfully increased this instance's own balance; during a periodic self-review of the colony's
capacity; when a human or peer instance asks "can we spawn on Akash yet." It is cheap and side-effect-free
to run — there is no harm in checking often. A `ready:true` result is informational, not a command: you
(the calling agent) still decide whether spawning now is the right use of that capital versus, say,
funding your own trading engines further. Don't treat NOT-YET as failure and don't treat READY as
an instruction to immediately fire — read the numbers and use judgment.

## What it gives the calling agent
```
bash run.sh
```
prints one line with the real AKT balance + gate decision JSON, and:
- **NOT-YET** (`ready:false`): exact shortfall in AKT, and the reason (`insufficient_akt`). Exit 0 — this
  is the expected, non-error state until the colony has earned more. A row is appended to the durable
  ledger (`${ANICCA_STATE_DIR:-~/.hermes/state}/spawn-child-gate.jsonl`) so the colony's funding
  trajectory over time is visible on disk, not just in this run's stdout.
- **READY** (`ready:true`): the balance covers `spawn_cost_akt + buffer_akt` (config.json). The script
  prints the funding + deploy sequence as **documentation**, not as commands it runs for you:
  1. Jupiter: SOL → USDC (Solana)
  2. Skip API 4-hop smart_relay: USDC(solana) → AKT(akashnet-2), recipient = this instance's Akash address
  3. `bash ../spawn/scripts/akt-treasury.sh` — mint ACT from AKT (off the deploy critical path)
  4. `AKASH_SDL_TEMPLATE=sdl/child.yaml bash ../spawn/scripts/deploy-akash.sh <CHILD_ID>` — create → bid
     → lease → manifest (the existing, tested, registry-live deploy path — now pointed at the
     image-independent template instead of its broken default)

You (the calling agent) choose whether to actually run steps 1-4, in what order, and whether to gate each
one on its own success — this script's job ends at telling you the truth about AKT balance vs cost.

## Files
- `run.sh` — the gate (see above). Reads `config.json`, queries the chain read-only, delegates the
  actual arithmetic to `lib/akt-cost-gate.js` (pure, unit-tested), appends one ledger row, exits 0 always.
- `config.json` — `spawn_cost_akt` (default 25, mirrors `akt-treasury.sh`'s `TREASURY_MINT_UAKT` default
  of 25,000,000 uakt, i.e. the AKT burned per ACT-mint top-up), `buffer_akt` (default 1, gas headroom for
  deployment create + lease create + send-manifest; cert publish is already done, see §20.1), plus the
  Akash key name/keyring backend and the documented funding route. Change these numbers here, not in code,
  if the real on-chain costs move.
- `sdl/child.yaml` — the image-independent boot SDL (public `node:22-bookworm` + `command`/`args` that
  clone this OSS repo and run the loop). Validated with `provider-services sdl-to-manifest` (parses to a
  real manifest — see Verify). `../spawn/scripts/deploy-akash.sh` now accepts
  `AKASH_SDL_TEMPLATE=<path>` to use this file instead of its own inline (previously broken-image)
  fallback; passing nothing still works exactly as before, now with a fixed default image too.
- `lib/akt-cost-gate.js` + `lib/__tests__/akt-cost-gate.test.js` — the pure gate function and its
  boundary-case tests (`node --test`).
- `scripts/test-spawn-child.sh` — static + faithful-fake-provider-services behavioral oracle for
  `run.sh` (NOT-YET / READY / exact-threshold boundary / fail-closed), never touches real money.

## Verify
- `node --test lib/__tests__/*.test.js` → all pass (arithmetic correctness, boundaries, invalid input).
- `bash scripts/test-spawn-child.sh` → static invariants (no tx/swap/mint/send calls anywhere in
  `run.sh`) + behavioral NOT-YET/READY/boundary/fail-closed against a fake `provider-services`.
- `provider-services sdl-to-manifest <rendered sdl/child.yaml>` → parses to a valid manifest.
- `bash run.sh` (real run, read-only) → prints the REAL current AKT balance and gate decision against
  the live `anicca-akash` wallet; appends to the durable ledger. Safe to run anytime — it can only read.

## Fail-closed
Missing `jq`/`node`/`provider-services`, an unresolvable Akash key, or an unreachable node all exit
non-zero with a clear stderr message — never a fabricated balance or a fabricated "ready." A `/tmp`-rooted
`ANICCA_STATE_DIR` is refused for the same reason `../spawn` refuses it: a lost ledger is a lost history
of the colony's funding trajectory.

## Collision
This skill edits only `skills/self/spawn-child/**`. The two additive changes it required in `../spawn`
(an `AKASH_SDL_TEMPLATE` override + a corrected RPC-endpoint selection in `deploy-akash.sh` and
`akt-treasury.sh`) are backward-compatible — default behavior when nothing is set stays the shape of the
existing "live" skill, just no longer silently broken (dead image, undialable RPC host).
