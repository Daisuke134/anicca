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
