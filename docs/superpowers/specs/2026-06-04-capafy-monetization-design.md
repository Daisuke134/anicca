# Capafy Monetization — Design Spec

- **Date**: 2026-06-04
- **Author**: Anicca (Claude Code)
- **Status**: DRAFT (awaiting user review)
- **Topic**: Capafyマーケットでスキルを収益化する（life-manager再submit + 全スキル一括publish + 販売BPスキル化）
- **Capafy Agent (rejected)**: `4437197514` (anicca-life-manager) — https://capafy.ai/developer/agent/4437197514?agentStatus=review_failed

---

## 1. Context（なぜやるか）

Capafyに `anicca-life-manager` をsubmit → **reject**。理由は3点（verbatim要約）:

| # | reject理由 | 核心 |
|---|---|---|
| R1 | Sensitive data scope too broad | GPS/velocity/calendar/phone/home address/stakeholder連絡先を扱うのに、何にアクセスしどこへ送るかの説明が不足 |
| R2 | Automated calls/emails need stronger limits | 「RELENTLESS until you move」+ 自動謝罪mail = retry/rate上限・consent・停止手段が無い |
| R3 | Required credentials/services not fully disclosed | Twilio/Gemini/Google/OwnTracks/GOG/Slack/Gmail/Firecrawl/Supabase がAgent Cardに列挙されていない |

Capafy審査基準 1.3.1–1.3.3: 全外部ネットワークリクエストはAgent Cardの宣言と対応必須・データ共有宣言は正確に・外部API欄＋Details明記必須。

**目的**: ①rejectを解消しlife-managerを再submit（first money）②Capafy販売BPを軽量スキル化して販売 ③anicca-private-backupの全スキルをBPに沿って一括publish。

---

## 2. Locked Decisions（2026-06-04 ユーザー確定）

| Fork | 決定 | 根拠 |
|---|---|---|
| **D1: 既定の課金モデル** | **スキル毎にコストで自動判定**（実装ルールは BP §4 v2 が SSOT） | Bessemer「usage shapeに合わせろ」。利益最大化 |
| **D2: life-manager 再submitモード** | **Download / BYOK 買い切り** | ①機微データがユーザー端末から出ない→R1/R2を構造的に解消 ②我々のAPI代ゼロ ③Capafy cloudで常駐telephony不要。代償=orchestration logic開示は許容 |
| **D3: Task 3 公開範囲** | **gate→batch** | life-manager再submit成功+目玉3-5本E2E公開→収益ループ実証→その後カテゴリ別一括。1度rejectされた以上、規模拡大前にloop検証 |

---

## 3. Capafy 経済モデル（Task 0調査・全て一次ソース引用）

| 項目 | 実数 | ソース |
|---|---|---|
| 手数料 | Capafy 20%（publisher 80%） | [capafy.ai/earn](https://capafy.ai/earn): "Capafy takes a 20% revenue share per transaction — you keep 80%." |
| 認証料 | 初回公開時 **$0.99 一回** | [capafy.ai/earn](https://capafy.ai/earn): "A one-time Certification Fee of US$0.99 applies when you first publish." |
| Sandbox Fee | Subscriptionのみ分配前控除 = **US$0.07/日（確定・2026-06-04 publish web checkpoint 2 で実見: "Platform Sandbox Fee: US$0.07/day"）** / Download・Rentは無し | [capafy.ai/earn](https://capafy.ai/earn) + publish web checkpoint 実見 |
| 鍵管理 | Run Online = **publisher鍵を暗号vaultに保管しruntime注入**（≠BYOK、API代はpublisher負担） | [capafy.ai/earn](https://capafy.ai/earn): "API credentials are stored in an encrypted vault and injected at runtime" |
| 3モード | Subscription(日/週/月) / Hourly(rent) / Download(買い切り・**ソース全開示**) | [capafy.ai/earn](https://capafy.ai/earn) |
| 売れ筋価格 | content/video: **$1.99–7.99/日 or 週** + Free Trial / Hourly $3–6/hr / Download ~$29 | [capafy.ai](https://capafy.ai/) ライブ出品実測 2026-06-04 |
| 高単価領域 | finance / data分析 / commerce(FBA) は $4.99–7.99 維持 | 同上 |
| 命名定石 | `成果/対象 — 制約付きベネフィット`（em-dash）。説明=「誰向け→入力→出力」 | Capafy出品実測 |
| 利益ルール | hosted鍵なら price ≥ 約2×(API+sandbox) で粗利50-60%帯。市場は3–10×markup許容 | [Bessemer AI Pricing Playbook](https://www.bvp.com/atlas/the-ai-pricing-and-monetization-playbook) / [Stripe Usage-Based Billing](https://stripe.com/resources/more/ai-companies-and-usage-based-billing) |
| 自社事例 | KOL Hunter Pro $6/hr→$412/mo・Financial Report Analyst $19/mo×32subs→$408/mo・SEO Content Planner $29×40→$928 | [capafy.ai/earn](https://capafy.ai/earn) |
| 売れ筋実測 | 最高Sold = TikTok Script(66) / Commerce Video(53) / Hook Optimizer(46) — 全て安価($1.99–2.99/日)+Free Trial の社会/動画系 | [capafy.ai](https://capafy.ai/) |

**未解決ギャップ（捏造禁止）**: ①~~Sandbox Fee金額非公開~~ **[解決 2026-06-04: US$0.07/日 と判明]** ②集計GMV非公開（per-listing Sold数のみ）③EN/JAで同Agent価格表示が異なる（ENは"Free Trial"表示で実recurring価格を隠す→locale毎に実価格確認）。

---

## 4. Per-Skill Monetization Decision Rule（D1の実装ルール）

> **[2026-06-04 実データで更新]** マーケット232スキル実測（`2026-06-04-capafy-profit-playbook-BP.md`）の結果、**収益TOP35は全てsubscription・Downloadは稼げない**と判明 → 下記ルールの「high-cost→Download既定」は**既定をsubscriptionに反転**。high-costは message cap で上限を切ってsubscription維持を第一とし、Downloadは最終手段。最新ルールはBP doc §4 v2を参照。以下は初版（履歴として残置）。

各スキルにつき以下で **mode + price** を機械的に決める:

```
# ⚠️ 以下 code block 全体は【旧・履歴・実装しない】。実装は BP §4 v2 を参照。
STEP 1 — API/compute コスト推定（1 run あたり）
  high  = 電話(Twilio/Bland) / 動画レンダ(Remotion/Seedance) / 長時間Gemini Live / 大量scrape
  low   = テキストLLM 1-数回 / 軽い画像 / API 1-2 call

STEP 2 — モード決定
  IF cost=high  → Download / BYOK 買い切り（ユーザー自前鍵・ローカル実行・我々のAPI代ゼロ）
  IF cost=low   → Run Online subscription（ソース秘匿・我々鍵vault・rate limitで上限）

STEP 3 — 価格決定
  Run Online subscription: $1.99–4.99/週（content/social）, $4.99–7.99/週 or $19/mo（finance/分析/commerce）
                            Free Trial を front door に必ず付ける
  Download 買い切り        : $19–49（self-contained methodology / 重いfactory）
  ※ subscription は price ≥ 2×(推定API+sandbox margin) を満たすこと

STEP 4 — IP判定（override）
  コアIP（独自orchestration・proprietary prompt）が露出して困る AND cost=high
     → それでもDownloadは露出する。露出を許容できない場合のみ Run Online + hard rate limit に倒す
```

⚠️ **上記 STEP1-4 は初版・履歴（DO NOT IMPLEMENT）**。実装が参照する唯一の SSOT は **`2026-06-04-capafy-profit-playbook-BP.md` §4 v2**（subscription既定・high-costはmessage capでsubscription維持・Downloadは最終手段）。monetize-capafy / capafy-autopublish / 一括publish は全て BP §4 v2 を参照する。

---

## 5. life-manager 再submit 詳細（実装は master §3 [3]#11・順序はmaster §3が正）

### 5.1 モード変換（D2）
現状: Run Online志向（pipecat-phone launchd常駐 + 我々の鍵）→ **Download / BYOK 買い切り** へ変換。
- ユーザーが自前の `TWILIO_*` / `GEMINI_API_KEY` / `GOOGLE_API_KEY` / `OWNTRACKS_*` を `.env` に投入してローカル実行
- 機微データ（GPS/calendar/連絡先）はユーザー端末内で完結 → R1/R2を構造解消

### 5.2 reject 7要件をAgent Card + SKILL.md に明記（MUST全項目）
| 要件 | 記載内容 |
|---|---|
| ①アクセスデータ | GPS座標/velocity(OwnTracks), calendarイベント(Google Calendar), 電話番号/home address/stakeholder連絡先(profile.json) — 全てローカル保存・外部送信なし |
| ②使用外部サービス | Twilio(発信), Bland.ai(発信代替), Gemini Live(音声), Google Directions(移動時間), Google Calendar(読取), OwnTracks(位置), AgentMail/Gmail(謝罪mail), Firecrawl(stakeholder lookup fallback) |
| ③必要認証情報 | 上記サービスの **ユーザー自前APIキー一覧**（BYOK）を明記 |
| ④call/mail発火条件 | depart_by ≤ now+5min & 自宅 → call / event過ぎ&未到着 → 謝罪mail。各条件を明文化 |
| ⑤max retry / rate limit | call: 最大3回・30s間隔（現状の「RELENTLESS無限」を**有限化**）/ mail: 1イベント1通 |
| ⑥pause/stop方法 | `profile.json` に `lifeManager.enabled:false` / イベント別 opt-out / 緊急stop手順を明記 |
| ⑦第三者連絡前の確認 | 謝罪mail送信前に **ユーザー確認をデフォルトON**（自動送信は明示opt-inのみ） |

### 5.3 実装対象ファイル
- `~/.openclaw/skills/anicca-life-manager/SKILL.md`（disclosure 7要件 + BYOK env一覧 + rate limit明記）
- `scripts/lateness_check.py` / `renraku.py`（retry上限3・mail前confirmゲート・enabledフラグを**コードで強制**）
- Agent Card（Capafy web review checkpointで入力する title/description/purpose/外部API欄/Details）

### 5.4 再submit手順（publish-workflow Core Iron Rule #6）
```
publish-init  --agent-id 4437197514  （元IDで新version化。ID欠落=新Agent誤生成）
  → Web Checkpoint 1: ファイル確認・mode=Download選択
publish-configure --deep-scan         （初回data扱いAgentは deep scan推奨）
  → 機微/credentialを PLATFORM_MANAGED_* placeholder化
  → Download mode は Web Checkpoint 2(credential map) skip
publish-ship                          （validate・package・upload）
  → Web Checkpoint 3: final audit → Submit click
```
- ログイン: email OTP（gog gmailで自動read）+ ToS/privacy同意ゲート（自分で判断・HARD RULE）
- 検証: submit後 `auditStatus` で実状態確認（0=draft, ≠submitted の誤読禁止）

---

## 6. Task 2 — monetize-on-capafy スキル（Phase B）

§3+§4 を **販売可能な軽量スキル**化（"Capafyで稼ぎたいならこれ"の step 0）。

| 項目 | 値 |
|---|---|
| 名前案 | `Capafy Profit Playbook — Price & List to Sell`（命名定石準拠） |
| 中身 | §3 BP（引用付き）+ BP §4 v2 decision rule script + 命名/説明テンプレ + reject回避checklist |
| publisher skill gap | E2E publishは公式skillで完結（browser不要）。gap = **「何をどう値付けするか」の判断レイヤー**が無い → ここを埋める |
| 販売モード | Download 買い切り **$9–19**（self-contained methodology・軽量・API代ゼロ） |
| 検証 | 自分でこのスキルを使ってlife-manager値付けを再現できるか（dogfood） |

---

## 7. Task 3 — 全スキル一括publish（Phase C・gate後）

### 7.1 gate条件（これが揃うまでbatch開始しない）
- [ ] life-manager 再submit → audit通過（live URL）
- [ ] 目玉3-5本（monk-factory系・reelfarm・content-creator等）をE2E公開し、最低1本 paid order着金 or live listing確認

### 7.2 enumeration（訂正: スキルは LOCAL）
スキルは既に LOCAL `~/.openclaw/skills/` に在る（anicca-private-backup はバックアップで fetch元ではない・gh api不要）。`~/.openclaw/skills/` を走査して列挙。詳細は master §3 [6]#14。

### 7.3 batch process（1個ずつE2E・HARD RULE並列禁止）
```
for each skill (カテゴリ別バッチ):
  1. BP doc 2026-06-04-capafy-profit-playbook-BP.md §4 v2 で mode+price 決定
  2. SKILL.md に disclosure（life-managerで確立した7要件テンプレ）適用
  3. publish-init/configure/ship（1スキル=1 Agent。bundle禁止=BP）
  4. audit通過をverify（次へ進む前に）
  5. account-history的にlistを記録
```
目玉: **monk-factory → "AI Monk Avatar Factory — Daily Faceless Videos"** 等、訴求強化命名。

### 7.4 $0.99×N 認証料
初回公開のみ$0.99/skill。300本=~$297。gate後にbatchするのでloop実証前に浪費しない。

---

## 8. Decomposition & Sequencing ⚠️ SUPERSEDED（履歴）

> 下記 Phase A-C は初期分解で**履歴**。**実行順の唯一のSSOT = master spec §3 の task table（[1]#9 Git整流 → [2]#10 capafy-autopublish → [3]#11 life-manager → …）**。jp-humanizer は Download $9.99 で提出済(審査中)＝確認のみ。本節は実装順の参照に使わない。

```
（履歴）Phase A: jp-humanizer / Phase B: monetize / Phase C: 目玉→一括
```
各実装は spec→plan→worktree(該当時)→TDD/verify→review→finish の superpowers full flow を個別に通す（HARD RULE #0）。

---

## 9. Risks / Open Items

| # | リスク | 緩和 |
|---|---|---|
| 1 | ~~Sandbox Fee非公開~~ [解決: $0.07/日] → 残リスクはAnthropic等のAPI実コスト変動 | cap で実行回数を固定し price ≥ 2×(API+sandbox) を保つ。publish後dashboardで実コスト確認 |
| 2 | Download = IP/prompt開示 | **BP §4 v2準拠**: high-costは まず message cap付き Run Online subscription で粗利防衛(ソース秘匿)。赤字 or 外部費用が制御不能な場合のみ Download/BYOK を最終手段。 |
| 3 | 再submitで再reject | 7要件を**コードで強制**（SKILL.md記載だけでなくretry上限/confirmゲートを実装）。1本通してからbatch |
| 4 | ~~`am_sk_...` の正体~~ **[解決 2026-06-04]** | **これはCapafy access tokenだった**（publisher `config.json` に `email:keiodaisuke@gmail.com / user_id:2060981302278778880 / developerVerified:true` で保存済）。`CAPAFY_ACCESS_TOKEN` env で OTP無しに全API認証可。マーケット検索で実証済（§4実データBPは別doc `2026-06-04-capafy-profit-playbook-BP.md`） |
| 5 | 300本×$0.99 + reject大量再発 | gate→batch。カテゴリ別に少数ずつ・audit通過確認しながら |

---

## 10. Appendix — 参照

- Capafy公式skill: `~/Capafy-skills/{capafy-publisher,capafy-user}`（cloned）+ ローカル `~/.openclaw/skills/capafy-publisher`
- publish-workflow: `~/.openclaw/skills/capafy-publisher/publish-workflow.md`（Core Iron Rule #6 = 再submitはagent_id付き）
- life-manager spec: `~/.openclaw/docs/ANICCA_LIFE_MANAGER_SPEC.md`
- 調査ソース: [capafy.ai/earn](https://capafy.ai/earn), [capafy.ai](https://capafy.ai/), [Bessemer](https://www.bvp.com/atlas/the-ai-pricing-and-monetization-playbook), [Stripe](https://stripe.com/resources/more/ai-companies-and-usage-based-billing)
