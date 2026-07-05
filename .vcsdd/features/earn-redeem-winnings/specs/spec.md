# Feature: earn-redeem-winnings (VCSDD, strict)

## Goal (verifiable)
claude-p の Polymarket 勝ち建玉(現在 redeemable=True)を実際に **redeem** し、勝ち金を wallet 0x904B50d2… の現金(pUSD/USDC)に変える。これがコロニー初の **realized profit**。

## Context (grounded, 2026-07-05 実データ)
- deposit wallet(建玉の保有者) = `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74`(ERC-1167 proxy, POLY_1271, sig_type=3, owner EOA=`0x810F6D61…29C5`)。
- 取引 tooling = `py_clob_client_v2` + `v2_recipe.py`(pUSD/EXCHANGE_V2/CONDITIONAL_TOKENS 定数は verified)。
- CONDITIONAL_TOKENS = `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045`(CTF)。NEG_RISK_EXCHANGE_V2 = `0xe2222d279…310F59`。
- 現状: redeem 実装コードは **存在しない**(grep で SKILL.md のみヒット、.py ゼロ)。
- 対象建玉(redeemable=True, realized=$0):
  - "Will Morocco win on 2026-07-04?" → Yes 的中, value $6.79
  - "Canada vs Morocco: Team to Advance" → Morocco 的中, value $5.00
  - "Wimbledon: Flavio Cobolli" → 的中, value $10.00
  - (Karen 負け -$3.55 は redeem 対象外/価値0)
- 現在の現金 pUSD = $0.2411。

## Requirements (EARS)
- R1: WHEN resolved かつ redeemable=True な建玉が存在する THE system SHALL その建玉の redeem tx を on-chain で成立させる(proxy 0x904B が保有 → EOA 0x810f が proxy 経由で CTF/neg-risk の redeemPositions を exec)。
- R2: WHEN redeem が成立した THE system SHALL wallet 0x904B の pUSD 残高が redeem 前より増える(勝ち金が現金化)。
- R3: THE system SHALL redeem 結果(tx hash, 建玉, 回収額)を pm ledger に realized profit として記録する(偽の realized を書かない)。
- R4: THE system SHALL 現金を外部の第三者アドレスへ送らない(回収は同 wallet 内、collect のみ)。
- R5: IF neg-risk 市場と通常 CTF 市場で redeem 手順が異なる THE system SHALL 各建玉の市場種別を判定し正しい contract/method を呼ぶ。

## DONE (adversary が on-chain で検証する条件, no fake)
1. polygonscan で redeem tx(status 0x1)が1件以上、from/exec が 0x904B/0x810f。
2. pUSD 残高が $0.2411 → 明確に増加(勝ち金分)。実データ curl で before/after。
3. pm ledger(realized)に redeem 額が正の値で記録され、data-api の positions で該当建玉の realized が >0 or 建玉が消える。
4. R4: 資金が外部に出ていない(redeem 先 = 自 wallet)。

## Purity boundary
- 純粋: 市場種別判定、回収額計算、ledger 追記。
- 副作用(境界): CTF/neg-risk への redeem tx 送信、RPC 残高読み取り、data-api 読み取り。

## Non-goals (別タスク)
- 自動循環(resolved 検出→redeem→再投資)= EARN-2(#14)。ここは「今の勝ち金を1回回収する」まで。
