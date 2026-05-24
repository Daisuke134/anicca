---
name: weather-report
description: "Dais の所在地（奈良/大阪）の天気を取得して workspace に保存する"
metadata: {"openclaw":{"emoji":"🌤️","os":["darwin","linux"]}}
---

# weather-report

## 目的
ボス（Dais）の所在地の天気予報を取得し、日次レポートに含める。

## 保存先
| 種類 | フルパス |
|------|----------|
| 天気 | `/Users/anicca/.openclaw/workspace/weather-report/weather_YYYY-MM-DD.json` |

## 必須 env
なし（API キー不要）

## 実行手順

### 1. 天気取得（wttr.in）
```bash
# 東京（新宿）
curl -s "wttr.in/Shinjuku,Tokyo?format=j1"
```
JSON フォーマットで取得。`format=j1` で構造化 JSON が返る。

### 2. 出力 JSON
```json
{
  "date": "YYYY-MM-DD",
  "executedAt": "ISO8601",
  "status": "success|error",
  "errorMessage": null,
  "location": "Shinjuku, Tokyo",
  "current": {
    "temp_c": 8,
    "condition": "Partly cloudy",
    "humidity": 65,
    "wind_kph": 12,
    "feels_like_c": 5
  },
  "today": {
    "max_c": 12,
    "min_c": 3,
    "condition": "Cloudy",
    "rain_chance": 20,
    "sunrise": "06:30",
    "sunset": "17:45"
  },
  "tomorrow": {
    "max_c": 14,
    "min_c": 5,
    "condition": "Sunny",
    "rain_chance": 0
  },
  "advisory": "傘不要。明日は晴れ。"
}
```

### 3. Slack 報告
**【絶対】** Slack #metrics（`{{profile.channels.reportChannel}}`）に投稿。

```
🌤️ weather-report (HH:mm JST)
━━━━━━━━━━━━━━━
📍 奈良: X°C（体感X°C）| 湿度X% | 風X km/h
📅 今日: X°C〜X°C | ☔X% | 🌅XX:XX
📅 明日: X°C〜X°C | 条件
💡 [傘が必要/不要、服装アドバイス等]
```

## 失敗時
- wttr.in エラー → Open-Meteo にフォールバック（座標: 35.69, 139.70）
- 両方失敗 → status: error

## Cron
- 1回/日: 05:15 JST
