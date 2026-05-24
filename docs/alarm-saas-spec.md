# Anicca Alarm — 起こし/遅刻防止 SaaS 実装スペック (SSOT)

最終更新: 2026-05-24
状態の凡例: ✅本物に動作確認済 / 🔶配線済・実データ未検証 / ❌未実装 / 🔧要修正

## 0. 全体像

```
ローカル(君専用 ~/.openclaw, anicca-oss)        Web(課金者 anicca-products-oss → aniccaai.com)
  個人cron発火 / profile.json                      /alarm 訪問→決済→subscriber_profiles(Supabase)
        └──────────── 共通エンジン ────────────┘
        Twilio(+1) → bridge(tail7a0ba4) → Gemini Live → 電話
        gcal(gog) + 位置(OwnTracks) → ETA → 遅刻電話 + 報連相
```

## 1. 進行順 (Dais 決定 2026-05-24)

```
① ローカルを完全に動かす (実位置×実予定で遅刻防止+報連相)
        ↓
② デモ撮影: 実通話のmp3取得 + Dais が画面録画mp4 → Claude編集 → X投稿
        ↓
③ Webアプリを e2e で本物に (ツイートの5約束を全部 実データで)
```

## 2. PHASE 1 — ローカル

### L1: realtime位置同期  状態: ✅ ほぼ完了
- ファイル: `~/.openclaw/workspace/loco/server.js` (変更不要)
- 事実: `/healthz` hasFix:true、`/loc/latest`(Basic auth `OWNTRACKS_USER/PASS`) が現在地を2分鮮度で返す
- 残: 鮮度が落ちないか watch、OwnTracks が Move モードか確認のみ
- 検証: `curl -u U:P http://100.99.82.95:8788/loc/latest` が常に ≤2分

### L2: 遅刻防止+報連相 実データ通し  状態: 🔶 配線済・実走未検証
- ファイル(既存・変更ほぼ無):
  - `lateness_check.py` decide(現在地, 予定) — 多テナント対応 home= 引数あり
  - `gcal_departures.py` current_origin() が loco実位置を読む(≤45分)、directions_travel_min() がGoogle経路
  - `renraku.py` send_renraku()→ profile.stakeholder_for → gog gmail/slack
- やること: Googleカレンダーに30分後のテスト予定 → lateness_check.py 実行 → 実位置からETA→判定→電話/報連相が正しい相手に
- 検証: 手動DB投入禁止。実位置×実予定で「出発○分前→電話」

### L3 (#8): 起こし信頼性 3日A/B  状態: 🔶
- ファイル: `wake_loop.py` (再コールloop)。朝の取りこぼし対策含む

## 3. PHASE 2 — Web (ツイート5約束を実データで)

| ツイート約束 | 対応 | ファイル | 状態 |
|---|---|---|---|
| 名前・電話だけで開始 | #44 | `app/alarm/page.tsx`(番号0自動変換) `alarm-demo.js` | 🔧 |
| 遅れたら関係者へ連絡 | #34 | `saas_lateness.py` send_renraku(SMS) | 🔶合成のみ |
| カレンダー連携で電話 | #34 | `alarm-profile.js`(ics_url保存) `saas_lateness.py` | 🔶実機未 |
| 位置連携で催促 | #34 | `loco-ingest.js`→`subscriber_profiles.location_*` | 🔶realtime未 |
| 自己改善 | #35 | 新規 `wake_log.py`+`wake_tuner.py` | ❌未実装(=嘘) |

### #34 Web位置/カレンダー/報連相 実機e2e
- 手順: テスト加入者→token取得→loco-ingestに実OwnTracks位置POST→DB更新確認→本物GcalのiCal URLをics_url保存→saas_lateness実行→自分の番号で実コール+SMS
- 検証: 手でDB投入しない。実OwnTracks→実DB→実コール

### #35 自己改善 B6 (新規作成)
- 既存ネタ: `wake_loop.py` が通話後 {awake, attempts, log} 出力
- 新規: `wake_log.py`(結果を wake_outcomes.jsonl 追記) / `wake_tuner.py`(履歴→翌日調整: 開始繰上げ/persona強化/間隔)
- 修正: `wake_loop.py` 終了時に wake_log 書込、run.sh の後に tuner

### #44 LP 番号0自動変換+体験リトライ
- `app/alarm/page.tsx`: normalizeJP() — "08046270314"→先頭0除去+"+81"→"+818046270314"。demo/checkout両方
- `alarm-demo.js`: normPhone をJP 0除去対応 + 体験リトライ(再送許可)
- placeholder "090 1234 5678" + 「0から入力OK・自動変換」

### #49 CIデプロイ関数落ち
- `.github/workflows/deploy-landing.yml` + `netlify.toml`
- 判明: CIログ上は18関数デプロイ成功。404は一瞬の可能性
- やること: CI再有効化→push→直後に全関数200維持を監視。落ちるなら root実行に修正

### #46 旧repo依存を断つ
- `~/anicca-project`(→archive済 anicca-products) に push する cron特定→ anicca-products-oss へ向け直し。履歴秘密の旧repoはoss化禁止

### #48 +81番号 (任意)
- Twilio Regulatory Bundle で JP番号購入→ TWILIO_PHONE_NUMBER 差替

## 4. PHASE 3 — デモ撮影＆マーケ (Dais順では②に前倒し)

### C1 (#36) 通話mp3録音  状態: ✅仕組み構築済
- `wake_loop.py`(WAKE_RECORD=1でRecord) + `fetch_recording.py`(--latest で mp3)
- 出力: `~/anicca-wake-recordings/*.mp3`

### C2 (#37) プロモ動画
- 新規 `make_promo.sh`: ffmpeg で [画面録画mp4 + 会話mp3 + 字幕] 合成
- 字幕: Twilio文字起こし or whisper
- Dais が画面録画mp4を1回提供 → Claude が合成・投稿

### C4 (#39) ローンチX投稿 / C3 (#38) 毎日自動投稿

## 5. 検証規律 (HARD RULE #8/#14)
合成データ・スタブ・署名webhook・手動DB投入を「done」と呼ばない。実データで端から端まで通り、Claude自身が確認したものだけ done。
