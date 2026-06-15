---
name: anicca-product-growth
description: Daily $0→$4K MRR loop for aniccaai.com per manoj_ahi/TheStatsApi recipe. (a) Firecrawl 3 niche directories (b) draft outreach email (50% affiliate offer) (c) send via gog (d) Reddit comment proposal (e) 1 programmatic SEO page (f) 1 blog post — commit to apps/landing. 10:23 JST daily.
metadata:
  type: scheduled_growth
  parallel_safe: true
  requires:
    bins: [firecrawl, gog, jq, python3, git]
    env: [GOG_ACCOUNT, GOG_KEYRING_PASSWORD]
---

# anicca-product-growth

## Source

Manoj `@manoj_ahi` TheStatsApi $0→$4K MRR thread (90 days). Verified recipe:
- Niche directory listings → 50% commission affiliate partnership
- Subreddit comments (help-first, no promo)
- Customer support chat → fast iteration → conversion boost
- Programmatic SEO pages (per league, per data point)
- Blog tutorials in popular langs/frameworks (Python, Node, Next.js)
- `llms.txt` for LLM search visibility
- Free tools as funnel

## Daily flow (cron 10:23 JST)

```bash
set -a; source ~/.openclaw/.env; set +a

# 1. Pick today's niche segment + 3 directories (rotation)
SEGMENT=$(./scripts/pick-segment.sh)
DIRECTORIES=$(./scripts/find-directories.sh "$SEGMENT" --limit 3)

# 2. For top 1 directory, draft + send outreach
DIR=$(echo "$DIRECTORIES" | jq -c '.[0]')
DIR_NAME=$(echo "$DIR" | jq -r .name)
DIR_OWNER_EMAIL=$(echo "$DIR" | jq -r .owner_email)
DIR_URL=$(echo "$DIR" | jq -r .url)
DIR_AUDIENCE=$(echo "$DIR" | jq -r .audience_description)

BODY=$(./scripts/generate-directory-pitch.sh "$DIR_NAME" "$DIR_URL" "$DIR_AUDIENCE")
SUBJECT="50% commission affiliate proposal — Anicca for $DIR_NAME"

if [ -n "$DIR_OWNER_EMAIL" ] && [ "$DIR_OWNER_EMAIL" != "null" ]; then
  RESULT=$(gog gmail send --account "$GOG_ACCOUNT" \
    --to "$DIR_OWNER_EMAIL" --subject "$SUBJECT" --body-file - <<<"$BODY")
  MSG_ID=$(echo "$RESULT" | jq -r .message_id)
  echo "{\"ts\":\"$(date -Iseconds)\",\"directory\":\"$DIR_NAME\",\"email\":\"$DIR_OWNER_EMAIL\",\"gmail_message_id\":\"$MSG_ID\"}" \
    >> state/outreach-$(date +%Y-%m-%d).jsonl
fi

# 3. Programmatic SEO page (1/day, target keyword from rotating pool)
KEYWORD=$(./scripts/pick-seo-keyword.sh)
SLUG=$(echo "$KEYWORD" | python3 -c "import sys,re; print(re.sub(r'[^a-z0-9-]','-',sys.stdin.read().lower().strip()))")
SEO_PAGE_PATH=/Users/anicca/anicca-project/apps/landing/app/seo/$SLUG/page.tsx
mkdir -p "$(dirname "$SEO_PAGE_PATH")"
./scripts/generate-seo-page.sh "$KEYWORD" > "$SEO_PAGE_PATH"

# 4. Blog post (1/day, mix of tech tutorial + AI mindset)
BLOG_TITLE=$(./scripts/pick-blog-title.sh)
BLOG_SLUG=$(echo "$BLOG_TITLE" | python3 -c "import sys,re; print(re.sub(r'[^a-z0-9-]','-',sys.stdin.read().lower().strip()))")
BLOG_PATH=/Users/anicca/anicca-project/apps/landing/content/blog/$BLOG_SLUG.md
mkdir -p "$(dirname "$BLOG_PATH")"
./scripts/generate-blog.sh "$BLOG_TITLE" > "$BLOG_PATH"

# 5. Commit + push
cd /Users/anicca/anicca-project
git add apps/landing/app/seo/$SLUG/page.tsx apps/landing/content/blog/$BLOG_SLUG.md
git commit -m "feat(growth): SEO page $SLUG + blog $BLOG_SLUG (anicca-product-growth daily)"
git push 2>&1 | tail -5

# 6. Reddit comment proposal (manual ship for now — draft only)
REDDIT_DRAFT=$(./scripts/draft-reddit-comment.sh "$SEGMENT")
echo "$REDDIT_DRAFT" >> state/reddit-drafts-$(date +%Y-%m-%d).md

# 7. Slack #metrics summary
```

## Segment rotation (weekly)

