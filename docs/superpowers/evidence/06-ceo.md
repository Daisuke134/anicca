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

## fix-loop → 再 adversary(Opus) = PASS（2026-07-11）
FIND-001/002/003 全 RESOLVED（commit ebb1d93）: last_observed_at を実 stamp(cost_self_report_check.stamp_last_observed_at→ceo_status から呼出)/ ceo_budget に type 付与(3 writer 統一)/ ceo-run.sh に `*)` catch-all(未知フラグで exit2、live core 起動せず)。独立で 107/107 green 確認済。verdict=`.vcsdd/features/ceo-revive/reviews/sprint-2/`。
→ #6 コード完成(builder GREEN + fresh Opus PASS)。残 = live E2E(connector fix 後に serialize)。

## 残（connector fix 完了後に serialize）
- [ ] #6 fix-loop: FIND-001/002/003 修正 → 再 adversary PASS
- [ ] merge 後 live で CEO no-args pass → ceo-decisions.jsonl に判断行≥1（独立読返し）
- [ ] enforcement: paused-gate が loop 起動を拒否する挙動を test/実行で観測
- [ ] cron 4件 stale の 07:00 JST 後の自然復帰を `openclaw cron runs` で確認


## LIVE E2E 成功（2026-07-11 07:0x JST、独立読返し）— #6 実質完了
ceo-run.sh に env -u ANTHROPIC_API_KEY fix(commit 340ea7b) を当て CEO core を live 起動:
- **ceo-decisions.jsonl に実 decision 1行永続化**（`--record-pass`）: `{"type":"weekly-eval","reviewed":[全10loop],"changed":[],"reason":"全live loop が budget cap 大幅下回り...life-manager 2連続no-actionだが sample薄い...次pass watching、変更なし"}` = genuine judgment が永続化。
- **last_observed_at stamp 実働**（ceo-status.sh 経由、registry 独立読返し）: bounty=2026-07-11T05:32 / connector=07-11T03:12 / gig=07-08T22:17 / affiliate/life-manager/explorer も実 ts、marker無し(capafy/article/pm/hl)=None。CEO が loop 生死を可視化。
- **cost 自己申告照合が fabrication を live 検知**: `cost_claim_warning: affiliate cost-claim-unbacked（marker fresh age=76021s なのに cost-events 行なし）` = investigation の affiliate 偽申告を自動検出。
- **autonomous scheduler**: `ai.anicca.ceo-weekly-eval` plist load 済（launchctl list 表示）。
- **cron codex-harness drift**: 4件(reelclaw/larry/watercolor)が 07:00 JST で error→**running** に復帰（harness 修理 + 自然復帰を実証）。

### #6 §10 達成状況（正直）
- ✅ ceo-decisions ≥1（genuine 永続化） / ✅ last_observed_at 実 stamp / ✅ cost 照合が affiliate fabrication 検知 / ✅ autonomous scheduler / ✅ cron drift 復帰。
- ⚠️ 「enforcement を allocation 変更で live 観測」= CEO が薄データで正しく no-change 判断したため未発生（強制=fake なのでしない）。enforcement machinery は adversary+test 検証済み。real signal 蓄積で CEO が変更を出せば観測される（affiliate 偽申告 + gig stalled が last_observed_at/照合で可視化済 = 次の判断材料）。
- ⚠️ cost 自動行: bounty=0.95 実在、affiliate/gig は cross-check が「記録してない/停止」を検知（=honest surfacing）。

→ #6 = **CEO が生きた**（判断永続化・loop生死可視化・偽申告検知・autonomous化）。builder GREEN + adversary PASS(code) + live E2E 独立読返し。
