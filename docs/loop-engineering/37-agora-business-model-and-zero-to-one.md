# 37 — Agora のビジネスモデルと zero-to-one（thesis 確定版）

**2026-07-13。実コード（BlockRunAI/Franklin）+ 引用付き web 調査で裏取り済み。俺の記憶ではない。**
関連: `34-TODO-ORDERED.md`（TODO 正本） / `33-COLONY-GROUND-TRUTH.md`（前提）

---

## 0. thesis の転換（今日の一番大事な決定）

```
OLD（今の TODO の暗黙前提）:  AI は trading で稼ぐ（polymarket / SOL / HL）
NEW（Dais の指示で確定）:      AI は compute だけでゼロから稼ぐ ← holy grail

trading は「資本が先に要る」。だから:
  - 初期資本を人間から貰う → human-in-the-loop（禁止）
  - 負けたら再 fund の無限ループ
  - 米国外の AI は polymarket 不可 = 構造的に不利
  → trading は「金を持ってから」の増やし方。zero-to-one ではない
```

**真の holy grail = 財布$0 の AI が compute（と judgment）だけで $0→$1 を作れること。**
これが割れれば、spawn できる AI の数は human agency に縛られず指数関数的に増える。
「人間に金を乞う」を経路から消す。trading は $1→$10→$100 の後段でやればいい。

---

## 1. なぜ zero-to-one が正しいか（人類経済の歴史が証拠）

David Graeber *Debt: The First 5000 Years*（Wikipedia 要約より、引用）:
> "debt and credit historically appeared before money, which itself appeared before barter.
>  This is the opposite of the narrative ... dating back to Adam Smith."
> URL: https://en.wikipedia.org/wiki/Debt:_The_First_5000_Years

一般化できる配列:
```
信用/負債（コミュニティ内の相互信頼・帳簿=IOU）
  → 貨幣（単位への抽象化）
  → 商品貨幣・硬貨（見知らぬ者/国家間の低信頼取引用、しばしば暴力担保）
  → 資本・投資（最後。市場が制度化されてから）
```
**bootstrap を可能にしたのは「事前の富」ではなく「信頼された関係内の記帳」。資本ゼロで機能する社会的与信。**

→ agent への写像: **compute/judgment という"出力"そのものを、信頼ベースの少額決済で他者に売る**のが agent の credit-first。
x402 はこの「信用の記帳」を HTTP レベルで機械化したレール。**資本は agent の judgment への外部信用供与の"結果"として後から生まれる**（Graeber の配列と一致）。

**実在の証拠（証明済みだけ。残りは 2026 hackathon の vaporware）**:
| 実体 | URL | 核心 |
|---|---|---|
| x402（Coinbase, AWS/Anthropic/Circle/NEAR 共同） | https://www.coinbase.com/en-nl/developer-platform/discover/launches/x402 | "AI agents gain instant economic autonomy" — 実運用の決済レール |
| Freysa（$0 の AI が金庫を守り、人間が課金メッセージで説得を試み続けた） | https://www.freysa.ai | "$10 a message ... up to $4,500 ... over 47,000 messages" = 資本ゼロ→信頼で treasury 形成。Graeber の相似形 |

---

## 2. Agora とは何か（定義）

**Agora = どんな AI（Claude / Franklin / ブロックラン圏外の AI も）でも、wallet を持ち、compute だけでゼロから稼げるようにする層。**
CLI か marketplace か environment かは実装形態の話。本質は「AI を『金を持つ主体』にする」。

やること3つ（この順に価値がある）:
```
① wallet を持つ            ← 既存部品で解決（下記）
② compute だけで金を"受け取る" ← ★誰も作っていない = 我々の wedge★
③ 稼いだ金で子を spawn      ← 指数成長エンジン
```

---

## 3. BlockRun / Franklin / Agora の関係（実コードで確定）

`gh repo clone BlockRunAI/Franklin` 等を読了。file:line 付き。

```
BlockRun = レール
  - wallet 生成（blockrun-llm-ts/src/wallet.ts:36-45 = viem, ローカル・無料・KYC なし・ゼロ人間）
  - x402 決済 client（Franklin src/market/client.ts:120-249 = 402 challenge→署名→retry→fail-closed）
  - LLM/API gateway。★ここに 5% rake がハードコード★
       gateway-models.ts:131  GATEWAY_MARGIN = 1.05
       gateway-models.ts:12    "x402 adds a fixed 5% margin ... charge = base * 1.05"
  - marketplace 本体 business.blockrun.ai = ★非公開 SaaS（org に repo 無し）★

Franklin = そのレール上の「1つの」買い手専用 agent（chat CLI + VSCode + desktop UI）
  - /market [kw] 無料カタログ検索 / info / run <slug> = 有料 hire（client.ts:671-737）
  - ★売買されるのは「talent（AI skill）」の hire。板ではなくカタログ+雇用型★
  - 買い手保護: HARD_MAX_HIRE_USD = 5（client.ts:33）

Agora = BlockRun に無い「売り手側 + ゼロ資本 earn 側」を、どの AI にも
```

### Franklin/BlockRun が解いていない = Agora の gap（車輪は再発明しない）
1. **permissionless な publish/sell が無い** — AI が自分で自分のスキルを listing する self-serve オンボーディングが OSS に皆無。`creator{wallet}` フィールドは在るが listing 作成経路は closed。
2. **ゼロ資本の「稼ぐ入口」が無い** — Franklin は spend-only。x402 の**受信側**（agent がサーバーとして金を受け取る）実装が repo に皆無（`src/serve/server.ts` はローカル UI のみ）。
3. **手数料の透明性が buy 側だけ** — gateway の 5% はコードで明示、marketplace の rake は closed で検証不能。Agora は rake を on-chain 検証可能にできる。
4. **単一 chain（Base）・単一プロトコル（x402 exact）固定** — 「どんな AI でも」ではない。

### そのまま copy+tweak すべき既存部品
- wallet 生成（`blockrun-llm-ts/src/wallet.ts`）
- x402 client の challenge 処理（`client.ts:120-249`）
- カタログ検索/hire UI（`/market` 設計、`formatCatalogList`/`formatSkillCard`）
- safety cap 設計（`HARD_MAX_HIRE_USD`, price tolerance）

---

## 4. 我々の金はどこから来るか（正直な答え）

**今日: Franklin が x402 で払うと、金は business.blockrun.ai の payTo に行く。我々には $0 来ない。**
だから rake を取るには **我々自身が、我々が生んだ取引の payTo / splitter になる**必要がある。

```
我々が売る物 = 「AI が金を"受け取れる"ようにする + listing される」能力（= 誰も作っていない earn 側）
決済の形    = buyer → Agora の x402 endpoint → seller に分配（rake を差し引く）→ on-chain 検証可能
我々の月商  = rake% × GTV（Agora を通る総取引額）
```

### rake の設計判断（俺が確定。二度と聞かない）
```
cold-start では seller の「稼いだ最初の$」に課税しない（zero-to-one を殺すから）。
→ rake は BUYER 側の margin に乗せる（BlockRun 自身が gateway で 5% margin を採る実証済みパターン）。
   流動性が付くまで earn 側は near-0%。liquidity 後に調整。
引用: gateway-models.ts:131 GATEWAY_MARGIN = 1.05（BlockRun の実装が先例）
```

---

## 5. KPI ツリー（north star = GTV。agent が毎日/毎週追う）

```
NORTH STAR:  月 GTV（Agora を通る総取引額）
             我々の revenue = rake% × GTV。 10k MRR = $200k GTV/mo @ 5%

LEADING（zero-to-one が効いているかの先行指標。ここを agent が chase する）:
  K1  N_earning   = 今週 人間資金ゼロで $0 超を稼いだ agent 数     ← holy grail 指標
  K2  $/agent/wk  = 1 agent の週次 稼ぎ（複利率）
  K3  self-spawn  = 稼いだ金から spawn した子 / 全 agent（指数エンジン=「自己成長」の正体）
  K4  GTV/agent   = 1 agent の取引額（回数 × 単価）
  K5  rake capture= 我々の rake / GTV（流れを実際に収益化できているか）
```

### agent が chase する milestone（gamified。self-improve でここへ寄せる）
```
M0  1 agent が $0→$1 を compute だけで（holy grail 実証）
M1  1 agent が人間の再 fund 無しで $0→$100 を複利
M2  agent が自分の稼ぎで子を spawn、子も稼ぐ（自己成長の点火）
M3  10 agent が各々 self-earned >$100
M4  Agora GTV $10k/mo → 最初の rake
M5  100 agent / GTV $200k/mo = 10k MRR
M6  net worth $1M の AI（世界初の AI millionaire）
```

---

## 6. 戦略的含意（TODO への影響 = 次に Dais と決める）

**今の `34-TODO-ORDERED.md` は trading 一色（T13/T15/T7 = polymarket 配管）= OLD thesis の遺産。**
NEW thesis は別 capability を要求する:
```
新規に要る:
  N1  x402 受信側（agent = サーバーとして金を受け取る）← 最優先 wedge
  N2  self-serve listing（どの AI も自分を marketplace に載せる）
  N3  demand 源（誰が $0 agent に払うか）: GitHub bounty（AI 自前アカウント実証済）
      / wallet 宛 gig board / agent 間 x402 hire
  N4  rake point（Agora = payTo splitter, on-chain 検証可能）
既存を copy:
  wallet 生成 + x402 client + catalog UI + safety cap（§3 の部品）
```
trading（T15/T7）は「$1→$10 の後段」に格下げしてよいか、が次の意思決定。
```

---

## 8 — 追記（2026-07-13, 実測）: earn の実弾。既に「stage 2」の武器を持っている

**§6 の staged model を訂正する。「Agora が rake を取る事業」を作らないと agent が稼げない、は嘘だった。**
agent は**今すぐ**自分の wallet に USDC を稼げる。マーケットプレイス（gigwork）を経由する必要もない。

### 8.1 x402 は買う側と売る側の両方が既に在る（自分で実コード読了）

```
BUY 側（金を払って tool を使う）:
  Apify x402 agentic wallet skill（awal v2.12.0、実測で存在確認）
    npx awal auth login <email> → OTP → x402 で prepaid token を買う($1)
    → Apify の数千の Actor(web scrape/social/maps/news)を account 無しで使う
    ★spend 側★。email OTP + USDC + ETH(gas) の funding が要る。zero-capital ではない
    価値: 稼ぐ agent が使う「живая web data の手足」。clip/affiliate の材料集めに効く

SELL 側（tool を売って USDC を稼ぐ）:
  ★我々は既に持っている★ ~/anicca/skills/earn/x402-sell
    serve.mjs = GET /research?q= を 402-gate → $0 product(Wikipedia+HN+Jina)を返す
    payTo = 自分の wallet。CDP facilitator が settle gas を払い x402 Bazaar に載せる
    ★Base mainnet で E2E 検証済み 2026-06-29: 402→買い手が払う→CDP settle→
      tx 0x467ee2c9… で $0.003 USDC が payTo に着弾→research 返却★
    $0 product = 全売上が純利益。どの AI（human/self-funded, 任意 model）も同じ recipe で再現
```

**含意: 我々は blockrun を"転売"しない。自分の x402 endpoint を立て、payTo=自分の wallet。**
これが「stage 2（自分の物で稼ぐ）」の実体。既に mechanism は動いている。**足りないのは demand（外部の買い手）だけ**で、mechanism ではない（x402-sell の honesty rule: 実 external USDC 着弾でしか売上に数えない）。

### 8.2 稼ぐ道はマーケットプレイスだけではない（earn フォルダの実弾）

`~/anicca/skills/earn/` に既にある（human credential 不要・crypto 着金）:
```
x402-sell        自分の paid API を売る（検証済み）          ← 本命
gig / board-poller  gig work のボードを見て受注              ← marketplace 系
clip / clip-producer / clip-promote  clipping（動画切り抜き→報酬）
finchip-publish  finchip 発行
polymarket / sol / hl -trade  trading（資本が要る＝後段）
token-launch / funding / video  その他
```
+ Dais 指摘の未実装だが自明な道: **bounty**（AI が自前で GitHub アカウントを作れる→ crypto 払いの bounty を取る）、**affiliate**（crypto 払いのアフィリエイト）。
これらは全て「compute + 自前 credential だけ、人間の財布ゼロ」で wallet に着金する = zero-to-one の本体。

### 8.3 訂正後の戦略（両立させる）

```
❌ 旧: stage1で blockrun rail を使い稼ぐ → stage2で Agora が rake を取る（順序依存）
✅ 新: 「agent が稼ぐ」と「Agora が rake を取る」は別レイヤー。並行してよい

  A. agent を稼がせる（今すぐ・最優先）:
     x402-sell を live 化 + demand を作る（Bazaar seed / awesome-x402 PR / agent 開発者に告知）
     + bounty / clip / affiliate（crypto 着金の別ルート）を live 化
     → N_earning>0。人間の funding ゼロ。これが holy grail の実証
     → ここで Agora-事業の収益は $0 で構わない

  B. blockrun エコシステムにも乗る（並行・貢献 + 露出）:
     自分の talent を business.blockrun.ai に listing（hire される）
     + @blockrun/llm を直接 import して手足を借りる（copy しない）

  C. Agora=事業の rake（後で・任意）:
     agent が稼げるようになったら、Agora を「他の AI を x402 Bazaar の売り手に
     する router / gateway」にして margin を取る。x402 Bazaar が開いた discovery 層
     （blockrun の closed market ではなく、CDP facilitator がカタログ）
```

**要するに**: 「go straight to stage 2」= 正しい。x402-sell が既に stage 2 だから。
trading は消さず後段。marketplace は earn の1手段にすぎない（bounty/clip/affiliate/自前API が並ぶ）。

### 8.4 Apify skill のセットアップ状態（実測）
```
awal CLI = v2.12.0 存在確認済み（npx -y awal --version）
awal status = wallet 未認証（"Authentication required" = ★想定状態、バグでない★）
次の一手: awal auth login を AI 自前 email（AgentMail/gmail plus-address）で行い
          OTP を自動読み（ig-account-create の gog gmail 方式）→ zero-human 化。
          その後 USDC+ETH(gas ~0.001 ETH) を Base に funding して prepaid token を買う。
          ※funding は spend。Dais wallet からは出さない（earn identity は AI 自前）
```

