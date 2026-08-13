from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .ledger import Ledger
from .summary import write_summary


HARD_GATES = (
    "japan_eligible",
    "compensation_floor_jpy_8000000",
    "truthful_candidate_facts",
    "ai_requirement_evidence",
    "language_requirement",
    "posting_not_expired",
    "clearance_eligibility",
    "cross_owner_duplicate_fence",
    "captcha_human_only",
)

SOURCE_TIERS = (
    ("general_web", "official_company_careers", "ashby", "greenhouse"),
    ("lever", "workday"),
    ("smartrecruiters", "tokyo_tech_boards", "remote_job_boards"),
)

BASE_QUERIES = {
    "dream": (
        ("en", 'AI agent leadership Japan OR "remote Japan" salary'),
        ("ja", "生成AI エージェント 高年収 東京 採用"),
    ),
    "strong_fit": (
        ("en", 'applied AI OR GenAI engineer Tokyo OR "remote Japan"'),
        ("ja", "生成AI LLM エンジニア 東京 リモート 求人"),
    ),
    "adjacent": (
        ("en", 'AI product OR technical program OR AI partnerships "Japan"'),
        ("ja", "AI プロダクトマネージャー 技術営業 パートナーシップ 求人"),
    ),
}

EXPANSION_QUERIES = {
    2: (
        ("en", "APAC remote from Japan AI hiring"),
        ("ja", "日本から海外リモート AI 採用"),
    ),
    3: (
        ("en", "fintech crypto consumer AI Japan careers"),
        ("ja", "フィンテック 暗号資産 コンシューマーAI 東京 求人"),
    ),
}


def build_discovery_plan(*, confirmed_count: int) -> dict[str, object]:
    buckets = tuple(BASE_QUERIES)
    scopes = [scope for tier in SOURCE_TIERS for scope in tier]
    queries = [
        {"bucket": bucket, "language": language, "query": query}
        for bucket in buckets
        for language, query in BASE_QUERIES[bucket]
    ]
    for expansion_queries in EXPANSION_QUERIES.values():
        for bucket in buckets:
            queries.extend(
                {
                    "bucket": bucket,
                    "language": language,
                    "query": f"{query} {bucket.replace('_', ' ')}",
                }
                for language, query in expansion_queries
            )
    return {
        "version": 2,
        "status": "active",
        "confirmed_count": confirmed_count,
        "source_scopes": scopes,
        "queries": queries,
        "hard_gates": list(HARD_GATES),
    }


def build_runtime_plan(
    ledger: Ledger,
    *,
    day: str,
) -> dict[str, object]:
    return build_discovery_plan(
        confirmed_count=ledger.confirmed_daily_count(day),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("plan",))
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--day", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parsed = parser.parse_args(argv)
    ledger = Ledger(parsed.ledger)
    try:
        plan = build_runtime_plan(ledger, day=parsed.day)
    finally:
        ledger.close()
    write_summary(parsed.output, plan)
    os.chmod(parsed.output, 0o600)
    print(json.dumps(plan, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
