-- 1.6.3: Per-device send log for APNs Problem Nudge Delivery
--
-- Why: A single profile can have multiple devices (multiple push_tokens).
-- nudge_deliveries is the immutable content snapshot per (profile, problem_type, slot, day),
-- but sending must be tracked per push_token to guarantee delivery on every device.

CREATE TABLE IF NOT EXISTS "nudge_delivery_sends" (
  "id" UUID NOT NULL DEFAULT gen_random_uuid(),
  "delivery_id" UUID NOT NULL,
  "push_token_id" UUID NOT NULL,
  "status" TEXT NOT NULL DEFAULT 'queued', -- queued|sending|sent|failed|blocked
  "apns_id" TEXT,
  "error" TEXT,
  "attempt_count" INT NOT NULL DEFAULT 0,
  "last_attempt_at" TIMESTAMPTZ,
  "next_attempt_at" TIMESTAMPTZ,
  "sent_at" TIMESTAMPTZ,
  "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "nudge_delivery_sends_pkey" PRIMARY KEY ("id")
);

-- One delivery should be sent at most once per device token.
CREATE UNIQUE INDEX IF NOT EXISTS "nudge_delivery_sends_delivery_id_push_token_id_key"
  ON "nudge_delivery_sends" ("delivery_id", "push_token_id");

CREATE INDEX IF NOT EXISTS "nudge_delivery_sends_push_token_id_status_next_attempt_at_idx"
  ON "nudge_delivery_sends" ("push_token_id", "status", "next_attempt_at");

ALTER TABLE "nudge_delivery_sends"
  ADD CONSTRAINT "nudge_delivery_sends_delivery_id_fkey"
  FOREIGN KEY ("delivery_id") REFERENCES "nudge_deliveries"("id")
  ON DELETE CASCADE;

ALTER TABLE "nudge_delivery_sends"
  ADD CONSTRAINT "nudge_delivery_sends_push_token_id_fkey"
  FOREIGN KEY ("push_token_id") REFERENCES "push_tokens"("id")
  ON DELETE CASCADE;

