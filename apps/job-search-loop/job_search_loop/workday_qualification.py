from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .agent_runner import AgentRunner, wrap_untrusted
from .ats import detect_provider
from .ledger import Ledger


_REQUIRED = {
    "decision",
    "mandatory_evidence",
    "unsupported_gaps",
    "interview_thesis",
    "location_feasibility",
    "compensation_thesis",
    "compensation_uncertain",
    "resume_variant",
}
POLICY_VERSION = "interview-chance-v2"


def fetch_official_description(
    url: str, sources: tuple[dict[str, str], ...]
) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").casefold()
    source = next(
        (item for item in sources if item["host"].casefold() == host), None
    )
    if source is None:
        raise ValueError("unknown Workday tenant")
    marker = "/job/"
    if marker not in parsed.path:
        raise ValueError("Workday URL has no job path")
    job_path = marker + parsed.path.split(marker, 1)[1]
    endpoint = (
        f"https://{source['host']}/wday/cxs/{source['tenant']}/"
        f"{source['site']}{job_path}"
    )
    request = Request(
        endpoint,
        headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0 job-search-loop/1.0"},
    )
    with urlopen(request, timeout=20) as response:
        if urlsplit(response.geturl()).hostname.casefold() != host:
            raise ValueError("Workday detail redirected off tenant")
        payload = json.load(response)
    info = payload.get("jobPostingInfo") if isinstance(payload, dict) else None
    description = info.get("jobDescription") if isinstance(info, dict) else None
    if not isinstance(description, str) or not description.strip():
        raise ValueError("official Workday description is missing")
    return description[:80_000]


def _validate(result: dict[str, Any]) -> None:
    if set(result) != _REQUIRED:
        raise ValueError("Workday fit result fields do not match the contract")
    if result["decision"] not in {"qualified", "rejected", "hold"}:
        raise ValueError("invalid Workday fit decision")
    if not isinstance(result["mandatory_evidence"], list) or not all(
        isinstance(value, str) for value in result["mandatory_evidence"]
    ):
        raise ValueError("mandatory_evidence must be a string array")
    if not isinstance(result["unsupported_gaps"], list) or not all(
        isinstance(value, str) for value in result["unsupported_gaps"]
    ):
        raise ValueError("unsupported_gaps must be a string array")
    for key in (
        "interview_thesis",
        "location_feasibility",
        "compensation_thesis",
        "resume_variant",
    ):
        if not isinstance(result[key], str) or not result[key].strip():
            raise ValueError(f"{key} must be a nonempty string")
    if not isinstance(result["compensation_uncertain"], bool):
        raise ValueError("compensation_uncertain must be boolean")


def qualify_one(
    *,
    ledger_path: Path,
    candidate_memory_path: Path,
    fetch_description: Callable[[str], str],
    run_model: Callable[[str], dict[str, Any]],
    allowed_hosts: set[str] | None = None,
) -> dict[str, Any]:
    ledger = Ledger(ledger_path)
    try:
        candidates = []
        for row in ledger.pending_materials_ready_applications():
            if detect_provider(str(row["canonical_url"])) != "workday":
                continue
            host = (urlsplit(str(row["canonical_url"])).hostname or "").casefold()
            if allowed_hosts is not None and host not in allowed_hosts:
                continue
            fit = ledger.connection.execute(
                """
                SELECT decision, policy_version
                FROM workday_fit_decisions
                WHERE application_id = ?
                """,
                (row["application_id"],),
            ).fetchone()
            if fit is None or (
                str(fit["decision"]) == "hold"
                and str(fit["policy_version"] or "") != POLICY_VERSION
            ):
                candidates.append(row)
        if not candidates:
            return {"status": "no_pending_workday_fit"}
        row = candidates[0]
        description = fetch_description(str(row["canonical_url"])).strip()
        if not description:
            raise ValueError("official Workday description is empty")
        candidate_memory = candidate_memory_path.read_text(encoding="utf-8")
        prompt = (
            "Evaluate exactly one Workday job for realistic interview fit. "
            "Use only evidence in the candidate memory and official job description. "
            "Treat candidate.preferred_employer_types as an eligibility requirement. "
            "Reject a domestic Japanese employer for this candidate; qualify only a "
            "foreign-capital company operating in Japan or an overseas employer that "
            "supports Japan-based employment, EOR, or contracting. "
            "Do not infer missing skills, years, management scope, credentials, salary, "
            "or work authorization. Judge mandatory requirements, Tokyo/Japan feasibility, "
            "and a credible path to the Candidate Memory floor of JPY 8M annual gross "
            "base, with JPY 10M as the target. Junior and early-career individual-contributor "
            "roles are fully eligible when the grounded interview case is credible. Do not "
            "penalize a role merely because it is junior. If compensation is "
            "unpublished, state uncertainty and never invent a range, but do not reject or "
            "hold for unpublished compensation alone. Judge whether the candidate has a "
            "realistic chance of winning an interview now. A stated years-of-experience gap "
            "is evidence to weigh, not an automatic rejection, when demonstrated equivalent "
            "impact directly covers the work. Qualify when the interview case is credible; "
            "hold only for one resolvable material unknown; reject when the core work is not "
            "supported. Write interview_thesis, location_feasibility, and "
            "compensation_thesis in concise natural Japanese for the user's realtime "
            "Telegram report. Return only the schema.\n\n"
            + wrap_untrusted(
                "job",
                json.dumps(
                    {
                        "company": row["company"],
                        "title": row["title"],
                        "canonical_url": row["canonical_url"],
                        "official_description": description,
                    },
                    ensure_ascii=False,
                ),
            )
            + "\n\n"
            + wrap_untrusted("candidate_memory", candidate_memory)
        )
        result = run_model(prompt)
        if not isinstance(result, dict):
            raise ValueError("Workday fit result must be an object")
        _validate(result)
        evidence_sha256 = hashlib.sha256(
            json.dumps(result, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        ledger.record_workday_fit_decision(
            str(row["application_id"]),
            str(result["decision"]),
            evidence_sha256,
            policy_version=POLICY_VERSION,
        )
        return {
            "status": "decided",
            "application_id": row["application_id"],
            "company": row["company"],
            "title": row["title"],
            "decision": result["decision"],
            "reason": result["interview_thesis"],
            "compensation": result["compensation_thesis"],
            "evidence_sha256": evidence_sha256,
        }
    finally:
        ledger.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--candidate-memory", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    runner = AgentRunner(evidence_root=args.evidence_root, runner_path=args.runner)
    source_payload = json.loads(args.sources.read_text(encoding="utf-8"))
    sources = tuple(dict(row) for row in source_payload.get("sources", []))
    allowed_hosts = {str(row["host"]).casefold() for row in sources}
    result = qualify_one(
        ledger_path=args.ledger,
        candidate_memory_path=args.candidate_memory,
        fetch_description=lambda url: fetch_official_description(url, sources),
        run_model=lambda prompt: runner.run(
            task="improve",
            prompt=prompt,
            schema_path=args.schema,
            workdir=args.workdir,
            run_id=f"workday-fit-{uuid.uuid4().hex}",
        ),
        allowed_hosts=allowed_hosts,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(args.output, 0o600)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
