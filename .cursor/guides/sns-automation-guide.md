# SNS自動投稿ガイド (Blotato API)

## 概要

このガイドでは、AIエージェントがBlotato API経由でSNS投稿を自動化する方法を説明する。

## 必要なもの

### API Keys
- **Blotato API Key**: Settings → API → "Generate API Key"
  - 注意: API Key生成で有料プランに自動移行
- **Fal.ai API Key** (オプション): 画像/動画生成用

### 接続済みアカウント
- Instagram Business Account
- TikTok
- X (Twitter)
- YouTube
- Pinterest
- (その他: LinkedIn, Facebook, Threads, Bluesky)

---

## 投稿戦略

### プラットフォーム別コンテンツ

| プラットフォーム | コンテンツタイプ | 備考 |
|-----------------|-----------------|------|
| **X** | Build in Public のみ | 開発進捗、技術的な話 |
| **Instagram** | Marketing + Build in Public | Reels中心、視覚的コンテンツ |
| **TikTok** | Marketing + Build in Public | 短尺動画、エンタメ要素 |
| **YouTube** | Marketing + Build in Public | Shorts中心 |
| **Pinterest** | Marketing + Build in Public | インフォグラフィック、カルーセル |

---

## Blotato API リファレンス

### Base URL
```
https://backend.blotato.com/v2
```

### 認証ヘッダー
```
blotato-api-key: YOUR_API_KEY
Content-Type: application/json
```

### エンドポイント

#### 1. アカウント一覧取得
```bash
GET /accounts
```

**レスポンス例:**
```json
{
  "accounts": [
    {
      "id": "acc_12345",
      "platform": "instagram",
      "username": "@anicca_app"
    }
  ]
}
```

#### 2. メディアアップロード
```bash
POST /media
```

**リクエスト:**
```json
{
  "url": "https://example.com/video.mp4"
}
```

**レスポンス:**
```json
{
  "url": "https://blotato-cdn.com/uploaded/abc123.mp4"
}
```

#### 3. 投稿作成 (即時)
```bash
POST /posts
```

**リクエスト:**
```json
{
  "post": {
    "accountId": "acc_12345",
    "content": {
      "text": "キャプション #hashtag",
      "platform": "instagram",
      "mediaUrls": ["https://blotato-cdn.com/uploaded/abc123.mp4"]
    },
    "target": {
      "targetType": "instagram"
    }
  }
}
```

#### 4. 投稿作成 (スケジュール)
```json
{
  "post": {
    "accountId": "acc_12345",
    "scheduledTime": "2025-03-10T15:30:00Z",
    "content": {
      "text": "キャプション",
      "platform": "twitter",
      "mediaUrls": []
    },
    "target": {
      "targetType": "twitter"
    }
  }
}
```

---

## プラットフォーム別パラメータ

### Instagram Reels
```json
{
  "target": {
    "targetType": "instagram"
  }
}
```

### TikTok
```json
{
  "target": {
    "targetType": "tiktok",
    "isYourBrand": "false",
    "privacyLevel": "PUBLIC_TO_EVERYONE",
    "isAiGenerated": "true",
    "disabledDuet": "false",
    "disabledStitch": "false",
    "disabledComments": "false"
  }
}
```

### X (Twitter)
```json
{
  "target": {
    "targetType": "twitter"
  }
}
```

---

## 使用例: Pythonスクリプト

### 環境変数設定
```bash
export BLOTATO_API_KEY="blt_xxxxx"
export FAL_API_KEY="fal_xxxxx"
```

### 投稿スクリプト
```python
import os
import json
import urllib.request

BLOTATO_API_KEY = os.environ.get("BLOTATO_API_KEY")
BASE_URL = "https://backend.blotato.com/v2"

def get_accounts():
    """接続済みアカウント一覧を取得"""
    req = urllib.request.Request(f"{BASE_URL}/accounts")
    req.add_header("blotato-api-key", BLOTATO_API_KEY)
    req.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

def upload_media(media_url):
    """メディアをBlotoにアップロード"""
    req = urllib.request.Request(f"{BASE_URL}/media", method="POST")
    req.add_header("blotato-api-key", BLOTATO_API_KEY)
    req.add_header("Content-Type", "application/json")

    data = json.dumps({"url": media_url}).encode()

    with urllib.request.urlopen(req, data) as response:
        return json.loads(response.read().decode())

def post_to_platform(account_id, platform, text, media_urls=None):
    """指定プラットフォームに投稿"""
    req = urllib.request.Request(f"{BASE_URL}/posts", method="POST")
    req.add_header("blotato-api-key", BLOTATO_API_KEY)
    req.add_header("Content-Type", "application/json")

    payload = {
        "post": {
            "accountId": account_id,
            "content": {
                "text": text,
                "platform": platform,
                "mediaUrls": media_urls or []
            },
            "target": {
                "targetType": platform
            }
        }
    }

    data = json.dumps(payload).encode()

    with urllib.request.urlopen(req, data) as response:
        return json.loads(response.read().decode())

# 使用例
if __name__ == "__main__":
    accounts = get_accounts()
    print(accounts)
```

---

## Build in Public コンテンツ例

### X (Twitter) 向け
```
Day 47: Implemented Problem Nudge System

13 problem types → personalized notifications

- staying_up_late → "Hey, it's getting late..."
- procrastination → "What's one tiny step?"
- self_loathing → "You're trying. That matters."

#buildinpublic #indiedev #ios
```

### Instagram/TikTok向け
```
6年間、何も変われなかった。

習慣アプリ10個試した。
全部3日坊主で挫折。

でも気づいた。
問題は「意志の弱さ」じゃない。
アプリが「人間」を理解してなかった。

Aniccaは違う。
あなたの「苦しみ」に寄り添う。

#習慣化 #自己改善 #行動変容
```

---

## Fal.ai 画像生成 (オプション)

### エンドポイント
```
POST https://queue.fal.run/fal-ai/flux/schnell
```

### 認証
```
Authorization: Key YOUR_FAL_API_KEY
```

### リクエスト例
```json
{
  "prompt": "minimalist app interface showing notification card, dark mode, iOS design",
  "image_size": "square_hd",
  "num_images": 1
}
```

---

## トラブルシューティング

### 401 Unauthorized
- API Keyが正しいか確認
- https://my.blotato.com/api-dashboard でキーの状態確認
- 有料プランに移行しているか確認

### メディアアップロード失敗
- URLが公開アクセス可能か確認
- ファイルサイズ制限を確認
- サポートされている形式か確認 (MP4, MOV, JPG, PNG)

---

## 参考リンク

- Blotato API Help: https://help.blotato.com/api/start
- Blotato Dashboard: https://my.blotato.com/api-dashboard
- Fal.ai: https://fal.ai/
- Instagram Graph API: https://developers.facebook.com/docs/instagram-platform/content-publishing/
- TikTok Content Posting API: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post

---

最終更新: 2025-01-19
