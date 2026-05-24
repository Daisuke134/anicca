---
name: tuning-skills
description: v0.2.0 — Python edition. Diagnose cron failures from runs.sqlite + jobs.json, propose repair patches via a known-fix table. Runs alongside production v0.1.0 (skill-log-analyzer/skill-fixer agent). Use when tuning-skills-nightly cron fires.
---

# tuning-skills (Python edition) SKILL

## バージョン

| Version | 実体 | 状態 |
|---------|------|------|
| v0.1.0 | `~/.openclaw/skills/skill-log-analyzer/` (skill-fixer agent) | **PRODUCTION** — 触らない |
| v0.2.0 | `~/.openclaw/skills/tuning-skills/` (this skill, Python scripts) | **LIVE (gated)** — 30-night audit PASSED 2026-05-19 (222 tickets, 0% manual_review << 20%). `--apply` allowed: MAX 1 cron/night, post-apply `openclaw cron run <id>` re-verify required (precept 5). |

**v0.2.0 = Python edition; production v0.1.0 = `skill-log-analyzer` agent-only. Both run in parallel until v0.2.0 has 30 nights of clean ticket history, then v0.1.0 is deprecated.**

## 概要

毎夜 02:00 JST に `runs.sqlite` + `jobs.json` を読み、`consecutiveErrors >= 1` の cron を抽出して ticket を書く。known-fix テーブルにマッチすれば repair patch を生成し、`--apply` 許可（30夜監査通過 2026-05-19）。1夜1cronまで、適用後に該当cronを `openclaw cron run` で再走し成功するまで次へ進まない（precept 5）。

## ウィザード（初回起動時）

| フィールド | デフォルト | 説明 |
|-----------|-----------|------|
| `cron.master_path` | `~/.openclaw/cron/jobs.json` | jobs.json のパス |
| `runs.db_path` | `~/.openclaw/tasks/runs.sqlite` | 実行履歴 DB |
| `slack.metrics_channel` | `{{profile.channels.reportChannel}}` | レポート通知先 |
| `tuning.dlq_threshold` | `1` | この値以上の `consecutiveErrors` で ticket 化 |
| `tuning.escalate_to` | `{{profile.contact.personalEmail}}` | 自動修復不能時のエスカレ先 |

## Known-fix テーブル（初期）

このセッションで実際に観測された3パターンから開始:

| パターン | マッチ条件 | 修正アクション |
|---------|-----------|---------------|
| `slack-target-missing` | エラー文字列に `target.*not found` または `channel.*invalid` を含む | `delivery.to` を `channel:{{profile.channels.reportChannel}}` に書き換え |
| `gpt-5.5-model-not-found` | エラーに `model_not_found` + `gpt-5.5` を含む | `payload.model` を `openai-codex/gpt-5.4-mini` に置換 |
| `edit-failed-stale-path` | エラーに `Edit failed` + `path` を含む | ticket に `manual_review_required: true` を立て、自動修復しない |

新しいパターンは `~/.openclaw/skills/tuning-skills/known_fixes.json` に追記して拡張。

## スクリプト

| スクリプト | 役割 | モード |
|-----------|------|------|
| `scripts/diagnose.py` | runs.sqlite から失敗 cron を抽出、ticket JSON を `tickets/<ts>-<skill>.json` に出力 | 常時 read-only |
| `scripts/repair.py` | ticket を読み、known-fix を当て、diff を `repairs/<ts>-<skill>.diff` に書く | `--dry-run` (default), `--apply`, `--undo` |

## ファイル

| 項目 | パス |
|------|------|
| ticket 出力 | `~/.openclaw/workspace/tuning-skills/tickets/` |
| repair diff | `~/.openclaw/workspace/tuning-skills/repairs/` |
| known-fix table | `~/.openclaw/skills/tuning-skills/known_fixes.json` |
| ログ | `~/.openclaw/logs/tuning-skills/` |

## クロン

| cron | schedule | mode |
|------|----------|------|
| `tuning-skills-nightly` | `0 2 * * *` JST | diagnose + `repair.py --apply` MAX 1 cron/night + post-apply re-verify |
| `tuning-skills-weekly-summary` | `0 9 * * 0` JST (Sun) | 直近7日 ticket を集計して Slack に投稿 |

## Slack 報告

週次要約を送る場合は `channel:{{profile.channels.reportChannel}}` を明示する。デフォルト送信先には依存しない。

## 30夜運用

30夜監査 2026-05-19 通過（222 tickets, manual_review 0%）。`repair.py --apply` 可。**1夜1cron**、適用後に該当cronを `openclaw cron run` で再走し成功確認するまで次へ進まない。失敗したら即 `--undo`。

## 絶対禁止

| 禁止 | 理由 |
|------|------|
| 1夜に2cron以上 `--apply` | 一括適用は precept 5 違反。1cronずつ・再走確認必須 |
| skill-log-analyzer / skill-fixer cron を触る | production だから |
| ticket を書かずに repair する | audit trail がなくなる |
