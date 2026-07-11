# TASKLIST — earn/record/verify を稼げる状態にする（atomic SSOT）

**これがタスクの source of truth。** 設計の正本(spec)は分離: `27-ideal-earn-record-verify-architecture.md`（2種の Anicca / 3層 / 図）。上位方針 = `23-...redesign.md §10`。
**進め方（Dais 2026-07-12 明示）**: ここから **main(私) が自分で build、1つずつ**。builder は信用せず、その出力は「下書き」として fresh adversary(Sonnet)+own-eyes で検証し、良い所だけ取り私が仕上げる/作り直す。3つ同時にやらない。
**Done 判定**: 金の真実 = wallet on-chain external:true のみ。report/test-green は稼ぎでない。各 atomic は「検証可能条件」を満たし私が own-eyes した時のみ ✅。

凡例: ⬜ 未着手 / 🔄 進行中 / 🧪 検証待ち(builder下書きあり) / ✅ done(own-eyes)

---

## #1 ledger 一意化  — status: 🧪(builder下書き worktree ledger-uniqueness、要検証)
- [ ] 1a. 3つの earn-ledger パスを grep 全特定、canonical を確定
- [ ] 1b. `defaultEarnLedgerPath()` を canonical(`$ANICCA_HOME/state/earn-ledger.jsonl`)へ統一
- [ ] 1c. reader に wallet フィルタ（自 instance 以外を除外）
- [ ] 1d. 混入 `0xa3cdd4` 行を `.quarantine.jsonl` へ move（削除しない）
- [ ] 1e. pure path 解決 + filter reader を unit test（RED→GREEN、own-eyes 実行）
- 検証可能条件: 1 instance=1 canonical ledger、読む場所が一意、他 wallet 行が除外される

## #2 pm reconcile 配線  — status: ⬜(#1 待ち)
- [ ] 2a. worktree の `reconcile.mjs` を本番 `skills/earn/lib/` へ
- [ ] 2b. pass 末尾で毎 wake `reconcile` 呼ぶ（HL reconcile.py と同形）
- [ ] 2c. reconcile 先を #1 の canonical パスに向ける
- [ ] 2d. 「負け・買いコストが負 drift で載る」を test + own-eyes
- 検証可能条件: pm でも ledger 合計 ≡ wallet delta

## #3 earn loop 一本化  — status: ⬜(#2 後)
- [ ] 3a. `pm-earner` launchd job を unload/廃止
- [ ] 3b. registry で polymarket-trade が index.mjs earn-menu に載るか確認、無ければ登録
- [ ] 3c. index.mjs 経由でのみ pm が回ることを確認（二重稼働解消）
- 検証可能条件: claude-p の earn loop が1本、pm は menu 経由のみ

## #4 build loop 一本化  — status: 🧪(builder下書き worktree build-loop-unify、要検証)
- [ ] 4a. mainloop + founder-loop を1スクリプトに統合
- [ ] 4b. 統合 prompt に「大脳=小脳を稼げるようにする専任、稼ぎ自体しない」明記
- [ ] 4c. SWITCHOVER.md（旧2 job unload→新1 job load の1コマンド）
- [ ] 4d. 親が own-eyes 後に実 launchd 切替
- 検証可能条件: 大脳 loop が1本、cron 重複解消

## #5 AGENTIC 検証実装(reality-verifier)  — status: 🧪(builder下書き worktree reality-verifier、要検証)
- [ ] 5a. `.claude/agents/reality-verifier.md` を doc24 準拠で作成
- [ ] 5b. 検証項目: report vs on-chain / 空稼働 / 内部送金 / mock / narrate-only
- [ ] 5c. DETERMINISTIC と役割境界を定義に明記
- [ ] 5d. spawn 配線案（self-fix/週次から fresh）
- 検証可能条件: fresh adversary が report vs on-chain 突合し PASS/FAIL を出す

## #6 own-eyes 1 wake  — status: ⬜(#1-3 後)
- [ ] 6a. 小脳 loop を1 wake 実行
- [ ] 6b. wallet on-chain delta = ledger delta を私が確認
- 検証可能条件: 記録と真実が一致

## #7 実稼ぎ  — status: ⬜(最後・唯一の gate)
- [ ] 7a. external:true 実 tx で wallet が増えるまで回す
- 検証可能条件: wallet on-chain が実 tx で増える

---

## 依存グラフ
`1 → 2 → 3 → 6 → 7`（earn/記録の直列）。`4`,`5` は独立ファイル群 → 先行可。
main が1つずつ処理。builder 下書き(#1/#4/#5)は戻り次第 adversary+own-eyes で検証、良ければ採用・悪ければ私が作り直す。
