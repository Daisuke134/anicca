# anicca-spawn-identity-resolution-fix — Behavioral Specification (VCSDD Phase 1a, lean mode)

**Feature**: `anicca-spawn-identity-resolution-fix` · **Mode**: lean (single, root-caused bash bug in a
production skill wrapper; a real reproducible incident, not new scope)
**Ground truth**: production incident observed on Franklin's real `ai.anicca.franklin-loop` launchd
daemon (`~/anicca/runtime/anicca-daemon.sh` → `~/anicca/runtime/loop/index.mjs`), 2026-07-08. A
one-time, human-authorized forced-tool-choice test made the loop pick the `self/spawn` slot for real.
The money gate (`decideColonySpawn`, `~/anicca/skills/self/spawn/lib/treasury-gate.mjs`) correctly
evaluated `eligible:true` (`colonySurplusUsd:9.867619878845 > spawnThresholdUsd:7.5`) — that gate is
NOT the bug. The subsequent real spawn attempt then failed closed with:
```
{"status":"failed","childId":null,"error":"no resolvable per-instance identity (ANICCA_HOME/HOME) -- cannot determine drivingCitizenWallet"}
```
No money moved (fail-closed, as designed) — this feature fixes the identity-resolution defect that
caused the fail-closed path to trigger when it should not have.

## Root cause (definitively confirmed by direct reproduction of the exact real subprocess chain)

`~/anicca/skills/self/spawn/run.sh` (invoked by `index.mjs`'s `runSkillWithKillRef` via
`spawn(skillPath, [], {env: childEnv})`, where `childEnv` correctly carries the caller's real
per-instance `ANICCA_HOME` — confirmed correct end to end: launchd plist → `process.env` →
`buildSkillEnv`'s `scrub(process.env)` spread → child env) has this preamble (before the fix):
```bash
set -a
[ -f "$HOME/.hermes/.env" ]   && . "$HOME/.hermes/.env"
[ -f "$HOME/.openclaw/.env" ] && . "$HOME/.openclaw/.env"
set +a
```
`$HOME` is the real, OS-level home directory (`/Users/anicca`), which is **shared by every instance
on this machine** (Franklin, the automaton, and any future spawned child all run as the same macOS
user) — it is NOT per-instance the way `ANICCA_HOME` is. `$HOME/.openclaw/.env` is the OpenClaw
automaton's own shared secrets file (contains Akash keys, API keys shared across skills, etc.) and —
confirmed by direct inspection — it unconditionally sets its OWN `ANICCA_HOME=/Users/anicca/.openclaw`
at line 354. Because `set -a` (allexport) is active while this file is sourced, that assignment
silently **overwrites** the caller's correct `ANICCA_HOME` (e.g. Franklin's `/Users/anicca/.blockrun`)
with the automaton's home, for the rest of the script and for the `wake-gate.mjs` process it execs.

`wake-gate.mjs`'s `defaultResolveDrivingCitizen(env)` then calls
`resolveEvmPrivateKey({env})`/`resolveSolanaSecret({env})`
(`~/anicca/skills/earn/lib/resolve-identity.mjs`), both of which compute
`effectiveHome = env.ANICCA_HOME` (now wrongly `/Users/anicca/.openclaw`) and look for
`/Users/anicca/.openclaw/.automaton/wallet.json` / `.../solana.json` — neither exists (confirmed via
direct filesystem check) — then fall back to the legacy path, which is gated on
`effectiveHome === path.join(HOME, '.anicca')` / `path.join(HOME, '.blockrun')`; since the polluted
`effectiveHome` (`/Users/anicca/.openclaw`) matches neither, both resolvers correctly (per their own
fail-closed contract) return `null`. `defaultResolveDrivingCitizen` returns `null` → the exact observed
error. **The resolvers themselves are correct and were never the bug** — `run.sh` handed them a
poisoned `ANICCA_HOME` before they ever ran.

This is a **deterministic, 100%-reproducible bug**, not a transient/race condition: it fires on every
real (non-`--dry-run`) invocation of `self/spawn` on any machine where `$HOME/.openclaw/.env` exists
and sets `ANICCA_HOME` (true for every instance colocated with the OpenClaw automaton on this Mac
Mini). It was masked in prior verification because (a) in-process unit tests call
`resolveEvmPrivateKey`/`resolveSolanaSecret` directly with a correct, hand-built env (never exercising
`run.sh`'s bash preamble), and (b) `--dry-run` invocations return before identity resolution is ever
reached (`wake-gate.mjs` line 173: `if (dryRun || !decisionCore.eligible) return`).

## REQ-001 — `run.sh` MUST NOT let shared per-user secrets files override the caller's per-instance `ANICCA_HOME`

`~/anicca/skills/self/spawn/run.sh` MUST preserve the exact `ANICCA_HOME` value it was invoked with
(the caller's per-instance identity, e.g. Franklin's `/Users/anicca/.blockrun`) across the sourcing of
`$HOME/.hermes/.env` and `$HOME/.openclaw/.env`, even when either of those files defines its own
`ANICCA_HOME`. Every other variable those files define (Akash signing key, API keys, etc.) MUST still
be exported to the child process exactly as before — this is the entire reason those files are
sourced at all; REQ-001 is about ONE variable's precedence, not about no longer reading those files.

- **Edge case — caller invoked with no `ANICCA_HOME` set at all** (not the production path — `index.mjs`
  always sets it — but a defensive edge case for any other caller, e.g. a manual shell invocation):
  if the CALLER did not set `ANICCA_HOME`, this requirement does not apply — whatever
  `$HOME/.openclaw/.env`/`$HOME/.hermes/.env` set (or leave unset) passes through unchanged, matching
  pre-fix behavior for that case.
- **Edge case — neither `.hermes/.env` nor `.openclaw/.env` exists**: the caller's `ANICCA_HOME` was
  never at risk; behavior is a no-op (identical before/after the fix).

## REQ-002 — Regression test MUST exercise the REAL subprocess chain, not just the in-process resolver

The existing `resolveEvmPrivateKey`/`resolveSolanaSecret` unit tests (verified passing in isolation
before this fix, given a correct env) do not cover this bug because the bug is entirely inside
`run.sh`'s bash preamble, not in any `.mjs` module. A regression test MUST invoke the real,
unmodified `run.sh` file as a real subprocess (matching `index.mjs`'s own `spawn(skillPath, [],
{env})` call shape) with a fixture `HOME` whose `.openclaw/.env` **and** `.hermes/.env` each
independently set a conflicting `ANICCA_HOME` (mirroring the real production conflict — both files
are sourced by the same vulnerable preamble, so both must be independently exercised, not just
whichever one happens to be populated on today's machine), and assert (a) the caller's `ANICCA_HOME`
is what the final child process actually receives in both cases, and (b) every OTHER variable each
file defines still flows through unmodified (the fix must not regress the original reason these files
are sourced).

## REQ-003 — The same vulnerable preamble pattern MUST be fixed everywhere it is duplicated, not just in self/spawn

(Added in fresh-adversary iteration 3, FIND-001 — blocking.) `~/anicca/skills/self/spawn/run.sh` is
not the only script with this exact preamble. `~/anicca/skills/economy/lending/run.sh`'s own header
comment explicitly documents that it "mirrors self/spawn/run.sh's own already-proven shape exactly" —
it is a literal copy of the vulnerable pattern, execing its own `scripts/wake-gate.mjs`.
`~/anicca/skills/self/spawn-child/run.sh` also contains the byte-identical preamble. Neither of these
two currently reads `ANICCA_HOME` downstream (confirmed by trace: `economy/lending`'s wake-gate.mjs
never imports `resolve-identity.mjs` or reads `env.ANICCA_HOME`; its `CITIZENS_REGISTRY_PATH` resolves
via `HOME`, not `ANICCA_HOME`; `spawn-child`'s run.sh only queries an Akash balance and never touches
`ANICCA_HOME` either) — so this bug is currently *dormant*, not actively exploited, in these two
files. It MUST still be fixed in both, identically to REQ-001's fix, because: (a) the vulnerability
class is "any script with this preamble pattern," not "this one specific script," and leaving
duplicates unpatched contradicts this spec's own root-cause framing; (b) `economy/lending`'s own
header comment already asserts parity with `self/spawn/run.sh` — leaving the fix un-mirrored breaks
that documented invariant; (c) it is a zero-risk, already-proven-safe change (no new logic, purely the
same save/restore bookkeeping) with no proportionate reason to leave latent. Both files' own existing
test suites (economy/lending: 131 tests; self/spawn-child: 13 tests) MUST still pass unmodified after
this fix.
- `capafy-loop/loop.sh` and `life-manager-loop/loop.sh` also source `~/.openclaw/.env` under `set -a`,
  but are OUT OF SCOPE: they are the OpenClaw automaton's OWN top-level daemon loops (not per-instance
  skill invocations dispatched via `index.mjs`'s `buildSkillEnv`), so `~/.openclaw/.env`'s own
  `ANICCA_HOME` is genuinely the correct value for them — there is no caller identity to preserve.

## REQ-004 — The fix MUST be a single shared implementation, never hand-copied per script

(Added in fresh-adversary iteration 4, FIND-004 — blocking structural finding, which directly
predicted and then found FIND-001's own newly-discovered 4th vulnerable instance in the SAME
iteration: `~/anicca/skills/earn/video/run.sh`.) Hand-copying REQ-001's fix into each affected
`run.sh` is itself the defect class that let one duplicate slip through in iteration 3 and a second
slip through in iteration 4 — every additional file found by a fresh adversary is evidence the
audit-by-grep approach does not converge. The fix MUST instead live in exactly ONE file,
`~/anicca/skills/_shared/lib/load-instance-env.sh` (a sourced, not executed, bash snippet), which
every affected `run.sh` sources via `. "$SKILL_DIR/../../_shared/lib/load-instance-env.sh"` (or the
equivalent path expression for its own directory depth) instead of re-implementing the
save/source/restore logic inline. This makes REQ-001/003's "identical fix in every duplicate" claim
true **by construction** (one implementation, N call sites) rather than by manual re-synchronization
that a future editor could silently forget.

### Precise scope criterion (finalized after iteration 7 — read this before the audit table)

Iterations 4 and 5 both found "one more file" with the vulnerable STRING PATTERN via open-ended
repo-wide grep (`grep -rl "HOME/.openclaw/.env"` and variants) — this process does not converge,
because the pattern also appears in dozens of unrelated standalone scripts (marketing-automation
CLIs, single-purpose launchd daemons, product-specific tooling) that were never part of the
multi-instance colony dispatch model this bug actually lives in. Open-ended pattern-grepping the
whole repo is the WRONG closure criterion. The RIGHT, closed, falsifiable criterion is:

> A file is in scope for this bug if and only if it is reachable from a `registry.json` slot with
> `"status": "live"` via that slot's real dispatch chain — either (a) it IS the slot's literal
> `entrypoint`, itself started by `index.mjs`'s `runSkillWithKillRef`/`buildSkillEnv` with the real
> caller's `ANICCA_HOME`, or (b) it is reached FROM that entrypoint through any `source`/`.`, `exec`,
> or plain `bash <script>` subprocess fork the entrypoint (or any script it in turn reaches,
> transitively) performs — because environment variables, including `ANICCA_HOME`, are inherited by a
> child process across a plain fork+exec exactly as they are across `exec` (process-image
> replacement); the OS distinction between the two does not create a trust boundary. In both (a) and
> (b), the same live, per-instance-dispatched process is the one whose `ANICCA_HOME` a reached
> script's own unguarded env-load could clobber. A standalone launchd daemon, a marketing-automation
> cron script, or a product-specific CLI is in scope ONLY if it is itself reached via (a) or (b) from
> some live slot; if it is never reached that way, it always runs in exactly ONE fixed context (its
> own dedicated `.plist`, or a human/cron invocation with one unchanging `ANICCA_HOME`/no
> `ANICCA_HOME` at all) — there is no "caller" whose identity could ever be clobbered, so the
> vulnerable string pattern existing there is not an instance of THIS bug, however desirable it might
> be to clean up as separate repo hygiene. "Not itself a `registry.json` slot" is NOT, by itself, a
> valid reason to call a file out of scope — only non-reachability via (a)/(b) is (iteration-7
> correction, FIND-002: `faceless-money-factory/scripts/run-daily.sh` was wrongly dismissed on
> registry-slot-membership alone despite being reachable via (b) from `earn/video`).

This criterion is closed and exhaustively checkable: `registry.json`'s `slots` object is a finite,
enumerable list (20 entries at the time of this audit). Every one of them was checked directly
against its declared `dir`/`entrypoint`.

### Complete, closed audit — every `registry.json` live slot's real entrypoint script

`registry.json`'s `slots` object has exactly 20 entries; every one is listed below (`declared`-status
slots that share a `live` slot's same `dir` inherit that slot's disposition — e.g. `earn/audit` and
`earn/_probe` are `declared`, not `live`, and out of scope by the registry's own status field).

| Slot | `dir` | Vulnerable pattern? | ANICCA_HOME-relevant? | Disposition |
|---|---|---|---|---|
| `self/spawn` | `skills/self/spawn` | yes (was) | yes — actively exploited (this incident) | **FIXED** (REQ-001) — sources the shared helper |
| `self/spawn-child` | `skills/self/spawn-child` | yes (was) | dormant today | **FIXED** (REQ-003) — sources the shared helper |
| `economy/lending` | `skills/economy/lending` | yes (was) | dormant today | **FIXED** (REQ-003) — sources the shared helper |
| `earn/video` | `skills/earn/video` | yes (was) | dormant today | **FIXED** (iteration 4, FIND-001) — `run.sh` itself now sources the shared helper. CORRECTED iteration 7 (FIND-002): `run.sh`'s own S3_post transition (`run.sh:128,176`) also forks a `bash` subprocess into `$HOME/.claude/skills/faceless-money-factory/scripts/run-daily.sh` (byte-identical OSS mirror at `~/anicca/skills/faceless-money-factory/scripts/run-daily.sh`) — reachable per criterion (b) above (plain `bash <script>` subprocess fork, not `exec`, but the child still inherits `run.sh`'s environment including `ANICCA_HOME`). That file's own preamble was unguarded (`set -a; . "$HOME/.openclaw/.env" 2>/dev/null \|\| true; set +a`, no save/restore). **Both copies now FIXED** (inline `_AH="${ANICCA_HOME:-}"` save/restore, functionally identical to the shared helper since `~/.claude/skills` has no `_shared/lib/` to source from) |
| `report` | `skills/report`, entrypoint `anicca-report.sh` (registry's own explicit `entrypoint` field — NOT the default `run.sh` convention) | no | live slot, no vulnerable pattern in the real entrypoint | Not applicable — clean |
| `earn` / `yield` / `hl_trade` / `x402_sell` / `token_launch` (legacy fat slot, all 5 share `dir: skills/earn`, entrypoint `run.sh`) | `skills/earn` | **no** — uses a named `EARN_ALLOW` allowlist (`case " $EARN_ALLOW " in *" $k "*) export ...`), never blanket `set -a` | yes, and genuinely reads `ANICCA_HOME` downstream (`node lib/resolve-identity.mjs evm`) | Not vulnerable — already uses a strictly safer named-allowlist pattern (its own header documents a PRIOR, unrelated identity-leak incident it already fixed this way). `ANICCA_HOME` is not in `EARN_ALLOW`, so it can never be overwritten from `.openclaw/.env` in the first place |
| `self/issue-dev` | `skills/self/issue-dev` | no | — | Not applicable — clean |
| `self/coordinate` | `skills/self/coordinate` | no | — | Not applicable — clean |
| `economy/gig` | `skills/economy/gig` | technically yes (`set -a; source "$GIG_ENV"; set +a`) | genuinely reads `ANICCA_HOME` downstream (documented in its own header) | Not vulnerable — `$GIG_ENV` resolves to `$HOME/.anicca-signing/gig-board/.env`, a DIFFERENT, dedicated custody-key file (confirmed by direct read: contains no `ANICCA_HOME` line) — never `$HOME/.openclaw/.env` |
| `economy/ubi` | `skills/economy/ubi` | no | — | Not applicable — clean. (Distinct from `skills/ubi/ubi-watcher-daemon.sh`, a separate standalone launchd daemon at a DIFFERENT path — see out-of-scope table below.) |
| `cook` | `skills/cook` | no | — | Not applicable — clean |
| `earn/clip` | `skills/earn/clip`, entrypoint `run.sh` | no | — | Not applicable — clean. (This slot's own `run.sh` has no vulnerable preamble. Note: `producer.sh` in the same directory IS reachable in a live per-instance-dispatched process via the `earn/clip-producer` slot's exec-chain — corrected below, iteration 6.) |
| `earn/clip-producer` | `skills/earn/clip-producer`, entrypoint `run.sh` → `exec bash ../clip/producer.sh` | **yes (via exec-chain)** — CORRECTED iteration 6 (FIND-001) | reachable: `clip-producer/run.sh:19` does `exec bash '.../clip/producer.sh'`, replacing the process image in place, so `producer.sh`'s preamble ran INSIDE the live process `index.mjs` started with the caller's real `ANICCA_HOME`. The iteration-5 audit missed this because it never traced the `exec` chain. Dormant (nothing under `skills/earn/clip/` reads `ANICCA_HOME` today) but reachable — REQ-004's criterion is reachability, not current exploitation. | **FIXED** — `producer.sh` now routes its env-load through `skills/_shared/lib/load-instance-env.sh` (identical to the 4 other fixed call sites), preserving the caller's `ANICCA_HOME`. This also closes the residual exposure of its dependents `clip-promote/run.sh` and `clip/launchd/ai.anicca.clip-producer.plist`. |
| `earn/audit` (`declared`, not `live`) | `skills/earn/audit` | — | — | Out of scope — not a live slot |
| `earn/_probe` (`declared`, no `dir`) | — | — | — | Out of scope — not a live slot, no directory |
| `earn/sol-trade` | `skills/earn/sol-trade` | no — resolves identity via an explicit `ANICCA_HOME="$HOME/.blockrun"` override passed directly to `node`, never sources `.openclaw/.env` | n/a | Not vulnerable — different, already-safe mechanism |
| `earn/polymarket-trade` | `skills/earn/polymarket-trade` | no — reads `ANICCA_HOME` only if ALREADY set in its own inherited environment (extensive header comments show this was a deliberate, considered design against exactly this risk class); never sources `.openclaw/.env` | n/a | Not vulnerable — different, already-safe, deliberately-designed mechanism |

This is a closed enumeration (20/20 registry slots checked) — not an open-ended repo grep. Every
`live` slot's real entrypoint, AND every script transitively reached from it via `source`/`exec`/
`bash` subprocess fork (criterion (b) above), is either fixed or independently confirmed to use a
different, already-safe mechanism. Iteration 7 (FIND-002) re-traced every live slot's full
transitive dispatch chain (not just its literal entrypoint file) and found exactly one additional
reachable, unfixed file — `faceless-money-factory/scripts/run-daily.sh`, reached via `earn/video`'s
`bash` subprocess fork — now fixed (see the `earn/video` row above) and moved out of the out-of-scope
table below, where it had been incorrectly parked on "not a registry.json slot" reasoning that
criterion (b) explicitly rejects. No further reachable-and-unfixed file was found in that re-trace
(see the out-of-scope table's per-row reachability reasoning below, and the negative-existence checks
recorded in this feature's iteration-7 evidence).

### Explicitly out of scope (verified NOT reachable from any live slot's dispatch chain, criterion (a)/(b) above)

These files contain the same string pattern but fail criterion (a)/(b) above: for each, iteration 7
directly checked (by tracing every live slot's real entrypoint for `source`/`.`/`exec`/`bash <file>`
references) that no live slot's dispatch chain ever reaches it — so, regardless of whether it is or
isn't itself a `registry.json` slot, it can never be handed a caller's `ANICCA_HOME` via THIS bug's
dispatch path. "Not itself a registry.json slot" is cited below only as descriptive context, never as
the reason for the disposition — the reason is always the reachability check itself (each row also
records whether the file even reads `ANICCA_HOME`, as a second, independent confirmation):

| File | Why it is out of scope (reachability check + ANICCA_HOME consumption) |
|---|---|
| `earn/clip-promote/run.sh`, `earn/clip-promote/clip-promote-cli.sh` | Checked: no live slot (`earn/clip`, `earn/clip-producer`, `earn/video`, or any other) `source`s/`exec`s/`bash`-forks into `clip-promote/`; it is triggered only by its own separate cron/CLI. Also, independently: `clip-promote/run.sh` has zero `ANICCA_HOME` references — even if reached, there is nothing to clobber. Standalone marketing-automation script for one fixed IG/TikTok account (`ANICCA_INSTANCE=clip-promote` tag), unrelated to the colony's `ANICCA_HOME` identity system |
| `earn/clip/clip-cli.sh`, `earn/clip/launchd/ai.anicca.clip-producer.plist` | Checked: neither is `source`d/`exec`d/`bash`-forked FROM any live slot's entrypoint — each is itself a separate trigger (CLI wrapper / dedicated launchd job) that in turn invokes a live slot's `run.sh`, not the reverse. (`earn/clip/producer.sh` itself is NOT in this table — it IS reachable via `earn/clip-producer`'s `exec` chain and is listed as **FIXED** in the audit table above; do not re-classify it here) |
| `earn/x402-sell/serve-mainnet-boot.sh` | Checked: `earn/run.sh` (the `x402_sell` live slot's real entrypoint) contains zero references to `serve-mainnet-boot.sh`. Dedicated `KeepAlive` launchd daemon for ONE fixed x402 research-seller process (`payTo` hardcoded to the founder wallet) — triggered by its own `.plist`, never registry-dispatched |
| `earn/sol-funding-daemon.sh` | Checked: `earn/sol-trade/run.sh` (the `earn/sol-trade` live slot's real entrypoint) contains zero references to `sol-funding-daemon.sh`. Has its own dedicated launchd job (`com.anicca.sol-funding.plist`) — standalone, fixed-purpose daemon |
| `ubi/ubi-watcher-daemon.sh` (at `skills/ubi/`, distinct from the live `economy/ubi` slot at `skills/economy/ubi/run.sh`) | Has its own dedicated launchd job (`com.anicca.ubi-watcher.plist`) — standalone daemon, not reached from `economy/ubi/run.sh`'s dispatch chain |
| `report/loop-report.sh`, `report/daily-nl-report.mjs`, `report/test-loop-report.sh` | Checked: `report/anicca-report.sh` (the `report` live slot's real, registry-declared `entrypoint`) contains zero references to `loop-report.sh`. `loop-report.sh` is instead called BY the non-live-slot CLI wrappers (`earn/video/video-cli.sh`, `earn/clip/clip-cli.sh`, `earn/clip-promote/clip-promote-cli.sh`) — the reverse direction, so it is never reached FROM a live slot. Also has zero `ANICCA_HOME` references of its own |
| `_shared/send-telegram.sh`, `_shared/credential-restore.sh` | Checked: zero references from any live slot's directory tree. Also has zero `ANICCA_HOME` references of its own — a shared utility with no identity dependency to clobber |
| `earn/video/video-cli.sh`, `earn/clip-promote/clip-promote-cli.sh` (STARTUP cron-prompt text) | A CLI wrapper that CREATES a cron job whose natural-language prompt text later instructs an agent to run `set -a; . ~/.openclaw/.env; set +a` before invoking the live slot's `run.sh` — but this is prompt text for a separate LLM-driven agent turn, not a `source`/`exec`/`bash <file>` edge in `run.sh`'s own dispatch chain (`run.sh` itself is fixed, above, and criterion (b) is about file-level subprocess forks, not natural-language instructions read by an agent across separate tool-call turns) |
| `self/capafy-loop/{loop.sh,capafy-loop-cli.sh}`, `self/life-manager-loop/{loop.sh,life-manager-loop-cli.sh}` | Checked: zero references from any live slot's directory tree. The OpenClaw automaton's OWN top-level daemon loops (not per-instance skill invocations) — `.openclaw/.env`'s own `ANICCA_HOME` is genuinely correct for them |
| `anicca-life-manager/scripts/run.sh`, `anicca-life-manager/scripts/morning_report.sh` | Checked: zero references from any live slot's directory tree — invoked directly by its own dedicated OpenClaw cron job (`b2bf06ee`), a fixed context. Independently: `run.sh` never reads `ANICCA_HOME` at all (its `SKILL` path is hardcoded to `$HOME/.openclaw/skills/anicca-life-manager`); `morning_report.sh` uses the ALREADY-SAFE pattern this feature's own fix generalizes — it resolves `ANICCA_HOME` FIRST (`"${ANICCA_HOME:-$HOME/.openclaw}"`) and only then sources `"$ANICCA_HOME/.env"` (the identity's OWN env file at the already-resolved path), never `$HOME/.openclaw/.env` unconditionally, so there is no shared file to clobber it FROM |
| `runtime/anicca-daemon.sh`, `scripts/fuel-usdc.sh`, `services/x402-worker/deploy.sh`, `uninstall.sh` | Top-level repo/infra scripts, not skill entrypoints and not reached from any live slot's dispatch chain |

**Scope decision (final, after 7 fresh-adversary iterations):** the criterion above is deliberately
narrower than "every file containing this string anywhere in the repo," because that criterion has no
natural stopping point in a 500+ file monorepo and does not correspond to an actual reachable bug (a
script that is never reached from any live slot's dispatch chain cannot receive a "wrong" identity via
THIS bug). It is, however, exactly as WIDE as genuine reachability — including transitive `bash`
subprocess forks, not just literal entrypoints or `exec` chains, per the iteration-7 correction above.
If broader repo-wide hygiene (eliminating the pattern from standalone daemons/CLIs too, purely for
consistency rather than because they are exploitable) is wanted, it should be a SEPARATE, dedicated
follow-up feature — continuing to fold new greps into this one does not converge and is disproportionate
to a lean-mode single-incident fix.

## Non-functional / safety constraints

- The fix MUST NOT touch `wake-gate.mjs`, `resolve-identity.mjs`, or `index.mjs` — all three are
  independently confirmed correct; changing them would be treating a symptom, not the cause (and would
  violate the "understand root cause before fixing" discipline).
- The fix MUST NOT be verified by triggering a real spawn attempt against the live Franklin daemon —
  all verification in this feature is either (a) a safe, zero-side-effect subprocess reproduction using
  a stand-in `node` binary and a throwaway identity-probe script (scratchpad only, never committed), or
  (b) the permanent regression test (REQ-002), which also performs zero real side effects (no
  `citizens.json` write, no `executeSpawnAttempt` call — it replaces `wake-gate.mjs` with a fake `node`
  shim that only echoes env for the duration of the test).
- Existing spawn test suite (204 tests, `node --test 'skills/self/spawn/lib/__tests__/**/*.test.mjs'
  'skills/self/spawn/lib/__tests__/**/*.test.js'`) MUST still pass unmodified — this fix adds exactly
  one new test file (2 test cases) and touches no existing test or production `.mjs` module. Full-suite
  evidence (206/206 green) is persisted at `evidence/full-suite-regression.log`.
