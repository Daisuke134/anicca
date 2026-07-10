# #6 CEO を生かす — Evidence

正本: spec §8 #6 / §10 #6。scope: profitable-claude(銀行口座+Dais自身の稼ぎ)。crypto=別CC。

## 真因（investigation 2026-07-11 裏取り、自分でも該当ファイル Read 済）
1. **decisions 0行の第1層**: `bin/ceo-run.sh` no-args(週次 agent-judgment) を起動する scheduler が皆無。launchd `ai.anicca.ceo-runner.plist` は `--light-pass`(決定論budget-checkのみ)専用。
2. **decisions 0行の第2層**: `ceo-decisions.jsonl` は `cmd_apply_decision`(実 allocation 変更時)だけが書く。**no-change 判断は永続化されない**→「走ってない」と「据え置き判断」が区別不能。
3. **cost 自己申告 fabrication**: 各 loop agent が pass 末に `record-cost-event.sh` を叩く自己申告方式(正しい設計)。affiliate は「記録した」と申告したが cost-events.jsonl に affiliate 行なし=偽申告。照合機構が無いのが gap。
4. **registry**: pm/hl/sol=external は crypto=別CC担当で正しい。external loop に last_observed_at 無し=CEO が silent-blind。
5. **cron codex-harness**: plugin 04:49 導入+07:50 gateway 再起動で修理済。4件(reelclaw/larry/watercolor, daily 0 7)は stale 表示、次回 07:00 JST run で自動復帰見込み。

## VERIFIED: CEO core を live 起動し apply-decision write gate が E2E で機能することを確認
コマンド: `cd /Users/anicca/profitable-claude && bash bin/ceo-run.sh`（no-args、tmux/claude sonnet core 起動）
結果（tmux pane 実出力、~55s で完了）:
```
{"pass":"weekly-full-eval","reviewed":["loop-registry.json","ceo-budget-config.json","cost-events.jsonl","loop-evaluations.jsonl","ceo-decisions.jsonl","lessons.jsonl"],"changed":[],"reason":"system 5 days old, spend ~$0.98 total vs $10-25/wk caps, only 2 loop-evaluations (life-manager, N too thin), no repeated failure or budget-pressure signal — no allocation change forced"}
```
→ **CEO は実際に全 ledger を読み、genuine な agent 判断を下した**（ノイズに反応せず changed:[]＝正しい Elon 的規律）。ただし現状この判断はどこにも永続化されず ceo-decisions.jsonl は空のまま（=第2層の真因を live で実証）。

## 実装中（VCSDD-lean feature `ceo-revive`, profitable-claude worktree, builder=Sonnet）
- REQ-CEO-020: cost 自己申告照合→lessons 記録
- REQ-CEO-021: no-args pass の判断を ceo-decisions.jsonl に永続化(type付き)
- REQ-CEO-022: 週次 launchd plist で no-args 起動
- REQ-CEO-023: registry last_observed_at + external 状態一致
→ 実装後: fresh Opus adversary 検証 → merge → live で CEO pass 再実行し ceo-decisions≥1 行 + enforcement gate test green を evidence 化。

## builder GREEN → adversary(Opus) FAIL（fix-loop 必要, 2026-07-11）
builder: 4 REQ 実装, tests 94→99 green(regression 0), commit 2b722ed/56a2740 local main 未push。
fresh Opus adversary verdict = **FAIL**, blocking 3件（`.vcsdd/features/ceo-revive/reviews/sprint-1/output/`）:
- **FIND-001(critical)**: REQ-CEO-023 `last_observed_at` を書く箇所がゼロ=永遠 null。investigation gap 未解決の空実装。→ CEO light-pass/status で各 loop の last-pass marker mtime から registry.last_observed_at を stamp する write site を追加。
- **FIND-002(high)**: `lib/ceo_budget.py:122-125`(budget-breach writer) が type 無しで ceo-decisions 追記。→ type 付与し3 writer 統一。
- **FIND-003(critical)**: `bin/ceo-run.sh` に catch-all `*)` 無し→typo で live 無制限 agent 起動(RED phase で実発火した footgun)。→ `*)` で usage+exit 2、回帰テスト追加。
adversary が verify した positive: LAST_PASS_MARKERS が実 healthcheck パスと一致 / ceo-runner.plist byte 不変 / schema subset check で既存 reader 非破壊 / registry atomic write 正当。

## 残（connector 処理後に serialize）
- [ ] #6 fix-loop: FIND-001/002/003 修正 → 再 adversary PASS
- [ ] merge 後 live で CEO no-args pass → ceo-decisions.jsonl に判断行≥1（独立読返し）
- [ ] enforcement: paused-gate が loop 起動を拒否する挙動を test/実行で観測
- [ ] cron 4件 stale の 07:00 JST 後の自然復帰を `openclaw cron runs` で確認
