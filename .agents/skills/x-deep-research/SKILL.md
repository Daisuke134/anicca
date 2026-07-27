---
name: x-deep-research
description: Search X deeply and read complete X posts/articles with a safe authenticated-browser search plus a no-key full-text fetch fallback.
---

# X Deep Research

Use this skill when the user asks to search X, inspect X discussions, compare
popular posts, read a thread or X Article, or ground research in current X
content.

## Non-negotiable boundary

This is a read-only research skill. It never posts, replies, likes, bookmarks,
deletes, drafts, or publishes. Use the existing Writer publication pipeline for
writes.

The browser adapter must never navigate a page whose URL contains `/compose`,
`/articles/edit`, `/intent/`, `/settings`, or `/messages`.

## Route

| Request | First tool | Why |
|---|---|---|
| Topic, keyword, author, or current discussion | `browser_search.py` | Reuses the authenticated daily-driver and does not consume depleted X API credits |
| Known X status URL | `x_fetch.py` | Restores the complete post or X Article body through pinned x-tweet-fetcher/FxTwitter |
| A search result selected for quoting or analysis | `x_fetch.py` after search | Visible search cards are previews; the full body is the evidence |
| Reply completeness or full-archive export | Report as unavailable in the free route | Do not invent completeness; use Xquik/official API only after a credential health check passes |

## Search

From the repository root:

```bash
uv run --with playwright \
  .agents/skills/x-deep-research/scripts/browser_search.py \
  '("loop engineering" OR "eval engineering") min_faves:20 -filter:replies' \
  --mode top \
  --count 40 \
  --max-scrolls 40
```

Use X search operators to bound the corpus:

```text
from:<handle>
since:YYYY-MM-DD
until:YYYY-MM-DD
min_faves:<n>
min_retweets:<n>
lang:en
lang:ja
-filter:replies
-filter:retweets
```

Run at least one high-engagement `top` query and one chronological `live`
query. For bilingual research, run separate English and Japanese queries.

Read these result fields:

- `complete`: whether the requested unique-result count was reached;
- `partial_reason`: why a bounded search stopped;
- `scrolls`: how far the browser actually traversed;
- `results[].url`: canonical evidence URL;
- `results[].metrics`: visible engagement labels.

Never describe a partial corpus as “all X posts.”

## Read a post or X Article in full

```bash
python3 .agents/skills/x-deep-research/scripts/x_fetch.py \
  'https://x.com/archiveexplorer/status/2080621294979023358'
```

For an Article, use:

```text
.raw.tweet.article.title
.raw.tweet.article.full_text
.raw.tweet.article.images
```

For a regular post, use:

```text
.raw.tweet.text
.raw.tweet.likes
.raw.tweet.retweets
.raw.tweet.bookmarks
.raw.tweet.views
```

Only quote or summarize when `complete=true`. Preserve the canonical X URL in
the output.

## Research loop

```text
1. Search top and live in English.
2. Search top and live in Japanese when relevant.
3. Deduplicate canonical status URLs.
4. Select posts by relevance, not engagement alone.
5. Fetch every selected URL in full.
6. Separate primary claims from commentary and hype.
7. Replace viral claims with official docs, papers, or source repositories.
8. Record search completeness and known blind spots.
```

X is a discovery and zeitgeist source. It is not the final authority for
technical claims.

## Current adapter state

| Adapter | State |
|---|---|
| Authenticated CDP search | Live and free |
| x-tweet-fetcher known-URL fetch | Live, pinned to `085b931f53557da9e25c0d2e6aa5b3b980513125` |
| Official X API | Configured but returned `402 credits depleted` on 2026-07-27 |
| Xquik | Best deep API design, but no local credential/live verification |
| Firecrawl | Useful second-source check; not the X retrieval authority |

Read [tool-evaluation.md](references/tool-evaluation.md) before changing the
route or adding an adapter.

