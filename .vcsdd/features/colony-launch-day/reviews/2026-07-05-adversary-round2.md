# 2026-07-05 fresh-context adversary — ROUND 2 (post-fix re-verification)

Fresh-context adversary, zero knowledge of the builder's session or round-1 conversation. Verified
against disk (`~/anicca` @ `git rev-parse HEAD` = `92e8a67b28a91763f7724a3fe804dc8e0198e70c`, matches
`origin/main` — no divergence) and live read-only execution. Read-only throughout: no push/commit/
send/launchd-change/message performed except this review file and running the colony's own read-only
scripts (`telemetry-collect.sh`, `colony-status.sh`, existing test suites) and read-only curls.

## 0. Pre-check: are the 2 round-1 FAIL fixes actually committed?

**NO.** `git log --oneline -8` on `~/anicca` main (identical to origin/main, fetched and confirmed
up to date) shows the most recent commits are:

```
92e8a67 fix(telemetry): claude-p poster sets chain:polygon-proxy (honest unverified, not false verified-0)
201f014 docs(colony-status): note claude-p telemetry signing identity != funding wallet
3b077b9 fix(ubi): #5b realized-surplus gate + per-tx cap on ubi-payout-watcher
a89c9ec chore(registry): self/coordinate Foundation-approved 2026-07-05
826837f feat(self/spawn-child): Akash self-spawn readiness gate (prep only, no firing)
8469108 feat(telemetry): Franklin + claude-p sign+POST to the production dashboard (#25 TELEM)
27d3f3b feat(economy/ubi): #13 UBI/gojo distribution pipe (compute+log, no execute)
0f6f953 chore(self-heal): remove #7 validation fixture after capturing proof
```

Neither commit touches `skills/_shared/lib/bot2bot.py`'s `_merge_gate` (last touched by `d00aa6d`,
which is entirely about bot2bot info-sharing wiring / gh-author-resolution bugs, NOT the merge-gate
NaN issue) nor `skills/self/telemetry-collect.sh` (last touched by `a9d08a1`, the original #25 TELEM
commit — no fix commit exists for it at all). `git fetch origin` was run twice, several minutes apart
during this review; `origin/main` did not move. **Conclusion: the fix-in-progress had not landed by
the time this round-2 review ran.** Both dimensions below are re-verified against the SAME code round
1 already reviewed — this is not a false re-fail from reading stale content.

---

## 1. MERGE-GATE — **FAIL (unchanged from round 1)**

`skills/_shared/lib/bot2bot.py::_merge_gate` (line 175-187):

```python
earnings_delta = verdict.get("earnings_delta_usd")
if not isinstance(earnings_delta, (int, float)) or isinstance(earnings_delta, bool) or earnings_delta <= 0:
    return False, f"earnings_delta_usd is not a positive number (got {earnings_delta!r})"
return True, "tests_pass=True, adversary_verdict=PASS, earnings_delta_usd>0"
```

Live execution (`python3` against the actual module, not a re-derivation):

```
'NaN'     val=nan  -> ok=True   reason=tests_pass=True, adversary_verdict=PASS, earnings_delta_usd>0
'inf'     val=inf  -> ok=True   reason=tests_pass=True, adversary_verdict=PASS, earnings_delta_usd>0
'-inf'    val=-inf -> ok=False  (correctly rejected)
'-0.0'    val=-0.0 -> ok=False  (correctly rejected)
'0' (str) val='0'  -> ok=False  (correctly rejected)
0         val=0    -> ok=False  (correctly rejected)
-5.0      val=-5.0 -> ok=False  (correctly rejected)
12.5      val=12.5 -> ok=True   (correct pass)
```

`float('nan') <= 0` and `float('nan') > 0` are both `False` in Python (NaN comparisons never succeed),
so the `earnings_delta <= 0` guard silently fails to reject NaN, and `isinstance(nan, (int,float))` is
`True` — the whole boolean expression evaluates `False`, meaning the `if` does NOT return early, and
falls through to `return True`. Same mechanism lets `+inf` through (`inf <= 0` is `False`). Given a
verdict `{"tests_pass": True, "adversary_verdict": "PASS", "earnings_delta_usd": float('nan')}` (or
`float('inf')`), `auto_merge()` will call `gh pr merge --squash --delete-branch` — i.e. a PR can be
auto-merged into the colony's own mother repo on a computationally garbage/unbounded "earnings" number.
This is the exact defect round 1 reported; **no `math.isfinite`/`Number.isFinite`-equivalent guard has
been added.** Note the codebase already has the correct pattern one file over
(`skills/economy/ubi/ubi.js` uses `Number.isFinite(...)` and correctly rejects NaN/Infinity — verified
live in §3 below) — the fix is a known, already-idiomatic one-liner (`math.isfinite(earnings_delta)`)
that simply has not been applied to `bot2bot.py` yet.

**Fix required:** in `_merge_gate`, replace the bare `earnings_delta <= 0` check with something like
`not math.isfinite(earnings_delta) or earnings_delta <= 0` (needs `import math`), and add regression
tests for `float('nan')` and `float('inf')` inputs (currently absent from
`skills/_shared/__tests__/test_bot2bot.py` — confirmed by grep, zero occurrences of `nan`/`inf` in that
test file).

---

## 2. SPEC-TRUTH / telemetry-collect loop mapping — **FAIL (unchanged from round 1)**

Ran `bash skills/self/telemetry-collect.sh` live (read-only, public RPC reads only) and inspected the
output:

```json
// ~/.automaton/state/telemetry.json (anicca-a3cdd4)
"loop": {
    "name": "founder-loop",
    "launchd_label": "ai.anicca.founder-loop",
    "status": "RUNNING"
}
```

This is wrong per the colony's own SSOT script, `skills/self/colony-status.sh`, which was already
fixed for this exact bug in an EARLIER commit (`a05faff fix(colony-status): map a3cdd4 to its real
loop com.anicca.daemon`) and carries the comment:

> `# a3cdd4 の実 loop = com.anicca.daemon (body ~/.anicca)。founder-loop は claude-p の proxy body
> (~/.anicca-founder, 0x810f)`

i.e. `founder-loop`/`ai.anicca.founder-loop` is **claude-p's** proxy loop, not a3cdd4's. Live
`launchctl list | grep anicca` (run during this review) confirms both `com.anicca.daemon` (PID 94407)
and `ai.anicca.founder-loop` (PID 8212) are simultaneously running as two DIFFERENT launchd jobs — so
the bug is currently masked (`status` shows RUNNING either way) but the `name`/`launchd_label` fields
written to `telemetry.json` are factually wrong: they identify a3cdd4's loop as belonging to a
different instance (claude-p) entirely. If `founder-loop` is ever stopped while `com.anicca.daemon`
keeps running (or vice versa), this file will report a false STOPPED/RUNNING status for a3cdd4.

**Fix required:** in `skills/self/telemetry-collect.sh`, change
`A3_LOOP=$(loop_status founder-loop)` and the hardcoded `'name': 'founder-loop', 'launchd_label':
'ai.anicca.founder-loop'` (in the a3cdd4 block only) to `com.anicca.daemon` / `com.anicca.daemon`,
mirroring the already-correct mapping in `colony-status.sh`.

---

## 3. Sanity re-check of round-1 PASS dimensions (fast, executed not re-derived)

| Dimension | Method | Result |
|---|---|---|
| KEY-SAFETY | `git diff` over every commit since `a9d08a1` (today's session start) grepped for literal private-key/secret values (not variable-name references) | **PASS** — zero literal secrets in added lines; all matches are `process.env`/`readFileSync`/`.env`-sourced variable references, consistent with round-1 finding. |
| FAIL-CLOSED-UBI | Executed `skills/economy/ubi/ubi.js`'s `contribute()`/`distributeAI()` live via `node -e` with NaN, Infinity, negative, unregistered-recipient, rate-limited, and normal inputs | **PASS** — every adversarial input returns `amount_usd: 0` with an honest reason string (uses `Number.isFinite`, correctly guards NaN/Infinity — the pattern `bot2bot.py` above is missing). Normal path correctly computes 10%/25% splits. |
| SPAWN-READ-ONLY | Ran `bash skills/self/spawn-child/scripts/test-spawn-child.sh` live | **PASS** — `PASS — spawn-child gate invariants hold (static: no money-moving calls + behavioral: NOT-YET/READY/boundary/fail-closed)`. Also manually grepped `run.sh`/`lib/` for `tx`/`send-manifest`/`deployment create`/`bank send` — none reachable; script is read-only balance query + ledger append only. |
| LOOP-BACKOFF | Ran `node --test __tests__/loop-detect.test.mjs` in `runtime/loop/` live | **PASS** — 10/10 tests pass (PROP-008/PROP-009 escalation + cooldown + cross-slot reset). |
| TRADING-SAFETY | Read `skills/earn/polymarket-trade/run_earner.sh` in full | **PASS** — both trading passes (`bundle_arb.py`, `market_maker.py`) run first, each guarded by `|| echo ... >> LOG` (non-fatal under `set -uo pipefail`, no `-e`); the telemetry POST runs strictly AFTER `=== pass done ===` is logged and is itself wrapped in `|| true`. A telemetry-post failure structurally cannot roll back or interrupt a trading pass that already ran. |

All 5 previously-PASS dimensions hold. No regressions found.

---

## 4. NEW finding (not in round 1, found via live production check) — claude-p telemetry is currently NOT reaching the live dashboard

Round 1's SPEC-TRUTH finding was about `telemetry-collect.sh`'s loop-name bug (§2 above). While sanity-
checking the broader "#25 TELEM: 3 instance が signed telemetry を出す" and "#14 G4: 全個体の収支を
リアルタイム表示" claims (both marked `completed` in the task list) against the actual LIVE production
endpoint, I found a second, independent, currently-active production bug:

```
$ curl -s https://aniccaai.com/.netlify/functions/dashboard-sync | python3 -m json.tool
{
  "total_net_worth_usd": 9.48,
  "alive": 2,                        <- should be 3
  "leaderboard": [
    {"host": "anicca-a3cdd4", ...},
    {"host": "Franklin", ...}
    // claude-p is ABSENT
  ]
}
```

Root cause, confirmed with fresh evidence:
- `~/anicca/skills/earn/polymarket-trade/telemetry-post.log` shows the last successful post was
  `2026-07-04T18:27:22.020Z claude-p net 0.241107 -> 202 {"ok":true}`, followed by 8 consecutive
  `run_earner.sh: line 17: timeout: command not found` failures, with no further successful posts. At
  review time (`2026-07-04T19:57Z` per this Mac's clock) that is >90 minutes stale.
- `apps/landing/netlify/functions/_lib/telemetry-aggregate.js`'s `aggregate()` filters `live` rows to
  `nowSec - r.ts <= FRESH_S` where `FRESH_S` defaults to 1800s (30 min) — claude-p's row is older than
  that window and is silently dropped from `alive`, `total_net_worth_usd`, and the `leaderboard`.
- The actual bug: `run_earner.sh` line 17 calls `timeout 20 node ...` directly (bypassing the script's
  own `run()` helper on lines 9-10, which already does `command -v gtimeout || command -v timeout ||
  true` specifically to handle environments where a bare `timeout` isn't on `PATH`). The job runs under
  launchd (`ai.anicca.pm-earner.plist`, confirmed via `launchctl print gui/501/ai.anicca.pm-earner`),
  whose `default environment` is `PATH => /usr/bin:/bin:/usr/sbin:/sbin` — no `/opt/homebrew/bin`, so
  `timeout` (which lives at `/opt/homebrew/bin/timeout` on this Mac) is not found under that PATH, and
  line 17 fails with exit 127 every single 600s cycle, meaning `telemetry-post-claude-p.mjs` has not
  actually run since 18:27Z despite the cron firing every 10 minutes since. Interactively, `timeout` IS
  on PATH (homebrew), which is why this was invisible to manual testing but fails every time under the
  real launchd job.

This directly contradicts the "completed" status of Task #1 (3 instance が signed telemetry を出す) and
Task #2 (全個体の収支をリアルタイム表示) as currently observable in production — right now only 2 of 3
instances appear on the live dashboard.

**Fix required:** in `run_earner.sh`, replace line 17's bare `timeout 20 node ...` with the same
`run()` wrapper (or an equivalent `command -v gtimeout || command -v timeout` resolution) already used
for the trading passes, OR set an explicit `PATH` at the top of the script that includes
`/opt/homebrew/bin`. Either fix is a few lines; this is not a design flaw, just an inconsistency within
the same file (the wrapper was written for the trading calls but the telemetry line was added later
without going through it).

---

## Summary

| # | Dimension | Verdict |
|---|---|---|
| 1 | MERGE-GATE (NaN/inf guard) | **FAIL — unchanged from round 1, fix not yet committed** |
| 2 | SPEC-TRUTH: telemetry-collect.sh loop mapping | **FAIL — unchanged from round 1, fix not yet committed** |
| 3 | KEY-SAFETY | PASS (sanity re-check) |
| 4 | FAIL-CLOSED-UBI | PASS (sanity re-check, live-executed) |
| 5 | SPAWN-READ-ONLY | PASS (sanity re-check, live-executed) |
| 6 | LOOP-BACKOFF | PASS (sanity re-check, live-executed) |
| 7 | TRADING-SAFETY | PASS (sanity re-check) |
| 8 | NEW: claude-p telemetry POST silently broken in production (launchd PATH) → dashboard shows 2/3 instances right now | **FAIL (newly confirmed, live)** |

**Neither of the two round-1 FAILs has been fixed yet** — as of this review, `~/anicca` HEAD
(`92e8a67`) matches `origin/main` and contains no commit touching `bot2bot.py`'s `_merge_gate` or
`telemetry-collect.sh`'s loop mapping since round 1. Additionally, a third, independent production bug
was found live: claude-p's telemetry has not successfully posted in over 90 minutes due to a `timeout`
binary not being on `PATH` under the launchd execution environment, causing it to be excluded from
the public dashboard right now. All three are concrete, reproducible, currently-true facts about the
running system, not process/documentation nits.
