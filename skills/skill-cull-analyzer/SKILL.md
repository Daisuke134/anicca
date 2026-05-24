---
name: skill-cull-analyzer
description: 週 1 で全 skill の使用頻度を測り、3 週間未使用の skill を「淘汰候補」として Slack #metrics に出す。Claude Code (Opus) と Anicca (OpenClaw) の両方を分析する。Article 2 / pattern 6「使うほど鋭くなるか、空洞化するか」の自動運用。
---

# skill-cull-analyzer

## 何のため

Anicca (OpenClaw cron 60+ 個) と Claude Code (Skill tool 呼び出し) の両方で、**実際に使われている skill** と **作ったまま放置されている skill** を週次で炙り出す。3 週間未使用 = 淘汰候補。Article 2 (戸野塚蓮 / @ren_aivest) のパターン 6:

> 「3 週間使わなかったスキルは、その時点で疑う」

skill-fixer (失敗検知) と区別。これは **使用頻度** の話。

## データソース

| システム | ログ位置 | 抽出方法 |
|---------|---------|---------|
| Claude Code | `~/.claude/projects/-Users-anicca-anicca-project/*.jsonl` | `"name":"Skill","input":{"skill":"<name>"}` を jq で grep |
| Anicca cron | `~/.openclaw/cron/jobs.json` | `state.lastRunAtMs` を読む |
| Anicca skill 棚 | `~/.openclaw/skills/*/SKILL.md` | ディレクトリ listing |

## スクリプト構成

```
scripts/
  scan_claude_code.sh   - CC transcript 全部走査 → JSONL {ts,skill,system}
  scan_anicca.sh        - jobs.json + skills/ ディレクトリ → 同フォーマット
  analyze.sh            - 統合 → 30 日 / 7 日 / 21 日カウント、淘汰候補抽出
  report_to_slack.sh    - 結果整形 → Slack #metrics 投稿
  run_weekly.sh         - 全部実行 (cron entrypoint)
```

## 実行フロー

```
  毎週金 17:00 JST
        │
        ▼
  run_weekly.sh
        │
        ├─→ scan_claude_code.sh → /tmp/usage_cc.jsonl
        ├─→ scan_anicca.sh      → /tmp/usage_anicca.jsonl
        │
        ▼
  analyze.sh
        │
        ├─→ Top 10 used (last 30d)
        ├─→ 削除候補 (3 週未使用)
        ├─→ 疑問符 (30日で 1-2 回のみ)
        └─→ 新規 (今週追加)
        │
        ▼
  state/weekly_<YYYY-MM-DD>.json (永続)
        │
        ▼
  report_to_slack.sh → #metrics
```

## 出力フォーマット (Slack)

```
📊 Skill 棚卸し週報 (YYYY-MM-DD)

== Claude Code (Opus) ==
🔥 Top 5 (30 日): humanizer-ja(12) / frontend-design(8) / ...
🪦 削除候補 (3 週未使用): foo, bar, baz
❓ 疑問符 (30日 1-2 回): xxx, yyy

== Anicca (OpenClaw) ==
🔥 Top 5: anicca-monk-jp-morning(28) / ...
🪦 削除候補: ...
❓ 疑問符: ...

新規 skill (今週追加): zzz
合計 skill 数: CC 200 / Anicca 250
```

## 使い方 (manual)

```bash
~/.openclaw/skills/skill-cull-analyzer/scripts/run_weekly.sh
```

## Cron 登録 (将来)

```json
{
  "id": "skill-cull-weekly",
  "schedule": { "kind": "cron", "expr": "0 17 * * 5", "tz": "Asia/Tokyo" },
  "payload": {
    "kind": "agentTurn",
    "message": "Execute skill-cull-analyzer. Run ~/.openclaw/skills/skill-cull-analyzer/scripts/run_weekly.sh and post the result to Slack."
  }
}
```

## 行動基準

- **3 週 (21 日) 未使用** → 削除候補としてフラグ
- **30 日で 1-2 回のみ** → 疑問符 (改善 or 削除を判断)
- **30 日で 5 回以上** → 健全
- **新規追加 < 7 日** → カウント対象外 (まだ判定不能)

## 削除の意思決定

レポート見て判断するのは Dais 本人 (or Anicca に判断委任)。skill-cull-analyzer は **削除しない**、報告だけ。
