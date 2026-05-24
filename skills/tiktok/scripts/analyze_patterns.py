#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from collections import defaultdict
from statistics import mean
from scripts.lib.storage import load_json, save_json
from scripts.lib.schema import now_iso
from scripts.lib.output import print_header


def avg(values):
    return round(mean(values), 2) if values else 0.0


def top_group(videos, field):
    grouped = defaultdict(list)
    for v in videos:
        key = (v.get(field) or "unknown").strip() or "unknown"
        grouped[key].append(v)

    scored = []
    for key, items in grouped.items():
        scored.append({
            "name": key,
            "count": len(items),
            "avg_views": avg([i.get("views", 0) for i in items]),
            "avg_completion": avg([i.get("completion_rate", 0.0) for i in items]),
            "avg_engagement": avg([
                i.get("likes", 0) + i.get("comments", 0) + i.get("shares", 0) for i in items
            ]),
        })

    scored.sort(key=lambda x: (x["avg_completion"], x["avg_views"]), reverse=True)
    return scored


def build_recommendations(videos):
    recs = []
    if not videos:
        return ["No analytics logged yet. Start logging results to generate local pattern insights."]

    overall_completion = avg([v.get("completion_rate", 0.0) for v in videos])
    overall_views = avg([v.get("views", 0) for v in videos])

    if overall_completion < 30:
        recs.append("Average completion is low. Tighten the first 1–3 seconds and reduce setup before payoff.")
    elif overall_completion < 45:
        recs.append("Completion is moderate. Add stronger pattern interrupts and clearer payoff earlier.")
    else:
        recs.append("Completion is relatively strong. Double down on similar pacing and framing structures.")

    if overall_views < 5000:
        recs.append("Average views are still modest. Test stronger hooks and more specific audience framing.")
    else:
        recs.append("Some topics are gaining traction. Compare top-performing angles and repeat the strongest framing.")

    return recs


def main():
    analytics = load_json("analytics")
    videos = analytics.get("videos", [])

    by_angle = top_group(videos, "angle")
    by_hook = top_group(videos, "hook_type")
    by_topic = top_group(videos, "topic")
    recs = build_recommendations(videos)

    report = {
        "generated_at": now_iso(),
        "summary": {
            "total_videos": len(videos),
            "top_angles": by_angle[:5],
            "top_hook_types": by_hook[:5],
            "top_topics": by_topic[:5],
        },
        "recommendations": recs,
    }

    save_json("pattern_report", report)

    print_header("📈 TIKTOK PATTERN REPORT")
    print(f"Generated: {report['generated_at']}")
    print(f"Videos analyzed: {report['summary']['total_videos']}")

    print("\nTop Angles:")
    if by_angle:
        for item in by_angle[:5]:
            print(f"- {item['name']} | count={item['count']} | avg_views={item['avg_views']} | avg_completion={item['avg_completion']}")
    else:
        print("- No data")

    print("\nTop Hook Types:")
    if by_hook:
        for item in by_hook[:5]:
            print(f"- {item['name']} | count={item['count']} | avg_views={item['avg_views']} | avg_completion={item['avg_completion']}")
    else:
        print("- No data")

    print("\nRecommendations:")
    for rec in recs:
        print(f"- {rec}")


if __name__ == "__main__":
    main()
