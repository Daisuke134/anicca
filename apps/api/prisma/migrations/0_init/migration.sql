-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateTable
CREATE TABLE "tokens" (
    "user_id" TEXT NOT NULL,
    "provider" TEXT NOT NULL,
    "provider_sub" TEXT,
    "email" TEXT,
    "access_token_enc" JSONB NOT NULL,
    "refresh_token_enc" JSONB,
    "scope" TEXT,
    "expiry" TIMESTAMPTZ,
    "rotation_family_id" TEXT,
    "revoked_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "tokens_pkey" PRIMARY KEY ("user_id","provider")
);

-- CreateTable
CREATE TABLE "refresh_tokens" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "token_hash" TEXT NOT NULL,
    "device_id" TEXT NOT NULL,
    "user_agent" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "rotated_from" UUID,
    "revoked_at" TIMESTAMPTZ,
    "last_used_at" TIMESTAMPTZ,
    "reuse_detected" BOOLEAN NOT NULL DEFAULT false,

    CONSTRAINT "refresh_tokens_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "mobile_profiles" (
    "device_id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "profile" JSONB NOT NULL DEFAULT '{}',
    "language" TEXT NOT NULL DEFAULT 'en',
    "updated_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ,

    CONSTRAINT "mobile_profiles_pkey" PRIMARY KEY ("device_id")
);

-- CreateTable
CREATE TABLE "mobile_voip_tokens" (
    "user_id" TEXT NOT NULL,
    "device_token" TEXT NOT NULL,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "mobile_voip_tokens_pkey" PRIMARY KEY ("user_id","device_token")
);

-- CreateTable
CREATE TABLE "mobile_alarm_schedules" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "habit_type" TEXT NOT NULL,
    "fire_time" TIMESTAMPTZ NOT NULL,
    "timezone" TEXT NOT NULL,
    "repeat_rule" TEXT NOT NULL DEFAULT 'daily',
    "next_fire_at" TIMESTAMPTZ NOT NULL,
    "created_at" TIMESTAMPTZ,
    "updated_at" TIMESTAMPTZ,

    CONSTRAINT "mobile_alarm_schedules_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_subscriptions" (
    "user_id" TEXT NOT NULL,
    "plan" TEXT NOT NULL DEFAULT 'free',
    "status" TEXT NOT NULL DEFAULT 'free',
    "stripe_customer_id" TEXT,
    "stripe_subscription_id" TEXT,
    "entitlement_source" TEXT NOT NULL DEFAULT 'revenuecat',
    "revenuecat_entitlement_id" TEXT,
    "revenuecat_original_transaction_id" TEXT,
    "entitlement_payload" JSONB,
    "current_period_end" TIMESTAMPTZ,
    "trial_end" TIMESTAMPTZ,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "user_subscriptions_pkey" PRIMARY KEY ("user_id")
);

-- CreateTable
CREATE TABLE "realtime_usage_daily" (
    "user_id" TEXT NOT NULL,
    "usage_date" DATE NOT NULL,
    "count" INTEGER NOT NULL DEFAULT 0,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "realtime_usage_daily_pkey" PRIMARY KEY ("user_id","usage_date")
);

-- CreateTable
CREATE TABLE "subscription_events" (
    "event_id" TEXT NOT NULL,
    "user_id" TEXT,
    "type" TEXT NOT NULL,
    "provider" TEXT NOT NULL DEFAULT 'revenuecat',
    "payload" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "subscription_events_pkey" PRIMARY KEY ("event_id")
);

-- CreateTable
CREATE TABLE "usage_sessions" (
    "session_id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "started_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ended_at" TIMESTAMPTZ,
    "billed_seconds" INTEGER NOT NULL DEFAULT 0,
    "billed_minutes" INTEGER NOT NULL DEFAULT 0,
    "source" TEXT NOT NULL DEFAULT 'realtime',
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "usage_sessions_pkey" PRIMARY KEY ("session_id")
);

-- CreateTable
CREATE TABLE "sensor_access_state" (
    "user_id" UUID NOT NULL,
    "screen_time_enabled" BOOLEAN NOT NULL DEFAULT false,
    "sleep_enabled" BOOLEAN NOT NULL DEFAULT false,
    "steps_enabled" BOOLEAN NOT NULL DEFAULT false,
    "motion_enabled" BOOLEAN NOT NULL DEFAULT false,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "sensor_access_state_pkey" PRIMARY KEY ("user_id")
);

-- CreateTable
CREATE TABLE "monthly_vc_grants" (
    "user_id" TEXT NOT NULL,
    "grant_month" DATE NOT NULL,
    "reason" TEXT NOT NULL,
    "minutes" INTEGER NOT NULL,
    "granted_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "monthly_vc_grants_pkey" PRIMARY KEY ("user_id","grant_month","reason")
);

-- CreateTable
CREATE TABLE "profiles" (
    "id" UUID NOT NULL,
    "email" TEXT,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "profiles_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_settings" (
    "user_id" UUID NOT NULL,
    "language" TEXT NOT NULL DEFAULT 'ja',
    "timezone" TEXT NOT NULL DEFAULT 'Asia/Tokyo',
    "notifications_enabled" BOOLEAN NOT NULL DEFAULT true,
    "preferences" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "user_settings_pkey" PRIMARY KEY ("user_id")
);

-- CreateTable
CREATE TABLE "user_traits" (
    "user_id" UUID NOT NULL,
    "ideals" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "struggles" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "big5" JSONB NOT NULL DEFAULT '{}',
    "keywords" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "summary" TEXT NOT NULL DEFAULT '',
    "nudge_intensity" TEXT NOT NULL DEFAULT 'normal',
    "sticky_mode" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "user_traits_pkey" PRIMARY KEY ("user_id")
);

-- CreateTable
CREATE TABLE "daily_metrics" (
    "user_id" UUID NOT NULL,
    "date" DATE NOT NULL,
    "sleep_duration_min" INTEGER,
    "sleep_start_at" TIMESTAMPTZ,
    "wake_at" TIMESTAMPTZ,
    "sns_minutes_total" INTEGER NOT NULL DEFAULT 0,
    "sns_minutes_night" INTEGER NOT NULL DEFAULT 0,
    "steps" INTEGER NOT NULL DEFAULT 0,
    "sedentary_minutes" INTEGER NOT NULL DEFAULT 0,
    "activity_summary" JSONB NOT NULL DEFAULT '{}',
    "mind_summary" JSONB NOT NULL DEFAULT '{}',
    "insights" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "daily_metrics_pkey" PRIMARY KEY ("user_id","date")
);

-- CreateTable
CREATE TABLE "nudge_events" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "domain" TEXT NOT NULL,
    "subtype" TEXT NOT NULL,
    "decision_point" TEXT NOT NULL,
    "state" JSONB NOT NULL,
    "action_template" TEXT,
    "channel" TEXT NOT NULL,
    "sent" BOOLEAN NOT NULL DEFAULT true,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "nudge_events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "nudge_outcomes" (
    "id" UUID NOT NULL,
    "nudge_event_id" UUID NOT NULL,
    "reward" DOUBLE PRECISION,
    "short_term" JSONB NOT NULL DEFAULT '{}',
    "ema_score" JSONB,
    "signals" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "nudge_outcomes_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "feeling_sessions" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "feeling_id" TEXT NOT NULL,
    "topic" TEXT,
    "action_template" TEXT,
    "started_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "ended_at" TIMESTAMPTZ,
    "ema_better" BOOLEAN,
    "summary" TEXT,
    "transcript" JSONB,
    "context" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "feeling_sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "habit_logs" (
    "id" UUID NOT NULL,
    "user_id" UUID NOT NULL,
    "habit_id" TEXT NOT NULL,
    "occurred_on" DATE NOT NULL,
    "status" TEXT NOT NULL,
    "payload" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "habit_logs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "bandit_models" (
    "id" UUID NOT NULL,
    "domain" TEXT NOT NULL,
    "version" INTEGER NOT NULL DEFAULT 1,
    "weights" JSONB NOT NULL,
    "covariance" JSONB NOT NULL,
    "meta" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "bandit_models_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_type_estimates" (
    "user_id" UUID NOT NULL,
    "primary_type" VARCHAR(10) NOT NULL,
    "type_scores" JSONB NOT NULL DEFAULT '{}',
    "confidence" DECIMAL(5,4) NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "user_type_estimates_pkey" PRIMARY KEY ("user_id")
);

-- CreateTable
CREATE TABLE "type_stats" (
    "type_id" VARCHAR(10) NOT NULL,
    "tone" VARCHAR(20) NOT NULL,
    "tapped_count" BIGINT NOT NULL DEFAULT 0,
    "ignored_count" BIGINT NOT NULL DEFAULT 0,
    "thumbs_up_count" BIGINT NOT NULL DEFAULT 0,
    "thumbs_down_count" BIGINT NOT NULL DEFAULT 0,
    "sample_size" BIGINT NOT NULL DEFAULT 0,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "type_stats_pkey" PRIMARY KEY ("type_id","tone")
);

-- CreateTable
CREATE TABLE "hook_candidates" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "text" TEXT NOT NULL,
    "tone" VARCHAR(20) NOT NULL,
    "target_problem_types" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "target_user_types" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "app_tap_rate" DECIMAL(5,4) NOT NULL DEFAULT 0,
    "app_thumbs_up_rate" DECIMAL(5,4) NOT NULL DEFAULT 0,
    "app_sample_size" INTEGER NOT NULL DEFAULT 0,
    "tiktok_like_rate" DECIMAL(5,4) NOT NULL DEFAULT 0,
    "tiktok_share_rate" DECIMAL(5,4) NOT NULL DEFAULT 0,
    "tiktok_sample_size" INTEGER NOT NULL DEFAULT 0,
    "tiktok_high_performer" BOOLEAN NOT NULL DEFAULT false,
    "is_wisdom" BOOLEAN NOT NULL DEFAULT false,
    "exploration_weight" DECIMAL(3,2) NOT NULL DEFAULT 1.0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "hook_candidates_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tiktok_posts" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "hook_candidate_id" UUID,
    "tiktok_video_id" VARCHAR(100),
    "blotato_post_id" VARCHAR(100),
    "caption" TEXT,
    "posted_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "metrics_fetched_at" TIMESTAMPTZ,
    "view_count" BIGINT,
    "like_count" BIGINT,
    "comment_count" BIGINT,
    "share_count" BIGINT,
    "agent_reasoning" TEXT,
    "scheduled_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "tiktok_posts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "wisdom_patterns" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "pattern_name" VARCHAR(100) NOT NULL,
    "description" TEXT,
    "target_user_types" TEXT[] DEFAULT ARRAY[]::TEXT[],
    "effective_tone" VARCHAR(20),
    "effective_hook_pattern" TEXT,
    "effective_content_length" VARCHAR(20),
    "app_evidence" JSONB NOT NULL DEFAULT '{}',
    "tiktok_evidence" JSONB NOT NULL DEFAULT '{}',
    "confidence" DECIMAL(5,4) NOT NULL DEFAULT 0,
    "verified_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "wisdom_patterns_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "profiles_email_key" ON "profiles"("email");

-- CreateIndex
CREATE UNIQUE INDEX "bandit_models_domain_version_key" ON "bandit_models"("domain", "version");

-- CreateIndex
CREATE INDEX "user_type_estimates_primary_type_idx" ON "user_type_estimates"("primary_type");

-- CreateIndex
CREATE INDEX "hook_candidates_tone_idx" ON "hook_candidates"("tone");

-- CreateIndex
CREATE UNIQUE INDEX "hook_candidates_text_tone_key" ON "hook_candidates"("text", "tone");

-- CreateIndex
CREATE UNIQUE INDEX "tiktok_posts_tiktok_video_id_key" ON "tiktok_posts"("tiktok_video_id");

-- CreateIndex
CREATE INDEX "tiktok_posts_hook_candidate_id_idx" ON "tiktok_posts"("hook_candidate_id");

-- CreateIndex
CREATE INDEX "tiktok_posts_posted_at_idx" ON "tiktok_posts"("posted_at" DESC);

-- CreateIndex
CREATE UNIQUE INDEX "wisdom_patterns_pattern_name_key" ON "wisdom_patterns"("pattern_name");

-- AddForeignKey
ALTER TABLE "user_settings" ADD CONSTRAINT "user_settings_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "profiles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "nudge_outcomes" ADD CONSTRAINT "nudge_outcomes_nudge_event_id_fkey" FOREIGN KEY ("nudge_event_id") REFERENCES "nudge_events"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "user_type_estimates" ADD CONSTRAINT "user_type_estimates_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "profiles"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "tiktok_posts" ADD CONSTRAINT "tiktok_posts_hook_candidate_id_fkey" FOREIGN KEY ("hook_candidate_id") REFERENCES "hook_candidates"("id") ON DELETE SET NULL ON UPDATE CASCADE;

