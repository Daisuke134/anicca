---
name: app-reviews
description: "App Store Connect から全 Anicca アプリのレビューを毎日取得し、新着に対して言語に合わせた返信を自動生成して直接 ASC API に投稿する。週次ダイジェストもサポート。"
metadata: {"openclaw":{"emoji":"⭐","os":["darwin","linux"]}}
---

# app-reviews — Auto-Reply ASO Engine

## 目的
Anicca ポートフォリオ全アプリの App Store レビューを毎日取得し、
新着に対して **言語を判定した返信を自動生成 → ASC API に直接 POST**、
完了後に Slack #metrics に証跡を残す。週次ダイジェストでスタッツを可視化する。

返信は人間の介在なし（fully autonomous）。投稿前の承認フローは存在しない。
品質ガードレールは内部的にだけ働く（暴言・法的脅迫・身バレリスク → 自動スキップして
Slack に手動対応依頼として上げる）。

## 保存先
| 種類 | フルパス |
|------|----------|
| ポートフォリオ定義 | `~/.openclaw/state/app-portfolio.json` |
| 日次レビュー | `~/.openclaw/workspace/app-reviews/<app_id>/reviews_YYYY-MM-DD.json` |
| 既知レビューID | `~/.openclaw/workspace/app-reviews/seen-review-ids.txt` |
| 返信ログ | `~/.openclaw/workspace/app-reviews/replies/<app_id>/replies_YYYY-MM-DD.json` |
| 週次ダイジェスト | `~/.openclaw/workspace/app-reviews/digests/digest_YYYY-MM-DD.json` |

## 必須 env
| キー | 用途 |
|------|------|
| `ASC_KEY_ID` | App Store Connect API Key ID |
| `ASC_ISSUER_ID` | Issuer ID |
| `ASC_PRIVATE_KEY` | JWT 署名用 P8 私鍵（`\n` エスケープ可）|
| `ASC_PRIVATE_KEY_PATH` | 上の代替（ファイルパス） |
| `SLACK_BOT_TOKEN` | Slack 通知 |
| `APP_REVIEW_DRY_RUN` | `true` で POST をスキップ（ログのみ） |
| `MODE` | 省略=daily / `weekly` で週次ダイジェスト |

## 動作モード

### MODE=daily（デフォルト）
1. ポートフォリオを読む → 各アプリでループ
2. レビュー取得 → 新着抽出
3. 返信生成 → ASC API に POST
4. Slack #metrics に投稿後ログ

### MODE=weekly（月曜 09:00 JST）
1. ポートフォリオ全体で過去7日のレビューを集計
2. アプリ別に件数・平均星・センチメント傾向・トップテーマ・トップ不満を集計
3. Slack #metrics にダイジェスト投稿

---

## 実行手順（daily mode）

### 0. 共通: JWT 生成
```bash
JWT=$(node -e "
const jwt = require('jsonwebtoken');
const fs = require('fs');
let key = process.env.ASC_PRIVATE_KEY;
if (!key && process.env.ASC_PRIVATE_KEY_PATH) {
  key = fs.readFileSync(process.env.ASC_PRIVATE_KEY_PATH, 'utf8');
}
key = key.replace(/\\\\n/g, '\n');
const token = jwt.sign({}, key, {
  algorithm: 'ES256',
  expiresIn: '20m',
  issuer: process.env.ASC_ISSUER_ID,
  audience: 'appstoreconnect-v1',
  header: { kid: process.env.ASC_KEY_ID }
});
console.log(token);
")
```

### 1. ポートフォリオを読み、各アプリをループ
```bash
PORTFOLIO=~/.openclaw/state/app-portfolio.json
APP_IDS=$(jq -r '.apps[] | select(.auto_reply==true) | .app_id' "$PORTFOLIO")

for APP_ID in $APP_IDS; do
  # ... 以下、アプリごと
done
```

各アプリにつき bundle_id / default_language / max_replies_per_run / talking_points を
ポートフォリオから取得して使う。

### 2. レビュー取得（過去30日 / 最大200件）
```bash
mkdir -p ~/.openclaw/workspace/app-reviews/$APP_ID
mkdir -p ~/.openclaw/workspace/app-reviews/replies/$APP_ID

DATE=$(date +%Y-%m-%d)
RAW=~/.openclaw/workspace/app-reviews/$APP_ID/reviews_${DATE}.json

# 全件 (`include=response` で既存返信もチェック → 二重投稿防止)
curl -sS "https://api.appstoreconnect.apple.com/v1/apps/$APP_ID/customerReviews?sort=-createdDate&limit=200&include=response" \
  -H "Authorization: Bearer ${JWT}" > "$RAW"
```

レスポンス構造:
- `data[]`: customerReviews（id, attributes.{rating,title,body,reviewerNickname,createdDate,territory}, relationships.response.data?）
- `included[]`: customerReviewResponses（既に返信済みのレビュー）

### 3. 新着抽出 & 既存返信チェック
```bash
SEEN=~/.openclaw/workspace/app-reviews/seen-review-ids.txt
touch "$SEEN"

# include=response が付いているレビューID 一覧
ALREADY_RESPONDED=$(jq -r '.data[] | select(.relationships.response.data != null) | .id' "$RAW")

# 新着 = 未シーン AND 未返信
NEW_IDS=$(jq -r '.data[].id' "$RAW" | while read id; do
  if ! grep -qx "$id" "$SEEN" && ! echo "$ALREADY_RESPONDED" | grep -qx "$id"; then
    echo "$id"
  fi
done)
```

### 4. 返信生成（per review）

各 NEW_ID について:

#### 4.1 言語判定
- 本文に CJK 漢字/かな/カナが多い → `ja`
- 本文に Hangul → `ko`
- それ以外（ラテン文字主体）→ `en`
- 自信が持てない場合 → `default_language`（ポートフォリオから）

#### 4.2 品質ガードレール（自動スキップ条件）
以下のいずれかにマッチしたら **返信せず** Slack に "🚨 manual response needed" として上げる:

- 暴言/差別語（多言語の代表的なリスト）
- 詐欺の告発（"scam", "詐欺", "fraud", "ripoff"）
- 法的脅迫（"sue", "lawsuit", "弁護士", "訴える"）
- 個人情報漏洩・身バレ系（電話番号・メールアドレス本文に含む）
- 返金トラブル系で具体的な金額・取引IDを含む（"refund", "返金", "RevenueCat" + 金額表記）

#### 4.3 返信文生成方針

**トーン**: warm, 具体的, おもねりすぎない、こちらの意図と反省を率直に。
**長さ**: 通常 80–300 文字。暴言以外でも 5,900 字超になりそうなら ellipsis (…) で truncate。
**構造**:

| 星 | 構造 |
|----|------|
| 5★ | (1) 具体的に何が良かったかを引用 → (2) 同じ価値を生み出している理由 → (3) 今後の改善方向や続報の予告 |
| 4★ | (1) ポジティブ点を承認 → (2) 残り 1★ を埋めるためにこちらが進めている改善 |
| 3★ | (1) 評価への謝意 → (2) 不満点を具体的に再現確認 → (3) 改善計画 or 次バージョンで対応する旨 |
| 1–2★ | (1) 不便を起こしたことの率直な謝罪 → (2) 再現条件のヒアリング窓口（support@anicca.ai）→ (3) 既知の場合は修正予定バージョン |

**talking_points** はポートフォリオから引いてきて、ポジティブ評価のときに自然に織り込む
（例: 5★ で "AI音声" に触れている人には「伴走者として声かけする設計」を再強調）。

**JP 例（5★）**:
> 「ttdd*su さん、レビューありがとうございます！『管理されているのではなく応援されている』
>  と感じていただけたことが、AI音声コーチを設計している私たちにとって何より嬉しいです。
>  今後も声のトーンとタイミングを磨き続けます。引き続きよろしくお願いいたします。」

**EN 例（3★）**:
> "Thanks for the honest 3-star feedback! You're right that the morning notification timing
>  could be more flexible — we're shipping per-habit time windows in v1.7. Drop us a note at
>  support@anicca.ai if you'd like early access."

#### 4.4 ASC POST

```bash
BODY=$(jq -n --arg id "$REVIEW_ID" --arg text "$REPLY_TEXT" '{
  data: {
    type: "customerReviewResponses",
    attributes: { responseBody: $text },
    relationships: { review: { data: { type: "customerReviews", id: $id } } }
  }
}')

if [ "$APP_REVIEW_DRY_RUN" = "true" ]; then
  echo "[DRY_RUN] would POST reply for $REVIEW_ID:"
  echo "$REPLY_TEXT"
  STATUS="dry_run"
  HTTP_CODE="000"
else
  RESP=$(curl -sS -w "\n%{http_code}" -X POST \
    "https://api.appstoreconnect.apple.com/v1/customerReviewResponses" \
    -H "Authorization: Bearer ${JWT}" \
    -H "Content-Type: application/json" \
    -d "$BODY")
  HTTP_CODE=$(echo "$RESP" | tail -n1)
  RESP_BODY=$(echo "$RESP" | sed '$d')
  if [ "$HTTP_CODE" = "201" ]; then
    STATUS="ok"
    echo "$REVIEW_ID" >> "$SEEN"
  else
    STATUS="failed"
  fi
fi
```

ASC エンドポイント: `POST https://api.appstoreconnect.apple.com/v1/customerReviewResponses`
スキーマ参照: https://developer.apple.com/documentation/appstoreconnectapi/customer_reviews_and_responses

成功は HTTP 201。失敗時は `RESP_BODY.errors[].detail` をログに残す。

#### 4.5 レート制御
アプリごとに `max_replies_per_run`（デフォルト 20）を超えたら break。
2ヶ月のバックログ消化中の暴走を防ぐ。日次が継続すれば実質無効。

### 5. 返信ログ書き出し

```jsonc
// ~/.openclaw/workspace/app-reviews/replies/<app_id>/replies_YYYY-MM-DD.json
{
  "app_id": "6755129214",
  "date": "2026-05-07",
  "executedAt": "2026-05-07T08:00:00+09:00",
  "dry_run": true,
  "totals": { "candidates": 5, "replied": 4, "skipped_existing": 0, "skipped_guardrail": 1, "failed": 0 },
  "items": [
    {
      "review_id": "00000192-...",
      "rating": 5,
      "language": "ja",
      "review_excerpt": "AI音声を活用した養成プランは...",
      "reply_text": "ttdd*su さん、レビューありがとうございます！...",
      "status": "ok|dry_run|failed|skipped_guardrail|skipped_existing",
      "http_code": "201",
      "error": null
    }
  ]
}
```

### 6. Slack 投稿（送信完了後）

**投稿先**: `#metrics` (`{{profile.channels.reportChannel}}`)
**フォーマット**:

```
⭐ app-reviews — Anicca (HH:mm JST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 候補 5件 | 返信 4件 | スキップ 1件 (manual) | 失敗 0件
（DRY_RUN モード — POST はしていません）

━━━ 返信内訳 ━━━

★★★★★ 「革新的」 — ttdd*su (JPN, 2026-05-06)
  └ 評価: AI音声を活用した養成プランは…
  └ 返信: ttdd*su さん、レビューありがとうございます！…
  └ ✅ replied (HTTP 201)

★★★☆☆ "Could be better" — johnD (USA, 2026-05-05)
  └ Review: The morning notification timing…
  └ Reply: Thanks for the honest 3-star feedback!…
  └ ✅ replied (HTTP 201)

🚨 manual response needed:
★☆☆☆☆ "Refund please" — anon (JPN) — 詐欺・金額表記検知
  https://appstoreconnect.apple.com/apps/6755129214/distribution/ratings
```

DRY_RUN モードのときは見出しに `(DRY_RUN モード — POST はしていません)` を必ず明記する。

### 7. seen-review-ids.txt への追記
本番モードで POST が 201 / または ASC 側に既存応答ありを確認した review id を追記。
DRY_RUN では追記しない（次回も再生成 → サンプル確認可能）。

---

## 実行手順（weekly mode）

`MODE=weekly` のとき:

1. 過去7日分の `~/.openclaw/workspace/app-reviews/<app_id>/reviews_*.json` を集計
2. アプリごと:
   - 件数・平均星・★ 別件数
   - センチメント trend（前週比）
   - トップ 5 テーマ（review.title + body から既存の keyThemes 分類器で抽出）
   - トップ 3 不満（1-3★ レビューの body から）
3. ダイジェスト JSON を `~/.openclaw/workspace/app-reviews/digests/digest_YYYY-MM-DD.json` に保存
4. Slack 投稿:

```
📊 app-reviews 週次ダイジェスト (Mon HH:mm JST)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▼ Anicca (6755129214)
  件数: 12 (前週比 +3) | 平均 ★4.6 | sentiment: positive (74%)
  ★★★★★ 8 / ★★★★ 2 / ★★★ 1 / ★★ 0 / ★ 1
  🔑 top themes: AI音声コーチ / 習慣化支援 / 通知タイミング
  ⚠️ top complaints: 朝の時間帯固定 / iPad 未対応 / 通知音バリエーション

💡 ASO ヒント: "AI音声" "習慣化" を keyword 上位に維持。
🎯 MRR 影響: 高評価レビューの伴走体験が DL→トライアル コンバージョンを後押し。
```

---

## 失敗時の挙動
- ASC API 401/403 → 即停止し、Slack に "❌ auth failed" を投稿（環境変数チェック）
- ASC API 429 (rate limit) → 60秒バックオフ → 再試行 1回 → ダメなら次のアプリへ
- Slack 投稿失敗 → ログ JSON は必ず残す（ローカル確認可能）
- 返信生成中の例外 → 該当 review だけスキップ、他は継続

## 自動拡張ポリシー（multi-app）
新アプリは `app-portfolio.json` に手動 1行追加で取り込まれる。
返信を始める前に必ず `auto_reply: true` に上げる必要がある（事故防止のため新規は false 推奨）。
オプション: 起動時に `GET /v1/apps` を叩いてポートフォリオに無いアプリ ID を検出 →
`auto_reply: false` で append、Slack に "🆕 new app detected — flip auto_reply to enable" 通知。

## DRY_RUN を本番に切り替える方法
`~/.openclaw/cron/jobs.json` の `app-reviews-daily` および `app-reviews-weekly-digest` の
`payload.env.APP_REVIEW_DRY_RUN` を `"true"` から `"false"` に変更する。
他に変更箇所なし。

## Cron
- `app-reviews-daily`: 毎日 08:00 JST
- `app-reviews-weekly-digest`: 月曜 09:00 JST
両方とも `delivery.mode: announce, channel: slack, to: channel:{{profile.channels.reportChannel}}`。
