#!/usr/bin/env python3
"""Rank measured Capafy Instagram Reels and update copy guidance."""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

LEDGER = Path(
    os.environ.get(
        "CAPAFY_IG_LEDGER",
        os.path.expanduser("~/.local/state/life-manager/state/capafy-marketing-ig-ledger.jsonl"),
    )
)
METRICS = Path(
    os.environ.get(
        "CAPAFY_IG_METRICS",
        os.path.expanduser("~/.local/state/life-manager/state/capafy-marketing-ig-metrics.jsonl"),
    )
)
OUTPUT = Path(
    os.environ.get(
        "CAPAFY_IG_BEST_PRACTICES",
        str(Path(__file__).resolve().parent.parent / "IG_BEST_PRACTICES.md"),
    )
)
MIN_PATTERN_SAMPLE = 3
TOP_LIMIT = 3


def read_jsonl(path: Path) -> tuple[list[dict], int]:
    rows: list[dict] = []
    invalid = 0
    if not path.exists():
        return rows, invalid
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                invalid += 1
                continue
            if isinstance(row, dict):
                rows.append(row)
            else:
                invalid += 1
    return rows, invalid


def normalize_url(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    raw = value.strip()
    parts = urlsplit(raw)
    if not parts.netloc:
        return raw.rstrip("/")
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def reel_code(row: dict) -> str:
    code = row.get("code")
    if isinstance(code, str) and code.strip():
        return code.strip()
    url = normalize_url(row.get("reel_url"))
    match = re.search(r"/(?:reel|p)/([^/]+)$", url)
    return match.group(1) if match else ""


def identities(row: dict) -> list[str]:
    keys: list[str] = []
    code = reel_code(row)
    url = normalize_url(row.get("reel_url"))
    if code:
        keys.append(f"code:{code}")
    if url:
        keys.append(f"url:{url}")
    return keys


def row_ts(row: dict) -> int:
    try:
        return int(row.get("ts", 0))
    except (TypeError, ValueError):
        return 0


def metric_count(row: dict, field: str) -> int:
    try:
        return max(0, int(row.get(field, 0)))
    except (TypeError, ValueError):
        return 0


def engagement_score(metric: dict) -> int:
    return (
        metric_count(metric, "views")
        + metric_count(metric, "likes") * 3
        + metric_count(metric, "comments") * 5
    )


def latest_unique_reels(rows: list[dict]) -> list[dict]:
    unique: dict[str, tuple[int, int, dict]] = {}
    for order, row in enumerate(rows):
        keys = identities(row)
        if not keys:
            continue
        primary = keys[0]
        candidate = (row_ts(row), order, row)
        if primary not in unique or candidate[:2] >= unique[primary][:2]:
            unique[primary] = candidate
    return [item[2] for item in sorted(unique.values(), key=lambda item: item[1])]


def latest_metrics_index(rows: list[dict]) -> dict[str, tuple[int, int, dict]]:
    index: dict[str, tuple[int, int, dict]] = {}
    for order, row in enumerate(rows):
        candidate = (row_ts(row), order, row)
        for key in identities(row):
            if key not in index or candidate[:2] >= index[key][:2]:
                index[key] = candidate
    return index


def join_latest(ledger_rows: list[dict], metric_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    reels = latest_unique_reels(ledger_rows)
    metric_index = latest_metrics_index(metric_rows)
    joined: list[dict] = []
    missing: list[dict] = []
    for reel in reels:
        candidates = [metric_index[key] for key in identities(reel) if key in metric_index]
        if not candidates:
            missing.append(reel)
            continue
        metric = max(candidates, key=lambda item: item[:2])[2]
        joined.append(
            {
                "reel_url": reel.get("reel_url") or metric.get("reel_url") or "",
                "code": reel_code(reel) or reel_code(metric),
                "listing_name": reel.get("listing_name") or metric.get("listing_name") or "unknown",
                "category": reel.get("listing_category") or reel.get("category"),
                "hook": reel.get("hook") or reel.get("on_screen_hook") or reel.get("video_hook"),
                "views": metric_count(metric, "views"),
                "likes": metric_count(metric, "likes"),
                "comments": metric_count(metric, "comments"),
                "metric_ts": row_ts(metric),
                "score": engagement_score(metric),
            }
        )
    joined.sort(
        key=lambda row: (
            -row["score"],
            -row["views"],
            -row["likes"],
            -row["comments"],
            str(row["reel_url"]),
        )
    )
    return joined, missing


def hook_style(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    hook = value.strip()
    if "?" in hook or "？" in hook:
        return "question"
    if re.match(r"^\s*\d", hook):
        return "number-led"
    if "!" in hook or "！" in hook:
        return "exclamation"
    return "statement"


def grouped_scores(rows: list[dict], field: str) -> list[tuple[str, int, float]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        value = row.get(field)
        if field == "hook":
            value = hook_style(value)
        if isinstance(value, str) and value.strip():
            groups[value.strip()].append(row["score"])
    summary = [
        (name, len(scores), sum(scores) / len(scores))
        for name, scores in groups.items()
    ]
    return sorted(summary, key=lambda item: (-item[2], -item[1], item[0].lower()))


def md_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def reel_table(rows: list[dict]) -> list[str]:
    lines = [
        "| Rank | Reel | Score | Views | Likes | Comments | Listing |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for rank, row in enumerate(rows, 1):
        url = md_cell(row["reel_url"])
        link = f"[{md_cell(row['code'] or 'reel')}]({url})" if url else md_cell(row["code"] or "unknown")
        lines.append(
            f"| {rank} | {link} | {row['score']} | {row['views']} | {row['likes']} | "
            f"{row['comments']} | {md_cell(row['listing_name'])} |"
        )
    return lines


def group_table(groups: list[tuple[str, int, float]]) -> list[str]:
    lines = ["| Observed group | Reels | Average score |", "|---|---:|---:|"]
    for name, count, average in groups:
        lines.append(f"| {md_cell(name)} | {count} | {average:.2f} |")
    return lines


def render(
    ledger_count: int,
    ranked: list[dict],
    missing: list[dict],
    invalid_ledger: int,
    invalid_metrics: int,
) -> str:
    measured = len(ranked)
    baseline_only = measured < MIN_PATTERN_SAMPLE
    cohort_size = min(TOP_LIMIT, max(1, measured // 3)) if measured else 0
    top = ranked[:cohort_size]
    bottom = ranked[-cohort_size:] if measured >= MIN_PATTERN_SAMPLE else []
    categories = grouped_scores(ranked, "category")
    hooks = grouped_scores(ranked, "hook")

    lines = [
        "# Instagram Reel Best Practices",
        "",
        "<!-- Generated by scripts/ig_reflect.py from the IG ledger and latest real metrics snapshots. -->",
        "",
        "## Measurement",
        "",
        "- Engagement score: `views + likes*3 + comments*5`.",
        "- One latest metrics snapshot per Reel. Snapshots are not summed.",
        f"- Ledger Reels: {ledger_count}",
        f"- Reels with metrics: {measured}",
        f"- Reels without metrics: {len(missing)}",
        f"- Invalid JSONL rows skipped: ledger={invalid_ledger}, metrics={invalid_metrics}",
        "",
        "## Status",
        "",
    ]
    if baseline_only:
        lines.append(
            f"**SAMPLE INSUFFICIENT — baseline only.** {measured} measured Reel(s); "
            f"at least {MIN_PATTERN_SAMPLE} are required before claiming a winning or losing pattern."
        )
    else:
        lines.append(
            f"Comparison active across {measured} measured Reels. Observations are associations, not causal proof."
        )

    lines.extend(["", f"## Top Reels (N={len(top)})", ""])
    if top:
        lines.extend(reel_table(top))
    else:
        lines.append("No Reel has a metrics snapshot yet.")

    lines.extend(["", "## Lower-performing Reels", ""])
    if bottom:
        lines.extend(reel_table(bottom))
    else:
        lines.append("Not reported until at least 3 Reels have metrics; a baseline cannot form a lower cohort.")

    lines.extend(["", "## Observed Tendencies", ""])
    if baseline_only:
        lines.append("- No winning pattern claimed from the current sample.")
        if measured == 1:
            lines.append(f"- Current baseline score: {ranked[0]['score']}.")
        if measured > 1 and len({row["score"] for row in ranked}) == 1:
            lines.append(f"- All measured Reels are tied at score {ranked[0]['score']}; no separation exists.")
    else:
        lines.append(f"- Observed score range: {ranked[-1]['score']} to {ranked[0]['score']}.")

    if categories:
        lines.extend(["", "### Listing category averages", "", *group_table(categories)])
    else:
        lines.append("- Listing category metadata unavailable; no category trend inferred from listing names.")

    if hooks:
        lines.extend(["", "### Hook style averages", "", *group_table(hooks)])
    else:
        lines.append("- Hook metadata unavailable; no hook-tone trend inferred.")

    lines.extend(["", "## Next Test Direction", ""])
    if baseline_only:
        needed = MIN_PATTERN_SAMPLE - measured
        lines.append(
            f"Collect metrics for {needed} more Reel(s). Keep current measured Reel(s) as baseline; "
            "do not change copy solely because of this ranking yet."
        )
    else:
        directions: list[str] = []
        if categories:
            directions.append(
                f"Test the highest observed category again: `{categories[0][0]}` "
                f"(average score {categories[0][2]:.2f}, n={categories[0][1]})."
            )
        if hooks:
            directions.append(
                f"Test the highest observed hook style again: `{hooks[0][0]}` "
                f"(average score {hooks[0][2]:.2f}, n={hooks[0][1]})."
            )
        if not directions:
            directions.append(
                "Use the top Reel URL as the measured reference. No category or hook element is identifiable from current metadata."
            )
        lines.extend(directions)

    if missing:
        lines.extend(["", "## Missing Metrics", ""])
        for reel in missing:
            label = reel.get("listing_name") or reel_code(reel) or reel.get("reel_url") or "unknown Reel"
            lines.append(f"- {md_cell(label)}")

    return "\n".join(lines) + "\n"


def main() -> int:
    ledger_rows, invalid_ledger = read_jsonl(LEDGER)
    metric_rows, invalid_metrics = read_jsonl(METRICS)
    reels = latest_unique_reels(ledger_rows)
    ranked, missing = join_latest(ledger_rows, metric_rows)
    content = render(len(reels), ranked, missing, invalid_ledger, invalid_metrics)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "ledger_reels": len(reels),
                "measured_reels": len(ranked),
                "unmeasured_reels": len(missing),
                "baseline_only": len(ranked) < MIN_PATTERN_SAMPLE,
                "output": str(OUTPUT),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
