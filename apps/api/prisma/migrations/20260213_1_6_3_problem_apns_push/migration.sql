-- 1.6.3: APNs Problem Nudge Delivery

-- user_settings extensions (day0 SSOT)
ALTER TABLE "user_settings"
  ADD COLUMN IF NOT EXISTS "nudge_day0_local_date" DATE,
  ADD COLUMN IF NOT EXISTS "nudge_day0_source" TEXT;

-- push_tokens: device token registry (env-specific)
CREATE TABLE IF NOT EXISTS "push_tokens" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "profile_id" UUID NOT NULL,
  "device_id" TEXT NOT NULL,
  "token" TEXT NOT NULL,
  "platform" TEXT NOT NULL DEFAULT 'ios',
  "env" TEXT NOT NULL,
  "disabled_at" TIMESTAMPTZ,
  "last_error" TEXT,
  "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "push_tokens_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "push_tokens_device_id_env_key" ON "push_tokens"("device_id", "env");
CREATE UNIQUE INDEX IF NOT EXISTS "push_tokens_token_env_key" ON "push_tokens"("token", "env");
CREATE INDEX IF NOT EXISTS "push_tokens_profile_id_idx" ON "push_tokens"("profile_id");

-- nudge_deliveries: idempotent send log + immutable snapshot for card
CREATE TABLE IF NOT EXISTS "nudge_deliveries" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "profile_id" UUID NOT NULL,
  "problem_type" TEXT NOT NULL,
  "scheduled_time" TEXT NOT NULL,
  "delivery_day_local" DATE NOT NULL,
  "timezone" TEXT NOT NULL,
  "lang" TEXT NOT NULL,
  "variant_index" INTEGER NOT NULL,
  "message_title" TEXT NOT NULL,
  "message_body" TEXT NOT NULL,
  "message_detail" TEXT NOT NULL,
  "status" TEXT NOT NULL DEFAULT 'queued',
  "apns_id" TEXT,
  "error" TEXT,
  "attempt_count" INTEGER NOT NULL DEFAULT 0,
  "last_attempt_at" TIMESTAMPTZ,
  "next_attempt_at" TIMESTAMPTZ,
  "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "sent_at" TIMESTAMPTZ,
  CONSTRAINT "nudge_deliveries_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "nudge_deliveries_idempotency_key"
  ON "nudge_deliveries"("profile_id", "problem_type", "scheduled_time", "delivery_day_local");

CREATE INDEX IF NOT EXISTS "nudge_deliveries_profile_created_idx"
  ON "nudge_deliveries"("profile_id", "created_at" DESC);
