-- AlterTable: Add scheduled_at column to tiktok_posts
ALTER TABLE "tiktok_posts" ADD COLUMN "scheduled_at" TIMESTAMPTZ;
