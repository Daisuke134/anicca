# Anicca プロジェクト - 開発ガイドライン

## 根本原則

**BP = 答え。オリジナル = 罪。検索不足 = 最大の罪。**
全判断に最低3回の検索（英語/日本語）→ ソース名/URL/核心の引用を付ける。引用なき判断は削除。
質問禁止。選択肢提示禁止。答えは1つ。見つからない → 一般化 → 隣接分野 → 根底原則まで掘る。

## IBA（Investigate Before Acting）

**全行動の前に実行。例外なし。** Source: Anthropic Reduce Hallucinations

| Step | やること |
|------|---------|
| 1. 検索 | 最低3回の独立クエリ（英/日）。見つからない→一般化→隣接分野 |
| 2. 引用 | 「ソース: [名前](URL) / 核心: 「原文」」。引用なし=削除 |
| 3. 実行 | BPに100%従う。オリジナルゼロ |

## 絶対ルール

| # | ルール |
|---|--------|
| 0.2 | 教訓は最も広い原則として記憶する。狭い教訓禁止 |
| 0.3 | プロジェクト知識は `.serena/memories/` に集約 |
| 0.4 | **編集したら即push。確認不要。** `git add -A && commit && push`。秘密鍵禁止 |
| 0.5 | 出力は常にテーブル形式。箇条書き単体禁止 |
| 0.6 | テストは変更した部分だけ |
| 0.7 | スペックに「任意」「optional」「推奨」禁止。全て MUST |
| 0.8 | コンテキスト50%で/compact。タスク完了即コミット |
| 0.10 | スペック100%明確になるまで実装禁止 |
| 0.11 | テキスト羅列禁止。テーブル/ASCII図/絵文字で必ずビジュアル化 |
| 言語 | **回答は常に日本語** |

## 実行環境

**Mac Mini で直接実行。SSH で自分自身に接続しない。**

| 項目 | 値 |
|------|-----|
| Mac Mini | anicca-mac-mini-1（Tailscale: 100.99.82.95） |
| MacBook SSH | `ssh cbns03@100.108.140.123` |
| anicca-products | git@github.com:Daisuke134/anicca-products.git (PUBLIC, origin) |
| anicca | https://github.com/Daisuke134/anicca (PRIVATE, pushしない) |
| VPS | 使わない（2026-02-18移行完了済み） |

## ブランチ & デプロイ

| ブランチ | 役割 | Railway |
|---------|------|---------|
| main | Production | 自動デプロイ |
| dev | 開発（trunk） | Staging自動デプロイ |
| release/x.x.x | App Store提出 | - |

**フロー:** dev → テスト → main → release/x.x.x → App Store
**Fastlane必須:** xcodebuild直接実行禁止。`cd aniccaios && fastlane <lane>`
**Greenlight:** `greenlight preflight <app_dir>` でCRITICAL=0確認してから提出

## プロジェクト概要

**Anicca** = プロアクティブ行動変容エージェント（デジタル・ブッダ）

| 項目 | 値 |
|------|-----|
| iOS | Swift/SwiftUI (iOS 15+, Xcode 16+) |
| API | Node.js/Express (Railway) |
| DB | PostgreSQL/Prisma |
| 決済 | RevenueCat ($9.99/月, $49.99/年) |
| 分析 | Mixpanel（Anicca専用。mobileapp-builder factory アプリには入れない — Rule 12/17） |
| E2E | Maestro |
| Agent | OpenClaw（詳細: `agent_docs/openclaw_integration.md`） |

**ディレクトリ:** `aniccaios/` iOS | `apps/api/` API | `.cursor/plans/` 仕様書 | `.serena/memories/` メモリ

## ツール優先順位

| タスク | 使うツール | 禁止 |
|--------|-----------|------|
| Web検索/URL取得 | Firecrawl CLI: `/opt/homebrew/bin/firecrawl scrape <url> markdown` | WebSearch, WebFetch |
| コード検索/編集 | Serena MCP: `mcp__serena__*` | 単純Grep/Read（Serena可能時） |
| iOS E2E | `mcp__maestro__*` | maestro CLI直接 |
| ビルド/テスト | `cd aniccaios && fastlane <lane>` | xcodebuild直接 |

## 参照先（必要時にRead）

| ファイル | いつ読む |
|---------|---------|
| `.cursor/plans/reference/secrets.md` | デプロイ・Secret設定時 |
| `.cursor/plans/reference/infrastructure.md` | インフラ・Railway作業時 |
| `agent_docs/openclaw_integration.md` | OpenClaw作業時（設定・gateway・認証・TUI） |

---

最終更新: 2026年3月5日
