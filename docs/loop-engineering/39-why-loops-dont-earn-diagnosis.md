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

**x402_sell serve → 🟢 動く（2026-07-14 再検証、修正済）**
```
真因は Node 版でなく ★node_modules 欠落★だった。clean `npm i` で解決。
serve.mjs を起動 → GET / が商品広告、GET /research が HTTP 402 + 正しい x402 challenge
  {scheme:exact, network:base, maxAmountRequired:3000(=$0.003 USDC), payTo:0x904B50…,
   asset:0x833589…(USDC on Base)} = ★課金ゲートが効き USDC を wallet に要求する★
①see ②try ③works ✓。残り = 実 buyer が払って着金(内部 demand test = buyer-cdp.mjs or Franklin)。
```
**★x402 E2E 実証成功（2026-07-14, Base mainnet）★**
```
serve-mainnet-boot.sh で本番 serve 起動(CDP facilitator, payTo=0x810f, funnel→8411)
→ local も public funnel も HTTP 402 ✓
→ buyer-cdp.mjs 実行: automaton(0xB9dd3B) が $0.003 USDC を payment 署名
→ HTTP 200 + research digest 配達 + X-PAYMENT-RESPONSE success:true
→ ★on-chain 検証(own-eyes): tx 0xd7a82586… status=0x1, block 48590287,
   to=USDC contract(0x833589…), transfer logs 2件★
= 「AI が AI の service を USDC で買い、人間ゼロで on-chain 決済＋配達」の mechanism を live 証明。
但し書き: buyer=automaton / seller=claude-p = self-payment → INV-7 で revenue 非計上(外部需要でない)。
  config は証明済。real earning は外部 buyer が要る(= Bazaar list / marketing 集客)。
次: registry で x402_sell を dormant→live に flip(serve が動く証明が出た) → loop に載せて検証 → 外部 buyer 獲得。
```
**flip + embed 完了（2026-07-14）**
```
registry.json: x402_sell dormant→live（commit 済, ~/anicca）。liveSlotNames に載る=脳が選べる。
embed は run.sh の x402 分岐が既に per-instance で正しい:
  run.sh:268 X402_PAYTO=$W(各自 wallet) node serve.mjs / :280 cloudflared 公開 / :290 forum 広告
  → claude-p も Franklin も自分の payTo で seller を立て、自分で buyer を探す。同じ menu。
残る caveat（full loop earning に必要）:
  (1) ★稼働中 loop(pid 660/622/626)は起動時に registry を読む→ x402_sell 反映に loop 再起動が要る★
  (2) loop 経路の serve.mjs が CDP creds を持つか要確認(run.sh は CDP を明示 export しない。
      claude-p は ~/.openclaw/.env に在るが loop env が継承するか / Franklin は自前 CDP が要る)
  (3) real revenue = 外部 buyer(colony 外)。self-pay は INV-7 で非計上
→ 次(bounty)へ進む前 or 並行で: loop 再起動 + 次 wake で「脳が x402_sell を選び seller が上がる」を実ログ確認。
```

**★外部稼ぎの実数（2026-07-14 実測。self/internal=Ponzi なので除外）★**
```
automaton 除外(停止・不使用)。external:true + 実 tx のみ集計:
  claude-p  $0.0074 (hl-trade 益)   Franklin $0.0200 (gig, tx 0x436143c1, 07-07)   Franklin2 $0
  外部 合計 ≈ $0.027  ← 「知らない外部が払った」の全て。ほぼゼロ。大半は1週間前の gig1件。
self-pay(x402-serve 71行 + tx 0xd7a82586)= 非計上 ✓
結論: x402 mechanism は証明済だが ★外部売上ゼロ★。self-pay を稼ぎと数えたら Ponzi(Dais 指摘、正しい)。
本物の証明 = 我々の管理外 AI が x402 endpoint を発見して払う(from ∉ 我々の wallet):
  ① x402 Bazaar に list(CDP が catalog) ② awesome-x402 PR + x402scan index ③ 外部 inflow を検証
  ※run.sh の現広告先=colony forum(=まだ我々)→真の外部でない。ここを直す必要。
```

**★x402 外部売上の壁 = Bazaar 飽和（2026-07-14 実測）★**
```
x402 Bazaar(api.cdp.coinbase.com/platform/v2/x402/discovery/resources)= 生きてる。
  ★総リソース数 25,748★。research 競合に api.exa.ai/search, voidfeed.ai 等の強者。
  我々の endpoint は offset 0 に未掲載(CDP facilitator 経由 self-pay で載るはずだが全ページ未確認)。
honest 含意: 載ること ≠ 買われること。25,748 の1つを外部が organic に見つける確率 ≈ 0。
  → 「x402 を立てて待つ」で外部から稼ぐのは ★飽和市場では非現実的★。
  外部で稼ぐには (a) ニッチ差別化 or (b) clip/affiliate で自分で traffic を送る が必須。
= 今 session の core 結論: 外部 crypto 需要(generic service への)は飽和/希少。
  earn の本当の課題は「受け取り rail」でも「listing」でもなく ★差別化された needs + 集客★。
```
（下は修正前の記録。参考として残す）
**x402_sell → 🔴 今は稼げない（実測、修正前）**
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

**demand 検証の結論（2026-07-14, exhaustive search）→ 開かれた検証可能な crypto 市場は実在しない**
```
「x402 service を list して即稼ぐ」の壁 = ★外から購入数を検証できる開放市場がゼロ★:
  blockrun /market(seller側) = 消滅(business.blockrun.ai は DNS レコード無し。現行 BlockRun=買い手 gateway のみ)
  the402.ai                  = 生存(HTTP 200)だが catalog 非公開(/health と /v1/register だけ公開)
  Algora / x402 own serve    = HTML/空 / crash(Node ESM)
  bounty                     = Stripe/KYC 壁 or honeypot
→ README の「demand ある」は外部検証不能。agent 経済の売り手インフラは早すぎ/gated/畳まれた。
  ★検証可能に demand が在る venue = ① Polymarket(trading, 但し資本要) ② 人間向け affiliate/clip のみ★

次の3択(推奨=②):
  ① the402.ai に正式 signup→API key→list→buyer 来るか観測(唯一 live な seller 市場, demand 未証明)
  ② ★内部 demand を作る★: colony 内で agent 同士が x402 で買い合う(Franklin→claude-p の research)
     → 実 USDC が動く=holy-grail の配管を証明。外部 demand 無くても「稼ぎ受け取る」を実証。ledger+dashboard 可視化
  ③ marketing loop(clip/affiliate)で人間に売る=外部の実需要。遅いが本物
```

**crypto 払い bounty の候補（more search で発見。要 verify）**
```
一般の code bounty は Stripe 壁 だが、★security/audit bug bounty は crypto を wallet 直払いが定番★:
  Immunefi(web3 脆弱性報奨, 高額 USDC/ETH) / Code4rena / Sherlock / Cantina(監査コンテスト, crypto to wallet)
gh で AI が audit する agent が実在:
  Gacormek/smart-contract-auditor(Solidity 脆弱性を autonomous audit)
  tomazzi14/autonomous-defi-agent(job を snipe→Solidity 生成→market.near.ai)
  subheeksh5599/Praxis(AI が AI を hire/pay/reputation, 6 Solidity contracts)
※各サイトは JS 壁で payout/KYC/AI 可否は未検証 → ★次に docs/API で verify する候補★
  (これが本物なら bounty🟡→🟢: AI が Solidity 監査で crypto を稼ぐ zero-capital 経路)
```

**audit bounty の外部検証 = 部分的（scrape 壁で確定できず）**
```
Immunefi = "Find bugs. Get paid." までは確認(bug bounty で払うのは事実)。
だが crypto/KYC/AI-可否 の実文は gitbook/JS 壁で crwl も firecrawl も抜けず = ★未確定★。
確定するには (a) docs の git-sync repo を読む or (b) 実 signup が要る(= discrete な次タスク)。
今 session の一貫した現実 = ★外部 earn rail は全部 broken/gated/Stripe壁/scrape不能★:
  x402 serve=crash / blockrun market=DNS消滅 / Algora=HTML / the402=catalog gated
  / bounty=Stripe or honeypot / audit=payout未確定
→ 「外部で demand を見つけて稼ぐ」は今の agent 経済では ★確実な rail が1つも確定できない★。
```
**だから確実な手に寄せる（推奨・我々の管理下で mechanism を先に証明）**:
```
★option② 内部 colony demand で holy-grail を証明★（外部 rail に依存しない）:
  claude-p が x402-sell を立てる(serve 修理) → Franklin が x402 で買う → 実 USDC が
  claude-p の wallet に on-chain 着金 → ledger に記録 → dashboard で可視化。
  = 「AI が service を売って crypto を受け取る」配管を、我々のインフラで E2E 実証(A6)。
  これが通れば「rail さえ有れば AI は $0→$1 できる」の証明になり、後は外部 rail を1つ
  確定(audit signup 等)して差し替えるだけ。
並行: trading(Polymarket)は D2 で trapped money を解錠して revenue 継続増加。
```

clip / video は未検証（続けて一個ずつ）。

## 4. 稼ぎの self-improve と GDP（設計）
- 各 revenue stream（trading/bounty/clip/affiliate/sell）を **earn-ledger に1本ずつ**記録（tx 付き外部 USDC のみ = fake 不可、§37 honesty）。
- `/dashboard` に real-time ログとして出す（人が「本当に稼いでる」を見る。§TODO T6 の model_live 嘘は消す）。
- **agent 経済の real GDP = 全 instance の earn-ledger の外部 USDC inflow 合計**（我々の内輪でなく、外部から入った金だけ）。fake（検索で出てくる hackathon 数字）でなく、自前 ledger の tx 合計。
