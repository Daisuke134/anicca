# App Store Connect メタデータ入力ワークフロー

## 概要
App Store Connect MCPを使ってアプリのメタデータを自動入力するワークフロー。

## 前提条件
- App Store Connect MCPが設定済み（~/.claude.json）
- API Key (P8ファイル) が存在すること

## ワークフロー

### 1. アプリ一覧取得
```
mcp__app-store-connect__list_apps
```

### 2. アプリ情報取得（バージョンID取得）
```
mcp__app-store-connect__get_app_info
  appId: "アプリID"
  include: ["appStoreVersions", "appInfos"]
```
→ `appStoreVersions` から `id` を取得

### 3. ローカライゼーションID取得
**注意**: MCPの `list_app_store_version_localizations` は動作しない（API制限）

直接APIを叩く必要あり:
```javascript
// /tmp/get_localizations.js
const jwt = require('jsonwebtoken');
// ... JWT生成してAPIコール
// GET /v1/appStoreVersions/{versionId}/appStoreVersionLocalizations
```

### 4. メタデータ更新
```
mcp__app-store-connect__update_app_store_version_localization
  localizationId: "取得したID"
  field: "description" | "keywords" | "promotionalText" | "whatsNew" | "supportUrl" | "marketingUrl"
  value: "値"
```

**注意点**:
- `whatsNew` は初回バージョン(1.0)では設定不可（アップデート時のみ）
- 複数フィールドは並列で更新可能

## 更新可能フィールド一覧
| フィールド | 説明 | 制限 |
|-----------|------|------|
| description | アプリ説明文 | 4000文字 |
| keywords | 検索キーワード | 100文字、カンマ区切り |
| promotionalText | プロモーションテキスト | 170文字 |
| whatsNew | 新機能 | 初回バージョン不可 |
| supportUrl | サポートURL | 必須 |
| marketingUrl | マーケティングURL | 任意 |

## MCPで対応できない項目（手動）
1. **スクリーンショット** - Sleek等で作成してApp Store Connectでアップロード
2. **ビルド選択** - TestFlightビルドをバージョンに紐付け
3. **年齢制限設定** - 質問に回答
4. **アプリ審査ノート** - Review Notes
5. **Privacy Policy URL** - アプリレベルで設定（バージョンレベルではない）

## URL構成（aniccaai.com）
ランディングページ構成:
```
/apps/landing/app/
├── dailydharma/
│   └── privacy/page.tsx    → /dailydharma/privacy
├── privacy/
│   ├── page.tsx            → /privacy (Anicca用)
│   ├── en/page.tsx         → /privacy/en
│   └── ja/page.tsx         → /privacy/ja
├── support/
│   ├── page.tsx            → /support
│   ├── en/page.tsx         → /support/en
│   └── ja/page.tsx         → /support/ja
└── terms/page.tsx          → /terms
```

### Daily Dharma用URL
- Privacy Policy: `https://aniccaai.com/dailydharma/privacy`
- Support: `https://aniccaai.com/support`（共通）または専用ページ作成
- Marketing: `https://aniccaai.com/dailydharma`

## デプロイ
- Netlify連携済み
- `main`ブランチにpushで自動デプロイ

## 参照ファイル
- メタデータ定義: `/daily-apps/daily-dhamma-app/app-store-metadata.md`
- リリースTODO: `/daily-apps/daily-dhamma-app/TODO_RELEASE.md`
