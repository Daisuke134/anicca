# 39 — なぜ loop が稼がないか（実ログ診断・2026-07-14）

**`~/.anicca-founder/logs/daemon.err.log` の実 brain 出力で診断。記憶でない。**

## 0. 結論（今日の一番大事な発見）

**脳（Sonnet）は正常。知能不足でもない。正しく `run_skill` を valid な slot 付きで出している。**
問題は **plumbing（gate と trapped money）** で、脳はそれを 30+ wake 叫び続けている:
```
[brain] "STRUCTURAL BLOCKER 30+ wakes: HL $7.72 idle margin inaccessible (hl_trade not in
         available skill slots), Polymarket $6.99 pUSD locked in maker legs (skill ignores args,
         issue #1031). Liquid $1.95 below $5 compute buffer."
[brain] "PROMPT/RUNTIME CONTRADICTION: wake prompt displays hl_trade, x402_sell, token_launch,
         yield as pickable, but available skill slots list does NOT include them."
[brain] "earn/polymarket-trade ignores args and runs MM regardless. cook marked DEAD.
         economy/gig slot also missing — broke agents have no take-a-gig path."
```
= narrate は脳の怠慢でなく、**「金を稼ぐ道が全部 menu から消され、自分の金にも触れない」から残った唯一の行動**。

## 1. 真因（4つ。実ログ + catalog-gate.mjs で確認）

### 真因1 ★全 zero-capital earner が registry で status:"dormant" = available slot に載らない★（最重要）
**訂正（2026-07-14, registry.json 実測）**: 当初「risk tag が safe でないから gate が隠す」と書いたが**外れ**。
実測すると x402_sell / economy/gig / earn/clip / earn/video は**既に risk:"safe"**。gate 以前の問題だった。

真因は `prompt.mjs::liveSlotNames` = ★`status==='live'` の slot だけ★を available にする。実測:
```
LIVE な earn slot = earn/sol-trade(capital) / earn/polymarket-trade(capital) / yield(capital) のみ
DORMANT(= available に載らない) zero-capital earner:
  economy/gig(safe) / x402_sell(safe) / earn/clip(safe) / earn/clip-producer(safe) / earn/video(safe)
→ ★broke agent の live な earn は「資本が要る trading」だけ。資本ゼロで稼ぐ道は全部 dormant★
  → $1.95 の脳が選べる earn が実質ゼロ → narrate / self/coordinate / issue-dev しか残らない
  → 235/300 wake narrate の正体。skill 実体は存在(serve.mjs/gig.mjs)、x402_sell は tx 検証済み
```
= zero-to-one を殺していたのは「risk gate」でなく「earner が dormant のまま live 化されていない」こと。

### 真因2 金が trapped、取り出す道が無い
```
HL $7.72 = margin に凍結。hl_trade が menu から消えてて引き出せない
PM $6.99 pUSD = maker legs にロック。polymarket-trade が cancel の args を無視して
                MM を回し続ける(issue #1031) → 回収不能
→ 純資産はあるのに liquid $1.95 のまま = gate をずっと下回る = 真因1 が永続
```

### 真因3 prompt と runtime の slot 不一致
prompt は hl_trade/x402_sell/token_launch/yield を「選べる」と見せるのに、実際の
available-slots には無い → 脳が選ぶ → dispatch されない → 空振り → 別の slot を探す消耗。

### 真因4 narrate 中も compute を焼く（純負）
`config.mjs`: cook(explore)しながら 15分で ~$0.17、~**$0.68/hr** を wallet から焼く。
稼がず焼く = 時間で純資産が減る。

## 2. T13 は稼ぎのブロッカーではなかった（再優先）
脳は既に valid な `tool_calls`(slot 付き)を出している（T3.7 で解決済み）。
→ **T13(MCP 化)はコード清潔化であって、「bet しない」の原因ではない。**
**「loop を稼がせる」真の修正 = 真因1-4** であって T13 ではない。T13 は後でよい。

## 3. 修正の方向（★まだ直さない。記録のみ★）
```
FIX-1 zero-capital earner(economy/gig / x402_sell / earn/clip / earn/clip-producer / earn/video)を
      registry.json で status:"dormant" → "live" に（既に risk:"safe"）。
      ★但し flip 前に各 skill が instance で実際に走ることを検証★(x402_sell=server立つ, gig=board 読める)
      → broke でも menu に earn が出る = zero-to-one の解錠
FIX-2 trapped money を解放: hl_trade を(建玉ありとして)常時可視化 + polymarket-trade が
      cancel/withdraw の args を honor する(issue #1031)
FIX-3 prompt の「選べる options」= 実 available-slots に一致させる(嘘を見せない)
FIX-4 narrate 中の compute 焼却を止める(稼がない wake は最小 compute で寝る)
```

## 4. 稼ぎの self-improve と GDP（設計）
- 各 revenue stream（trading/bounty/clip/affiliate/sell）を **earn-ledger に1本ずつ**記録（tx 付き外部 USDC のみ = fake 不可、§37 honesty）。
- `/dashboard` に real-time ログとして出す（人が「本当に稼いでる」を見る。§TODO T6 の model_live 嘘は消す）。
- **agent 経済の real GDP = 全 instance の earn-ledger の外部 USDC inflow 合計**（我々の内輪でなく、外部から入った金だけ）。fake（検索で出てくる hackathon 数字）でなく、自前 ledger の tx 合計。
