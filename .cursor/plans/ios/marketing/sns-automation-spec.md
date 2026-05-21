# SNS自動投稿システム - 実装スペック

## 概要

Blotato API + Fal.ai を使用して、Anicca の SNS 投稿を自動化するシステム。
Cursor から直接操作可能。画像/動画生成から投稿まで一気通貫で実行。

---

## API Keys

### 保存場所
```
/Users/cbns03/Downloads/anicca-project/.env
```

### 環境変数
```bash
BLOTATO_API_KEY=blt_mJ9wjP4/z2Z1ETnBUCkr9edrB8jfcLCJs4nafSd1TaY=
FAL_API_KEY=11381e88-f880-4104-923e-31efa88905eb:4c456913b8bae3d17f1fc7901625d6c3
```

---

## 接続アカウント

| プラットフォーム | ユーザー名 | Account ID | テスト状況 |
|-----------------|-----------|------------|-----------|
| YouTube | Daisuke Narita (Anicca - AI Coaching app) | `25421` | ✅ テスト完了 |
| Instagram | @anicca.daily | `28682` | ✅ テスト完了 |
| Pinterest | @aniccaai | `3965` | ⏳ boardId取得待ち |
| TikTok | @anicca.ai | `27339` | ✅ テスト完了 |
| X (Twitter) | @xg2grb | `11820` | ✅ テスト完了 |

---

## 投稿戦略

| プラットフォーム | コンテンツ | 頻度 | 言語 |
|-----------------|-----------|------|------|
| **X** | Build in Public のみ | 3回/日 | 英語 + 時々日本語 |
| **Instagram** | Marketing + Build in Public | **1回/日のみ** | 英語 |
| **TikTok** | Marketing + Build in Public | 3回/日 | 英語 |
| **Pinterest** | Marketing + Build in Public | 3回/日 | 英語 |
| **YouTube** | Marketing + Build in Public | 3回/日 | 英語 + 時々日本語 |

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

#### ユーザー情報取得
```bash
GET /v2/users/me
```

#### アカウント一覧取得
```bash
GET /v2/users/me/accounts
```

#### メディアアップロード
```bash
POST /v2/media
```
```json
{
  "url": "https://example.com/image.jpg"
}
```

#### 投稿作成
```bash
POST /v2/posts
```

---

## プラットフォーム別投稿フォーマット

### X (Twitter)
```json
{
  "post": {
    "accountId": "11820",
    "content": {
      "text": "投稿テキスト #hashtag",
      "mediaUrls": [],
      "platform": "twitter"
    },
    "target": {
      "targetType": "twitter"
    }
  }
}
```

### Instagram
```json
{
  "post": {
    "accountId": "28682",
    "content": {
      "text": "キャプション #hashtag",
      "mediaUrls": ["https://..."],
      "platform": "instagram"
    },
    "target": {
      "targetType": "instagram",
      "mediaType": "reel"
    }
  }
}
```
- `mediaType`: `"reel"` または `"story"` (省略時は通常投稿)
- **メディア必須**

### TikTok
```json
{
  "post": {
    "accountId": "27339",
    "content": {
      "text": "キャプション #hashtag",
      "mediaUrls": ["https://..."],
      "platform": "tiktok"
    },
    "target": {
      "targetType": "tiktok",
      "privacyLevel": "PUBLIC_TO_EVERYONE",
      "disabledComments": false,
      "disabledDuet": false,
      "disabledStitch": false,
      "isBrandedContent": false,
      "isYourBrand": false,
      "isAiGenerated": true
    }
  }
}
```
- **全パラメータ必須**
- **メディア必須**

### Pinterest
```json
{
  "post": {
    "accountId": "3965",
    "content": {
      "text": "説明文",
      "mediaUrls": ["https://..."],
      "platform": "pinterest"
    },
    "target": {
      "targetType": "pinterest",
      "boardId": "BOARD_ID_HERE",
      "title": "ピンタイトル",
      "link": "https://anicca.app"
    }
  }
}
```
- **boardId 必須** (要取得)
- **メディア必須**

### YouTube
```json
{
  "post": {
    "accountId": "25421",
    "content": {
      "text": "動画説明",
      "mediaUrls": ["https://..."],
      "platform": "youtube"
    },
    "target": {
      "targetType": "youtube",
      "title": "動画タイトル",
      "privacyStatus": "public",
      "shouldNotifySubscribers": true,
      "isMadeForKids": false
    }
  }
}
```
- **title, privacyStatus, shouldNotifySubscribers 必須**
- **動画必須**

---

## Fal.ai リファレンス

### 認証
```
Authorization: Key YOUR_FAL_API_KEY
```

### 画像生成 (FLUX)
```bash
POST https://queue.fal.run/fal-ai/flux/schnell
```
```json
{
  "prompt": "プロンプト",
  "image_size": "square_hd",
  "num_images": 1
}
```

### 動画生成 (Seedance)
```bash
POST https://queue.fal.run/fal-ai/seedance/v1/pro/text-to-video
```
```json
{
  "prompt": "プロンプト",
  "aspect_ratio": "9:16",
  "duration": 10
}
```

### 音声生成 (MMAudio)
```bash
POST https://queue.fal.run/fal-ai/mmaudio-v2/text-to-audio
```
```json
{
  "prompt": "BGMの説明",
  "duration": 10
}
```

---

## ディレクトリ構成

```
/Users/cbns03/Downloads/anicca-project/
├── .env                          # API Keys (gitignore対象)
├── scripts/
│   └── sns-poster/
│       ├── __init__.py
│       ├── config.py             # アカウントID、設定
│       ├── blotato.py            # Blotato API wrapper
│       ├── fal_ai.py             # Fal.ai API wrapper
│       ├── post.py               # メイン投稿スクリプト
│       ├── generate_image.py     # 画像生成
│       ├── generate_video.py     # 動画生成
│       ├── batch_post.py         # バッチ投稿
│       └── requirements.txt
└── generated/
    ├── images/                   # 生成した画像
    └── videos/                   # 生成した動画
```

---

## セットアップ手順

### Step 1: 環境変数ファイル作成
```bash
# /Users/cbns03/Downloads/anicca-project/.env
BLOTATO_API_KEY=blt_mJ9wjP4/z2Z1ETnBUCkr9edrB8jfcLCJs4nafSd1TaY=
FAL_API_KEY=11381e88-f880-4104-923e-31efa88905eb:4c456913b8bae3d17f1fc7901625d6c3
```

### Step 2: .gitignore に追加
```
.env
generated/
```

### Step 3: 依存関係インストール
```bash
pip install python-dotenv requests
```

### Step 4: 残りのプラットフォームをテスト
- [ ] Instagram (メディア付き)
- [ ] TikTok (メディア付き)
- [ ] Pinterest (boardId取得後)
- [ ] YouTube (動画付き)

---

## 使い方

### Cursor から直接投稿

**テキストのみ (X向け):**
```
「Xに以下を投稿して:
Day 2: SNS自動化完成！
#buildinpublic」
```

**画像生成 + 投稿:**
```
「Build in Public の画像を生成して、IG/TikTokに投稿して。
テーマ: アプリ開発の進捗」
```

**バッチ投稿:**
```
「以下の5つのコンテンツを全プラットフォームに投稿して:
1. ...
2. ...
」
```

### ローカル画像/動画を使う
```
「/Users/cbns03/Downloads/promo.mp4 を TikTok と IG に投稿して。
キャプション: ...」
```

---

## 自動化 (cron)

### 設定例
```bash
# crontab -e
# 毎日 9:00, 13:00, 18:00 に自動投稿
0 9,13,18 * * * cd /Users/cbns03/Downloads/anicca-project && python scripts/sns-poster/post.py
```

### スケジュール投稿 (Blotato API)
```json
{
  "post": { ... },
  "scheduledTime": "2025-01-21T09:00:00Z"
}
```

---

## 参考: viralfal.json ワークフロー

n8n ワークフローの流れ:
```
Schedule Trigger (24h毎)
  ↓
GPT-4 でアイデア生成
  ↓
Google Sheets に保存
  ↓
Fal.ai Seedance で動画生成
  ↓
Fal.ai MMAudio で音声生成
  ↓
FFmpeg で合成
  ↓
Blotato API → IG/TikTok に投稿
```

本システムでは n8n の代わりに Python + cron で同等の自動化を実現。

---

## 残タスク

- [x] Pinterest の boardId を取得 → **要手動取得（Blotato Web UIから）**
- [x] Instagram テスト投稿 (Reel) → ✅ 完了
- [x] TikTok テスト投稿 → ✅ 完了
- [x] YouTube テスト投稿 → ✅ 完了
- [x] Python スクリプト作成 → ✅ 完了
- [ ] Pinterest boardId を config.py に設定
- [ ] cron 設定（オプション）

---

## トラブルシューティング

### 401 Unauthorized
- API Key が正しいか確認
- 環境変数が読み込まれているか確認

### メディアアップロード失敗
- URL が公開アクセス可能か確認
- ファイル形式: MP4, MOV, JPG, PNG
- ファイルサイズ制限を確認

### TikTok 投稿失敗
- 全ての必須パラメータが含まれているか確認
- `privacyLevel`, `disabledComments`, `disabledDuet`, `disabledStitch`, `isBrandedContent`, `isYourBrand`, `isAiGenerated` は全て必須

---

最終更新: 2026-01-20

---

## セットアップ完了状況

✅ **完了済み:**
- `.env` ファイル作成（API Keys保存）
- `.gitignore` に `generated/` と `.venv/` 追加
- `scripts/sns-poster/` ディレクトリ＆Pythonスクリプト作成
- venv作成＆依存関係インストール
- X, Instagram, TikTok, YouTube テスト投稿成功

⏳ **手動作業が必要:**
- Pinterest boardId: https://my.blotato.com → Remix → Pinterest投稿作成 → Publish → boardId取得
- 取得後 `config.py` の `ACCOUNTS['pinterest']['board_id']` に設定
