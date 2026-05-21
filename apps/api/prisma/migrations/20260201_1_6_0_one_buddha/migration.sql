-- 1.6.0 Phase 3: Hook Storage → TS Loop — hook_candidates extensions
ALTER TABLE "hook_candidates" ADD COLUMN "source" VARCHAR(20) NOT NULL DEFAULT 'manual';
ALTER TABLE "hook_candidates" ADD COLUMN "generated_for_user_id" UUID;
ALTER TABLE "hook_candidates" ADD COLUMN "promoted" BOOLEAN NOT NULL DEFAULT false;

-- 1.6.0 Phase 5: X engagement metrics on hook_candidates
ALTER TABLE "hook_candidates" ADD COLUMN "x_engagement_rate" DECIMAL(5,4) NOT NULL DEFAULT 0;
ALTER TABLE "hook_candidates" ADD COLUMN "x_sample_size" INTEGER NOT NULL DEFAULT 0;
ALTER TABLE "hook_candidates" ADD COLUMN "x_high_performer" BOOLEAN NOT NULL DEFAULT false;

-- Index for source filtering
CREATE INDEX "hook_candidates_source_idx" ON "hook_candidates"("source");

-- 1.6.0 Phase 4: X/Twitter posts
CREATE TABLE "x_posts" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "hook_candidate_id" UUID,
    "x_post_id" VARCHAR(100),
    "text" TEXT NOT NULL,
    "posted_at" TIMESTAMPTZ,
    "metrics_fetched_at" TIMESTAMPTZ,
    "impression_count" BIGINT NOT NULL DEFAULT 0,
    "like_count" BIGINT NOT NULL DEFAULT 0,
    "retweet_count" BIGINT NOT NULL DEFAULT 0,
    "reply_count" BIGINT NOT NULL DEFAULT 0,
    "engagement_rate" DECIMAL(7,6) NOT NULL DEFAULT 0,
    "agent_reasoning" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "x_posts_pkey" PRIMARY KEY ("id")
);

-- x_posts indexes and constraints
CREATE UNIQUE INDEX "x_posts_x_post_id_key" ON "x_posts"("x_post_id");
CREATE INDEX "x_posts_hook_candidate_id_idx" ON "x_posts"("hook_candidate_id");
CREATE INDEX "x_posts_posted_at_idx" ON "x_posts"("posted_at" DESC);

ALTER TABLE "x_posts" ADD CONSTRAINT "x_posts_hook_candidate_id_fkey"
    FOREIGN KEY ("hook_candidate_id") REFERENCES "hook_candidates"("id")
    ON DELETE SET NULL ON UPDATE CASCADE;

-- 1.6.0 Phase 7: Notification Schedules (Commander Decision storage)
CREATE TABLE "notification_schedules" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "user_id" UUID NOT NULL,
    "schedule" JSONB NOT NULL,
    "agent_raw_output" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "notification_schedules_pkey" PRIMARY KEY ("id")
);

-- One schedule per user (upsert pattern)
CREATE UNIQUE INDEX "notification_schedules_user_id_key" ON "notification_schedules"("user_id");
