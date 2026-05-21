# Anicca プロジェクト概要

## Aniccaとは
**コアは「エージェント（意思決定主体）」**。iOSアプリはそのエージェントが人間をNudgeするための主要チャネルの1つ。
AIを活用したプロアクティブな通知（Nudge）で、ユーザーの「苦しみ」に寄り添う。

## ターゲットユーザー
6-7年間習慣化に失敗し続けている25-35歳。習慣アプリ10個以上試して全部3日坊主。「自分はダメ」と信じ込んでいるが、心の奥では変わりたい。

## 技術スタック
- **iOS**: Swift, SwiftUI (iOS 15+, Xcode 16+)
- **API**: Node.js + Express (Railway)
- **DB**: Railway PostgreSQL + Prisma ORM
- **決済**: RevenueCat + RevenueCatUI ($9.99/月, $49.99/年)
- **分析**: Mixpanel
- **AI**: OpenAI (Commander agent, 構造化出力でNudge生成)
- **E2Eテスト**: Maestro
- **実行基盤（手足）**: OpenClaw Gateway（Mac Mini常駐。Slack/Cron/Web/exec等で外部操作）

## リポジトリ構成
- `aniccaios/` — iOSアプリ本体
- `apps/api/` — APIサーバー（Railway）
- `apps/landing/` — ランディングページ（Netlify）
- `daily-apps/` — 関連アプリ（Daily Dhamma等）
- `.cursor/plans/` — 仕様書・計画
- `.kiro/` — ステアリング・スペック
- `.claude/` — Claude Code設定・ルール・スキル
- `.serena/memories/` — Serenaメモリ（プロジェクト知識ベース）

## 現在のバージョン
iOS 1.6.3 (2026年2月)
