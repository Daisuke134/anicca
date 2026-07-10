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

## 残（pending verification）
- [ ] builder GREEN(tests 実green) + fresh Opus adversary PASS
- [ ] merge 後 live で CEO no-args pass → ceo-decisions.jsonl に判断行≥1（独立読返し）
- [ ] enforcement: paused-gate が loop 起動を拒否する挙動を test/実行で観測
- [ ] cron 4件 stale の 07:00 JST 後の自然復帰を `openclaw cron runs` で確認
