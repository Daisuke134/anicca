# OpenClaw Anicca スキル（1.6.2 SSOT）

VPS `/home/anicca/.openclaw/skills/` に配置する SKILL.md のソース。

## 初回セットアップ（完全版スキル）

trend-hunter が動くには **x-research, reddit-cli** の実行コードが必要。sync だけでは不足。

```bash
scp scripts/openclaw-vps/install-full-skills-on-vps.sh anicca@VPS:~/
ssh anicca@VPS 'bash ~/install-full-skills-on-vps.sh'
```

## 配置手順

### Skills
```bash
rsync -av --exclude='jobs.json' openclaw-skills/ ${VPS_USER}@${VPS_HOST}:/home/anicca/.openclaw/skills/
```

### Cron jobs (jobs.json)
OpenClaw の cron は `~/.openclaw/cron/jobs.json` を参照。**Gateway 停止中のみ**手動編集可能。
```bash
# 1) Gateway を停止
ssh ${VPS_USER}@${VPS_HOST} 'systemctl --user stop openclaw-gateway.service || true'

# 2) jobs.json を送信（19ジョブ＝TODO-NEXT準拠）
scp openclaw-skills/jobs.json ${VPS_USER}@${VPS_HOST}:/home/anicca/.openclaw/cron/jobs.json

# 3) Gateway を再起動
ssh ${VPS_USER}@${VPS_HOST} 'systemctl --user start openclaw-gateway.service'
```
※ `jobs.json` のフォーマットは OpenClaw の cron.add と同等。Gateway が別形式で書く場合は `openclaw cron add` で逐次登録すること。

## スキル一覧
| スキル | Cron |
|--------|------|
| ops-heartbeat | */5 * * * * |
| mission-worker | * * * * * |
| trend-hunter | 0 */4 * * * |
| suffering-detector | */5 * * * * |
| x-poster | 0 9, 21 * * * (morning/evening) |
| tiktok-poster | 0 9, 21 * * * |
| app-nudge-sender | 0 9, 14, 20 * * * |
| roundtable-standup | 0 9 * * * |
| roundtable-memory-extract | 55 8 * * * |
| roundtable-initiative-generate | 5 9 * * * |
| hookpost-ttl-cleaner | 0 3 * * * |
| sto-weekly-refresh | 0 3 * * 0 |
| autonomy-check | 0 3 * * * |

## Anicca Daily Report（日次メトリクス投稿）

**このレポには含まれていません。** あのフォーマット（📊 Anicca Daily Report, APP STORE, REVENUECAT, FUNNEL, 変換率, :person_in_lotus_position: Anicca Metrics Bot）を出しているのは **daily-metrics-reporter** スキルです。

| 場所 | 説明 |
|------|------|
| **openclaw-skills/** | なし。`daily-memory` は別（学び・日記の記録用）。 |
| **VPS** | 仕様上は `~/.openclaw/skills/daily-metrics-reporter/` または OpenClaw **bundled** スキル（npm 同梱）。 |
| **Cron** | 仕様では 05:00 JST。当リポの `jobs.json` には未登録（Gateway 側 or 別 crontab の可能性あり）。 |

フォーマット仕様: `.cursor/plans/ios/1.6.2/metrics-ops-spec.md`
