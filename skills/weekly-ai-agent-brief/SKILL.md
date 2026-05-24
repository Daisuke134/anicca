---
name: weekly-ai-agent-brief
description: "ダイス専用 weekly AI agent intelligence brief。毎週日曜 18:00 JST に過去 7 日の latest-papers + dais-x-feed-digest + mufg-epoc-watcher を集約 → A4 1 ページ markdown brief + Marp slides outline を生成し Slack #metrics へ投稿。ICLR 2026 Sao Paulo 発表素材 + MUIT 社内勉強会の両用。"
metadata: {"openclaw":{"emoji":"📊","os":["darwin","linux"]}}
---

# weekly-ai-agent-brief

## 目的
ダイスが
- (a) ICLR 2026 Sao Paulo presentation
- (b) MUIT 社内 weekly 勉強会
- (c) 上司・同僚への週次 brief

の 3 用途で同じ素材を回せるよう、**過去 7 日に蓄積された 3 つの workspace データを 1 ページ markdown + Marp slides outline に圧縮する** skill。

人間が毎週 1 時間かけて作る素材を 5 分で土台まで作る。最終仕上げは Dais 本人が 30 分で行う前提。

## 入力 (過去 7 日分を集約)
| ソース | パス |
|--------|------|
| AI agent 論文 | `~/.openclaw/workspace/latest-papers/papers_YYYY-MM-DD.json` (last 7) |
| Dais X feed digest | `~/.openclaw/workspace/dais-x-feed-digest/digest_YYYY-MM-DD.json` (last 7) |
| MUFG/EPOC daily brief | `~/.openclaw/workspace/mufg-epoc-watcher/brief_YYYY-MM-DD.json` (last 7) |

3 ソースとも JSON。最新の 7 日分を読んで concat → Grok synthesis に投入。

## 出力
| 種類 | フルパス |
|------|----------|
| A4 1 ページ brief | `~/.openclaw/workspace/weekly-ai-agent-brief/brief_YYYY-MM-DD.md` |
| Marp slides outline | `~/.openclaw/workspace/weekly-ai-agent-brief/slides_YYYY-MM-DD.md` |
| Slack | チャンネル `#metrics` ({{profile.channels.reportChannel}})、prefix `📊 [Weekly AI Agent Brief]` |

## brief.md フォーマット (Grok 出力)
```markdown
# Weekly AI Agent Brief — Week of YYYY-MM-DD

## 🎯 Top 3 takeaways (1 line each)
1. ...
2. ...
3. ...

## 📚 Key papers (3-5)
| Title | Authors | Why it matters | Anicca/EPOC application |
|-------|---------|---------------|-------------------------|
| ... | ... | ... | ... |

## 🚀 Product / agent launches (3-5)
- ...

## 🛡️ Safety & alignment (2-3)
- ...

## 🏦 Banking / financial services AI (2-3)
- ...

## 🎤 Use this week
- ICLR Sao Paulo: which slide(s) to add
- MUIT 勉強会: 1 行 talking point
- Anicca: 1 個 implementation idea

## 🔮 Next-week prediction (3 lines)
...
```

## slides.md フォーマット (Marp markdown)
```markdown
---
marp: true
theme: default
paginate: true
---

# Weekly AI Agent Brief
## Week of YYYY-MM-DD

By Dais (MUIT data science / ICLR 2026 Sao Paulo)

---

## Top 3 takeaways
- ...
- ...
- ...

---

## Paper #1: ...
- ...

---

(以下 paper / launch / safety / banking で 1 slide ずつ、計 8-10 slides)
```

## 必須 env
| キー | 用途 |
|------|------|
| `XAI_API_KEY` | Grok 4 fast (synthesis、tools 不要) |
| `SLACK_BOT_TOKEN` | Slack 投稿 |
| `SLACK_CHANNEL_ID` | 投稿先 (default `{{profile.channels.reportChannel}}` = #metrics) |

## 実行
```bash
bash ~/.openclaw/skills/weekly-ai-agent-brief/run.sh
```

## Cron
| ジョブ ID | スケジュール | TZ |
|-----------|-------------|-----|
| `weekly-ai-agent-brief-sunday` | `0 18 * * 0` (毎週日曜 18:00 JST) | Asia/Tokyo |

日曜の夜に Slack で読んで月曜の社内勉強会・1on1 に持ち込む。

## コスト
| 項目 | 値 |
|------|-----|
| 1 synthesis call (Grok 4 fast、long input) | ~$0.10 |
| 週 | ~$0.10 |
| 月 | ~$0.50 |

## Idempotency
同日再実行時は brief.md / slides.md 上書き + Slack 新規投稿 2 通 (brief + slides)。

## 失敗時
- 入力ファイルが 7 日分揃わなくても、存在する分だけ集約して続行 (status: degraded)
- Grok API error → status: error。Slack に error 投稿。

## 検証 (Skill 開発 5 ステップ)
| Step | 確認 |
|------|------|
| 1 | 手動: `bash run.sh` → brief.md / slides.md / Slack 2 投稿確認 |
| 2 | skill 化 (この SKILL.md 完成) |
| 3 | skill 経由再走で同じ output |
| 4 | today cron で gateway 経由実行確認 |
| 5 | 翌日曜 18:00 weekly cron 実行確認 |
