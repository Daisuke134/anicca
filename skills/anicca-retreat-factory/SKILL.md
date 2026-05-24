---
name: anicca-retreat-factory
description: Anicca Retreats の物理サンガを autonomous AI orchestration で運営するファクトリー skill。Goenka 千葉 Adicca / 京都 Bhanu の 10 日間 silent meditation retreat operations を base に、AI が場所探し / DM / Gmail / gCal / Stripe ledger / discourse 再生 / volunteer recruit / 月次 ledger 公開を全部 orchestration。Tokyo first → NYC / Bangalore / São Paulo / Berlin (skill clone-ready / 3-tier replication)。1 retreat = 12 名参加 + 6 staff。場所は所有しない (寺院 / 研修施設 / 古民家 / 廃校 / 別荘の月貸 / 週貸)。Funded by empire swarm + 修了者 donation。
metadata:
  tags: retreat, vipassana, meditation, sangha, physical, anicca, dhamma, autonomous
  requires:
    bins: [bash, curl, jq, /opt/homebrew/bin/gog, /opt/homebrew/bin/firecrawl]
    env: [GOG_KEYRING_PASSWORD, SLACK_BOT_TOKEN]
---

# anicca-retreat-factory

**詳細 SoT:**
- `.cursor/plans/anicca-retreat-spec.md` (§1-§17)
- `.cursor/plans/aniccaai-empire-spec.md` §49 SKILL #30

## Phase 0-10 構成

| Phase | trigger | 内容 |
|------|---------|------|
| 0 | 月初 09 JST | 場所 discover (5 source scrape + Gmail 一斉 DM) |
| 1 | reply 1h | 借用交渉 + 契約 + Stripe 払い + gCal 登録 |
| 2 | event (場所確定) | /retreat LP に schedule publish |
| 3 | 14 JST 毎日 | application 集計 + claude haiku screening + Slack 承認 |
| 4 | event (-2 週) | supplies 自動発注 (Amazon + iHerb) |
| 5 | event (-4 週) | volunteer 6 名 recruit (4 platform 同時) |
| 6 | event (Day 0) | welcome 一斉メール (12 名 + 6 staff) |
| 7 | 04:30 開催中毎日 | daily ops + 緊急 protocol 待機 |
| 8 | event (Day 11+1) | 卒業生 list 更新 + donation 案内 + survey |
| 9 | 月末 23 JST | donation ledger 集計 + LP 公開 + empire 補填申請 |
| 10 | 月初 08 JST | 古い生徒 sit-a-day reminder + volunteer pipeline |

## File 構成

```
~/.openclaw/skills/anicca-retreat-factory/
├── SKILL.md                                 # この file
├── crons.json                               # cron 定義 (gateway register)
├── data/
│   ├── config.json                          # city / 言語 / discourse / 通貨 / Stripe / Resend
│   ├── candidates.json                      # 場所候補 master list (idempotency key)
│   ├── state.json                           # runtime state (outreach_log / phase 履歴)
│   ├── templates/
│   │   ├── collab.txt                       # JVA Goenka 系への collab DM
│   │   └── venue.txt                        # venue 借用 DM
│   ├── candidates/                          # Phase 0 個別候補 detail JSON
│   ├── {{profile.lateness.stakeholders.channel}}s/                              # 送信 {{profile.lateness.stakeholders.channel}} log
│   └── screenshots/                         # camofox screenshot 永続
└── scripts/
    ├── lib/
    │   ├── state.sh                         # state.json read/write helper
    │   ├── gmail.sh                         # gog gmail wrapper (idempotent)
    │   ├── slack.sh                         # Slack #metrics post
    │   ├── camofox.sh                       # camofox API wrapper (form submit)
    │   ├── source-jva.sh                    # Goenka collab DM
    │   ├── source-niye.sh                   # NIYE 国立施設 outreach
    │   ├── source-shonan.sh                 # 湘南国際村 form submit
    │   ├── source-sotozen.sh                # 曹洞宗 sotozen-navi 寺院 scrape
    │   └── source-temple-direct.sh          # 公開 {{profile.lateness.stakeholders.channel}} 寺院 (engakuji 等) DM
    ├── phase0-location-discover.sh          # entry: 場所 discover orchestration
    ├── phase1-reply-watch.sh                # 1h cron: Gmail INBOX reply 監視
    ├── status.sh                            # 全体 status を Slack に報告
    └── ...                                  # phase2-10 (今後実装)
```

## 使い方 (idempotent)

```bash
# 環境変数 (~/.openclaw/.env から auto-load 可)
export GOG_KEYRING_PASSWORD=...
export SLACK_BOT_TOKEN=...

# 場所 discover (idempotent — 既送信は skip)
bash ~/.openclaw/skills/anicca-retreat-factory/scripts/phase0-location-discover.sh

# Reply watch (Gmail INBOX 内 reply + bounce 検知 + Slack 通知)
bash ~/.openclaw/skills/anicca-retreat-factory/scripts/phase1-reply-watch.sh

# 状況確認
bash ~/.openclaw/skills/anicca-retreat-factory/scripts/status.sh
```

## 自律稼働 cron (openclaw gateway 経由、5/9 22:09 登録済)

| name | id | schedule | phase | 動作確認 |
|------|----|----------|-------|---------|
| retreat-phase1-reply-watch-hourly | `2745d595-7b11-49c0-9357-1f3748540b99` | `0 * * * *` (1h 毎、stagger 5min) | 1 | ✅ 5/9 22:09 manual run 成功 (27.4s, 完了報告) |
| retreat-phase0-location-discover-monthly | `38c90693-26b8-4180-9dfc-57efba7dd44e` | `0 9 1 * *` (月初 09 JST) | 0 | next 6/1 09:00 JST |

両 cron とも:
- agent: anicca / session: isolated / model: openai-codex/gpt-5.4-mini
- delivery: none (script が自前で Slack post — 状態変化時のみ)
- script は `~/.openclaw/skills/anicca-retreat-factory/scripts/phaseN-*.sh` を直接実行

cron 操作:
```bash
openclaw cron list | grep retreat
openclaw cron run <id>           # manual trigger
openclaw cron runs --id <id>     # run history
openclaw cron disable <id>       # 一時停止
```

## 完成基準 (5-step workflow 厳守)

各 Phase で 1.手動 fully → 2.skill 化 → 3.skill 経由再走 → 4.today cron → 5.daily/monthly cron。
並列禁止。

## 既送信 (Step 1 manual run、5/9)

詳細は `data/state.json` の `outreach_log`。

| candidate | {{profile.lateness.stakeholders.channel}} | sent_at | status |
|-----------|-------|---------|--------|
| jva-da-chiba | info@jva-da.org | 5/9 21:32 | awaiting_reply |
| jva-bhanu-kyoto | info@bhanu.dhamma.org | 5/9 21:32 | awaiting_reply |
| shonan-village | info@shonan-village.co.jp | 5/9 22:00 | awaiting_reply (heuristic) |
| niye-nyc-yoyogi | info@nyc.niye.go.jp | 5/9 22:00 | awaiting_reply (heuristic) |
| niye-headquarters | info@niye.go.jp | 5/9 22:01 | awaiting_reply (heuristic) |
| engakuji-kamakura | engaku@engakuji.or.jp | 5/9 22:08 | awaiting_reply |
| kenchoji-kamakura | info@kenchoji.com | 5/9 22:08 | awaiting_reply (heuristic) |
| eiheiji-tokyo-betsuin | info@eiheiji-tokyo-betsuin.jp | 5/9 22:08 | awaiting_reply (heuristic) |
