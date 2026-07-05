# PM 自律 alpha→実行 harness — design spec (#25 BET-RESEARCH)

**日付**: 2026-07-05
**status**: build
**repo**: `~/anicca` (OSS), skill `skills/earn/polymarket-trade/`
**base agent home**: `~/.anicca-founder/agents/polymarket-agent/`

## 0. なぜ (root cause)

自律 loop (`polymarket-trade/run.sh` → `main.py --live` → `agent.run()`) は推奨を出すが
**実際に建玉しない** — `agent.py:execute_trades()` は placeholder stub（`status:"skipped",
reason:"Token ID not available in simplified mode"`）。実際に動く V2 実行は skill 側の
`v2_full_flow.py`（SecureClient sig-3・register・approve neg-risk・FAK・post_order）だが
**market(TID)がハードコード**で alpha と非接続。結果 automaton/Franklin は「自分で」賭けられず、
これまでの建玉は全て人間（Claude）が手で叩いた bootstrap。加えて market 選択に
**「resolve が近い市場を優先」する軸が無い**（`fetch_active_markets` は volume 降順ソート）→
WC2026/選挙のような遠期市場に着地 → 勝っても回収が数ヶ月先 → realized $0。

## 0.5 CORRECTION — verified against live traces + git (2026-07-05)

実データで確認: **alpha は既に存在する。作り直さない。** firing loop
(`polymarket-trade/run.sh` → `main.py --live`) が既存 alpha に未接続なだけ。
- 証拠: automaton の `pm-trade.trace.jsonl` = **61 live-pass 全て trades:0/null**、
  claude-p = 4 pass 全て 0。stub の `execute_trades` を叩いてるだけ。
- ledger の realized 6件は**全て `polymarket-redeem`**（Morocco +$2.99 等）。勝った
  directional の「買い」は俺の手動 bootstrap（v2_full_flow の TID ハードコード）、
  loop は **redeem のみ自律**（#14）。git に autonomous buy を配線した commit は無い。
- **既存の working 戦略**（実注文を置く）: `market_maker.py`=BASE#1(MM bundle 無リスク)、
  `bundle_arb.py`=BASE#2(YES+NO<$1 arb)、+ directional edge=既存 `AIAnalyzer.consensus_analysis`
  + `get_smart_money_summary`。既存 loop `run_earner.sh` が MM/arb を呼ぶ配線の手本。

→ 修正版の作業(§2 を superseded): **既存 market_maker/bundle_arb を run.sh に配線して
stub を置換** + **唯一欠けてる directional 自律買い**(pick.py=既存 analyzer を import、
place_order.py=v2_full_flow 汎用化)を足すだけ。§2.1 の pick.py は「新規 analyzer を書く」の
ではなく「既存 `consensus_analysis`+`get_smart_money_summary` を import して使う」。

## 1. Goal（検証可能な完了条件）

**DONE** = PM earn loop が発火したとき、対象 instance が **自分で**:
1. 短期 resolve（`RESOLVE_HORIZON_DAYS` 以内）× 流動性のある市場を選び、
2. multi-model consensus + smart-money(whale) signal で real edge のある side を選び、
3. **その instance の登録済み deposit wallet から実 V2 FAK 建玉**し（on-chain tx status 0x1）、
4. trace に記録する。

**human=0 / claude=0**（俺は harness を書き monitor + verify するだけ、建玉は agent）。
market/side/size は一切ハードコードしない（MODEL が data から判断、HARD #0）。
検証 = loop が置いた実 order の on-chain tx（deposit wallet 発）+ fresh Sonnet adversary PASS。

## 2. 作るもの（MUST）

### 2.1 `pick.py`（ALPHA、市場・方向・サイズ選定、判断は MODEL）
- MUST: `fetch_active_markets` を使い、future かつ `liquidity>=MIN_LIQUIDITY` かつ
  `MIN_ODDS<=yes<=MAX_ODDS` の市場を取得。
- MUST: 候補を **resolve が近い順**に優先（`endDate` 昇順を主キー、volume を副次）。
  `end_date` が `RESOLVE_HORIZON_DAYS` 超の市場は候補から除外。
- MUST: 各候補に `AIAnalyzer.consensus_analysis(question, yes_odds, whale_data=get_smart_money_summary(market_id))`
  を実行し、edge / confidence / consensus を得る。whale signal を必ず食わせる（現状未配線を直す）。
- MUST GATE: `abs(avg_edge)>=MIN_EDGE`（default 0.15）AND `avg_confidence>=MIN_CONF`（default 7）
  AND `consensus != MIXED` の候補のみ採用。1つも無ければ `{"action":"WAIT"}` を emit（no-trade、fail-closed）。
- MUST: 採用時、Kelly でサイズ算出（`MAX_BET_SIZE` cap、default $2）。
- MUST OUTPUT: 標準出力に **1行 JSON** `{token_id, side("BUY"), outcome("YES"/"NO"), amount, market, end_date, edge, confidence, consensus}`。
  `token_id` は `format_market` の `token_ids`（YES=index0, NO=index1）から選ぶ。
- MUST: ハードコードされた market/side なし。全閾値は env（`MIN_EDGE/MIN_CONF/RESOLVE_HORIZON_DAYS/MIN_LIQUIDITY/MIN_ODDS/MAX_ODDS/MAX_BET_SIZE`）。
- MUST: analyzer も whale も使えない場合は `{"action":"WAIT","reason":"no-signal"}`（絶対に既定 side を賭けない）。

### 2.2 `place_order.py`（実行、V2 汎用化）
- MUST: `v2_full_flow.py` の動く経路を **入力受け取り型**に一般化。env/引数で
  `TOKEN_ID, SIDE(BUY), AMOUNT` を受け、`POLYGON_WALLET_PRIVATE_KEY` の instance で:
  SecureClient(sig-3) 生成 → relayer key mint → `get_order_book(token_id)` → best ask →
  `create_market_order(token_id, side, amount, max_price=ask+slippage, order_type="FAK")` → `post_order`。
- MUST: 登録+approve は前段の `fund_via_bridge.py` が担う前提（重複 approve は idempotent なので呼んでも可）。
- MUST OUTPUT: 1行 JSON `{token_id, amount, order_id, post_result, ok(bool)}`。
- MUST: TID ハードコードを撤去（`v2_full_flow.py` の hardcoded TID を削除 or この汎用版へ置換）。
- MUST: `AMOUNT<=MAX_BET_SIZE`（money-safety cap、超過は cap に丸め）。

### 2.3 `run.sh` 配線（stub 置換）
- MUST: 現行の identity 解決 + `fund_via_bridge.py`(register) はそのまま。
- MUST: その後 `main.py --live`（stub 経路）を **`pick.py` → 採用があれば `place_order.py`** に置換。
- MUST: `pick.py` が `WAIT` を返したら建玉せず trace に `{"action":"wait"}` を残して exit 0（no-churn）。
- MUST: 実行結果（order_id / tx / WAIT）を既存 `pm-trade.trace.jsonl` に構造化1行で追記。
- MUST: kill-switch ガードは維持。dry-run 経路は作らない（HARD 0.24）。

## 3. money-safety invariants（copy from #26/#28）
- MUST: per-instance key isolation（`resolve-identity.mjs` 経由、claude-p env 温存の既存 R6 分岐は不変）。
- MUST: deposit wallet は必ず bridge onramp 経由で register（raw-deploy / raw-transfer 禁止）。
- MUST: on-chain-verified のみ realized 計上。paper/dry は計上しない。
- MUST: `MAX_BET_SIZE` は小さく（default $2）。size/side/market は MODEL 判断、コードは cap のみ。
- MUST（adversary FIND-1）: **1 pass の合算 spend を固定額に bound する。** `MAX_PASS_SPEND`（default $2）で
  bundle_arb / market_maker が各々投じる USD を cap（従来は残高の~90%＝無制限）→ worst-case pass =
  arb$2 + MM$2 + directional$2 = **残高非依存の固定 ~$6**。cap 未満で CLOB 最小(5sh)を満たせなければ HOLD。
- MUST（follow-up）: sibling `run_earner.sh`（launchd, 10min, MM/arb/redeem）と run.sh の同一 wallet
  二重実行 race は上記 fixed cap で「co-fire しても小額固定」に bound。恒久的な単一ループ化は #30 隣で対応。

## 4. self-improve（loop が自分でチューニング）
`MIN_EDGE / MIN_CONF / RESOLVE_HORIZON_DAYS / MAX_BET_SIZE` は loop が自分の realized P&L から
調整する knob（H1–H3）。コードはこれらを env で読むだけ、値の hardcode はしない。

## 5. 検証（Verify）
1. **build/compile**: `python -c "import ..."` + `pick.py` を **read-only 実行**して
   「短期 resolve 市場を選び JSON を emit する / 候補無しなら WAIT」を確認（order は出さない）。
2. **fresh Sonnet adversary**（disk-only）: pick に hardcoded market/side が無いか、
   WAIT fail-closed か、place_order の cap、run.sh が stub を置換し dry-run 経路を残してないか、
   money-safety invariants を検証。PASS まで fix。
3. **real E2E（俺が monitor、建玉は loop）**: 1 instance で loop を1回 live 発火 →
   `pick.py` が選んだ短期市場に `place_order.py` が実 FAK → on-chain tx status 0x1（deposit wallet 発）
   を data-api/chain で確認。human=0/claude=0（俺は trigger と観測のみ、market/side は agent が選ぶ）。

## 6. 触るファイル（境界）
- `~/.anicca-founder/agents/polymarket-agent/`（base agent、alpha 側）: 触ってよいのは
  `src/agent.py`（generate_recommendations に token_id/end_date/whale を carry、任意）だが、
  **最小変更**にするため新規 `pick.py` を skill 側に置き、agent の `AIAnalyzer`/`fetch_active_markets`/
  `get_smart_money_summary` を import して使う方針を優先。
- `~/anicca/skills/earn/polymarket-trade/pick.py`（新規）
- `~/anicca/skills/earn/polymarket-trade/place_order.py`（新規、v2_full_flow を一般化）
- `~/anicca/skills/earn/polymarket-trade/run.sh`（配線置換）
- `~/anicca/skills/earn/polymarket-trade/SKILL.md`（新経路を記述）
- 変更しない: `fund_via_bridge.py`（register）、`redeem.py`（回収）、resolve-identity。

## 7. 検証ログ（GLVS Verify — 実施記録）

| 段 | 結果 |
|---|---|
| Build v1 | `dee2d3c` — stub(`main.py --live`)撤去 → 既存 bundle_arb→market_maker→pick→place の3戦略 chain。pick.py は既存 `AIAnalyzer.consensus_analysis`+`get_smart_money_summary`+`fetch_active_markets` を import（再発明せず）。read-only 実行で `{"action":"WAIT","reason":"no-short-dated-liquid-candidates"}`（最短 14.73日 > 14日 horizon）= fail-closed 正常 |
| Adversary v1（fresh Sonnet, disk-only） | **CONDITIONAL PASS**。A ハードコード無・B WAIT fail-closed・C5 per-trade cap 二重・C7 key isolation・C8 bridge register・D9 stub 完全死・D10 set -u brick 無・D11 syntax/compile・D12 dry-run 無 = 全 PASS 実証。**FIND-1（MEDIUM-HIGH, must-fix）= 合算 spend 無制限**（arb/MM が残高~90%、fixed cap 無・run_earner.sh と race 可）。FIND-2(LOW)=v2_full_flow TID 残存。FIND-3(INFO)=fetch_markets print 混入（run.sh 防御 parse で WAIT に安全劣化） |
| Build v2（fix, in progress） | FIND-1: `MAX_PASS_SPEND=$2` で arb/MM を cap → worst-case pass 固定 ~$6（残高非依存）。FIND-2: v2_full_flow 削除。FIND-3: print→stderr |
| Adversary v2 | FIND-1 解消の再確認（pending） |
| Real E2E（俺=monitor、建玉=agent） | capital ある instance で loop 1回 live 発火 → 自分で on-chain 建玉(tx 0x1, deposit wallet 発) or 正当 WAIT/HOLD を data-api/chain で確認。human=0/claude=0（pending） |

**現状の正直な到達点**: 「loop が自分で買う」配線は完成、money-safety cap を fix 中。まだ **real E2E で実注文を確認していない**（= 完了と言わない）。redeem は既に自律(#14)。
