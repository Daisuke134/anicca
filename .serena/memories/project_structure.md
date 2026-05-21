# プロジェクト構造 (2026-02-08)

## ルートディレクトリ
```
anicca-project/
├── aniccaios/              — iOSアプリ本体 (Swift/SwiftUI)
│   ├── aniccaios/          — ソースコード
│   │   ├── Views/          — SwiftUI画面
│   │   ├── Services/       — ビジネスロジック
│   │   ├── Models/         — データモデル
│   │   ├── Onboarding/     — オンボーディング4ステップ
│   │   ├── Notifications/  — 通知スケジューリング
│   │   ├── Authentication/ — Apple Sign-in, DeviceID
│   │   ├── DesignSystem/   — テーマ・UIコンポーネント
│   │   ├── Components/     — 再利用可能UI
│   │   ├── Extensions/     — Swift拡張
│   │   ├── Resources/      — ローカライズ(6言語), プロンプト, サウンド
│   │   └── Security/       — Keychain
│   ├── aniccaiosTests/     — Unit/Integration テスト
│   └── fastlane/           — Fastfile (ビルド/テスト/リリース)
├── apps/
│   ├── api/                — Node.js APIサーバー (Railway)
│   │   ├── src/            — ソースコード
│   │   │   ├── routes/     — エンドポイント
│   │   │   ├── services/   — ビジネスロジック
│   │   │   ├── jobs/       — Cronジョブ
│   │   │   ├── agents/     — LLMエージェント(Commander)
│   │   │   └── middleware/ — 認証・バリデーション
│   │   └── prisma/         — スキーマ・マイグレーション
│   └── landing/            — ランディングページ (Netlify)
├── daily-apps/             — Daily Dhamma等
├── maestro/                — E2Eテスト (Maestro YAML)
├── scripts/                — ユーティリティスクリプト
├── .claude/                — Claude Code設定
│   ├── rules/              — 開発ルール (自動読み込み)
│   └── skills/             — スキル定義
├── .cursor/plans/          — 仕様書・計画
├── .kiro/                  — ステアリング・スペック
└── .serena/memories/       — Serenaメモリ（プロジェクト知識ベース）
```

## 主要エントリーポイント
| アプリ | ファイル |
|--------|---------|
| iOS | `aniccaios/aniccaios/aniccaiosApp.swift` |
| API | `apps/api/src/server.js` |
| Landing | `apps/landing/` |

## DB
- **メイン**: Railway PostgreSQL + Prisma ORM (25テーブル)
- **補助**: Supabase (レガシー、段階的廃止中)

## テスト実行
- Unit/Integration: `cd aniccaios && fastlane test`
- E2E: `maestro test maestro/`
- xcodebuild直接実行は禁止
