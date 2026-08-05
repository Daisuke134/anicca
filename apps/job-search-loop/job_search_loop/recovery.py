from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .ledger import Ledger
from .portfolio import PORTFOLIO_LIMITS
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


def build_recovery_plan(
    *,
    portfolio_deficit: dict[str, int],
    consecutive_deficits: int,
) -> dict[str, object]:
    normalized = {
        bucket: max(0, int(portfolio_deficit.get(bucket, 0)))
        for bucket in PORTFOLIO_LIMITS
    }
    missing = [bucket for bucket, count in normalized.items() if count > 0]
    if not missing:
        return {
            "version": 1,
            "status": "quota_met",
            "consecutive_deficits": 0,
            "portfolio_deficit": normalized,
            "source_scopes": [],
            "queries": [],
            "hard_gates": list(HARD_GATES),
        }
    level = min(3, max(1, int(consecutive_deficits)))
    scopes = [scope for tier in SOURCE_TIERS[:level] for scope in tier]
    queries = [
        {"bucket": bucket, "language": language, "query": query}
        for bucket in missing
        for language, query in BASE_QUERIES[bucket]
    ]
    for expansion_level in range(2, level + 1):
        for bucket in missing:
            queries.extend(
                {
                    "bucket": bucket,
                    "language": language,
                    "query": f"{query} {bucket.replace('_', ' ')}",
                }
                for language, query in EXPANSION_QUERIES[expansion_level]
            )
    return {
        "version": 1,
        "status": "expanded",
        "expansion_level": level,
        "consecutive_deficits": max(1, int(consecutive_deficits)),
        "portfolio_deficit": normalized,
        "source_scopes": scopes,
        "queries": queries,
        "hard_gates": list(HARD_GATES),
    }


def build_runtime_plan(
    ledger: Ledger,
    *,
    day: str,
    now: datetime | None = None,
) -> dict[str, object]:
    events = ledger.quota_deficit_events(day)
    portfolio_confirmed = ledger.confirmed_daily_portfolio(day)
    portfolio_deficit = {
        bucket: max(0, limit - portfolio_confirmed[bucket])
        for bucket, limit in PORTFOLIO_LIMITS.items()
    }
    consecutive = 1
    if events:
        current = now or datetime.now(timezone.utc)
        first_observed = datetime.fromisoformat(events[0]["observed_at"])
        elapsed_hours = max(0, int((current - first_observed).total_seconds() // 3600))
        consecutive = max(len(events), elapsed_hours + 1)
    plan = build_recovery_plan(
        portfolio_deficit=portfolio_deficit,
        consecutive_deficits=consecutive,
    )
    plan["source_event_id"] = events[-1]["event_id"] if events else None
    return plan


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
