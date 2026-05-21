# Anicca 1.6.3 — Game Plan

最終更新: 2026-02-13  
ステータス: 実装準備完了

---

## 📍 Big Picture

1.6.3 は **「投稿して終わり」から「学習ループ」への転換** を実現するリリース。

```
┌─────────────────────────────────────────────────────────────────────┐
│                      1.6.3 — LEARNING LOOPS                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────┐     ┌───────────────┐     ┌───────────────┐     │
│  │  Hook-Based   │     │   Viral       │     │   Paywall     │     │
│  │  Content Loop │     │   Nudge Eval  │     │   Experiment  │     │
│  └───────┬───────┘     └───────┬───────┘     └───────┬───────┘     │
│          │                     │                     │             │
│          ▼                     ▼                     ▼             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   EVIDENCE → LEARN → ITERATE                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  + iPad 対応 (Minimum)                                              │
│  + P0-P2 技術負債解消                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Goals

| # | Goal | Metric | Target |
|---|------|--------|--------|
| 1 | 投稿事故率ゼロ | 文字化け・可読性NG | 0% |
| 2 | Hook 再利用率 | リミックス vs オリジナル | 70:30 |
| 3 | TikTok 初動維持率 | 3秒視聴率 | +20% |
| 4 | Paywall CVR | 継続実験 | 4.2% → 8% (6ヶ月) |
| 5 | iPad 対応 | App Store 提出可能 | ✅ |
| 6 | P0 バグ | 即時対応完了 | 0件 |

---

## 📦 Initiatives (5つ)

### Initiative 1: Viral Nudge Evaluation Loop
**Spec:** `1.6.3-viral-nudge-eval-spec.md`  
**要約:** 投稿前品質ゲート + 再生成ループ + 投稿後証跡  
**核心:** No Verify, No Post

```
As-Is: 生成 → 投稿 → 祈り
To-Be: 生成 → 評価(≥85) → 投稿 → publicUrl保存
       └─ <85 → 再生成(max 10) → fallback
```

**実装タスク:**
| # | タスク | ファイル | 見積 |
|---|--------|----------|------|
| T1 | Evaluate Service | `services/evaluation/` | 1d |
| T2 | Regeneration Orchestrator | `services/generation/` | 0.5d |
| T3 | TikTok Publisher Update (autoAddMusic: true) | `jobs/tiktok-poster.ts` | 0.5d |
| T4 | Evidence Logging (submissionId/publicUrl) | `lib/evidence.ts` | 0.5d |
| T5 | X/iOS Minimal Parity | 各 poster | 0.5d |

---

### Initiative 2: Hook-Based Content Loop
**Spec:** `hook-based-content-loop.md`  
**要約:** Hook DB から効いた Hook をリミックス → 投稿 → 25h 後学習  
**核心:** 競合で効いたものをリミックス、結果を学ぶ

```
As-Is: trend-hunter → Hook 貯まる → 使われない
To-Be: trend-hunter → Hook DB → draft → verify → post → fetch_metrics (25h後)
                                                          └─ Hook DB 更新
```

**実装タスク:**
| # | タスク | ファイル | 見積 |
|---|--------|----------|------|
| E1 | draft_content executor | `executors/draft_content.ts` | 1d |
| E2 | verify_content executor | `executors/verify_content.ts` | 0.5d |
| E3 | post_x executor (X API → postId → schedule fetch) | `executors/post_x.ts` | 0.5d |
| E4 | post_tiktok executor | `executors/post_tiktok.ts` | 0.5d |
| E5 | fetch_metrics executor (25h後) | `executors/fetch_metrics.ts` | 1d |
| E6 | Hook DB schema (ourViews, ourLikes, useCount) | `prisma/schema.prisma` | 0.5d |

---

### Initiative 3: Paywall Experiment Loop
**Spec:** `paywall-experiment-loop.md`  
**要約:** RevenueCat Experiments で週次 A/B → 勝者昇格 → 新 Variant 生成  
**核心:** Candle 原則（コアバリューは訴求しない、深さ・進捗・カスタマイズを訴求）

```
As-Is: Paywall 固定、データなし
To-Be: 毎週月曜 → 実験結果 → 有意差あり? → 勝者昇格 → 新 Variant 生成
```

**実装タスク:**
| # | タスク | ファイル | 見積 |
|---|--------|----------|------|
| P1 | RevenueCat API client | `lib/revenuecat.ts` | 0.5d |
| P2 | 統計的有意差判定 (chi-squared) | `lib/statistics.ts` | 0.5d |
| P3 | LLM Variant 生成 (Candle 原則) | `lib/paywall-generator.ts` | 0.5d |
| P4 | Cron job (毎週月曜9時) | VPS cron | 0.25d |
| P5 | Slack 通知フォーマット | `lib/slack-templates.ts` | 0.25d |

---

### Initiative 4: iPad 対応 (Minimum)
**Spec:** `ipad.md`  
**要約:** iPhone 拡大ではなく、iPadアプリとして提供  
**核心:** Split View / Stage Manager で破綻しない

```
As-Is: TARGETED_DEVICE_FAMILY = 1 (iPhone only)
To-Be: TARGETED_DEVICE_FAMILY = 1,2 (iPhone + iPad)
       + UIRequiresFullScreen = false
       + 最大幅制限 (600-720pt)
```

**実装タスク:**
| # | タスク | ファイル | 見積 |
|---|--------|----------|------|
| I1 | プロジェクト設定変更 | `project.pbxproj` | 0.5d |
| I2 | UI 最大幅制限 | 全 View | 0.5d |
| I3 | オンボーディング iPad 調整 | `OnboardingFlowView.swift` | 0.5d |
| I4 | NudgeCard/Paywall iPad 表示 | 各 View | 0.5d |
| I5 | Split View リサイズ対応 | 全 View | 1d |
| I6 | App Store スクショ作成 | 運用 | 0.5d |

---

### Initiative 5: P0-P2 技術負債解消
**Spec:** `review-reflection.md`  
**要約:** Agent Teams レビューで検出された19件の修正  
**核心:** AppState God Object 分割、Cron バッチ化、罪悪感文言修正

```
As-Is: AppState.swift (934行)、Cron 逐次処理、URLSession リーク
To-Be: State/ 分割 (4ファイル)、バッチ INSERT、lazy var session
```

**P0 タスク (即時対応):**
| # | 問題 | 修正 | 見積 |
|---|------|------|------|
| P0-1 | AppState God Object (934行) | State/ に分割 | 2d |
| P0-2 | Cron 逐次処理 | p-limit + バッチ INSERT | 1d |
| P0-3 | URLSession リーク | `lazy var session` | 0.1d |
| P0-4 | Paywall 拒否後レビュー依頼 | 削除 | 0.25d |
| P0-5 | ローカライズバグ | `String(localized:)` | 0.1d |
| P0-6 | 罪悪感文言 | Localizable.strings 修正 | 0.25d |

---

## 📅 Implementation Order

**依存関係を考慮した実行順序:**

```
Week 1: P0 技術負債 (ブロッカー解消)
  ├─ P0-3: URLSession リーク (0.1d) ← 最も簡単、即効果
  ├─ P0-4: Paywall レビュー削除 (0.25d)
  ├─ P0-5: ローカライズバグ (0.1d)
  ├─ P0-6: 罪悪感文言 (0.25d)
  └─ P0-1: AppState 分割 (2d) ← 他の iOS 変更の前提

Week 2: Hook-Based Content Loop
  ├─ E6: Hook DB schema (0.5d) ← 他の executor の前提
  ├─ E2: verify_content (0.5d) ← E1 の前に品質チェック
  ├─ E1: draft_content (1d)
  ├─ E3: post_x (0.5d)
  ├─ E4: post_tiktok (0.5d)
  └─ E5: fetch_metrics (1d)

Week 3: Viral Nudge Evaluation Loop
  ├─ T1: Evaluate Service (1d)
  ├─ T2: Regeneration Orchestrator (0.5d)
  ├─ T3: TikTok Publisher Update (0.5d)
  ├─ T4: Evidence Logging (0.5d)
  └─ T5: X/iOS Parity (0.5d)

Week 4: iPad + Paywall
  ├─ I1-I5: iPad 対応 (3.5d)
  └─ P1-P5: Paywall Experiment Loop (2d)

Week 5: 統合テスト + バグ修正 + リリース
```

---

## 🧪 Test Strategy

### Unit Tests (Codex 実装)
| カテゴリ | テスト例 |
|---------|---------|
| Evaluation | 文字化け判定、スコア計算、Hard Fail 条件 |
| Hook DB | 7日クールダウン、重み付きランダム選択 |
| Statistics | chi-squared 検定、有意差判定 |
| State | AuthState 変更で NudgeView 再レンダリングされない |

### Integration Tests
| カテゴリ | テスト例 |
|---------|---------|
| Content Loop | draft → verify → post → fetch_metrics 全フロー |
| Blotato | TikTok投稿 → publicUrl 取得 |
| RevenueCat | Experiment 結果取得 → Offering 更新 |

### E2E Tests (Maestro)
| フロー | シナリオ |
|--------|---------|
| Onboarding | iPad Portrait/Landscape |
| NudgeCard | 表示 → 👍/👎 → dismiss |
| Paywall | 表示 → 閉じる (レビュー依頼なし確認) |

---

## 🚨 Risks & Mitigations

| リスク | 対策 |
|--------|------|
| AppState 分割で regression | 段階的移行、各 State ごとにテスト |
| 評価ゲート厳格すぎ | fallback テンプレート、閾値調整 |
| Hook DB 枯渇 | trend-hunter 頻度 UP、閾値下げ |
| RevenueCat API 変更 | エラー時 Slack 通知、手動フォールバック |
| iPad スクショ不足 | シミュレータ自動生成 |

---

## 🎯 Definition of Done

### 1.6.3 リリース条件:

**Must Have (全て満たす):**
- [ ] P0-1〜P0-6 修正完了
- [ ] TikTok 投稿前評価ゲート稼働
- [ ] score < 85 の投稿が本番に出ない
- [ ] Hook DB からリミックス可能
- [ ] 投稿後 25h で metrics 収集
- [ ] iPad で主要フロー完走
- [ ] Maestro E2E 全パス

**Should Have:**
- [ ] Paywall Experiment 初回稼働
- [ ] NavigationSplitView (iPad regular)
- [ ] P1 修正完了

**Nice to Have:**
- [ ] P2 修正
- [ ] 週次コンテンツレポート自動化

---

## 📁 Related Specs

| ファイル | 内容 |
|----------|------|
| `1.6.3-viral-nudge-eval-spec.md` | 投稿前評価ゲート詳細 |
| `hook-based-content-loop.md` | Hook DB 活用フロー詳細 |
| `paywall-experiment-loop.md` | Paywall A/B テスト詳細 |
| `ipad.md` | iPad 対応詳細 |
| `review-reflection.md` | P0-P2 修正詳細 |

---

## 🛠 Commands

```bash
# iOS テスト
cd aniccaios && FASTLANE_SKIP_UPDATE_CHECK=1 fastlane test

# API テスト
cd apps/api && npm test

# E2E テスト (Maestro)
maestro test maestro/flows/

# Codex 実装依頼
ssh cbns03@100.108.140.123 'export PATH="/opt/homebrew/bin:$PATH" && cd /Users/cbns03/Downloads/anicca-project && /opt/homebrew/bin/codex exec --dangerously-bypass-approvals-and-sandbox "Implement T1: Evaluate Service as per 1.6.3-viral-nudge-eval-spec.md"'
```

---

## Changelog

- 2026-02-13: v1.0 Game Plan 作成

---
---

## 🧘 ゲームプラン：苦しみを減らす 24/7 エージェント

---

### ミッション（絶対忘れない）

> **What if Buddha were software?**
> 
> 苦しみを減らす。お金を稼ぐ。また苦しみを減らす。この無限ループ。
> 
> **ベストプラクティスに従う。オリジナルは入れない。謙虚に。コピーする。反復する。**

---

## 📋 スキル統合マップ

| スキル | どこに統合 | 使い方 |
|--------|-----------|--------|
| **bird** | X 投稿 cron | x-poster cron を bird に置き換え |
| **moltbook-interact** | Moltbook 投稿 cron | ✅ 完了 |
| **gog** | Gmail/Calendar cron | 毎朝 7:00 Calendar、8:00 Gmail |
| **x402** | 将来の Agent 経済 | 他 Agent への支払い・収益 |
| **proactive-agent** | 全体アーキテクチャ | WAL Protocol、Working Buffer 採用 |
| **revenuecat** | daily-metrics cron | MRR/Churn データ取得 |
| **master-marketing** | Hook 作成時 | AARRR、Content Remix |
| **copywriting** | 投稿作成時 | Hook 最適化 |
| **tdd-discipline** | 開発時 | anicca-auto-development に統合 |
| **systematic-debugging** | 開発時 | anicca-auto-development に統合 |
| **swift-expert** | iOS 開発時 | Spec 作成、コードレビュー |
| **swiftui-ui-patterns** | UI 開発時 | SwiftUI パターン参照 |
| **social-intelligence** | トレンド分析 | trend-hunter に統合 |

---

## 🔄 Heartbeat vs Cron（決定版）

### Heartbeat（30分ごと、メインセッション）

**HEARTBEAT.md に書くこと：**

```markdown
# HEARTBEAT.md

## 常に確認すること
- [ ] SESSION-STATE.md 更新（WAL Protocol）
- [ ] context % 確認（60%超えたら Working Buffer 開始）
- [ ] 最近の会話で「ベストプラクティス」検索したか？
- [ ] 何か proactive にできることはないか？

## 2-4時間ごとにローテーション
- [ ] Gmail 未読チェック（重要なのだけ）
- [ ] Calendar 今日・明日の予定
- [ ] Moltbook hot posts 確認
- [ ] X mentions 確認

## 毎日1回（朝の Heartbeat で）
- [ ] MEMORY.md に昨日の学びを追加
- [ ] 「今日は何を ship するか」を考える
```

### Cron（正確な時刻、独立セッション）

| 時刻 | ジョブ | payload | delivery |
|------|--------|---------|----------|
| **07:00** | calendar-briefing | VPS→Mac SSH で `gog calendar events primary --from today --to tomorrow` → Slack #metrics | announce |
| **08:00** | gmail-briefing | VPS→Mac SSH で `gog gmail search 'is:unread newer_than:1d' --max 10` → Slack #metrics | announce |
| **09:00** | x-poster-morning | **bird** skill で投稿 | announce |
| **09:00** | tiktok-poster-morning | Blotato 経由 | announce |
| **09:00** | app-nudge-morning | iOS push | announce |
| **05:00** | daily-appstore-metrics | **revenuecat** + Mixpanel + ASC | announce |
| **20:30** | moltbook-poster | **moltbook-interact** | announce |
| **21:00** | x-poster-evening | **bird** skill で投稿 | announce |
| **21:00** | tiktok-poster-evening | Blotato 経由 | announce |
| **23:00** | daily-memory | 日記・教訓記録 | announce |
| **4時間毎** | trend-hunter | トレンド収集 | none（重要な時だけ通知） |
| **5分毎** | suffering-detector | 危機監視 | none（危機時だけ通知） |

**VPS→Mac で gog を動かすとき（必須）:** Mac の非インタラクティブ SSH では `PATH` に `/opt/homebrew/bin` が入らないため、**必ず PATH を export するか gog をフルパスで呼ぶ**。

```bash
# calendar-briefing (07:00) - VPS 上で実行するコマンド例
ssh -o ConnectTimeout=10 -o BatchMode=yes cbns03@100.108.140.123 'export PATH="/opt/homebrew/bin:$PATH" && gog calendar events primary --from today --to tomorrow'

# gmail-briefing (08:00) - VPS 上で実行するコマンド例
ssh -o ConnectTimeout=10 -o BatchMode=yes cbns03@100.108.140.123 'export PATH="/opt/homebrew/bin:$PATH" && gog gmail search "is:unread newer_than:1d" --max 10'
```

---

## 🚀 24/7 自律運用アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                    ANICCA (VPS)                         │
│                   🧘 Buddhist Agent                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Heartbeat  │  │    Cron     │  │   Main      │     │
│  │  (30分毎)   │  │  (正確時刻)  │  │  Session    │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │             │
│         ▼                ▼                ▼             │
│  ┌─────────────────────────────────────────────────┐   │
│  │               SKILL 統合層                       │   │
│  │                                                  │   │
│  │  [投稿] bird, moltbook-interact, tiktok-poster  │   │
│  │  [分析] revenuecat, master-marketing            │   │
│  │  [生活] gog (Gmail/Calendar)                    │   │
│  │  [開発] swift-expert, tdd-discipline            │   │
│  │  [支払] x402                                    │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                               │
│                         ▼                               │
│  ┌─────────────────────────────────────────────────┐   │
│  │                OUTPUT 層                         │   │
│  │                                                  │   │
│  │  📱 iOS App (nudge)                             │   │
│  │  🐦 X (@AniccaNudges)                           │   │
│  │  🎵 TikTok (@anicca.self)                       │   │
│  │  🦞 Moltbook                                    │   │
│  │  📧 Newsletter                                  │   │
│  │  💬 Slack #metrics (報告)                       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│                   CODEX (Mac)                           │
│                   ⚡ Player Agent                        │
├─────────────────────────────────────────────────────────┤
│  - iOS App 実装                                         │
│  - TestFlight 配信                                      │
│  - App Store 申請                                       │
│  - コードレビュー                                       │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 投稿フロー（ベストプラクティス必須）

```
1. トレンド検索（FireCrawl, web_search）
   ↓
2. バズってる Hook を収集（master-marketing）
   ↓
3. Hook をコピー・リミックス（copywriting）
   ↓
4. 投稿作成
   ↓
5. 検証ゲート（内容チェック）
   ↓
6. 投稿（bird / Blotato）
   ↓
7. 25h 後にメトリクス収集
   ↓
8. 学習（何が効いた？ダブルダウン）
```

**絶対ルール:**
- **オリジナルを入れない** — バズった Hook をコピー
- **検索してから作る** — 「検索せずに作る」は禁止
- **反復** — 効いたものにダブルダウン

---

## 📅 1日のスケジュール

| 時刻 | 何をする | 誰が報告を見る |
|------|----------|---------------|
| 05:00 | daily-appstore-metrics（MRR, Downloads） | Slack #metrics |
| 07:00 | calendar-briefing（今日の予定） | Slack #metrics → Dais |
| 08:00 | gmail-briefing（未読メール） | Slack #metrics → Dais |
| 09:00 | X 投稿 + TikTok 投稿 + iOS nudge | Slack #metrics |
| 14:00 | iOS nudge (午後) | - |
| 20:00 | iOS nudge (夜) | - |
| 20:30 | Moltbook 投稿 | Slack #metrics |
| 21:00 | X 投稿 + TikTok 投稿 | Slack #metrics |
| 23:00 | daily-memory（日記） | Slack #metrics |
| **常時** | Heartbeat (30分毎) | - |
| **常時** | suffering-detector (5分毎) | 危機時のみ Slack |
| **常時** | iOS 開発 → Codex に依頼 → レビュー → Ship | Slack #metrics |

---

## 🎯 TODO（実装する時の順番）

1. **x-poster cron を bird に置き換え**
2. **calendar-briefing cron 新規作成（07:00）**
3. **gmail-briefing cron 新規作成（08:00）**
4. **daily-appstore-metrics を revenuecat スキルで改善**
5. **HEARTBEAT.md を更新（上記の内容）**
6. **proactive-agent の WAL Protocol を採用**

---

## 🧠 僕が常に考えること

1. **どうすれば苦しみを減らせる？**
2. **収益を増やすには？**（iOS App, Newsletter, TikTok, X）
3. **ベストプラクティスは何？**（検索して従う）
4. **今日は何を ship する？**
5. **何が効いた？ダブルダウンできる？**

---

**これがゲームプラン。実装する？**