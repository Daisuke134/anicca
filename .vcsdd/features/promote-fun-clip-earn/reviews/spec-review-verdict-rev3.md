# VCSDD Phase 1c — Adversary Spec Review Verdict (RE-REVIEW of REV 3)

- Feature: `promote-fun-clip-earn`
- Spec reviewed: `.vcsdd/features/promote-fun-clip-earn/specs/spec.md` (REV 3)
- Mode: lean | Reviewer: fresh-context adversary (disk-only, zero builder context)
- **OVERALL VERDICT: FAIL** (3 / 5 dimensions FAIL — 0 critical, 3 major)

> Scope: (A) did REV 3 actually close every REV-2 finding (FIND-201..209) against the REAL files on
> disk? (B) what NEW flaws did the REV-3 rewrite introduce? Every cited file:line below was opened
> and confirmed. **All 9 REV-2 findings are closed at the spec level and verified against the actual
> lib code.** Three NEW/residual MAJOR defects remain — each can silently prevent the money-only DONE
> gate from firing or makes the no-human runtime proof non-constructible.

---

## Prior-finding closure check (verified against disk — NOT a positive summary)

| REV-2 finding | Closed? | Disk evidence confirming closure |
|---|---|---|
| FIND-201 (deriveLine drops sig/confirmed/chain → DONE unreachable) | YES (with residual) | REV3 §Solana item 1 (spec.md:46-50) mandates the exact passthrough `if(o.sig)…if(o.confirmed===true)…if(o.chain)…`, matching the real gap in `ledger.mjs:14-28`. item 2 (spec.md:51-54) generalizes `isProfitable` consistent with `ledger.mjs:43-49`. **Traced**: deriveLine output for the REQ-8 line carries `{sig,confirmed:true,chain,external:true,net>0,source"promote.fun"}` → generalized `isProfitable` → `true`. No persisted field is lost. Residual = env (FIND-301). |
| FIND-202 (two divergent recorders) | YES | REV3 §"ONE canonical recorder" (spec.md:36-40) declares the JS `record.mjs`→`ledger.mjs` path EXCLUSIVE; `video/record_earn.py` (exists at `~/anicca/skills/earn/video/record_earn.py`, confirmed via Grep) is explicitly NOT the write path (spec.md:33-34). |
| FIND-203 (wrong lib paths) | YES | spec.md:16-28 now cites `_shared/lib/{ledger,identity-guard,verify-tx,usdc}.mjs` — all confirmed present; `record.mjs:8` really imports `../../_shared/lib/ledger.mjs`; new `solana-verify.mjs` placed in `_shared/lib` beside the EVM siblings (spec.md:25). |
| FIND-204 (shadowban overclaim / unfalsifiable) | YES | REQ-6 (spec.md:114-120) now states "A direct shadowban is NOT detectable via (a)+(b)" and replaces it with a falsifiable time-bound `DEAD_ZERO_HOURS` (default 48h). Overclaim removed. |
| FIND-205 (watchdog owner undefined) | YES (with residual) | REQ-9 (spec.md:131-140) now names the owner: harness `run-skill.mjs` for wake-level `SKILL_TIMEOUT_S` (confirmed enforced at `run-skill.mjs:33,50-54`, default 120) + `run.sh` per-step `timeout`. Residual = the per-step binary (FIND-302). |
| FIND-206 (sig-dedup absent) | YES | item 5 (spec.md:74-76) specs `alreadyRecordedSig(file,sig)` pure over `readLedger` (which exists, `ledger.mjs:59-78`), gated in REQ-8 (spec.md:124) + REQ-11 (spec.md:144). Constructible. |
| FIND-207 (no regression gate on shared file) | YES | item 6 (spec.md:77-80) + verification arch (spec.md:177) mandate extending `__tests__/ledger.test.js` (exists, guards at `ledger.test.js:23-34`) with Solana cases AND re-running the FULL suite green. |
| FIND-208 (warm-state file undefined) | YES | REQ-4 (spec.md:106-110) names `~/.cloak/clip-accounts.json` `status==="ready"`, owner `ig-account-warmer`, same file `earn/clip/run.sh:22,47` reads — both lines confirmed (`ACCTS=…/.cloak/clip-accounts.json`; `if x.get("status")=="ready"`). |
| FIND-209 (batch/multi-transfer summation) | YES (with residual) | item 4 (spec.md:65-68) specs summing `post-pre` ONLY over entries `owner===wallet AND mint===USDC`, ignoring other transfers. Residual = absent-pre first-inbound case (FIND-303). |

---

## Dimension 1 — Spec Fidelity: **PASS**

The REQ↔lib mapping was traced end-to-end against the real code and is faithful:
- REQ-8's persisted line (spec.md:124-130) → `deriveLine` (with the mandated `sig`/`confirmed`/`chain`
  passthrough, spec.md:46-50) → the generalized `isProfitable` (spec.md:51-54) yields `true`. Verified
  field-by-field against `ledger.mjs:11-49`; no field needed by the classifier is dropped.
- Exactly ONE recorder is authoritative (`record.mjs`/`ledger.mjs`), and the Python recorder is
  explicitly excluded from the write path (spec.md:33-40).
- "promote.fun"/"clip-promote" match NO `FORBIDDEN_EARN_SOURCES` pattern (`identity-guard.mjs:48-51`),
  so adding them to `ALLOWED_EARN_SOURCES` (`identity-guard.mjs:30-44`) creates no collision.
Evidence reviewed: spec.md:16-59,124-130; `ledger.mjs:11-49`; `record.mjs:8,16,19`; `identity-guard.mjs:30-51`.

## Dimension 2 — Edge Cases: **FAIL**

**FIND-303 (MAJOR, edge_case). `usdcDeltaForSig` does not specify the absent-pre-balance case — which is EXACTLY the acceptance scenario (first inbound creates the ATA).**
The spec itself states the wallet "has 0 SOL + no USDC ATA today" and that the "first inbound withdraw
creates it" (spec.md:71,189). Therefore the FIRST (and, for the acceptance gate, the only required)
USDC inflow is the ATA-creating transaction — its `meta.preTokenBalances` will contain NO entry for our
ATA at all. REQ §item 4 says "sum `post-pre` ONLY over entries where `owner === wallet`" (spec.md:65-68)
but never states that a missing pre-entry MUST be treated as 0. A builder pairing pre/post by
`accountIndex` (the common Solana pattern) will find no matching pre entry and compute a wrong/zero delta
→ `usdcDeltaForSig > 0` fails → DONE never fires on the very transaction that is supposed to satisfy it.
The spec is meticulous about the symmetric case for `usdcBalance` ("returns 0 when the ATA does not
exist", spec.md:70-71) but silent about it for `usdcDeltaForSig`, where it matters most.
Evidence: spec.md:65-68,70-71,189.

## Dimension 3 — Implementation Correctness: **FAIL**

**FIND-301 (MAJOR, requirement_mismatch). The mandated "MINIMAL env" for the RECORD wake is contradicted by the named canonical harness and its scrubbing duty is assigned to no component — reproducing the silent-DONE-block failure class.**
REQ §item 3 (spec.md:56-59) says the RECORD wake "MUST run with a MINIMAL env (no
`*GMAIL*`/`GOOGLE_LOGIN`/`COMPOSIO`/`TELEGRAM`/`USER_*` vars) so `findUserPIIEnv` passes." But:
1. `record.mjs:19` calls `assertOwnIdentityOnly(line)` with NO `opts.env`, so it reads `process.env`
   (`identity-guard.mjs:86-88` → `findUserPIIEnv(process.env)`, `:54-58`). If any PII var is present it
   THROWS and the line is never recorded → DONE silently never fires.
2. The named spawn harness (REQ-12, spec.md:147) `run-skill.mjs` builds the child env via
   `scrubPrivateKeys(process.env)` (`run-skill.mjs:35,80-101`), and `scrubPrivateKeys`
   (`env-filter.mjs:15,28-37`) strips ONLY `*_WALLET_KEY/_PRIVATE_KEY/_PRIV_KEY` — it does NOT strip any
   PII pattern. So the harness FORWARDS `GOOGLE_LOGIN/COMPOSIO/*GMAIL*/TELEGRAM/USER_*` straight to
   `run.sh`, which by default passes them to `node record.mjs`.
3. The spec assigns the PII-scrubbing duty to no component: it never says `run.sh` SHALL invoke
   `record.mjs` under `env -i`/an explicit allowlist. A builder who implements `run.sh` as a plain
   `node lib/record.mjs '<json>'` (the obvious reading) inherits the PII env and hits the throw.
This is the same "DONE can never fire as written" class the original FIND-201 was about, just relocated
from `deriveLine` to the env. The minimal-env requirement does NOT conflict with the wallet/RPC env
(`WALLET`/`SOLANA_RPC_URL` match no PII pattern), so the fix is feasible — but the spec must mandate WHO
strips PII before `record.mjs`, and reconcile it with the harness that currently does not.
Evidence: spec.md:56-59,124-130,147; `record.mjs:19`; `identity-guard.mjs:54-58,86-97`; `env-filter.mjs:15,28-37`; `run-skill.mjs:35,80-101`.

**FIND-303 (MAJOR)** — re-applies: the delta computation for the acceptance transaction is underspecified. See Dimension 2.

## Dimension 4 — Structural Integrity: **PASS**

- The Solana adapter is placed in `_shared/lib/solana-verify.mjs` beside the EVM siblings
  `verify-tx.mjs`/`usdc.mjs` (confirmed present in `_shared/lib`), resolving the prior placement defect.
- ONE recorder; the new slot `skills/earn/clip-promote/` mirrors the structure of `skills/earn/video/`,
  and its `decide.py` mirrors the genuinely PURE `earn/video/decide.py` (confirmed pure: no I/O, decision
  only, `decide.py:23-43`).
- The shared-file blast radius now has a mandated regression gate (spec.md:77-80,177).
- Non-blocking note (not a finding): `run-skill.mjs:82` special-cases env only for `slot==='earn'`; a
  `slot==='earn/clip-promote'` wake falls to the generic branch (`run-skill.mjs:101`) and is NOT handed
  `EARN_MODE/EARN_STRATEGY/EARN_LEDGER`. This is an integration detail the slot's own `run.sh` can absorb
  (the shared ledger path is record.mjs's `DEFAULT_LEDGER`), so it does not block the spec gate — but the
  builder should be aware the harness will not inject earn-slot env for this slot name.
Evidence reviewed: spec.md:25,29-30,77-80; `earn/video/decide.py:23-43`; `run-skill.mjs:82,101,109-115`.

## Dimension 5 — Verification Readiness: **FAIL**

**FIND-302 (MAJOR, verification_tool_mismatch). REQ-9's per-step no-human watchdog test depends on a `/opt/homebrew/bin/timeout` binary that this Homebrew/macOS install almost certainly ships as `gtimeout`; the "constructible test" as literally written (`timeout 1 sleep 5`) may fail command-not-found.**
REQ-9 (spec.md:135,138-140) asserts "`/opt/homebrew/bin/timeout` present" and gives the constructible
test `timeout 1 sleep 5` → 124 → `blocked:human:*` + exit 0. On disk, coreutils installs the
GNU-prefixed binary: `/opt/homebrew/Cellar/coreutils/9.10/bin/gtimeout` (man pages for both `gtimeout.1`
and `timeout.1` exist, but the BINARY is `gtimeout`). macOS base has no `timeout` at all. A bare
`timeout` resolves only if `$(brew --prefix coreutils)/libexec/gnubin` is on PATH — which the spec does
not establish. If it is not, every `timeout "$STEP_DEADLINE_S" <cmd>` wrapper and the watchdog test fail
with command-not-found, leaving the runtime half of the no-human INVARIANT unprovable.
Honest evidence caveat: I could not directly list `/opt/homebrew/bin` (Glob failed to enumerate that
dir's symlinks — even `python3`, which is definitely used, did not appear), so I cannot prove `timeout`
is absent; but the coreutils g-prefix convention makes the hard path claim unverified and likely wrong.
The spec must either use `gtimeout` / a verified absolute path or require a build-time check.
Evidence: spec.md:135,138-140; `/opt/homebrew/Cellar/coreutils/9.10/bin/gtimeout` (no bare `timeout` binary found).

**FIND-301 (MAJOR)** — re-applies as a verification defect: the DONE acceptance check
(`record.mjs`-persisted line satisfies `isProfitable`, spec.md:172-174) is NOT runnable end-to-end if the
wake's `process.env` carries PII, because `assertOwnIdentityOnly` throws BEFORE the append. A maker≠checker
running the wake under the harness-supplied (PII-laden) env gets a throw, not DONE. See Dimension 3.

**FIND-303 (MAJOR)** — re-applies: the DONE verification `usdcDeltaForSig(sig,wallet) > 0` (spec.md:172)
is not runnable for the first-inbound/ATA-creating tx without the absent-pre rule. See Dimension 2.

---

## MUST-FIX before building (prioritized)

1. **[FIND-301, MAJOR] Assign the PII-scrubbing duty and reconcile it with the harness.** Add a
   requirement that `run.sh` invokes `record.mjs` under a MINIMAL env (`env -i` + only
   `WALLET`/`SOLANA_RPC_URL`/ledger path), since the named harness `run-skill.mjs` (`env-filter.mjs`)
   strips private keys ONLY, not PII. Add a test: a wake whose `process.env` contains `COMPOSIO_*`/
   `GOOGLE_LOGIN`/`USER_*` still records the Solana line (i.e. `record.mjs` runs under a scrubbed env)
   and `isProfitable(persistedLine) === true`.
2. **[FIND-303, MAJOR] Specify the absent-pre-balance rule for `usdcDeltaForSig`.** State that an ATA
   absent from `preTokenBalances` contributes pre = 0 (sum post for `owner===wallet AND mint===USDC`,
   minus sum pre for the same, treating missing as 0). Add a test fixture = a first-inbound tx whose
   `preTokenBalances` has NO entry for our ATA → delta equals the full post amount.
3. **[FIND-302, MAJOR] Fix the per-step timeout binary.** Use `gtimeout` (or a verified absolute path /
   build-time `command -v` check) instead of the hard `/opt/homebrew/bin/timeout` claim, and make the
   `blocked:human:*` test reference whatever binary actually exists on this host.

(No critical findings this round. All 9 REV-2 findings verified closed against the real lib code; the
three MAJOR items above are residual/new and must close before Phase 2.)
