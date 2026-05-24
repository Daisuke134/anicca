---
name: tt-draft-graduator
description: Auto-flip TikTok factories from UPLOAD (draft) mode to DIRECT_POST (live) after N days of warmup. Reads from `~/.openclaw/state/tt-posting-state.json` (central SoT). Replaces per-factory `.env WARMUP_MODE` flags. TikTok-only — IG/X/YT post directly from day 1. Use when triggered by tt-draft-graduator-daily cron at 04:30 JST, or manually as `bash scripts/check.sh`.
metadata:
  tags: tiktok, posting-mode, automation, warmup, graduator
  requires:
    bins: [bash, jq, date]
---

# tt-draft-graduator

Central state machine for TikTok posting mode across all factories.

## Why

| 旧 (悪) | 新 (採用) |
|--------|---------|
| `.env WARMUP_MODE=true` 各 factory が独自管理 | 中央 `~/.openclaw/state/tt-posting-state.json` 一元管理 |
| 手動で `false` に切替 | N 日経過で自動 flip |
| 全プラットフォーム同じ扱い | TT のみ。IG/X/YT は day 1 DIRECT |

## State schema

`~/.openclaw/state/tt-posting-state.json`:

```json
{
  "<factory-name>": {
    "started_at": "ISO 8601",
    "draft_days": 3,
    "in_draft": true,
    "auto_graduated_at": null
  }
}
```

## Cron

| 項目 | 値 |
|------|---|
| name | `tt-draft-graduator-daily` |
| schedule | cron `30 4 * * *` JST |
| script | `bash ~/.openclaw/skills/tt-draft-graduator/scripts/check.sh` |

## How factories consume

```bash
DRAFT=$(jq -r --arg key "$FACTORY" '.[$key].in_draft // "false"' ~/.openclaw/state/tt-posting-state.json)
[ "$DRAFT" = "true" ] && TT_METHOD="UPLOAD" || TT_METHOD="DIRECT_POST"
```

IG / X / YT は条件分岐なしで常に `DIRECT_POST`。

## Adding a new factory

```bash
jq '."new-factory" = {"started_at":"'"$(date -u +%FT%TZ)"'","draft_days":3,"in_draft":true,"auto_graduated_at":null}' \
  ~/.openclaw/state/tt-posting-state.json > /tmp/s && mv /tmp/s ~/.openclaw/state/tt-posting-state.json
```

3 日後 04:30 cron が auto-flip → 永遠に手動操作なし。
