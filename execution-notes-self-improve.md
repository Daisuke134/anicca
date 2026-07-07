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
- [ ] P1: spec 作り直し（openevolve + BP5層 + grounded要素、misattributed DA/EV5 破棄）→ fresh Opus adversary vcsdd-spec-review PASS
- [ ] P2: TDD(RED: denylist reject / held-out regress / adversary DISAPPROVE→no-merge / reward-hacking) → impl(GREEN)
- [ ] P2: openevolve run で EVOLVE-BLOCK 戦略に fitness=realized/backtest USD、≥1 accepted edit が baseline 超え（証拠=fitness数値+diff）
- [ ] P3: LOOP 1 を1周 human-zero（self-issue→build→adversary→自merge）
- [ ] cheap win 並行: Franklin OBSERVE(telemetry Solana残高再利用) / HL closed_pnl 永続化

## Blocked
- SI-4 live embed + claude-p exit = 経済spec P2(gig市場 live, 別CC) 依存 → paper/backtest まで完了させ BLOCKED 明記
- ★disk 3.7Gi 残（要監視。重い install 前に df -h /）

## Evidence checked
- openevolve 実在: evaluator.py + examples/*/evaluator.py 多数（function_minimization に EVOLVE-BLOCK 例）
- ch08 外部検証: eval-driven-earning=4/6 grounded, DA/EV5 misattributed, BP3逸脱

## Invariants
人間ゼロ / 人間credentialゼロ / openevolve使用(自作しない) / good判定=adversary+外部引用 /
.vcsdd/features/anicca-agent-economy 触らない / denylist(wallet/keys/.env/.solana-session/ledger.mjs/spend cap) /
live trade 禁止(paper のみ, SOL_TRADE_MAX_SPEND=0)
