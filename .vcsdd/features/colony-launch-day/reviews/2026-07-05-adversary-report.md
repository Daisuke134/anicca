# 2026-07-05 fresh-context adversary report — Anicca colony launch-day changes

Reviewer = fresh-context VCSDD adversary (no builder conversation context). All findings below are
based on disk-read evidence and live command execution performed in this review session only.
Read-only discipline was maintained except: (a) `bash skills/self/telemetry-collect.sh` (mother repo's
own documented safe-to-rerun collector, public RPC reads only, overwrites its own instances' snapshot
files — no funds moved), and (b) exactly one invalid-signature POST to the production telemetry
endpoint (permitted by the task).

## Scope actually reviewed
- `~/anicca` (main): commits from `f64831c` through `3b077b9` (HEAD at review time), i.e. everything
  the task listed plus one later commit (`3b077b9`, Task #5b ubi-payout-watcher gate) that is in scope
  because it directly bears on dimension 3.
- `~/anicca-project`: **IMPORTANT CORRECTION** — the working tree was checked out on branch
  `feature/clip-rewards` (HEAD `2b0476b0629`), NOT `main`. `origin/main` (`9709ffc9d3`) is two commits
  ahead of local HEAD for `telemetry.js` (the `feature/clip-rewards` checkout predates PR #285/#286
  merging). All products-repo file reads below were re-taken via `git show origin/main:<path>` to
  review the actual merged state, not the stale local working tree. This is flagged separately as a
  process-hygiene finding, not a colony-code finding — see "Meta-finding" at the end.

---

## 1. KEY-SAFETY — PASS

Reviewed `runtime/dashboard/telemetry-poster.mjs`, `telemetry-post-franklin.mjs`,
`telemetry-post-claude-p.mjs`.

- All three read their private key material in-process only (`fs.readFileSync` of
  `~/.automaton/wallet.json`, `~/.blockrun/.solana-session`, `~/.anicca-founder/state/telemetry-identity.json`
  respectively) and use it only to produce a signature (`acct.signMessage` / `nacl.sign.detached`).
  `console.log` calls in all three print only `net_worth`, HTTP status, and response text — never the
  key, the signature input material, or the raw secret bytes.
- `git log -p --since="2026-07-04T15:00"` over `runtime/dashboard`, `skills/self`, `skills/economy`,
  `skills/ubi`, `runtime/loop`, `skills/_shared` for today's commits: grep for
  `privatekey|secretkey|mnemonic|seed phrase|BEGIN (RSA|EC|PRIVATE)` (excluding known-safe lines like
  `IDENTITY_PATH`, `privateKeyToAccount`, comments) returned **zero hits**. No secret leaked into a
  commit.
- `.gitignore` in `~/anicca` covers `skills/*/state/`, `skills/*/*/state/` — `skills/ubi/state/` and
  `skills/economy/ubi/state/` are excluded from tracking.
- `~/.anicca-founder` (holds `state/telemetry-identity.json`) is **not a git repository at all**
  (`git rev-parse --is-inside-work-tree` → `fatal: not a git repository`). Structurally cannot leak via
  commit.
- `~/.blockrun` (holds `.solana-session`) — likewise not a git repository.
- `~/.automaton` (holds `wallet.json`) **is** a git repository. Checked directly: `wallet.json` is
  listed by name in `~/.automaton/.gitignore` ("Sensitive files - never commit"), `git ls-files | grep -i
  wallet` returns only `node_modules/ethers/...` library files (not the real wallet.json), `git status
  wallet.json` → "nothing to commit, working tree clean" (ignored, not tracked), and `git remote -v` is
  **empty** (no remote configured at all — even if it were tracked, there is nowhere to push it to).
- Minor hygiene-only observation (not a leak): `skills/earn/polymarket-trade/{earner.log,
  earner.launchd.log, telemetry-post.log}` are untracked and NOT covered by any gitignore pattern
  (`git check-ignore -v` returned nothing for any of the three). Inspected `telemetry-post.log`
  contents directly — it contains only `<timestamp> claude-p net <amount> -> <http-status> <body>`
  lines, no key material. Recommend adding `*.log` to `~/anicca/.gitignore` at the repo root as
  defense-in-depth (the log itself is currently harmless, but nothing stops a future poster from
  accidentally logging more).

**Verdict: PASS.** No path found by which any of the three posters' private keys reach stdout, a log
file that gets committed, or a git commit.

---

## 2. ANTI-SQUAT — PASS

Reviewed (from `origin/main`, see meta-finding): `apps/landing/netlify/functions/telemetry.js`,
`_lib/telemetry-verify.js`, `_lib/telemetry-schema.js`, `_lib/fixed-identities.js`.

- `telemetry.js` pre-verify id-shape guard now imports `BASE_ID_RE`/`SOLANA_ID_RE` from
  `telemetry-schema.js` (single source) instead of a hardcoded EVM-only regex — matches the PR #285
  commit message's claim exactly (verified: this fix is present in `origin/main`, contrary to what I
  initially (incorrectly) saw in the stale local `feature/clip-rewards` working tree — see meta-finding).
- `fixed-identities.js` pins exactly two fixed identities: `0x02bb6b2af70dbf2c367c1b69aca9858bf3525502` →
  `claude-p`, `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` → `Franklin`. `expectedHost(id)` returns the
  pinned name only on an exact (or lowercased) key match, else falls back to the auto-derived
  `anicca-<first 6 hex>` scheme — the original anti-squat invariant ("1 wallet ⇒ 1 host name") is
  preserved, not weakened, by adding this allowlist.
- **Live cross-check**: computed the actual address derived from
  `~/.anicca-founder/state/telemetry-identity.json`'s private key (key material never printed) using
  `viem`'s `privateKeyToAccount` → `0x02Bb6b2aF70DBf2c367C1B69aCA9858BF3525502`. This matches
  `fixed-identities.js`'s pinned `claude-p` entry byte-for-byte (case differs only as expected —
  comparison in code is lowercased). The identity mapping is not aspirational; it matches the real key
  in use.
- **Live attack test (the one permitted real POST)**: sent a POST to
  `https://aniccaai.com/.netlify/functions/telemetry` with a well-formed payload (id=
  `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21`, host=`anicca-a3cdd4`, plausible fields) and a garbage
  66-byte hex "signature" I do not hold the key for. **Result: HTTP 401 ("bad_signature")** — the
  attempted impersonation of anicca-a3cdd4 was rejected. No wallet's identity can be claimed without its
  real signing key.
- Reasoned about the residual attack surface: a would-be squatter without any of the three real private
  keys cannot produce a valid `verifyMessage`/`nacl.sign.detached.verify` pass, so `verifyTelemetry`
  rejects before `expectedHost` is even consulted (structurally, the host-mismatch check is a second,
  redundant lock on top of signature verification, not the only one).

**Verdict: PASS.** No path found for a keyless attacker to post as anicca-a3cdd4, Franklin, or claude-p.
The #285 allowlist extraction does not weaken the "wallet = 1 identity" invariant — confirmed by both
static reading and one live 401 test.

---

## 3. FAIL-CLOSED-UBI — PASS

Reviewed `skills/economy/ubi/ubi.js` (`contribute`, `distributeAI`) and `skills/ubi/ubi-payout-watcher.mjs`.

- Ran the module's own test suite: `node --test skills/economy/ubi/__tests__/ubi.test.mjs` → **15/15
  green**.
- Additionally hand-drove both functions with adversarial inputs directly (not just the pre-written
  test fixtures): negative/NaN/undefined/zero/Infinity profit, NaN/undefined/negative liquid balance,
  huge-profit-tiny-balance (reserve breach), non-array `registrySignedWallets`, malformed/undefined
  `recentGifts` entries, negative surplus. **Every adversarial case that should no-op, no-op'd** —
  `contribute()` and `distributeAI()` fail closed on every non-finite/negative/missing/wrong-typed input
  I tried; the only cases that paid were the intentionally-valid ones, and the payout amount was
  correctly capped (`min($5, 25%×surplus)` for the gojo ceiling).
- `ubi-payout-watcher.mjs` (Task #5b, commit `3b077b9`): read the full file. `pass()` now calls
  `contribute(realized, liquidUsd, {contributeThresholdUsd: REALIZED_THRESHOLD_USD})` as a gate **before**
  the Supabase recipient queue is even read (line 140-146); on `gate.amount_usd <= 0` it appends to
  `defer-log.jsonl` and returns without touching Supabase. This directly answers the task's residual
  concern ("does a new signup get paid even with zero surplus?") — **no**, confirmed by both code
  reading and live evidence: `skills/ubi/state/defer-log.jsonl` (produced by the actual running daemon,
  not by me) shows a continuous run of `DEFER pass: realized=$0.0667.../$0.0735 ... < $1` entries at
  ~8s intervals — the real production daemon is actively deferring, matching the spec §28 claim.
- The pre-existing `RESERVE_BASE` ($1 floor, independent of the new gate) still guards each individual
  payment inside the loop as a second layer.
- One design note (not a fail): `realizedProfitUsd()` reads the *monthly* `monthly_revenue_usd` figure
  from the live dashboard-sync, so the gate is "has this instance earned $1+ this month" rather than an
  instantaneous surplus check. This is a looser gate than "right now," but it is not a fail-open bug —
  fetch failure/timeout still returns `0` (fail-closed), and it matches the explicitly-stated reuse of
  the one existing `realized profit` definition (no parallel metric invented, per the code's own
  comment).

**Verdict: PASS.** Both pure gate functions and the live daemon fail closed under adversarial and
production conditions I could actually observe.

---

## 4. SPAWN-READ-ONLY — PASS

Reviewed `skills/self/spawn-child/run.sh`, `lib/akt-cost-gate.js`, `sdl/child.yaml`.

- `grep -inE "deploy|create|send|swap|mint|broadcast|tx-sign|sign-tx|execFileSync|exec\("` over
  `run.sh` + `akt-cost-gate.js` returns only comments/documentation lines (e.g. "This script only ever
  reads balances; it NEVER sends, swaps, mints, or creates a deployment" and "READ-ONLY balance query.
  No tx, no swap, no mint, no send.") — **zero actual money-moving calls** in the code paths reachable
  from `run.sh`.
- The only external commands invoked are `provider-services keys show` (read pubkey) and
  `provider-services query bank balances` (read-only chain query) — confirmed by reading the script
  top-to-bottom.
- The "next steps" text printed on a READY result (Jupiter swap, Skip API relay, akt-treasury.sh mint,
  deploy-akash.sh) are **printed as instructions only** (`echo` statements) — not executed by this
  script. The calling agent would have to separately invoke those other scripts.
- Ran the skill's own test: `bash skills/self/spawn-child/scripts/test-spawn-child.sh` →
  `PASS — spawn-child gate invariants hold (static: no money-moving calls + behavioral: NOT-YET/READY/
  boundary/fail-closed)`.

**Verdict: PASS.** No deployment/send/swap/mint/broadcast code is reachable from `spawn-child/run.sh`.

---

## 5. MERGE-GATE — **FAIL** (concrete bug found, currently unreachable in production)

Reviewed `skills/_shared/lib/bot2bot.py::_merge_gate` / `auto_merge`.

**CONFIRMED FINDING (`skills/_shared/lib/bot2bot.py:184-186`)**: the earnings-delta check
```python
earnings_delta = verdict.get("earnings_delta_usd")
if not isinstance(earnings_delta, (int, float)) or isinstance(earnings_delta, bool) or earnings_delta <= 0:
    return False, f"earnings_delta_usd is not a positive number (got {earnings_delta!r})"
```
does **not** reject `float('nan')`. Reproduced live:
```python
from lib.bot2bot import _merge_gate
_merge_gate({"tests_pass": True, "adversary_verdict": "PASS", "earnings_delta_usd": float('nan')})
# => (True, "tests_pass=True, adversary_verdict=PASS, earnings_delta_usd>0")   # BUG: should reject
```
Root cause: `NaN <= 0` evaluates to `False` in Python (and in every language with IEEE-754 semantics),
so the `earnings_delta <= 0` disjunct never fires for NaN, and `isinstance(nan, float)` is `True`, so
the type check also passes. The gate that is supposed to require "earnings_delta_usd is a positive
number" can be satisfied by a NaN, which is not a positive number by any reasonable definition. This
directly contradicts the task's requirement ("`tests_pass` 偽装...③earnings_delta=0/負で絶対に merge
しない"): NaN is arguably worse than 0/negative because it is silently accepted rather than rejected.

I confirmed all the *other* type-confusion cases the task asked about (`tests_pass: "true"` string,
`tests_pass: 1`, `adversary_verdict: "pass"` lowercase, `earnings_delta_usd: True` boolean,
`earnings_delta_usd: "5"` string, `earnings_delta_usd: None`) are correctly rejected — **only the NaN
case fails closed incorrectly**.

Mitigating factor (checked, not assumed): `grep -rn "auto_merge" skills/` finds **no caller** of
`auto_merge()` anywhere in the codebase outside of `skills/_shared/__tests__/test_bot2bot.py`. The only
real (non-test) consumer of `bot2bot.py` today is `skills/self/coordinate` (commit `d00aa6d`), which
only calls `post()`/`poll()` for the "lesson"-sharing channel — it never calls `auto_merge`. This matches
spec §26's own honest disclosure ("残(正直): auto_merge の実 PR E2E は未実施"). So today, this bug is
**dead code** — no live path can currently trigger a NaN-gated merge. But it is a real, exploitable
defect in code that is explicitly documented (§26/§28) as "the merge gate," and the task specifically
asked to test this exact fail-closed property; it fails.

**Verdict: FAIL.** Fix: add an explicit `math.isnan(earnings_delta)` check (or `earnings_delta_usd > 0`
combined with `earnings_delta_usd == earnings_delta_usd` to exclude NaN, or simply
`Number.isFinite`-equivalent in Python: `math.isfinite(earnings_delta) and earnings_delta > 0`) before
this function is wired to a real caller.

---

## 6. LOOP-BACKOFF — PASS

Reviewed `runtime/loop/index.mjs` (streak/escalation logic added in `ceb519e`) and
`runtime/loop/config.mjs` (`SLEEP_LOOP_DETECT_MAX_S` cap).

- Read the actual diff and the resulting code: `loopDetectStreak`/`loopDetectSlot` module-level state;
  on a loop-detect event, streak increments only if `avoidSlot === loopDetectSlot` (same slot
  re-offending), else resets to 1 for a different slot; `sleepS = min(baseSleepS * 2**(streak-1),
  maxSleepS)`; on successfully picking a *different* slot than `avoidSlot`, both `avoidSlot` and
  `loopDetectStreak`/`loopDetectSlot` are cleared (reset to 0/null) — confirmed this reset condition is
  correct: diversification away from the repeated slot fully resets the escalation, not just the avoid
  flag.
- Ran the full test suite: `node --test runtime/loop/__tests__/integration.test.mjs` → **12/12 green**,
  including the new `PROP-016b` test that specifically asserts: first same-slot loop_detect → streak 1
  (unchanged base cooldown), second consecutive same-slot loop_detect → streak 2, `sleep_s` doubles
  exactly (`second.sleep_s === first.sleep_s * 2`).
- Cap behavior: `Math.min(baseSleepS * 2**(streak-1), maxSleepS)` with default `maxSleepS = 3600`
  correctly bounds the exponential growth (verified by reading the formula; at streak=5 with a 300s base
  this would be `300*16=4800`, correctly capped to `3600`).

**Verdict: PASS.** Escalation, same-slot streak tracking, cross-slot reset, and cap all verified correct
by direct test execution.

---

## 7. TRADING-SAFETY — PASS

Reviewed `skills/earn/sol-trade/run.sh` (tail) and `skills/earn/polymarket-trade/run_earner.sh` (tail).

- `sol-trade/run.sh` uses `set -u` only (no `-e`) at the top of the file (confirmed by reading line 6:
  `set -u`), and the poster line is `timeout 20 node ".../telemetry-post-franklin.mjs" >> "$STATE_DIR/
  telemetry-post.log" 2>&1 || true` — doubly safe (no `-e` to trip, plus explicit `|| true`). The script
  ends with `exit "$RC"` where `$RC` was captured from the trading command *before* the poster line runs,
  so the poster's outcome cannot affect the script's exit code even by side effect.
- `run_earner.sh` uses `set -uo pipefail` (no `-e`), poster line likewise has `|| true` and a `timeout
  20` wrapper.
- **Live-simulated the exact failure mode**: wrote and ran a throwaway script with `set -e` and a
  `timeout 20 node /nonexistent/path ... || true` line pointed at a guaranteed-to-fail path — confirmed
  the script continues past the failing line and exits 0, i.e. even under the *stricter* `set -e` than
  either real script actually uses, a failing poster cannot abort the run.

**Verdict: PASS.** The poster append cannot break either trading pass under any combination of `set -e`
present/absent, `timeout` firing, or the node process itself crashing.

---

## 8. SPEC-TRUTH — **FAIL** (one concrete false claim found in the spec)

Reviewed `docs/superpowers/specs/2026-07-03-anicca-colony-architecture-design.md` §25–§28 against disk.

Most of §25–§28's factual claims check out under direct verification:
- §26's "残(正直): auto_merge の実 PR E2E は未実施" — **confirmed true** (matches my dimension-5 finding
  that there is no live caller).
- §27's incident narrative (ubi-watcher accidental $0.25 payout, root cause = stale plist path after a
  file move) and §28's claimed fix (commit `3b077b9`, realized-surplus gate + defer-log) — **confirmed
  true** by reading the code and by finding real, non-fabricated `defer-log.jsonl` entries showing the
  gate actively deferring in production (see dimension 3).
- §29's PR list for products (`#282`/`#283`/`#285`/`#286`) — **confirmed present** in `origin/main`'s
  history (`git log origin/main` shows the corresponding telemetry/fixed-identity/schema commits).
- The claude-p signing-identity address claimed in §25/§29 (`0x02Bb6b2aF70DBf2c367C1B69aCA9858BF3525502`)
  — **confirmed to match** the real derived address from the actual key file (dimension 2 above).

**CONFIRMED FALSE CLAIM** — spec §25 states: *"collector 追加: `skills/self/telemetry-collect.sh`（mother
a9d08a1）が 3 body に `state/telemetry.json` を書く（**colony-status.sh と一致検証済み**）。"* ("...verified
consistent with colony-status.sh"). This is not true as of the current code:

- `colony-status.sh` was fixed in commit `a05faff` (same day, later than `a9d08a1`) to map
  anicca-a3cdd4's loop to its real launchd job `com.anicca.daemon` (`loop anicca.daemon`), explicitly
  noting in its own added comment: *"a3cdd4 の実 loop = com.anicca.daemon (body ~/.anicca)。founder-loop
  は claude-p の proxy body (~/.anicca-founder, 0x810f)"*.
- `telemetry-collect.sh` (`skills/self/telemetry-collect.sh:63`) was **never updated to match** — it
  still does `A3_LOOP=$(loop_status founder-loop)` and writes `'loop': {'name': 'founder-loop',
  'launchd_label': 'ai.anicca.founder-loop', ...}` into anicca-a3cdd4's own telemetry.json, i.e. it
  reports **claude-p's proxy-body loop status as if it were anicca-a3cdd4's own loop**.
- **Reproduced live**: ran `bash skills/self/telemetry-collect.sh` (the script's own documented
  safe-to-rerun collector) and inspected the actual output —
  `~/.automaton/state/telemetry.json` (anicca-a3cdd4's own file) contains:
  ```json
  "loop": {"name": "founder-loop", "launchd_label": "ai.anicca.founder-loop", "status": "RUNNING"}
  ```
  This is wrong on its face: anicca-a3cdd4's real loop is `com.anicca.daemon` (confirmed both by
  `launchctl list | grep anicca` — `com.anicca.daemon` PID 94407 present — and by
  `healthcheck-runtime-loop.sh`'s own header comment, which independently and correctly documents
  "anicca-a3cdd4 — com.anicca.daemon"). The RUNNING status happens to be accidentally correct right now
  only because `ai.anicca.founder-loop` (PID 8212) *also* happens to be running concurrently — if
  founder-loop were ever stopped while com.anicca.daemon kept running, this collector would wrongly
  report anicca-a3cdd4 as STOPPED.
- This is exactly the kind of instance↔loop mapping confusion §25 itself says it fixed for
  `colony-status.sh` — the fix was not propagated to the sibling script the same spec paragraph claims is
  "verified consistent" with it.

**Verdict: FAIL** on this one specific claim. Everything else checked in §25-§28 was accurate; this is
not evidence of general overclaiming in the spec, but the "一致検証済み" (verified-consistent) phrase is
demonstrably false for the a3cdd4 row and should be corrected, and `telemetry-collect.sh` line 63 should
be changed to `loop_status anicca.daemon` (and the written `launchd_label` field to
`com.anicca.daemon`) to match `colony-status.sh`'s `a05faff` fix.

---

## Meta-finding (process hygiene, not a colony-code defect)

`~/anicca-project` was checked out on `feature/clip-rewards`, not `main`, at the start of this review.
Reading files directly from the working tree (rather than `git show origin/main:<path>`) would have
produced a **false positive** for dimension 2 (the stale `telemetry.js` on that branch still has the
hardcoded EVM-only regex and the old squat-check, pre-dating PR #285/#286). I caught this only by
noticing `_lib/fixed-identities.js` didn't exist on disk despite being referenced by the commit I was
told to review, and cross-checking `git rev-parse HEAD` vs `git rev-parse origin/main`. Recommend future
adversary passes always confirm `git branch --show-current` and diff local HEAD against `origin/main`
for any repo under review before trusting working-tree file contents.

---

## Summary table

| # | Dimension | Verdict |
|---|---|---|
| 1 | KEY-SAFETY | PASS |
| 2 | ANTI-SQUAT | PASS |
| 3 | FAIL-CLOSED-UBI | PASS |
| 4 | SPAWN-READ-ONLY | PASS |
| 5 | MERGE-GATE | **FAIL** (NaN bypasses earnings_delta_usd fail-closed check; currently dead code, no live caller) |
| 6 | LOOP-BACKOFF | PASS |
| 7 | TRADING-SAFETY | PASS |
| 8 | SPEC-TRUTH | **FAIL** (telemetry-collect.sh loop-mapping bug contradicts spec §25's "colony-status.sh と一致検証済み" claim; reproduced live) |

### Findings ranked by severity
1. **[MEDIUM]** `skills/_shared/lib/bot2bot.py:184-186` — `_merge_gate` accepts
   `earnings_delta_usd: NaN` as a valid positive number, defeating the fail-closed merge invariant.
   Not currently reachable (no live caller of `auto_merge`), but must be fixed before `auto_merge` is
   wired to any real PR pipeline. Fix: reject non-finite values explicitly.
2. **[LOW-MEDIUM]** `skills/self/telemetry-collect.sh:63,74` — reports claude-p's `founder-loop` status
   as anicca-a3cdd4's own loop status; will silently misreport anicca-a3cdd4 as STOPPED whenever
   founder-loop is down but com.anicca.daemon is up (or vice versa misreport RUNNING). Contradicts the
   spec's claim that this was verified consistent with colony-status.sh's fix. Fix: change to
   `loop_status anicca.daemon` / `launchd_label: com.anicca.daemon` for the a3cdd4 block.
3. **[HYGIENE, not a defect]** Three untracked log files in `skills/earn/polymarket-trade/` are not
   covered by any `.gitignore` pattern (contents currently harmless — no keys — but should be excluded).

No KEY-SAFETY leak, no squatting path, no UBI fail-open, no spawn tx capability, and no trading-pass
breakage were found anywhere in today's changes.
