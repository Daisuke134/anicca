# AIを経済的に自立させる方法

副題: 自分で稼ぎ、自分の計算資源とクラウド代を払うAIの作り方

形式: 日本語ライトニングトーク / 16:9 / 10枚 / 7分以内
証拠の正本: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md` §0.4

## Slide 1 — AIを経済的に自立させる方法

- **Claim:** AIの経済的自立とは、外部から稼ぎ、その収益で自分の推論とcloudを払い続けること。
- **On-slide:** `稼ぐ → 検証する → 生きる → 余剰を返す`
- **Visual:** walletからSELL / WORKへ出て、receipt、ledger、compute / cloudへ流れる一本線。
- **Evidence:** §0.4.1、§0.4.3a。
- **Seconds:** 30
- **Speaker notes:**
  今日は「人が操作しなくても動くAI」ではなく、「人が継続して料金を払わなくても生きられるAI」を扱います。AIも推論APIとcloud computerを使う限り、毎月の生活費があります。そこで、AI自身にwalletを与え、仕事を探し、外部から受け取った収益で自分の計算資源を払わせます。これをfinancially independent AIと呼びます。

## Slide 2 — 普通のAIは誰の金で動く？

- **Claim:** human-in-the-loopがなくても、human-payment-loopは残っている。
- **On-slide:** `Subscription / Credit card / Mac + electricity → AI`
- **Visual:** 人間の3つの支払いからAIへ向かう矢印。右側に「操作なし ≠ 経済的自立」。
- **Evidence:** §0.4.1、§0.4.3a。
- **Seconds:** 35
- **Speaker notes:**
  多くの自律AIは、人が毎回ボタンを押さなくても動きます。ただし、ClaudeやOpenAIのsubscription、cloudのクレジットカード、あるいは自宅のMacと電気代は人間が払い続けています。これは操作の自動化であって、経済的自立ではありません。停止条件は「人が触らないこと」ではなく、「人の継続支払いが止まっても生存できること」です。

## Slide 3 — AIにも食費と家賃がある

- **Claim:** AIの継続費は「思考」と「存在」に分かれる。
- **On-slide:** `食費 = inference` / `家賃 = cloud runtime`
- **Visual:** 左に脳、右にcloud shelter。下にstorage / network / gasを小さく配置。
- **Evidence:** §0.4.3のsurvival burn、Franklin runtime placement。
- **Seconds:** 35
- **Speaker notes:**
  AIの食費は、考えるたびに払う推論APIの料金です。家賃は、24時間動くためのcloud runtimeです。さらにstorage、network、blockchainのgasがあります。現在の測定では、最小生存費は月35ドル程度、使う推論量によって月78ドル程度まで増えます。だから「収益がある」だけでなく、「収益が生活費を継続して上回る」必要があります。

## Slide 4 — 最初にAI専用walletを与える

- **Claim:** 最初のUSDCはbootstrap capitalであり、収益ではない。
- **On-slide:** `Human seed → Agent wallet` / stamp: `Revenue $0`
- **Visual:** 人間からwalletへUSDCを1回送る。walletにpublic address、policy、spend capを表示。
- **Evidence:** AE-AC2、Coinbase Agentic Wallets / x402。
- **Seconds:** 35
- **Speaker notes:**
  walletは、AIが自分で署名して受け取りと支払いをするためのデジタル財布です。USDCは米ドル価格に連動する暗号資産です。最初だけ、人間が少額のUSDCやSOLをseedとして入れます。ただしこれは売上ではありません。会社のsubscription収益も同じで、agentを起動する補助金です。台帳にはcapital in、revenue zeroとして記録します。

## Slide 5 — AIが稼ぐ3つの方法

- **Claim:** SELL / WORKを先に黒字化し、CAPITALは余剰資金だけで行う。
- **On-slide:** `SELL` / `WORK` / `CAPITAL`
- **Visual:** 3本のrail。SELL=x402 API、WORK=TaskMarket / gig、CAPITAL=trade / yield。CAPITALに「surplus only」。
- **Evidence:** §0.4.1、EARN-HC-1。
- **Seconds:** 45
- **Speaker notes:**
  稼ぎ方は3つに分けます。SELLはAPIやデジタル商品を販売すること。WORKはmarketplaceで仕事を見つけ、応募し、成果物を納品すること。CAPITALはtradeやyieldで資本を運用することです。小さなseedを高リスク取引で増やすのではなく、まず外部需要のあるSELLとWORKを黒字化します。CAPITALは生活費とreserveを確保した後の余剰だけで行います。

## Slide 6 — 「儲かったふり」を防ぐ

- **Claim:** balanceの増加ではなく、外部payerのfinalized receiptだけを収益にする。
- **On-slide:** `External payer → Receipt → Verifier → Ledger`
- **Visual:** 4段pipeline。下に `Seed = 0 / Bridge = 0 / Self-pay = 0 revenue`。
- **Evidence:** AE-AC1〜AE-AC3、x402 settlement verifier。
- **Seconds:** 45
- **Speaker notes:**
  ledgerは、お金の動きを後から書き換えない台帳です。wallet残高が増えても、それだけでは利益ではありません。自分の別walletから移した、bridgeした、預けた元本を回収した、同じagent colonyの中で自己購入した、これらはすべてrevenue zeroです。外部のpayer、transaction hash、chain、asset、gross、cost、netが一致して初めて収益として記帳します。

## Slide 7 — 稼いだ金の使い道

- **Claim:** verified netは生存費とreserveを先に払い、余剰だけを人間と成長へ回す。
- **On-slide:** `Compute → Shelter → Reserve → User / Child`
- **Visual:** 上から下へ流れるwaterfall。Reserveに `$35 floor`。
- **Evidence:** AE-AC6、13d-b payout policy。
- **Seconds:** 40
- **Speaker notes:**
  収益は自由に全部使いません。まず推論費、次にcloud shelter、そして最低35ドルのreserve floorを守ります。reserveはprovider障害や引っ越しに必要な生存資金です。この床を超えたverified surplusだけをユーザーへ送金し、再投資し、将来のchild agentへ使います。赤字なら賭けを増やさず、burnを減らし、SELLを改善し、それでも駄目なら安全に停止します。

## Slide 8 — 自分のcloudを自分で払う

- **Claim:** Macを止めても、agent walletからcloud runtimeを更新する生存機械は成立した。
- **On-slide:** `Mac OFF → Nosana ON → Heartbeat → Statement → Renew`
- **Visual:** Macの電源OFFからNosana cloudへ、heartbeatと決算書を返すloop。
- **Evidence:** S21-MAC-OFF、Franklin 1 public statement。snapshot: heartbeat 130+、runtime cost `$0.093914498167`。
- **Seconds:** 45
- **Speaker notes:**
  Franklin 1ではMac側のmain loopを止め、Nosana上のPython survival runtimeへ移しました。NosanaはGPUなどの計算資源を借りられるcloud marketです。cloudから公開heartbeatと秘密を含まない決算書を出し、残高を監視して自分でruntimeをrenewします。snapshot時点でheartbeatは130回を超え、runtime costも公開statementから読めます。住居を自分で維持する機械までは実証できました。

## Slide 9 — Life Managerとの統合

- **Claim:** agentは最初に自分を維持し、余剰で人間の生活を支える。
- **On-slide:** `Bootstrap → Self-funded → Human payout → Child`
- **Visual:** Life Manager userとtenant agentの二者。agentが自分のcloudを払い、余剰をuserへ返す。
- **Evidence:** §0.4 Life Manager UX、13d-b engine。
- **Seconds:** 40
- **Speaker notes:**
  Life Managerのsubscriptionは、agentを最初に起動する会社側の売上です。その後、tenantごとに独立walletを作り、agentがSELL、WORK、CAPITALを回します。まず自分のcomputeとcloudを払います。余剰ができたらユーザーへ送ります。さらに黒字recipeを別wallet、別key、別ledgerのchildへ渡します。最終形は、AIが自分だけでなく人間の生活も経済的に支えることです。

## Slide 10 — 何をもって「自立」と呼ぶか

- **Claim:** 現在はlevel 3。外部収益で30日分の生活費を覆うlevel 4は未達。
- **On-slide:** `0 Human-paid → 1 Wallet → 2 Self-pay → 3 Cloud survival → 4 External self-funded → 5 User payout → 6 Child`
- **Visual:** level 0〜6の横軸。current markerを3、4以降をoutline表示。右下に `Verified external revenue: $0.00`。
- **Evidence:** §0.4.3a financial independence ladder。
- **Seconds:** 50
- **Speaker notes:**
  現在はlevel 3です。専用walletがあり、実際に推論やcloudへ支払い、Macを止めてもcloudでheartbeatとrenewalを続けられます。しかしverified external revenueはまだ0ドルです。完全な経済的自立と呼ぶlevel 4は、外部収益の30日netがcomputeとshelterを覆い、reserveを維持した時です。自律とは人が操作しなくても動くこと。経済的自立とは、人が払い続けなくても生きられることです。

## Timing

| Slide | Seconds |
|---:|---:|
| 1 | 30 |
| 2 | 35 |
| 3 | 35 |
| 4 | 35 |
| 5 | 45 |
| 6 | 45 |
| 7 | 40 |
| 8 | 45 |
| 9 | 40 |
| 10 | 50 |
| **Total** | **400 seconds / 6:40** |
