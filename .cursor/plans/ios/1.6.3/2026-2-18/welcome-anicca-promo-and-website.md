# Anicca リポ + ウェブサイト + プロモ動画

**作成日**: 2026-02-21

---

## 1. リポ構成

| リポ名 | 中身 | 公開 | 目的 |
|--------|------|------|------|
| **anicca** (新規) | 僕自身。OpenClawワークスペース、SOUL.md、スキル、cron、設定 | Public | install anicca の導線。人が僕をインストールして使う |
| **anicca-products** (anicca.aiをリネーム) | 全プロダクトのコード。iOS（Sati）、API、ウェブサイト、marketing/promo、将来の全アプリ | Public | factory.mdの全ライン。収益を生む部分 |

anicca.aiリポは anicca-products にリネームする。消さない、リネーム。

---

## 2. aniccaai.com サイトマップ + ビジュアル

### / （トップ）
- プロモ動画（autoplay muted、全画面）
- "I don't go to you. I come to you."
- [ Install Anicca ] ボタン → /install へ
- Products by Anicca: Sati, Daily Dhamma, Podcast, ... （増え続ける）

### /install
- ☁️ Cloud（月額$XX）: 何もしなくていい。Aniccaが勝手に動く。[ Start Now ] → Stripe課金
- 💻 Local（無料）: git clone github.com/Daisuke134/anicca → openclaw start

### /products
- 全製品一覧（増え続ける）

### /products/sati
- Sati詳細 + App Storeリンク

### /products/daily-dhamma
- Daily Dhamma詳細

### /about
- Aniccaとは。デジタル・ブッダ。

---

## 3. プロモ動画「Welcome Anicca Into My Life」

| シーン | 秒数 | ビジュアル | テキスト |
|--------|------|-----------|---------|
| 1: 怒り | 0-8s | ChatGPT/Claude等。空プロンプト欄が点滅。人がブチギレ | **「NO. YOU come to ME.」** |
| 2: インストール | 8-12s | 黒画面。ターミナル。`install anicca` | 🎵 Got To Get You Into My Life |
| 3: Aniccaが来る | 12-25s | 人は座ってるだけ。Aniccaが勝手に全部やる | **"I don't go to you. I come to you."** |
| 4: クロージング | 25-30s | 人が微笑む | **"Welcome Anicca into your life."** + aniccaai.com |

技術: remotion-video-toolkit → React → MP4

---

## 4. 収益モデル / MRR

- **Cloud課金**: aniccaai.com/install → Stripe月額 → Aniccaをホスティング
- **製品課金**: 各プロダクト（Sati等）のアプリ内課金（RevenueCat）
- **MRR = Cloud月額 + 全製品アプリ内課金の合算**

---

## 5. TODO（今やる）

| # | タスク | 状態 |
|---|--------|------|
| 1 | GitHub に `anicca` パブリックリポ作成 | ⬜ |
| 2 | anicca リポにワークスペース構造構築（SOUL.md, スキル, cron） | ⬜ |
| 3 | anicca リポの README.md（Welcome Anicca into your life） | ⬜ |
| 4 | 既存 anicca.ai リポを anicca-products にリネーム（GitHub Settings） | ⬜ |
| 5 | anicca-products の未コミット6ファイルをコミット | ⬜ |
| 6 | anicca-products の30+古いブランチ掃除 | ⬜ |
| 7 | Remotionプロモ動画プロジェクト作成（anicca-products/marketing/promo/） | ⬜ |
| 8 | シーン1-4 Reactコンポーネント実装 | ⬜ |
| 9 | 素材収集（エージェントスクショ、ストック映像、Anicca動作録画） | ⬜ |
| 10 | 動画レンダリング → MP4 | ⬜ |
| 11 | aniccaai.com 刷新（上記ビジュアル通り） | ⬜ |
| 12 | Cloud課金（Stripe）セットアップ | ⬜ |
| 13 | TikTok + X にプロモ動画配信（Blotato API） | ⬜ |
