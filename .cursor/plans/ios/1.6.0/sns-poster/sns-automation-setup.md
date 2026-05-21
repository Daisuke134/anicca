# SNS自動投稿システム - 完全ガイド

**作成日**: 2026-01-20  
**ステータス**: ✅ 稼働中

---

## 📊 アカウント一覧

**詳細は `platform_strategy.md` を参照**

| 区分 | Platform | アカウント | コンテンツ | 言語 | 頻度 | 状態 |
|------|----------|-----------|----------|------|------|------|
| **メイン** | X | @xg2grb (11820) | Build in Public | EN | 3回/日 | ✅ |
| サブ | X | @AniccaNudges (11852) | マーケティング | EN | 3回/日 | ✅ |
| **メイン** | IG | @anicca.ai (28896) | マーケティング | EN | 3回/日 | ✅ |
| **メイン** | IG | @anicca.japan (28897) | マーケティング | JP | 3回/日 | ✅ |
| サブ | IG | @anicca.daily (28682) | マーケティング | EN | 1回/日 | ✅ |
| **メイン** | TT | @anicca.ai (27339) | マーケティング | EN | 3回/日 | ✅ |
| **メイン** | TT | @anicca.japan (27527) | マーケティング | JP | 3回/日 | ✅ |
| サブ | TT | @anicca57 (27528) | マーケティング | EN | 1回/日 | ✅ |
| **メイン** | YouTube | Daisuke Narita (25421) | マーケティング | EN | 3回/日 | ✅ |
| ⏳ | Pinterest | @aniccaai (3965) | マーケティング | EN | - | 認証待ち |

---

## ⏰ 最適な投稿時間（ベストプラクティス）

### グローバル推奨（UTC基準 → JST +9時間）

| プラットフォーム | ベストタイム (UTC) | ベストタイム (JST) | ベスト曜日 |
|-----------------|-------------------|-------------------|-----------|
| **X (Twitter)** | 8:00-10:00 AM | 17:00-19:00 | 水・木 |
| **Instagram** | 11:00 AM - 1:00 PM | 20:00-22:00 | 火・水・木 |
| **TikTok** | 7:00-9:00 PM | 4:00-6:00 (翌朝) | 火・木・金 |
| **YouTube** | 2:00-4:00 PM | 23:00-1:00 | 木・金 |
| **Pinterest** | 8:00-11:00 PM | 5:00-8:00 (翌朝) | 土・日 |

### 日本向け推奨（JST）

| 時間帯 | 理由 | おすすめ |
|--------|------|---------|
| **7:00-8:00** | 朝の通勤時間 | X, Instagram |
| **12:00-13:00** | ランチ休憩 ⭐ | 全プラットフォーム |
| **18:00-20:00** | 帰宅・夜のリラックス | TikTok, Instagram |
| **21:00-23:00** | 就寝前のスマホ時間 | TikTok, YouTube |

**→ 12:30 JST はランチ休憩で最適！ 正解！** 🎯

---

## 🎬 できること一覧

### ✅ 完全自動（依頼するだけ）

| 機能 | 説明 |
|------|------|
| ローカルファイル投稿 | MP4, 画像を指定 → 全SNSに投稿 |
| 画像生成 + 投稿 | Fal.ai FLUX で生成 → 投稿 |
| 動画生成 + 投稿 | Fal.ai Seedance で生成 → 投稿 |
| 音声生成 + 動画合成 | Fal.ai MMAudio + FFmpeg |
| 複数SNS同時投稿 | 1回の依頼で全プラットフォーム |
| スケジュール投稿 | 日時指定で予約 |
| 生成動画のダウンロード | URL取得 → ローカル保存可能 |

### 🟡 可能だが設定が必要

| 機能 | 方法 |
|------|------|
| 音楽付き動画 | Fal.ai MMAudio で BGM生成 → 合成 |
| 音声付き動画 | Kling 2.5/Seedance 1.5 (要調査) |
| cron自動投稿 | スクリプト設定 |

### ❌ 現在対応外

| 機能 | 理由 |
|------|------|
| Pinterest | Blotato認証待ち（help@blotato.com にメール） |

---

## 📝 使用例（チャットで依頼）

### 1. ローカルファイルを投稿

```
「この動画を全SNSに投稿して:
ファイル: /Users/cbns03/Downloads/promo.mp4
タイトル: 朝のルーティン
キャプション: Your morning sets the tone ✨」
```

### 2. @AniccaNudges（日本語マーケティング）

```
「@AniccaNudgesに投稿して:
🧘 今日も一歩ずつ。
小さな習慣が大きな変化を生む。
#anicca #習慣」
```

### 3. @xg2grb（Build in Public）

```
「Build in Public投稿:
Day 8: SNS automation complete! 
Now posting to 5 platforms with one command.
#buildinpublic #indiehacker」
```

### 4. YouTube（日本語OK）

```
「YouTubeに投稿:
タイトル: 【習慣化のコツ】朝5時起きを3ヶ月続けた結果
説明: 早起きで人生が変わった話
動画: [URL]」
```

### 5. 動画生成 → 編集 → 投稿

```
ステップ1: 「禅の庭の動画を生成して、URLを教えて」
→ URLを取得

ステップ2: (自分で編集)

ステップ3: 「編集した動画を投稿して:
ファイル: /Users/cbns03/Downloads/edited.mp4」
```

### 6. 音楽付き動画

```
「動画を生成して、リラックスBGMも生成して合成して:
動画: peaceful meditation scene
音楽: calm ambient music, soft piano」
```

---

## 🎵 音楽・音声について

### 現在対応

| 機能 | 方法 | 品質 |
|------|------|------|
| **BGM生成** | Fal.ai MMAudio | ✅ 良好 |
| **動画+BGM合成** | Fal.ai FFmpeg API | ✅ 可能 |

### 今後追加可能

| 機能 | モデル | 状態 |
|------|--------|------|
| **音声付き動画** | Seedance 1.5 Pro | 🟡 対応可能 |
| **話す動画** | Kling 2.5 | 🔴 要API追加 |
| **ナレーション** | ElevenLabs | 🔴 要API追加 |

---

## 📁 ローカルファイルのワークフロー

### 生成 → 編集 → 投稿

```
1. 動画生成依頼
   → URLを取得（例: https://v3b.fal.media/xxx.mp4）

2. ダウンロード
   → curl -o edited.mp4 "URL" または ブラウザで保存

3. 編集（Premiere, CapCut, etc.）

4. 投稿依頼
   → 「この動画を投稿: /path/to/edited.mp4」
```

### ローカルファイル対応

```
「このMP4をTikTokに投稿:
/Users/cbns03/Downloads/my_video.mp4
キャプション: Check this out!」
```

※ ローカルファイルは一旦アップロードしてから投稿

---

## 📅 投稿スケジュール提案

### 平日（月〜金）

| 時間 (JST) | プラットフォーム | 内容 |
|------------|-----------------|------|
| **8:00** | X (@xg2grb) | Build in Public 朝 |
| **12:30** | Instagram, TikTok, X (@AniccaNudges) | メインコンテンツ |
| **19:00** | YouTube, TikTok | 動画コンテンツ |
| **21:00** | X (@AniccaNudges) | 夜のエンゲージメント |

### 週末（土・日）

| 時間 (JST) | プラットフォーム | 内容 |
|------------|-----------------|------|
| **10:00** | Instagram, Pinterest | ビジュアルコンテンツ |
| **15:00** | YouTube | 長尺動画 |
| **20:00** | TikTok | エンタメ系 |

---

## 🔧 コマンドリファレンス

### X (@xg2grb) - Build in Public

```bash
python post.py x "Day 9: Shipped feature X! #buildinpublic"
```

### X (@AniccaNudges) - マーケティング

```bash
python -c "
from blotato import BlotatoClient
client = BlotatoClient()
client.post_to_x('日本語テキスト', account='x_nudges')
"
```

### スケジュール投稿

```bash
python post.py x "Tomorrow's post" --schedule "2026-01-21T12:30:00+09:00"
```

---

## 📧 対応待ちタスク

1. **Pinterest**: help@blotato.com にメールして認証をリクエスト
2. **Kling 2.5 API**: 音声付き動画が必要なら追加検討

---

## 💡 ヒント

- **Instagram は1日1回のみ**（アルゴリズム的に最適）
- **YouTube は日本語タイトル可能**（視聴者に合わせて）
- **12:30 JST はランチ休憩で最高のタイミング**
- **ローカル編集 → 投稿のワークフローは完全対応**

---

最終更新: 2026-01-20
