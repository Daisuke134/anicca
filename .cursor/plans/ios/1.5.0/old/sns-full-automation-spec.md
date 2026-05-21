# v1.5.0 SNS 完全自動化 Spec

**作成日**: 2026-01-27
**ステータス**: Draft
**バージョン**: 1.5.0

---

## 開発環境

| 項目 | 値 |
|------|-----|
| **ワークツリーパス** | `/Users/cbns03/Downloads/anicca-sns-poster` |
| **ブランチ** | `feature/sns-poster` |
| **ベースブランチ** | `dev` |
| **作業状態** | 計画中 → 実装待ち |
| **並列作業** | 1.5.0 main-spec（Track A/B）と同時進行。ファイル重複なし |

### 並列作業の安全性

| Worktree | 触るディレクトリ | コンフリクト |
|----------|----------------|------------|
| 1.5.0 Track A（クロスユーザー学習） | `apps/api/src/services/`, `apps/api/src/routes/`, `apps/api/src/jobs/` | なし |
| 1.5.0 Track B（TikTok投稿） | `apps/api/src/jobs/`, `apps/api/src/services/` | なし |
| **sns-poster**（本 Spec） | `.cursor/plans/ios/sns-poster/*.py`, `.github/workflows/` | **なし** |

**結論: 完全に独立。並列実行可能。**

### 1.5.0 main-spec との関係

| 項目 | main-spec（1.5.0） | sns-poster（本 Spec） |
|------|--------------------|-----------------------|
| 言語 | Node.js（バックエンド） | Python（スタンドアロン） |
| TikTok 投稿 | Hook候補ライブラリから選定 → Blotato 投稿 | Content Brain が全プラットフォーム向けコンテンツ生成 → Blotato 投稿 |
| 学習ループ | アプリ内 tap/👍👎 + TikTok like/share → wisdom 判定 | Analytics → Content Brain にフィードバック |
| 統合（Phase 5） | sns-poster の Content Brain が Anicca の Nudge 生成エンジンと統合 | main-spec の Hook 候補ライブラリと連携 |

---

## 概要

### 何を解決するか（What）

現在の SNS 投稿は **毎回人間が「投稿して」と指示しないと動かない**。Content Brain（アイデア生成）、メディア生成、投稿実行、スケジュール実行の4段階のうち、**前半2つが完全に手動**。

ReelFarm で TikTok スライドショーは自動化済みだが、**他プラットフォーム（IG/X/YouTube/Threads）は手動**。本 Spec で全プラットフォームを完全自動化し、ReelFarm に依存しない自前システムを構築する。

### なぜ必要か（Why）

- 毎日12アカウントに投稿する → 人間が毎日トリガーするのは持続不可能
- バズるコンテンツはトレンドに乗る必要がある → 人間の判断は遅い
- ReelFarm は TikTok のみ → 全プラットフォーム対応の自前システムが必要
- Anicca のプロアクティブエージェント技術の基盤になる（Phase 5 でアプリ統合）
- Cal AI は12アカウント + 1000本動画で $1M MRR → 量と自動化が命

### 成功事例（ベンチマーク）

| アプリ | 結果 | 戦略 | ソース |
|--------|------|------|--------|
| **Cal AI** | $1M MRR、700K DL/月 | TikTok 12アカウント、1000+動画、$5 CPM インフルエンサー | [growwithplutus.com](https://growwithplutus.com/blog/cal-ai-app-tiktok-strategy) |
| **TurboLearn** | $100K MRR、App Store Top 10 | マルチアカウント TikTok 戦略 | [growwithplutus.com](https://growwithplutus.com/blog/turbolearn-app-tiktok-strategy) |
| **Coconote AI** | 383M+ ビュー、$200K MRR | マルチアカウント戦略 | [growwithplutus.com](https://growwithplutus.com/blog/coconote-tiktok-strategy) |
| **Rayz AI** | $80K MRR（75日） | TikTok マーケティング最適化 | [shortimize.com](https://www.shortimize.com/blog/from-zero-to-80k-mrr-in-75-days-how-rayz-ai-mastered-tiktok-marketing) |

**Cal AI が最も参考になる。** Anicca と同じ構造：12アカウント運用、量で攻める。

---

## 受け入れ条件

| # | 条件 | テスト可能な形式 |
|---|------|-----------------|
| AC-1 | GitHub Actions cron が毎朝 00:00 UTC（09:00 JST）に自動実行される | cron ログで実行確認 |
| AC-2 | Content Brain が9アカウント分のコンテンツ（テキスト + 画像プロンプト）を JSON で生成する | 出力 JSON のバリデーション |
| AC-3 | Trend Scraper が Exa + Apify で自己改善/習慣化ニッチのトレンドデータを取得する | API レスポンスの確認 |
| AC-4 | Fal.ai で画像/動画を自動生成する | メディア URL の存在確認 |
| AC-5 | Blotato で全アカウントに 09:00 JST スケジュール投稿する | Blotato API レスポンスの確認 |
| AC-6 | 全工程が人間の介入なしで完了する | E2E 実行で手動ステップ 0 |
| AC-7 | 実行ログが `schedule_log.json` に記録される | ログファイルの内容確認 |
| AC-8 | エラー時に Slack/Discord 通知が飛ぶ | エラーハンドリングテスト |
| AC-9 | ReelFarm なしで TikTok 以外の全プラットフォームに投稿できる | Blotato 経由で投稿成功 |
| AC-10 | 全コンテンツが「苦しみ軽減」に統一されている（BIP 廃止） | Content Brain の出力に BIP なし |
| AC-11 | TikTok は新アカウント作成後に Phase 1 に追加可能 | config.py にアカウント追加で対応 |

---

## As-Is（現状）

### 自動化状況

| ステージ | 状態 | 担当 |
|---------|------|------|
| アイデア出し | **手動** | 人間が毎回考える |
| スクリプト作成 | **手動** | 人間がキャプション書く |
| 画像/動画生成 | **自動** | Fal.ai（FLUX, Ideogram, Kling, Seedance） |
| 投稿実行 | **自動** | Blotato（12アカウント接続済み） |
| スケジュール投稿 | **半自動** | Blotato で時間指定可能だが手動トリガー |
| 毎日の実行 | **手動** | cronなし。毎回「投稿して」と依頼 |
| トレンド調査 | **手動** | 何がバズるか調べてない |
| パフォーマンス分析 | **なし** | フィードバックループなし |
| TikTok スライドショー | **自動** | ReelFarm（TikTok のみ、既存2アカウント運用中 → 新システムとは分離） |

### 既存コード

| ファイル | 役割 | 再利用 |
|---------|------|--------|
| `blotato.py` | Blotato API ラッパー（全プラットフォーム対応） | ✅ そのまま |
| `fal_ai.py` | Fal.ai API ラッパー（画像/動画/音声生成） | ✅ そのまま |
| `config.py` | アカウント設定、APIキー | ✅ スロット時間を更新 |
| `post.py` | 単一投稿スクリプト | ✅ そのまま |
| `batch_post.py` | 複数プラットフォーム一括投稿 | ✅ そのまま |
| `schedule_log.json` | 投稿ログ | ✅ 構造は維持、スロット更新 |

### 参考にした既存ツール/ワークフロー

| ツール | 評価 | 採用 |
|--------|------|------|
| [n8n #5916](https://n8n.io/workflows/5916-viral-video-creator-falai-ai-videos-tiktok-youtube-and-instagram-automation/) | Fal.ai + Blotato パイプライン（まさに俺らのスタック） | ✅ 設計を参考 |
| [n8n #6918](https://n8n.io/workflows/6918-create-viral-social-media-videos-with-falai-fluxkling-and-gpt-4-automation/) | Flux→Kling→FFmpeg→60秒動画 | ✅ マルチシーン動画生成を参考 |
| [ShortGPT](https://github.com/RayVentura/ShortGPT) | スクリプト→素材→音声→字幕→レンダリング | 🟡 アーキテクチャ参考のみ（MoviePyベースで古い） |
| [OASIS](https://github.com/camel-ai/oasis) | SNSシミュレーター（研究用） | ❌ 使えない |
| ReelFarm | TikTok スライドショー自動化 | ❌ TikTokのみ。自前システムで置き換え |

**判断：n8n の設計を参考に Python で自作。** 理由：n8n は GUI で Claude Code から操作不可。Python なら Anicca に統合可能、GitHub Actions で無料稼働。

---

## To-Be（変更後の設計）

### 全体アーキテクチャ

```
GitHub Actions (cron: 00:00 UTC = 09:00 JST)
    │
    ▼
orchestrator.py（メインエントリポイント）
    │
    ├─→ trend_scraper.py    → Exa + Apify でトレンド + 競合フック取得
    │
    ├─→ content_brain.py    → OpenAI API でコンテンツ生成
    │                          入力: トレンド + ペルソナ + 過去データ + 4柱戦略
    │                          出力: 9アカウント分の JSON（TikTok 除外）
    │
    ├─→ media_generator.py  → Fal.ai で画像/動画生成（n8n #5916 式パイプライン）
    │                          3シーン並列生成 → FFmpeg 結合 → 9:16
    │
    ├─→ auto_poster.py      → Blotato で全アカウントに投稿
    │
    └─→ schedule_log.json   → 実行ログ記録
```

### 新規ファイル

| ファイル | 役割 |
|---------|------|
| `orchestrator.py` | 全体を繋ぐメインスクリプト。cron から呼ばれる |
| `content_brain.py` | OpenAI API でコンテンツ生成（アイデア + スクリプト + 画像プロンプト） |
| `trend_scraper.py` | Exa + Apify でトレンド・競合データ取得 |
| `media_generator.py` | Fal.ai 呼び出しのオーケストレーション（n8n #5916 式マルチシーン） |
| `auto_poster.py` | Blotato 呼び出しのオーケストレーション |
| `analytics_collector.py` | パフォーマンスデータ取得（Phase 2） |
| `.github/workflows/sns-daily.yml` | GitHub Actions cron 設定 |

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `config.py` | 全アカウントのスロットを `["09:00"]` に統一。Anthropic/Exa/Apify API キー追加 |
| `requirements.txt` | `anthropic`, `exa-py`, `apify-client` 追加 |
| `schedule_log.json` | スロット構造を新スケジュールに更新 |

---

## コンテンツ4柱戦略（Cal AI 式）

Cal AI は4種類のコンテンツフォーマットを12アカウントで回して $1M MRR を達成。Anicca に翻訳する：

| # | 柱 | Cal AI での例 | Anicca での例 |
|---|-----|-------------|-------------|
| 1 | **アプリデモ** | 食事写真スキャン → カロリー表示 | Anicca の通知 → NudgeCard → 行動変容 |
| 2 | **ストーリー/顔出し** | 創業者がダイエット語る | 「6年間何も変われなかった」挫折→希望の物語 |
| 3 | **テキスト動画（faceless）** | 機能紹介 + 字幕オーバーレイ | フック + 仏教的メッセージ + 字幕 |
| 4 | **Myth-busting / 比較** | 「習慣アプリは意味ない」を論破 | 「習慣アプリが全部失敗する本当の理由」 |

Content Brain は毎日この4柱をローテーションしてコンテンツを生成する。

---

## トレンド・フック検索ツール構成

| ツール | 用途 | 特徴 | コスト |
|--------|------|------|--------|
| **Exa** (既にMCP接続済み) | 意味検索（記事、分析、競合パターン） | ニューラル検索、LLM最適化 | 〜$50/月 |
| **Apify TikTok Scraper** | TikTok トレンド動画のフック・メトリクス抽出 | ビュー、いいね、シェア、フック分析 | 従量課金 |
| **TikTok Creative Center** | リアルタイムのバズ動画、ハッシュタグ | 無料、人口統計データ付き | 無料 |
| **Glimpse** | クロスプラットフォーム新興トレンド | Reddit/YouTube/TikTok/Pinterest 横断 | 無料〜 |

### なぜ Exa だけじゃ足りないか

| Exa が得意 | Exa が苦手（Apify が補完） |
|-----------|-------------------------|
| 記事検索、分析レポート | TikTok の具体的な動画メトリクス |
| 意味検索（概念で検索） | リアルタイムのビュー数、いいね数 |
| 競合の成功パターン記事 | 特定ハッシュタグのトップ動画のフック抽出 |

### Trend Scraper のデータフロー

```
Exa API ─────→ 「self improvement viral tiktok 2026」等で記事・分析を検索
                → バズパターン、成功フォーマット、競合戦略

Apify ────────→ TikTok トレンド動画の具体的メトリクス
                → ビュー数トップ動画のフック文、ハッシュタグ、エンゲージメント率

TikTok CC ───→ リアルタイムのトレンドハッシュタグ
                → 人口統計データ（25-35歳のエンゲージメント）

Glimpse ─────→ 新興トレンド（まだ飽和してないもの）
                → Reddit/YouTube で盛り上がり始めてるトピック

        ↓ 全部まとめて JSON

Content Brain に入力
```

---

## To-Be 詳細設計

### 1. `orchestrator.py`

```python
# シグネチャ
def main(dry_run: bool = False) -> None:
    """
    メインオーケストレーション。
    1. トレンド取得（Exa + Apify）
    2. 過去パフォーマンスデータ読み込み（あれば）
    3. コンテンツ生成（OpenAI API、4柱ローテーション）
    4. メディア生成（Fal.ai、n8n #5916 式マルチシーン）
    5. 投稿（Blotato、Phase 1 は9アカウント ※TikTok 除外）
    6. ログ記録（schedule_log.json）
    dry_run=True の場合、投稿せずに生成結果だけ出力。
    エラー時は通知して継続（1アカウント失敗でも他は投稿する）
    """

def notify_error(error: str, context: dict) -> None:
    """エラー通知（Slack webhook or Discord webhook）"""
```

### 2. `content_brain.py`

```python
# シグネチャ
@dataclass
class ContentPiece:
    account_key: str        # "x_aniccaxxx", "ig_anicca_ai", etc.
    platform: str           # "twitter", "instagram", "youtube", "threads", "pinterest"
    lang: str               # "EN" or "JP"
    pillar: str             # "demo" | "story" | "faceless" | "mythbust"
    hook: str               # "I snoozed my alarm for 6 years straight"
    caption: str            # フルキャプション
    image_prompt: str       # Fal.ai 用プロンプト
    hashtags: str           # "#habits #anicca"
    content_type: str       # "image" or "video"
    video_prompt: str | None  # 動画の場合のプロンプト
    scenes: list[str] | None  # マルチシーン動画の場合の各シーンプロンプト

def generate_daily_content(
    trends: TrendData,
    past_performance: dict | None,
    persona: str,
    pillar_rotation: str,
) -> list[ContentPiece]:
    """
    OpenAI API で対象アカウント分のコンテンツを一括生成（Phase 1: 9アカウント）。

    入力:
    - trends: Trend Scraper の出力（Exa + Apify）
    - past_performance: Analytics の出力（Phase 2、最初は None）
    - persona: Anicca ペルソナ定義
    - pillar_rotation: 今日のコンテンツ柱（4柱ローテーション）

    出力:
    - 12個の ContentPiece（各アカウント1個）
    """
```

**プロンプト設計（Content Brain の核）:**

```
System:
あなたは Anicca の SNS コンテンツ戦略家。
Cal AI（$1M MRR、12アカウント運用）の戦略を参考に、バズるコンテンツを生成する。

## ペルソナ（必ず従え）
ターゲット: 6-7年間、習慣化に失敗し続けている25-35歳
- 習慣アプリを10個以上試して全部3日坊主で挫折
- 「自分はダメな人間だ」と信じ込んでいる
- 諦めモードだが、心の奥では変わりたい

## コンテンツ4柱（今日の柱: {pillar}）
1. demo: アプリの機能を見せる（通知→NudgeCard→変化）
2. story: 挫折→希望の物語（「6年間何も変われなかった」系）
3. faceless: テキスト動画（フック + 仏教的メッセージ + 字幕）
4. mythbust: 「習慣アプリが全部失敗する本当の理由」系

## 刺さるフック（使え）
- 「6年間、何も変われなかった」
- 「習慣アプリ10個全部挫折した」
- 具体的な年数、回数、失敗の詳細
- 最初の1秒で止まるフック（ショート動画最重要）

## 禁止フック（絶対使うな）
- 「簡単に習慣化！」「たった○日で！」「誰でもできる！」
→ ターゲットはこれを信じない。警戒する。

## トレンドデータ（今日のバズネタ）
{trends}

## 過去のパフォーマンス（あれば）
バズったもの: {top_posts}
ダメだったもの: {flop_posts}
→ バズったフォーマットをもっと使え。ダメだったパターンは避けろ。

## プラットフォーム特性（必ず守れ）
- X: テキスト主役。痛烈な自己認識ツイート、逆説・気づき系、スレッドが武器。RTされる共感文。画像は補助
- Instagram: ビジュアル重視。保存されるコンテンツ。カルーセルも可
- YouTube Shorts: サムネ+タイトルが命。検索にも引っかかるように。縦型9:16
- Threads: カジュアルな語り口。共感ベース
- Pinterest: ビジュアル検索。保存される美しい画像+啓発テキスト

## コンテンツ統一方針
全アカウント「苦しみ軽減」コンテンツに統一。Build in Public（BIP）は廃止。
理由: Anicca のミッション=苦しみを終わらせること。ターゲットは開発者ではなく苦しんでいる人。

## 出力形式
12アカウント分の ContentPiece を JSON 配列で出力。
```

### 3. `trend_scraper.py`

```python
# シグネチャ
@dataclass
class TrendData:
    topics: list[str]              # バズってるトピック
    viral_hooks: list[str]         # バズってるフレーズ（Apify から）
    formats: list[str]             # バズってるフォーマット（字幕動画、比較等）
    hashtags: list[str]            # トレンドハッシュタグ
    competitor_posts: list[dict]   # 競合のトップ投稿（Exa から）
    tiktok_trending: list[dict]    # TikTok トレンド動画のメトリクス（Apify から）

def scrape_trends() -> TrendData:
    """
    複数ソースからトレンドデータを収集:

    1. Exa API:
       - "viral tiktok self improvement habits 2026" → バズコンテンツ
       - "tiktok hooks mental health procrastination" → 刺さるフック
       - "top mindfulness meditation tiktok accounts" → 競合分析
       - "習慣化 バズ SNS 2026" → 日本語トレンド

    2. Apify TikTok Scraper:
       - #selfimprovement #habits #mindfulness のトップ動画
       - ビュー数、いいね数、フック文を抽出

    3. Glimpse (optional):
       - 新興トレンド（まだ飽和してないもの）
    """
```

### 4. `media_generator.py`

```python
# シグネチャ（n8n #5916 式マルチシーンパイプライン）
def generate_media(content: ContentPiece) -> str:
    """
    ContentPiece に基づいてメディアを生成。

    n8n #5916 のパイプラインを Python で再実装:
    1. content.scenes がある場合 → マルチシーン動画
       a. 各シーンを並列で Fal.ai に投げる
       b. 音声も並列で生成（MMAudio v2）
       c. Fal.ai FFmpeg API で結合 → 9:16 最終動画
    2. content_type == "image" → Ideogram v3 or Nano Banana Pro
    3. content_type == "video"（単一シーン）→ Kling 2.5 Pro or Seedance

    戻り値: メディア URL
    """

def generate_multi_scene_video(scenes: list[str], audio_prompt: str) -> str:
    """
    n8n #6918 式: 複数シーン → 個別動画生成 → FFmpeg 結合
    → 60秒の完成動画 URL を返す
    """
```

### 5. `auto_poster.py`

```python
# シグネチャ
def post_all(contents: list[ContentPiece], media_urls: dict[str, str]) -> dict:
    """
    全アカウントに投稿。

    - 各アカウントの 09:00 JST スロットにスケジュール投稿
    - 失敗したアカウントはスキップして続行
    - 結果を schedule_log.json に記録

    戻り値: {account_key: {"success": bool, "post_id": str | None, "error": str | None}}
    """
```

### 6. `analytics_collector.py`（Phase 2）

```python
# シグネチャ
@dataclass
class PostPerformance:
    account_key: str
    platform: str
    post_id: str
    views: int
    likes: int
    shares: int
    comments: int
    saves: int          # Instagram のみ
    hook_text: str       # 使ったフック
    pillar: str          # どの柱のコンテンツか
    content_type: str

def collect_performance(days_back: int = 7) -> list[PostPerformance]:
    """
    過去 N 日間の投稿パフォーマンスを収集。

    TikTok → Apify TikTok Scraper で自分のアカウントのメトリクス取得
    Instagram → Meta Graph API / Blotato API

    イテレーション戦略:
    - Phase 2: X/IG/YouTube 分析開始 → TikTok 新アカウント追加後は TikTok ファースト
    - Phase 3: 全プラットフォーム分析 → 各プラットフォーム固有の最適化
    """

def get_top_and_flop(performances: list[PostPerformance]) -> dict:
    """
    トップ3 とワースト3 を抽出 → Content Brain にフィードバック
    """
```

### 7. GitHub Actions Cron

```yaml
# .github/workflows/sns-daily.yml
name: Daily SNS Auto Post
on:
  schedule:
    - cron: '0 0 * * *'  # 00:00 UTC = 09:00 JST
  workflow_dispatch: {}   # 手動実行も可能

env:
  BLOTATO_API_KEY: ${{ secrets.BLOTATO_API_KEY }}
  FAL_API_KEY: ${{ secrets.FAL_API_KEY }}
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  EXA_API_KEY: ${{ secrets.EXA_API_KEY }}
  APIFY_API_TOKEN: ${{ secrets.APIFY_API_TOKEN }}

jobs:
  post:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r .cursor/plans/ios/sns-poster/requirements.txt
      - name: Run orchestrator
        run: python .cursor/plans/ios/sns-poster/orchestrator.py
      - name: Upload log artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: sns-log-${{ github.run_number }}
          path: .cursor/plans/ios/sns-poster/schedule_log.json
```

---

## スケジュール設計

### 全アカウント統一: 09:00 JST

### Phase 1 対象（9アカウント）

| # | Platform | アカウント | 言語 | 投稿時間 | コンテンツ |
|---|----------|-----------|------|---------|-----------|
| 1 | X | @aniccaxxx | JP | 09:00 JST | 苦しみ軽減 |
| 2 | X | @aniccaen | EN | 09:00 JST | 苦しみ軽減 |
| 3 | IG | @anicca.ai | EN | 09:00 JST | 苦しみ軽減 |
| 4 | IG | @anicca.japan | JP | 09:00 JST | 苦しみ軽減 |
| 5 | IG | @anicca.daily | EN | 09:00 JST | 苦しみ軽減 |
| 6 | YouTube | Daisuke Narita | EN | 09:00 JST | 苦しみ軽減 |
| 7 | YouTube | @anicca.jp | JP | 09:00 JST | 苦しみ軽減 |
| 8 | Threads | @anicca.japan | JP | 09:00 JST | 苦しみ軽減 |
| 9 | Pinterest | @aniccaai | EN | 09:00 JST | 苦しみ軽減（認証待ち） |

### TikTok（Phase 1 除外 → 新アカウント作成後に追加）

| # | アカウント | 言語 | 状態 | 理由 |
|---|-----------|------|------|------|
| - | （新規作成予定） | JP | ⏳ 作成待ち | 既存 @anicca.japan は ReelFarm 運用中 |
| - | （新規作成予定） | EN | ⏳ 作成待ち | 既存 @anicca.ai, @anicca57 は ReelFarm 運用中 |

**既存 TikTok アカウント（ReelFarm 運用中 → 自動化対象外）:**
- `@anicca.ai` (EN) - ReelFarm でスライドショー投稿中
- `@anicca.japan` (JP) - ReelFarm でスライドショー投稿中
- `@anicca57` (EN) - ReelFarm でスライドショー投稿中

---

## コールドスタート戦略（データゼロからの開始）

### Phase 1: 外部データで学習（Day 1-14）

自分の投稿データがないため、**競合とトレンドデータのみ**で Content Brain を動かす。

| データソース | 取得方法 | 何を学ぶか |
|------------|---------|-----------|
| TikTok トレンド動画 | **Apify TikTok Scraper** | ニッチのトップ動画のフック、エンゲージメント |
| TikTok Creative Center | **Exa API** 経由で分析記事を取得 | フォーマット、ベストプラクティス |
| 競合アカウント | **Exa API** で検索 | バズったフック、キャプション構成 |
| バズ分析記事 | **Exa deep_research** | 「なぜバズったか」のパターン |
| 日本語トレンド | **Exa API** で日本語検索 | JP 市場のトレンド |
| 新興トレンド | **Glimpse** | まだ飽和してないトピック |

### Phase 2: 自分のデータ混合（Day 15-30）

各プラットフォームから自分の投稿パフォーマンスを取得開始。**TikTok 新アカウント追加後は TikTok ファーストで分析。**

| データ | 取得先 | Content Brain への入力 |
|--------|-------|----------------------|
| 再生数トップ3 | **Apify** で自アカウントスクレイプ | 「このフォーマットをもっと使え」 |
| 再生数ワースト3 | **Apify** | 「このパターンは避けろ」 |
| バズったフック | ログから抽出 | 「このフック構造を再利用しろ」 |
| 保存率 | Instagram Insights / Meta API | 「保存されるコンテンツの特徴」 |

### Phase 3: 自己最適化（Day 31+）

自分のデータが主。外部データは補助。フィードバックループ完成。

---

## イテレーション戦略

### Phase 1: 全プラットフォーム一斉投稿（TikTok 除外）

**9アカウントに毎日投稿。TikTok は新アカウント作成後に追加。**

```
Day 1〜: 9アカウント（X/IG/YouTube/Threads/Pinterest）に毎日自動投稿
    │
    ▼
Day 14〜: 各プラットフォームのパフォーマンスデータ収集開始
    │
    ├─→ IG: 保存率の高いコンテンツを分析 → ビジュアル最適化
    ├─→ X: RT率・いいね率の高い文体を分析 → テキスト最適化
    ├─→ YouTube: CTR + 平均視聴時間を分析 → サムネ + タイトル最適化
    └─→ Threads: エンゲージメント率を分析 → 語り口最適化
    │
    ▼
TikTok 新アカウント作成後: TikTok 追加 → TikTok ファースト分析に移行
    │
    ▼
TikTok で勝ちパターン発見 → 他プラットフォームに横展開
```

### なぜ TikTok ファーストは維持するか（新アカウント作成後）

| 理由 | 説明 |
|------|------|
| フォロワー0でもバズれる | TikTok アルゴリズムがコンテンツベース |
| フィードバックが最速 | 24時間以内に結果が出る |
| バイラル確率31.4倍 | Buffer 2026 データ |
| Cal AI もここから始めた | 12アカウント TikTok → $1M MRR |
| ReelFarm との完全分離 | 新アカウントなら干渉ゼロ |

---

## 実装後の UX（完全自動化の日常）

### ユーザーの日常（実装完了後）

**何もしなくていい。寝てる間に全部終わる。**

```
┌─────────────────────────────────────────────────────────────┐
│  あなたの1日（実装後）                                       │
│                                                             │
│  🌙 寝てる間（08:00 JST）                                   │
│  ├── GitHub Actions が自動起動                               │
│  ├── Trend Scraper: 今日のバズネタ収集（Exa + Apify）       │
│  ├── Content Brain: 12アカウント分のコンテンツ生成           │
│  ├── Media Generator: 画像/動画を Fal.ai で生成             │
│  └── Auto Poster: 09:00 JST に9アカウントにスケジュール     │
│                                                             │
│  ☀️ 起きたら（09:00+ JST）                                  │
│  ├── 9アカウントに投稿済み（TikTok は新アカウント追加後）      │
│  ├── Slack/Discord に実行レポート届いてる                    │
│  └── 何もしなくていい                                       │
│                                                             │
│  📊 たまに見る（週1くらい）                                  │
│  ├── TikTok のビュー数チェック                               │
│  ├── 「このフック良かったな」→ 自動でフィードバック済み      │
│  └── Content Brain が自動で学習して改善してる                │
│                                                             │
│  🎯 ReelFarm との違い                                       │
│  ├── ReelFarm: TikTok スライドショーのみ（既存アカウント）   │
│  ├── 自前システム: X + IG + YouTube + Threads + Pinterest   │
│  ├── ReelFarm: プロンプト手入力                              │
│  ├── 自前システム: トレンド自動取得 → 自動生成               │
│  └── TikTok: 新アカウント作成後に自前システムに追加          │
└─────────────────────────────────────────────────────────────┘
```

### 例：ある日の自動実行ログ

```
[2026-02-01 08:00:00 UTC] 🚀 SNS Orchestrator 起動
[2026-02-01 08:00:05 UTC] 📊 Trend Scraper 開始
  - Exa: "dopamine detox" がバズ中（+340% this week）
  - Apify: #selfimprovement トップ動画 "I quit my phone for 30 days" (2.3M views)
  - Glimpse: "micro habits" が新興トレンド
[2026-02-01 08:01:30 UTC] 🧠 Content Brain 生成開始（今日の柱: story）
  - JP x 4: 「6年間スマホをやめられなかった」系ストーリー（X/IG/YouTube/Threads）
  - EN x 5: "I tried 10 habit apps and they all failed" 系ストーリー（X/IG×2/YouTube/Pinterest）
  - トレンド "dopamine detox" を織り込み
[2026-02-01 08:03:00 UTC] 🎬 Media Generator 開始
  - IG/YouTube: Fal.ai Seedance で 9:16 動画生成（並列5本）
  - X: Nano Banana Pro で画像生成（並列2枚）+ テキスト重視キャプション
  - Threads: テキストのみ（メディア不要）
  - Pinterest: Nano Banana Pro で美しい画像生成
[2026-02-01 08:15:00 UTC] 📤 Auto Poster 開始
  - 9アカウントに 09:00 JST スケジュール投稿を設定
  - 全成功 ✅
[2026-02-01 08:15:30 UTC] 📝 ログ記録完了
[2026-02-01 08:15:31 UTC] 💬 Slack 通知: "本日の投稿完了。9/9 成功。"
```

### ReelFarm との比較

| 項目 | ReelFarm | 自前システム |
|------|---------|------------|
| 対応プラットフォーム | TikTok のみ | X + IG + YouTube + Threads + Pinterest（9アカウント、TikTok 追加予定） |
| コンテンツ形式 | スライドショーのみ | 画像、動画、テキスト、マルチシーン動画 |
| アイデア出し | 人間がプロンプト入力 | Content Brain が自動生成 |
| トレンド反映 | なし | Exa + Apify で自動取得 |
| フィードバックループ | なし | Analytics → Content Brain 自動改善 |
| コスト | 月額課金 | GitHub Actions 無料 + API 従量課金 |
| カスタマイズ | 制限あり | 完全自由（Python） |

→ **ReelFarm の上位互換。** 全プラットフォーム対応 + 自動トレンド反映 + 自動改善ループ。

---

## Anicca プロダクトとの統合ビジョン（Phase 5）

### 短期：sns-poster は Anicca の実験場

sns-poster で作った技術は、そのまま Anicca アプリに統合する。

| sns-poster で作るもの | Anicca での転用 |
|---------------------|----------------|
| Content Brain（LLM でコンテンツ生成） | Nudge 生成エンジンの強化 |
| Trend Scraper（外部データ取得） | ユーザーの「今」に合わせた Nudge |
| Analytics Loop（効果測定 → 改善） | Nudge 効果測定 + A/B テスト |
| ペルソナベース生成 | 個別ユーザーへのパーソナライゼーション |

### 長期：Anicca がプロアクティブに苦しみにリーチする

**最終形**: Anicca 自体が SNS 投稿エージェントとして機能する。

```
Anicca = Proactive Agent（苦しみを終わらせるエージェント）
    │
    ├── 対ユーザー（アプリ内）
    │   ├── パーソナライズ Nudge（既存: LLMNudgeService）
    │   ├── DeepDive セッション
    │   └── 行動変容トラッキング
    │
    └── 対世界（SNS = アプリ外）← Phase 5 で統合
        ├── Content Brain がトレンドに合わせてコンテンツ生成
        ├── 苦しんでる人にプロアクティブにリーチ
        ├── 「6年間何も変われなかった」に共感するコンテンツ
        └── アプリ内 Nudge と SNS コンテンツが同じ知性から生まれる
```

**なぜ sns-poster を Anicca の中に作るのか：**
- 同じ AI 脳（Content Brain）がアプリ内 Nudge と SNS 投稿の両方を担当
- 同じペルソナ理解を共有
- 同じ Analytics ループで改善
- 無駄ゼロ。全てが Anicca のプロダクトになる

---

## To-Be チェックリスト

| # | To-Be | 必須 |
|---|-------|------|
| 1 | `orchestrator.py` が全工程を自動実行する | ✅ |
| 2 | `content_brain.py` が OpenAI API で9アカウント分の「苦しみ軽減」コンテンツを4柱で生成する | ✅ |
| 3 | `trend_scraper.py` が Exa + Apify でトレンド + 競合データを取得する | ✅ |
| 4 | `media_generator.py` が Fal.ai で画像/動画を n8n #5916 式で生成する | ✅ |
| 5 | `auto_poster.py` が Blotato で全アカウントに投稿する | ✅ |
| 6 | `config.py` のスロットが全アカウント 09:00 JST に統一される | ✅ |
| 7 | GitHub Actions cron が毎日 00:00 UTC に実行される | ✅ |
| 8 | `schedule_log.json` に実行結果が記録される | ✅ |
| 9 | エラー時に通知が飛ぶ | ✅ |
| 10 | `requirements.txt` に `anthropic`, `exa-py`, `apify-client` が追加される | ✅ |
| 11 | MacBook 不要で動く（GitHub Actions 完結） | ✅ |
| 12 | ReelFarm なしで TikTok 以外の全プラットフォーム自動投稿できる | ✅ |
| 13 | コンテンツ4柱が定義されローテーションする | ✅ |
| 14 | 全コンテンツが「苦しみ軽減」に統一（BIP 廃止） | ✅ |
| 15 | TikTok 新アカウント（JP/EN）を作成し config.py に追加 | ⏳ ユーザー作業 |
| 16 | `analytics_collector.py` が各プラットフォームのパフォーマンスを取得する | Phase 2 |
| 17 | フィードバックループが自動で Content Brain を改善する | Phase 2 |
| 18 | 各プラットフォーム固有のイテレーション | Phase 3 |

---

## テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|-------|----------|--------|
| 1 | Content Brain が JSON 出力する | `test_content_brain_output_format` | ✅ |
| 2 | Content Brain が9アカウント分生成する（TikTok 除外） | `test_content_brain_all_accounts` | ✅ |
| 3 | Content Brain が禁止フック使わない | `test_content_brain_no_banned_hooks` | ✅ |
| 4 | Content Brain が4柱をローテーションする | `test_content_brain_pillar_rotation` | ✅ |
| 5 | Trend Scraper が Exa + Apify から TrendData 返す | `test_trend_scraper_multi_source` | ✅ |
| 6 | Media Generator が URL 返す（画像） | `test_media_generator_image` | ✅ |
| 7 | Media Generator がマルチシーン動画を生成する | `test_media_generator_multi_scene` | ✅ |
| 8 | Auto Poster が全アカウントに投稿する | `test_auto_poster_all_accounts` | ✅ |
| 9 | Orchestrator が E2E で動く（dry-run） | `test_orchestrator_e2e_dry_run` | ✅ |
| 10 | エラー時に通知が飛ぶ | `test_error_notification` | ✅ |
| 11 | schedule_log.json が更新される | `test_log_update` | ✅ |

---

## 境界（Boundaries）

### やること

- Content Brain（OpenAI API + 4柱戦略でコンテンツ生成）
- Trend Scraper（Exa + Apify + Glimpse でトレンド取得）
- Media Generator（Fal.ai、n8n #5916 式マルチシーンパイプライン）
- Orchestrator（全工程を繋ぐ）
- GitHub Actions cron（毎日自動実行）
- スケジュール統一（全アカウント 09:00 JST）
- TikTok 以外のプラットフォームで ReelFarm に依存しない自動投稿を実現
- 全コンテンツを「苦しみ軽減」に統一（BIP 廃止）

### やらないこと

- iOS アプリのコード変更（sns-poster は Python 独立モジュール）
- API サーバー（`apps/api/`）への変更
- Pinterest 認証（別途メールで対応）
- 有料広告運用（Cal AI 式 Phase 2 で検討）
- インフルエンサー管理（Cal AI 式 Phase 3 で検討）
- 複数回/日投稿（1アカウント1回/日で統一）
- 既存 TikTok アカウントへの投稿（ReelFarm 運用中のため Phase 1 除外）
- Build in Public コンテンツ（苦しみ軽減に統一）

### 触るファイル

```
.cursor/plans/ios/sns-poster/
├── orchestrator.py        （新規）
├── content_brain.py       （新規）
├── trend_scraper.py       （新規）
├── media_generator.py     （新規）
├── auto_poster.py         （新規）
├── analytics_collector.py （新規 - Phase 2）
├── config.py              （変更）
├── requirements.txt       （変更）
├── schedule_log.json      （変更）
└── tests/                 （新規）
    ├── test_content_brain.py
    ├── test_trend_scraper.py
    ├── test_media_generator.py
    ├── test_auto_poster.py
    └── test_orchestrator.py

.github/workflows/
└── sns-daily.yml          （新規）
```

### 触らないファイル

- `aniccaios/` （iOS アプリ全体）
- `apps/api/` （バックエンド）
- `apps/landing/` （ランディングページ）
- 既存の `.github/workflows/` ファイル

---

## 実行手順

### Phase 1: コア実装

```bash
# 1. 依存関係追加
cd .cursor/plans/ios/sns-poster
pip install anthropic exa-py apify-client

# 2. Trend Scraper 実装 + テスト
python -c "from trend_scraper import scrape_trends; print(scrape_trends())"

# 3. Content Brain 実装 + テスト
python -c "from content_brain import generate_daily_content; ..."

# 4. Media Generator 実装（n8n #5916 式）
python -c "from media_generator import generate_media; ..."

# 5. Orchestrator 実装 + E2E テスト
python orchestrator.py --dry-run  # 投稿せずに生成結果だけ確認

# 6. 本番実行（初回）
python orchestrator.py

# 7. GitHub Actions 設定
# .github/workflows/sns-daily.yml 作成
# GitHub Secrets に API キー追加
```

### Phase 2: Analytics + フィードバックループ

```bash
# TikTok パフォーマンスデータ取得
python analytics_collector.py

# Content Brain にフィードバック
python orchestrator.py  # 自動で過去データを読み込む
```

### Phase 3: 全プラットフォームイテレーション

```bash
# 各プラットフォーム固有の分析 → 最適化
python analytics_collector.py --platform tiktok
python analytics_collector.py --platform instagram
python analytics_collector.py --platform twitter
python analytics_collector.py --platform youtube
```

---

## ユーザー作業（実装前）

| # | タスク | 手順 | 取得するもの | 優先度 |
|---|--------|------|-------------|--------|
| **S0** | **TikTok 新アカウント作成（EN）** | **TikTok アプリ → 新規作成 → Blotato に接続** | **Blotato Account ID** | **最優先（実装前に必要）** |
| S1 | OpenAI API キーをローテーション | OpenAI Dashboard → API Keys → 新キー生成 → 古いキー無効化 | 新しい `OPENAI_API_KEY` | 最優先（セキュリティ） |
| S2 | Exa API キー取得 | https://exa.ai → API Key | `EXA_API_KEY`（取得済み） | 高 |
| S3 | GitHub Secrets 設定 | GitHub → Settings → Secrets → Actions → 4つのキーを追加 | GitHub Actions で使える環境変数 | 高（cron 動かす時） |
| S4 | Apify API トークン取得 | https://apify.com → Settings → API Token | `APIFY_API_TOKEN` | 低（Phase 2 で使用） |
| S5 | TikTok 新アカウント作成（JP） | TikTok アプリ → 新規作成 → Blotato に接続 | Blotato Account ID | 低（EN 動作確認後） |

## ユーザー作業（実装中）

| # | タイミング | タスク | 理由 |
|---|-----------|--------|------|
| 1 | 初回 dry-run 後 | 生成コンテンツを確認 | Content Brain の品質チェック |
| 2 | 初回本番実行後 | SNS で投稿を確認 | 自動テスト不可（外部サービス） |

## ユーザー作業（実装後）

| # | タスク | 確認項目 |
|---|--------|---------|
| 1 | 翌朝 09:00 JST 確認 | 9アカウントに投稿されてるか |
| 2 | GitHub Actions ログ確認 | cron が正常実行されたか |
| 3 | 週1でパフォーマンス確認 | 各プラットフォームのエンゲージメント推移 |
| 4 | TikTok 新アカウント作成後 | config.py にアカウント追加 → 自動投稿対象に追加 |

---

## Skills / Sub-agents 使用マップ

| ステージ | 使用するもの | 用途 |
|---------|-------------|------|
| Spec 作成 | `/plan` | 実装計画の作成 |
| 実装 | 直接実装（Python） | TDD は過剰（スクリプト系） |
| コードレビュー | `/code-review` | 実装後のレビュー |
| ビルドエラー | `/build-fix` | エラー発生時の修正 |
| Spec/コードレビュー | `/codex-review` | 自動レビューゲート |

---

## レビューチェックリスト

- [ ] 全 To-Be がテストマトリックスに含まれているか
- [ ] 受け入れ条件がテスト可能な形式か
- [ ] 設計（シグネチャ、データモデル）が明確か
- [ ] 境界（やらないこと）が定義されているか
- [ ] 後方互換性は保たれているか（→ N/A: 新規機能）
- [ ] As-Is の問題が To-Be で解決されるか
- [ ] GitHub Actions secrets が必要なキーを網羅しているか
- [ ] MacBook 不要で動くか（GitHub Actions 完結）
- [ ] コンテンツ4柱が明確に定義されているか
- [ ] トレンド取得が複数ソース（Exa + Apify）で構成されているか
- [ ] Anicca 統合ビジョンが Phase 5 として明記されているか

---

## リスクと緩和策

| リスク | 影響 | 緩和策 |
|--------|------|--------|
| OpenAI API のレート制限 | コンテンツ生成失敗 | リトライ + フォールバックテンプレート |
| Fal.ai タイムアウト | メディア生成失敗 | 5分タイムアウト + 前日のメディア再利用 |
| Blotato API ダウン | 投稿失敗 | エラー通知 + 手動投稿フォールバック |
| Exa API 制限 | トレンドデータなし | キャッシュ（前日のトレンドを再利用） |
| Apify クレジット不足 | TikTok データ取得失敗 | Exa のみで続行（品質低下は許容） |
| GitHub Actions cron の遅延 | 09:00 より遅れる | ±15分は許容。Blotato のスケジュール投稿で吸収 |
| コンテンツ品質の低下 | エンゲージメント低下 | Analytics フィードバックループ（Phase 2） |
| TikTok の反スクレイピング対策 | Apify が使えなくなる | 公式 TikTok Business API に切り替え |

---

## 実装タスクリスト

### Phase 1: コア実装（sns-poster Worktree）

| # | タスク | 担当 | 内容 |
|---|--------|------|------|
| **S0** | **TikTok EN アカウント作成** | **ユーザー** | **TikTok 新規作成 → Blotato 接続 → ID 共有** |
| S1 | Worktree 作成 | エージェント | `git worktree add ../anicca-sns-poster -b feature/sns-poster` |
| S2 | config.py に TikTok EN 追加 | エージェント | S0 で取得した ID を ACCOUNTS に追加 |
| S3 | Content Brain 実装 | エージェント | OpenAI API で 10 アカウント分コンテンツ生成 |
| S4 | Trend Scraper 実装 | エージェント | Exa API でトレンド取得 |
| S5 | Media Generator 実装 | エージェント | Fal.ai マルチシーンパイプライン |
| S6 | Auto Poster 実装 | エージェント | Blotato で全アカウントに投稿 |
| S7 | Orchestrator 実装 | エージェント | 全工程を繋ぐ + dry-run テスト |
| S8 | GitHub Actions cron | エージェント | `.github/workflows/sns-daily.yml` |
| S9 | TikTok JP アカウント作成 | ユーザー | EN 動作確認後 |

### Phase ロードマップ

| Phase | タスク | ゴール |
|-------|--------|--------|
| **Phase 1** | Content Brain + Trend Scraper + Orchestrator + cron | 完全自動投稿が毎日動く |
| **Phase 2** | Analytics Collector + フィードバックループ | データで自動改善 |
| **Phase 3** | 各プラットフォーム固有のイテレーション | 全プラットフォームで最適化 |
| **Phase 4** | Cal AI 式インフルエンサー戦略 | 勝ちクリエイティブ → 有料広告転用 |
| **Phase 5** | Anicca アプリとの統合 | Content Brain = Nudge 生成エンジン（main-spec と統合） |

---

## 参考リンク

- [Cal AI TikTok Strategy](https://growwithplutus.com/blog/cal-ai-app-tiktok-strategy) - $1M MRR の12アカウント戦略
- [n8n Viral Video Creator](https://n8n.io/workflows/5916-viral-video-creator-falai-ai-videos-tiktok-youtube-and-instagram-automation/) - Fal.ai + Blotato パイプライン
- [n8n Fal.ai Flux/Kling](https://n8n.io/workflows/6918-create-viral-social-media-videos-with-falai-fluxkling-and-gpt-4-automation/) - マルチシーン動画生成
- [Apify TikTok Trending](https://apify.com/simpleapi/tiktok-trending-videos-insights) - TikTok トレンドスクレイパー
- [Glimpse](https://meetglimpse.com/) - クロスプラットフォームトレンド発見
- [ShortGPT](https://github.com/RayVentura/ShortGPT) - アーキテクチャ参考
- [Buffer 2026 Social Media Report](https://buffer.com/resources/ai-social-media-content-creation/) - 投稿頻度ベストプラクティス

---

最終更新: 2026-01-27（並列Worktree計画追加、OpenAI統一、S0=TikTok EN作成、main-spec連携明記、タスクリスト追加）
