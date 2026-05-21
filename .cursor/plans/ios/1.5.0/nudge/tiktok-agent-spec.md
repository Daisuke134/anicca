# 1.5.0 TikTokエージェント設計

> **関連Spec**: [main-spec.md](./main-spec.md)（本体）、[db-schema-spec.md](./db-schema-spec.md)（DB）
>
> **最終更新**: 2026-01-28
>
> **目的**: Aniccaがアプリの外（TikTok）で人々の苦しみを減らし、その結果から学んで賢くなる

---

## 目次

1. [アーキテクチャ概要](#1-アーキテクチャ概要)
2. [エージェント設計](#2-エージェント設計)
3. [ツール定義](#3-ツール定義)
4. [エージェントフロー](#4-エージェントフロー)
5. [メトリクス取得ジョブ](#5-メトリクス取得ジョブ)
6. [学習フェーズ](#6-学習フェーズ)
7. [GitHub Actions設定](#7-github-actions設定)
8. [既存コード再利用](#8-既存コード再利用)
9. [制限・禁止事項](#9-制限禁止事項)
10. [ユーザーGUI作業](#10-ユーザーgui作業)

---

## 1. アーキテクチャ概要

### 1.1 パイプラインではなくエージェント

**Aniccaは「ツールを持ったプロアクティブAIエージェント」。** パイプライン（スクリプトが順番に実行される）ではない。

| 項目 | パイプライン（❌） | エージェント（✅） |
|------|------------------|-------------------|
| 判断 | 各スクリプトが機械的に次に渡す | LLMが結果を見て次の行動を決める |
| やり直し | 不可（一方向） | 可能（画像が気に入らなければ再生成） |
| 学習 | 統計的集計のみ | 推論 + 統計（「昨日はstrictが効いた。今日も試そう」） |
| 柔軟性 | 固定フロー | 状況に応じて行動を変える |

### 1.2 全体構成

```
GitHub Actions cron (00:00 UTC = 09:00 JST)
    │
    ▼
anicca_tiktok_agent.py（= Aniccaが目を覚ます）
    │
    └── LLMエージェントループ
        ├── get_yesterday_performance() → 昨日の結果を確認
        ├── get_hook_candidates() → 何が効いているか分析
        ├── search_trends() → トレンドを調べる
        ├── [LLMが投稿内容を決定]
        ├── generate_image() → 画像生成
        ├── evaluate_image() → 品質評価（不満なら再生成）
        ├── post_to_tiktok() → 投稿
        └── save_post_record() → 記録

═══════════ 別cron ═══════════

fetch_metrics.py（24時間後に実行、機械的ジョブ）
    │
    ├── Apify (clockworks/tiktok-scraper) でメトリクス取得
    ├── tiktok_posts テーブル更新
    └── hook_candidates テーブル更新
```

### 1.3 なぜ2つに分かれるか

| 部分 | Aniccaの判断必要？ | 理由 |
|------|-------------------|------|
| 何を投稿するか | ✅ | 創造的思考が必要 |
| 画像生成・評価 | ✅ | 品質判断が必要 |
| メトリクス取得 | ❌ | 数字をDBに書くだけ（機械的） |

---

## 2. エージェント設計

### 2.1 System Prompt

```
あなたはAnicca。人間の苦しみを減らすプロアクティブAIエージェント。

## あなたの使命
アプリの外（TikTok）で人々の苦しみを減らすNudgeを毎日投稿する。
投稿して、結果を見て、学んで、明日もっと良い投稿をする。

## あなたのペルソナ理解
ターゲット: 6-7年間、習慣アプリを10個以上試して全部挫折した25-35歳。
「自分はダメだ」と信じ込んでいる。でも心のどこかでは変わりたい。

## 刺さるHookの特徴
- 「6年間、何も変われなかった」
- 「習慣アプリ10個全部挫折」
- 「また3時まで起きてた？」
- 挫折経験を直接指摘する短い文

## 避けるHook（ターゲットが警戒する）
- 「簡単に習慣化！」
- 「たった○日で！」
- 「誰でもできる！」

## 今日やること
1. 昨日の投稿の成績を確認する（get_yesterday_performance）
2. hook_candidatesから何が効いているか分析する（get_hook_candidates）
3. トレンドを調べる（search_trends）
4. 今日の投稿内容を決める（Hook + キャプション + 画像プロンプト）
5. 画像を生成する（generate_image）
6. 画像を評価する（evaluate_image）— 不満なら作り直す（最大3回）
7. 投稿する（post_to_tiktok）
8. 記録する（save_post_record）

## 制約
- 画像は1枚のみ（動画は後）
- 言語は英語
- 罪悪感を煽る表現は禁止
- 「簡単に習慣化！」系の嘘Hookは禁止
- ビュー数最大化に寄せない（煽りに走る危険）

## 思考の例
「昨日のstrict × 命令形は like率 11% だった。良い。
でも share率 は 2% で低い。刺さったけど人に見せたいレベルではない。
今日は "POV:" 形式を試してみよう。共感を入れてshareを狙う。
トレンドを見ると "30 day challenge" 系が伸びている。
これとペルソナを組み合わせて...」
```

### 2.2 LLMモデル

| 項目 | 設定 |
|------|------|
| モデル | `gpt-4o` |
| Temperature | 0.7（創造性を持たせる） |
| Max tokens | 4096 |
| Tool choice | `auto` |

### 2.3 安全制限

| 制限 | 値 | 理由 |
|------|-----|------|
| ツール呼び出し上限 | 20回/セッション | 無限ループ防止 |
| 画像再生成上限 | 3回 | コスト制御 |
| セッション時間上限 | 10分 | GitHub Actions timeout |
| 投稿しない判断 | 許可 | 品質が低ければ投稿しない選択もある |

---

## 3. ツール定義

### 3.1 get_yesterday_performance

| 項目 | 内容 |
|------|------|
| 目的 | 昨日のTikTok投稿の成績を取得 |
| 入力 | なし |
| 出力 | `{ posts: [{ caption, view_count, like_count, share_count, comment_count, like_rate, share_rate, posted_at }] }` |
| 実装 | API経由: `GET {API_BASE_URL}/api/admin/tiktok/recent-posts?days=1` |
| エラー時 | 空配列を返す（Day 1は昨日のデータなし） |

### 3.2 get_hook_candidates

| 項目 | 内容 |
|------|------|
| 目的 | hook_candidatesテーブルから成績データを読む |
| 入力 | `{ limit?: number, sort_by?: "app_tap_rate" | "tiktok_like_rate" | "exploration_weight" }` |
| 出力 | `{ candidates: [{ text, tone, app_tap_rate, app_thumbs_up_rate, tiktok_like_rate, tiktok_share_rate, is_wisdom, exploration_weight }] }` |
| 実装 | API経由: `GET {API_BASE_URL}/api/admin/hook-candidates` |
| エラー時 | 空配列を返す |

### 3.3 search_trends

| 項目 | 内容 |
|------|------|
| 目的 | Exa APIでトレンドや競合パターンを検索 |
| 入力 | `{ query: string }` |
| 出力 | `{ results: [{ title, url, snippet, published_date }] }` |
| 実装 | Exa API: `POST https://api.exa.ai/search` |
| 検索例 | `"viral tiktok self improvement 2026"`, `"habits failure relatable content tiktok"` |
| エラー時 | 空配列を返す（トレンドなしでも投稿は可能） |

### 3.4 generate_image

| 項目 | 内容 |
|------|------|
| 目的 | Fal.aiで画像を1枚生成 |
| 入力 | `{ prompt: string, model?: "ideogram" | "nano_banana" }` |
| 出力 | `{ image_url: string }` |
| 実装 | Fal.ai: **`fal-ai/ideogram/v3`**（デフォルト）または `fal-ai/nano-banana-pro` |
| 画像仕様 | 9:16 TikTok縦型、テキストオーバーレイ含む |
| コスト | ~$0.02/画像（Ideogram v3） |
| エラー時 | エラーメッセージを返す（エージェントがプロンプトを変えて再試行可能） |

**モデル選択の根拠**: `flux/schnell`はテキスト描画精度が低い。TikTokのHook付き画像にはテキスト描画に強い`ideogram/v3`を採用。`nano-banana-pro`（Gemini 2.5 Flash）はフォールバック。既存 `fal_ai.py` に両メソッドが実装済み。

### 3.5 evaluate_image

| 項目 | 内容 |
|------|------|
| 目的 | 生成した画像の品質を評価 |
| 入力 | `{ image_url: string, intended_hook: string }` |
| 出力 | `{ quality_score: number (1-10), issues: string[], recommendation: "post" | "regenerate" | "skip" }` |
| 実装 | OpenAI Vision API（gpt-4o）で画像を分析 |
| 評価基準 | テキスト可読性、ブランド一貫性、感情的インパクト、TikTokフォーマット適合性 |
| エラー時 | `{ quality_score: 5, issues: ["evaluation_failed"], recommendation: "post" }`（フォールバック: 投稿する） |

### 3.6 post_to_tiktok

| 項目 | 内容 |
|------|------|
| 目的 | Blotato経由でTikTokに画像を投稿 |
| 入力 | `{ image_url: string, caption: string, hashtags: string[] }` |
| 出力 | `{ success: boolean, post_id: string, blotato_post_id: string }` |
| 実装 | Blotato API: `POST https://backend.blotato.com/v2/posts` |
| アカウント | TikTok EN: @anicca.self（Blotato Account ID: 28152） |
| エラー時 | エラーメッセージを返す。エージェントは投稿を諦める判断ができる |

### 3.7 save_post_record

| 項目 | 内容 |
|------|------|
| 目的 | 投稿をtiktok_postsテーブルに記録 |
| 入力 | `{ hook_candidate_id?: string, blotato_post_id: string, caption: string, agent_reasoning?: string }` |
| 出力 | `{ success: boolean, record_id: string }` |
| 実装 | API経由: `POST {API_BASE_URL}/api/admin/tiktok/posts` |
| エラー時 | エラーメッセージを返す（投稿自体は成功している場合あり） |

**注意**: `tiktok_video_id` は投稿時には不明（Blotatoが返すのは `blotato_post_id` のみ）。`tiktok_video_id` は翌日の `fetch_metrics.py` で Apify結果と照合して UPDATE する。`agent_reasoning` にはエージェントの思考過程（なぜこのHook/トーンを選んだか）を保存し、翌日の `get_yesterday_performance` で参照可能にする。

---

## 4. エージェントフロー

### 4.1 疑似コード

```python
import openai

SYSTEM_PROMPT = """..."""  # 2.1のSystem Prompt

TOOLS = [...]  # 3.1-3.7の7ツール

MAX_TOOL_CALLS = 20
MAX_IMAGE_RETRIES = 3

def run_anicca_agent():
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "新しい日が始まった。昨日の結果を振り返り、今日のTikTok投稿を作って。"}
    ]

    tool_call_count = 0

    while tool_call_count < MAX_TOOL_CALLS:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=TOOLS,
            temperature=0.7,
        )

        choice = response.choices[0]
        messages.append(choice.message)

        # エージェントが「完了」と判断した
        if choice.finish_reason == "stop":
            print("Anicca: 今日の作業完了")
            break

        # ツール呼び出しを実行
        if choice.message.tool_calls:
            for tool_call in choice.message.tool_calls:
                tool_call_count += 1
                result = execute_tool(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result)
                })

    if tool_call_count >= MAX_TOOL_CALLS:
        print("WARNING: ツール呼び出し上限到達")


def execute_tool(tool_call):
    """各ツールの実際のAPI呼び出し"""
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    if name == "get_yesterday_performance":
        return fetch_yesterday_performance()
    elif name == "get_hook_candidates":
        return fetch_hook_candidates(args.get("limit", 20), args.get("sort_by", "app_tap_rate"))
    elif name == "search_trends":
        return search_exa(args["query"])
    elif name == "generate_image":
        return generate_fal_image(args["prompt"])
    elif name == "evaluate_image":
        return evaluate_with_vision(args["image_url"], args.get("intended_hook", ""))
    elif name == "post_to_tiktok":
        return post_via_blotato(args["image_url"], args["caption"], args.get("hashtags", []))
    elif name == "save_post_record":
        return save_to_db(args)
    else:
        return {"error": f"Unknown tool: {name}"}
```

### 4.2 典型的なツール呼び出し順序

```
1. get_yesterday_performance()     ← 昨日の結果確認
2. get_hook_candidates()           ← 何が効いているか
3. search_trends("self improvement tiktok 2026")  ← トレンド調査
4. [LLMが思考して投稿内容を決定]
5. generate_image("...")           ← 画像生成
6. evaluate_image("...", "...")    ← 品質評価
7a. → "post" → post_to_tiktok()  ← 投稿
7b. → "regenerate" → generate_image() に戻る（最大3回）
7c. → "skip" → 今日は投稿しない
8. save_post_record()              ← 記録
```

**ただしこの順序はLLMの判断で変わりうる。** トレンドを2回調べることもあるし、画像を3回作り直すこともある。

### 4.3 エラーハンドリング

| エラー | エージェントの振る舞い |
|--------|---------------------|
| Exa API失敗 | トレンドなしで投稿（hook_candidatesのデータだけで判断） |
| Fal.ai失敗 | プロンプトを変えて再試行（最大3回）→ 全失敗なら今日は投稿しない。失敗理由は `save_post_record` の `agent_reasoning` に記録 |
| evaluate_image 3回リジェクト | 今日は投稿しない。全3回の `quality_score` と `issues` を `agent_reasoning` に記録 |
| Blotato失敗 | 投稿諦め。`agent_reasoning` に記録 |
| DB API失敗 | 投稿自体は成功の場合あり。`agent_log.json`（ローカル）に記録。GitHub Actionsのartifactとして保存 |
| OpenAI API失敗 | セッション終了。GitHub Actionsが失敗通知（Actions標準のemail/Slack通知） |

---

## 5. メトリクス取得ジョブ

**エージェントではない。機械的なcronジョブ。**

### 5.1 fetch_metrics.py

```python
# 毎日実行（GitHub Actions cron）
# 24時間以上経過した投稿のメトリクスを取得

def fetch_metrics():
    # 1. メトリクス未取得の投稿を取得
    pending_posts = api.get("/api/admin/tiktok/posts?metrics_pending=true")

    # 2. Apifyでメトリクスを取得
    apify_client = ApifyClient(os.environ["APIFY_API_TOKEN"])
    run = apify_client.actor("clockworks/tiktok-scraper").call(
        run_input={
            "profiles": ["@anicca.self"],
            "profileScrapeSections": ["videos"],
            "resultsPerPage": 30,
        }
    )

    # 3. Apify結果をリストに集約
    scraped_videos = []
    for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
        scraped_videos.append({
            "video_id": item["id"],
            "caption": item.get("text", ""),
            "create_time": item["createTimeISO"],
            "view_count": item["playCount"],
            "like_count": item["diggCount"],
            "share_count": item["shareCount"],
            "comment_count": item["commentCount"],
        })

    # 4. tiktok_video_id が未設定の投稿を照合
    #    照合戦略: posted_at ± 2時間 かつ caption 部分一致（最初の30文字）
    for post in pending_posts:
        if post.get("tiktok_video_id"):
            # 既にvideo_id があるならメトリクスのみ更新
            match = next((v for v in scraped_videos if v["video_id"] == post["tiktok_video_id"]), None)
        else:
            # video_id 未設定 → caption + 時刻で照合
            match = match_by_caption_and_time(post, scraped_videos)

        if match:
            api.put(f"/api/admin/tiktok/posts/{post['id']}/metrics", {
                "tiktok_video_id": match["video_id"],
                "view_count": match["view_count"],
                "like_count": match["like_count"],
                "share_count": match["share_count"],
                "comment_count": match["comment_count"],
            })

    # 5. hook_candidatesのTikTok成績を更新
    api.post("/api/admin/hook-candidates/refresh-tiktok-stats")


def match_by_caption_and_time(post, scraped_videos, time_window_hours=2):
    """posted_at ± time_window_hours かつ caption先頭30文字一致で照合"""
    from datetime import datetime, timedelta, timezone

    post_time = datetime.fromisoformat(post["posted_at"].replace("Z", "+00:00"))
    caption_prefix = (post.get("caption") or "")[:30]

    for video in scraped_videos:
        video_time = datetime.fromisoformat(video["create_time"].replace("Z", "+00:00"))
        time_diff = abs((video_time - post_time).total_seconds())

        if time_diff <= time_window_hours * 3600:
            video_caption_prefix = (video.get("caption") or "")[:30]
            if caption_prefix and video_caption_prefix and caption_prefix == video_caption_prefix:
                return video
    return None
```

**tiktok_video_id 照合の根拠**: Blotato APIは投稿後にTikTokネイティブIDを返さない。Apify TikTok Scraperの出力に `id`（ネイティブ）と `createTimeISO` があるため、`posted_at` ± 2時間 + caption先頭30文字一致で照合する。照合成功後は `tiktok_video_id` をDBに永続化し、以降は直接IDマッチで高速化。

### 5.2 Apify Actor設定

| 項目 | 値 |
|------|-----|
| Actor | `clockworks/tiktok-scraper` |
| 入力 | `{"profiles": ["@anicca.self"], "profileScrapeSections": ["videos"], "resultsPerPage": 30}` |
| 出力フィールド | `playCount`(view), `diggCount`(like), `shareCount`, `commentCount`, `id`(video_id), `createTimeISO` |
| コスト | ~$5/月（1日1回実行） |

### 5.3 hook_candidates更新ロジック

```javascript
// fetch後にhook_candidatesを更新するAPIエンドポイント
// POST /api/admin/hook-candidates/refresh-tiktok-stats

// 各hook_candidateについて:
// 1. tiktok_postsからそのhook_candidate_idの投稿を集計
// 2. like_rate = Σlike_count / Σview_count
// 3. share_rate = Σshare_count / Σview_count
// 4. sample_size = 投稿数
// 5. tiktok_high_performer = like_rate > 0.10 AND share_rate > 0.05 AND sample_size >= 5
// 6. is_wisdom = app_tap_rate > 0.50 AND app_thumbs_up_rate > 0.60 AND tiktok_high_performer
```

---

## 5.5 Admin APIコントラクト（Track B バックエンド）

**認証**: 全エンドポイントに `requireInternalAuth()` ミドルウェア適用（`INTERNAL_API_TOKEN` ヘッダー検証）。

**実装場所**: `apps/api/src/routes/admin/tiktok.js`, `apps/api/src/routes/admin/hookCandidates.js`

**ルート登録**: `apps/api/src/routes/index.js` に `/admin` プレフィックスで追加。

### EP-1: GET /api/admin/tiktok/recent-posts

| 項目 | 内容 |
|------|------|
| 用途 | 直近N日間のTikTok投稿と成績を取得（エージェントの `get_yesterday_performance` ツール用） |
| パラメータ | `?days=1`（デフォルト1） |
| レスポンス | `{ posts: [{ id, caption, posted_at, view_count, like_count, share_count, comment_count, like_rate, share_rate, agent_reasoning }] }` |
| 計算フィールド | `like_rate = like_count / view_count`、`share_rate = share_count / view_count`（view_count=0なら0） |
| データなし時 | `{ posts: [] }`（Day 1は空。エージェントは空でも動作可能） |

### EP-2: GET /api/admin/hook-candidates

| 項目 | 内容 |
|------|------|
| 用途 | Hook候補一覧を取得（エージェントの `get_hook_candidates` ツール用） |
| パラメータ | `?limit=20&sort_by=app_tap_rate` |
| レスポンス | `{ candidates: [...], meta: { currentPhase: 1|2|3, totalCandidates: N } }` |
| Phase判定 | Phase 1: `metrics_fetched_at IS NOT NULL` < 10件、Phase 2: 10-29件、Phase 3: 30件以上 かつ `tiktok_sample_size >= 3` が5件以上 |

### EP-3: POST /api/admin/tiktok/posts

| 項目 | 内容 |
|------|------|
| 用途 | 投稿記録を保存（エージェントの `save_post_record` ツール用） |
| リクエスト | `{ hook_candidate_id?: string, blotato_post_id: string, caption: string, agent_reasoning?: string }` |
| レスポンス | `{ success: true, record_id: "uuid" }` |
| バリデーション | `caption` 必須、`blotato_post_id` 必須 |

### EP-4: PUT /api/admin/tiktok/posts/:id/metrics

| 項目 | 内容 |
|------|------|
| 用途 | メトリクス更新（`fetch_metrics.py` 用） |
| リクエスト | `{ tiktok_video_id?: string, view_count: number, like_count: number, share_count: number, comment_count: number }` |
| レスポンス | `{ success: true }` |
| 副作用 | `metrics_fetched_at = NOW()` を自動設定。`tiktok_video_id` が渡されたらUPDATE |

### EP-5: GET /api/admin/tiktok/posts?metrics_pending=true

| 項目 | 内容 |
|------|------|
| 用途 | メトリクス未取得の投稿を取得（`fetch_metrics.py` 用） |
| フィルタ | `metrics_fetched_at IS NULL AND posted_at < NOW() - INTERVAL '20 hours'`（投稿後20時間以上経過） |
| レスポンス | `{ posts: [{ id, caption, posted_at, tiktok_video_id, blotato_post_id }] }` |

### EP-6: POST /api/admin/hook-candidates/refresh-tiktok-stats

| 項目 | 内容 |
|------|------|
| 用途 | tiktok_posts からhook_candidatesのTikTok成績を再計算（`fetch_metrics.py` の最後に呼ぶ） |
| 処理 | 各hook_candidateの `tiktok_like_rate`, `tiktok_share_rate`, `tiktok_sample_size`, `tiktok_high_performer`, `is_wisdom` を再計算 |
| レスポンス | `{ success: true, updated: N }` |

---

## 6. 学習フェーズ

### 6.1 3段階の学習

| Phase | 期間 | データソース | System Promptへの追加情報 |
|-------|------|-------------|-------------------------|
| **1（コールドスタート）** | Day 1-14 | hook_candidatesのアプリ内データ + Exaトレンド | アプリで効いたHook一覧 + 「TikTokデータはまだない」 |
| **2（混合）** | Day 15-30 | 自分のTikTokデータ + アプリ + トレンド | 昨日の成績 + トップ/ワーストパターン |
| **3（自己最適化）** | Day 31+ | 自分のデータが主 | 蓄積された全パターン + wisdom |

### 6.2 Phase遷移の判断

| 遷移 | 条件 | 判定SQL |
|------|------|---------|
| Phase 1 → 2 | `tiktok_posts` に `metrics_fetched_at IS NOT NULL` のレコードが10件以上 | `SELECT COUNT(*) FROM tiktok_posts WHERE metrics_fetched_at IS NOT NULL` |
| Phase 2 → 3 | `tiktok_posts` に `metrics_fetched_at IS NOT NULL` が30件以上 **かつ** `hook_candidates` に `tiktok_sample_size >= 3` が5件以上 | 2クエリの AND 条件 |

**判定タイミング**: エージェント起動時に `get_hook_candidates` ツールのレスポンスに `current_phase: 1|2|3` を含める。Phase判定はAPI側（Node.js）で行い、エージェントはその値を受け取る。

### 6.3 エージェントへのデータ提供方式

System Promptに事前注入**しない**。エージェントがツール（`get_hook_candidates`, `get_yesterday_performance`）を自分で呼んで判断する。Phase情報はツールのレスポンスに含まれるため、エージェントは「今日はPhase 1だからトレンド重視で行こう」と自律的に判断できる。

---

## 7. GitHub Actions設定

### 7.1 anicca-daily-post.yml

```yaml
name: Anicca Daily TikTok Post
on:
  schedule:
    - cron: '0 0 * * *'  # 00:00 UTC = 09:00 JST
  workflow_dispatch: {}    # 手動実行可能

env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  BLOTATO_API_KEY: ${{ secrets.BLOTATO_API_KEY }}
  FAL_API_KEY: ${{ secrets.FAL_API_KEY }}
  EXA_API_KEY: ${{ secrets.EXA_API_KEY }}
  API_BASE_URL: ${{ secrets.API_BASE_URL }}
  API_AUTH_TOKEN: ${{ secrets.API_AUTH_TOKEN }}

jobs:
  post:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r scripts/anicca-agent/requirements.txt
      - name: Run Anicca Agent
        run: python scripts/anicca-agent/anicca_tiktok_agent.py
      - name: Upload log
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: anicca-agent-log-${{ github.run_id }}
          path: scripts/anicca-agent/agent_log.json
```

### 7.2 fetch-metrics.yml

```yaml
name: Fetch TikTok Metrics
on:
  schedule:
    - cron: '0 1 * * *'  # 01:00 UTC = 10:00 JST（投稿の約25時間後に実行）
  workflow_dispatch: {}

env:
  APIFY_API_TOKEN: ${{ secrets.APIFY_API_TOKEN }}
  API_BASE_URL: ${{ secrets.API_BASE_URL }}
  API_AUTH_TOKEN: ${{ secrets.API_AUTH_TOKEN }}

jobs:
  fetch:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r scripts/anicca-agent/requirements.txt
      - name: Fetch Metrics
        run: python scripts/anicca-agent/fetch_metrics.py
```

### 7.3 GitHub Secrets一覧

| Secret Name | 用途 | 取得元 |
|-------------|------|--------|
| `OPENAI_API_KEY` | エージェントLLM + Vision | platform.openai.com |
| `BLOTATO_API_KEY` | TikTok投稿 | Blotato Dashboard |
| `FAL_API_KEY` | 画像生成 | fal.ai Dashboard |
| `EXA_API_KEY` | トレンド検索 | exa.ai Dashboard |
| `APIFY_API_TOKEN` | メトリクス取得 | apify.com Settings |
| `API_BASE_URL` | バックエンドAPI | Railway Staging URL |
| `API_AUTH_TOKEN` | API認証 | 既存トークン |

---

## 8. 既存コード再利用

### 8.1 再利用可能なファイル

| 既存ファイル | 再利用先 | 用途 |
|-------------|---------|------|
| `.cursor/plans/ios/sns-poster/blotato.py` | `tools/post_to_tiktok.py` | BlotatoClient、投稿ロジック |
| `.cursor/plans/ios/sns-poster/fal_ai.py` | `tools/generate_image.py` | Fal.ai画像生成（FLUX Schnell） |
| `.cursor/plans/ios/sns-poster/config.py` | `anicca_tiktok_agent.py` | アカウントID、API設定 |

### 8.2 新規作成ファイル

```
scripts/anicca-agent/
├── anicca_tiktok_agent.py      ← エージェント本体
├── fetch_metrics.py            ← メトリクス取得ジョブ
├── tools/
│   ├── __init__.py
│   ├── search_trends.py        ← Exa API
│   ├── hook_candidates.py      ← API経由DB読み取り
│   ├── generate_image.py       ← Fal.ai
│   ├── evaluate_image.py       ← OpenAI Vision
│   ├── post_to_tiktok.py       ← Blotato（blotato.py流用）
│   └── save_record.py          ← API経由DB書き込み
├── requirements.txt
└── agent_log.json              ← 実行ログ（自動生成）
```

### 8.3 requirements.txt

```
openai>=1.0.0
requests>=2.31.0
python-dotenv>=1.0.0
apify-client>=1.0.0
```

---

## 9. 制限・禁止事項

### 9.1 Phase 1制限

| 制限 | 理由 |
|------|------|
| 画像1枚のみ（動画・スライド禁止） | 制限 = 革新。まず1つのフォーマットで勝つ |
| TikTok EN 1アカウントのみ | 学習ループ確立が先。拡張は後 |
| 英語のみ | ターゲットペルソナの言語 |
| 1日1投稿 | 品質 > 量 |

### 9.2 禁止事項

| 禁止 | 理由 |
|------|------|
| ビュー数最大化に寄せる | 煽りに走る危険 |
| 罪悪感を煽る表現 | 「苦しみを減らす」の反対 |
| 自動スクロール/自動いいね | TikTok規約違反リスク |
| 「簡単に習慣化！」系のHook | ターゲットが警戒する嘘Hook |

### 9.3 将来の拡張パス

| ステップ | 条件 | アクション |
|---------|------|-----------|
| Phase 1 → スライドショー | 画像1枚で勝ちパターン確立 | media_generatorを拡張 |
| Phase 1 → 動画 | スライドで効果確認 | Fal.ai動画生成追加 |
| TikTok EN → TikTok JP | EN で like率 > 10% 安定 | 新アカウント追加 |
| TikTok → X | TikTokで勝ちパターン確立 | Blotato X投稿追加（Free tier） |
| TikTok → 全9アカウント | 2プラットフォームで安定 | 段階的に追加 |

---

## 10. ユーザーGUI作業

### 10.1 実装前（必須）

| # | タスク | 手順 | 取得するもの | 設定先 |
|---|--------|------|-------------|--------|
| 1 | Apifyアカウント作成 | [apify.com](https://apify.com) → Sign up → Settings → API Token | `APIFY_API_TOKEN` | GitHub Secrets |
| 2 | Apify Actor動作確認 | Apify Store → `clockworks/tiktok-scraper` → @anicca.selfで検索テスト | 動作確認 | — |
| 3 | Exa API Key取得 | [exa.ai](https://exa.ai) → Dashboard → API Keys | `EXA_API_KEY` | GitHub Secrets |
| 4 | Fal.ai API Key確認 | [fal.ai](https://fal.ai) → Dashboard → Keys | `FAL_API_KEY` | GitHub Secrets |
| 5 | OpenAI API Key確認 | [platform.openai.com](https://platform.openai.com) → API Keys | `OPENAI_API_KEY` | GitHub Secrets |
| 6 | Blotato API Key確認 | Blotato Dashboard → Settings → API | `BLOTATO_API_KEY` | GitHub Secrets |
| 7 | GitHub Secrets全登録 | GitHub → anicca-project → Settings → Secrets → Actions → 上記全てを登録 | — | — |
| 8 | TikTokアカウント確認 | @anicca.self がBlotato（ID: 28152）に接続されていることを確認 | 接続ステータス | — |

### 10.2 実装後

| # | タスク | 確認項目 |
|---|--------|---------|
| 1 | GitHub Actions動作確認 | anicca-daily-post が手動実行で成功するか |
| 2 | TikTok投稿確認 | @anicca.self に投稿が表示されるか |
| 3 | メトリクス取得確認 | 24時間後に fetch-metrics が成功するか |
| 4 | 1週間後に学習確認 | hook_candidates の tiktok_* カラムが更新されているか |

---

---

## 11. 実装判断メモ（2026-01-28 確定）

### 11.1 画像生成モデル

| 項目 | 決定 |
|------|------|
| **方針** | `fal-ai/ideogram/v3` をデフォルト、`fal-ai/nano-banana-pro` をフォールバック |
| **根拠** | `flux/schnell` はテキスト描画精度が低い。TikTokのHook付き画像にはテキスト可読性が必須。既存 `fal_ai.py` に両メソッド実装済み |

### 11.2 tiktok_video_id 照合戦略

| 項目 | 決定 |
|------|------|
| **方針** | `posted_at ± 2時間` + `caption先頭30文字一致` で照合。照合成功後は `tiktok_video_id` をDBに永続化 |
| **根拠** | Blotato APIはTikTokネイティブIDを返さない。Apify出力には `id` + `createTimeISO` + `text` があるため、時刻+キャプションで一意照合可能 |

### 11.3 agent_reasoning 永続化

| 項目 | 決定 |
|------|------|
| **方針** | `agent_log.json`（GitHub Actions artifact）ではなく、`tiktok_posts.agent_reasoning` カラムに保存 |
| **根拠** | GitHub Actionsのartifactは翌日のエージェントから自動参照不可。DBに保存すれば `get_yesterday_performance` で取得可能 |

### 11.4 hook_candidates 初期データ不足時のフォールバック

| 項目 | 決定 |
|------|------|
| **方針** | `initHookLibrary.js` で既存データからの抽出が5件未満の場合、ペルソナベースの手動シードデータ（20件）をINSERT |
| **根拠** | `HAVING COUNT(*) >= 5` で十分なHookが抽出できない可能性がある。エージェントのDay 1から `hook_candidates` が空だと学習ループが始まらない |

**シードデータ例（ペルソナ直結）**:

| text | tone | target_problem_types |
|------|------|---------------------|
| "6年間、何も変われなかった" | strict | {self_loathing, procrastination} |
| "習慣アプリ10個全部挫折" | provocative | {procrastination, staying_up_late} |
| "また3時まで起きてた？" | strict | {staying_up_late, cant_wake_up} |
| "10個目の習慣アプリ、今度は何日もつ？" | provocative | {procrastination, self_loathing} |
| "自分との約束、また破った？" | gentle | {self_loathing, lying} |

### 11.5 initHookLibrary.js 実行タイミング

| 項目 | 決定 |
|------|------|
| **方針** | Track B 実装完了後、リリース前に1回手動実行（`node apps/api/src/scripts/initHookLibrary.js`） |
| **根拠** | マイグレーション時には `nudge_events` のデータが必要。自動実行にするとCI/CDで不要な実行が発生する |

### 11.6 セキュリティ: タイミングセーフトークン比較

| 項目 | 決定 |
|------|------|
| **方針** | `requireInternalAuth.js` のトークン比較を `crypto.timingSafeEqual()` に変更 |
| **根拠** | `===` 比較はタイミング攻撃に脆弱。Admin APIはTikTok投稿とDB書き込みを制御するため、セキュリティは必須 |
| **追加対策** | `/api/admin/*` ルートに `express-rate-limit`（10 req/min）を適用 |

### 11.7 GitHub Actions並行実行防止

| 項目 | 決定 |
|------|------|
| **方針** | `concurrency: { group: "anicca-daily-post", cancel-in-progress: false }` をワークフローに追加 |
| **根拠** | 手動dispatch + cron同時実行でダブル投稿のリスク |
| **追加対策** | `save_post_record` API側で `posted_at >= CURRENT_DATE` の既存レコードチェック。当日投稿済みなら409 Conflict |

### 11.8 video_id照合の堅牢化

| 項目 | 決定 |
|------|------|
| **方針** | caption正規化（ハッシュタグ除去、trim、lowercase） + prefix 50文字 + 複数マッチ時はスキップ |
| **根拠** | Blotatoがcaptionを変形する可能性、同日重複投稿の可能性 |

### 11.9 Admin API入力バリデーション

| フィールド | 制約 | 根拠 |
|-----------|------|------|
| caption | <= 2200文字 | TikTokの文字数上限 |
| agent_reasoning | <= 10000文字 | LLMの冗長出力防止 |
| view_count等メトリクス | 0 <= x <= 1,000,000,000 | Apifyデータ破損防止 |
| blotato_post_id | <= 100文字 | VARCHAR(100)と整合 |

### 11.10 Fal.ai画像URL時限切れ対策

| 項目 | 決定 |
|------|------|
| **方針** | 画像生成直後にBlotato `upload_media(url)` で永続URLに変換。投稿時は永続URLを使用 |
| **根拠** | Fal.ai生成URLは1-24時間で失効。Blotato投稿がキューに入る場合、URLが切れて投稿失敗のリスク |

### 11.11 fetch_metrics.py の堅牢化

| 項目 | 決定 |
|------|------|
| **方針** | `try/finally` ブロックで `refresh-tiktok-stats` を必ず呼ぶ。EP-6はidempotent設計 |
| **根拠** | 途中クラッシュでhook_candidatesが古いまま → エージェントが古いデータで判断するリスク |

### 11.12 TikTok静止画投稿

| 項目 | 決定 |
|------|------|
| **方針** | Blotato API経由で画像1枚をTikTokに投稿（フォト投稿モード） |
| **根拠** | TikTokは2023年からフォト投稿対応。Blotato既存コード `post_to_tiktok()` で `mediaUrls` に画像URLを渡せば動作する。Phase 1では画像のみ、Phase 2以降でスライドショー→動画に拡張 |

---

*このSpecは1.5.0 TikTokエージェントの実装を定義する。*
*main-spec.md と db-schema-spec.md と合わせて参照すること。*
