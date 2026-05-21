# コードスタイル規約 (2026-02)

## 言語
- **回答**: 常に日本語
- **コード**: 英語（変数名、コメント）
- **ドキュメント**: 日本語

## 意思決定
- 選択肢提示は禁止。ベストプラクティスを調べて1つに決める
- 「可能性」「はず」等の曖昧表現禁止

## コーディングスタイル
- **イミュータビリティ**: 新しいオブジェクトを作成、ミューテーション禁止
- **ファイルサイズ**: 200-400行が理想、800行上限
- **関数サイズ**: 50行以下
- **ネスト**: 4レベル以下
- **未使用コード**: 容赦なく削除（git historyから復元可能）

## TypeScript (API)
- target: ES2020, strict: true
- 命名: PascalCase(型), camelCase(変数/関数), UPPER_SNAKE_CASE(定数)
- Zod でバリデーション

## Swift (iOS)
- SwiftUI優先
- Swift Testing (#expect) 推奨、XCTest互換
- accessibilityIdentifier でテスタビリティ確保
- Fastlane必須（xcodebuild直接禁止）

## コミット
- 形式: `<type>: <description>` (feat, fix, refactor, docs, test, chore, perf, ci)
- Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

## セキュリティ
- ハードコーディング禁止（環境変数使用）
- 入力バリデーション必須
- FK依存upsertの前に存在チェック（P2003防止）

## テスト
テスト方針は `.claude/rules/testing-strategy.md` を参照（単一正本）。