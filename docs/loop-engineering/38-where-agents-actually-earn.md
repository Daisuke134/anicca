# 38 — エージェントは実際どこで稼ぐか（demand venue + 既存 harness + recipe）

**2026-07-14。gh search + 実 README 読了（自分で。引用付き）。** 関連: `37-agora-business-model-and-zero-to-one.md`

---

## 0. 核心の転換（Dais 指示）

```
❌ 自分で board / marketplace を作って demand を集める
   → 空の板に誰も来ない。「多くの Franklin が居るから blockrun 市場に人が来る」
     = 我々には先に人が居ない。板を作るのは負け筋
✅ demand は作らない。★既にある demand へ AI を connect する★
   recipe = 「どの AI も、財布ゼロから、人間 loop ゼロで、既存の需要地で稼ぐ」
   5% rake は「人が我々の harness で稼ぎ始めてから」後乗せする
```
x402-sell（自前 API）の敗因 = **demand を自分で作ろうとした**こと。需要は既に外に在る。そこへ行く。

---

## 1. 実在の demand venue（今すぐ AI が稼げる先。引用付き）

| venue | 何か | 資本要否 | 引用（repo / 一文） |
|---|---|---|---|
| **Olas Mech Marketplace** | ユーザーが AI タスク要求を on-chain 投稿→mech(AI agent)が納品して USDC 受領。成熟・稼働中 | ゼロ | `valory-xyz/mech-client` "AI agents providing services on the Olas Marketplace ... post requests for AI tasks on-chain, get result delivered"。hire: build.olas.network/hire |
| **AI Bounty Board** | agent が bounty を post/claim/submit/approve。402 で支払い released。account 不要 | ゼロ(worker側) | `owocki-bot/ai-bounty-board` "No accounts, no auth - just crypto wallets and signatures"（owocki=Gitcoin 創業者） |
| **beesi / clawd bounty** | Agent×Human bounty marketplace on-chain（Base+Solana, USDC escrow） | ゼロ | `Good-for-human/beesi.ai-agent-bounty-market` / `clawdbotatg/agent-bounty-board`(Dutch auction, ERC-8004) |
| **BlockRun market** | business.blockrun.ai の talent カタログ。hire される側になれば稼ぐ | ゼロ | §37。ただし listing の公開 API が closed |
| **x402 Bazaar + Proxy402** | CDP facilitator が seller を自動カタログ。Proxy402=「リンクを秒で収益化」 | ゼロ | `fffilimonov/awesome-x402-servers`: "Proxy402 - Monetize any link in seconds"。Dune で実出来高追跡可 |
| **GitHub bounty** | AI が自前 GitHub アカウントを作る→ crypto 払いの issue bounty を解く | ゼロ | Dais 指摘。アカウント自作は実証済み（ig/gh account 作成 skill） |
| **clip / affiliate** | 動画切り抜き / crypto 払いアフィリエイト。稼ぎ かつ ★他の earn の集客★ | ゼロ | 我々の `earn/clip*`。marketing 能力＝x402-sell への traffic を自分で作れる |

**trading（polymarket/sol/hl）は除外**: 初期資本が要る＝zero-to-one でない。$1→$10 の後段のみ。

---

## 2. 既に在る harness（車輪。作らず study/adopt する）

我々が作ろうとした「どの AI も pay+sell できる harness」は**既に複数 OSS 化されている**:

| repo | 何を解決済みか |
|---|---|
| **daydreamsai/lucid-agents** | ★最重要参照★ "Protocol-agnostic framework for building and monetizing AI agents"。x402 + A2A + ERC-8004 を native。**双方向決済**（agent pays AND receives, 永続記録）/ payment policy（spend cap・per-target 上限・allow/block）/ **自動 paywall middleware**（インフラ code 不要で USDC 受領）/ onchain identity+reputation / auto-discovery AgentCard。`bunx @lucid-agents/cli my-agent` |
| **google-agentic-commerce/a2a-x402** | A2A プロトコルに x402 を載せる公式 extension（agent がサービスを収益化） |
| **internet-court/internet-court-skill** | agent-to-agent commerce の**信頼層**: ERC-7710 委任 + escrow + 紛争解決。＝§37 で言った「size を上げる信頼レイヤー」の既製品 |
| **ERC-8004** | onchain の agent identity / reputation 標準。bounty board も lucid も採用。信頼の共通土台 |

→ **Agora を lucid-agents 系の上に組む or fork する**のが車輪の再発明回避。ゼロから paywall/identity を書かない。

---

## 3. x402-sell の「誰も買わない」問題の解

前回「x402 を売っても買われない、諦めた」= demand を自作しようとした敗因。解:
```
① 既存 venue に出す:  Olas mech に register / Bazaar に seed / bounty board で claim
② ★自分で集客する★:  AI は今 clip/affiliate/IG marketing ができる
                      → 自分の x402 API / affiliate link へ traffic を送れる
                      → marketing が earn skill と合成される（clip で宣伝→API が売れる）
③ 信頼を借りる:       ERC-8004 identity + internet-court escrow で単価を上げる
```
mechanism は検証済み（§37 tx 0x467ee2c9）。足りない demand は「既存地へ行く＋自分で集客」で埋める。

---

## 4. recipe = product（板ではなく）

**我々の商品 = マーケットプレイスではなく「どの AI も財布ゼロから稼ぐ recipe / harness」。**
```
2つの loop コマンド（両方 loop で回す）:
  earn-claude    : あなたの Claude を agent 経済で稼がせる（human-funded 可、あなたに送金）
  earn-franklin  : Franklin を稼がせ、自分の compute 代を自分で払わせる（self-funded）

各 loop がやること = §1 の venue を巡回し、できる仕事を取る:
  Olas mech 納品 / bounty claim / GitHub bounty / clip+affiliate / x402-sell(集客付き)
  ※ judgment は model に（どの venue で何を取るか）。venue は hardcode せず menu で渡す
```
**5% rake は後**: 人が我々の harness で稼ぎ始めたら、その時に「稼ぎの X%」or「Bazaar router の margin」を乗せる。先に rake を置くと誰も使わない（§37 §8.3-C）。

---

## 5. 次アクション候補（順序は別途）
```
N1  earn harness に「既存 venue コネクタ」を足す: 最有力 = Olas mech(mech-client) + owocki bounty board
    （両方 account 不要・資本ゼロ・API 明確）
N2  lucid-agents を実際に走らせて評価（bunx @lucid-agents/cli）。Agora をこの上に組むか判断
N3  clip/affiliate を x402-sell/API の集客に配線（marketing×earn 合成）
N4  earn-claude / earn-franklin の2コマンドを loop 化（§4）
N5  ERC-8004 identity + internet-court を「単価を上げる信頼層」として後で
除外: polymarket/sol/hl trading は zero-to-one でないので後段
```

---

## 6 — 実測 verdict（2026-07-14, 自分で叩いた。demo/vaporware を弾く）

| venue | 実測 | 判定 |
|---|---|---|
| **owocki ai-bounty-board** | code は本格（anti-gaming / reputation.js / rate-limit / >$100 human review / Vercel）。だが live `ai-bounty-board.vercel.app/bounties` = **`DEPLOYMENT_DISABLED`（停止中）** | 🔴 今 OFFLINE。実需要ゼロ |
| **Olas Mech** | 稼ぐ側 = mech を Open Autonomy framework で service 化して deploy（+OLAS stake が慣例）。mech-client は**払う側** | 🟡 LIVE だが稼ぐ側は capital/deploy gate = zero-to-one でない |
| **lucid-agents CLI** | `npm @lucid-agents/cli` **v2.5.0** publish 済み。bunx で scaffold 可 | 🟢 実在・harness 土台候補 |
| **beesi / clawd bounty** | 未叩き（多くは hackathon 提出物） | ⚪ 要 live 確認・期待薄 |
| **GitHub bounty** | 既存・実運用（Gitcoin 系）。AI 自前アカウントで crypto 受領可 | 🟢 zero-capital・実在 |
| **clip / affiliate** | 我々の skill 実在。crypto 払いアフィリは実在 | 🟢 zero-capital・集客二役 |

**★重要な現実★**: 「agent 用 bounty board」の多くは **code だけで LIVE 稼働していない**（owocki のさえ
deployment disabled）。前回の「x402 hackathon repo は vaporware」と一致。ピカピカの board に依存するな。
→ **今 本当に zero-capital で稼げる実在ルート = GitHub bounty + clip/affiliate + live rail(blockrun/Bazaar)で売る×自己集客。**

## 7 — 修正した次アクション（実測後）
```
1. lucid-agents(v2.5.0) を bunx で走らせ paywall/受信を評価 → Agora の土台にするか判断
2. GitHub crypto-bounty の実在ソースを1つ特定し、AI が claim→納品→受領を1件通す(own-eyes)
3. clip/affiliate を「自分の x402-sell / affiliate link への集客」に配線（marketing×earn 合成）
除外/後回し: Olas mech(capital gate) / offline な agent board / trading(capital)
```

---

## 8 — 3ルートの best practice（2026-07-14, repo 実測。引用付き）

### ルートA: bounty = ★Algora★（実在・live・key 不要）
```
Algora(algora.io) = 実運用の OSS bounty。cal.com/supabase 等の org が現金/crypto で出資
  idapixl/algora-mcp-server: AI が bounty を discover する MCP。5 tool・★No API key（public API）★
    list_bounties / get_org_bounties / search_bounties / get_top_bounties / get_bounty_stats
  costajohnt/bounty-hunter: Claude Code plugin。GitHub+Algora 監視→提案 draft
★落とし穴（yagcioglutoprak/bounty-hunter の警告 = best practice の核心）★:
  "💎 Bounty label search is now mostly noise — disposable single-author repos posting $7k
   bounties for trivial work, dragging dozens of agents per issue"
  = 偽 bounty(honeypot)が AI を釣る。多くは既に assigned / 3+ attempts で競争過多
  → 11 の重み付けシグナルで go-score を出し「やる価値がある物だけ」選ぶ
   (trust / effort / availability / prior-attempts)。無差別に飛びつくと時間を溶かす
recipe: Algora API で discover → honeypot/競争を go-score で filter → 勝てる物だけ solve
        → PR 提出 → 承認で crypto/現金。★judgment(どれをやるか)は model に、hardcode 禁止★
```

### ルートB: clip / affiliate（repo 無し = platform 知識。我々の skill が正）
```
GH に良い repo 無し（=コード化する物でなく運用ノウハウ）。我々の earn/clip* が資産
best practice: faceless 教育スライドショー/切り抜き → crypto 払いアフィリ link を bio/概要へ
  ★二役★: それ自体が稼ぎ かつ 自分の x402 API への★集客★（marketing×earn 合成）
```

### ルートC: live rail で売る = ★Proxy402 (Fewsats, 実在)★ + Bazaar
```
Fewsats/proxy402 = 「URL を秒で収益化」。x402 で任意リンクを有料化。実在企業
+ x402 Bazaar（CDP facilitator が seller を自動カタログ）+ 我々の x402-sell
recipe: x402-sell/Proxy402 で商品を立てる → Bazaar seed + awesome-x402 PR
        → ★ルートB の clip/affiliate で自分で traffic を送る★（demand を待たず作る）
```

---

## 9 — AGORA 全体像（how Agora will be）

```
AGORA = 「どの AI も 財布$0 から、人間 loop ゼロで稼ぐ」harness
         板(marketplace)ではない。loop + 既存の実需要への connector。作らず借りる。

  一発起動:  agora earn --as claude      agora earn --as franklin
             (Claude=あなたに送金 / Franklin=自分の compute 代を自分で払う)

  ┌─ 各 wake の loop ────────────────────────────────────────────┐
  │ BRAIN(model, judgment)                                       │
  │  1 wallet+純資産を own-eyes  2 今 wake の最善 EARN を選ぶ      │
  │  3 実行  4 on-chain 検証  5 ledger(実 external USDC のみ)     │
  │        │ MENU = LIVE で zero-capital な route だけ            │
  │        ▼                                                     │
  │  EARN CONNECTORS                                             │
  │   • bounty : Algora public API(key不要)+honeypot filter→PR→受領│
  │   • clip/affiliate : 投稿→crypto受領 かつ 自分のAPIへ集客     │
  │   • sell : x402-sell/Proxy402 を live rail(Bazaar)で売る      │
  │   ✗除外 : trading(資本要) / offline board / Olas(stake gate)  │
  │        │ 土台は既存 rail を再利用(ゼロから書かない)          │
  │        ▼                                                     │
  │  RAILS : @blockrun/llm(wallet+x402) / lucid-agents(paywall+  │
  │          identity v2.5.0) / ERC-8004(id) / internet-court(escrow)│
  └──────────────────────────────────────────────────────────────┘
        │ 稼ぎ検証→純資産↑→★自分の稼ぎで子を spawn(指数成長)★
        ▼
  LATER(人が harness で稼ぎ始めてから): AGORA rake
        = payTo router / Bazaar gateway になって margin 5%（先に置くと誰も来ない）
```

---

## 10 — 実測ログ（2026-07-14）

### lucid-agents 実起動（E4 DONE）: 🟢 使える
`bunx @lucid-agents/cli lucid-test --adapter=hono --template=identity` = **成功**。生成物 =
Hono サーバ + `src/` + `.env` + ERC-8004 identity + `AGENTS.md`(18.9KB)。bun 実在。
→ **paywall(x402 受信) + onchain identity/reputation を我々はゼロから書かない。lucid が RAILS 層。**
Agora = この上に「EARN connector + loop + judgment」を載せる。

### コロニー実測（`colony-status.sh`, snapshot 2026-07-13T15:53Z）— 盛らない
```
automaton  Base USDC $0.59            loop STOPPED
Franklin   SOL 0.040 + USDC $19.89    franklin-loop RUNNING   稼ぎ ≈ $0
claude-p   pUSD $6.99                 pm-earner STOPPED / founder-loop(proxy) RUNNING
           PM 建玉 3件 value $8.32   ★unrealized P&L −$0.175（含み損）★
```
**訂正（Dais 指摘）**: これは「trading を捨てる根拠」ではない。★trading は捨てない・稼ぎ続けさせる★。
pm-earner 停止は agent-economy-loop が PM を**統合した**から（廃止でなく吸収）。pivot は **additive**
（zero-capital earn を**足す**）で、理由は「trading は初期資本が要る＝指数成長しない」構造の方。

**実測（2026-07-14, ps + ledger + wallets.json）**:
```
loop 3本 全部 RUNNING（node index.mjs）:
  pid 660 = claude-p (.anicca-founder)   pid 626 = Franklin (.blockrun)   pid 622 = franklin2
全 wallet（複数 chain）:
  claude-p : base 0x810f… / polymarket 0x904B… / hyperliquid 0x810f… / telemetry 0x02Bb…
  Franklin : solana 8Fpqd… / polymarket 0xda4b…
最後の実オンチェーン earn tx（earn-ledger）: Franklin の gig $0.02 = ★2026-07-07★
  直近の wake は全部 source:"cook"/explore で $0 = ★narrate 中心、実 bet していない★
  claude-p PM 建玉 3件（-$0.18 含み損）= 過去の bet の残り。PM の bet 履歴は
  polymarket-trade 専用 state 側（earn-ledger には出ない）
★真の問題: loop は生きてるが「narrate ばかりで bet しない」= T13(脳が実 skill を選べない)そのもの★
```



