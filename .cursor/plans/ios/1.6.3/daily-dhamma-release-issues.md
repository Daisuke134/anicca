# Daily Dhamma リリース課題メモ（2026-02-20）

## Build #11 は正しいか
YES。2026-02-19 23:21 JST にアップロードしたビルド。これが正しい。

---

## 問題1: 日本語が表示されない

### 原因
`getLocalizedVerse()` を実装してデータ (`textJa`) も追加したが、**UIとnotificationsに一切ワイヤリングしていない**。

| ファイル | 現状 | 修正 |
|---------|------|------|
| `app/index.tsx` line 84 | `item.text` 直接参照 | `getLocalizedVerse(item, locale)` に変更 |
| `utils/notifications.ts` line 55 | `verse.text` 直接参照 | `getLocalizedVerse(verse, locale)` に変更 |
| `app/settings.tsx` line 247 | `verse.text` 直接参照 | `getLocalizedVerse(verse, locale)` に変更 |

### 修正に必要なこと
1. `expo-localization` で端末ロケール取得 (`Localization.locale`)
2. 全 `verse.text` 参照を `getLocalizedVerse(verse, locale)` に置換
3. 通知の日本語: `stayPresentMessagesJa` も同様にロケールで切り替え

---

## 問題2: 価格が $2.99/$90.99 と表示される

### 原因
`asc subscriptions availability set` で **USA のみ** に設定した。
日本のApple IDユーザーは製品が利用不可 → RC SDK が App Store からプロダクトを取得できない
→ RC がフォールバックとして Test Store プロダクト (`daily_dharma_monthly`/$2.99, `daily_dharma_yearly`/$90.99) を表示している。

### 修正に必要なこと
1. ASC で availability を全テリトリーに設定（または少なくとも JPN を追加）
2. JPN の価格を設定（`asc subscriptions prices add --territory JPN`）
   - Monthly: ¥600〜¥700 相当
   - Annual: ¥2,000〜¥2,500 相当
3. または Apple の自動 price equalization を使う（USA 設定から他国を自動換算）

---

## 問題3: Stay Present 通知のタイムスロット

### 現在の実装
- 起動時間: 8:00〜21:00（13時間）
- `interval = 13 / frequency` で均等分割
- 各時刻に最大30分のランダムオフセット追加

### 実際のタイムスロット
| プラン | 回数 | 間隔 | 時刻（概算） |
|-------|------|------|------------|
| Free | 3回 | 4.3h | 10:10, 14:30, 18:50 |
| Premium | 5回 | 2.6h | 9:18, 11:54, 14:30, 17:06, 19:42 |
| Premium | 7回 | 1.9h | 8:56, 10:47, 12:38, 14:30, 16:22, 18:13, 20:04 |
| Premium | 10回 | 1.3h | 8:38, 9:58, 11:18...毎78分 ⚠️ |

### 問題点
- 10回/日は**78分間隔**で多すぎる可能性
- 10回×7日 = 70 + 朝7 = **77通知 > iOS上限64** でオーバーフロー
- 朝7時のverseと10:10のstay presentが重なる感じは自然（3時間空く）

### 修正方針
- 10回/日は `daysToSchedule = 5` に下げる (10×5+5 = 55 < 64)
- または最大7回/日のキャップを設ける

---

## 問題4: 「永遠に」通知を届けられるか

### 現在の実装
- **ローカル通知**（サーバーなし）
- 7日分を事前スケジュール
- アプリ起動ごとに再スケジュール（AppProviderのuseEffect）

### リスク
- ユーザーが7日間アプリを開かないと通知が止まる
- 本当の「永遠配信」には APNs サーバーサイドが必要

### 判断
現時点のMVPとしてはローカル通知で十分。ただし:
- 再スケジュールはアプリ起動のたびに走っている（AppProvider確認済み）
- 朝の verse は 7 日後に止まるが、ユーザーが翌日アプリを開けばリセット
- 本格的な「永遠配信」は将来の Backend APNs プッシュで対応

---

## 次にやること（優先順）

| # | タスク | 影響 | 工数 |
|---|--------|------|------|
| 1 | 価格（JPN territoryの追加） | リジェクトリスク・購入不可 | 30分 |
| 2 | 日本語ワイヤリング | UX・Apple 4.5.4ガイドライン | 1〜2h |
| 3 | 通知上限バグ（10回/日） | クラッシュリスクではなく単に止まる | 15分 |
