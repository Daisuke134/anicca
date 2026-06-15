---
name: mufg-epoc-watcher
description: "ダイス専用 MUIT/MUFG EPOC project 周辺 AI agent intel daily brief。毎朝 6:00 JST に Slack #metrics へ投稿。社内勉強会・上司提案・EPOC ロードマップ会議で即使えるネタを 5 ソース + EPOC 用 action 3 件で配信。"
metadata: {"openclaw":{"emoji":"🏦","os":["darwin","linux"]}}
---

# mufg-epoc-watcher

## 目的
ダイスが MUIT (MUFG IT) data science department の EPOC project (Salesforce Financial Services Cloud + Tableau、2026 年度 26,000 行員へ拡大) に **会社データを一切触らずに** contribute するための daily intel brief。

OpenClaw / Anicca は MUFG データ access 不可。だから「外部世界の AI agent 動向を Dais が社内に持ち込む人間レイヤー」だけを支援する。

## 5 テーマ
| ID | テーマ |
|----|--------|
| salesforce_agentforce | Salesforce Agentforce 360 / Financial Services Cloud (banking) |
| banking_ai_deployment | 大手銀行 AI agent deployment (JPM/Goldman/HSBC/DBS/Citi/MUFG/SMBC/Mizuho/Nomura) |
| ai_safety_finance | AI safety / alignment / regulation (EU AI Act / 金融庁 / BIS / OCC) |
| anthropic_enterprise | Anthropic / Claude / Constitutional AI in enterprise & banking (Petri/Mythos 含む) |
| ai_agent_crm_productivity | AI agent x CRM productivity (Salesforce/HubSpot/MS Dynamics) |

各テーマに「👉 EPOC への示唆」1 行付き。最後に **「EPOC contribution 案 3 件」** セクション (synthesis) で本日の actionable items 3 つを生成。

## 必須 env
| キー | 用途 |
|------|------|
| `XAI_API_KEY` | xAI Grok Responses API (x_search tool) |
| `SLACK_BOT_TOKEN` | Slack 投稿 |
| `SLACK_CHANNEL_ID` | 投稿先 (default `C091G3PKHL2` = #metrics) |

## ソース制限
**xAI Grok Responses API + x_search tool のみ。** Apify / web scraping / X API v2 直叩き禁止。
理由: X API v2 は credits 枯渇 (2026-05-08 確認、`dais-x-feed-digest` 同様)。

## 出力
| 種類 | フルパス |
|------|----------|
| JSON | `~/.openclaw/workspace/mufg-epoc-watcher/brief_YYYY-MM-DD.json` |
| Slack | チャンネル `#metrics` (C091G3PKHL2)、prefix `🏦 [MUFG/EPOC Daily]` |

## 実行
```bash
bash ~/.openclaw/skills/mufg-epoc-watcher/run.sh
```

## Cron
| ジョブ ID | スケジュール | TZ |
|-----------|-------------|-----|
| `mufg-epoc-watcher-daily` | `0 6 * * *` (06:00 JST) | Asia/Tokyo |

朝の通勤前に Dais が Slack で読んで、その日の 1on1 / 朝会 / 社内勉強会で使う。

## コスト
| 項目 | 値 |
|------|-----|
| 1 query (Grok 4 fast + x_search) | ~$0.07 |
| synthesis (Grok 4 fast、tools 無し) | ~$0.02 |
| 1 日 (5 query + 1 synthesis) | ~$0.37 |
| 月 | ~$11 |

## 検証 (Skill 開発 5 ステップ)
| Step | 確認 |
|------|------|
| 1 | 手動: `bash run.sh` → JSON + Slack 投稿確認 |
| 2 | skill 化 (この SKILL.md 完成) |
| 3 | skill 経由再走で同じ output |
| 4 | today cron で gateway 経由実行確認 |
| 5 | daily cron 06:00 JST 実行確認 |

## Idempotency
同日再実行時は JSON 上書き + Slack 新規投稿。並列禁止 (5 step workflow)。

## 失敗時
- Grok API error → status: error。フォールバック禁止。Slack に error 投稿。
- watchlist 5 query のうち 1 つでも空 → そのセクションは `(no result)` として続行。全失敗で初めて status: error。
