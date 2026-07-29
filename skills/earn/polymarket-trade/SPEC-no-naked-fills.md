# SPEC: pm-no-naked-fills（A = sim-to-real 漏れ止め / §9 R2 / map M7+M2）

## 開発環境
- worktree: `$LIFE_MANAGER_REPO/.worktrees/pm-no-naked/`、branch `feature/pm-no-naked-fills`
- 触るファイル境界（これ以外を変更しない）:
  - `skills/earn/polymarket-trade/positions.py`（per-token 保有を返すよう拡張）
  - `skills/earn/polymarket-trade/market_maker.py`（naked 検知→flatten を pass 冒頭に）
  - `skills/earn/polymarket-trade/bundle_arb.py`（逐次 FOK の片脚残りを unwind）
  - `skills/earn/polymarket-trade/test_no_naked.py`（新規、pure-logic テスト）

## 背景（実証済み根因、§9 + 本 session own-eyes）
pUSD 12.79→4.19（-$8.60）の真因 = **naked 片側約定**。`market_maker.py` は binary market の YES/NO 両側を post_only 指値で置く。両脚約定なら risk-free だが、**片脚だけ約定すると naked 方向ポジが resolution まで残り、逆 resolve で負ける**。`cancel_all()` は未約定の指値を消すだけで、約定済み脚は残す。`bundle_arb.py` は2脚を逐次 FOK 発注するため、YES が約定して NO が kill されると naked YES が残る。

## 不変条件（このSPECの唯一のゴール）
**1パス完了後、binary market に対して naked な単脚ポジション（YES 保有 xor NO 保有）が残ってはならない。** 保有は「両脚揃った bundle（=risk-free）」か「ゼロ」のいずれかでなければならない。

## 要件（全て MUST）

### R1 positions.py: per-token 保有の公開
- MUST: `parse_positions_by_token(json_text) -> list[dict]` を追加する。各 dict は `{asset, market, size}`（asset = clobTokenId、size = 保有株数 float）を持つ。
- MUST: fail-closed（malformed 入力 → `[]`、crash しない、欠損フィールドを捏造しない）。既存 `parse_positions_response` は変更しない（後方互換）。

### R2 naked 検知（pure function）
- MUST: `naked_legs(holdings, market_token_pairs) -> list[dict]` を `market_maker.py`（または新 helper module）に追加する。入力 = R1 の holdings と、対象 market の (yes_token, no_token) ペア列。出力 = naked な脚のリスト `{market, held_token, held_size, missing_token}`（片脚のみ size>0 の market）。
- MUST: 両脚とも size>0（bundle 成立）または両脚とも 0 の market は naked に含めない。
- MUST: 完全に純粋（ネットワーク・wallet・I/O を呼ばない）。単体テスト可能。

### R3 market_maker.py: pass 冒頭で naked を flatten
- MUST: 新規 quote を置く前に、R1+R2 で現保有の naked 脚を検知する。
- MUST: naked 脚があれば、**反対脚を taker で買って bundle を完成させる（yes+no 合計コスト < $1 の時）か、held 脚を best_bid で売って flatten する**。どちらを選ぶかは「flatten コストが小さい方」を選ぶ決定関数 `plan_naked_fix(naked_leg, books) -> {"action":"complete"|"sell", ...}` を pure function として実装し単体テストする。
- MUST: naked 脚が残っている間は**新規 maker-bundle quote を置かない**（漏れを増やさない、fail-closed）。
- MUST: MAX_PASS_SPEND / balance floor の既存 money-safety gate を壊さない。

### R4 bundle_arb.py: 逐次 FOK の片脚残りを unwind
- MUST: leg1（YES）FOK が約定し leg2（NO）FOK が kill/失敗した場合、**即 leg1 を FOK/taker で sell して naked を残さない**。
- MUST: 発注順序に関わらず「片脚だけ約定して終了」が起きないこと。両脚成功 or ゼロ脚（両方 unwind 済）のみ。

### R5 テスト（money-safe、live 発注しない）
- MUST: `test_no_naked.py` を新規作成。R1/R2/R3 の plan/R4 の unwind 判断を **pure function として mock データで検証**する。実 wallet・実 CLOB 発注を一切呼ばない。
- MUST: 少なくとも次のケースを含む: ①片脚のみ保有→naked 検知される ②両脚保有→naked でない ③naked に対し complete/sell の安い方を選ぶ ④bundle_arb で leg2 kill 時に leg1 unwind 判断が出る。

## 非ゴール（やらない）
- backtest fixture（pm_backtest_strategy.py）の改修は本 SPEC では行わない（別 feature）。live の漏れ止めに集中する。
- pick.py（directional consensus）は触らない。

## Done 判定
- `python3 -m pytest test_no_naked.py -q`（or 既存 runner）が green（私が own-eyes で実行して確認）。
- adversary（fresh context, Sonnet）が spec+impl を blocking 0 件で PASS。
- 不変条件「1パス後に naked 単脚が残らない」がコード経路で保証されることを adversary が確認。
