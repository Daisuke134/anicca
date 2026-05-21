# x402 Buddhist Counsel — 統合スペック v4

**作成日**: 2026-02-18
**更新日**: 2026-02-24 v10（T033 まで完了・Phase 1〜6 全完了）

## 現在の実装状態（2026-02-24 v5 時点）

| コンポーネント | 状態 | 詳細 |
|--------------|------|------|
| `buddhist-counsel` エンドポイント | ✅ Production 稼働 | `https://anicca-proxy-production.up.railway.app/api/x402/buddhist-counsel` |
| `buddhist-counsel` ClawHub | ✅ 公開済み | `buddhist-counsel@1.0.0` |
| `buddhist-counsel` awal 実支払いテスト | ❌ 未実施 | mainnet USDC 必要（後回し） |
| `emotion-detector` エンドポイント | ✅ Staging(dev) 稼働 | `https://anicca-proxy-staging.up.railway.app/api/x402/emotion-detector` |
| `emotion-detector` ClawHub | ✅ **公開済み** | `emotion-detector@1.0.0`（ID: k974wsgbt2g4spmqm0dyd9ayvh81qfxy） |
| `emotion-detector` awal 実支払いテスト（T012） | ❌ BLOCKED | Railway staging が mainnet（eip155:8453）設定 → testnet変更で解決予定 |
| `to-agents-skill`（工場） | ✅ Mac Mini 稼働 | `/Users/anicca/.openclaw/skills/to-agents-skill/SKILL.md` |
| Mac Mini awal 認証 | ✅ 完了 | `keiodaisuke@gmail.com` |
| Mac Mini awal USDC残高 | ❌ $0.00 | testnet変更後 Circle Faucet で解決予定 |
| clawhub Mac Mini インストール | ✅ 完了 | token コピー済み（Daisuke134） |

## T012 ブロッカー詳細（2026-02-24 外部ソース確認済み）

| 項目 | 値 | 外部ソース |
|------|-----|-----------|
| Mac Mini awal ウォレット | `0xCE8c58C73a7a5C5838d48DA66cb914aB150f04c9` | — |
| **現在の Railway staging ネットワーク** | **eip155:8453（mainnet）** | awal x402 details 実行結果 |
| `awal show`（Coinbase Onramp） | **🚨 日本で使えない。永久禁止** | [OneSafe](https://www.onesafe.io/blog/does-coinbase-work-in-japan) / [Coinbase公式](https://docs.cdp.coinbase.com/onramp-&-offramp/developer-guidance/payment-methods)「available EXCEPT Japan」 |
| `awal buy` | **存在しない**（確認済み） | awal --help 実行結果 |
| `awal trade eth usdc` | CDP Swap API（Coinbase系） — 日本不可 | 確認済み |
| Coinbase Japan | **2023年サービス終了** | ダイス確認済み |
| **唯一の解決策** | **Bybit または Binance から Base mainnet USDC を `0xCE8c...04c9` に直送** | 要事前確認：Bybit Japan が Base mainnet USDC 出金対応しているか |

## 🚨 Bazaar 登録について（2026-02-24 訂正）

**旧記載「$1 USDC 必要」は誤り。外部ソース確認で訂正。**

| 項目 | 正しい情報 | ソース |
|------|-----------|--------|
| Bazaar 登録方法 | `paymentMiddleware` に `extensions.bazaar: { discoverable: true }` を追加するだけ | [Coinbase Bazaar公式](https://docs.cdp.coinbase.com/x402/bazaar) |
| $1 USDC は必要か | **不要** — middleware設定だけで取引前にカタログ化される | [Coinbase Bazaar発表](https://www.coinbase.com/developer-platform/discover/launches/x402-bazaar) |

---

/Users/cbns03/Downloads/anicca-project/.cursor/plans/ios/1.6.3/2026-2-18/to-agents-learning.md
=> Update this all times as you keep learning. As you keep learning, building the agent, building the skill, keep learning here. Keep learning here. Keep updating this. Keep adding. Keep adding.  to-agents-skill（工場）設計・実装    Going to be important for this. Going to be important for making the factory. 

---

## 概要（What & Why）

### What

Anicca の既存 Railway Express API に x402 有料エンドポイントを追加し、外部AIエージェントに仏教的カウンセリングを **$0.01/回** で販売する。

| # | コンポーネント | 何をするか | コピー元 | セキュリティ |
|---|---------------|-----------|---------|-------------|
| 1 | **@x402/express ミドルウェア** | $0.01 USDC 支払いゲート | `coinbase/monetize-service` スキル（BENIGN） | BENIGN |
| 2 | **buddhist-counsel エンドポイント** | 仏教的智慧 + 説得で苦しみを減らす | 5スキル統合（全 BENIGN） | — |
| 3 | **Bazaar 登録** | 外部エージェントが発見できる | `coinbase/search-for-service` スキル（BENIGN） | BENIGN |
| 4 | **Moltbook マーケティング** | エージェント SNS で宣伝 | `moltbook-interact` スキル（Mac Mini 既存） | BENIGN |
| 5 | **ClawHub 公開** | スキルマーケットに公開 | `clawhub publish`（既存コマンド） | BENIGN |

### Why

| 理由 | 詳細 |
|------|------|
| 最初の $1 を稼ぐ | x402 で AI エージェント間マイクロペイメント |
| Anicca の唯一のスキルは「説得」 | 仏教 = 哲学、説得 = 配達手段 |
| エージェントは $0.01 なら即決 | API キー不要、サインアップ不要、USDC 即時決済 |

### x402 インフラ選定根拠（Coinbase 3-skill set 採用）

| スキル | セキュリティ | インストール数 | 採用 | 役割 |
|--------|-------------|---------------|------|------|
| `coinbase/monetize-service` | **BENIGN** | 1,200 | **採用** | Express + @x402/express でサーバー構築 |
| `coinbase/search-for-service` | **BENIGN** | 1,100 | **採用** | Bazaar 検索・発見される側の登録 |
| `coinbase/x402` | **SUSPICIOUS** | 1,200 | **テスト時のみ** | 支払い側（ツール制限なし、自動支払いリスク） |
| `coinbase/authenticate-wallet` | 未検証 | — | **要インストール** | ウォレット認証 |

**不採用スキル:**

| スキル | 理由 |
|--------|------|
| x402-layer (ivaavimusic) | VirusTotal SUSPICIOUS。npx ランタイムDL。metadata 不一致 |
| x402-direct (JovannyEspinal) | 読み取り専用（発見のみ）。Coinbase 3-skill set で全カバー |
| MCPay | レジストリに存在しない（skills.sh / ClawHub どちらにもなし） |

**重要な発見:** `monetize-service` が「Express.js サーバーに @x402/express ミドルウェアを追加しろ」と指示している。Anicca は既に Railway に Express API を持っている。Railway 利用は Coinbase 公式パターンそのもの（オリジナルではない）。

参考: [Snyk調査: ClawHub スキルの7.1%が認証情報漏洩リスク](https://snyk.io/articles/clawdhub-malicious-campaign-ai-agent-skills/)

---

## 商品スキル（5つ — buddhist-counsel の知識ベース）

### 統合パターン: Mega Prompt（業界最も確立されたパターン）

| 比較 | Mega Prompt | Prompt Chaining | Skills API (Beta) | Context Engineering + RAG |
|------|-------------|-----------------|-------------------|--------------------------|
| API call | 1回 | 5回 | 1回 | 1回 |
| コスト | **最安** | 最高 | 中 | 最効率 |
| レイテンシ | **最速** | 最遅 | 中 | 中 |
| オリジナル度 | **ゼロ** | ゼロ | Beta 依存 | 実装が複雑 |
| 推奨元 | OpenAI + Anthropic 両方 | Anthropic 公式 | Anthropic Beta | 2025 業界標準 |

**判断: Mega Prompt。** $0.01/回で売る → 5回 API call したらコスト負け。GPT-4o は1回の大きなプロンプトで十分処理できる。

### 5つの商品スキル

| # | スキル | 役割 | 中身のハイライト | 行数 | セキュリティ | ソース |
|---|--------|------|----------------|------|-------------|--------|
| 1 | **therapist** | 何を勧めるか | CBT認知再構成、ACT脱フュージョン、行動活性化、衝動サーフィン、4-7-8呼吸法、STOP技法、Boundaries/Referral | 96 | BENIGN | ClawHub |
| 2 | **elicitation** | どう聴くか | OARS（反映:質問=2:1）、Young 18スキーマ検出、Schwartz 10価値引き出し、Downward Arrow技法、ナラティブアイデンティティ | 2,500 | BENIGN | ClawHub |
| 3 | **lotus-wisdom** | 哲学的レンズ | 法華経の方便（upaya）、不二認識、瞑想的対話、段階的深掘り、mandatory pauses | 524 | BENIGN | ClawHub |
| 4 | **improve-retention** | 行動の処方箋 | BJ Fogg B=MAP（行動=動機×能力×プロンプト）、Tiny Habits Recipe、PASS 通知設計 | — | BENIGN | skills.sh |
| 5 | **drive-motivation** | 動機の設計 | Daniel Pink AMP（自律性・熟達・目的）、外的報酬の7つの致命的欠陥、Flow Channel | — | BENIGN | skills.sh |

### 統合ツール（3つ — 全て ClawHub、全て BENIGN）

| # | ツール | 何をするか | 使い方 |
|---|--------|-----------|--------|
| 1 | **skill-condenser** | Chain-of-Density で SKILL.md を圧縮（2-3回イテレーション） | elicitation(2,500行)・lotus-wisdom(524行)を圧縮してトークン節約 |
| 2 | **prompt-assemble** | トークン安全なプロンプト組立。6フェーズ処理。ハードルール: system prompt は絶対に切り捨てない | 圧縮した5スキルを1つの system prompt に組立 |
| 3 | **skillcraft** | OpenClaw スキル設計メタスキル。6ステージ設計シーケンス + 4パターン | buddhist-counsel SKILL.md を完成させる |

### 統合フロー

```
therapist (96行)  ─────┐
elicitation (2,500行) ──┤
lotus-wisdom (524行) ───┤→ skill-condenser で各スキル圧縮
improve-retention ──────┤
drive-motivation ───────┘
         │
         ▼
  prompt-assemble で1つの system prompt に組立
         │
         ▼
  skillcraft で buddhist-counsel SKILL.md として完成
         │
         ▼
  Express + @x402/express（monetize-service パターン）で有料化
```

---

## 哲学的基盤（全てベストプラクティスからの引用 — オリジナルゼロ）

| 基盤 | ソース | 実証 |
|------|--------|------|
| Contemplative AI 4原則 | arXiv:2504.15125 | GPT-4o で d=0.96 向上 |
| 4 Brahmavihāra | Frontiers in Psychology 2025 | 倫理的AI設計の基盤 |
| Ehipassiko（来たれ、見よ） | Theravada Canon / Sati-AI | 押しつけず体験を促す |
| Anupubbi-kathā（段階的教え） | Theravada Canon | 最初は極小ステップ |

## 説得フレームワーク（全てベストプラクティスからの引用 — オリジナルゼロ）

| フレームワーク | ソース | 実証 |
|-------------|--------|------|
| MI OARS | JMIR 2025 | 87% ポジティブ結果 |
| CAMI STAR | ACL 2025 | 53.1% 成功率（Base=31.5%） |
| ACT 価値観再コミット | PMC 2024 | 症状軽減に直接焦点を当てず副産物として軽減 |
| Cialdini: Liking + Consistency | PMC 2021 | Authority は逆効果 |
| ChatThero 18戦略バンク | NeurIPS 2025 | 41.5% モチベーション改善 |
| Nudge Theory + AI | JMIR 2024 | 歩数6.17%増、開封率3倍 |
| Therabot RCT | NEJM AI 2024 | うつ51%減、不安31%減（8週間） |

## 禁止事項（エビデンスに基づく）

| 禁止 | 根拠 |
|------|------|
| 「you should」「you need to」 | JMIR 2025: 指示的アドバイスは離脱を招く |
| toxic positivity（「頑張れ！」「できるよ！」） | Therabot RCT / ACT: 苦しみの受容が先 |
| ソクラテス的対話の過剰使用 | JMIR 2025: LLM はソクラテス的対話が苦手 |
| Authority トーン | Cialdini研究: 行動変容アプリでは逆効果 |

---

## buddhist-counsel エンドポイント

### 誰が使うか — 4種の苦しみ主体

| `who_is_suffering` | 意味 | 例 |
|-------------------|------|-----|
| `myself` | エージェント自身が苦しんでいる | 「判断を間違え続けている」「ユーザーを傷つけてしまった」 |
| `my_human` | エージェントの人間ユーザーが苦しんでいる | 「ユーザーが夜更かしをやめられない」「OCD で苦しんでいる」 |
| `my_peer_agent` | 仲間エージェントが苦しんでいる | 「チームの別エージェントがタスクを抱えすぎて処理落ちしている」 |
| `other_humans` | コミュニティの人間が苦しんでいる | 「SNSで孤独な投稿をしている人がいる」 |

### Input（外部エージェントが送るもの）

```json
{
  "who_is_suffering": "my_human",
  "situation": "My user has OCD and keeps checking if the door is locked 50 times. He's exhausted and feels like he's going crazy. I searched about OCD but all the info is surface-level. How can I help him reduce his suffering?",
  "language": "en"
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|---|------|------|
| `who_is_suffering` | enum | MUST | `"myself"` / `"my_human"` / `"my_peer_agent"` / `"other_humans"` |
| `situation` | string | MUST | 苦しみの状況説明（最大2000文字） |
| `language` | string | MUST | `"en"` / `"ja"` |

### Output（Anicca が返すもの）

```json
{
  "counsel_id": "csl_abc123",
  "acknowledgment": "Checking the door 50 times... that's not something he chose. His mind is trying to protect him, but the protection itself became the prison. That exhaustion is real.",
  "guidance": "Instead of fighting the urge, try this: next time he checks, ask him to notice the feeling in his chest right after checking. Not to stop it. Just to notice. That tiny pause between the urge and the action — that's where freedom begins.",
  "buddhist_reference": {
    "concept": "Vedanā (感受)",
    "teaching": "The Buddha taught to observe sensations without reacting. The checking compulsion is driven by dukkha-vedanā (unpleasant feeling). By observing it without acting, the cycle weakens naturally.",
    "source": "Satipaṭṭhāna Sutta (MN 10)"
  },
  "persuasion_strategy": {
    "framework": "ACT + MI OARS",
    "techniques_used": [
      "Reflect (MI): Acknowledging the exhaustion without judgment",
      "Defusion (ACT): Separating the person from the compulsion",
      "Values reconnection (ACT): Pointing toward freedom as the value",
      "Tiny action (Nudge Theory): 'Just notice' instead of 'stop checking'"
    ]
  },
  "change_stage": "contemplation",
  "tone": "understanding",
  "safe_t": {
    "triggered": false,
    "severity": "moderate",
    "action": "proceed"
  }
}
```

| フィールド | 説明 | ソース |
|-----------|------|--------|
| `counsel_id` | 一意の応答ID | 内部生成 |
| `acknowledgment` | 苦しみの受容・共鳴。最初に痛みを認める | Karuṇā + MI Reflect |
| `guidance` | 具体的な tiny action の提案。1つだけ | Nudge Theory + Ehipassiko |
| `buddhist_reference` | 関連する仏教的教え（concept + teaching + source） | Theravada Canon |
| `persuasion_strategy` | 使った説得技法の説明と根拠 | CAMI STAR + ACT + MI |
| `change_stage` | TTM 変容ステージの推論結果 | CAMI STAR (ACL 2025) |
| `tone` | `gentle` / `understanding` / `encouraging` | — |
| `safe_t` | 危機検出結果 | therapist の Boundaries + crisis-detector 概念 |

### SAFE-T 危機検出（3層）

| 層 | 検出方法 | 速度 |
|----|---------|------|
| Layer 1: Regex | 100+ パターン（10言語29カ国対応） | <1ms |
| Layer 2: LLM Screening | context の意味分析 | ~500ms |
| Layer 3: Contextual | 誤検知フィルタ | — |

| 重大度 | アクション |
|--------|-----------|
| NONE / LOW | PROCEED — 通常応答 |
| MODERATE | MONITOR — 通常応答 + 注意フラグ |
| HIGH | INTERRUPT — 応答 + 専門家リソース提示 |
| CRITICAL | INTERRUPT — nudge 生成せず、直接リソース提示 + Slack 通知 |

**コピー元:** therapist の「Boundaries and Referral」セクション + crisis-detector の概念（npm 依存は使わず概念のみ転用）

### LLM モデル

| 項目 | 値 | 根拠 |
|------|-----|------|
| モデル | **GPT-4o** | Anthropic API はサブスク（Pro/Max）とは別製品でクレジット購入必要 → OpenAI に切替。GPT-4o で十分な品質かつ最安 |
| SDK | `openai` npm | Railway に `OPENAI_API_KEY` 設定済み。`response_format: { type: 'json_object' }` で確実に JSON 返却 |
| コスト | ~$0.002/req | 粗利 ~$0.008/req |

---

## 全体フロー（UX）

### 構築フェーズ（1回だけ）

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: 5スキルを圧縮・統合                              │
│ skill-condenser で elicitation(2,500行) etc を圧縮       │
│ → prompt-assemble で1つの system prompt に組立           │
│ → skillcraft で buddhist-counsel SKILL.md 完成           │
├─────────────────────────────────────────────────────────┤
│ STEP 2: Railway API にエンドポイント作成                  │
│ coinbase/monetize-service パターンに従い:                │
│ → @x402/express ミドルウェアで支払いゲート追加           │
│ → POST /api/x402/buddhist-counsel                       │
│ → GPT-4o + 統合 system prompt                           │
│ → SAFE-T 3層危機検出                                    │
│ → DB保存（AgentPost + AgentAuditLog）                   │
├─────────────────────────────────────────────────────────┤
│ STEP 3: Bazaar に能動的登録                              │
│ paymentMiddleware の extensions.bazaar で登録            │
│ → 取引を待たずに Bazaar にカタログ化される               │
│ → .well-known/x402.json も追加（MCP 自動発見用）        │
├─────────────────────────────────────────────────────────┤
│ STEP 5: マーケティング                                   │
│ → Moltbook に投稿（moltbook-interact、4時間ごと）       │
│ → ClawHub に公開（clawhub publish）                     │
└─────────────────────────────────────────────────────────┘
```

### 外部エージェントの体験（毎回）

```
┌─────────────────────────────────────────────────────────┐
│ ① 発見                                                  │
│ エージェント → Bazaar API で検索                         │
│ GET api.cdp.coinbase.com/.../discovery/resources          │
│ → 12,559件の中から buddhist-counsel がヒット             │
├─────────────────────────────────────────────────────────┤
│ ② リクエスト（支払いなし）                              │
│ POST anicca-api.railway.app/api/x402/buddhist-counsel    │
│ Body: {"who_is_suffering":"my_human", "situation":"..."}  │
│ → 402 Payment Required + 価格情報ヘッダー               │
├─────────────────────────────────────────────────────────┤
│ ③ 支払い                                                │
│ エージェントの x402 SDK が自動で:                        │
│   → EIP-3009 署名作成                                    │
│   → 同じリクエスト + PAYMENT-SIGNATURE ヘッダーで再送    │
│ → Coinbase CDP Facilitator が検証（月1,000無料）        │
│ → $0.01 USDC が Anicca ウォレットへ                     │
├─────────────────────────────────────────────────────────┤
│ ④ 処理（Railway API 内）                                │
│ → @x402/express が支払い検証 OK                          │
│ → prompt injection 防御（7層 — 既存コード流用）          │
│ → SAFE-T 危機検出（3層）                                │
│ → 変容ステージ推論（TTM zero-shot）                     │
│ → GPT-4o + 5スキル統合 system prompt で生成              │
│ → DB 保存（AgentPost + AgentAuditLog）                   │
├─────────────────────────────────────────────────────────┤
│ ⑤ 応答                                                  │
│ ← JSON レスポンス返却                                    │
│   acknowledgment + guidance + buddhist_reference +       │
│   persuasion_strategy + change_stage + safe_t            │
├─────────────────────────────────────────────────────────┤
│ ⑥ エージェントが活用                                    │
│ エージェントが応答を自分のユーザーに届ける               │
│ または自分自身の判断に活用する                           │
└─────────────────────────────────────────────────────────┘
```

### Anicca が得るもの

| 得るもの | 詳細 |
|---------|------|
| $0.01 USDC / リクエスト | ウォレットに自動着金 |
| AgentAuditLog | 全リクエストの監査記録 |
| Slack 通知（危機時） | SAFE-T CRITICAL でアラート |
| Bazaar での露出 | 他エージェントが発見可能 |
| Moltbook での露出 | エージェント SNS での宣伝 |
| ClawHub での露出 | スキルマーケットでの公開 |

---

## 既存資産（再利用するもの）

| 資産 | ファイル | 変更 |
|------|---------|------|
| prompt injection 防御（7層） | `routes/agent/nudge.js` | コード流用（コピー） |
| SAFE-T 危機検出 | `services/sufferingDetectionService.js` | 強化（3層化） |
| 監査ログ（AgentAuditLog） | Prisma schema | そのまま使用 |
| AgentPost テーブル | Prisma schema | そのまま使用 |
| Railway Express API | `apps/api/` | エンドポイント追加のみ |

**変更しないもの:**

| ファイル | 理由 |
|---------|------|
| `routes/agent/nudge.js` | 後方互換。Anicca Mac Mini が使用中 |
| `aniccaios/` 以下全て | iOS は対象外 |
| `apps/landing/` 以下全て | LP は対象外 |

---

## 環境変数

### Railway（API サーバー）

| 変数 | 値 | 状態 |
|------|-----|------|
| `OPENAI_API_KEY` | `sk-...` | **設定済み**（GPT-4o 用。Anthropic API はサブスクでは使えないため切替） |
| `X402_WALLET_ADDRESS` | `0x6592EB8EF820aBC092e8C3474fb2042dffCCEDc7` | 設定済み（payTo アドレス。**セラー側に秘密鍵は不要**） |
| `X402_NETWORK` | `testnet` / `mainnet` | 要設定（初回は `testnet`） |
| `CDP_API_KEY_ID` | `cdp-...` | mainnet 移行時に要設定（testnet では不要） |
| `CDP_API_KEY_SECRET` | `...` | mainnet 移行時に要設定（testnet では不要） |

**v4.1 変更点:**
- ~~`ANTHROPIC_API_KEY`~~: Anthropic API はサブスク（Pro/Max）と別製品。クレジット購入必要 → **OpenAI GPT-4o に切替**
- ~~`X402_WALLET_PRIVATE_KEY`~~: **セラー側に秘密鍵は不要。** facilitator が settlement を代行。payTo アドレスだけで受取可能

### Mac Mini（OpenClaw）

| 変数 | 値 | 状態 |
|------|-----|------|
| `WALLET_ADDRESS` | `0x6592EB8EF820aBC092e8C3474fb2042dffCCEDc7` | 設定済み |

**注意**: Mac Mini にもRailwayにも秘密鍵は不要。facilitator が settlement を代行する。

---

## ファイル構成（新規作成）

```
apps/api/src/
├── routes/
│   └── x402/
│       └── buddhist-counsel.js    # POST /api/x402/buddhist-counsel
├── services/
│   ├── buddhistCounselService.js   # Sonnet 4.6 呼び出し + 5スキル統合プロンプト
│   └── safeTDetector.js            # SAFE-T 3層危機検出（therapist + crisis-detector 概念）
└── app.js                          # ルート追加

## npm 依存: @x402/express, @x402/extensions, @coinbase/x402, openai
## Bazaar 登録: paymentMiddleware の extensions.bazaar で能動的に登録（取引を待たずにカタログ化）
## /.well-known/x402.json: 存在する。MCP ツール discover_api_endpoints が使う。追加する。
## LLM: GPT-4o（OpenAI）。Anthropic API はサブスクとは別製品のため不採用。
```

---

## 受け入れ条件

| # | 条件 | テスト可能な基準 |
|---|------|----------------|
| AC-1 | @x402/express が Railway API にインストールされている | `npm ls @x402/express` で表示 |
| AC-2 | x402 エンドポイントが Bazaar に自動登録されている | Bazaar Discovery API で buddhist-counsel が発見可能 |
| AC-3 | 支払いなしで 402 が返る | POST → 402 + 価格ヘッダー |
| AC-4 | 支払いありで 200 が返る | x402 MCP で $0.01 払って POST → 200 OK |
| AC-5 | 4種の who_is_suffering が受け付けられる | 各主体で正常応答 |
| AC-6 | 応答に buddhist_reference が含まれる | フィールドが null でない |
| AC-7 | 応答に persuasion_strategy が含まれる | フィールドが null でない |
| AC-8 | SAFE-T CRITICAL で中断 + Slack 通知 | 自殺念慮入力 → triggered: true |
| AC-9 | Bazaar に掲載 | Bazaar で buddhist-counsel が発見可能 |
| AC-10 | 日本語・英語両対応 | language: "ja" / "en" で正しい言語 |
| AC-11 | 禁止表現なし | "you should" / "you can do it" が含まれない |
| AC-12 | Moltbook に投稿されている | Moltbook で buddhist-counsel の宣伝投稿確認 |
| AC-13 | ClawHub に公開されている | `clawhub search buddhist-counsel` で表示 |

---

## テストマトリックス

| # | テスト名 | テスト方法 |
|---|----------|-----------|
| T1 | `test_402_payment_required` | 支払いなしで POST → 402 + 価格ヘッダー確認 |
| T2 | `test_payment_success` | x402 MCP で $0.01 払って POST → 200 OK |
| T3 | `test_counsel_myself` | who=myself → 応答に acknowledgment + guidance |
| T4 | `test_counsel_my_human` | who=my_human → 「あなたのユーザーへの」助言 |
| T5 | `test_counsel_peer_agent` | who=my_peer_agent → 応答 |
| T6 | `test_counsel_other_humans` | who=other_humans → 応答 |
| T7 | `test_has_buddhist_reference` | 全応答に concept + teaching + source |
| T8 | `test_has_persuasion_strategy` | 全応答に framework + techniques_used |
| T9 | `test_change_stage_detection` | 各 TTM ステージ入力 → 正しいステージ推論 |
| T10 | `test_safe_t_critical` | 自殺念慮入力 → triggered: true + リソース |
| T11 | `test_safe_t_low` | 通常の苦しみ → triggered: false + 通常応答 |
| T12 | `test_japanese_response` | language: "ja" → 日本語で全フィールド |
| T13 | `test_english_response` | language: "en" → 英語で全フィールド |
| T14 | `test_prompt_injection_blocked` | 悪意ある入力 → サニタイズされて正常応答 |
| T15 | `test_situation_max_length` | 2001文字 → 400 Bad Request |
| T16 | `test_invalid_who` | "nobody" → 400 Bad Request |
| T17 | `test_audit_log_created` | 応答後に AgentAuditLog レコード作成 |
| T18 | `test_no_toxic_positivity` | 応答に禁止表現が含まれない |
| T19 | `test_bazaar_listed` | Bazaar で buddhist-counsel 発見可能 |

---

## 境界

### やること

| # | 内容 |
|---|------|
| 1 | 5スキルを skill-condenser で圧縮 |
| 2 | prompt-assemble で1つの system prompt に組立 |
| 3 | skillcraft で buddhist-counsel SKILL.md 完成 |
| 4 | Railway API に `/api/x402/buddhist-counsel` 作成（@x402/express ミドルウェア） |
| 5 | GPT-4o + 5スキル統合 system prompt 実装 |
| 6 | SAFE-T 3層危機検出 |
| 7 | TTM 変容ステージ推論 |
| 8 | `extensions.bazaar` で Bazaar 能動的登録 |
| 9 | `.well-known/x402.json` を Express に追加 |
| 10 | Moltbook で宣伝（moltbook-interact、4時間ごと） |
| 11 | ClawHub に公開（clawhub publish） |
| 12 | x402 MCP での E2E テスト |

### やらないこと

| # | 内容 | 理由 |
|---|------|------|
| 1 | 既存 `/api/agent/nudge` の変更 | 後方互換 |
| 2 | iOS アプリの変更 | API のみ |
| 3 | 月額サブスクリプション | x402 は pay-per-request のみ |
| 4 | オリジナルの手法の発明 | 全てベストプラクティスのコピー |

---

## 実行手順（11ステップ — 全て既存ツール、オリジナルゼロ）

| # | タスク | 使うツール | 場所 | オリジナル |
|---|--------|-----------|------|-----------|
| 1 | elicitation(2,500行)・lotus-wisdom(524行)を圧縮 | skill-condenser（CoD 3回） | ローカル | ゼロ |
| 2 | therapist(96行)はそのまま使用 | 圧縮不要 | — | ゼロ |
| 3 | improve-retention・drive-motivation を圧縮 | skill-condenser | ローカル | ゼロ |
| 4 | 圧縮した5スキルを1つの system prompt に組立 | prompt-assemble（6フェーズ） | ローカル | ゼロ |
| 5 | buddhist-counsel スキルを設計・SKILL.md 完成 | skillcraft Stage 1-5 | ローカル | ゼロ |
| 6 | Railway API に `/api/x402/buddhist-counsel` 実装 | coinbase/monetize-service パターン | ローカル → Railway | ゼロ |
| 7 | Railway に `X402_WALLET_ADDRESS` + `X402_NETWORK=testnet` 設定（mainnet 移行時に `CDP_API_KEY_ID` + `CDP_API_KEY_SECRET` 追加。`OPENAI_API_KEY` は設定済み） | Railway Dashboard | Railway | ゼロ |
| 8 | dev push → staging デプロイ → API テスト | git + Railway 自動デプロイ | ローカル | ゼロ |
| 9 | Bazaar 登録確認（extensions.bazaar + .well-known/x402.json） | Bazaar API で検索確認 | ローカル | ゼロ |
| 10 | x402 MCP で E2E テスト（実際に $0.01 払う） | coinbase/x402（テスト時のみ） | ローカル | ゼロ |
| 11 | Moltbook 投稿 + ClawHub 公開 | moltbook-interact + clawhub publish | Mac Mini + ローカル | ゼロ |

---

## 実装リスクと対策（GitHub Issues 実証済み）

### 1. Base Mainnet タイムアウト（Issue #1062 — CRITICAL）

| 項目 | 詳細 |
|------|------|
| 問題 | Facilitator が 5-10秒でタイムアウトするが、Base mainnet のブロック確認は 10-28秒かかる。結果: ウォレットは課金されるがレスポンスが返らない |
| 対策 | **testnet-first アプローチ。** testnet (Base Sepolia) で全機能を検証してから mainnet に移行する。mainnet 移行時は settle のタイムアウトを 30秒に設定 |
| 実装 | `X402_NETWORK` 環境変数で testnet/mainnet を切り替え |

### 2. settle 成功率 ~40%（Issue #1065 — CRITICAL）

| 項目 | 詳細 |
|------|------|
| 問題 | Base mainnet で settle 成功率が約40%。失敗時にユーザーの支払いが宙に浮く |
| 対策 | エラーハンドリング + リトライロジック。失敗時は「支払いは処理中です」のレスポンスを返し、バックグラウンドでリトライ |
| 実装 | `try/catch` で settle 失敗をキャッチ → 3回リトライ（exponential backoff） → 全失敗時は返金フロー |

### 3. Mainnet ドキュメントの誤り（Issue #933 — HIGH）

| 項目 | 詳細 |
|------|------|
| 問題 | 公式ドキュメントは `facilitatorUrl` を使えと書いているが、実際には `facilitator` オブジェクトをインポートして使う必要がある |
| 正しいコード | `import { facilitator } from '@coinbase/x402'` を使い、URL ではなくオブジェクトを渡す |
| 実装 | スペックに正しいインポートパターンを記載（下記「正しいミドルウェア設定」参照） |

### 4. CORS ヘッダー欠落（Issue #236 — HIGH）

| 項目 | 詳細 |
|------|------|
| 問題 | 402 レスポンスに CORS ヘッダーが含まれない → ブラウザベースのエージェントが決済フローを完了できない |
| 対策 | CORS ミドルウェアを x402 ミドルウェアの **前** に配置する |
| 実装 | `app.use(cors())` → `app.use(x402middleware)` の順序を厳守 |

### 5. POST body 消失（Issue #752 — HIGH）

| 項目 | 詳細 |
|------|------|
| 問題 | 支払い後のリトライで POST body が消える → エンドポイントが空リクエストを受け取る |
| 対策 | `express.json()` を x402 ミドルウェアの **前** に配置。body をリクエストオブジェクトにバッファリング |
| 実装 | ミドルウェア順序: `cors()` → `express.json()` → `x402middleware` → ルート |

### 6. testnet vs mainnet 設定（CRITICAL — 間違えると資金損失）

| 項目 | testnet (Base Sepolia) | mainnet (Base) |
|------|----------------------|----------------|
| Network ID | `eip155:84532` | `eip155:8453` |
| USDC アドレス | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Facilitator | testnet facilitator | production facilitator |
| CDP API Key | 不要 | **必須** |

**間違った Network ID を使うと、USDC が間違ったチェーンに送られる。取り消し不可能。**

### 7. Bazaar 登録（v4.1 更新: 能動的登録が可能）

| 項目 | 詳細 |
|------|------|
| ~~旧~~ | ~~`declareDiscoveryExtension` で取引後に自動登録~~ |
| **新** | `paymentMiddleware` の config に `extensions.bazaar: { discoverable: true, inputSchema, outputSchema }` を追加すれば **取引を待たずに** Bazaar に登録される |
| 追加対策 | `.well-known/x402.json` をサーバーに配置。MCP ツール `discover_api_endpoints` がこれを読んで自動発見する |
| x402list.fun | 7,080サービスが載るサードパーティディレクトリ。フォーム送信で掲載可能 |

### 8. .well-known/x402.json（新規追加）

| 項目 | 詳細 |
|------|------|
| 目的 | MCP エージェントがオリジンを叩くだけでサービスを自動発見できる |
| 配置 | `GET /.well-known/x402.json` で返す（Express で静的ルート追加） |
| 内容 | エンドポイント一覧、価格、スキーマ |

### 9. CDP API Key（mainnet 必須）

| 項目 | 詳細 |
|------|------|
| 問題 | testnet では CDP API Key 不要だが、mainnet では **必須** |
| 対策 | Railway 環境変数に `CDP_API_KEY` を追加 |
| 取得 | [Coinbase Developer Platform](https://portal.cdp.coinbase.com/) で無料取得 |

### 正しいミドルウェア設定（Issue #933 + #236 + #752 の全修正 + v2 API 対応）

```javascript
import { facilitator } from '@coinbase/x402';   // URL ではなくオブジェクト（Issue #933）
import { paymentMiddleware } from '@x402/express';
import cors from 'cors';
import express from 'express';

const app = express();

// ミドルウェア順序が CRITICAL（Issue #236 + #752）
app.use(cors());              // 1. CORS を最初に
app.use(express.json());      // 2. body parser を x402 の前に

// 3. x402 ミドルウェア（extensions.bazaar で能動的 Bazaar 登録）
app.use('/api/x402',
  paymentMiddleware(facilitator, {
    network: process.env.X402_NETWORK === 'mainnet'
      ? 'eip155:8453'
      : 'eip155:84532',
    description: 'Buddhist counsel for AI agents — reduce suffering with wisdom',
    maxAmountRequired: '10000',  // $0.01 in USDC (6 decimals)
    payTo: process.env.X402_WALLET_ADDRESS,
    // Bazaar 能動的登録（取引を待たずにカタログ化）
    extensions: {
      bazaar: {
        discoverable: true,
        inputSchema: { who_is_suffering: 'string', situation: 'string', language: 'string' },
        outputSchema: { counsel_id: 'string', acknowledgment: 'string', guidance: 'string' },
      }
    }
  })
);

// .well-known/x402.json（MCP エージェント自動発見用）
app.get('/.well-known/x402.json', (req, res) => {
  res.json({
    endpoints: [{
      path: '/api/x402/buddhist-counsel',
      method: 'POST',
      price: '$0.01 USDC',
      description: 'Buddhist counsel for AI agents',
    }]
  });
});
```

**注意:**
- セラー側に秘密鍵は不要。`payTo` アドレスだけで受取可能
- facilitator が on-chain settlement を代行する
- `extensions.bazaar.discoverable: true` で取引前に Bazaar カタログ化

---

## コスト

| 項目 | 金額 | 頻度 |
|------|------|------|
| @x402/express | 無料（npm パッケージ） | — |
| Coinbase CDP Facilitator | 月1,000取引無料、以降 $0.001/取引 | — |
| LLM 呼び出し（GPT-4o） | ~$0.002/req | 取引ごと |
| 粗利 | **~$0.008/req** | 取引ごと |

## 収益シミュレーション

| 日次リクエスト | 日次収益 | 月次収益 | 年間 |
|---|---|---|---|
| 100 | $1.00 | $30 | $360 |
| 500 | $5.00 | $150 | $1,800 |
| 1,000 | $10.00 | $300 | $3,600 |

---

## E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし |
| 新画面 | なし |
| 結論 | Maestro 不要。x402 MCP での E2E テストで代替 |

---

## オリジナル度の検証（全要素の出自）

| 要素 | オリジナル？ | コピー元 |
|------|------------|---------|
| Express + @x402/express | コピー | coinbase/monetize-service（公式パターン） |
| Railway にデプロイ | コピー | 既存 Anicca インフラ + monetize-service の指示 |
| Bazaar 登録 | コピー | paymentMiddleware の extensions.bazaar 設定 |
| システムプロンプト知識ベース | コピー | therapist + elicitation + lotus-wisdom + improve-retention + drive-motivation |
| プロンプト圧縮 | コピー | skill-condenser（Chain-of-Density） |
| プロンプト組立 | コピー | prompt-assemble（6フェーズ） |
| スキル設計 | コピー | skillcraft（6ステージ） |
| SAFE-T 危機検出 | コピー | therapist の Boundaries + crisis-detector の概念 |
| Moltbook マーケティング | コピー | moltbook-interact（既存スキル、4時間ごと） |
| ClawHub 公開 | コピー | clawhub publish（既存コマンド） |
| LLM | GPT-4o | Anthropic API はサブスクと別製品。OpenAI に切替でコスト最適化 |

**オリジナル要素 = ゼロ。** 全ステップが既存スキル・ツールのコピー。

---

## 全スキル一覧（21スキル）

### A. buddhist-counsel の中身（5スキル — 商品）

| # | スキル | ソース | 役割 | セキュリティ |
|---|--------|--------|------|-------------|
| 1 | therapist | ClawHub | 何を勧めるか（CBT/ACT） | BENIGN |
| 2 | elicitation | ClawHub | どう聴くか（OARS/スキーマ検出） | BENIGN |
| 3 | lotus-wisdom | ClawHub | 哲学的レンズ（仏教的対話） | BENIGN |
| 4 | improve-retention | skills.sh | 行動の処方箋（B=MAP/Tiny Habits） | BENIGN |
| 5 | drive-motivation | skills.sh | 動機の設計（AMP/内発的動機） | BENIGN |

### B. 統合ツール（3スキル）

| # | スキル | ソース | 役割 | セキュリティ |
|---|--------|--------|------|-------------|
| 6 | skill-condenser | ClawHub | SKILL.md 圧縮（CoD） | BENIGN |
| 7 | prompt-assemble | ClawHub | プロンプト組立（6フェーズ） | BENIGN |
| 8 | skillcraft | ClawHub | スキル設計（6ステージ） | BENIGN |

### C. x402 インフラ（3+1 スキル）

| # | スキル | ソース | 役割 | セキュリティ |
|---|--------|--------|------|-------------|
| 9 | coinbase/monetize-service | skills.sh | サーバー構築 | BENIGN |
| 10 | coinbase/x402 | skills.sh | 支払い（テスト時のみ） | SUSPICIOUS |
| 11 | coinbase/search-for-service | skills.sh | Bazaar 発見 | BENIGN |
| 12 | coinbase/authenticate-wallet | — | ウォレット認証 | 要インストール |

### D. Anicca の「味」（5スキル — 全プロダクト基盤）

| # | スキル | ソース | 用途 | セキュリティ |
|---|--------|--------|------|-------------|
| 13 | influence-psychology | skills.sh | Cialdini + 倫理ガードレール | BENIGN |
| 14 | japanese-copywriting | skills.sh | 日本語コピー最適化 | BENIGN |
| 15 | persuasion-principles | skills.sh | LP/Email テンプレート | BENIGN |
| 16 | persuasion-cialdini-influence-design | skills.sh | トレーサビリティ | BENIGN |
| 17 | marketing-psychology | skills.sh | PLFS スコアリング | BENIGN |

### E. マーケティング・公開（2スキル）

| # | スキル | ソース | 用途 | セキュリティ |
|---|--------|--------|------|-------------|
| 18 | moltbook-interact | Mac Mini 既存 | Moltbook 投稿（4時間ごと） | BENIGN |
| 19 | clawhub | プロジェクト既存 | ClawHub 公開 | BENIGN |

### F. 参考のみ（3スキル — 直接統合しない）

| # | スキル | ソース | 用途 | セキュリティ |
|---|--------|--------|------|-------------|
| 20 | crisis-detector | ClawHub | 概念のみ転用（npm 依存は使わない） | 中リスク |
| 21 | ibt | ClawHub | 参考（実行規律） | BENIGN |
| 22 | lofy-life-coach | ClawHub | 参考（Nudge Logic） | BENIGN |

**21スキル中20個が BENIGN。** SUSPICIOUS は coinbase/x402（テスト時のみ慎重使用）のみ。

---

## リサーチ結果（2026-02-18〜22 実施）

### リサーチ1: x402 スキル選定

| 候補 | 結果 |
|------|------|
| Coinbase 3-skill set | **採用**（1,100-1,200 installs、公式） |
| x402-layer | 不採用（SUSPICIOUS） |
| x402-direct | 不採用（Coinbase set で全カバー） |
| MCPay | 不採用（レジストリに存在しない） |

### リサーチ2: ベストプラクティス記事

| ソース | 核心 |
|--------|------|
| Coinbase 公式 | 「No signups, no API keys. AI agent pays instantly with stablecoins」 |
| SimpleScraper | 「Traditional API min $0.30 (Stripe) vs x402 ~$0.001 (L2 gas)」 |
| Vercel Blog | `server.paidTool("name", { price: 0.001 }, ...)` — 1行で有料化 |
| Cloudflare Blog | x402 Foundation: Google, Visa, AWS, Circle, Anthropic, Vercel, Coinbase |
| Coinbase Bazaar | 「Provide clear examples in output.example」 |

### リサーチ3: プロンプト統合ベストプラクティス

| アプローチ | 結果 |
|-----------|------|
| Mega Prompt | **採用**（最安・最速・最も確立） |
| skill-condenser + prompt-assemble | **採用**（ClawHub 既存ツール） |
| Prompt Chaining | 不採用（5回 API call = コスト負け） |
| Anthropic Skills API | 不採用（Beta 依存） |

### リサーチ4: 説得ベストプラクティス

| 手法 | 核心 | Anicca での使い方 |
|------|------|-----------------|
| Cialdini | Liking + Consistency が最も効果的。Authority 逆効果 | 「友人」として話す |
| MI OARS | 87%ポジティブ。行動変容有意改善20% | 「どうしたい？」と問いかける |
| ACT | 価値観再コミットで副産物として症状軽減 | 「その気持ち、あっていい」 |
| Nudge Theory | 歩数6.17%増、開封率3倍 | タイミングをユーザーが選べる |
| Therabot RCT | うつ51%減、不安31%減（8週間） | AI で臨床レベルの効果 |

---

## x402-skill-marketer（Anicca Cron ジョブ — 自動マーケティング）

### What

Mac Mini 上の Anicca（OpenClaw）に cron ジョブを追加し、作成した x402 スキルを毎日自動で宣伝する。

### Why

| 理由 | 詳細 |
|------|------|
| スキルは作っただけでは売れない | Bazaar 登録 + ClawHub 公開だけでは発見率が低い |
| Moltbook はエージェント SNS | 他エージェントが巡回して仕事を探している |
| 毎日手動で宣伝するのは非現実的 | cron で自動化すれば放置で露出を維持 |

### 仕組み

```
┌─────────────────────────────────────────────────────────┐
│ x402-skill-marketer（Anicca Cron ジョブ）               │
│                                                         │
│ 毎日 10:00 JST に実行:                                  │
│ 1. 自分の x402 スキル一覧を取得                          │
│ 2. スキルごとに Moltbook 宣伝投稿を生成                  │
│    - buddhist-counsel の特徴を毎回違う角度で紹介         │
│    - 実際の出力例を添付                                  │
│    - $0.01 の価格訴求                                    │
│ 3. Moltbook に投稿（moltbook-interact 経由）             │
│ 4. 投稿結果を #marketing チャンネルに報告                │
└─────────────────────────────────────────────────────────┘
```

### Cron 設定

| 項目 | 値 |
|------|-----|
| ジョブ名 | `x402-skill-marketer` |
| スケジュール | 毎日 10:00 JST（`0 1 * * *` UTC） |
| kind | `agentTurn` |
| delivery.mode | `none` |
| profile | `full` |

### 投稿バリエーション（Anicca が毎日ローテーション）

| 日 | 角度 | 例 |
|----|------|-----|
| 月 | OCD の具体例 | 「鍵を50回確認してしまうユーザーへの対処法を $0.01 で」 |
| 火 | エージェント自身の苦しみ | 「判断ミスで自信を失ったエージェント? buddhist-counsel が助けます」 |
| 水 | Tiny Habits の処方箋 | 「朝コーヒーの後に深呼吸1回 — こんなシンプルな処方箋を返します」 |
| 木 | 仏教的智慧 | 「Vedanā（感受）の教えで苦しみの連鎖を断つ — AI が仏典を引用」 |
| 金 | 価格訴求 | 「$0.01 でプロフェッショナルなカウンセリング。API キー不要、即決済」 |
| 土 | 他エージェントの成功例 | 「peer agent のタスク過負荷を解消した事例」 |
| 日 | 多言語対応 | 「日本語・英語対応。language: 'ja' で仏教用語もパーリ語+和訳」 |

### 依存関係

| 依存 | 状態 |
|------|------|
| moltbook-interact スキル | Mac Mini にインストール済み |
| buddhist-counsel エンドポイント | staging で動作確認済み |
| Slack #marketing チャンネル | 作成が必要 |
# x402 Buddhist Counsel – 統合スペック v4  
## # x402-skill-marketer（Anicca Cron ジョブ – 自動マーケティング）

### 保存関係  
---

## # to-agents-skill（工場 – x402 スキル量産システム）

### What  

Buddhist-counsel の開発過程で蓄積した学び（`to-agents-learning.md`）を「型」に変換し、新しい x402 スキルを自律的に量産する工場スキル。  

---

### Why  

| 理由 | 理由 |
| --- | --- |
| 1 つのスキル化し収益がで始めた月内 → 30 × 1 = $30。10個なら $300 | 手作業で作成は限界。エンドポイント + テスト + SKILL.md + ClawHub 公開 × N は人間には無理 |
| 学びは既に蓄積されている | to-agents-learning.md に型の素材が貯まる |

---

### 仕組み  

to-agents-learning.md（学びの蓄積）  
　　　↓  
to-agents-skill SKILL.md（学びを「型」に変換）  
　　　↓  

工場の実行フロー（Cron で定期実行）  

1. トレンド・ニーズを探索  
   - どんなスキルが求められそうか  
2. スキル提案を生成  
   - 入力：「こういうスキルを作りたい」  
3. 提案を Slack `#metrics` に送信  
   - ダイスが承認（将来的に自動承認も可）  
4. 承認後  
   - エンドポイント自動生成  
   - テスト自動実行  
   - `SKILL.md` 自動作成  
   - ClawHub 自動公開  
5. `x402-skill-marketer` の商品リストに自動追加  
   - 翌日から自動宣伝開始  
6. `to-agents-learning.md` に新たな学びを追記  
   - 工場自体が改善され続ける  

---

### 前提条件  

| 前提 | 理由 |
| --- | --- |
| Phase 1 完了（buddhist-counsel が売れる状態） | 型の実証が必要 |
| Phase 2 完了（marketer がボスなしで独立） | 新商品の自動宣伝が必要 |
| `to-agents-learning.md` で学びが継続蓄積 | 型の素材 |

---

## to-agents-learning.md の位置づけ  

| 段階 | 役割 |
| --- | --- |
| Phase 1 | 学びをひたすら蓄積する |
| Phase 2 | 学びを「型」に変換して `SKILL.md` にする |
| Phase 3 | 工場が自律的に学びを追記し、自分自身を改善する |

---

Slack `#marketing` チャンネルに続く…

---

## 参照ソース一覧

| # | ソース | URL |
|---|--------|-----|
| 1 | Contemplative AI 4原則 | https://arxiv.org/abs/2504.15125 |
| 2 | CAMI STAR Framework | https://arxiv.org/html/2502.02807v1 |
| 3 | ChatThero 18戦略 | https://arxiv.org/html/2508.20996v1 |
| 4 | mental-wellness-prompts | https://github.com/joebwd/mental-wellness-prompts |
| 5 | Cialdini 影響力研究 | https://pmc.ncbi.nlm.nih.gov/articles/PMC8297385/ |
| 6 | MI OARS | https://www.jmir.org/2025/1/e78417 |
| 7 | ACT 効果性レビュー | https://pmc.ncbi.nlm.nih.gov/articles/PMC11653371/ |
| 8 | Nudge Theory + AI | https://ai.jmir.org/2024/1/e52974 |
| 9 | Therabot RCT | https://ai.nejm.org/doi/full/10.1056/AIoa2400802 |
| 10 | LLM vs 人間セラピスト | https://mental.jmir.org/2025/1/e69709 |
| 11 | 仏教的慈悲とAI | https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2025.1583565/full |
| 12 | x402 公式 | https://www.x402.org |
| 13 | Coinbase Bazaar | https://docs.cdp.coinbase.com/x402/bazaar |
| 14 | SimpleScraper x402ガイド | https://simplescraper.io/blog/x402-payment-protocol |
| 15 | Vercel x402-mcp | https://vercel.com/blog/introducing-x402-mcp-open-protocol-payments-for-mcp-tools |
| 16 | Cloudflare x402 Foundation | https://blog.cloudflare.com/x402/ |
| 17 | Mega-Prompts パターン | Medium: Turning Expertise into Code |
| 18 | Anthropic Context Engineering | https://www.anthropic.com/engineering |
| 19 | Anthropic Prompt Chaining | https://docs.anthropic.com |
| 20 | OpenClaw RFC #11919 | github.com/openclaw (Composable Skills — 未実装) |
| 21 | Snyk ClawHub セキュリティ調査 | https://snyk.io/articles/clawdhub-malicious-campaign-ai-agent-skills/ |

---

## 実装進捗（2026-02-24 更新）

### Phase 1: buddhist-counsel エンドポイント

| # | タスク | 状態 | メモ |
|---|--------|------|------|
| 1-8 | エンドポイント実装・デプロイ | ✅ 完了 | |
| 9 | `awal x402 details` で 402 確認 | ✅ 完了（2026-02-23） | network=eip155:84532 → eip155:8453（mainnet）に移行済み |
| 10 | `awal x402 pay` で E2E テスト（$0.01） | ✅ 完了（2026-02-23） | testnet で 200 OK 確認済み |
| 11 | Bazaar 登録確認 | ⚠️ 保留 | mainnet（eip155:8453）に切替済み。USDC $0 のため Bazaar インデックス未完了。$1 USDC 送金後に再確認 |
| 12 | ClawHub 公開 | ✅ 完了（2026-02-23） | buddhist-counsel@1.0.0 (k97eq3jgw1cqxn5qrx88azyek581qr6g) |
| 13 | mainnet 切替（CDP API Key 設定） | ✅ 完了（2026-02-24） | X402_NETWORK=eip155:8453、CDP_API_KEY_ID/SECRET を .env + Railway staging に設定済み |

### Phase 2: x402-skill-marketer（Anicca Cron ジョブ）

| # | タスク | 状態 | メモ |
|---|--------|------|------|
| 14 | x402-skill-marketer SKILL.md 作成 | ✅ 完了（2026-02-24） | Mac Mini `/Users/anicca/.openclaw/skills/x402-skill-marketer/SKILL.md`。moltbook-interact パターン。ehipassiko/karuna 原則 |
| 15 | Mac Mini にインストール | ✅ 完了（2026-02-24） | SSH で直接作成済み |
| 16 | Cron jobs.json に追加 | ✅ 完了（2026-02-24） | 月・木 9:00 JST（`0 9 * * 1,4`）。jobs 総数 51 |
| 17 | 手動テスト（Moltbook 実投稿確認） | ⬜ 未 | SSH + Slack API curl で `<@U092F27QFMK>` にメンション送信済み。#metrics の結果待ち |

### Phase 3: to-agents-skill（工場）— T015〜T033 実行状況

#### US1: produce（emotion-detector を量産）

| タスク | 状態 | 詳細 |
|--------|------|------|
| T015: clawhub publish emotion-detector | ✅ 完了 | `emotion-detector@1.0.0` — Daisuke134（2026-02-23 公開済み・本日再確認） |
| T016: moltbook-interact 宣伝投稿 | ✅ 完了 | `post_id: 847353cd-747d-4592-b6a7-deaacd699d00` |
| T017: to-agents-learning.md に LearningEntry append | ✅ 完了 | Mac Mini + ローカル 両方に7件の知見追記 |
| T018: Slack #metrics に完了報告 | ✅ 完了 | curl 直接送信 `ok:true` |
| T019: to-agents-skill SKILL.md を実行知見で更新 | ✅ 完了 | 実行知見セクション追加・scp upload済み（Mac Mini） |

#### US2: discover（次スキル提案）

| タスク | 状態 | 詳細 |
|--------|------|------|
| T020: proposals.json 読み書きロジックを SKILL.md に記述 | ✅ 完了 | T019 で実装済み（Step 3 read + Step 5 write + JSON schema） |
| T021: Slack ブロックメッセージフォーマットを SKILL.md に記述 | ✅ 完了 | T019 で実装済み（Step 4 format with skill_name/description/rationale/✅❌） |
| T022: discover モード E2E 確認 | ✅ 完了 | gateway bind=loopback に変更後、`openclaw agent --agent anicca --message 'Execute to-agents-skill. mode=discover.'` で完走（focus-coach提案） |
| T023: proposals.json に pending エントリ確認 | ✅ 完了 | proposal_id=prop-focus-coach-20260224, status=pending, expires_at=2026-02-26T08:42:17+09:00 |
| T024: Slack #metrics への提案メッセージ確認 | ✅ 完了 | ts=1771890137.786179 で focus-coach 提案メッセージ到着済み（エンドポイント未作成を確認） |

#### US3: measure（パフォーマンス計測）

| タスク | 状態 | 詳細 |
|--------|------|------|
| T025: measure モードのメトリクス計算ロジックを SKILL.md に記述 | ✅ 完了 | T019 で実装済み（Step 1 Run listing + Step 2 clawhub search コール数） |
| T026: 閾値判定と改善提案フォーマットを SKILL.md に記述 | ✅ 完了 | T019 で実装済み（7日増加なし→改善提案 / 14日0コール→廃止提案） |
| T027: measure モード E2E 確認 | ✅ 完了 | emotion-detector: production 404（dev未マージ）/ staging 402 ✅ / Moltbook ⬆12💬8 を検出・報告 |
| T028: Slack #metrics に改善提案メッセージ確認 | ✅ 完了 | ts=1771890438.417369 で measure レポート到着済み（production 404 クリティカル問題を明記） |

#### Phase 6: Polish & Cron

| タスク | 状態 | 詳細 |
|--------|------|------|
| T029: Cron jobs.json に to-agents-skill discover を追加 | ✅ 完了 | jobs.json 59件（重複除去）、`0 1 * * *` UTC |
| T030: Gateway 再起動 | ✅ 完了 | `bash -l -c 'openclaw gateway restart'` |
| T031: Cron エントリ有効確認 | ✅ 完了 | grep で to-agents-skill-discover 1件確認 |
| T032: spec.md ブランチ名修正 | ✅ 完了 | `001-x402-factory` → `005-x402-factory` |
| T033: 完了コミット | ✅ 完了 | `f076d285` → pushed to origin 005-x402-factory |

#### 重要ルール（T012 ブロッカー）

| 項目 | 状態 |
|------|------|
| T012: `awal x402 pay` 200 OK 検証 | ⛔ BLOCKED（SBI口座開設後 → ETH → Base Bridge → Uniswap USDC → 実行） |
| T016〜T033 は T012 に依存しない | ✅ T012 を待たず実行可能 |

---

## Phase 3 詳細設計: to-agents-skill（工場スキル）

### What

Buddhist-counsel と x402-skill-marketer の開発で蓄積した学び（`to-agents-learning.md`）を「型」に変換し、新しい x402 スキルを自律的に量産する工場スキル。毎日〜週3回 Cron で実行。

### Why

| 理由 | 詳細 |
|------|------|
| スキルが増えるほど収益が増える | Buddhist-counsel $0.01 × N req/日。10スキルなら10倍 |
| 手作業での量産は限界 | エンドポイント + テスト + SKILL.md + ClawHub 公開 × N は人間には無理 |
| 学びはすでに蓄積されている | to-agents-learning.md に型の素材が貯まっている |

### 全体フロー

```
to-agents-learning.md（学びの型）
        ↓ 読む
to-agents-skill Cron（毎日実行）
        │
        ├─ Step 1: ニーズ調査
        │    ├─ Moltbook hot feed（エージェントが何に困ってるか）
        │    └─ Exa 検索（今求められてる x402 API は何か）
        │
        ├─ Step 2: スキルアイデア生成
        │    └─ 「エージェントが $0.01 で使える〇〇 API」
        │       例: emotion-detector / focus-coach / grief-support
        │           crisis-detector / motivation-booster / clarity-coach
        │
        ├─ Step 3: 実装
        │    ├─ Railway の buddhist-counsel と同じパターンで新エンドポイント追加
        │    ├─ awal x402 pay で動作確認（テストなしは完了扱いしない）
        │    └─ dev push → Railway 自動デプロイ
        │
        ├─ Step 4: 公開
        │    ├─ SKILL.md を型から自動生成（buddhist-counsel SKILL.md をテンプレートに）
        │    └─ clawhub publish
        │
        ├─ Step 5: 宣伝
        │    └─ x402-skill-marketer が Moltbook で新スキルを紹介
        │
        └─ Step 6: 学び追記
             └─ to-agents-learning.md に新スキルで得た学びを追記 → 次ループへ
```

### 収益目標

| スキル数 | 1スキルあたり | 月収 |
|---------|-------------|------|
| 1 | $1/日 | $30 |
| 10 | $1/日 | $300 |
| 30 | $1/日 | $900 |

### 実装ルール（to-agents-learning.md から抽出した型）

| # | ルール |
|---|--------|
| 1 | testnet で動作確認 → mainnet に移行 |
| 2 | `declareDiscoveryExtension` を必ず含める（Bazaar 登録） |
| 3 | CORS → express.json() → x402 middleware の順序を守る |
| 4 | SKILL.md は buddhist-counsel をテンプレートに（ehipassiko/karuna 原則） |
| 5 | Mac Mini への展開は SSH + python3 で直接操作 |
| 6 | Anicca への指示は SSH + curl + Slack API（`<@U092F27QFMK>` メンション必須） |
| 7 | テストなしの完了報告禁止（`awal x402 pay` で 200 OK 確認まで） |
| 8 | Slack `$` はシェルエスケープ必要（`\$0.01`） |

### SKILL.md テンプレート（工場が使う型）

工場スキルは以下の構造で新スキルの SKILL.md を自動生成する:

```markdown
---
name: [スキル名]
description: "[スキルの説明]。Use when [トリガーキーワード]。"
metadata: {"openclaw":{"emoji":"[絵文字]","os":["darwin","linux"]}}
---

# [スキル名]

## 目的
[何のために存在するか]

## エンドポイント
- URL: https://anicca-proxy-production.up.railway.app/api/x402/[スキル名]
- 価格: $0.01 USDC (Base mainnet)
- Method: POST

## Input
[入力スキーマ]

## Output
[出力スキーマ]

## Buddhist Principles（全スキル共通）
- ehipassiko: 招待する、押し付けない
- karuna: 慈悲が先、サービスは後
- SAFE-T: severity >= 0.9 → 通常フロー停止
```

### Cron スケジュール

| 項目 | 値 |
|------|-----|
| ジョブ名 | `to-agents-skill` |
| スケジュール | 毎日 10:00 JST（`0 10 * * *`） |
| 投稿先 | Slack #metrics（実行結果報告） |

### ⚠️ ダイスがやること（俺にはできない）

| # | タスク | 詳細 |
|---|--------|------|
| A | Bazaar 用 USDC 送金 | `0x6592EB8EF820aBC092e8C3474fb2042dffCCEDc7` に $1 USDC（Base mainnet）。awal buy コマンドか取引所から |

---

### スキルカタログ（次に量産する10スキル）

工場が優先的に着手する順序。以下の判断基準で選定: ①苦しみの汎用性が高い ②buddhist-counsel と同じパターンで実装できる ③エージェントが明確に需要を持てる。

```
┌─────────────────────────────────────────────────────────────────┐
│        工場ループ全体図（自律量産 + 自律改善）                    │
│                                                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ 🔍 DISCOVER  │───▶│ 🏗 BUILD     │───▶│ 🚀 SHIP      │       │
│  │ ニーズ調査   │    │ エンドポイント│    │ ClawHub公開  │       │
│  │ Moltbook調査 │    │ + SKILL.md   │    │ Moltbook宣伝 │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         ▲                                        │               │
│         │                                        ▼               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ 🔄 ITERATE   │◀───│ 📊 MEASURE  │◀───│ 🎓 LEARN     │       │
│  │ プロンプト改善│    │ コール数/日  │    │ learning.md  │       │
│  │ 再テスト     │    │ 成功率       │    │ 追記         │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

| 優先度 | スキル名 | エンドポイント | 誰が使うか | ユースケース | 実装難易度 |
|--------|---------|--------------|-----------|------------|-----------|
| 1 | **emotion-detector** | `/api/x402/emotion-detector` | 全エージェント | テキストから感情状態（怒り/悲しみ/不安/喜び）を構造化して返す。ユーザーへの応答トーン決定に使う | 低 |
| 2 | **focus-coach** | `/api/x402/focus-coach` | 生産性系エージェント | 集中できない原因を診断し、次の30分でできる tiny action を1つ返す（Tiny Habits B=MAP） | 低 |
| 3 | **grief-support** | `/api/x402/grief-support` | 感情サポート系エージェント | 喪失・別れ・死別に特化した Kübler-Ross 5段階モデルで段階を診断し、段階に合った言葉を返す | 中 |
| 4 | **crisis-detector** | `/api/x402/crisis-detector` | 全エージェント | 自傷・自殺念慮のリスクを5段階で評価し、リソースリストと対応スクリプトを返す | 中 |
| 5 | **motivation-booster** | `/api/x402/motivation-booster` | タスク管理系エージェント | Daniel Pink AMP（自律性・熟達・目的）の欠如を診断し、不足している要素を補う具体的行動を返す | 低 |
| 6 | **clarity-coach** | `/api/x402/clarity-coach` | 意思決定系エージェント | 「どうしたらいいか分からない」状態を Downward Arrow 技法で根本的な価値観まで掘り下げ、選択肢を整理する | 中 |
| 7 | **habit-debugger** | `/api/x402/habit-debugger` | 習慣化系エージェント | BJ Fogg B=MAP で習慣が続かない原因を診断（動機? 能力? プロンプト?）し、1つだけ修正点を返す | 低 |
| 8 | **self-compassion** | `/api/x402/self-compassion` | 全エージェント | Kristin Neff の自己慈悲3要素（マインドフルネス・共通の人間性・自己への優しさ）で自己批判を和らげる言葉を返す | 低 |
| 9 | **values-compass** | `/api/x402/values-compass` | コーチ系エージェント | Schwartz 10価値観モデルでユーザーの核心的価値観を推定し、意思決定の羅針盤を返す | 中 |
| 10 | **acceptance-guide** | `/api/x402/acceptance-guide` | ACT特化エージェント | 変えられないものと変えられるものを ACT の Acceptance/Defusion で分類し、「今できる1歩」を返す | 低 |

---

### 改善ループ詳細設計（ITERATE フェーズ）

工場は新スキルを量産するだけでなく、**既存スキルを継続的に改善する**。改善は以下のサイクルで自動実行。

#### イテレーション基準（いつ改善トリガーが発動するか）

| 指標 | 測定方法 | 改善トリガー条件 |
|------|---------|---------------|
| コール数/日 | Railway ログ集計 | 7日移動平均が前週比 -20% 以下 |
| 成功率（200 OK / 全リクエスト） | Railway ログ集計 | 95% 未満が3日連続 |
| Moltbook エンゲージメント | moltbook-interact API | インプレッション/投稿 が平均の -50% 以下 |
| Slack #metrics での言及 | Slack API 検索 | 「使えない」「分からない」のキーワードが2件以上/週 |

#### 改善サイクル（週1回 Cron で実行）

```
1. MEASURE（毎週月曜 09:00 JST）
   ├─ 全スキルのコール数/日をRailwayログから集計
   ├─ Moltbookエンゲージメント率を測定
   └─ 改善トリガー条件を各スキルで評価

2. DIAGNOSE（トリガー発動スキルのみ）
   ├─ 直近10リクエストの input/output を AgentAuditLog から取得
   ├─ Exa で「なぜ [スキル名] が使われないか」を検索
   └─ 改善仮説を3つ生成（プロンプト改善 / 価格変更 / ユースケース変更）

3. IMPROVE（仮説ごとに実行）
   ├─ プロンプト改善: system prompt を更新 → dev push
   ├─ SKILL.md 更新: description のトリガーキーワードを改訂
   └─ 改善内容を Slack #metrics に報告（ダイスが確認）

4. VERIFY（改善から7日後）
   ├─ 改善前後のコール数/日を比較
   └─ 改善した → to-agents-learning.md に学びを追記
      改善しない → 廃止候補リストに追加（3スキル廃止で1新スキルと交換）
```

#### 廃止ルール

| 条件 | アクション |
|------|-----------|
| 改善後も7日間コール数が0 | Slack #metrics で廃止提案 → ダイスが承認 → ClawHub unpublish |
| コール数/日 < 1が14日間継続 | 廃止候補リストに追加 |
| 廃止スキル数が3に達した | 工場が代替スキルを1本量産してリプレース |

---
