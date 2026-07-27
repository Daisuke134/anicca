# Crypto track handoff — Life Manager FINANCIAL organ（13d-b engine本番稼働後）

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
| 収支台帳 | `lib/earnings-ledger.js` + `lib/earnings-runtime.js` + `lib/polymarket-cycle.js` + `lib/x402-sale-ledger.js` + `lib/the402-work-provenance.js` | append-only、minor-unit BigInt、損失月も盛らない月次 rollup。**13c-PMのproduction実収支行は1件**: `financial_realized_loss=$3.15`。SELL/WORK bridgeはBase finalized receiptと正確なUSDC Transferを再検証し、The402 settlement+terminal jobが一意に揃う時だけ`x402_work`へ分離する。self-pay/曖昧provenanceは拒否。外部収入はまだ`$0.00` |
| user payout | `lib/payout-policy.js` + `lib/base-usdc-payout.js` + `lib/payout-runtime.js` + `scripts/run-agent-payout.js` | **PR #1188 / production launchd稼働**。verified profit・Base残高−`$35` reserve・transaction capの最小値だけを送る。deterministic EIP-3009 nonce、専用mainnet facilitator、exact receipt、tenant UID、記帳→TG順。production 2 run / exit 0、現残高0で`no_verified_surplus`、tx/TGは未実証 |

## 次に刺す2点（13d-b engine完了、実着金/実送金は自動待機）

```
13c-SELL/WORK: observer→settlement verifier→provenance classifier→earnings-runtime bridgeは本番稼働済み
          → colony外buyer/job累計$1の実着金待ち（非blocking、現在$0.00）
13d-b:  engineは本番稼働。実tx + §9.11 TGはwalletが$35 reserveを超えた最初のverified surplusで自動実証
REPORT-1: active cursor。daily/weekly TGとpanelを同じledger rollupへ接続し、停止理由と分配可能額を同じ数字にする
```

13c-PM evidence:
`docs/evidence/agent-economy/2026-07-27-polymarket-tatiana-cycle.json`。
production row 1件、再実行duplicate、月次損失報告、Polygon残高の独立再読込まで完了。

13c-SELL bridge evidence:
`docs/evidence/agent-economy/2026-07-27-x402-ledger-bridge.json`。
launchd実発火exit 0、候補/verified/production rowはすべて0。これは接続の生存証明であり外部売上証明ではない。

13c-WORK bridge evidence:
`docs/evidence/agent-economy/2026-07-27-the402-work-ledger.json`。
実入札2件は未採用。acquisition/provider/worker/settlement/accounting loopはliveだが、jobs/threads/settled/work rowはすべて0。
これは自動仕事・分類接続の生存証明であり、仕事成功や外部収益の証明ではない。

13d-b payout evidence:
`docs/evidence/agent-economy/2026-07-27-13d-base-usdc-payout.json`。
production launchd 2 run / exit 0、USDC 0・ledger 0の独立readback、`no_verified_surplus`、facilitator未起動を記録。
これは送金機械とゼロ状態の生存証明であり、実tx・実TG receiptの証明ではない。

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
