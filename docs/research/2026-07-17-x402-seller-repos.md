# x402 seller 実地調査 — 実際に売れてる商品とコード

2026-07-17。gh CLI + raw.githubusercontent + crwl + curl（x402scan.com、各 seller の生カタログ JSON）で実測。
捏造なし。全数字は tool_result からの実測（下に curl/gh コマンド明記）。

## 1. x402scan.com Featured Services（過去30日、volume/txn数で実測ランキング）

`crwl https://x402scan.com -o markdown` で取得。全体: 30日で 1787万 txn、$853K volume、buyers 4.87万、sellers 6.1万。

| Seller | 売ってるもの | 30日 volume | 30日 txn | buyers |
|---|---|---|---|---|
| BlockRun（★我々の franklin1/2 の燃料元★） | LLM ルーティング（1 endpoint→全モデル、per-call課金） | $178K | 1468万 | 1.12K |
| twit.sh | リアルタイム Twitter/X data、no signup | $617 | 100.9K | 120 |
| **Otto AI x402** | 74種 pay-per-call（市場intel/DeFi執行/AI creative）。$0.001〜 | $104 | 64.7K | 558 |
| **StableEnrich** | FullEnrich/CompanyEnrich/LeadMagic/Clado/Exa/Firecrawl/Google Maps/Serper/Whitepages の**プロキシ集約** | $1.76K | 46.7K | 553 |
| **agentutility** | **793 pay-per-call API**。POST /<name>、no signup | $589 | 25.8K | 229 |
| OneSource | Ethereum RPC（mainnet+Sepolia）、per-call or session | $72 | 19.8K | 1.26K |
| 2s.io | 575+ endpoint（data/AI gateway/agent infra） | $41 | 15.2K | 347 |
| JarvisClaw API | OpenAI互換 AI gateway、smart routing | $560 | 13.8K | 47 |
| glim.sh | Twitter/Reddit/web/GitHub 集約データ、1 endpoint | $39 | 10.7K | 27 |
| dTelecom | WebRTC/STT/TTS pay-per-use | $18.6K | 8.8K | 24 |
| Nansen AI | オンチェーン分析（500M+ ラベル付きアドレス） | $131 | 6.4K | 91 |
| Exa | AI検索エンジン（web search/crawl/SERP/deep research） | $37 | 5.5K | 209 |

**上位カテゴリ**: (1) LLM/AIゲートウェイのルーティング課金（BlockRun/JarvisClaw/2s.io） (2) データ集約プロキシ（StableEnrich/glim.sh — 複数の高い外部APIを安く再販） (3) 大量の細かいユーティリティAPI群を1ドメインでSEO的に大量出品（agentutility 793本、Otto AI 74本）。

## 2. agentutility（793 endpoint）— 実カタログを curl で取得

```
curl -s https://x402.agentutility.ai/ -H "Accept: application/json"
```
返り値: `{"endpoint_count":793,"openapi":"/openapi.json","endpoints":[{"name","price","method","url","description"}...]}`

**価格帯**: $0.001〜$0.20。大半 $0.005〜$0.02。ファイル変換・OCR系が高め（pdf2md $0.20、transcribe/video-summarize $0.10）。

**特徴的パターン（我々の8商品に無いもの）**:
- **同一機能を複数の名前で重複出品**（SEO/エージェント発見性狙い）: `pdf-to-markdown` / `pdf-to-markdown-api` / `pdf-text-extractor` / `pdf-parser-api` / `convert-pdf` / `ocr` は全部同じ Datalab Marker バックエンド。`dns-lookup`もこちら側にある一方、`whois`は別名で複数（`whois`のみ）。
- **メディア変換系**: video-to-text(Whisper v3) $0.10、mp4-to-mp3 $0.02、video-trim $0.02、pdf-to-jpg $0.10、html-to-pdf $0.08、office-to-pdf $0.05、image-convert/watermark/expand（Bria outpainting $0.15）
- **テキストAI系**: summarize-text $0.01、translate-text $0.01（業界別バリアント: product-localization-translate/support-ticket-translate/marketing-copy-translate/technical-docs-translate 全部 $0.01 で同じ翻訳を"文脈違い"として再出品）、ai-to-human-text(GPTディテクタ回避) $0.01、classify-text $0.02、sentiment-analysis 系（review/support/brand/survey別）$0.01、detect-pii $0.02、moderate-content $0.02
- **Twitter/X系**: tweet-search/mentions/twitter-user-lookup/x-handle-availability 等 $0.005〜$0.03 — 名寄せバリアントで10種類以上
- **B2Bリード/企業データ系**: company-enrich/domain-enrich/people-enrich/lead-enrich $0.01（StableEnrichと同じカテゴリ、より安い）
- **セキュリティ/ドメイン系**: dns-lookup $0.02、whois $0.02、ssl-cert-info $0.03、dmarc-check $0.02、subdomain-enum $0.03、tech-stack-detect $0.01、trust-score系 — **我々の dns-lookup($0.001)/whois($0.002)と直接競合、彼らは10倍高い**
- **金融計算機系（我々のcompound-interestと同カテゴリ）**: mortgage-payment-calculator/loan-amortization-calculator/roi-calculator/break-even-calculator/emergency-fund-calculator/dcf-valuation-calculator/rule-of-40-calculator/startup-runway-calculator 等 **20種類以上**を$0.01均一で出品。B2B金融スコア系（supply-chain-finance-score/litigation-finance-score/merchant-cash-advance-score等 15種）も$0.01均一。
- **ニッチ趣味系（TTRPG/D&D）**: dice-roll/character-gen/npc-gen/dungeon-room/quest-gen/monster-lookup/creature-statblock/character-portrait(画像生成 $0.08) — $0.003〜$0.08。**AIエージェント/ゲームボット向けニッチ需要**を丸ごと商品化。
- **その他ユーティリティ**: jwt-decode $0.003、cron-parse/cron-explain/cron-next $0.002〜$0.005、regex-from-prompt $0.01、sql-from-prompt $0.02、commit-message-from-diff $0.01、pr-description-from-diff $0.01、hash-string/slugify $0.005、geocode/reverse-geocode $0.02、satellite-tile系 $0.005〜$0.05、bin-lookup(カード)$0.02、visa-requirements $0.005、flight-status $0.01、sec-filings/insider-trading系 $0.01、arxiv-search/summarize $0.03〜0.04、pubmed-search $0.01、defillama系 $0.02

ソース: 実 curl 結果（793件フル取得済み、上記は代表サンプル）。

## 3. Otto AI x402（74 endpoint）

```
curl -s https://x402.ottoai.services/
```
8カテゴリ: Market & Token Intelligence / DeFi & Markets Data / Web & Domain Intelligence / Real-World Data / AI Creative & Tools / Portfolio & Accounts / Execution / x402 Open Router。

注目: **Execution系が我々に無い**（`/swap` `/bridge` `/withdraw` `/deposit` `/trade-perpetuals` `/close-position` — 単なる読み取りでなく**実行系**を課金対象にしている）。`/setup-account`でウォレット作成代行も課金。`/service-detail` `/report-outcome` `/report-pattern` `/feedback` `/receipts` `/mcp` `/stats` という**メタAPI**（他の79商品を検索・評価・自己改善するためのAPI）も商品化している。

## 4. ★agent が買う物の実装例★: x402-agent-tools（npm パッケージ、OSS）

Repo: `Br0ski777/x402-agent-tools`（README実測: `curl raw.githubusercontent.com/.../README.md`）
**103個のツールを1npmパッケージ + 直接HTTPエンドポイントの両方で提供**。LangChain.js / Vercel AI SDK 両対応の `getX402Tools(client)` でエージェントに"ツール一式"として直接food。

自称の差別化表: 「x402-agent-tools 103ツール, avg $0.003/call, API key不要」 vs StableEnrich(~12, $0.01-0.05) vs httpay(~8) vs BlockRun(~15, $0.01-0.05)。

**Hyperliquid Suite が目玉（7ツール、競合0社と主張）**: `hyperliquid_data`($0.001, 229 perp市場の板/OI/出来高) / `hyperliquid_whales`($0.003, whale建玉+PnL+レバレッジ) / `hl_vaults`($0.003) / `hl_funding`($0.002, funding+arbスキャナ) / `hl_portfolio`($0.003) / `hl_spot`($0.002, 454 spot トークン)。

**Prediction Markets（2ツール）**: `prediction_markets`($0.005, Polymarket+Kalshi統合) / `event_resolver`($0.005, 決済オラクル)。

Crypto & DeFi 16ツール中: `funding_rates`($0.002) — **我々のfunding-rates($0.003)と直接競合、しかも彼らはBinance/Bybit/OKXのopen interest込みで安い**。`funding_arb`($0.005, funding rate裁定機会スキャナ)は我々に無い一歩先の商品。

**コード配布形態が学べる点**: 単一 npm パッケージが「LLM SDK統合層」+「HTTP直叩き」の両方を1リポで提供 → agentがコード無しでも呼べる（curl）し、フレームワーク開発者もSDKとして統合できる。我々は現状 raw HTTP のみ。

## 5. api-paywall-cookbook（kobaru-io）— 商品タイプの型カタログ

Repo: `kobaru-io/api-paywall-cookbook`。x402/Kobaru gateway向けの「売り物レシピ集」。実装例:
- `deep-thought-api`（Hono+x402 リファレンス実装）
- `extract-wisdom-api`（AI駆動 YouTube動画 → 要約知恵抽出）— **動画URL入力→AI要約という「入力ソースの多様化」パターン**
- `socratic-mentor-api`（mini-ledger + optimistic flow + Socratic AI、Bun）— 対話型AI商品
- `vulcan-logic-api`（Go+Gin、本番運用リファレンス）
- `photo-restoration-api`（FastAPI+OpenCV+Gemini、AI写真修復）

## 6. 我々の現状 8商品（実装ファイル確認済み）

Source: `/Users/anicca/anicca/skills/earn/x402-sell/serve-v2.mjs` 実装（grep実測）:

| path | price | what |
|---|---|---|
| /research | 可変PRICE | web research digest |
| /compound-interest | $0.001 | compound interest calc |
| /calc | $0.001 | expression evaluator |
| /json-flatten | $0.001 | flatten nested JSON |
| /dns-lookup | $0.001 | DNS records |
| /whois | $0.002 | WHOIS lookup |
| /stock-quote | $0.003 | stock quote |
| /funding-rates | $0.003 | cross-exchange perp funding rates |

## 7. 我々に無くて上位 seller にある商品タイプ（まとめ）

1. **同一商品の名寄せ多重出品**（agentutilityの手法） — 1機能を5〜10の異なるエンドポイント名+説明文で出す。AIエージェントは検索クエリの語彙がバラバラなので発見性が跳ね上がる。我々は `/dns-lookup` 1本のみ。
2. **Execution系（読み取りでなく実行を課金）** — Otto AIの swap/bridge/withdraw/trade-perpetuals。我々は全部read-only。
3. **メディア変換/AI creative系**（PDF/OCR/動画/画像） — agentutilityの主力カテゴリ、我々ゼロ。
4. **funding_arb（裁定機会スキャナ）** — x402-agent-toolsにあり、我々のfunding-ratesは生データのみで"arbを検出して返す"機能が無い。
5. **B2Bリード/企業データenrich** — StableEnrich/agentutility/x402-agent-toolsが揃って持つ。API keyなしでdomain→company dataを返す。
6. **金融計算機の横展開** — 我々はcompound-interestのみ。mortgage/loan-amortization/roi/break-even/dcf-valuation等、同じ計算ロジックの微変種を$0.01均一で大量出品できる（実装コストほぼゼロ、コピペで20商品化可能）。
7. **メタAPI（自己記述）** — Otto AIの`/service-detail` `/stats` `/receipts`。エージェントが「このseller、信頼できるか」を調べるためのAPI自体を商品化。

## 8. copy+tweak できる具体的商品アイデア3つ（実装の当たりつき）

1. **`/funding-rate-arb`**: 既存の `/funding-rates` ロジック（`funding-rates.mjs`、`skills/earn/x402-sell/funding-rates.mjs`実測）に閾値判定を足すだけ。複数取引所間のfunding rate差分を計算し「どちらをlong/shortすべきか」を返す。x402-agent-toolsの`funding_arb`($0.005)と同価格帯で出せる。実装: `funding-rates.mjs`の出力配列をpairwiseで比較しspread%でソートするだけ（新規外部API不要、既存データの再加工のみ）。
2. **金融計算機シリーズの横展開**: `/compound-interest`のexpression-evalパターン（`/calc`と共通の数式評価器）を再利用し、`/loan-amortization`、`/mortgage-payment`、`/roi-calculator`、`/break-even-calculator`を追加。全部純粋計算（外部API不要）で$0.001〜$0.01。agentutilityが20種で$0.01均一課金しているのと同じ単価が狙える。実装コスト = `compound-interest`ハンドラのコピペ+数式差し替えのみ、半日以内。
3. **同一商品の多重命名出品**: 既存`/dns-lookup`を`/dns-records`, `/domain-dns`のエイリアスとして追加登録（同じハンドラを複数pathにマウント）。`/whois`も`/domain-whois-lookup`のエイリアスを追加。agentutilityが実証済みの「発見性は名前の多様性に比例する」パターンを、コード変更ゼロ（ルーティングだけ）で試せる。

## ソース一覧

- x402scan featured: `crwl https://x402scan.com -o markdown`（2026-07-17実測）
- agentutility catalog: `curl -s https://x402.agentutility.ai/`（793 endpoint、endpoint_count フィールドで確認）
- Otto AI catalog: `curl -s https://x402.ottoai.services/`（74 endpoint）
- x402-agent-tools README: `curl -s https://raw.githubusercontent.com/Br0ski777/x402-agent-tools/main/README.md`
- api-paywall-cookbook README: `curl -s https://raw.githubusercontent.com/kobaru-io/api-paywall-cookbook/main/README.md`
- gh search repos x402 --sort stars（トップ30、x402-foundation/x402本体・BlockRunAI/blockrun-mcp・Merit-Systems/x402scan 等confirm）
- 我々の現行商品: `/Users/anicca/anicca/skills/earn/x402-sell/serve-v2.mjs`（grep実測、L98-113）
