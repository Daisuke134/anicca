from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

from .discovery import _default_providers, search_jobs
from .dedup import fingerprint_text
from .jobs import Job
from .knockout import _jpy_amounts, assess_candidate, shortlist_candidates
from .portfolio import classify_portfolio
from .ranking import evaluate
from .state import canonical_url


JAPAN_RE = re.compile(r"\b(?:japan|tokyo)\b|日本|東京", re.IGNORECASE)
WORLDWIDE_REMOTE_RE = re.compile(
    r"\b(?:remote worldwide|worldwide remote|work from anywhere|remote from anywhere|"
    r"anywhere in the world|globally remote|global remote)\b",
    re.IGNORECASE,
)
AI_RE = re.compile(r"\b(?:AI|LLM|GenAI|machine learning)\b|生成AI", re.IGNORECASE)
CUSTOMER_DEPLOYMENT_RE = re.compile(
    r"\b(?:deployment|forward deployed|solutions?|customer-facing|customers?)\b",
    re.IGNORECASE,
)
PRODUCT_RE = re.compile(r"\bproduct\b", re.IGNORECASE)


def _role_family(title: str, description: Any) -> str:
    text = f"{title} {description if isinstance(description, str) else ''}"
    title_folded = title.casefold()
    if "product" in title_folded:
        return "ai_product_management"
    if "program" in title_folded:
        return "technical_program_management"
    if "partnership" in title_folded:
        return "ai_partnerships"
    if "business development" in title_folded:
        return "ai_business_development"
    if "customer success" in title_folded:
        return "ai_customer_success"
    if "sales engineer" in title_folded:
        return "ai_sales_engineering"
    if "account" in title_folded:
        return "technical_account_management"
    if AI_RE.search(text) or CUSTOMER_DEPLOYMENT_RE.search(title):
        return "applied_ai"
    return "unknown"


def _source_for(candidate: dict[str, Any], field: str) -> str | None:
    marker = f"#{field}="
    return next(
        (span for span in candidate.get("source_spans", []) if marker in span),
        None,
    )


def _compensation(
    candidate: dict[str, Any], description: Any
) -> tuple[int | None, bool, str]:
    structured = candidate.get("compensation_evidence")
    if isinstance(structured, dict) and structured.get("type") == "annual_salary":
        currency = structured.get("currency")
        minimum = structured.get("min")
        if isinstance(minimum, int) and minimum > 0:
            if currency == "JPY":
                return minimum, False, "verified_jpy"
            if currency == "USD" and minimum >= 100_000:
                return None, True, "verified_six_figure_usd"
    amounts = _jpy_amounts(description)
    return (
        (min(amounts), False, "verified_jpy")
        if amounts
        else (None, False, "unverified")
    )


def _japan_eligibility(
    candidate: dict[str, Any], description: Any
) -> tuple[bool, str | None]:
    location_parts = [str(candidate.get("location") or "")]
    secondary = candidate.get("secondary_locations")
    if isinstance(secondary, list):
        location_parts.extend(str(value) for value in secondary)
    location_text = "; ".join(value for value in location_parts if value)
    if JAPAN_RE.search(location_text):
        primary_span = _source_for(candidate, "location")
        if primary_span and JAPAN_RE.search(str(candidate.get("location") or "")):
            return True, primary_span
        return True, (
            f"{candidate.get('official_url')}#secondary_locations={location_text}"
        )
    text = f"{location_text} {description if isinstance(description, str) else ''}"
    match = WORLDWIDE_REMOTE_RE.search(text)
    if match is None:
        return False, None
    return True, _source_for(candidate, "description") or _source_for(
        candidate, "location"
    )


def _rank_candidate(candidate: dict[str, Any], description: Any) -> dict[str, Any]:
    title = str(candidate.get("title") or "")
    location = str(candidate.get("location") or "")
    text = f"{title} {description if isinstance(description, str) else ''}"
    role_family = _role_family(title, description)
    compensation_min_jpy, six_figure_usd, compensation_status = _compensation(
        candidate, description
    )
    japan_eligible, japan_evidence = _japan_eligibility(candidate, description)
    skills: list[str] = []
    if AI_RE.search(text):
        skills.append("ai")
    if re.search(r"\bagents?\b", text, re.IGNORECASE):
        skills.append("agents")
    if CUSTOMER_DEPLOYMENT_RE.search(text):
        skills.append("customer_deployment")
    if PRODUCT_RE.search(text):
        skills.append("product")
    domains = ["enterprise_ai"] if AI_RE.search(text) else []
    job = Job(
        company=str(candidate.get("company") or ""),
        title=title,
        url=str(candidate.get("official_url") or ""),
        location=location,
        japan_eligible=japan_eligible,
        compensation_min_jpy=compensation_min_jpy,
        clearance_required=False,
        skills=skills,
        domains=domains,
    )
    evaluation = evaluate(job, six_figure_usd_verified=six_figure_usd)
    portfolio_bucket = None
    if evaluation.eligible and role_family != "unknown":
        portfolio_bucket = classify_portfolio(
            score=evaluation.score,
            compensation_min_jpy=compensation_min_jpy,
            role_family=role_family,
        )
    return {
        "role_family": role_family,
        "compensation_min_jpy": compensation_min_jpy,
        "compensation_status": compensation_status,
        "ranking_inputs": {
            "japan_eligible": job.japan_eligible,
            "japan_eligible_source_span": japan_evidence,
            "role_family_source_span": _source_for(candidate, "title"),
            "compensation_source_span": candidate.get("compensation_evidence"),
            "six_figure_usd_verified": six_figure_usd,
            "skills": skills,
            "domains": domains,
        },
        "ranking": {
            "eligible": evaluation.eligible,
            "score": evaluation.score,
            "components": evaluation.components,
            "reasons": list(evaluation.reasons),
            "warnings": list(evaluation.warnings),
        },
        "portfolio_bucket": portfolio_bucket,
        "ranking_ready": evaluation.eligible and portfolio_bucket is not None,
    }


def _excerpt(text: Any, pattern: re.Pattern[str], limit: int = 240) -> str | None:
    if not isinstance(text, str):
        return None
    match = pattern.search(text)
    if match is None:
        return None
    start = max(0, match.start() - 80)
    return text[start : start + limit].strip() or None


def build_prefilter_result(
    plan: dict[str, Any], *, search: Callable[[str], dict[str, Any]]
) -> dict[str, Any]:
    queries = plan.get("queries")
    if not isinstance(queries, list):
        raise ValueError("recovery plan requires queries")
    candidates_by_url: dict[str, dict[str, Any]] = {}
    provider_results: list[dict[str, Any]] = []
    for query_item in queries:
        if not isinstance(query_item, dict):
            continue
        query = str(query_item.get("query", "")).strip()
        if not query:
            continue
        try:
            discovery = search(query)
        except Exception as exc:
            provider_results.append(
                {
                    "provider": "multi_source",
                    "query": query,
                    "status": "failed",
                    "result_count": 0,
                    "error": str(exc)[-500:],
                }
            )
            continue
        providers = discovery.get("providers")
        if isinstance(providers, list):
            for provider in providers:
                if not isinstance(provider, dict):
                    continue
                provider_results.append(
                    {
                        "provider": str(provider.get("name", "unknown")),
                        "query": query,
                        "status": str(provider.get("status", "unknown")),
                        "result_count": int(provider.get("count", 0) or 0),
                        "error": (
                            str(provider["error"])[-500:]
                            if provider.get("error") is not None
                            else None
                        ),
                    }
                )
        rows = discovery.get("results")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            url = str(row.get("canonical_url") or row.get("url") or "").strip()
            title = str(row.get("title") or "").strip()
            company = str(row.get("company") or "").strip()
            if not url or not title or not company:
                continue
            normalized_url = canonical_url(url)
            if normalized_url in candidates_by_url:
                continue
            location = str(row.get("location") or "").strip() or None
            description = row.get("description")
            secondary_locations = row.get("secondary_locations")
            compensation = row.get("compensation")
            candidate = {
                "bucket": query_item.get("bucket"),
                "language": query_item.get("language"),
                "provider": row.get("discovery_provider"),
                "official_url": normalized_url,
                "title": title,
                "company": company,
                "location": location,
                "ai_requirement_evidence": _excerpt(description, AI_RE),
                "japan_eligibility_evidence": None,
                "compensation_evidence": (
                    compensation if isinstance(compensation, dict) else None
                ),
                "secondary_locations": (
                    secondary_locations
                    if isinstance(secondary_locations, list)
                    else []
                ),
                "is_remote": row.get("is_remote") is True,
                "workplace_type": row.get("workplace_type"),
                "deadline_evidence": None,
                "jd_fingerprint": fingerprint_text(description),
            }
            candidate.update(
                assess_candidate(
                    {
                        **candidate,
                        "url": normalized_url,
                        "description": description,
                    }
                )
            )
            candidate.update(_rank_candidate(candidate, description))
            candidate["japan_eligibility_evidence"] = (
                location
                if location and JAPAN_RE.search(location)
                else candidate["ranking_inputs"]["japan_eligible_source_span"]
            )
            candidates_by_url[normalized_url] = candidate
    candidates = list(candidates_by_url.values())
    return {
        "status": "usable" if candidates else "browser_fallback_required",
        "candidates": candidates,
        "provider_results": provider_results,
        "blocked": [],
    }


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--queue-output", type=Path)
    parser.add_argument("--framework-root", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.recovery_plan.read_text(encoding="utf-8"))
    app_root = Path(__file__).resolve().parents[1]

    def search(query: str) -> dict[str, Any]:
        return search_jobs(
            query,
            providers=_default_providers(
                query,
                app_root=app_root,
                framework_root=args.framework_root.expanduser().resolve(),
            ),
        )

    queue_result = build_prefilter_result(plan, search=search)
    result = {
        **queue_result,
        "candidates": shortlist_candidates(queue_result["candidates"], limit=12),
    }
    if args.queue_output is not None:
        _write_private_json(args.queue_output, queue_result)
    _write_private_json(args.output, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "candidate_count": len(result["candidates"]),
                "queue_candidate_count": len(queue_result["candidates"]),
                "provider_result_count": len(result["provider_results"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
