-- Migration: Add slot columns and unique constraints for slot-based posting
--
-- Context:
--   tiktok_posts.blotato_post_id already exists from 0_init migration (line 340).
--   This migration only adds 'slot' to tiktok_posts and new columns to x_posts.
--   The DO block below deduplicates any existing blotato_post_id values before
--   creating the UNIQUE INDEX. PostgreSQL allows multiple NULLs in UNIQUE columns.
--
-- Deploy procedure:
--   1. Run `prisma migrate deploy` (or `prisma migrate resolve --applied` for baseline)
--   2. Verify: SELECT COUNT(*) FROM tiktok_posts WHERE blotato_post_id IS NOT NULL
--      GROUP BY blotato_post_id HAVING COUNT(*) > 1;  -- should return 0 rows
--   3. If step 2 returns rows, the DO block already nullified duplicates (kept newest)
--
ALTER TABLE "tiktok_posts" ADD COLUMN IF NOT EXISTS "slot" VARCHAR(20);

-- AlterTable: x_posts (NEW columns)
ALTER TABLE "x_posts" ADD COLUMN IF NOT EXISTS "blotato_post_id" VARCHAR(100);
ALTER TABLE "x_posts" ADD COLUMN IF NOT EXISTS "slot" VARCHAR(20);

-- CreateIndex: unique constraints on blotato_post_id
-- tiktok_posts.blotato_post_id: existing column, need to deduplicate before adding unique index
-- Use DO block to handle case where duplicates exist (set them to NULL first)
DO $$
BEGIN
  -- Deduplicate tiktok_posts.blotato_post_id: keep newest, NULL the rest
  UPDATE tiktok_posts SET blotato_post_id = NULL
  WHERE id NOT IN (
    SELECT DISTINCT ON (blotato_post_id) id
    FROM tiktok_posts
    WHERE blotato_post_id IS NOT NULL
    ORDER BY blotato_post_id, created_at DESC
  ) AND blotato_post_id IS NOT NULL;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS "tiktok_posts_blotato_post_id_key" ON "tiktok_posts"("blotato_post_id");
CREATE UNIQUE INDEX IF NOT EXISTS "x_posts_blotato_post_id_key" ON "x_posts"("blotato_post_id");
