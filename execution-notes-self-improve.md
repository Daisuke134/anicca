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
- [ ] P2 残: REAL openevolve run（LLM が実際に候補を提案）で EVOLVE-BLOCK 戦略に fitness=realized/backtest USD、≥1 accepted edit が baseline 超え（証拠=fitness数値+diff+adversary verdict）。今回は openevolve 自体を pip install/vendor していない（disk 3.5Gi 節約、この段階では不要）→ 次段で ClawRouter free-tier endpoint を config.yaml の llm.api_base に設定し、openevolve を vendor して実行する必要あり。
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
cd /Users/operator/anicca/.worktrees/self-improve-harness
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
