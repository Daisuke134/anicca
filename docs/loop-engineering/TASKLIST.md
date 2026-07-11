# TASKLIST — earn/record/verify を稼げる状態にする（atomic SSOT）

**これがタスクの source of truth。** 設計の正本(spec)は分離: `27-ideal-earn-record-verify-architecture.md`（2種の Anicca / 3層 / 図）。上位方針 = `23-...redesign.md §10`。
**進め方（Dais 2026-07-12 明示）**: ここから **main(私) が自分で build、1つずつ**。builder は信用せず、その出力は「下書き」として fresh adversary(Sonnet)+own-eyes で検証し、良い所だけ取り私が仕上げる/作り直す。3つ同時にやらない。
**Done 判定**: 金の真実 = wallet on-chain external:true のみ。report/test-green は稼ぎでない。各 atomic は「検証可能条件」を満たし私が own-eyes した時のみ ✅。

凡例: ⬜ 未着手 / 🔄 進行中 / 🧪 検証待ち(builder下書きあり) / ✅ done(own-eyes)

---

## #1 ledger 一意化  — status: ✅ DONE(2026-07-12, main merged + live quarantine, own-eyes)
- [x] 1a. canonical = `<ANICCA_HOME>/skills/earn/state/earn-ledger.jsonl`(6 writer が既に合意)。founder-loop の `state/earn-ledger.jsonl` は別物(GATE-0専用)＝意図的分離、merge しない
- [x] 1b. `resolveEarnLedgerPath()`(JS) + `resolve_ledger_path()`(Py) で両言語が同一 canonical を返す
- [x] 1c. `filterOwnWalletRows()`(JS)/`filter_own_wallet_rows()`(Py) = 自 wallet allow-list、walletless(sol/hl/narrate)は通す、他 wallet は fail-closed 除外
- [x] 1d. **live founder ledger の他 wallet 295行(a3cdd4/b9dd3b等)を `.earn-ledger.quarantine.jsonl` へ退避、自分170行保全、.bak 作成（非破壊、own-eyes 検証）**。汚染行に external:true は0件だった(偽稼ぎは無し)
- [x] 1e. JS 18/18 + Python 14/14 = 32/32 pass（私が自分で実行確認）
- 検証済み: main に merge(ledger.mjs grep=3)、live ledger は 0x810f のみ、読む場所が一意

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

## #4 build loop 一本化  — status: ✅ 既に達成(2026-07-12 own-eyes で判明、実質no-op)
- [x] 検証: `founder-loop.sh` は **claude を呼ばない**（record-earn.mjs = 唯一の ledger writer + ceo bandit、prompt.txt 無し）。`claude --model sonnet -p` を呼ぶ build loop は **claude-p-mainloop ただ1本**。→ 「2つの重複 claude build loop」は存在しなかった（doc27 旧記述が誤り、私の前回 stale-read が原因）
- [x] つまり大脳 build loop は既に1本。追加統合は不要。builder が入れた mainloop の model override(`CLAUDE_P_MAINLOOP_MODEL`)は任意採用（未 merge、優先度低）
- 注: founder-loop(30min, deterministic 記録+CEO) と mainloop(6h, claude build) は**別役割**で、統合してはいけない（記録を6hに遅らせるのは害）

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
