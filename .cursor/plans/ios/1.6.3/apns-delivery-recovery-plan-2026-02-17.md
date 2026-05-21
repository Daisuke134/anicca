# Anicca 1.6.3 APNs Delivery Recovery Plan

作成日: 2026-02-17
対象: iOS (aniccaios), Backend (apps/api), Production DB

## 1. 問題サマリ
- 目的は「アプリ非起動でも毎日通知が届く（server-driven APNs）」だったが、実運用で通知が止まるユーザーが発生。
- 実DB確認で以下を検出:
- `push_tokens` は存在するが、`nudge_deliveries` / `nudge_delivery_sends` が増えていないケースがある。
- 一部ユーザーで `mobile_profiles.user_id` が UUID ではなく `device_id` 文字列のまま残っている。
- APNs送信ジョブは `push_tokens.profile_id` を軸に `mobile_profiles` を引いて `struggles` を取得するため、紐付け不整合で送信対象が空になる。

## 2. 根本原因
- データ整合性ギャップ:
- `push_tokens.profile_id` は UUID。
- `mobile_profiles.user_id` が UUID でない行が残存。
- その結果、送信ジョブが `struggles` を取得できず `continue` でスキップ。

## 3. 解決方針
- 方針A: 本番データを一括修復して即時に配信再開。
- 方針B: 送信ジョブを耐障害化し、将来のデータ欠損でも配信停止しない。
- 方針C: API経路で UUID 正規化を強制し、再発を防止。
- 方針D: 監視を追加し、無配信状態を早期検知。

## 4. 実行プラン
1. Productionバックフィル（即時）
- `device_id` 基準で `mobile_profiles.user_id` を UUID (`push_tokens.profile_id`) に同期。
- 対象は不整合行のみ。

2. APNs送信ジョブ強化
- `struggles` 取得を多段化:
- 第1候補: `mobile_profiles.profile.struggles`
- 第2候補: `mobile_profiles.profile.problems`
- 第3候補: `user_traits.struggles`
- どれか取得できれば配信継続。

3. API再発防止
- `/api/mobile/push/token` で token登録時に `mobile_profiles.user_id` を `profile_id` に同期。
- `/api/mobile/profile` 保存時の `user_id` 正規化を厳格化。

4. 監視/アラート
- 条件:
- `active push_tokens > 0` かつ `nudge_deliveries` が30分以上0件。
- `nudge_delivery_sends` の失敗率が閾値超過。
- Slack通知に接続。

## 5. 検証手順
1. データ整合性チェック
- `push_tokens.profile_id` と `mobile_profiles.user_id` の乖離件数を確認。

2. 送信実績チェック
- `nudge_deliveries` が時刻スロットごとに増加すること。
- `nudge_delivery_sends.status='sent'` が発生すること。

3. 端末実機チェック
- 1.6.3でAPNs token登録後、スロット時刻に通知受信。
- タップ有無に関係なく翌日も配信継続。

## 6. バージョン別の挙動
- 1.6.2:
- APNs token登録の新経路がないため、1.6.3のserver-driven APNs運用の恩恵は基本的に受けない。
- 旧ローカル通知運用に依存するため、長時間非起動時に枯渇リスクが残る。

- 1.6.3 (TestFlight / App Store):
- アプリが一度起動して token 登録が完了すれば、Backend修復後すぐにAPNs配信対象になる。
- App Store審査完了は必須ではない。TestFlight 1.6.3でも同じ配信経路で受信可能。

## 7. 期待される状態
- 全ユーザーが「通知タップ有無に依存せず」毎日通知を受信できる。
- データ不整合が再発しても配信停止に直結しない。
- 無配信状態を運用監視で早期検知できる。
