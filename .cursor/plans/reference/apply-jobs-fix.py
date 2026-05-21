#!/usr/bin/env python3
"""cron-skills-fix に従い jobs.json を変換。結果を stdout に出力。"""
import json
import sys

DAILY_MEMORY_MESSAGE = (
    "Execute daily-memory skill. Extract today's learnings from session history, "
    "roundtable-standup の結果、および今日の cron の成功/失敗. Do NOT read AGENTS.md. "
    "Append to ~/.openclaw/workspace/daily-memory/lessons-learned.md. "
    "Write today's diary to ~/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md (use today's date). "
    "CRITICAL: Post execution summary to Slack #metrics (C091G3PKHL2)."
)

# 20:00 開始の 8 本。時刻 -> 分 時 日 月 曜
TODAY_8 = {
    "trend-hunter-5am-today": "0 20 * * *",
    "trend-hunter-5pm-today": "5 20 * * *",
    "suffering-detector-today": "10 20 * * *",
    "x-poster-morning-today": "15 20 * * *",
    "x-poster-evening-today": "20 20 * * *",
    "tiktok-poster-morning-today": "25 20 * * *",
    "tiktok-poster-evening-today": "30 20 * * *",
}

# 今日のやり直しに含めない *-today → disabled
OTHER_TODAY_DISABLE = {
    "app-nudge-morning-today",
    "app-nudge-afternoon-today",
    "app-nudge-evening-today",
    "roundtable-standup-today",
    "roundtable-initiative-generate-today",
    "autonomy-check-today",
    "daily-memory-today",
}

X_POSTER_MORNING_MSG = (
    "Execute x-poster skill. Read ~/.openclaw/workspace/hooks/9am/YYYY-MM-DD.json for today "
    "(replace YYYY-MM-DD with today's date in Asia/Tokyo). Post the postText from that file to X now. "
    "CRITICAL: After you finish, you MUST post a summary of your execution results to Slack #metrics channel (channel ID: C091G3PKHL2)."
)
X_POSTER_EVENING_MSG = (
    "Execute x-poster skill. Read ~/.openclaw/workspace/hooks/9pm/YYYY-MM-DD.json for today "
    "(replace YYYY-MM-DD with today's date in Asia/Tokyo). Post the postText from that file to X now. "
    "CRITICAL: After you finish, you MUST post a summary of your execution results to Slack #metrics channel (channel ID: C091G3PKHL2)."
)
TIKTOK_MORNING_MSG = (
    "Execute tiktok-poster skill. Read ~/.openclaw/workspace/hooks/9am/YYYY-MM-DD.json for today "
    "(replace YYYY-MM-DD with today's date in Asia/Tokyo). Post the caption and imageUrl "
    "(or generate image from imagePrompt via FAL if imageUrl empty) to TikTok via backend.blotato.com. "
    "CRITICAL: After you finish, you MUST post a summary of your execution results to Slack #metrics channel (channel ID: C091G3PKHL2)."
)
TIKTOK_EVENING_MSG = (
    "Execute tiktok-poster skill. Read ~/.openclaw/workspace/hooks/9pm/YYYY-MM-DD.json for today "
    "(replace YYYY-MM-DD with today's date in Asia/Tokyo). Post the caption and imageUrl "
    "(or generate image from imagePrompt via FAL if imageUrl empty) to TikTok via backend.blotato.com. "
    "CRITICAL: After you finish, you MUST post a summary of your execution results to Slack #metrics channel (channel ID: C091G3PKHL2)."
)

ANICCA_AUTO_DEV_TODAY = {
    "id": "anicca-auto-development-today",
    "agentId": "anicca",
    "jobId": "anicca-auto-development-today",
    "name": "anicca-auto-development (today test)",
    "schedule": {"kind": "cron", "expr": "35 20 * * *", "tz": "Asia/Tokyo"},
    "sessionTarget": "isolated",
    "wakeMode": "now",
    "payload": {
        "kind": "agentTurn",
        "message": (
            "Execute anicca-auto-development skill. Read ~/.openclaw/skills/anicca-auto-development/SKILL.md and run the skill. "
            "Write survey to workspace/anicca-auto-development/survey_YYYY-MM-DD-HH.json and result to workspace/anicca-auto-development/result_YYYY-MM-DD-HH.json. "
            "CRITICAL: Post execution summary to Slack #metrics (C091G3PKHL2)."
        ),
    },
    "delivery": {"mode": "announce", "channel": "slack", "to": "channel:C091G3PKHL2"},
    "enabled": True,
    "state": {},
}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "jobs-vps-current.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    new_jobs = []
    for j in data["jobs"]:
        jid = j.get("id", "")
        if jid in TODAY_8:
            j = dict(j)
            j["schedule"] = dict(j["schedule"])
            j["schedule"]["expr"] = TODAY_8[jid]
            j["enabled"] = True
            if jid == "x-poster-morning-today":
                j["payload"] = dict(j["payload"])
                j["payload"]["message"] = X_POSTER_MORNING_MSG
            elif jid == "x-poster-evening-today":
                j["payload"] = dict(j["payload"])
                j["payload"]["message"] = X_POSTER_EVENING_MSG
            elif jid == "tiktok-poster-morning-today":
                j["payload"] = dict(j["payload"])
                j["payload"]["message"] = TIKTOK_MORNING_MSG
            elif jid == "tiktok-poster-evening-today":
                j["payload"] = dict(j["payload"])
                j["payload"]["message"] = TIKTOK_EVENING_MSG
            new_jobs.append(j)
        elif jid in OTHER_TODAY_DISABLE:
            j = dict(j)
            j["enabled"] = False
            if jid == "daily-memory-today":
                j["payload"] = dict(j["payload"])
                j["payload"]["message"] = DAILY_MEMORY_MESSAGE
            new_jobs.append(j)
        elif jid == "daily-memory":
            j = dict(j)
            j["payload"] = dict(j["payload"])
            j["payload"]["message"] = DAILY_MEMORY_MESSAGE
            new_jobs.append(j)
        elif jid == "x-poster-morning":
            j = dict(j)
            j["payload"] = dict(j["payload"])
            j["payload"]["message"] = X_POSTER_MORNING_MSG
            new_jobs.append(j)
        elif jid == "x-poster-evening":
            j = dict(j)
            j["payload"] = dict(j["payload"])
            j["payload"]["message"] = X_POSTER_EVENING_MSG
            new_jobs.append(j)
        elif jid == "tiktok-poster-morning":
            j = dict(j)
            j["payload"] = dict(j["payload"])
            j["payload"]["message"] = TIKTOK_MORNING_MSG
            new_jobs.append(j)
        elif jid == "tiktok-poster-evening":
            j = dict(j)
            j["payload"] = dict(j["payload"])
            j["payload"]["message"] = TIKTOK_EVENING_MSG
            new_jobs.append(j)
        else:
            new_jobs.append(j)

    data["jobs"] = new_jobs + [ANICCA_AUTO_DEV_TODAY]
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
