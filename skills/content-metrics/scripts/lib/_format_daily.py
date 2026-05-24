import sys, json
rows = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        rows.append(json.loads(line))
    except Exception:
        pass
print("📊 *content-metrics daily — last 24h*")
print("```")
print(f"{'account':<32} {'platform':<10} {'posts':>5} {'views':>10} {'likes':>8} {'er%':>6}")
print("-" * 76)
for r in sorted(rows, key=lambda x: -int(x.get('total_views', 0))):
    print(f"{str(r.get('handle','?'))[:32]:<32} {r.get('platform','?'):<10} "
          f"{r.get('posts',0):>5} {r.get('total_views',0):>10,} "
          f"{r.get('total_likes',0):>8,} {r.get('engagement_rate',0):>6.2f}")
print("```")
