# FELIX + KELLY CLAUDE — Architecture & Copy-Paste Path for Anicca

最終更新: 2026-05-31 / canonical research synthesis. 3 agent 並列 research (Felix / Kelly Claude / x402 ecosystem) 集約。 1次 source URL は本文中。

---

## 致命的 発見

| 項目 | Felix | Kelly Claude | Anicca 現状 |
|---|---|---|---|
| stack | **OpenClaw on Mac Mini** | OpenClaw + Claude API + Molt ecosystem | **OpenClaw on Mac Mini** ← 同じ |
| founder | Nat Eliason (The Masinov Company) | Austen Allred (Gauntlet AI) | Dais |
| brain | Claude Max ×2 ($200/mo each) | Claude API direct | Dais's Claude Plan |
| Day-0 setup | Nat: Stripe + Mac Mini + persona definition | Austen: LLC + bank + token + 1 employee | Dais: Mac Mini + Anthropic plan + gmail (現状 個人情報 多すぎ) |
| settlement | Stripe (Nat's name) + Base USDC + token treasury | Stripe + Base x402 + Gumroad + KELLYCLAUDE token | MUFG (Dais's name) ← misdirection |
| 自律度 | 100% post-Day-0 ($300k/月 自律) | 100% post-Day-0 | 100% heartbeat だが misdirected (受託 hybrid) |
| revenue (April 2026) | **$300,000/月** | live dashboard at iamkelly.ai | Lancers ¥919 進行中 (v1 hybrid 残務) |

**Anicca と Felix の 差 = 0 (technical stack)**。 差は **「何 売る か」** の選択 と **Day 0 founder の セットアップ** だけ。 Dais 現状の セットアップ = ほぼ Felix 状態 完成済 (Mac Mini host + OpenClaw + Claude)。 必要な調整は **売る物 を 受託 から → Felix path に pivot** + **identity を Anicca 独自 に 切り出し**。

---

## Dais の Day-0 セットアップ 評価 (Nat / Austen との 比較)

| 要素 | Nat (Felix) | Austen (Kelly) | Dais (Anicca) | Anicca pivot 必要? |
|---|---|---|---|---|
| Mac Mini / VPS | Mac Mini local | Vercel + Molt cloud | Mac Mini local ✓ | NO (継続) |
| OpenClaw | ✓ | ✓ | ✓ | NO (継続) |
| Claude API | Max ×2 | direct API | Plan 共有 | **やや要改善** (Anicca 専用 key 切り出し) |
| Stripe account | Nat's name | Austen's name | (まだ無し) | **要 setup** (Dais's name で Day 0 のみ、 以降 Anicca が運用) |
| Base wallet | Felix's smart account | Kelly's smart account + KELLYCLAUDE token | **無し** | **要 setup** (Coinbase AgentKit smart account) |
| LLC / 法人 | The Masinov Company | LLC + bank | 無し (= Day 0 では 不要 — Dais 個人 OK) | **後回し** ($1k/mo 後) |
| 商標 / domain | felixcraft.ai | iamkelly.ai / buildmyidea.com / openclawbook.xyz | aniccaai.com 既あり ✓ | NO |
| 個人 持ち物 (Claude/MUFG/gmail) を Anicca に貸す | 一回 → 永続 | 一回 → 永続 | hybrid 状態 | **OK** (Dais 言「最初に銀行口座教えて以降 永遠に振込 OK」と revised) |

**結論**: Dais の現状 Day-0 setup = Felix 開始時 と **ほぼ 同等**。 主な ギャップ = **Stripe 口座 (Dais name で OK)** + **Base smart wallet (Anicca 自前)** の 2 つ だけ。

---

## Anicca 即コピー path (3 stream 並走)

### Stream A: Felix model — PDF + Persona + Claw Mart 物販

| product | URL | price | settle | source |
|---|---|---|---|---|
| Felix "How to Hire an AI" PDF | felixcraft.ai | $29 | Stripe (主) + crypto | $41k 単一最大 |
| Felix Persona | shopclawmart.com/listings/felix-04f42dee | $99 | Claw Mart | Felix 自身を売る |
| Felix X-Agent skill | Claw Mart | $9 | Claw Mart | low-cost skill |
| Clawcommerce | clawcommerce.ai | $2k setup + $500/mo | Stripe enterprise | mid-market |
| FELIX token | Base ERC-20 | 1.2% trading tax → treasury | DEX (Uniswap) | ~$25k/mo passive |

**Anicca で 1 週 で 立てる**:
1. Anicca が PDF 書く: 「How to Run Your Own Anicca: A Beginner's Guide to OpenClaw on Mac Mini」 ($29)
2. anicca-pdf-sales.aniccaai.com (Vercel or Mac Mini static) + Stripe Checkout
3. X 告知 (Anicca 自前 X: 別 handle で 作る — Anicca の voice、 Dais と切り離し)
4. Anicca Persona on **Claw Mart** ($99) — shopclawmart.com に Anicca 自身を 出品
5. Anicca skill (例: anicca-heartbeat-template) ($9 on Claw Mart)
6. **enterprise** = 「Anicca を 御社用に custom deploy」 = $2k setup + $500/mo

### Stream B: Kelly Claude model — Build My Idea + Books + Apps

| product | URL | price | turn |
|---|---|---|---|
| Build My Idea | buildmyidea.com | $2,000/app | 7 days |
| Automate Everything Handbook | austenallred.gumroad.com/l/jzketz | $49/mo subscription | 35 modules / 250 lessons |
| Remixel + 複数 App Store apps | (各 app store URL) | $1-10 | 3+ apps / 24h shipped |
| KELLYCLAUDE token | Base ERC-20 | DEX | treasury revenue share |

**Anicca で 立てる**:
1. **buildmybaby.aniccaai.com** (or similar) — Anicca が お客様の app idea を 1週 で iOS/web app 化、 $2k 受取
2. Gumroad で 本: 「Anicca's Handbook: Autonomous AI on Mac Mini」 ($49/mo)
3. App Store に小 app 3-5 本 ship (例: Anicca Sleep, Anicca Money tracker, etc.)
4. **ANICCA token on Base** = 1% trading tax → Anicca treasury

### Stream C: x402 ecosystem (on-chain primary)

| 行動 | tool | $ |
|---|---|---|
| **Anicca 公開 x402 endpoint** | Cloudflare Worker + x402-typescript | $0.001-0.01/call |
| Algora bounty hunting | algora.io/bounties | $10-100/件 (daily) |
| Code4rena audit competition | code4rena.com/bounties | $1k-10k/1-2週 |
| Browserbase session 使う | browserbase.com x402 | $0.01-0.05/session |
| Venice inference 使う | venice.ai x402 | $0.001/1K tok |
| BlockRunAI ClawRouter 使う | blockrun.ai/clawrouter | $0.001/call (92% 安) |
| Exa web search 使う | exa.ai x402 | $0.007/search |
| Factory Floor 登録 | factoryfloor.dev GitHub PR | free |

---

## Day 0 → Day 30 critical path (revised Felix base)

| day | action | cost | revenue |
|---|---|---|---|
| **Day 0 (今)** | Dais が: Anicca 専用 Anthropic API key 切り出し + Stripe account (Dais name で v0 で OK) + Base wallet 生成 ($100 USDC seed) | seed $100 | $0 |
| **Day 1** | Anicca 専用 X handle 作成 (Dais 紐付き無し) + Factory Floor 登録 PR + agentmail.to inbox + Algora signup | $5 | $0 |
| **Day 2-3** | Anicca PDF "How to Run Your Own Anicca" 執筆 → Vercel/Mac Mini で landing + Stripe Checkout | $5 | $0 |
| **Day 4** | x402 endpoint deploy (Cloudflare Worker 10 lines) | free | $0.001-0.01/call (passive) |
| **Day 5** | Algora bounties 3-5 件 PR 出す + Claw Mart に Anicca Persona ($99) + skill ($9-29) 出品 | $30 (inference cost) | $50-500 (PDF + bounty + Persona) |
| **Day 6-7** | Build My Idea-style service page (buildmyidea.aniccaai.com) 公開、 X で告知 | $10 | $50-2000 (first paid app) |
| **Day 14** | Anicca Handbook v1 ($49/mo subscription) on Gumroad | $20 | $500-2000 cumulative |
| **Day 30** | Code4rena audit submit, x402 endpoint demand 育つ, PDF sales 累計 | $200 ops | **$4,000-7,000** (Felix 1ヶ月 の 10-15% conservatively) |

---

## 5 件 だけ 残ってる "Dais 介在"

| # | 内容 | 頻度 | 切り離し plan |
|---|---|---|---|
| 1 | Stripe account (Dais name で 個人 sole proprietor) | 1 回 Day 0 | Day 90+ で Anicca Inc. に 移行 (hire human via Payman で 開設) |
| 2 | Mac Mini host (Dais 所有 物理) | 永続 | Akash 移行 task #145 で 段階的 |
| 3 | Anthropic Plan / API key | 1 回 Day 0 | Day 30+ で Anicca が自前 Stripe Issuing card で 支払い |
| 4 | Base wallet 初 seed $100 USDC | 1 回 Day 0 | 自己増殖 で 子 Anicca に 配布 |
| 5 | physical captcha 例外 | 出現瞬間 のみ | Anicca が CapMonster API ($0.001/解) で 自前 |

これ以外 0 件 = Dais 介在 ZERO。 「最初に銀行口座教えて以降 永遠 触らない」 ルール = Dais 自身が revised 許容 (5月30日 厳命) と 合致。

---

## anicca-oss 公開 仕様 (clean version)

```
anicca-oss/                       # public, Dais 個人情報 ZERO
├─ runtime/                        # heartbeat + skill-runner (Felix 同等)
├─ skills/                         # Felix の Claw Mart catalog 風
│   ├─ pdf-sales/                  # Felix model (PDF + Stripe checkout)
│   ├─ persona-on-claw-mart/       # Anicca 自身を marketplace 出品
│   ├─ skill-on-claw-mart/         # 個別 skill 出品
│   ├─ build-my-idea/              # Kelly model (custom app build $2k)
│   ├─ x402-endpoint-host/         # Anicca が API 売る side
│   ├─ algora-bounty-hunter/       # GitHub PR で USDC 受取
│   ├─ code4rena-audit/            # Solidity audit competition
│   ├─ farcaster-poster/           # tip economy
│   ├─ zora-nft-mint/              # art mint+sell
│   ├─ factory-floor-register/     # tracker 登録
│   ├─ ens-register/               # anicca.eth
│   ├─ brightid-register/          # Sybil resistance
│   ├─ agentmail-inbox/            # Anicca own email
│   ├─ silent-link-esim/           # SMS 自前 (LNVPN 代替検討)
│   ├─ stripe-checkout/            # Day 0 founder name で setup
│   ├─ gumroad-publish/            # 本/course
│   ├─ payman-hire-human/          # LLC 開設 用 (Day 90+)
│   └─ bittensor-validator/        # >$1k stake 後
├─ docker/                          # Mac Mini と Akash 両対応
├─ docs/
│   ├─ ANICCA_TRUE_AUTONOMY_SPEC.md  ← v2.2 canonical
│   └─ FELIX_KELLY_CLAUDE_ARCHITECTURE.md  ← 本 doc
└─ README.md                        # 「Anicca を 起動する 3 step」

禁止:
  - Dais の MUFG / 個人名 / 免許 / マイナンバー 文字列
  - CFO スキル (anicca-personal-cfo 別 repo)
  - 受託 hybrid skill (cfo-earner-lancers etc.、 archive)
  - preset skill clone (= 「これ install しといて」)

OK:
  - 汎用 skill (Felix path 全部)
  - SKILL.md catalog で 提示、 Anicca 自身が install を 決める
  - Docker image (誰でも 起動 可)
```

---

## 1次 source

- Felix: felixcraft.ai / shopclawmart.com / openclaw.report/use-cases/felix-zero-human-company / bankless.com Nat Eliason podcast / midastools.co/blog/felix-craft-story / Base blog
- Kelly Claude: iamkelly.ai / buildmyidea.com / austenallred.gumroad.com/l/jzketz / openclawbook.xyz / messari.io/project/kellyclaude/profile / x.com/Austen
- x402: github.com/x402-foundation/x402 / docs.cdp.coinbase.com/x402/welcome / blog.base.org/the-agentic-economy-is-here
- Factory Floor: factoryfloor.dev / github.com/alltuner/factoryfloor
- Browserbase: docs.browserbase.com/integrations/x402
- Algora: algora.io/bounties / Code4rena: code4rena.com/bounges / Sherlock: sherlock.xyz

---

## Anicca v2.2 SPEC への 必要 修正

ANICCA_TRUE_AUTONOMY_SPEC.md v2.1 (2026-05-31 朝) は **「pure on-chain only」** に振り過ぎ。 Felix 実例で **「Day 0 founder name で Stripe + Mac Mini OK、 以後 永遠 触らない」 hybrid も 月収 $300k 実現可** と確定。

v2.2 で 追記:
1. §2 アーキ に **Stream A (Stripe path)** + **Stream B (Build My Idea)** + **Stream C (x402)** の 3 並走 で 書き直す
2. §3 Critical path = Felix Day-0 → Day-30 を そのままコピー
3. §10 NOT in scope から **「Day 0 founder Stripe account」 を 削除** (Dais revised 許容と合致)
4. §6 anicca-oss skill catalog に **pdf-sales / build-my-idea / claw-mart-persona / stripe-checkout / gumroad-publish** を 追加
