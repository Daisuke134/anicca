# Newsletter（毎朝の手紙）+ Feedback（改善してほしいこと）404 修正 — 設計書

- **日付**: 2026-06-15
- **対象**: iOS `aniccaios` + backend `apps/api`
- **ブランチ**: `dev`（worktree で作業）→ `main`（production deploy）
- **ステータス**: 設計（brainstorming stage）

---

## 1. 問題（ユーザー報告）

iOS アプリ内 Settings から:
1. **「毎朝の手紙」のメール購読登録** — 自分のメールアドレスを入れて登録 → **「失敗しました。もう一回試してください」**
2. **「改善してほしいこと」の送信** — 送信 → **同じ失敗メッセージ**

ユーザーの直感：「これはバックエンドの問題だと感じている」→ **正しい**（実証済み）。

---

## 2. 根本原因（RCA・証拠付き）

### 2.1 一行サマリ
iOS 1.9.1 の UI（newsletter / feedback フォーム）は **App Store に出ている**が、その UI が叩く backend ルートが **production / staging のどちらにもデプロイされていない** → サーバが **HTTP 404** を返す → iOS が非2xxを検知して `"Failed. Please try again."` を表示。

### 2.2 何が起きたか（git 証拠）
- 該当機能の実装は単一コミット `27e0c0e0`「feat(1.9.1): spec ⑥/⑦ newsletter + feedback (UI inline + backend)」に存在。
- このコミットは **`release/1.9.1` ブランチにのみ存在**。
  - `git merge-base --is-ancestor 27e0c0e0 HEAD` → **NO**（dev に無い）
  - `git merge-base --is-ancestor 27e0c0e0 origin/main` → **NO**（main に無い）
  - `git branch --contains 27e0c0e0` → `release/1.9.1` のみ
- iOS（`SettingsSheet.swift` +236行）は `release/1.9.1` でビルド → App Store に出荷済 → ユーザーはフォームを操作できる。
- backend（routes / migration / schema / scheduler / 依存）は `release/1.9.1` に commit されたが **main にマージされず** → Railway（main 自動デプロイ）に未反映。

### 2.3 本番への実証 curl（決定的証拠）
本番 base: `https://anicca-proxy-production.up.railway.app/api`

| リクエスト | 結果 | 意味 |
|---|---|---|
| `GET /api/mobile/entitlement`（既存ルート） | **400** | ルート存在（ボディ不正で400） |
| `GET /api/mobile/nudge/pending`（既存ルート） | **400** | ルート存在 |
| `GET /api/mobile/newsletter/subscribers` | **404** | ルート未登録 |
| `POST /api/mobile/newsletter/subscribers` | **404** | ルート未登録 |
| `GET /api/mobile/feedback` | **404** | ルート未登録 |
| `POST /api/mobile/feedback` | **404** | ルート未登録 |
| staging `POST .../newsletter/subscribers` | **404** | staging も未デプロイ |
| staging `POST .../feedback` | **404** | staging も未デプロイ |

### 2.4 iOS 側の失敗トリガ（コード）
`aniccaios/aniccaios/Views/Feed/SettingsSheet.swift`（release/1.9.1）:
```swift
let (_, resp) = try await URLSession.shared.data(for: req)
guard let http = resp as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
    errorMsg = "Failed. Please try again."   // ← 404 でここに落ちる
    return
}
```

---

## 3. 影響範囲

| 機能 | 現状 | 直すと |
|---|---|---|
| Newsletter 登録 | 404 → 失敗表示 | 200 → 登録成功 |
| 毎日配信（08:30 JST / 23:30 UTC scheduler） | 未デプロイ → 0通 | 毎日1通 affirmation メール |
| Feedback 送信 | 404 → 失敗表示 | 200 → keiodaisuke@gmail.com に届く |

**最小修正の核心**: backend を production にデプロイすれば、既に App Store にある iOS 1.9.1 アプリがそのまま動き出す。iOS のバイナリ再提出は不要。

---

## 4. 修正方針（パッチレベル）

### 4.1 アプローチ選定
- `release/1.9.1` の schema.prisma を**丸ごと**持ち込むと `NudgeDelivery.quoteId` が消える（dev と乖離）= **危険**。
- よって **「release/1.9.1 から必要なファイル/モデルのみを dev へ個別移植」** を採用。`git checkout release/1.9.1 -- <file>` と、schema は newsletter/feedback の3モデルだけ追記。

### 4.2 backend 移植対象（`apps/api`）
| ファイル | 操作 |
|---|---|
| `src/routes/mobile/newsletter.js` | 新規（release から checkout） |
| `src/routes/mobile/feedback.js` | 新規（release から checkout） |
| `src/routes/mobile/index.js` | newsletter/feedback router を import + mount（2行 + import 2行）追加 |
| `prisma/schema.prisma` | 3モデル（`newsletter_subscribers` / `feedback_log` / `failed_resend_calls`）**のみ追記**（quotev削除は持ち込まない） |
| `prisma/migrations/20260603_add_newsletter_feedback/migration.sql` | 新規（`CREATE TABLE IF NOT EXISTS` ×3） |
| `src/server.js` | daily newsletter scheduler（setInterval、23:30 UTC window）追加。`closePool` 変更は dev の既存 db.js と整合する形で取り込む（dev の `pool.end()` を壊さない） |
| `package.json` | `"resend": "^6.12.4"` を dependencies に追加 |
| `src/generated/prisma/*` | `npx prisma generate` で再生成（手書き移植しない） |
| affirmations catalog | `newsletter.js` が `modules/affirmations/catalog/{ja,es,en}.json` を読む。dev に存在するか確認、無ければ移植 |

### 4.3 iOS 移植対象（`aniccaios`）— Maestro E2E のため dev を 1.9.1 に追従
| ファイル | 操作 |
|---|---|
| `Views/Feed/SettingsSheet.swift` | newsletter/feedback UI（+236行）を release から取り込み |
| `Resources/*.lproj/Localizable.strings` | `newsletter_*` / `feedback_*` キー（ja/en 他）を移植 |
| `AppState.resolveDeviceId()` 等の依存 | dev に存在するか確認、無ければ移植 |

**注**: App Store の修正には iOS バイナリは不要。iOS 移植は「dev を最新化して Maestro でE2E検証可能にする」目的。

### 4.4 改善点（移植ついで）
- iOS のエラー文言が英語ハードコード `"Failed. Please try again."`。`String(localized:)` 化して ja に「送信に失敗しました。もう一度お試しください。」を追加（ユーザー体験の整合）。— **scope内の小改善**。

---

## 5. インフラ / 環境変数（要確認・設定）

| 項目 | 確認/作業 |
|---|---|
| `RESEND_API_KEY` | Railway **staging + production** 両方に設定されているか確認。無ければ設定（Resend ダッシュボード or 既存キー） |
| Resend 送信ドメイン | `anicca@aniccaai.com` / `anicca-feedback@aniccaai.com` の from ドメイン `aniccaai.com` が Resend で **verified** か確認 |
| Prisma migration | `prisma migrate deploy` を staging→production の DB に適用（`IF NOT EXISTS` なので冪等） |
| `resend` npm | staging/production で `npm install` 反映（Railway ビルド） |

---

## 6. テスト戦略

### 6.1 ユニット（TDD: RED→GREEN）
- `newsletter.js`:
  - `POST /subscribers` バリデーション: INVALID_EMAIL(400) / DEVICE_ID_REQUIRED(400) / RATE_LIMITED(429) / 正常(200 `{ok:true}`)
  - upsert ロジック（既存 deviceId は update、無ければ create、optedOutAt リセット）
  - `sendDailyNewsletter()`: subscriber 0件→`{sent:0}`、送信成功で `lastSentAt` 更新、3-retry 後失敗で `failed_resend_calls` 記録（Resend と Prisma は mock）
- `feedback.js`:
  - TEXT_REQUIRED(400) / TEXT_TOO_SHORT(<5,400) / TEXT_TOO_LONG(>2000,413) / RATE_LIMITED(429) / 正常(200) / Resend失敗時 graceful 202
- scheduler 時刻window判定（23:28–23:32 UTC のみ発火、同日二重発火しない）
- 既存テストスイートが green のまま（`apps/api/src/__tests__/`）

### 6.2 E2E（Maestro + 実メール）
1. iOS（シミュレータ/実機）起動 → Settings 画面へ
2. newsletter section にメール（`keiodaisuke@gmail.com`）入力 → 送信
3. UI が登録成功状態（`newsletter-status-text` = 登録済み表示）になる
4. feedback section にテキスト入力 → 送信 → `✓ Sent`
5. **実メール検証**: `keiodaisuke@gmail.com` に
   - feedback メール（`[Anicca Feedback] ...`）が届く
   - daily newsletter を手動 fire（`sendDailyNewsletter()` 実走）→ affirmation メール（`🌅 ...`）が届く
6. Apple Sign-In で詰まる場合は自分で解決（テスト用フロー）

### 6.3 「毎日来る」の実証
- scheduler ロジックのユニットテスト（時刻window）+ `sendDailyNewsletter()` の実走で**実際に1通飛ぶ**ことを確認 = 「決められた時間に毎日1通」の実証。

---

## 7. デプロイ & 検証フロー

```
dev に移植 + TDD green
  → push（Railway staging 自動デプロイ）
  → staging で curl 200 + 実メール受信 verify
  → Maestro E2E（staging 向けビルド）green
  → main へ（PR/merge、Dais 判断）
  → production 自動デプロイ
  → production DB に migrate deploy
  → production で curl 200 + App Store アプリから実登録 + 実メール受信 verify
  → 毎日配信 fire 実証
```

---

## 8. 完了の定義（E2E 検証 = 全て）

- [ ] production `POST /api/mobile/newsletter/subscribers` → 200 `{ok:true}`
- [ ] production `POST /api/mobile/feedback` → 200 `{ok:true}`
- [ ] `keiodaisuke@gmail.com` に feedback メール実着信（件名・本文確認）
- [ ] `keiodaisuke@gmail.com` に daily newsletter メール実着信
- [ ] DB に `newsletter_subscribers` 行が作られている
- [ ] iOS（App Store版 or Maestroビルド）から登録 → 成功表示
- [ ] scheduler が毎日 08:30 JST に発火する設定であることをコード+テストで確認
- [ ] ユニットテスト全 green、既存テスト退行なし

---

## 9. リスク / 注意

| リスク | 対策 |
|---|---|
| schema 丸取りで `quoteId` 消失 | モデルのみ追記方式（4.1） |
| `RESEND_API_KEY` 未設定で送信失敗 | デプロイ前に Railway 両環境で確認・設定 |
| Resend ドメイン未verifyで送信失敗 | Resend ダッシュボードで `aniccaai.com` verify 確認 |
| migration 二重適用 | `CREATE TABLE IF NOT EXISTS` で冪等 |
| `src/generated/prisma` 手書き移植の不整合 | `prisma generate` で再生成 |
| dev の db.js と server.js の `pool`/`closePool` 不整合 | dev の実装に合わせて scheduler を取り込む |
| in-memory rate limit（複数インスタンス） | 現スケールでは許容（spec通り）。将来 Redis 化は scope外 |
```
