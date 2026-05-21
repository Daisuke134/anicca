# 1.6.2 実装仕様書: コンテンツNudge品質向上 + Skills移行

> **RFC 2119 準拠**: MUST, SHOULD, MAY を使用
> **最終更新**: 2026-02-03

---

## 1. 目標

| 項目 | 目標 |
|------|------|
| **X フォロワー** | 今月末までに 100 |
| **TikTok フォロワー** | 今月末までに 100 |
| **コンテンツ品質** | 検証ループで score >= 7/10 のみ投稿 |
| **インフラ** | GitHub Actions → OpenClaw Skills 完全移行 |

---

## 2. 現在の実装状況（As-Is）

### 2.1 GitHub Actions（移行対象）

| Workflow | 機能 | スケジュール |
|----------|------|-------------|
| `anicca-x-post.yml` | X投稿 | 08:50/20:50 JST |
| `anicca-daily-post.yml` | TikTok投稿 | TBD |
| `cross-post-tiktok-to-ig.yml` | TikTok→IG | 15:00/01:00 JST |
| `fetch-x-metrics.yml` | Xメトリクス収集 | 10:00 JST |
| `fetch-tiktok-metrics.yml` | TikTokメトリクス収集 | TBD |

### 2.2 現在のX投稿フロー

```
scripts/x-agent/anicca_x_agent.py

1. Commander Agent が xPosts を生成済み（別プロセス）
2. GET /api/admin/x/pending?slot=morning|evening
3. Blotato API で即時投稿
4. POST /api/admin/x/posts で記録保存

問題点:
- 品質チェックなし（生成されたら即投稿）
- 学習ループなし（何が効くかわからない）
- GitHub Actions 依存（ログ分散、失敗検知困難）
```

### 2.3 既存 API エンドポイント

| エンドポイント | 用途 | 状態 |
|---------------|------|------|
| `POST /api/agent/content` | コンテンツ生成 | ✅ 実装済み |
| `POST /api/agent/nudge` | Nudge生成 | ✅ 実装済み |
| `POST /api/agent/feedback` | フィードバック更新 | ✅ 実装済み |
| `GET /api/agent/wisdom` | Wisdom取得 | ✅ 実装済み |
| `GET /api/admin/x/pending` | 保留X投稿取得 | ✅ 実装済み |
| `POST /api/admin/x/posts` | X投稿記録 | ✅ 実装済み |

---

## 3. To-Be アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OpenClaw VPS (24/7)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  schedule.yaml                                                               │
│  ├─ x-poster:        cron "0 9,21 * * *" (09:00, 21:00 JST)                 │
│  ├─ tiktok-poster:   cron "0 9,21 * * *" (09:00, 21:00 JST)                 │
│  ├─ trend-hunter:    interval "4h"                                           │
│  ├─ feedback-fetch:  interval "4h"                                           │
│  └─ suffering-detector: interval "5m" (Moltbook/Slack)                       │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                         SKILLS                                      │     │
│  │                                                                     │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │     │
│  │  │  x-poster    │  │tiktok-poster │  │ trend-hunter │              │     │
│  │  │              │  │              │  │              │              │     │
│  │  │ • フック選定 │  │ • フック選定 │  │ • X検索      │              │     │
│  │  │ • 生成      │  │ • 生成      │  │ • Reddit検索 │              │     │
│  │  │ • 検証      │  │ • 検証      │  │ • フック抽出 │              │     │
│  │  │ • 投稿      │  │ • 投稿      │  │ • 保存       │              │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │     │
│  │                                                                     │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │     │
│  │  │feedback-fetch│  │ suffering-  │  │  review-     │              │     │
│  │  │              │  │  detector   │  │  responder   │              │     │
│  │  │ • X API     │  │              │  │              │              │     │
│  │  │ • TikTok    │  │ • Moltbook  │  │ • App Store  │              │     │
│  │  │ • Z-Score   │  │ • Slack     │  │ • 返信生成   │              │     │
│  │  │ • 昇格      │  │ • Nudge     │  │ • 通知       │              │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │     │
│  │                                                                     │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │     │
│  │  │content-      │  │     Nia     │  │  wisdom-     │              │     │
│  │  │ syndicator  │  │              │  │  researcher  │              │     │
│  │  │              │  │ • 仏教文献  │  │              │              │     │
│  │  │ • X         │  │ • 論文      │  │ • Nia検索    │              │     │
│  │  │ • TikTok    │  │ • インデックス│ │ • Wisdom生成│              │     │
│  │  │ • Reddit    │  │              │  │              │              │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                      │                                       │
│                                      ↓ ANICCA_AGENT_TOKEN                   │
└──────────────────────────────────────┼───────────────────────────────────────┘
                                       │
                                       ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Railway API                                     │
│  /api/agent/content | /api/agent/nudge | /api/agent/feedback                │
│  /api/agent/wisdom  | /api/admin/x/posts | hook_candidates                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 完全タスクリスト

### カテゴリA: GitHub Actions → Skills 移行 + コンテンツ質向上（P0）

| # | タスク | 詳細 | AC（完了条件） |
|---|--------|------|----------------|
| A1 | **x-poster Skill 作成** | フック選定 → 生成 → 検証 → 投稿 | VPS `/home/anicca/openclaw/skills/x-poster/` に配置、手動実行で投稿成功 |
| A2 | **tiktok-poster Skill 作成** | 同上、TikTok向け | VPS に配置、手動実行で投稿成功 |
| A3 | **テキスト検証機能** | LLMで score >= 7 判定、3回まで再生成 | 検証ログが出力される |
| A4 | **画像検証機能** | Vision LLMで score >= 7 判定 | 検証ログが出力される |
| A5 | **schedule.yaml 更新** | x-poster, tiktok-poster を 09:00/21:00 JST に設定 | `openclaw schedule list` で確認 |
| A6 | **GitHub Actions 無効化** | `anicca-x-post.yml`, `anicca-daily-post.yml` を無効化 | GHAが実行されない |

### カテゴリB: 苦しみ検出 + 応答（P1）

| # | タスク | 詳細 | AC（完了条件） |
|---|--------|------|----------------|
| B1 | **suffering-detector Skill** | Moltbook/Slack でキーワード検出 → Nudge | m/endingsuffering 投稿に返信成功 |
| B2 | **review-responder Skill** | App Store レビュー検出 → 返信ドラフト | Slack に通知届く |

### カテゴリC: トレンド + コンテンツ配信（P1）

| # | タスク | 詳細 | AC（完了条件） |
|---|--------|------|----------------|
| C1 | **trend-hunter Skill** | X/Reddit トレンド監視 → フック抽出 | hook_candidates に新規レコード追加 |
| C2 | **content-syndicator Skill** | 1フック → 複数プラットフォーム配信 | X + Reddit に同時投稿成功 |

### カテゴリD: Nia統合（P1）

| # | タスク | 詳細 | AC（完了条件） |
|---|--------|------|----------------|
| D1 | **Nia Skill インストール** | `clawhub install arlanrakh/nia@v1.0.2` | `clawhub list` で表示 |
| D2 | **仏教文献インデックス** | accesstoinsight.org, dhammatalks.org | `nia sources list` で表示 |
| D3 | **心理学論文インデックス** | arXiv 4本 | `nia sources list` で表示 |
| D4 | **wisdom-researcher Skill** | Nia検索 → Wisdom生成 | 引用付きWisdomが返る |

### カテゴリE: 学習ループ（P1）

| # | タスク | 詳細 | AC（完了条件） |
|---|--------|------|----------------|
| E1 | **feedback-fetch 拡張** | X/TikTokエンゲージメント収集追加 | agent_posts.likes 等が更新 |
| E2 | **Z-Score 計算** | X/TikTok の Z-Score 計算 | agent_posts.xZ, tiktokZ が計算される |
| E3 | **hook_candidates 昇格** | 高スコアNudge → 昇格 | hook_candidates に新規レコード |

---

## 5. 詳細設計

### 5.1 x-poster Skill

**場所:** `/home/anicca/openclaw/skills/x-poster/`

**ファイル構成:**
```
x-poster/
├── skill.yaml       # Skill定義
├── main.py          # メインロジック
├── verifier.py      # 検証ロジック
└── config.py        # 設定
```

**skill.yaml:**
```yaml
name: x-poster
description: Post wisdom content to X/Twitter with quality verification
version: 1.0.0

triggers:
  schedule:
    cron:
      - "0 0 * * *"   # 09:00 JST (UTC+9)
      - "0 12 * * *"  # 21:00 JST (UTC+9)
    timezone: "Asia/Tokyo"

env:
  - ANICCA_AGENT_TOKEN
  - ANICCA_PROXY_BASE_URL
  - BLOTATO_API_KEY
  - X_ACCOUNT_ID
  - OPENAI_API_KEY

outputs:
  - agent_post_id
  - blotato_post_id
  - text_score
  - image_score
```

**main.py:**
```python
"""
x-poster Skill — Post to X with quality verification

Flow:
1. Select best hook from hook_candidates
2. Generate text content via /api/agent/content
3. Verify text quality (score >= 7, max 3 attempts)
4. Generate image via fal (optional)
5. Verify image quality (score >= 7, max 3 attempts)
6. Post via Blotato API
7. Save to agent_posts via /api/agent/feedback (new post)
8. Notify Slack
"""
import os
import json
import requests
from datetime import datetime, timezone, timedelta

from verifier import verify_text, verify_image

# Config
API_BASE_URL = os.environ["ANICCA_PROXY_BASE_URL"]
AGENT_TOKEN = os.environ["ANICCA_AGENT_TOKEN"]
BLOTATO_API_KEY = os.environ["BLOTATO_API_KEY"]
BLOTATO_BASE_URL = "https://api.blotato.com/v2"
X_ACCOUNT_ID = os.environ["X_ACCOUNT_ID"]
FAL_API_KEY = os.environ.get("FAL_API_KEY", "")

JST = timezone(timedelta(hours=9))
MAX_VERIFICATION_ATTEMPTS = 3
MIN_SCORE = 7


def api_get(path, params=None):
    """GET request to Railway API."""
    url = f"{API_BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {AGENT_TOKEN}"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_post(path, data):
    """POST request to Railway API."""
    url = f"{API_BASE_URL}{path}"
    headers = {"Authorization": f"Bearer {AGENT_TOKEN}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=data, timeout=60)
    resp.raise_for_status()
    return resp.json()


def select_hook():
    """Select the best hook from hook_candidates."""
    # Get high-performing hooks that haven't been used recently
    candidates = api_get("/api/agent/wisdom", params={"limit": 10})
    if not candidates.get("hooks"):
        raise Exception("No hooks available")
    
    # Sort by unified_score and pick the best unused one
    hooks = sorted(candidates["hooks"], key=lambda h: h.get("unifiedScore", 0), reverse=True)
    return hooks[0]


def generate_content(hook):
    """Generate content via /api/agent/content."""
    result = api_post("/api/agent/content", {
        "topic": hook["content"],
        "problemType": hook.get("problemType", "procrastination"),
        "tone": "gentle",
        "language": "ja",
    })
    return result


def generate_image(text):
    """Generate image via fal API."""
    if not FAL_API_KEY:
        return None
    
    prompt = f"""
Create a warm, minimalist illustration for this message:
"{text[:200]}"

Style: Soft colors, simple shapes, calming, no text in image.
"""
    # fal API call
    resp = requests.post(
        "https://fal.run/fal-ai/flux/dev",
        headers={"Authorization": f"Key {FAL_API_KEY}"},
        json={"prompt": prompt, "image_size": "square_hd"},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json().get("images", [{}])[0].get("url")


def blotato_post(text, image_url=None):
    """Post to X via Blotato API."""
    payload = {
        "post": {
            "accountId": X_ACCOUNT_ID,
            "content": {
                "text": text,
                "mediaUrls": [image_url] if image_url else [],
                "platform": "twitter",
            },
            "target": {"targetType": "twitter"},
        },
    }
    resp = requests.post(
        f"{BLOTATO_BASE_URL}/posts",
        headers={"blotato-api-key": BLOTATO_API_KEY, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def notify_slack(message):
    """Send notification to Slack #metrics."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_AGENTS")
    if not webhook_url:
        print(f"[Slack] No webhook, skipping: {message}")
        return
    requests.post(webhook_url, json={"text": message}, timeout=10)


def main():
    print("=== x-poster Skill ===")
    now = datetime.now(JST)
    slot = "morning" if now.hour < 12 else "evening"
    
    # 1. Select hook
    print("[1/6] Selecting hook...")
    hook = select_hook()
    print(f"  Hook: {hook['content'][:50]}...")
    
    # 2. Generate content
    print("[2/6] Generating content...")
    content = generate_content(hook)
    text = content["formats"]["short"]
    print(f"  Text: {text[:80]}...")
    
    # 3. Verify text
    print("[3/6] Verifying text...")
    text_score = 0
    for attempt in range(MAX_VERIFICATION_ATTEMPTS):
        result = verify_text(text)
        text_score = result["score"]
        print(f"  Attempt {attempt + 1}: score={text_score}")
        
        if text_score >= MIN_SCORE:
            break
        
        # Regenerate with feedback
        if attempt < MAX_VERIFICATION_ATTEMPTS - 1:
            print(f"  Regenerating with feedback: {result['feedback']}")
            content = generate_content(hook)  # TODO: Pass feedback
            text = content["formats"]["short"]
    
    if text_score < MIN_SCORE:
        notify_slack(f"⚠️ x-poster: Text verification failed after {MAX_VERIFICATION_ATTEMPTS} attempts. Aborting.")
        raise Exception(f"Text verification failed: score={text_score}")
    
    # 4. Generate image (optional)
    print("[4/6] Generating image...")
    image_url = None
    image_score = None
    
    try:
        for attempt in range(MAX_VERIFICATION_ATTEMPTS):
            candidate_url = generate_image(text)
            if not candidate_url:
                print("  Skipping image (no FAL_API_KEY)")
                break
            
            result = verify_image(candidate_url, text)
            image_score = result["score"]
            print(f"  Attempt {attempt + 1}: score={image_score}")
            
            if image_score >= MIN_SCORE:
                image_url = candidate_url
                break
    except Exception as e:
        print(f"  Image generation failed: {e}")
        image_url = None
    
    # 5. Post via Blotato
    print("[5/6] Posting via Blotato...")
    result = blotato_post(text, image_url)
    blotato_id = str(result.get("postSubmissionId", result.get("id", "")))
    print(f"  Blotato ID: {blotato_id}")
    
    # 6. Save to agent_posts
    print("[6/6] Saving to agent_posts...")
    post_data = {
        "platform": "x",
        "content": text,
        "hook": hook["content"],
        "hookId": hook.get("id"),
        "externalPostId": blotato_id,  # Will be updated with real tweet ID later
        "reasoning": json.dumps({
            "textScore": text_score,
            "imageScore": image_score,
            "slot": slot,
        }),
    }
    # Note: We'll create a new endpoint for this or use existing feedback with create mode
    
    # Notify Slack
    notify_slack(f"""📤 X投稿完了
• Hook: {hook['content'][:50]}...
• Text Score: {text_score}/10
• Image: {'✅' if image_url else '❌'}
• Blotato ID: {blotato_id}""")
    
    print("=== x-poster complete ===")


if __name__ == "__main__":
    main()
```

**verifier.py:**
```python
"""
Content verification using LLM.
"""
import os
import json
import requests
from openai import OpenAI

client = OpenAI()

PERSONA = """6-7年間習慣化に失敗し続けている25-35歳。
自分はダメな人間だと信じ込んでいる。
「簡単に習慣化！」のような言葉には警戒する。"""


def verify_text(text: str) -> dict:
    """
    Verify text content quality.
    Returns: {"score": int, "feedback": str, "suggestions": list}
    """
    prompt = f"""あなたはSNSコンテンツの品質審査官です。
以下のX投稿を1-10で採点してください。

採点基準:
- フックの強さ (最初の一文で止まるか): 30%
- 共感度 (ターゲットの心に刺さるか): 30%
- 行動喚起 (読んだ後に何かしたくなるか): 20%
- 簡潔さ (280文字以内、無駄がないか): 20%

ターゲット:
{PERSONA}

投稿:
{text}

JSON形式で回答:
{{"score": 7, "feedback": "...", "suggestions": ["...", "..."]}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=500,
    )
    
    return json.loads(response.choices[0].message.content)


def verify_image(image_url: str, text: str) -> dict:
    """
    Verify image quality using Vision LLM.
    Returns: {"score": int, "feedback": str, "suggestions": list}
    """
    prompt = f"""あなたはSNS画像の品質審査官です。
以下の画像を1-10で採点してください。

採点基準:
- テキストとの一致性 (メッセージを視覚的に伝えているか): 30%
- 感情伝達 (見た瞬間に感情が動くか): 30%
- 可読性 (文字があれば読めるか): 20%
- ブランドトーン (温かく、寄り添う雰囲気か): 20%

関連テキスト:
{text}

JSON形式で回答:
{{"score": 7, "feedback": "...", "suggestions": ["...", "..."]}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=500,
    )
    
    return json.loads(response.choices[0].message.content)
```

---

### 5.2 tiktok-poster Skill

**場所:** `/home/anicca/openclaw/skills/tiktok-poster/`

x-poster と同様の構造。差分:
- Blotato API の `platform: "tiktok"`
- 動画生成は 1.7.0+ へ延期（現在はテキスト + 画像のみ）

---

### 5.3 trend-hunter Skill

**場所:** `/home/anicca/openclaw/skills/trend-hunter/`

**main.py:**
```python
"""
trend-hunter Skill — Discover viral hooks from X/Reddit

Flow:
1. Search X for suffering-related trending topics
2. Search Reddit hot posts in relevant subreddits
3. Extract high-engagement content
4. Analyze and save as hook_candidates
"""
import os
import requests
from datetime import datetime, timezone, timedelta

API_BASE_URL = os.environ["ANICCA_PROXY_BASE_URL"]
AGENT_TOKEN = os.environ["ANICCA_AGENT_TOKEN"]
X_BEARER_TOKEN = os.environ.get("X_BEARER_TOKEN", "")

JST = timezone(timedelta(hours=9))

# Subreddits to monitor
SUBREDDITS = [
    "getdisciplined",
    "habits",
    "productivity",
    "selfimprovement",
    "DecidingToBeBetter",
]

# Keywords to search
KEYWORDS = [
    "習慣化 失敗",
    "procrastination help",
    "can't stick to habits",
    "always give up",
    "self-discipline",
]


def search_x(query, max_results=20):
    """Search X for relevant tweets."""
    if not X_BEARER_TOKEN:
        return []
    
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
    params = {
        "query": f"{query} -is:retweet lang:ja OR lang:en",
        "max_results": max_results,
        "tweet.fields": "public_metrics,created_at",
    }
    
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"X API error: {resp.status_code}")
        return []
    
    return resp.json().get("data", [])


def search_reddit(subreddit, limit=25):
    """Fetch hot posts from a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    headers = {"User-Agent": "Anicca/1.0"}
    params = {"limit": limit}
    
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"Reddit API error for r/{subreddit}: {resp.status_code}")
        return []
    
    posts = resp.json().get("data", {}).get("children", [])
    return [p["data"] for p in posts]


def calculate_engagement_rate(post, platform):
    """Calculate engagement rate for a post."""
    if platform == "x":
        metrics = post.get("public_metrics", {})
        total = metrics.get("like_count", 0) + metrics.get("retweet_count", 0) + metrics.get("reply_count", 0)
        # X doesn't provide impressions in search, estimate based on engagement
        return total / 100  # Simplified
    
    elif platform == "reddit":
        score = post.get("score", 0)
        comments = post.get("num_comments", 0)
        return (score + comments * 2) / 100  # Weighted
    
    return 0


def extract_hook(post, platform):
    """Extract hook (first sentence or title) from post."""
    if platform == "x":
        text = post.get("text", "")
        return text.split("。")[0] if "。" in text else text[:100]
    
    elif platform == "reddit":
        return post.get("title", "")[:200]
    
    return ""


def save_hook_candidate(hook, source_platform, engagement_rate, source_url=None):
    """Save hook candidate to database."""
    url = f"{API_BASE_URL}/api/agent/hooks"
    headers = {"Authorization": f"Bearer {AGENT_TOKEN}", "Content-Type": "application/json"}
    
    data = {
        "content": hook,
        "source": source_platform,
        "engagementRate": engagement_rate,
        "sourceUrl": source_url,
    }
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Failed to save hook: {e}")
        return None


def main():
    print("=== trend-hunter Skill ===")
    hooks_found = 0
    
    # 1. Search X
    print("[1/2] Searching X...")
    for keyword in KEYWORDS[:3]:  # Limit to avoid rate limits
        tweets = search_x(keyword)
        for tweet in tweets:
            engagement = calculate_engagement_rate(tweet, "x")
            if engagement > 0.05:  # 5% threshold
                hook = extract_hook(tweet, "x")
                if hook and len(hook) > 20:
                    save_hook_candidate(hook, "x", engagement)
                    hooks_found += 1
                    print(f"  Found hook: {hook[:50]}... (engagement: {engagement:.2%})")
    
    # 2. Search Reddit
    print("[2/2] Searching Reddit...")
    for subreddit in SUBREDDITS:
        posts = search_reddit(subreddit)
        for post in posts[:10]:  # Top 10 per subreddit
            engagement = calculate_engagement_rate(post, "reddit")
            if engagement > 0.1:  # Higher threshold for Reddit
                hook = extract_hook(post, "reddit")
                if hook and len(hook) > 20:
                    url = f"https://reddit.com{post.get('permalink', '')}"
                    save_hook_candidate(hook, "reddit", engagement, url)
                    hooks_found += 1
                    print(f"  Found hook: {hook[:50]}... (engagement: {engagement:.2%})")
    
    print(f"\n=== trend-hunter complete: {hooks_found} hooks found ===")


if __name__ == "__main__":
    main()
```

---

### 5.4 suffering-detector Skill

**場所:** `/home/anicca/openclaw/skills/suffering-detector/`

既存の `moltbook-responder` を拡張。Slack チャンネル監視を追加。

---

### 5.5 Nia 統合

**インストール:**
```bash
clawhub install arlanrakh/nia@v1.0.2
```

**インデックス作成:**
```bash
# 仏教文献
nia index --source "https://accesstoinsight.org/" --type documentation
nia index --source "https://www.dhammatalks.org/" --type documentation

# 心理学論文
nia index --source "arxiv:2312.00752" --type paper  # Self-Compassion
nia index --source "arxiv:2301.08745" --type paper  # Procrastination
nia index --source "arxiv:2205.03548" --type paper  # MBCT
nia index --source "arxiv:2110.14168" --type paper  # Digital Habits
```

---

## 6. schedule.yaml（完全版）

```yaml
# /home/anicca/openclaw/schedule.yaml

skills:
  # ─────────────────────────────────────────────
  # P0: コンテンツ投稿（1日2回）
  # ─────────────────────────────────────────────
  x-poster:
    cron:
      - "0 0 * * *"   # 09:00 JST (UTC+9)
      - "0 12 * * *"  # 21:00 JST
    timezone: "Asia/Tokyo"
    retry:
      max_attempts: 2
      backoff: "exponential"
    on_error: "notify_slack"

  tiktok-poster:
    cron:
      - "0 0 * * *"   # 09:00 JST
      - "0 12 * * *"  # 21:00 JST
    timezone: "Asia/Tokyo"
    retry:
      max_attempts: 2
      backoff: "exponential"
    on_error: "notify_slack"

  # ─────────────────────────────────────────────
  # P1: トレンド監視（4時間ごと）
  # ─────────────────────────────────────────────
  trend-hunter:
    interval: "4h"
    retry:
      max_attempts: 2
      backoff: "linear"
    on_error: "log_and_continue"

  # ─────────────────────────────────────────────
  # P1: フィードバック収集（4時間ごと）
  # ─────────────────────────────────────────────
  feedback-fetch:
    interval: "4h"
    retry:
      max_attempts: 2
      backoff: "linear"
    on_error: "log_and_continue"

  # ─────────────────────────────────────────────
  # P1: 苦しみ検出（5分ごと）
  # ─────────────────────────────────────────────
  suffering-detector:
    interval: "5m"
    retry:
      max_attempts: 3
      backoff: "exponential"
    on_error: "log_and_continue"

  # ─────────────────────────────────────────────
  # P1: 既存スキル
  # ─────────────────────────────────────────────
  moltbook-responder:
    interval: "5m"
    retry:
      max_attempts: 3
      backoff: "exponential"
    on_error: "log_and_continue"

  slack-reminder:
    cron:
      - "0 21 * * 0"   # 日曜 21:00 JST (前日通知)
      - "25 12 * * 1"  # 月曜 12:25 JST (当日リマインダー)
    timezone: "Asia/Tokyo"
    skip_if:
      - holiday: "https://holidays-jp.github.io/api/v1/date.json"

  # ─────────────────────────────────────────────
  # P2: レビュー対応（1時間ごと）
  # ─────────────────────────────────────────────
  review-responder:
    interval: "1h"
    retry:
      max_attempts: 2
      backoff: "linear"
    on_error: "log_and_continue"
```

---

## 7. 新規 API エンドポイント

### 7.1 POST /api/agent/hooks

hook_candidates にフックを追加するエンドポイント。

**リクエスト:**
```json
{
  "content": "習慣アプリ10個試して全部挫折した話",
  "source": "reddit",
  "engagementRate": 0.15,
  "sourceUrl": "https://reddit.com/r/getdisciplined/...",
  "problemType": "procrastination"
}
```

**レスポンス:**
```json
{
  "id": "uuid",
  "content": "...",
  "source": "reddit",
  "createdAt": "2026-02-03T12:00:00Z"
}
```

### 7.2 POST /api/agent/posts

agent_posts に新規投稿を作成するエンドポイント。

**リクエスト:**
```json
{
  "platform": "x",
  "content": "投稿テキスト",
  "hook": "使用したフック",
  "hookId": "uuid",
  "externalPostId": "blotato_123",
  "reasoning": "{\"textScore\": 8, \"imageScore\": 7}"
}
```

---

## 8. テスト計画

### 8.1 手動テスト

| # | テスト | 手順 | 期待結果 |
|---|--------|------|---------|
| 1 | x-poster 単体 | VPS で `openclaw skill run x-poster --test` | 投稿成功、Slack通知あり |
| 2 | 検証ループ | 低品質テキストを入力 | 再生成される |
| 3 | trend-hunter | VPS で `openclaw skill run trend-hunter` | hook_candidates に追加 |
| 4 | feedback-fetch | 4時間待機後に確認 | agent_posts.likes 更新 |
| 5 | Nia 検索 | `nia search "procrastination buddhism"` | 引用付き結果 |

### 8.2 E2E テスト

| # | テスト | 手順 | 期待結果 |
|---|--------|------|---------|
| 1 | 投稿→収集→昇格 | x-poster 実行 → 4時間待機 → feedback-fetch | 高エンゲージメント投稿が hook_candidates に昇格 |
| 2 | トレンド→投稿 | trend-hunter で発見 → x-poster で使用 | 発見したフックで投稿成功 |

---

## 9. 完了チェックリスト

| # | タスク | 状態 |
|---|--------|------|
| A1 | x-poster Skill 作成 | ❌ |
| A2 | tiktok-poster Skill 作成 | ❌ |
| A3 | テキスト検証機能 | ❌ |
| A4 | 画像検証機能 | ❌ |
| A5 | schedule.yaml 更新 | ❌ |
| A6 | GitHub Actions 無効化 | ❌ |
| B1 | suffering-detector Skill | ❌ |
| B2 | review-responder Skill | ❌ |
| C1 | trend-hunter Skill | ❌ |
| C2 | content-syndicator Skill | ❌ |
| D1 | Nia Skill インストール | ❌ |
| D2 | 仏教文献インデックス | ❌ |
| D3 | 心理学論文インデックス | ❌ |
| D4 | wisdom-researcher Skill | ❌ |
| E1 | feedback-fetch 拡張 | ❌ |
| E2 | Z-Score 計算 | ❌ |
| E3 | hook_candidates 昇格 | ❌ |
| POST /api/agent/hooks | ❌ |
| POST /api/agent/posts | ❌ |
| 手動テスト完了 | ❌ |
| X 100フォロワー達成 | ❌ |
| TikTok 100フォロワー達成 | ❌ |

---

## 10. 更新履歴

| 日付 | 内容 |
|------|------|
| 2026-02-03 | 初版作成 |
