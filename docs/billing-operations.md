# 課金運用フロー
最終更新日: 2025-02-21

## 1. 目的
音声アシスタントサービス「Anicca」Proプランの課金・返金・解約を適切に運用し、StripeとSupabaseのデータ整合を維持する。

## 2. 責任者
- 運用責任者: 成田 大祐（keiodaisuke@gmail.com）
- バックアップ担当: 不在時は上記メールへの転送でフォロー

## 3. 返金手順
1. Stripeダッシュボード → Payments で対象決済を特定し、Refundボタンから全額または部分返金を実行。
2. 返金理由と対応内容を本ドキュメント末尾「運用ログ」に追記。
3. Supabase `user_subscriptions` の該当ユーザーが最新の `status` / `plan` に更新されているか確認。未反映ならRailway API `/api/billing/sync` を手動実行。
4. 顧客へメールで返金完了と利用継続可否を案内。

## 4. 解約確認
1. Customer Portal でユーザーがキャンセルすると `customer.subscription.updated` webhook が発火。
2. Railwayログでイベントを確認し、Supabase `status=canceled` / `plan=grace` へ更新されたことをチェック。
3. デスクトップアプリで無料モードへ戻るかE2E確認。

## 5. サポート対応
- 窓口メール: keiodaisuke@gmail.com（24時間受付、原則2営業日以内に返信）。
- 個別課金サポートは GitHub Private Project または非公開Issueで管理し、公開リポジトリには個人情報を残さない。

## 6. 月次監査
- 毎月末、Stripe Dashboard → Reports → Subscriptions をエクスポートし、Supabase `user_subscriptions` と照合。
- `invoice.payment_failed` 等の失敗イベントが未処理でないか合わせて確認。

## 7. 監視
- Railway Logs → stripe-webhook サービスでエラーを監視し、障害発生時は即時調査。
- macOS の `~/Library/Logs/anicca-agi/main.log` を参照し、Desktopアプリのアップグレード反映状況を確認。

## 8. 運用ログ
- 返金・解約・サポート対応など重要イベントはここに追記する。
  - 例: `2025-02-21 返金完了（ユーザーID xxx） 担当: 成田`

## 9. 変更履歴
- 2025-02-21: 初版作成。
