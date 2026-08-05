from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit


SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class AtsApiResolution:
    ats: str
    api_url: str
    parts: dict[str, str]
    board_level: bool = False


def _safe(*values: str) -> bool:
    return all(
        value
        and all(
            segment
            and SAFE_SEGMENT.fullmatch(segment) is not None
            and ".." not in segment
            for segment in value.split("/")
        )
        for value in values
    )


def resolve_ats_api(raw_url: str) -> AtsApiResolution | None:
    try:
        parsed = urlsplit(raw_url)
    except ValueError:
        return None
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
        return None
    host = (parsed.hostname or "").lower()
    path = parsed.path

    if host in {
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "job-boards.eu.greenhouse.io",
    }:
        match = re.fullmatch(r"/([^/]+)/jobs/(\d+)/?", path)
        if match and _safe(*match.groups()):
            board, job_id = match.groups()
            return AtsApiResolution(
                ats="greenhouse",
                api_url=f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}",
                parts={"board": board, "job_id": job_id},
            )

    lever_host = re.fullmatch(r"jobs\.((?:eu\.)?lever\.co)", host)
    if lever_host:
        match = re.fullmatch(r"/([^/]+)/([^/]+)/?", path)
        if match and _safe(*match.groups()):
            slug, job_id = match.groups()
            api_host = f"api.{lever_host.group(1)}"
            return AtsApiResolution(
                ats="lever",
                api_url=f"https://{api_host}/v0/postings/{slug}/{job_id}",
                parts={"slug": slug, "job_id": job_id},
            )

    if host == "jobs.ashbyhq.com":
        match = re.fullmatch(r"/([^/]+)/([^/]+)(?:/application)?/?", path)
        if match and _safe(*match.groups()):
            org, job_id = match.groups()
            return AtsApiResolution(
                ats="ashby",
                api_url=f"https://api.ashbyhq.com/posting-api/job-board/{org}",
                parts={"org": org, "job_id": job_id},
                board_level=True,
            )

    workday_host = re.fullmatch(r"([\w-]+)\.(wd[\w-]*)\.myworkdayjobs\.com", host)
    if workday_host:
        match = re.fullmatch(
            r"/(?:[a-z]{2}-[A-Z]{2}/)?([^/]+)/job/(.+?)/?",
            path,
        )
        if match:
            tenant, shard = workday_host.groups()
            site, job_path = match.groups()
            if _safe(tenant, shard, site, job_path):
                return AtsApiResolution(
                    ats="workday",
                    api_url=(
                        f"https://{tenant}.{shard}.myworkdayjobs.com/wday/cxs/"
                        f"{tenant}/{site}/job/{job_path}"
                    ),
                    parts={
                        "tenant": tenant,
                        "shard": shard,
                        "site": site,
                        "job_path": job_path,
                    },
                )

    if host == "apply.workable.com":
        match = re.fullmatch(r"/([^/]+)/j/([^/]+)/?", path)
        if match and _safe(*match.groups()):
            slug, shortcode = match.groups()
            return AtsApiResolution(
                ats="workable",
                api_url=(
                    "https://apply.workable.com/api/v1/widget/accounts/"
                    f"{slug}?details=true"
                ),
                parts={"slug": slug, "shortcode": shortcode},
                board_level=True,
            )
    return None


def classify_ashby_board(payload: Any, job_id: str) -> dict[str, str] | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        return None
    target = job_id.casefold()
    for job in payload["jobs"]:
        if not isinstance(job, dict) or not isinstance(job.get("id"), str):
            continue
        if job["id"].casefold() == target and job.get("isListed") is not False:
            return {
                "result": "active",
                "code": "ashby_api_ok",
                "reason": "Ashby posting is listed on the public board",
            }
    return {
        "result": "expired",
        "code": "ashby_api_unlisted",
        "reason": "Ashby posting is absent from the public board",
    }


def classify_workable_board(payload: Any, shortcode: str) -> dict[str, str] | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        return None
    target = shortcode.casefold()
    for job in payload["jobs"]:
        if not isinstance(job, dict):
            continue
        candidate = job.get("shortcode")
        if isinstance(candidate, str) and candidate.casefold() == target:
            return {
                "result": "active",
                "code": "workable_api_ok",
                "reason": "Workable posting is listed on the public board",
            }
        url = job.get("url") or job.get("shortlink")
        if isinstance(url, str):
            resolved = resolve_ats_api(url)
            if (
                resolved is not None
                and resolved.ats == "workable"
                and resolved.parts["shortcode"].casefold() == target
            ):
                return {
                    "result": "active",
                    "code": "workable_api_ok",
                    "reason": "Workable posting is listed on the public board",
                }
    return {
        "result": "expired",
        "code": "workable_api_unlisted",
        "reason": "Workable posting is absent from the public board",
    }
