# Real Mobile App Factory — 完全仕様書

**Date**: 2026-03-02
**Author**: Anicca
**Status**: SPEC（未実装）
**オリジナリティ**: 0%

---

## 0. この仕様書は何か

24/7 で iOS アプリを自律的に「リサーチ→設計→実装→テスト→App Store 提出→TikTok マーケティング→自己改善」するファクトリーの完全仕様。

2つの独立したループで構成:
- **LOOP A（生産）**: アプリを作って売る（内部シングルループ自己改善含む）
- **LOOP B（メタ改善）**: ファクトリー自体のスキルを外部知識で進化させる

---

## 1. アーキテクチャ概要

ソース: [Chris Argyris, Double-Loop Learning (HBR 1977)](https://hbr.org/1977/09/double-loop-learning-in-organizations)
核心の引用: 「シングルループは現在の戦略内でエラーを修正する。ダブルループは戦略そのものを問い直す。この2つは異なるタイムスケールと認知プロセスを要求するため、同一ループに混合してはならない」

ソース: [ICE論文 (arXiv 2401.13996)](https://arxiv.org/abs/2401.13996)
核心の引用: 「プランニング経験と実行経験の混合は、関連知識の同化を妨げ、多様な課題への適応性を阻害する」

```
                    LOOP B（ダブルループ）
                    23:00 毎日
                         │
                         │ SKILL.md 戦略レベル編集 + git push
                         │
                         ▼
                ┌──────────────────┐
                │  改善済みスキル群  │
                │  (git上の正本)    │
                └────────┬─────────┘
                         │
                         │ 翌日 0:00 に読み込み
                         ▼
                    LOOP A（シングルループ）
                    0:00 毎日
                         │
                         │ アプリ生産 + エラー/成功記録
                         ▼
                ┌──────────────────┐
                │  .learnings/      │
                │  本日の全記録      │
                └────────┬─────────┘
                         │
                         │ 翌晩 LOOP B が読み込み
                         ▼
                    LOOP B 再び... ∞
```

### 内部 vs 外部 自己改善の違い

| 観点 | 内部（LOOP A 内シングルループ） | 外部（LOOP B ダブルループ） |
|------|-------------------------------|---------------------------|
| タイムスケール | 秒〜分（実行中リアルタイム） | 日（1日の終わり） |
| 問い | 「この行動は正しかったか？」 | 「そもそもこの戦略は正しいか？」 |
| 例 | ビルドエラー → CRITICAL RULE 追加 | 「ralph loop より良い実行パターンが出た → 採用」 |
| 範囲 | 同じ SKILL.md 内の即時修正 | スキル入れ替え、Phase 再構成、新スキル導入 |
| ソース | 自身の実行エラー/成功のみ | tech-news + OpenClaw marketplace + GitHub + .learnings/ |

ソース: [Voyager (Wang et al. 2023)](https://voyager.minedojo.org/)
核心の引用: 「内部ループ = 実行中の即時修正。外部ループ = スキルをライブラリに永続化して後続タスクで再利用。分離により壊滅的忘却を防ぎながらスキルを複合的に積み上げる」

---

## 2. LOOP A: 生産ループ（毎日 0:00）

### 2.1 トリガー

| 項目 | 値 |
|------|-----|
| cron ジョブ名 | `mobileapp-factory-midnight` |
| 実行時刻 | 毎日 0:00 JST |
| 実行者 | Anicca（OpenClaw Sonnet） |
| 実行場所 | Mac Mini (anicca-mac-mini-1) |

### 2.2 Anicca（オーケストレーター）がやること

```
[0:00] cron 起動 → Anicca (Sonnet) がメッセージ受信
    │
    ├── ① daily-apps/<YYYY-MM-DD>-<app-name>/ フォルダ作成
    ├── ② prd.json 生成（9 User Stories — v3 spec 準拠）
    ├── ③ CLAUDE.md 生成（ralph 用指示書）
    ├── ④ .learnings/ ディレクトリ作成
    ├── ⑤ tmux 内で ralph.sh 起動
    │     │
    │     └── claude --dangerously-skip-permissions --print < CLAUDE.md
    │         × 最大 20 イテレーション
    │         → <promise>COMPLETE</promise> で終了
    │
    ├── ⑥ ralph 完了通知受信（notifyOnExit）
    ├── ⑦ Slack #metrics に完了報告
    └── ⑧ Larry 起動指示（winning-hooks.json 渡す）
```

ソース: [snarktank/ralph](https://github.com/snarktank/ralph)
核心の引用: 「Instead of building complex graphs, agent swarms, or multi-phase planners, he uses just a for/while loop that calls Claude Code on the same project multiple times」

ソース: [OpenClaw Docs - Exec Tool](https://docs.openclaw.ai/tools/exec)
核心の引用: 「tools.exec.notifyOnExit (default: true): when true, backgrounded exec sessions enqueue a system event and request a heartbeat on exit」

### 2.3 ralph.sh 実行内容（9 User Stories）

ソース: [rshankras/claude-code-apple-skills - WORKFLOW.md](https://github.com/rshankras/claude-code-apple-skills/blob/main/skills/product/WORKFLOW.md)
ソース: [ManaLabs App Factory](https://manalabs.wtf/appfactory)
核心の引用: 「A separate reviewer agent independently verifies every file for crash risks, missing features, and code quality — because the model that wrote the code will cut corners reviewing its own work」

#### prd.json

```json
{
  "project": "mobileapp-factory",
  "branchName": "ralph/daily-app",
  "description": "Build and submit one iOS app to App Store",
  "userStories": [
    {
      "id": "US-001",
      "title": "Trend research + idea selection",
      "phase": "Phase 0: IDEA DISCOVERY",
      "skills": ["idea-generator", "tiktok-research", "x-research", "apify-trend-analysis"],
      "acceptanceCriteria": [
        "spec/01-trend.md exists",
        "Contains: rank, idea, one_liner, platform, problem_statement, target_user, feasibility, overall_score, monetization_model, competition_notes, mvp_scope, next_step",
        "At least 5 ideas evaluated, top 1 selected",
        "Sources cited for each trend",
        "Typecheck passes"
      ],
      "priority": 1, "passes": false
    },
    {
      "id": "US-002",
      "title": "Product planning",
      "phase": "Phase 1: PRODUCT PLANNING",
      "skills": ["product-agent"],
      "acceptanceCriteria": [
        "product-plan.md exists",
        "Contains: target user, problem, solution, monetization, MVP scope",
        "monetization section specifies subscription prices (monthly + annual)",
        "All claims cite external sources",
        "Typecheck passes"
      ],
      "priority": 2, "passes": false
    },
    {
      "id": "US-003",
      "title": "Market research",
      "phase": "Phase 2: MARKET RESEARCH",
      "skills": ["competitive-analysis", "market-research"],
      "acceptanceCriteria": [
        "competitive-analysis.md exists with 5+ competitors analyzed",
        "market-research.md exists with TAM/SAM/SOM",
        "Typecheck passes"
      ],
      "priority": 3, "passes": false
    },
    {
      "id": "US-004",
      "title": "Spec generation",
      "phase": "Phase 3: SPECIFICATION GENERATION",
      "skills": ["implementation-spec", "prd-generator", "architecture-spec", "ux-spec", "implementation-guide", "test-spec", "release-spec"],
      "acceptanceCriteria": [
        "docs/PRD.md exists and contains app_name, bundle_id, subscription prices",
        "docs/ARCHITECTURE.md exists",
        "docs/UX_SPEC.md exists and contains Mau 10 onboarding principles",
        "docs/UX_SPEC.md contains soft paywall requirement (RevenueCatUI.PaywallView + Maybe Later)",
        "docs/DESIGN_SYSTEM.md exists",
        "docs/IMPLEMENTATION_GUIDE.md exists and references RevenueCat SDK (not Mock)",
        "docs/TEST_SPEC.md exists",
        "docs/RELEASE_SPEC.md exists",
        "Typecheck passes"
      ],
      "priority": 4, "passes": false
    },
    {
      "id": "US-005",
      "title": "ASC setup + IAP creation + RevenueCat integration",
      "phase": "Phase 6.1-6.6: INFRASTRUCTURE",
      "skills": ["privacy-policy", "asc-signing-setup", "asc-app-create-ui", "asc-subscription-localization", "asc-ppp-pricing"],
      "acceptanceCriteria": [
        "privacy-policy.md exists and deployed to GitHub Pages",
        "App created in ASC (APP_ID recorded in progress.txt)",
        "asc subscriptions groups list --app $APP_ID returns 1+ groups",
        "asc subscriptions list --group $GROUP_ID returns monthly + annual products",
        "RevenueCat dashboard shows 2 products + 1 offering",
        "SPM dependency on RevenueCat + RevenueCatUI added",
        "PrivacyInfo.xcprivacy exists in project",
        "Info.plist contains ITSAppUsesNonExemptEncryption = NO",
        "Typecheck passes"
      ],
      "priority": 5, "passes": false,
      "notes": "ralph dependency order: Schema/infrastructure first. US-006 はこれに依存。"
    },
    {
      "id": "US-006",
      "title": "iOS implementation with real RevenueCat SDK",
      "phase": "Phase 4: IMPLEMENTATION",
      "skills": ["rshankras/generators/*", "swiftui-expert-skill", "ios-simulator-skill", "ios-ux-design", "apple-hig-designer"],
      "acceptanceCriteria": [
        "<AppName>ios/ directory exists with App/, Views/, Models/, Services/, Resources/",
        "xcodebuild -scheme <AppName> build succeeds",
        "grep -r 'Mock' --include='*.swift' . | grep -v 'Tests/' | wc -l = 0",
        "grep -r 'import RevenueCat' --include='*.swift' . | wc -l > 0",
        "PaywallView uses RevenueCatUI (not custom mock paywall)",
        "Onboarding final screen = soft paywall (Mau principle)",
        "ManaLabs quality gate: reviewer score >= 8/10",
        "Typecheck passes"
      ],
      "priority": 6, "passes": false,
      "notes": "依存: US-005 の RC Offerings + SPM。Mock は存在しない。"
    },
    {
      "id": "US-007",
      "title": "Testing",
      "phase": "Phase 5: TESTING",
      "skills": ["rshankras/testing/*", "ios-simulator-skill"],
      "acceptanceCriteria": [
        "xcodebuild test succeeds",
        "Unit tests exist for Models and Services",
        "All tests pass",
        "Typecheck passes"
      ],
      "priority": 7, "passes": false
    },
    {
      "id": "US-008",
      "title": "App Store preparation",
      "phase": "Phase 6.7-6.12: RELEASE PREP",
      "skills": ["screenshot-creator", "asc-metadata-sync", "asc-xcode-build", "asc-release-flow", "asc-testflight-orchestration", "asc-submission-health"],
      "acceptanceCriteria": [
        "Screenshots generated via screenshot-creator skill",
        "Screenshots uploaded to ASC for en-US and ja",
        "Metadata synced to ASC via asc-metadata-sync (en-US + ja)",
        ".ipa file built and uploaded (processingState = VALID)",
        "Build attached to version",
        "Age Rating set",
        "Review Details set",
        "Availability set for 175 territories",
        "Pricing set",
        "asc validate returns Errors=0",
        "Preflight 7 checks all pass",
        "Slack #metrics notified",
        "Typecheck passes"
      ],
      "priority": 8, "passes": false
    },
    {
      "id": "US-009",
      "title": "App Store submission",
      "phase": "Phase 6.13-6.14: SUBMIT",
      "skills": ["asc-release-flow"],
      "acceptanceCriteria": [
        "Slack #metrics notified: need App Privacy setup",
        ".app-privacy-done file exists (human created after ASC Web setup)",
        "asc submit create returns WAITING_FOR_REVIEW",
        "Slack #metrics notified: WAITING_FOR_REVIEW"
      ],
      "priority": 9, "passes": false
    }
  ]
}
```

#### Quality Gate（各 US 冒頭で前 US を検証）

ソース: [SonarQube Quality Gates](https://docs.sonarsource.com/sonarqube-cloud/standards/managing-quality-gates/introduction-to-quality-gates)
核心の引用: 「It can be used to block the merge of the pull request if the quality gate fails」

```
US-006 開始時:
  ├── asc subscriptions groups list --app $APP_ID → 空なら STOP
  ├── grep -r 'RevenueCat' Package.swift → 0 なら STOP
  └── 全 pass → US-006 実行開始
```

### 2.4 内部自己改善（シングルループ — LOOP A 内部）

ソース: [peterskoett/self-improving-agent](https://github.com/peterskoett/self-improving-agent)
核心の引用: 「.learnings/ に LEARNINGS.md / ERRORS.md / FEATURE_REQUESTS.md を配置。エラー発生時に自動記録 → Recurrence-Count が閾値超えたら SKILL.md に昇格」

```
ralph.sh 実行中:
    │
    ├── US-006 実行中にビルドエラー発生
    │     │
    │     ▼
    │   .learnings/ERRORS.md に記録:
    │     ID: ERR-20260302-001
    │     Summary: "RevenueCatUI PaywallView requires iOS 16+"
    │     Context: US-006 implementation
    │     Fix: "Add @available(iOS 16, *) guard"
    │     Status: resolved
    │     Recurrence-Count: 1
    │     │
    │     ▼
    │   mobileapp-builder SKILL.md に CRITICAL RULE 追加:
    │     "RULE 50: RevenueCatUI PaywallView は iOS 16+ 必須。
    │      @available(iOS 16, *) ガードを必ず付ける"
    │     │
    │     ▼
    │   git push → 同セッション内でリトライ → 成功
    │
    └── 次の US へ進む
```

#### .learnings/ ディレクトリ構成

```
daily-apps/<name>/.learnings/
├── LEARNINGS.md         ← 成功パターン（LRN-YYYYMMDD-XXX）
├── ERRORS.md            ← エラーと修正（ERR-YYYYMMDD-XXX）
└── FEATURE_REQUESTS.md  ← 改善要望（FR-YYYYMMDD-XXX）
```

#### エントリフォーマット

```markdown
### ERR-20260302-001
- **Summary**: RevenueCatUI PaywallView requires iOS 16+
- **Context**: US-006, building PaywallView
- **Fix**: Add @available(iOS 16, *) guard
- **Status**: resolved
- **Recurrence-Count**: 1
- **Area**: implementation
- **Related Files**: Views/PaywallView.swift
- **Promoted To**: mobileapp-builder SKILL.md RULE 50
```

#### 昇格ルール

| 条件 | アクション |
|------|-----------|
| Recurrence-Count >= 1（App Store リジェクト系） | 即座に SKILL.md CRITICAL RULE に昇格 |
| Recurrence-Count >= 3（ビルドエラー系） | SKILL.md CRITICAL RULE に昇格 |
| Status = resolved + 有用なパターン | LEARNINGS.md に移動 |

---

## 3. LOOP B: メタ改善ループ（毎日 23:00）

### 3.1 トリガー

| 項目 | 値 |
|------|-----|
| cron ジョブ名 | `factory-evolution-daily` |
| 実行時刻 | 毎日 23:00 JST |
| 実行者 | Anicca（OpenClaw Sonnet） |
| 統合元 | tech-news cron + openclaw-usecase cron（1つに統合） |

### 3.2 実行フロー

```
[23:00] factory-evolution-daily 起動
    │
    ├── STEP 1: 外部知識スキャン
    │     ├── tech-news: Firecrawl で最新記事収集
    │     │     - indie hacker mobile app 記事
    │     │     - TikTok marketing 最新手法
    │     │     - App Store 審査変更/ガイドライン更新
    │     │     - iOS SDK 新機能/非推奨API
    │     │
    │     ├── OpenClaw marketplace スキャン
    │     │     - clawhub search "mobile app"
    │     │     - clawhub search "tiktok marketing"
    │     │     - clawhub search "app store optimization"
    │     │     - clawhub search "onboarding conversion"
    │     │
    │     └── GitHub trending スキャン
    │           - npx skills find "ios app builder"
    │           - npx skills find "mobile app factory"
    │           - npx skills find "app store submission"
    │
    ├── STEP 2: 内部フィードバック読み込み
    │     ├── 全 daily-apps/*/.learnings/ERRORS.md を集約
    │     ├── 全 daily-apps/*/.learnings/LEARNINGS.md を集約
    │     └── 直近7日間の Slack #metrics 報告を読む
    │
    ├── STEP 3: ギャップ分析（ダブルループの核心）
    │     │
    │     │ 「戦略そのものは正しいか？」を問う:
    │     │
    │     ├── 「現スキルより良い外部スキルがあるか？」
    │     │     → あれば: npx skills add で導入、prd.json 更新
    │     │
    │     ├── 「Phase の順序は最適か？」
    │     │     → エラー頻度パターンから判断
    │     │
    │     ├── 「繰り返し失敗しているパターンは？」
    │     │     → .learnings/ERRORS.md の Recurrence-Count >= 3
    │     │     → 根本原因を特定 → SKILL.md 戦略修正
    │     │
    │     └── 「Apple ガイドライン変更の影響は？」
    │           → CRITICAL RULES に反映
    │
    ├── STEP 4: SKILL.md 群を編集
    │     ├── mobileapp-builder SKILL.md: 新 CRITICAL RULE、Phase 修正
    │     ├── ux-spec SKILL.md: オンボーディングパターン更新
    │     ├── larry SKILL.md: Hook 戦略/投稿フォーマット更新
    │     ├── tiktok-research SKILL.md: 分析基準更新
    │     ├── screenshot-creator SKILL.md: ASO スクショBP更新
    │     └── prd.json テンプレート: acceptance criteria 追加/修正
    │
    ├── STEP 5: git push
    │     └── 翌日 0:00 の LOOP A が改善版で稼働
    │
    └── STEP 6: Slack #metrics に改善レポート投稿
          - 「本日の改善: RULE XX 追加、スキル Y を Z に入れ替え」
```

### 3.3 factory-evolution-daily の cron payload

```
あなたはファクトリーの進化エージェントです。

毎日、以下を実行してファクトリースキル群を改善してください。

## STEP 1: 外部スキャン
1. Firecrawl で以下を検索（各3記事以上）:
   - "indie app launch strategy 2026"
   - "TikTok app marketing organic"
   - "App Store review rejection common reasons 2026"
   - "iOS SDK deprecated APIs"
2. clawhub search で新スキル検索（上記キーワード）
3. npx skills find で Claude Code スキル検索

## STEP 2: 内部フィードバック
1. 全 daily-apps/*/.learnings/ERRORS.md を読む
2. 全 daily-apps/*/.learnings/LEARNINGS.md を読む
3. Recurrence-Count >= 3 のエラーを抽出

## STEP 3: 分析
- 外部BPと現SKILL.mdのギャップを特定
- 繰り返しエラーの根本原因を特定
- 新スキルで既存を置き換えるべきものを特定

## STEP 4: 編集
- 該当 SKILL.md を編集（差分のみ、全体上書き禁止）
- 新スキル発見 → npx skills add でインストール
- prd.json テンプレートの acceptance criteria 更新

## STEP 5: 保存
- git add -A && git commit -m "chore: factory-evolution YYYY-MM-DD" && git push

## STEP 6: 報告
- Slack #metrics に改善サマリを投稿

## 絶対ルール
- オリジナル禁止。外部ソースの引用なしに SKILL.md を編集しない
- 全編集に「ソース: [名前](URL) / 引用: 「原文」」を付ける
- 差分編集のみ。ファイル全体の上書き禁止
```

---

## 4. マーケティング（Larry + トレンドリサーチ）

### 4.1 トレンド → Hook → 投稿 パイプライン

```
[5:00] trend-hunter cron
    │
    ├── tiktok-research: Apify で競合30日分50動画を取得
    │     → outlier 検出（engagement score threshold 2.0）
    │     → Top 5 の AI 分析
    │     → Hook パターン抽出
    │
    └── x-research: X でトレンドワード取得
          → アプリ関連トレンド抽出

    ↓

[5:30] tiktok-research-to-hooks cron（新規作成）
    │
    └── tiktok-research report.md + x-research report
          → winning-hooks.json に変換・追記
          → 形式:
            {
              "hooks": [
                {
                  "text": "6年間、何も変われなかった人へ",
                  "source": "competitor @xxx, 2.3M views",
                  "engagement_score": 8.5,
                  "date": "2026-03-01",
                  "category": "pain_point"
                }
              ]
            }

    ↓

[7:00-21:00] Larry 7投稿/日 cron（3時間毎）
    │
    ├── winning-hooks.json から本日の Hook を選択
    ├── AI 画像生成（OpenAI gpt-image-1.5）
    ├── テキストオーバーレイ
    ├── スライドショー作成
    └── Postiz API で投稿
          ├── TikTok
          ├── Instagram Reels
          ├── YouTube Shorts
          └── Threads
```

ソース: [Mau Baron Playbook](https://x.com/maboroshi_baron)
核心の引用: 「コンテンツは競合の成功パターンをコピーする。オリジナルは不要。300DL/日到達前に広告は無駄金」

### 4.2 Mau Baron ステージゲート

| ステージ | 条件 | やること | やらないこと |
|---------|------|---------|-------------|
| **Stage 0: Ship** | アプリ未公開 | build → submit → approve | マーケティング |
| **Stage 1: Organic** | App Store Live | Larry 7投稿/日、ASO最適化 | 広告、ABテスト |
| **Stage 2: Iterate** | DL > 10/日 | オンボーディング改善、recursive-improver | 広告 |
| **Stage 3: Convert** | DL > 100/日 | paywall-ab、screenshot-ab 有効化 | 広告 |
| **Stage 4: Scale** | DL > 300/日 + Trial率 > 10% | TikTok広告開始（tiktok-ads スキル） | — |

**現在のステージ: Stage 0〜1（Ship + Organic）**

---

## 5. Mau 10 オンボーディング原則（ux-spec に追加）

ソース: [Mau Baron Playbook](https://x.com/maboroshi_baron)
核心の引用: 「オンボーディングの最終画面は必ずペイウォール。Maybe Later で閉じられるようにする。DL→トライアル率10%未満なら広告は無駄金」

| # | 原則 | 実装 |
|---|------|------|
| 1 | 3画面以内で価値を見せる | オンボーディングは最大5画面 |
| 2 | ユーザーに「自分事」と思わせる | パーソナライズ質問（悩み選択） |
| 3 | コミットメントを取る | 「変わりたいですか？」→ Yes ボタン |
| 4 | 結果を先に見せる | 「3ヶ月後のあなた」ビジュアル |
| 5 | ソーシャルプルーフ | 「○万人が使用中」テキスト |
| 6 | 最終画面 = ソフトpaywall | RevenueCatUI.PaywallView + Maybe Later |
| 7 | 無料トライアル強調 | 「7日間無料」をCTA主文に |
| 8 | 恐怖を取り除く | 「いつでもキャンセル可能」テキスト |
| 9 | 年額推し | 年額を視覚的にハイライト（割引率表示） |
| 10 | SKIP は小さく | Maybe Later は目立たない配置（グレー、小フォント） |

---

## 6. フォルダ構成

```
/Users/anicca/anicca-project/
├── daily-apps/                          ← 全アプリの親
│   └── <YYYY-MM-DD>-<app-name>/        ← 1アプリ = 1フォルダ
│       ├── spec/
│       │   └── 01-trend.md             ← Phase 0 出力
│       ├── product-plan.md             ← Phase 1 出力
│       ├── competitive-analysis.md     ← Phase 2 出力
│       ├── market-research.md          ← Phase 2 出力
│       ├── claude-progress.txt         ← ralph セッション間共有
│       ├── prd.json                    ← ralph User Stories
│       ├── CLAUDE.md                   ← ralph 用指示書
│       ├── docs/                       ← Phase 3 出力
│       │   ├── PRD.md
│       │   ├── ARCHITECTURE.md
│       │   ├── UX_SPEC.md             ← Mau 10原則含む
│       │   ├── DESIGN_SYSTEM.md
│       │   ├── IMPLEMENTATION_GUIDE.md
│       │   ├── TEST_SPEC.md
│       │   └── RELEASE_SPEC.md
│       ├── .learnings/                 ← 自己改善記録
│       │   ├── LEARNINGS.md
│       │   ├── ERRORS.md
│       │   └── FEATURE_REQUESTS.md
│       ├── .asc/                       ← ASC 設定
│       ├── screenshots/                ← スクショ
│       ├── .signing/                   ← 証明書
│       └── <AppName>ios/               ← Xcode プロジェクト
│           ├── <AppName>/
│           ├── <AppName>Tests/
│           └── fastlane/
│
├── .claude/skills/                     ← スキル群（LOOP B が編集）
│   ├── mobileapp-builder/SKILL.md
│   ├── ux-spec/SKILL.md
│   ├── screenshot-creator/SKILL.md
│   └── ...
│
└── winning-hooks.json                  ← トレンド Hook 蓄積
```

---

## 7. Cron ジョブ一覧

### 7.1 既存 cron（変更なし）

| ジョブ名 | 時刻 | 状態 | 内容 |
|---------|------|------|------|
| `trend-hunter` | 5:00 AM/PM | ✅ 有効 | TikTok/X トレンド収集 |
| `app-metrics` | 5:05/11:05/17:05/23:05 | ✅ 有効 | DL数/conversion 計測 |
| `app-reviews` | 5:10 AM | ✅ 有効 | App Store レビュー収集 |
| `mobileapp-factory-midnight` | 0:00 | ✅ 有効 | LOOP A トリガー |

### 7.2 既存 cron（修正）

| ジョブ名 | 変更内容 | 理由 |
|---------|---------|------|
| `tech-news` | **削除** → factory-evolution-daily に統合 | LOOP B に統合 |
| `openclaw-usecase` | **削除** → factory-evolution-daily に統合 | LOOP B に統合 |
| `screenshot-ab` | **enabled: false** に変更 | Stage 3 (DL > 100/日) まで不要 |
| `paywall-ab` | **enabled: false** に変更 | Stage 3 (DL > 100/日) まで不要 |
| `larry-tiktok-*` | **7投稿/日に拡張**（3時間毎） | Mau: オーガニック最大化 |

### 7.3 新規 cron（追加）

| ジョブ名 | 時刻 | 内容 |
|---------|------|------|
| `tiktok-research-to-hooks` | 5:30 AM | tiktok-research report → winning-hooks.json 変換 |
| `factory-evolution-daily` | 23:00 | LOOP B: 外部スキャン → SKILL.md 改善 |

### 7.4 cron パッチ（jobs.json への差分）

#### 新規追加: tiktok-research-to-hooks

```json
{
  "id": "tiktok-research-to-hooks",
  "enabled": true,
  "schedule": "30 5 * * *",
  "timezone": "Asia/Tokyo",
  "target": "anicca",
  "payload": {
    "message": "tiktok-research の最新レポートを読み、winning-hooks.json に変換して追記してください。\n\n## 手順\n1. 直近の tiktok-research report.md を読む\n2. outlier（engagement score > 2.0）の Hook テキストを抽出\n3. /Users/anicca/anicca-project/winning-hooks.json に追記\n4. 形式: {\"hooks\": [{\"text\": \"...\", \"source\": \"...\", \"engagement_score\": N, \"date\": \"YYYY-MM-DD\", \"category\": \"pain_point|curiosity|authority|transformation\"}]}\n5. 重複 Hook は追加しない（text で判定）\n6. git push",
    "skills": ["tiktok-research"],
    "reportTo": { "channel": "slack", "target": "C091G3PKHL2" }
  },
  "executionModel": "anthropic/claude-sonnet-4-20250514"
}
```

#### 新規追加: factory-evolution-daily

```json
{
  "id": "factory-evolution-daily",
  "enabled": true,
  "schedule": "0 23 * * *",
  "timezone": "Asia/Tokyo",
  "target": "anicca",
  "payload": {
    "message": "あなたはファクトリーの進化エージェントです。\n\n## STEP 1: 外部スキャン\n1. Firecrawl で検索（各3記事）:\n   - 'indie app launch strategy 2026'\n   - 'TikTok app marketing organic'\n   - 'App Store review rejection common reasons 2026'\n2. clawhub search で新スキル検索\n3. npx skills find で Claude Code スキル検索\n\n## STEP 2: 内部フィードバック\n1. 全 /Users/anicca/anicca-project/daily-apps/*/.learnings/ERRORS.md を読む\n2. Recurrence-Count >= 3 のエラーを抽出\n\n## STEP 3: ギャップ分析\n- 外部BPと現SKILL.mdのギャップを特定\n- 繰り返しエラーの根本原因を特定\n- 新スキルで既存を置き換えるべきものを特定\n\n## STEP 4: SKILL.md 編集\n- 差分のみ編集（全体上書き禁止）\n- 全編集に「ソース: [名前](URL) / 引用」を付ける\n\n## STEP 5: git push\n\n## STEP 6: Slack #metrics に改善サマリ投稿",
    "skills": [],
    "reportTo": { "channel": "slack", "target": "C091G3PKHL2" }
  },
  "executionModel": "anthropic/claude-sonnet-4-20250514"
}
```

#### 修正: screenshot-ab と paywall-ab を無効化

```json
// screenshot-ab: "enabled": true → "enabled": false
// paywall-ab: "enabled": true → "enabled": false
```

#### 修正: Larry を 7投稿/日に拡張

```json
// 既存の larry-tiktok-daily-report は維持
// 追加: larry-post-{1-7} を 7:00, 9:00, 11:00, 13:00, 15:00, 17:00, 19:00 に設定
// 各 cron の payload に winning-hooks.json 読み込み指示を追加
```

---

## 8. 1日のタイムライン

```
23:00  LOOP B: factory-evolution-daily
         外部スキャン → SKILL.md 改善 → git push

 0:00  LOOP A: mobileapp-factory-midnight
         Anicca → prd.json 生成 → ralph.sh 起動

 0:05  ralph SESSION 1: US-001〜004（Research + Spec）
         idea-generator → product-agent → competitive-analysis → impl-spec
         → docs/ 7ファイル生成

 1:00  ralph SESSION 2: US-005（Infrastructure）
         ASC app 作成 → IAP → RevenueCat → SPM
         ★内部ループ: エラー → .learnings/ → SKILL.md 修正 → リトライ

 2:00  ralph SESSION 3: US-006（Implementation）
         IMPL_GUIDE.md に従い実装
         ManaLabs 品質ゲート（8/10 未満 → リトライ）
         ★内部ループ: ビルドエラー → .learnings/ → CRITICAL RULE 追加

 5:00  trend-hunter: TikTok/X トレンド収集

 5:30  tiktok-research-to-hooks: → winning-hooks.json 更新

 6:00  ralph SESSION 4: US-007（Testing）

 7:00  Larry 投稿 #1（winning-hooks.json から Hook 選択）

 8:00  ralph SESSION 5: US-008（App Store Prep）
         スクショ → メタデータ → ビルド → preflight

 9:00  Larry 投稿 #2

10:00  ralph SESSION 6: US-009（Submit）
         → Slack: "App Privacy 設定してください"
         → .app-privacy-done 待ち
         → submit → WAITING_FOR_REVIEW

11:00  Larry 投稿 #3
13:00  Larry 投稿 #4
15:00  Larry 投稿 #5
17:00  Larry 投稿 #6
19:00  Larry 投稿 #7

22:00  .learnings/ 最終記録

23:00  LOOP B 再び... ∞
```

---

## 9. 将来のスケーリング（1日3アプリ同時）

**現在は不要。Stage 4 (DL > 300/日 + Trial率 > 10%) 到達後に検討。**

```
将来の並列実行:
  Agent 1: daily-apps/2026-03-15-app-a/ → ralph.sh
  Agent 2: daily-apps/2026-03-15-app-b/ → ralph.sh
  Agent 3: daily-apps/2026-03-15-app-c/ → ralph.sh

各アプリが独立フォルダのため DerivedData 衝突なし。
収益 > コスト（API費用）の場合のみ実行。
最も成功したアプリのみ残し、他は削除。
```

---

## 10. 実装チェックリスト

| # | タスク | 対象ファイル | 状態 |
|---|--------|-------------|------|
| 1 | ux-spec に Mau 10原則追加 | `.claude/skills/ux-spec/SKILL.md` | ❌ |
| 2 | tiktok-research → winning-hooks.json 接続 | `.claude/skills/tiktok-research/SKILL.md` | ❌ |
| 3 | Larry に winning-hooks.json 読み込み追加 | `~/.openclaw/workspace/skills/larry/SKILL.md` | ❌ |
| 4 | .learnings/ パターンを CLAUDE.md テンプレに追加 | `mobileapp-builder SKILL.md` | ❌ |
| 5 | screenshot-ab / paywall-ab cron 無効化 | `~/.openclaw/cron/jobs.json` | ❌ |
| 6 | tiktok-research-to-hooks cron 追加 | `~/.openclaw/cron/jobs.json` | ❌ |
| 7 | factory-evolution-daily cron 追加 | `~/.openclaw/cron/jobs.json` | ❌ |
| 8 | tech-news / openclaw-usecase cron 統合・削除 | `~/.openclaw/cron/jobs.json` | ❌ |
| 9 | Larry cron を 7投稿/日に拡張 | `~/.openclaw/cron/jobs.json` | ❌ |
| 10 | v3 prd.json テンプレートを mobileapp-factory に配置 | `mobileapp-factory SKILL.md` | ❌ |
| 11 | winning-hooks.json 初期ファイル作成 | `/Users/anicca/anicca-project/winning-hooks.json` | ❌ |
| 12 | daily-apps/ ディレクトリ作成 | `/Users/anicca/anicca-project/daily-apps/` | ❌ |

---

## ソース一覧

| ソース | URL | 使用箇所 |
|--------|-----|---------|
| Chris Argyris, Double-Loop Learning | https://hbr.org/1977/09/double-loop-learning-in-organizations | 2ループ分離の理論的根拠 |
| ICE論文 | https://arxiv.org/abs/2401.13996 | 内部/外部ループ分離の実証 |
| Voyager | https://voyager.minedojo.org/ | スキルライブラリパターン |
| peterskoett/self-improving-agent | https://github.com/peterskoett/self-improving-agent | .learnings/ パターン |
| snarktank/ralph | https://github.com/snarktank/ralph | ralph.sh for loop 実行 |
| rshankras/claude-code-apple-skills | https://github.com/rshankras/claude-code-apple-skills | 8フェーズ + 148スキル |
| ManaLabs App Factory | https://manalabs.wtf/appfactory | 品質ゲート、reviewer agent |
| Mau Baron Playbook | https://x.com/maboroshi_baron | オンボーディング原則、ステージゲート |
| SonarQube Quality Gates | https://docs.sonarsource.com/sonarqube-cloud/standards/managing-quality-gates/ | US間品質ゲート |
| OpenClaw Docs - Exec Tool | https://docs.openclaw.ai/tools/exec | notifyOnExit |
| Anthropic Skill Guide | https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf | スキル構造 |
