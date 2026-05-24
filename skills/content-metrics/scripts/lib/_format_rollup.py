import sys, json
data = json.loads(sys.stdin.read())
top, bot = data.get('top5', []), data.get('bottom5', [])
print(f"🏆 *content-7day-rollup* — {data.get('period_start','?')} → {data.get('period_end','?')}")
if data.get('dry_run'):
    print("_(DRY_RUN — top-performers.json marked dry_run:true)_")
print("\n*Top 5 (by views)*")
for i, r in enumerate(top, 1):
    print(f"{i}. `{r['handle']}` ({r['platform']}) — {r.get('total_views',0):,} views, "
          f"{r.get('total_likes',0):,} likes, {r.get('posts',0)} posts")
print("\n*Bottom 5 (by views)*")
for i, r in enumerate(bot, 1):
    print(f"{i}. `{r['handle']}` ({r['platform']}) — {r.get('total_views',0):,} views, "
          f"{r.get('total_likes',0):,} likes, {r.get('posts',0)} posts")
