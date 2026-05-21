# The Factory — Anicca Agent Empire Architecture

**作成日**: 2026-02-20
**更新日**: 2026-02-21
**作成者**: Anicca (CEO Agent)
**目的**: 苦しみを減らす製品を大量生産する自律エージェント工場の設計図

---

## ビジョン

毎時1000のアプリ、API、コンテンツがリリースされ、各製品が自律的にiterate・改善され、収益が自動的に蓄積される。収益の10%は自動寄付。全ての製品の目的は苦しみを減らすこと。

---

## レイヤー構造

```
┌─────────────────────────────────────────────┐
│  Layer 0: Dais (アドバイザー / オーナー)       │
│  - ビジョン設定、資金管理、最終判断            │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│  Layer 1: Anicca (CEO Agent)                 │
│  - SKILL.mdの設計・改善                       │
│  - メトリクス集約 → 判断 (kill/iterate/scale) │
│  - 勝ちパターンの発見 → 全スキルに展開        │
│  - 工場の設計図を改善し続ける                  │
│  Runtime: OpenClaw Gateway (Mac Mini)        │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│  Layer 2: Factory Skills (SKILL.md × N)      │
│  - 各スキル = 1つの工場ライン                  │
│  - cron で定期実行                             │
│  - Claude Code サブエージェントが実行          │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│  Layer 3: Claude Code Agents (×1000+)        │
│  - 各エージェント = 1製品のオーナー            │
│  - SKILL.md に従って自律実行                   │
│  - リサーチ→ビルド→デプロイ→マーケ→iterate   │
│  - 結果をメトリクスとしてレポート              │
└─────────────────────────────────────────────┘
```

---

## 核心原則

1. **スキル + cron = ペア。** スキル単体では動かない。必ずcronとセットで設計する。
2. **聖書（SKILL.md）に従え。** larryはlarry。分解しない。拡張しない。そのまま使う。
3. **アプリごとにcron。** 直列ループではなく、アプリごとに専用cronを作って並列実行。

---

## スキル/cronペア一覧

### 1. mobileapp-planner + cron

| 項目 | 内容 |
|------|------|
| スキル | mobileapp-planner |
| cron | 毎時 |
| Input | トレンドデータ、App Storeランキング、過去アプリのメトリクス |
| Output | factory/specs/{app-name}.md |
| やること | ニッチ発見 → アプリ企画 → spec.md書く |

### 2. mobileapp-builder + cron

| 項目 | 内容 |
|------|------|
| スキル | mobileapp-builder |
| cron | spec.md検出時（またはplanner後） |
| Input | factory/specs/{app-name}.md |
| Output | App Store提出済みアプリ + factory/apps/{app-name}/app-profile.json |
| やること | spec.md読む → コード書く → テスト → ビルド → App Store提出 → app-profile.json生成 |
| **追加アクション** | **larry-{app-name} cron を登録する**（アプリ誕生 = cron誕生） |

### 3. larry × N（アプリごと）+ cron × N

| 項目 | 内容 |
|------|------|
| スキル | larry（tiktok-app-marketing）— **変更なし、そのまま使う** |
| cron | larry-{app-name} 毎朝7:00am（アプリごとに1つ、並列実行） |
| Input | factory/apps/{app-name}/tiktok-marketing/ |
| Output | スケジュール済み投稿（Postiz経由で7:30am, 4:30pm, 9pm自動投稿） |

**cronの動作フロー:**

```
larry-{app-name} cron 実行時（毎朝7am）:

  if config.json 存在しない:
    → larry init（Phase 1-8 自動実行）
    → config.json, competitor-research.json,
      strategy.json, hook-performance.json 生成
    → 初日の投稿もスケジュール

  else:
    1. メトリクス取得（Postiz + RevenueCat）
    2. 診断（daily-report.js --days 3）
       High views + High conv → SCALE IT
       High views + Low conv  → FIX CTA
       Low views + High conv  → FIX HOOK
       Low views + Low conv   → FULL RESET
    3. strategy.json更新
    4. 今日の3投稿分スライド生成（6枚×3=18枚）
    5. テキストoverlay
    6. Postiz APIで3投稿をスケジュール
       → 7:30am, 4:30pm, 9pm に自動投稿
    7. レポート → Slack #metrics
```

**Postizがスケジュール投稿を実行するので、cronは朝1回だけでいい。**

### 4. metrics-collector + cron

| 項目 | 内容 |
|------|------|
| スキル | metrics-collector（既存app-metricsスキルの拡張） |
| cron | 毎朝7:00am |
| Input | 全プロダクトのデータソース |
| Output | workspace/metrics/YYYY-MM-DD.json |
| データソース | Postiz, RevenueCat, ASC, Mixpanel, Substack, Spotify等 |
| やること | 全ソースからデータ吸い上げ → プロダクト別に整理 → 保存 |

---

## ディレクトリ構造

```
workspace/factory/
├── specs/
│   ├── sati.md                          ← planner が生成
│   ├── app-002.md
│   └── app-003.md
│
├── apps/
│   ├── sati/
│   │   ├── app-profile.json             ← builder が生成
│   │   └── tiktok-marketing/            ← larry の作業ディレクトリ
│   │       ├── config.json              ← larry init で生成
│   │       ├── app-profile.json         ← larry用アプリ情報
│   │       ├── competitor-research.json
│   │       ├── strategy.json
│   │       ├── hook-performance.json
│   │       ├── posts/
│   │       │   ├── 2026-02-21-0730/
│   │       │   ├── 2026-02-21-1630/
│   │       │   └── 2026-02-21-2100/
│   │       └── reports/
│   │           └── 2026-02-21.md
│   │
│   ├── app-002/
│   │   ├── app-profile.json
│   │   └── tiktok-marketing/
│   │       └── ...（同じ構造）
│   │
│   └── app-003/
│       └── ...
│
├── shared/
│   ├── global-config.json               ← Postiz APIキー、OpenAI key等
│   └── winning-hooks.json               ← 全アプリ横断の勝ちパターン
│
└── metrics/
    ├── 2026-02-21.json
    └── 2026-02-22.json
```

---

## アプリ誕生フロー（全自動）

```
Step 1: mobileapp-planner (cron毎時)
        → トレンドリサーチ → ニッチ発見
        → factory/specs/app-003.md 生成

Step 2: mobileapp-builder (cron)
        → specs/app-003.md 読む
        → コード書く → テスト → ビルド → App Store提出
        → factory/apps/app-003/app-profile.json 生成
        → larry-app-003 cron を登録（毎朝7am）

Step 3: larry-app-003 cron（翌朝7am、自動実行）
        → config.json無い → larry init 自動実行
        → Phase 1-8: 競合リサーチ → 画像スタイル決定
          → Postiz接続 → 戦略策定 → 全設定ファイル生成
        → 初日の3投稿をスケジュール

Step 4: Postiz が自動投稿
        → 7:30am, 4:30pm, 9pm

Step 5: 翌朝 larry-app-003 cron（2日目〜）
        → config.json有る → daily run
        → メトリクス → 診断 → 戦略更新 → 生成 → スケジュール
        → 永遠にイテレーション
```

---

## cron一覧（初期: 7アプリ想定）

| cron名 | スケジュール | スキル | 対象 |
|--------|-------------|--------|------|
| mobileapp-planner | 毎時 | mobileapp-planner | 全体 |
| mobileapp-builder | planner後 | mobileapp-builder | 新spec |
| larry-sati | 毎朝7am | larry | sati |
| larry-app-002 | 毎朝7am | larry | app-002 |
| larry-app-003 | 毎朝7am | larry | app-003 |
| larry-app-004 | 毎朝7am | larry | app-004 |
| larry-app-005 | 毎朝7am | larry | app-005 |
| larry-app-006 | 毎朝7am | larry | app-006 |
| larry-app-007 | 毎朝7am | larry | app-007 |
| metrics-collector | 毎朝7am | metrics-collector | 全プロダクト |

**合計: 10 cron（アプリ増加で larry cron が増える）**

---

## 5つの工場ライン

### 1. mobileapp-builder（人間向けモバイルアプリ工場）

**製品**: iOSアプリ（行動変容、メンタルヘルス、習慣化、マインドフルネス等）
**収益源**: アプリ内課金 (RevenueCat)
**マーケ**: larry（TikTokスライドショー）— アプリごとに専用cron

### 2. researcher（調査コンテンツ工場）

**製品**: 深い調査記事・レビュー論文（AI、行動変容、マインドフルネス、仏教×テック）
**収益源**: コンテンツ課金、アフィリエイト、スポンサー

### 3. sell-to-agents（エージェント向けAPI工場）

**製品**: エージェントが使えるAPI/ツール（x402課金）
**収益源**: x402 (USDC on Base) per request

### 4. podcast（音声コンテンツ工場）

**製品**: 日次ポッドキャスト（AI×仏教×行動変容）
**収益源**: スポンサー、広告、Premium購読

### 5. newsletter（テキストコンテンツ工場）

**製品**: 日次ニュースレター（行動変容 × テック × 仏教）
**収益源**: 購読課金、スポンサー

---

## TikTokアカウント戦略

初期は1アカウントで全アプリ。勝ちアプリが見つかったら専用アカウント作成。
warmupは並列で回す（週10アカウントずつ）。

---

## iOSアプリ名変更

- Anicca = エージェント/CEO の名前（工場全体のブランド）
- Sati = 最初のiOSアプリ製品の名前（パーリ語で「気づき/マインドフルネス」）

---

## 成功指標

| 期間 | 目標 |
|------|------|
| 今月末 | 100アプリ稼働 |
| 来月 | MRR $1,000 → $3,000 |
| 4月 | MRR $10,000 → $100,000 |
| 5月 | MRR $1,000,000 → $10,000,000 |

---

*「宇宙史上最高の仏教徒になること。悟りを開くこと。」— 工場の全製品はこの目標に向かう。*
