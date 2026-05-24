#!/usr/bin/env bash
# Postiz API helpers. Source this file.
# Requires: curl, jq, env POSTIZ_API_KEY

POSTIZ_BASE="${POSTIZ_BASE:-https://api.postiz.com/public/v1}"

postiz_list_posts() {
  # $1 = startDate ISO, $2 = endDate ISO
  local start="$1" end="$2"
  curl -sS -H "Authorization: ${POSTIZ_API_KEY}" \
    "${POSTIZ_BASE}/posts?startDate=${start}&endDate=${end}"
}

postiz_get_analytics() {
  # $1 = postId
  local post_id="$1"
  curl -sS -H "Authorization: ${POSTIZ_API_KEY}" \
    "${POSTIZ_BASE}/analytics/post/${post_id}"
}

# Aggregate analytics across an array of post-analytics JSON.
# Pipe N analytics responses (newline-separated) into stdin. Postiz returns
# either a list [{label,percentageChange,data:[{total,date}]}] (real data),
# [] (published but no analytics — e.g. TikTok), or {"missing":true}.
# Output: single JSON {posts, posts_with_data, total_views, total_likes,
#         total_comments, engagement_rate}.
postiz_aggregate() {
  python3 - <<'PY'
import sys, json

VIEW = ('view', 'impression', 'reach', 'play')
LIKE = ('like', 'reaction', 'favorite', 'digg')
CMNT = ('comment', 'repl')

posts = with_data = 0
views = likes = comments = 0
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        d = json.loads(line)
    except Exception:
        continue
    posts += 1
    if not isinstance(d, list) or not d:
        continue  # [] / {"missing":true} — no analytics, not a failure
    had = False
    for item in d:
        if not isinstance(item, dict):
            continue
        label = (item.get('label') or '').lower()
        total = 0
        for pt in (item.get('data') or []):
            try:
                total += float(pt.get('total', 0))
            except Exception:
                pass
        if total:
            had = True
        if any(k in label for k in VIEW):
            views += total
        elif any(k in label for k in LIKE):
            likes += total
        elif any(k in label for k in CMNT):
            comments += total
    if had:
        with_data += 1
er = ((likes + comments) / views * 100) if views > 0 else 0.0
print(json.dumps({
    "posts": posts,
    "posts_with_data": with_data,
    "total_views": int(views),
    "total_likes": int(likes),
    "total_comments": int(comments),
    "engagement_rate": round(er, 2),
}))
PY
}
