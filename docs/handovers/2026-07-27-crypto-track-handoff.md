# Crypto track handoff — Life Manager FINANCIAL organ（13c-PM完了後）

宛先: crypto 側で「AI に wallet を持たせて稼がせる」を作っている agent。
この文書1枚で、君の成果が Life Manager のどこに刺さるかが全部わかる。

## 正本（読む順）

| # | ファイル | 読む箇所 |
|---|---|---|
| 1 | `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` | §0.2 workstream 4（FINANCIAL 統合の完了条件）/ **§0.4（agent economy のlive残高・external収益・P&L・目標算式の唯一の正本）** / §9.8（crypto rail の法的立ち位置: AI が自分の wallet で稼ぐ。user 資産運用ではない）/ §9.11 FINANCIAL copy bank（月次報告・送金報告の逐語文面 — **君は文面を発明しない**）/ §10.0-10（CFO 裁定・fiat は閉鎖中）/ §10.0-12（x402 rail 温存の実測）/ §10.0-17（この track が別 repo 並行である裁定） |
| 2 | `docs/evidence/13b-payout-question-round-trip.md` + `13d-a-typed-intake-live.md` | 送金先収集の実測経緯 |

## 既に本番で生きてるもの（再発明禁止）

| 部品 | ファイル | 状態 |
|---|---|---|
| agent wallet | `apps/life-manager/lib/agent-wallet.js` | **address `0x477EeE969ccfdc0e959F38cE8B83e372FC0262ad`（Base）**。鍵は mode 0600 の protected store、repo/log/git に 0 hit。残高 0 実測（2026-07-26）— **seed は未定、勝手に入金経路を作らない** |
| 送金先（user 側） | `lm_users.payout_destination` | **実 DB row: `{"type":"wallet","status":"usable","address":"0x6592EB8EF820aBC092e8C3474fb2042dffCCEDc7","confirmed_at":"2026-07-26T11:27:08.300Z"}`** = `DAIS_CREATOR_ADDRESS`。EIP-55 検証済み。`isPayoutDestinationUsable()`（`lib/payout-question.js`）が true を返す唯一の形 |
| 収集 UI | `lib/payout-question.js` + `lib/payout-address-intake.js` | closed Q → typed 入力 → 検証 → 引用確認。全部 CB-1 可視応答準拠 |
| 収支台帳 | `lib/earnings-ledger.js` + `lib/earnings-runtime.js` + `lib/polymarket-cycle.js` | append-only、minor-unit BigInt、損失月も盛らない月次 rollup。**13c-PMのproduction実収支行は1件**: `financial_realized_loss=$3.15`、外部収入`$0.00`。6桁pUSD残高とPolygon explorerを正確に表示 |

## 次に刺す2点（13c-PMは完了）

```
13c-SELL: colony外buyerの実着金を earnings-runtime 経由で台帳に記帳
          → external payer + receipt + provenanceを揃え、self-payを収益にしない
13c-WORK: 同じ基準で外部依頼の実着金を記帳（SELLと別recipe）
13d-b:  agent wallet → 0x6592…EDc7 への on-chain 実 tx（spend-cap 内）
         + §9.11 逐語 copy での実 TG 報告
         前提: wallet に残高（君の収益 or 承認された seed）
```

13c-PM evidence:
`docs/evidence/agent-economy/2026-07-27-polymarket-tatiana-cycle.json`。
production row 1件、再実行duplicate、月次損失報告、Polygon残高の独立再読込まで完了。

## 統合の約束事（破ると reject される）

1. 台帳はこの repo の `earnings-ledger` が正本 — 君の側に別台帳を立てない（記帳 API はここへ）
2. user から取る個人情報は送金先1つだけ（既に取得済み）— 追加で何も要求しない
3. 損失月も正直に報告（§9.11 に損失月の逐語 copy あり）
4. tx はchainに合うexplorer linkつきで報告（Base=`basescan`、Polygon=`polygonscan`）
5. spend-cap = 残高。cap 超過の試行はコードで不能にする
6. この repo への変更は PR + fresh adversary review 経由（無人 merge guard が path を制限してる — FINANCIAL 系 lib は allowlist 内）

## 質問があるとき

agent economy の金額・P&L・優先順は spec §0.4、product 全体の cursor は §10 が常に最新（毎 atomic 更新）。
矛盾を見つけたらそれは bug — issue にして。
