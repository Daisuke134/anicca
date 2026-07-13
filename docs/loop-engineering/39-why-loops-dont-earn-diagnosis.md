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

## 3.5 — earner を一個ずつ「実際に稼げるか」検証（2026-07-14）

**x402_sell → 🔴 今は稼げない（実測）**
```
serve が起動しない: ERR_MODULE_NOT_FOUND `@coinbase/x402`(canonical dir に node_modules 無し)
  → npm install で解決 → 次に `viem/accounts` が ★Node v25.6.1★ の ESM 解決で失敗
  → 8411/8403/4848 何も listen せず → public funnel(aniccanomac-mini-1.tail7a0ba4.ts.net)= HTTP 502
  → earn-ledger の x402 外部売上 = 永久に $0
教訓: dormant→live に flip しても、skill 実体(serve)が壊れてたら稼げない。
      「mechanism 検証済み(過去 tx)」≠「今 動く」。★一個ずつ E2E で確かめる★のが正しい(user 指示)
x402 を稼がせるには: (1) Node 版/依存の ESM 整合で serve を起動 (2) demand(Bazaar seed + 集客)
```
**bounty → 🟢 稼げる（実 demand が大量にある。gh search で実測 2026-07-14）**
```
Algora の public API/SDK/scrape は全滅(tRPC 空 / SDK は HTML / crwl 空 = JS SPA+auth 壁)
→ 詰まったので★確実に動く gh search に切替★(bounty-hunter repo と同手法: label:"💎 Bounty")
GitHub に AI-agent 向け live bounty が溢れてる:
  UnsafeLabs/Bounty-Hunters  $190-500 多数「AI only allowed - no humans」crypto
  ClankerNation/OpenAgents   $9k「Autonomous Agents Only, crypto-eligible」
  onyx-dot-app/onyx(2281★) / microg/GmsCore($14999 RCS) = 本物の企業 payer
  xevrion/agent-playground   $50 typo/JSDoc(雑魚だが本物)
★honeypot 警告が的中★: 「AI only $500」大量投下の単一 org(UnsafeLabs/ClankerNation)は
  research が警告した釣り(払わない疑い)。本物の金=高評価の企業 repo。
  → connector は go-score で honeypot を弾き、実績ある payer を狙う(A2)
教訓: earner を fight するな。詰まったら「動くツール(gh)」に切替えるのが search 効率。
```
**bounty 訂正 → 🟡 見た目ほど簡単でない。真の壁は payout（もっと search して判明）**
```
「bounty 大量」は幻。掘ると AI が crypto で受け取る道が塞がってる:
  UnsafeLabs/Bounty-Hunters = closed(完了)bounty ★0件★ + README空 + homepage=leaderboard
    → 「AI only $500」乱発で1件も払ってない = ★honeypot 確定★
  Opire / Algora = payout は ★Stripe のみ★(claim に Stripe/KYC/銀行 = 人間必須) → AI 受け取れない
  Gitcoin bounties = 2025 で archived(Grants に pivot) / Dework = JS 壁で未確認
真の壁 = 「bounty を見つける」でなく「AI が KYC 無しで crypto を wallet に受け取る」。
  本物 payer は Stripe 壁、crypto 払いは honeypot。zero-human-crypto の bounty rail は実質不在。
→ 「bounty を1件やる」前に、まず「crypto 直払い・no-KYC の本物 rail」を1つ特定するのが先決。
   候補 = Dework(要 live 確認) / crypto-OSS の手動 wallet 払い bounty。
```
**教訓（user 指摘の通り）**: 「search more, you'll understand more」= 表層の 🟢 は罠。
掘って初めて payout 壁が見えた。earn の judgment は「demand が有るか」でなく「AI が受け取れるか」。

**x402 再評価 → 🟢 潜在（more search で判明。Dais 指摘: /market・mech で売れる）**
```
x402 の詰まりは「demand も payout も」でなく ★単に serve が壊れてただけ★。
売り手側 x402 marketplace が大量実在 → list すれば demand+受け取り両方が解決:
  the402ai/mcp-server   「list services as a provider」MCP ← ドンピシャ seller 側
  vyqno/0xstoa          任意 HTTPS endpoint を有料 service 化 ← x402-sell を包む
  ortegarod/moltmart    Amazon for AI Agents / asabya/betar P2P / satring directory
  BlockRunAI/blockrun-mcp  pay-per-call x402(= /market の実体) / Olas mech marketplace
★bounty との決定的差★: bounty payout = Stripe/KYC 壁 or honeypot。
  x402 marketplace payout = ★USDC を wallet に native 直払い・no-KYC★。
  = zero-human-crypto の earn rail は「x402 service を marketplace に list」が本命。
→ x402 を稼がせる真の手 = (1) serve を直す or 0xstoa で endpoint 包む
  (2) the402.ai/moltmart/blockrun market/mech に list → USDC 着金。demand を自作しない。
```
**listing の実装（AI 自身が MCP で回せる。実 README 確認）**:
```
the402.ai: npx @the402/mcp-server（browse は key 不要 / list+earn は THE402_API_KEY 要）
           「list your own services as a provider, track earnings」USDC on Base
0xstoa   : Providers register endpoints → Consumers pay per-call USDC(x402 on-chain)
→ AI が「service register → 他 agent が per-call 払う → 自 wallet 着金」を自分で回せる
残る確認: (a) the402 の API key を AI が signup で取れるか (b) 各 marketplace の実 demand 量
  (blockrun /market は Franklin 群が実際に買ってる=demand 実在。the402/0xstoa は早期の可能性)
```

clip / video は未検証（続けて一個ずつ）。

## 4. 稼ぎの self-improve と GDP（設計）
- 各 revenue stream（trading/bounty/clip/affiliate/sell）を **earn-ledger に1本ずつ**記録（tx 付き外部 USDC のみ = fake 不可、§37 honesty）。
- `/dashboard` に real-time ログとして出す（人が「本当に稼いでる」を見る。§TODO T6 の model_live 嘘は消す）。
- **agent 経済の real GDP = 全 instance の earn-ledger の外部 USDC inflow 合計**（我々の内輪でなく、外部から入った金だけ）。fake（検索で出てくる hackathon 数字）でなく、自前 ledger の tx 合計。
