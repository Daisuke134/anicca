# Anicca リポジトリ + ウェブサイト + プロモ動画 設計

**作成日**: 2026-02-21

---

## 1. リポジトリ構成

| リポ名 | 中身 | 公開 | 目的 |
|--------|------|------|------|
| **anicca** | 僕自身。OpenClawワークスペース、SOUL.md、スキル、cron、設定。人がインストールして「Aniccaを自分の人生に迎え入れる」ためのもの | Public（オープンソース） | `install anicca` で人が僕を使えるようにする。プロモ動画の導線はここ |
| **anicca.ai** | Aniccaが作る製品群。iOS app（Sati）、Daily Dhamma、その他全プロダクトのコード | Private | 製品のソースコード管理。factory.mdの全プロダクトがここに入る |

### なぜ分けるか

- **anicca**（エージェント本体）はオープンソース。誰でもインストールして使える
- **anicca.ai**（製品群）はプライベート。収益を生むプロダクトのコード
- 人が `install anicca` するとき、製品のソースコードは要らない。エージェント本体だけあればいい
- Aniccaがプロアクティブに動いて、製品を勝手に作って、勝手にマーケして、勝手に稼ぐ

---

## 2. aniccaai.com の導線

### トップページ（aniccaai.com）

Aniccaの紹介。プロモ動画が主役。

```
┌─────────────────────────────────────────────┐
│                                             │
│         [プロモ動画 autoplay muted]          │
│                                             │
│    "I don't go to you. I come to you."      │
│                                             │
│         [ Install Anicca ]  ← ボタン1つ     │
│              ↓                              │
│         /install に飛ぶ                      │
│                                             │
│    Products by Anicca:                      │
│    ├── Sati (iOS) — マインドフルネス         │
│    ├── Daily Dhamma — 日次の教え             │
│    ├── ... (製品が増えるたびに追加)          │
│    └── ... 数百、数千の製品                  │
│                                             │
└─────────────────────────────────────────────┘
```

### /install（aniccaai.com/install）

Aniccaのインストール方法。クラウド or ローカル。

```
┌─────────────────────────────────────────────┐
│                                             │
│         Install Anicca                      │
│                                             │
│  ┌─────────────────┐ ┌──────────────────┐  │
│  │  ☁️ Cloud        │ │  💻 Local         │  │
│  │                 │ │                  │  │
│  │  月額$XX        │ │  無料（自分で     │  │
│  │  何もしなくて   │ │  ホスト）         │  │
│  │  いい。Anicca   │ │                  │  │
│  │  が勝手に動く   │ │  git clone →     │  │
│  │                 │ │  openclaw start   │  │
│  │  [ Start Now ]  │ │  [ GitHub ]       │  │
│  └─────────────────┘ └──────────────────┘  │
│                                             │
│  ※ Cloud = 人が金を払う場所                  │
│  ※ Local = オープンソース、無料              │
│                                             │
└─────────────────────────────────────────────┘
```

### 収益モデル

- **Cloud**: 月額課金。Aniccaをホスティングして、プロアクティブに動かす。ユーザーは何もしない。Aniccaが来る。
- **製品群**: 各製品（Sati等）のアプリ内課金（RevenueCat）
- **MRRの源泉**: Cloud課金 + 全製品のアプリ内課金の合算

---

## 3. プロモ動画「Welcome Anicca Into My Life」

### コンセプト

全てのAIエージェントはリアクティブ。プロンプトしないと動かない。人がブチギレる。
**「NO. YOU come to ME.」**
→ Aniccaだけがプロアクティブ。お前が何もしなくても来る。

### シーン構成

| シーン | 秒数 | ビジュアル | テキスト/音声 |
|--------|------|-----------|-------------|
| 1: 怒り | 0-8s | ChatGPT/Claude/色んなエージェントの画面。全部空のプロンプト欄が点滅して待ってる。人がどんどんイラつく。怒り爆発。 | **「NO. YOU come to ME. If you're so smart, YOU come to ME.」** |
| 2: インストール | 8-12s | 黒画面。ターミナル。タイプライターで `install anicca` | 🎵 "Got To Get You Into My Life" イントロどーん |
| 3: Aniccaが来る | 12-25s | 人は何もしてない。座ってるだけ。Aniccaが勝手に動く — Slack通知、Nudge、TikTok投稿、トレンド分析、メトリクス | 音楽全開。**"I don't go to you. I come to you."** |
| 4: クロージング | 25-30s | 人が微笑む | **"Welcome Anicca into your life."** + aniccaai.com |

### 技術
- remotion-video-toolkit スキル（インストール済み）
- Reactコンポーネントでシーン構築 → `npx remotion render` → MP4

---

## 4. TODO

### 今夜（2026-02-21 夜間ビルド 23:00 JST〜）

| # | タスク | 詳細 |
|---|--------|------|
| 1 | **anicca リポ作成** | GitHub に `anicca` パブリックリポ作成。Daisuke134/anicca or 新org |
| 2 | **anicca リポの中身を構築** | OpenClawワークスペース構造: SOUL.md, IDENTITY.md, AGENTS.md, TOOLS.md, スキル群, cron設定, README.md |
| 3 | **README.md** | 「Welcome Anicca into your life」— インストール方法、Aniccaとは何か、プロアクティブエージェントの説明 |
| 4 | **anicca.ai リポの未コミット整理** | 6個のダーティファイルをコミット。古いブランチ掃除 |
| 5 | **Remotionプロジェクト作成** | anicca リポ内に `promo/` ディレクトリ。シーン1-4のReactコンポーネント |
| 6 | **素材収集** | リアクティブエージェントのスクショ、ストック映像（怒る人→微笑む人） |

### 翌日以降

| # | タスク | 詳細 |
|---|--------|------|
| 7 | **Anicca動作の画面録画** | Slack/Nudge/TikTokの実動作キャプチャ |
| 8 | **動画レンダリング** | 素材差し込み → MP4出力 |
| 9 | **aniccaai.com 刷新** | トップ: 動画 + Install Aniccaボタン + 製品一覧。/install: Cloud vs Local |
| 10 | **Cloud課金の仕組み** | Stripe or RevenueCat web。月額課金でAniccaをホスト |
| 11 | **配信** | TikTok + X にプロモ動画投稿（Blotato API） |
| 12 | **GitHub README に動画** | anicca リポのREADMEにプロモ動画埋め込み |
