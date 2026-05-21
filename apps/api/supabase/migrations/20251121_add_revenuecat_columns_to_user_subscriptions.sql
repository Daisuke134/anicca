-- RevenueCat連携用カラム追加（既存マイグレーションが適用されていない場合の保険）
-- 既に20251110_add_revenuecat_columns.sqlで追加されている場合は、IF NOT EXISTSによりスキップされる
ALTER TABLE public.user_subscriptions
  ADD COLUMN IF NOT EXISTS entitlement_source text DEFAULT 'stripe',
  ADD COLUMN IF NOT EXISTS revenuecat_entitlement_id text,
  ADD COLUMN IF NOT EXISTS revenuecat_original_transaction_id text,
  ADD COLUMN IF NOT EXISTS entitlement_payload jsonb;

-- インデックス追加（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_entitlement_source 
  ON public.user_subscriptions(entitlement_source);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_revenuecat_entitlement_id 
  ON public.user_subscriptions(revenuecat_entitlement_id);

