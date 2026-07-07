# execution-notes (self-improve harness) — /goal run-state

/goal = human-zero self-improve loop（openevolve fork）を paper/backtest で realized 改善実証まで。
正本 = ~/anicca-project/docs/loop-engineering/09-cobus-adoption-no-human-and-my-exit.md（P0-P5）+ 08（外部検証）。
メール送付済（keiodaisuke, msg 19f3cb028a57382d）。長さ検証 PASS(3569/4000)。
※ この worktree root の `execution-notes.md` は別作業(sprint-4)の物 → 触らない。

## Open items（highest-risk 順）
- [x] P0 openevolve 実interface確認済(証拠): EVOLVE-BLOCK-START/END(進化範囲を物理区切り=denylist構造強制) /
      evaluate(program_path)→EvaluationResult(metrics={combined_score=fitness}, artifacts={adversary feedback}) /
      cascade stage1(quick)+stage2(walk-forward)=L0 / run=openevolve-run.py or run_evolution / config.llm.api_base 任意=ClawRouter可
      → 設計は openevolve に構造的一致。次: ~/anicca に vendor + P1 spec
- [x] P1: spec 作り直し（openevolve + BP5層 + grounded要素、misattributed DA/EV5 破棄）→ fresh-context adversary vcsdd-spec-review PASS（behavioral-spec.md/verification-architecture.md、mode: strict）
- [x] P2 (deterministic core のみ): TDD(RED→GREEN) — denylist reject(fixed-region line 変更 + evolvable region 内 denylisted import/wallet path) / held-out regress(stage1 pass だが stage2 walk-forward regress→promotion gate False) / reward-hacking trip-wire(>3x population-best→flagged) / baseline-beat(hand-crafted better config が real backtest で baseline 超え、promotion gate True) — 全 GREEN。証拠は下の「P2 evidence」参照。scope_guard/gate_math の壊す→REDに戻る sanity check 済（本物のRED-GREENサイクルであることを事後検証）。
- [x] P2 残: REAL openevolve run — DONE (2026-07-07/08)。詳細・実数値は下の「P2 Stage-2 evidence (real openevolve run)」参照。1 accepted edit が baseline (stage2 OOS -0.3959) を大きく超え (9.4486)、scope_guard PASS、diff は EVOLVE-BLOCK 内に完全収容。
- [ ] P3: LOOP 1 を1周 human-zero（self-issue→build→adversary→自merge）
- [ ] cheap win 並行: Franklin OBSERVE(telemetry Solana残高再利用) / HL closed_pnl 永続化

## Blocked
- SI-4 live embed + claude-p exit = 経済spec P2(gig市場 live, 別CC) 依存 → paper/backtest まで完了させ BLOCKED 明記
- ★disk 3.7Gi 残（要監視。重い install 前に df -h /）

## Evidence checked
- openevolve 実在: evaluator.py + examples/*/evaluator.py 多数（function_minimization に EVOLVE-BLOCK 例）
- ch08 外部検証: eval-driven-earning=4/6 grounded, DA/EV5 misattributed, BP3逸脱

## P2 evidence (deterministic core — this stage's real, run output)

Files (all under `skills/earn/self-improve/`, this worktree):
`lib/gate_math.py` (pure), `lib/scope_guard.py` (effectful denylist/scope enforcement — the SOLE
enforcement mechanism, per INV-3), `lib/promote.py` (effectful promotion write+commit, not
exercised with a real git commit by any test — tests mock it or never reach it),
`evaluator.py` (evaluate/evaluate_stage1/evaluate_stage2/tripwire_check, plain-dict return, no
`import openevolve`), `strategies/pm_backtest_strategy.py` (the evolvable program, exactly one
EVOLVE-BLOCK-START/END pair verified via `grep -c`), `strategies/fixtures/pm_history.csv` (84-row
synthetic historical fixture, 6 windows, deterministic generation seed 20260707),
`config.yaml`, `run_evolve.sh`, `launchd/ai.anicca.self-improve-evolve.plist`, `tests/*.py`
(18 tests across 4 files + conftest.py).

Exact command run (from this worktree root; venv with only `pytest` installed, to avoid touching
the homebrew-managed system Python under PEP 668 — see below):
```
cd /Users/anicca/anicca/.worktrees/self-improve-harness
<scratchpad>/venv-self-improve/bin/python3 -m pytest skills/earn/self-improve/tests/ -v
```
Result (verbatim tail):
```
============================== 18 passed in 0.05s ==============================
```

Sanity check performed (proves the RED phase was real, not vacuous): temporarily patched
`scope_guard.check` to always return `(True, "scope-guard-pass")` → 4/5 denylist tests correctly
FAILED (the control "clean edit" test correctly still passed); temporarily broke
`gate_math.beats_baseline` to always return `True` → the held-out-regress promotion test
correctly FAILED. Both reverted; full suite re-confirmed 18/18 green afterward.

pytest was not present anywhere on this Mac (checked `python3 -m pytest`, python3.11/3.12/3.13,
pip3 list). Installed into an isolated venv under the scratchpad directory (NOT this repo, NOT
system Python) via `python3 -m venv ... && pip install --no-cache-dir pytest`; pip cache purged
after. openevolve itself was deliberately NOT installed this stage (disk was 3.1-3.6Gi free
throughout; not needed for these deterministic tests; explicit constraint from the delegating
task).

/goal Done-condition mapping: condition (2) "tests green" = the 18/18 result above. Condition (4)
"denylist reject" = `tests/test_denylist_reject.py` (2 dedicated rejection tests + 1 control +
1 stage1-wiring test). Condition (3) "≥1 accepted edit beats baseline" — the DETERMINISTIC HALF
only (real backtest math + real scope_guard + real stage_gate boolean, all wired end-to-end and
proven with real numbers over the real committed fixture) is proven by
`tests/test_baseline_beat.py`; the REMAINING half of condition (3) — an actual openevolve LLM run
proposing that edit itself, plus a fresh (non-mocked) vcsdd-adversary PASS on that specific
diff — is explicitly NOT done yet (see "P2 残" above).

## Invariants
人間ゼロ / 人間credentialゼロ / openevolve使用(自作しない) / good判定=adversary+外部引用 /
.vcsdd/features/anicca-agent-economy 触らない / denylist(wallet/keys/.env/.solana-session/ledger.mjs/spend cap) /
live trade 禁止(paper のみ, SOL_TRADE_MAX_SPEND=0)

## P2 Stage-2 evidence (real openevolve run) — 2026-07-07/08

### Setup
- `pip install --no-cache-dir openevolve` into the existing scratchpad venv
  (`<scratchpad>/venv-self-improve`, python3.14) → `openevolve==0.3.0` installed. Real CLI entrypoint
  is `openevolve-run` (not `openevolve-run.py`, despite `run_evolve.sh`'s naming — that script's
  invocation was NOT changed this stage since it wasn't executed; the manual commands below used the
  correct real entrypoint name).
- Endpoint (no human credential, REQUIRED): the colony's own local ClawRouter proxy at
  `http://127.0.0.1:8402/v1` (an already-running `clawrouter` process, PID confirmed via `lsof`),
  backed by the SELF-FUNDED `anicca-a3cdd4` automaton's own wallet
  (`0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` on Base). `clawrouter wallet` showed balance
  **$0.00 USDC** the whole session — a structural guarantee that only FREE-tier models could ever be
  used (no spend was even possible, let alone attempted). Model used: `free/mistral-large-3-675b`,
  verified live via direct curl (HTTP 200, response `model` field matches the request, not silently
  downgraded to a different free model the way `free/qwen3-coder-480b` was observed to be).

### Real bugs found and fixed while wiring the real harness (both are infra fixes, NOT scope_guard/evaluator-decision changes)
1. **Fixture path bug**: real openevolve copies each candidate's file TEXT into a throwaway
   `tempfile.NamedTemporaryFile` before calling `evaluate_stage1`/`evaluate_stage2` — so
   `pm_backtest_strategy.py`'s own `load_fixture()` default arg
   (`os.path.dirname(__file__)`-relative) resolved to `/tmp/.../fixtures/pm_history.csv`, which does
   not exist, for every real candidate (confirmed: even generation-0's byte-identical copy of the
   baseline failed with `FileNotFoundError` in the first trial run). Fix: `evaluator.py` now defines
   its own `FIXTURE_PATH` (absolute, evaluator.py's own `__file__`-relative — evaluator.py itself is
   always loaded by openevolve from its real path, never tempfile-copied) and passes it explicitly:
   `module.load_fixture(FIXTURE_PATH)` in both `evaluate_stage1` and `evaluate_stage2`.
2. **`top_p: null` 400**: openevolve's OpenAI client always includes `top_p` in the request body
   (even when unset → `null`); the local ClawRouter proxy's schema validator 400s on
   `"top_p": null` ("expected number, received null"). Fix: `config.yaml` sets `llm.top_p: 1.0`.

### The caching/determinism trap (the reason early full runs looked "stuck")
At generation 0 (single seed program, no population yet) openevolve's own rendered prompt is
BYTE-IDENTICAL across "iterations" — `evolution_round` is never interpolated into the template text,
and `prompt.template_variations` defaults to `{}` (no stochasticity content) even though
`use_template_stochasticity: true` is openevolve's own default. With a single fixed
`primary_model`+`temperature`, every early iteration sent the literal same request. The local
ClawRouter proxy has a live response cache (`clawrouter cache` showed `hits: 43, misses: 1660` after
one session) — so only the FIRST-ever identical request reached a real generation; every subsequent
"iteration" at generation 0 resolved in <100ms, served straight from the proxy's cache with the exact
same (good-or-bad) content. A run stuck on one bad generation-0 sample could therefore never see a
second real sample no matter how many `--iterations` were requested — confirmed directly: two
separate full 20-25 iteration runs (models `nvidia/glm-4.7` then `free/mistral-large-3-675b`, each at
one fixed temperature) each produced exactly ONE real LLM generation total, all other iterations
being instant cache hits of that one (repeatedly bad) sample.

Fix (a real, sanctioned openevolve mechanism, not a workaround): replaced the single
`llm.primary_model` with `llm.models:` — 3 entries of the SAME free model at 3 different
temperatures (0.5 / 0.9 / 1.15), each `weight: 1.0`. `LLMEnsemble._sample_model` (real
`openevolve/llm/ensemble.py` code) does a weighted `random.choice` over this list on every single
`generate_with_context` call — this is openevolve's documented multi-model-ensemble feature, used
here for its designed purpose (request diversity), not a hack. This both changes the request bytes
(escapes the proxy cache) and 3x's the chance of landing a well-formed, in-scope diff per attempt.

Also added (openevolve's own `prompt.system_message` field, a plain string — verified via
`prompt/sampler.py` that a literal string not matching a known template key is used verbatim as the
system message): explicit natural-language guidance that every SEARCH/REPLACE hunk MUST fall
strictly between the `# EVOLVE-BLOCK-START`/`# EVOLVE-BLOCK-END` markers. This follows the colony's
own agent-building rule ("guidance goes in the PROMPT, natural language to the model — never a
hardcoded gate that overrides the model") — `scope_guard.py` remains the actual enforcement
regardless of what the model does; the system message only steers it. Real openevolve's own default
templates (`prompts/defaults/diff_user.txt` + `prompt/sampler.py`) never mention "EVOLVE-BLOCK" at
all — confirmed by grep against the installed package.

### The real run that produced the accepted, baseline-beating edit
```
cd skills/earn/self-improve
<scratchpad>/venv-self-improve/bin/openevolve-run \
  strategies/pm_backtest_strategy.py \
  evaluator.py \
  --config config.yaml \
  --iterations 30 \
  --output runs/run6-20260707T151345Z \
  --log-level INFO
```
Real stdout tail:
```
Evolution complete!
Best program metrics:
  combined_score: 9.4486
  stage1_pass: 1.0000
```
20 real programs ended up in the persisted database (`database.db_path: runs/db`, real
`DatabaseConfig.db_path`/`log_prompts` fields). Multiple DISTINCT scope_guard-passing candidates
were generated across the run with combined_score values -18.13, -17.87, -4.72, -4.47 (baseline),
-0.81, -0.24, -0.21, -0.07, and the winner 9.4486 — real exploration variety, not one lucky fluke.
One candidate was correctly rejected as `out-of-scope-edit` (lines outside EVOLVE-BLOCK) even after
the system-message fix — scope_guard is still doing real work, not rubber-stamping everything.

**Independently re-verified** (fresh python process, NOT trusting openevolve's own printed number):
```python
import evaluator
from lib import scope_guard
cand_code = open('evidence/best_program.py').read()
base_code = open(evaluator.BASELINE_PATH).read()
ok, reason = scope_guard.check(cand_code, base_code)     # -> True, "scope-guard-pass"
baseline_score = evaluator.baseline_stage2_score()         # -> -0.3959371620826199
full = evaluator.evaluate('evidence/best_program.py')
# full == {'combined_score': 9.44855790310848, 'stage1_pass': True, 'stage2_pass': True,
#          'baseline_stage2_score': -0.3959371620826199, 'window_pairs': [...], ...}
```
Per-window-pair OOS net USD (evaluate_stage2, test windows only): window(0→1)=+3.36,
window(2→3)=+67.26, window(4→5)=-42.28 → mean = combined_score = 9.4486.

**/goal Done-condition (3) — VERIFIED TRUE**: one real openevolve run (30 iterations, real LLM,
no human credential) produced ≥1 accepted bounded strategy edit
(`233d923c-0fb2-451f-ab94-90fa64b9cb8d`, parent `a11af17f-97fa-4714-92b7-4563a01b7021`) whose
backtest `combined_score` (9.4486) is realized > the baseline's (-0.3959), `scope_guard_ok=True`
(the diff touches only the `score_candidate` function body between the EVOLVE-BLOCK markers — the
fixed region, including `load_fixture`/`_stake_for_row`/`run_backtest`, is byte-identical to the
committed baseline).

### Evidence files (`skills/earn/self-improve/evidence/`)
- `best_program.py` — the full evolved program (identical to
  `runs/run6-20260707T151345Z/best/best_program.py`, verified with `diff`)
- `evolved.diff` — unified diff vs. the committed baseline `strategies/pm_backtest_strategy.py`
  (confined entirely to `score_candidate`'s body: adds a non-linear edge/confidence-ratio scaling
  plus liquidity/resolve-horizon multipliers to the stake-sizing formula)
- `run-result.json` — `{baseline_score: -0.3959371620826199, best_score: 9.44855790310848,
  beats_baseline: true, iterations: 30, endpoint_used: "free/mistral-large-3-675b (...)",
  scope_guard_ok: true, stage1_pass: true, window_pairs_oos_net_usd: [...], candidate_program_id,
  candidate_parent_id, run_id, command}` — no secret/API key anywhere in the file (endpoint recorded
  as model name + local proxy address only)

### Not committed / left as-is
`runs/` (per-run stdout logs, checkpoints, the persisted `runs/db/` program database) stays in this
worktree as raw evidence backing the summary above; the caller may choose what (if anything) under
`runs/` to commit versus `.gitignore`. `config.yaml` now points at a live local endpoint + contains
the working temperature-ensemble/system_message/db_path fields used for this real run (no secrets).

## HONEST re-read of the +9.4486 candidate — NOT a validated strategy (fresh-context adversary finding, 2026-07-08)

A fresh-context vcsdd-adversary review of this implementation (impl/iteration-1) independently
re-derived the same numbers above (baseline=-0.3959371620826199, best=9.44855790310848,
beats_baseline=True — bit-for-bit reproduced in a clean process) and confirmed scope_guard/no-
human-credential/no-live-money all PASS. It also surfaced a finding this file must not let a later
reader miss: **the accepted candidate `233d923c` is variance-amplification (stake-sizing/leverage
on the SAME trade selection as baseline), not evidence of a better strategy.**

- The candidate makes the IDENTICAL trade-selection decisions as baseline in every stage2 window
  (n_trades matches baseline exactly: 10/9/12 in test windows 1/3/5). The LLM's only change is
  scaling the stake size (leverage), not picking different/better trades.
- Per-window OOS net USD: window(0→1)=+3.36, window(2→3)=+67.26, window(4→5)=-42.28 → mean=9.4486.
  The inter-window standard deviation across just these 3 points is ~44.9 — nearly **5x** the mean
  improvement over baseline (~9.85). One bad window (-42.28) is larger in magnitude than the whole
  claimed edge.
- edge/confidence correlate with actual outcome near zero in the worst OOS window (window 5:
  corr(edge,outcome)=0.040, corr(confidence,outcome)=0.035, computed directly off
  `strategies/fixtures/pm_history.csv`), and the single LARGEST stake in that window (highest edge
  in-window) landed on a LOSING trade — a textbook noise-chasing / variance-amplification
  signature, not a generalizing edge.

**What is proven**: the MECHANISM works end-to-end — openevolve proposes a real LLM-authored
bounded edit, `scope_guard` gates it to the EVOLVE-BLOCK (fail-closed, independently re-verified
with 5 adversarial probes), `evaluator.py` scores it on a real disjoint-window walk-forward
backtest, and a real accepted candidate's `combined_score` beats the real baseline's — all with no
human in the loop and no human credential.

**What is NOT proven**: that this specific candidate is a good trading strategy, or that it is safe
to promote to any paper/live capital allocation. It is not. The per-candidate promotion adversary
(REQ-RH4 step 3 — a FRESH vcsdd-adversary PASS on the specific candidate diff, required IN ADDITION
to the numeric stage2 gate before ANY promotion) has correctly NOT been invoked for this candidate,
and must not be until (at minimum) a stability re-check across more/different OOS windows is done.
No promote.py call has ever happened for this candidate (no "self-improve" promote commit exists in
git log) — this section exists so that evidence file is never mistaken for a promotion-ready
result by a later reader (including a future instance of me).

## Fix for adversary-verdict BLOCKING finding (impl/iteration-1) — REQ-OE7 wiring, 2026-07-08

The adversary's FAIL was correct and reproducible: `run_evolve.sh` checked/invoked a binary name
(`openevolve-run.py`) that does not exist anywhere on this machine (confirmed again independently:
`ls <venv>/bin` after a fresh `pip install openevolve` shows only `openevolve-run`, no `.py`
suffix) — every real/scheduled invocation of the committed script silently took the
"openevolve-not-installed → skip, exit 0" branch and never ran real evolution. The evidence above
(the +9.4486 run) was produced by a MANUAL `openevolve-run` call that bypassed `run_evolve.sh`
entirely, which is exactly what the adversary flagged.

Fixes applied (all under `skills/earn/self-improve/`):
1. **Durable, non-scratchpad venv**: `python3 -m venv ~/.anicca-venvs/self-improve` (outside this
   git repo, outside any session scratchpad — the earlier `<scratchpad>/venv-self-improve` used to
   produce the +9.4486 evidence no longer exists, having been cleaned between sessions — this is
   the actual root cause of why a durable path is required). Installed via
   `~/.anicca-venvs/self-improve/bin/pip install --no-cache-dir openevolve openai`, then
   `pip cache purge`. No heavy ML deps pulled in (no torch/etc — openevolve's own deps are small:
   openai, pydantic, flask, numpy, pyyaml, tqdm); disk moved only 2.8Gi → 2.7Gi avail during
   install (checked `df -h /` before/after per the disk-tight constraint). Verified
   `~/.anicca-venvs/self-improve/bin/openevolve-run --help` works standalone.
2. **`run_evolve.sh`**: now invokes `${OPENEVOLVE_BIN:-$HOME/.anicca-venvs/self-improve/bin/openevolve-run}`
   by absolute path (no reliance on `command -v` / PATH lookup at all). The old silent
   "not-installed → exit 0" branch is replaced with a LOUD failure: missing/non-executable binary
   now logs a `FATAL` line to both the state log and stderr and `exit 1` — the script can no longer
   pretend to succeed when openevolve isn't reachable.
3. **`launchd/ai.anicca.self-improve-evolve.plist`**: added `WorkingDirectory` (the skill dir) and
   an explicit `EnvironmentVariables` `PATH` (venv bin first, then standard system dirs) + `HOME`,
   so a launchd-triggered run (which gets a minimal default PATH with no project/user
   customization) resolves the same durable venv `run_evolve.sh` now references by absolute path.
   Validated with `plutil -lint` (OK).
4. **Re-verification under minimal PATH** (the actual proof, not just a code read): ran
   ```
   env -i HOME="$HOME" PATH=/usr/bin:/bin SELF_IMPROVE_ITERATIONS=2 bash skills/earn/self-improve/run_evolve.sh
   ```
   (`PATH` stripped to just `/usr/bin:/bin` — no venv, no homebrew, no project bin dirs — simulating
   launchd's minimal environment; `SELF_IMPROVE_ITERATIONS=2` uses the script's existing env
   override to keep the proof cheap). Script exited 0. The state log
   (`skills/earn/state/self-improve-evolve.log`) and the new
   `runs/run-20260707T162316Z/logs/openevolve_20260708_012317.log` show REAL openevolve startup —
   `Initialized OpenAI LLM with model: free/mistral-large-3-675b`, `Initialized LLM ensemble...`,
   a real LLM round-trip (`Error on attempt 1/6: degraded response: repetitive assistant loop.
   Retrying...` — a genuine network response, not a canned skip message), `Starting process-based
   evolution from iteration 1 for 2 iterations`, and a `best/best_program.py` + `best_program_info.json`
   written to the new run dir — i.e. it reached and ran the real binary, NOT the
   `skip openevolve-not-installed` branch that the adversary caught. This particular 2-iteration
   run's LLM samples happened to return "No valid diffs found" (real sampling variance at n=2, not
   a wiring failure — see the +9.4486 run above at n=30 for a real accepted candidate), so the
   tracked "best" for this tiny proof run is just the unmodified seed program
   (`combined_score=-4.4683, stage1_pass=false`) — this run's purpose is proving the SCRIPT+PLIST
   wiring reaches real openevolve under a minimal PATH, not re-proving beats-baseline (already
   proven and independently reproduced by the adversary above).

## Close-loop fix: 3 Stop-hook-review gaps, human-zero (2026-07-08)

A Stop-hook review of the merged harness found 3 gaps, all provable on PAPER (not the live-money
part). Fixed on branch `feature/self-improve-close-loop`, worktree
`~/anicca/.worktrees/self-improve-close-loop`.

### Gap 1 — OBSERVE: read realized P&L from earn-ledger.jsonl

Added `lib/ledger_reader.py`: read-only Python mirror of
`skills/_shared/lib/ledger.mjs::isProfitable`/`readLedger` (net_usdc>0, not a swap source,
external===true, chain-correct confirmation — EVM tx+status=="0x1" or Solana sig+confirmed==true).
INV-5 tension disclosed in the module's own docstring: this is a duplicated READ-ONLY view of one
boolean rule, not a second ledger/writer — a subprocess->node round trip was rejected as the
alternative (this harness has intentionally had zero subprocess dependency until now; `subprocess`
is even on `scope_guard.py`'s own EVOLVE-BLOCK denylist). 13 pytest cases
(`tests/test_ledger_reader.py`), including the exact fixture shapes `ledger.mjs` itself documents
(EVM row, Solana row, narrate-only row excluded, swap row excluded even though net-positive,
negative-net row excluded, unconfirmed-tx row excluded).

Wired as an OBSERVE step at the START of `run_evolve.sh`, before EVOLVE: real output against the
real ledger, 2026-07-08 —
`{"ledger_path": ".../skills/earn/state/earn-ledger.jsonl", "total_rows": 30,
"profitable_row_count": 6, "realized_net_usd": 8.4731}` — logged to
`skills/earn/state/self-improve-evolve.log` every run, never blocking (a missing/sparse ledger
degrades to an all-zero summary).

### Gap 2 — risk-adjusted fitness (kill variance-amplification)

`evaluator.py`'s stage2/promotion `combined_score` changed from raw mean OOS net USD to
`gate_math.risk_adjusted_score` — Sharpe-like `mean(oos) / max(stddev(oos), eps)` (Lopez de Prado +
Lilian Weng cited in the function's own docstring). Deliberately `max(stddev, eps)`, not
`stddev + eps`: the additive form is NOT exactly scale-invariant under leverage (a real, if tiny,
reward-hacking crack — caught by this feature's OWN test suite before being shipped, see
`test_risk_adjusted_fitness.py` git history); `max()` makes leverage-invariance EXACT whenever the
real stddev clears the eps floor (true for every realistic run).

The ORIGINAL fixture (`strategies/fixtures/pm_history.csv`) had ~zero edge/confidence-outcome
correlation (per the "HONEST re-read" section above), so raw-USD scoring could ONLY be improved by
leveraging identical trade selection — exactly what candidate `233d923c` did. A risk-adjusted
metric needs a fixture with a GENUINE, if noisy, edge to reward anything at all, so the fixture was
regenerated deterministically: `strategies/fixtures/generate_fixture.py`, `SEED=192`, `ALPHA=0.5`
(`true_prob = price + 0.5*edge + noise`) — confirmed `corr(edge, outcome) = 0.1503` on the
regenerated data (weak-but-real, not free money).

Real numbers off the regenerated fixture (not invented, reproduced by `tests/test_baseline_beat.py`
+ `tests/test_risk_adjusted_fitness.py`):
- baseline (`min_edge=0.15, min_confidence=6.0, base_stake=5.0`): `combined_score=1.2628`,
  `mean_oos_net_usd=5.6919`, `std_oos_net_usd=4.5073`, **`worst_window_oos_net_usd=-0.4732`**
  (a genuinely losing OOS window).
- hand-crafted GENUINE selection-change candidate (`min_edge: 0.15 -> 0.24`, nothing else changed):
  `combined_score=2.4385` (beats baseline), `mean_oos_net_usd=7.9775` (mean UP),
  `std_oos_net_usd=3.2715` (variance DOWN), **`worst_window_oos_net_usd=4.5268`** (worst window
  flips to positive) — a genuine Pareto improvement, not a variance trick.
- hand-crafted LEVERAGE-ONLY candidate (`base_stake: 5.0 -> 20.0`, thresholds unchanged, therefore
  IDENTICAL trade selection every window): `combined_score` is numerically identical to baseline's
  (`1.2628...` both, `math.isclose(rel_tol=1e-9)`) — proven both algebraically (docstring) and by a
  real end-to-end evaluator run (`test_leverage_only_candidate_does_not_beat_baseline_on_real_fixture`)
  that leverage alone cannot beat baseline under this metric.

### Gap 3 — per-candidate promotion adversary (REQ-RH4) + full autonomous cycle

Added `lib/promote_gate.py` (pure: `assess_candidate`/`decide_promotion`/`promote_if_approved`,
unit-tested with zero LLM cost in `tests/test_adversary_disapprove.py` by mocking
`lib.promote.promote`) + `lib/promote_gate_run.py` (effectful driver: builds the prompt, shells out
to a FRESH `claude --model opus --dangerously-skip-permissions --print --output-format json
--json-schema ... --max-budget-usd 1.00` — same pattern as `~/anicca/skills/self/self-fix.sh`'s
adversary spawn, here synchronous since the verdict is needed before deciding to promote) +
`promote_gate.sh` (thin shell entrypoint). REQ-RH4 order enforced structurally: stage2
beats_baseline + trip-wire clear are checked BEFORE any LLM call — an ineligible candidate costs
zero tokens. `run_evolve.sh` now runs the full cycle: OBSERVE -> EVOLVE -> promote_gate.sh -> log.

**Found and fixed a real bug while proving this**: `lib.promote.promote(..., commit=False)` (a
pre-existing file from before this close-loop revision) writes `baseline_path` to disk
UNCONDITIONALLY — only the git-commit step is gated by `commit`. The first smoke test of
`promote_gate.sh --dry-run` against a hand-crafted candidate actually overwrote the real
`strategies/pm_backtest_strategy.py` in this worktree (caught immediately via `git status`/`git
diff`, reverted with `git checkout --`, confirmed clean before proceeding). Fix: `--dry-run` in
`promote_gate_run.py` now skips calling `promote_if_approved`/`promote.promote` entirely (zero file
writes) rather than relying on `commit=False`'s partial/misleading protection — `lib/promote.py`
itself was left untouched (out of this gap's scope, and nothing else in the repo depends on its
`commit=False` behavior).

**Smoke test (hand-crafted candidate, `--dry-run`, real adversary call, evidence in
`evidence/close-loop/handcrafted_candidate_adversary_verdict.json`)**: the `min_edge=0.24` genuine
selection-change candidate from Gap 2 was assessed as `eligible_for_adversary_review=true`
(scope_guard PASS, stage1 PASS, stage2 beats_baseline, trip-wire clear), and the REAL fresh Opus
adversary independently re-derived the numbers and returned `verdict=PASS`: *"a genuine selection/
logic change... base_stake is untouched at 5.0, so this is unambiguously a selection/logic change...
not a leverage/stake-multiplier... willing to promote into the committed backtest baseline"*
(cost_usd≈$0.35–0.71 across 2 real calls). `--dry-run` correctly did NOT commit — `git status`
confirmed the baseline file was untouched.

**Real "RUN IT ONCE" proof (human-zero, minimal PATH, evidence in `evidence/close-loop/real_run_*`)**:
`env -i HOME="$HOME" PATH=/usr/bin:/bin bash run_evolve.sh` (`SELF_IMPROVE_ITERATIONS=10`).
OBSERVE logged the real ledger summary above. EVOLVE ran real openevolve against the free-tier
model; every one of the 10 iterations across all 3 islands failed with `No valid diffs found in
response` / `degraded response: repetitive assistant loop` (the free model's own diff-compliance
flakiness, previously documented in this file — not a wiring failure: the run's own log shows real
per-iteration LLM round-trips and retries). openevolve's own tracked "best" program therefore
remained the UNMODIFIED generation-0 seed (`combined_score=1.2628`, byte-identical to baseline —
confirmed via `diff`, zero lines). promote_gate's deterministic pre-check correctly marked this
candidate `eligible_for_adversary_review=false` (`stage2_pass=false`: a tie against baseline never
beats it, EDGE-2) and logged the rejection reason WITHOUT ever invoking the LLM adversary (zero
token cost) — `verdict.json`: `{"promote": false, "reason": "deterministic gate not cleared before
adversary review: ... stage2_pass=False ...", "adversary_invoked": false}`. Nothing was promoted;
`strategies/pm_backtest_strategy.py` is unchanged (confirmed via `git status`).

**Honest summary**: this run is a fully wired, human-zero, real proof of the OBSERVE->EVOLVE->
promote_gate->log cycle, correctly and honestly rejecting a non-improving candidate without any
LLM cost — it is NOT a proof that openevolve's free-tier model can currently find a real
risk-adjusted improvement on its own within 10 iterations (it did not, this run). The separate
hand-crafted-candidate smoke test (previous paragraph) proves the ADVERSARY step itself works
end-to-end with a real opus call and a real, correct, cited PASS verdict — that mechanism is
proven; a real openevolve-discovered accepted candidate under the NEW risk-adjusted metric remains
future work (more iterations / a stronger free-tier model / more islands), same caveat class as
this file's very first sections.

**Fixture split disclosed**: the backtest fitness (Gap 2) uses the synthetic, documented-edge
`pm_history.csv` fixture — real market-feature history per historical decision isn't available
(earn-ledger.jsonl records outcomes/P&L, not the per-decision market features a backtest replay
would need). `ledger_reader.py` (Gap 1) reads the REAL ledger for the OBSERVE/realized-P&L signal.
A real-market-data backtest replay stays deferred, same as the original spec's own
`out_of_scope_this_phase` framing.
