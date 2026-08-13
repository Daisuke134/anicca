from __future__ import annotations

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


TOKEN_RE = re.compile(r"[A-Za-z0-9+#.-]{2,}")
STOPWORDS = {"and", "or", "the", "from", "with", "job", "jobs", "hiring"}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _api_url(board: dict[str, str]) -> str:
    ats = board["ats"]
    slug = board["slug"]
    if re.fullmatch(r"[A-Za-z0-9._-]+", slug) is None or ".." in slug:
        raise ValueError("unsafe ATS board slug")
    if ats == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    if ats == "greenhouse":
        return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    raise ValueError(f"unsupported ATS board: {ats}")


def _request_json(
    url: str, *, timeout_seconds: float, follow_redirects: bool
) -> Any:
    if follow_redirects:
        raise ValueError("official ATS board requests must not follow redirects")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {
        "api.ashbyhq.com",
        "boards-api.greenhouse.io",
    }:
        raise ValueError("official ATS board request escaped fixed hosts")
    opener = build_opener(_NoRedirect())
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 AniccaJobSearch/1.0",
        },
        method="GET",
    )
    with opener.open(request, timeout=timeout_seconds) as response:
        if int(response.status) != 200:
            raise ValueError(f"official ATS board returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def _posted_at_ms(value: Any) -> int | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return None


def _ashby_annual_salary(value: dict[str, Any]) -> dict[str, Any] | None:
    compensation = value.get("compensation")
    components = (
        compensation.get("summaryComponents")
        if isinstance(compensation, dict)
        else None
    )
    if not isinstance(components, list):
        return None
    for component in components:
        if not isinstance(component, dict):
            continue
        if (
            component.get("compensationType") != "Salary"
            or component.get("interval") != "1 YEAR"
        ):
            continue
        currency = str(component.get("currencyCode", "")).upper()
        minimum = component.get("minValue")
        maximum = component.get("maxValue")
        if (
            currency not in {"JPY", "USD"}
            or not isinstance(minimum, (int, float))
            or minimum <= 0
        ):
            continue
        return {
            "type": "annual_salary",
            "currency": currency,
            "min": int(minimum),
            "max": (
                int(maximum)
                if isinstance(maximum, (int, float)) and maximum > 0
                else None
            ),
            "source": "official_ashby",
        }
    return None


def _ashby_secondary_locations(value: dict[str, Any]) -> list[str]:
    locations = value.get("secondaryLocations")
    if not isinstance(locations, list):
        return []
    return [
        str(item.get("location", "")).strip()
        for item in locations
        if isinstance(item, dict) and str(item.get("location", "")).strip()
    ]


def _normalize(board: dict[str, str], payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError("unexpected official ATS board response")
    rows: list[dict[str, Any]] = []
    for value in payload["jobs"]:
        if not isinstance(value, dict):
            continue
        if board["ats"] == "ashby":
            if value.get("isListed") is False:
                continue
            title = str(value.get("title", "")).strip()
            url = str(value.get("jobUrl", "")).strip()
            location = str(value.get("location", "")).strip()
            posted = _posted_at_ms(value.get("publishedAt"))
            description = value.get("descriptionPlain") or value.get("description")
            compensation = _ashby_annual_salary(value)
            secondary_locations = _ashby_secondary_locations(value)
        else:
            title = str(value.get("title", "")).strip()
            url = str(value.get("absolute_url", "")).strip()
            location_value = value.get("location")
            location = (
                str(location_value.get("name", "")).strip()
                if isinstance(location_value, dict)
                else ""
            )
            posted = _posted_at_ms(value.get("first_published"))
            description = value.get("content")
            compensation = None
            secondary_locations = []
        try:
            parsed = urlsplit(url)
        except ValueError:
            continue
        if not title or parsed.scheme != "https" or not parsed.hostname:
            continue
        row: dict[str, Any] = {
            "title": title,
            "url": url,
            "company": board["company"],
            "location": location,
            "source_kind": "official",
            "ats": board["ats"],
        }
        if posted is not None:
            row["posted_at_ms"] = posted
        if isinstance(description, str) and description.strip():
            row["description"] = description[:1_000]
        if compensation is not None:
            row["compensation"] = compensation
        if board["ats"] == "ashby":
            row["is_remote"] = value.get("isRemote") is True
            workplace_type = str(value.get("workplaceType", "")).strip()
            if workplace_type:
                row["workplace_type"] = workplace_type
            if secondary_locations:
                row["secondary_locations"] = secondary_locations
        rows.append(row)
    return rows


def _load_cache(path: Path, ttl_seconds: int) -> list[dict[str, Any]] | None:
    try:
        if time.time() - path.stat().st_mtime > ttl_seconds:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    rows = payload.get("jobs") if isinstance(payload, dict) else None
    return rows if isinstance(rows, list) else None


def _write_cache(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps({"version": 1, "jobs": rows}, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _fetch_all(
    boards: Iterable[dict[str, str]], request
) -> list[dict[str, Any]]:
    boards = list(boards)
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(boards)))) as executor:
        futures = {
            executor.submit(
                request,
                _api_url(board),
                timeout_seconds=30.0 if board["ats"] == "ashby" else 12.0,
                follow_redirects=False,
            ): board
            for board in boards
        }
        for future in as_completed(futures):
            board = futures[future]
            try:
                rows.extend(_normalize(board, future.result()))
            except Exception:
                continue
    return rows


def search_official_boards(
    query: str,
    *,
    boards: Iterable[dict[str, str]],
    request=_request_json,
    cache_path: Path | None = None,
    cache_ttl_seconds: int = 900,
    max_results: int = 25,
    write_cache: bool = True,
) -> list[dict[str, Any]]:
    if max_results <= 0:
        raise ValueError("max_results must be positive")
    rows = _load_cache(cache_path, cache_ttl_seconds) if cache_path else None
    if rows is None:
        rows = _fetch_all(boards, request)
        if cache_path is not None and write_cache:
            _write_cache(cache_path, rows)
    terms = tuple(
        token.casefold()
        for token in TOKEN_RE.findall(query)
        if token.casefold() not in STOPWORDS
    )
    ranked = []
    for row in rows:
        title = str(row.get("title", "")).casefold()
        location = str(row.get("location", "")).casefold()
        description = str(row.get("description", "")).casefold()
        score = sum(
            (3 if term in title else 0)
            + (2 if term in location else 0)
            + (1 if term in description else 0)
            for term in terms
        )
        if terms and score == 0:
            continue
        ranked.append((score, int(row.get("posted_at_ms", 0)), row))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    results = []
    for _, _, row in ranked[:max_results]:
        compact = dict(row)
        description = compact.get("description")
        if isinstance(description, str):
            compact["description"] = description[:500]
        results.append(compact)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?")
    parser.add_argument("--boards", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--refresh-only", action="store_true")
    args = parser.parse_args()
    app_root = Path(__file__).resolve().parents[1]
    boards_path = args.boards or app_root / "config" / "official-ats-boards.v1.json"
    state_root = Path(
        os.environ.get(
            "JOB_SEARCH_STATE_ROOT",
            Path.home() / ".local/state/anicca/job-search",
        )
    )
    cache_path = args.cache or state_root / "official-ats-board-cache.v1.json"
    payload = json.loads(boards_path.read_text(encoding="utf-8"))
    boards = payload.get("boards")
    if not isinstance(boards, list):
        raise ValueError("official ATS boards config requires boards")
    if args.refresh_only:
        rows = _fetch_all(boards, _request_json)
        if not rows:
            raise ValueError("official ATS refresh returned zero jobs")
        _write_cache(cache_path, rows)
        print(json.dumps({"status": "refreshed", "job_count": len(rows)}, sort_keys=True))
        return
    if not args.query:
        parser.error("query is required unless --refresh-only is used")
    print(
        json.dumps(
            {
                "results": search_official_boards(
                    args.query,
                    boards=boards,
                    cache_path=cache_path,
                    write_cache=False,
                )
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
