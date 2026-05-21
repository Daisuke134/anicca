# task: App Store Connect API リリース自動化

## 出典
X投稿（日本語記事）— ASC APIでプロモーションテキスト＋リリースノートを自動化

## 問題
バージョン更新のたびに：
1. プロモーションテキストを全言語分、前バージョンから手動コピペ
2. リリースノートを全言語分手入力
→ 毎回同じ作業。コマンド一発で終わるべき。

## 解決策

### 1. プロモーションテキスト自動コピー
- ASC APIでライブ版のプロモテキストを全言語取得
- 編集可能な新バージョンを自動検出
- PATCHリクエストで各言語に一括コピー
- iOS/iPadOS + macOS両対応

### 2. リリースノート自動生成
- gitログ分析 → 前バージョン以降の主要変更を特定
- 全言語のリリースノートを自動生成
- ASC APIでwhatsNewフィールドを一括更新

## セットアップ（初回のみ）
環境変数:
```
ASC_ISSUER_ID="your-issuer-id"
ASC_KEY_ID="your-key-id"
ASC_PRIVATE_KEY_PATH="/path/to/AuthKey_XXXXX.p8"
ASC_APP_ID="6755129214"
```
- ASC → ユーザーとアクセス → 統合 → App Store Connect API → キーを生成
- .p8ファイルのダウンロードは1回きり！

## 技術スタック
- bash + Python (PyJWT) でJWT認証
- 初回実行時にPython仮想環境を自動セットアップ
- Claude Codeスキル化: `.claude/skills/asc-promo-copy/SKILL.md`

## Aniccaへの適用
- App ID: 6755129214
- 次回リリース: 1.4.0
- 対応言語: 日本語 + 英語 + 他（要確認）
- night-builder実装時: スクリプト作成 + .p8キー設定 + スキル化

## 事前にDaisがやること
- [ ] ASC APIキーを生成（.p8ダウンロードは1回きり）
- [ ] Issuer ID, Key IDをメモ
- [ ] .p8ファイルをMacの安全な場所に保存
