---
name: calendar-with-travel-time
description: Google Calendar に予定を登録する時、必ず家(<your-address>)からの移動時間を逆算して event start を「出発時刻」にする skill。known-distance JSON + OSM Nominatim 経由で東京圏の予定を移動時間込みで登録。
metadata:
  tags: calendar, google, travel-time, scheduling, anicca
  requires:
    bins: [gog, jq, python3, curl]
    env: []
---

# calendar-with-travel-time

**Dais の HARD RULE #7 (2026-05-14):** Calendar に予定を入れる時は **必ず家(<your-address>)からの移動時間を逆算**して event start を「出発時刻」にする。「予約時刻」だけ登録は禁止。

## When to use

- Anicca / Claude Code が `gog calendar events insert` する全シナリオ
- Dais の予約 (歯医者 / フライト / ミーティング / 公演) を Calendar に入れる時
- 例外なし

## How to invoke

```bash
bash ~/.openclaw/skills/calendar-with-travel-time/scripts/create.sh \
  --title "歯医者" \
  --destination "信濃町駅" \
  --arrive-by "2026-06-23T06:00" \
  --duration 60 \
  --calendar primary \
  --location "<your-address>"
```

引数:

| arg | desc |
|-----|------|
| `--title` | event title (必須) |
| `--destination` | 行き先 (駅名 or 住所、必須) |
| `--arrive-by` | 到着必須時刻 ISO8601 JST (必須) |
| `--duration` | 予定時間 minutes (必須) |
| `--from` | 出発地 (省略時 "<your-address>") |
| `--calendar` | Google Calendar (省略時 primary) |

## What it does

1. **`data/known-distances.json`** から `from` → `destination` の移動時間を lookup
2. 見つかれば: travel_min を取得
3. 見つからなければ: OSM Nominatim で geocode + 直線距離 / 想定速度 (徒歩 4.5 km/h + 電車 30 km/h で粗推定) → 不確実な場合は Dais に Slack 確認
4. `event_start = arrive_by - travel_min - 5min(buffer)`
5. `event_end = arrive_by + duration + 30min(buffer for 帰り)`
6. description に内訳を埋め込む:
   ```
   ⏰ 移動込みスケジュール:
     {start_time} 出発 (from {from})
     {arrive_at} 到着 ({destination})
     {start_meeting} 開始
     {end_meeting} 終了予定
   📍 距離計算: known-distance JSON (or Nominatim)
   ```
7. reminder = 1h 前 + 30min 前
8. `gog calendar events insert` で Calendar 登録

## Output

```
✅ event created: <event_id>
   start: <ISO>
   end:   <ISO>
   travel: <N> min
   calendar: <id>
```

## ❌ 違反例 (絶対やらない)

```
title: 四ツ谷 廃車
start: 06:00 (= 予約時刻、移動考慮なし)
reminder: 10 min before
```

10 min 前にリマインドされても、家から出てる時点で遅刻確定。

## ✅ 正しい例

```
title: 四ツ谷 廃車手続き
start: 05:25 (家を出る時刻)
end:   07:30 (帰り移動込み)
reminder: 60 min before + 30 min before
description:
  05:25 家出発 (<your-address>)
  05:50 四ツ谷着 (徒歩+JR 25 min)
  06:00 廃車手続き開始
  07:00 終了
```

## 関連

- Claude memory: `feedback_google_calendar_travel_time_mandatory.md` (HARD RULE #7)
- Anicca agent memory: `~/anicca-project/.serena/memories/google_calendar_travel_time_rule.md`
- `data/known-distances.json` 東京圏の駅・空港・予約場所別の移動時間
