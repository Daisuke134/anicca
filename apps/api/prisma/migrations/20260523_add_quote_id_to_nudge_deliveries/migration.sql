-- 2026-05-23: Affirmation notifications.
--
-- The remote APNs sender now delivers daily affirmations instead of problem nudges.
-- The payload carries quoteId so the app can deep-link to the matching Feed card.
-- We persist quote_id on the delivery snapshot so retried sends keep the deep-link.

ALTER TABLE "nudge_deliveries" ADD COLUMN IF NOT EXISTS "quote_id" TEXT;
