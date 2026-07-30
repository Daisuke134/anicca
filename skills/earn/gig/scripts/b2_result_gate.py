#!/usr/bin/env python3
"""Freeze B2 policy inputs and verify that an apply step actually completed.

The model chooses feasibility and writes proposals.  Code owns the measurable
boundaries: current strategy thresholds, prior application identities, result
cardinality, fresh marketplace evidence, fresh submit proof, and the durable ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit


class ContractError(ValueError):
    """The frozen policy input is absent or malformed."""


_RETAINER_ULID = re.compile(r"[0-9A-HJKMNP-TV-Z]{26}")


def _valid_request_id(value: Any) -> bool:
    request_id = str(value or "").strip()
    return bool(re.fullmatch(r"\d+", request_id) or _RETAINER_ULID.fullmatch(request_id))


def _request_id_sort_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.isdigit() else (1, value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise ContractError(f"{label}_invalid")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{label}_invalid") from exc
    if number < minimum:
        raise ContractError(f"{label}_invalid")
    return number


def _applied_ids(path: Path) -> list[str]:
    found: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise ContractError("applied_ledger_unreadable") from exc
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or "action" in row:
            continue
        if row.get("recorded_by") in {
            "application_report_proof_recovery",
            "application_report_intent_recovery",
        } and not (
            row.get("submit_verified") is True
            and row.get("applied_page_verified") is True
        ):
            # A file named "*-submitted.png" is not itself proof of submission.
            # Production pass 1785261605 reached only the final modal, saved that
            # filename, and proof recovery otherwise blacklisted the still-open job.
            continue
        request_id = str(row.get("requestId") or row.get("request_id") or "").strip()
        if _valid_request_id(request_id):
            found.add(request_id)
    return sorted(found, key=_request_id_sort_key)


def build_context(prep: dict[str, Any], applied_path: Path) -> dict[str, Any]:
    if not isinstance(prep, dict):
        raise ContractError("prep_invalid")
    thresholds = prep.get("apply_skip_thresholds")
    if not isinstance(thresholds, dict):
        raise ContractError("apply_skip_thresholds_missing")
    categories = [
        str(value).strip()
        for value in (prep.get("category_order") or [])
        if str(value).strip()
    ]
    return {
        "version": 6,
        "target_applications": 4,
        "target_retainer_applications": 1,
        "max_applications": min(
            7, max(4, _integer(prep.get("max_apply_per_pass"), "max_apply_per_pass", minimum=1))
        ),
        "min_budget_jpy": _integer(
            thresholds.get("min_budget_jpy"), "min_budget_jpy", minimum=0
        ),
        "fulfillment_capabilities": {
            "asynchronous_text": True,
            "scheduled_recurring_text": True,
            "durable_follow_up_queue": True,
            "authorized_owner_profile_facts": True,
            "external_account_operations": True,
            "synchronous_voice_video_or_live_presence": False,
            "human_voice_recording": False,
            "physical_presence": False,
        },
        "active_strategy_experiment": (
            prep.get("active_strategy_experiment")
            if isinstance(prep.get("active_strategy_experiment"), dict)
            else None
        ),
        "already_applied_request_ids": _applied_ids(applied_path),
        "required_search_source_ids": [
            "single:new",
            *(f"single:category:{category}" for category in categories),
            "single:keyword",
            "retainer:new",
        ],
    }


def _read_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label}_unreadable") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{label}_invalid")
    return value


def _owned_fresh_file(
    value: Any, root: Path, min_mtime: float
) -> tuple[Path | None, str | None]:
    try:
        path = Path(str(value or "")).resolve()
        path.relative_to(root.resolve())
    except (OSError, ValueError):
        return None, "not_owned"
    try:
        stat = path.stat()
        if not path.is_file() or stat.st_size == 0:
            return None, "missing"
        if stat.st_mtime < min_mtime:
            return None, "stale"
    except OSError:
        return None, "missing"
    return path, None


def _spot_search_url(parsed: Any) -> bool:
    """Accept only Coconala's current newest-single route and its page cursor."""
    if parsed.path != "/job_matching/supplier/new":
        return False
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    if any(key not in {"type", "page"} for key, _ in pairs):
        return False
    type_values = [raw for key, raw in pairs if key == "type"]
    page_values = [raw for key, raw in pairs if key == "page"]
    return (
        type_values == ["spot"]
        and len(page_values) <= 1
        and (
            not page_values
            or re.fullmatch(r"\d+", page_values[0]) is not None
            and int(page_values[0]) >= 1
        )
    )


def _marketplace_url(value: Any) -> bool:
    parsed = urlsplit(str(value or ""))
    if (
        parsed.scheme == "https"
        and parsed.hostname in {"coconala.com", "www.coconala.com"}
        and _spot_search_url(parsed)
    ):
        return True
    return (
        parsed.scheme == "https"
        and parsed.hostname in {"coconala.com", "www.coconala.com"}
        and (
            parsed.path in {
                "/requests",
                "/job_matching/requests",
                "/job_matching/outsources",
            }
            or re.fullmatch(r"/requests/categories/\d+", parsed.path) is not None
        )
        and (
            parsed.path == "/job_matching/outsources"
            or
            not parsed.query
            or parse_qs(parsed.query, keep_blank_values=True).get("sort") == ["new"]
        )
    )


def _request_url(value: Any, request_id: str, bucket: str) -> bool:
    parsed = urlsplit(str(value or ""))
    expected_paths = (
        {
            f"/requests/{request_id}",
            f"/job_matching/requests/{request_id}",
        }
        if bucket == "single"
        else {f"/job_matching/outsources/{request_id}"}
    )
    return (
        parsed.scheme == "https"
        and parsed.hostname in {"coconala.com", "www.coconala.com"}
        and parsed.path in expected_paths
    )


def _search_url(value: Any) -> bool:
    parsed = urlsplit(str(value or ""))
    return (
        parsed.scheme == "https"
        and parsed.hostname in {"coconala.com", "www.coconala.com"}
        and (
            parsed.path in {"/requests", "/job_matching/requests"}
            or parsed.path == "/job_matching/outsources"
            or re.fullmatch(r"/requests/categories/\d+", parsed.path) is not None
            or _spot_search_url(parsed)
        )
    )


def _next_page_url(value: Any) -> str:
    url = str(value or "")
    if not _search_url(url):
        raise ContractError("continuation_source_url_invalid")
    parsed = urlsplit(url)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    page_index: int | None = None
    current_page = 1
    for index, (key, raw) in enumerate(pairs):
        if key != "page":
            continue
        if page_index is not None or not re.fullmatch(r"\d+", raw) or int(raw) < 1:
            raise ContractError("continuation_page_invalid")
        page_index = index
        current_page = int(raw)
    next_pair = ("page", str(current_page + 1))
    if page_index is None:
        pairs.append(next_pair)
    else:
        pairs[page_index] = next_pair
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(pairs), parsed.fragment)
    )


def _search_page_number(value: Any) -> int:
    """Return the validated one-based page number for a search URL."""
    url = str(value or "")
    if not _search_url(url):
        raise ContractError("continuation_source_url_invalid")
    page = 1
    page_seen = False
    for key, raw in parse_qsl(urlsplit(url).query, keep_blank_values=True):
        if key != "page":
            continue
        if page_seen or not re.fullmatch(r"\d+", raw) or int(raw) < 1:
            raise ContractError("continuation_page_invalid")
        page_seen = True
        page = int(raw)
    return page


def _search_url_advances(previous: Any, current: Any) -> bool:
    """Return true when one source's current URL is on a later result page."""
    if not _search_url(previous) or not _search_url(current):
        return False

    def position(value: Any) -> tuple[tuple[Any, ...], int] | None:
        parsed = urlsplit(str(value or ""))
        page = 1
        page_seen = False
        stable_pairs: list[tuple[str, str]] = []
        for key, raw in parse_qsl(parsed.query, keep_blank_values=True):
            if key != "page":
                stable_pairs.append((key, raw))
                continue
            if page_seen or not re.fullmatch(r"\d+", raw) or int(raw) < 1:
                return None
            page_seen = True
            page = int(raw)
        return (
            (
                parsed.scheme,
                parsed.hostname,
                parsed.path,
                tuple(sorted(stable_pairs)),
                parsed.fragment,
            ),
            page,
        )

    previous_position = position(previous)
    current_position = position(current)
    return (
        previous_position is not None
        and current_position is not None
        and previous_position[0] == current_position[0]
        and current_position[1] > previous_position[1]
    )


def next_search_cursor(summary_path: Path, context_path: Path) -> dict[str, Any]:
    summary = _read_object(summary_path, "b2_runner_summary")
    if summary.get("status") != "success" or summary.get("task_label") != "gig-B2":
        raise ContractError("b2_runner_summary_not_success")
    result_path = Path(str(summary.get("result_path") or ""))
    result = _read_object(result_path, "b2_result")
    current = result.get("current_b2")
    if not isinstance(current, dict):
        raise ContractError("current_b2_missing")
    sources = current.get("search_sources")
    if not isinstance(sources, list) or not all(isinstance(row, dict) for row in sources):
        raise ContractError("search_sources_malformed")
    inspected = current.get("inspected_requests")
    if not isinstance(inspected, list) or not all(isinstance(row, dict) for row in inspected):
        raise ContractError("inspected_requests_malformed")
    prior_ids = sorted(
        {
            str(row.get("request_id") or "").strip()
            for row in inspected
            if _valid_request_id(row.get("request_id"))
        },
        key=_request_id_sort_key,
    )

    def cursor(**values: Any) -> dict[str, Any]:
        if prior_ids:
            values["prior_inspected_request_ids"] = prior_ids
        return values
    by_id = {
        str(row.get("source_id") or ""): row
        for row in sources
        if str(row.get("source_id") or "")
    }
    context = _read_object(context_path, "b2_context")
    required = [
        str(value)
        for value in context.get("required_search_source_ids", [])
        if str(value)
    ]
    raw_applications = result.get("applications")
    applications = raw_applications if isinstance(raw_applications, list) else []
    application_ids = {
        str(row.get("request_id") or "").strip()
        for row in applications
        if isinstance(row, dict)
        and _valid_request_id(row.get("request_id"))
    }
    target = _integer(
        context.get("target_applications"),
        "target_applications",
        minimum=1,
    )
    target_retainer = _integer(
        context.get("target_retainer_applications"),
        "target_retainer_applications",
        minimum=0,
    )
    verified_retainer_count = sum(
        1 for request_id in application_ids if not request_id.isdigit()
    )
    if (
        len(application_ids) >= target
        and verified_retainer_count < target_retainer
        and "retainer:new" in required
    ):
        source = by_id.get("retainer:new")
        if source is None:
            return cursor(
                source_id="retainer:new",
                previous_url="",
                next_url="https://coconala.com/job_matching/outsources",
                reason="inspect_missing_source",
            )
        source_url = str(source.get("url") or "")
        if source.get("has_next") is True:
            return cursor(
                source_id="retainer:new",
                previous_url=source_url,
                next_url=_next_page_url(source_url),
                reason="next_page",
            )
        if source.get("inspected_count") == 0 and _search_url(source_url):
            return cursor(
                source_id="retainer:new",
                previous_url=source_url,
                next_url=source_url,
                reason="inspect_current_page",
            )
    if "single:new" in required and "single:new" not in by_id:
        return cursor(
            source_id="single:new",
            previous_url="",
            next_url="https://coconala.com/requests?sort=new",
            reason="inspect_missing_source",
        )
    single_candidates: list[tuple[int, int, dict[str, Any]]] = []
    retainer_candidates: list[tuple[int, int, dict[str, Any]]] = []
    for required_index, source_id in enumerate(required):
        source = by_id.get(source_id)
        if source is None:
            continue
        source_url = str(source.get("url") or "")
        candidate: dict[str, Any] | None = None
        coverage_page = _search_page_number(source_url)
        if source.get("inspected_count") == 0:
            candidate = cursor(
                source_id=source_id,
                previous_url=source_url,
                next_url=source_url,
                reason="inspect_current_page",
            )
            coverage_page = 0
        elif source.get("has_next") is True:
            candidate = cursor(
                source_id=source_id,
                previous_url=source_url,
                next_url=_next_page_url(source_url),
                reason="next_page",
            )
        if candidate is None:
            continue
        ranked = (coverage_page, required_index, candidate)
        if source_id == "retainer:new":
            retainer_candidates.append(ranked)
        else:
            single_candidates.append(ranked)
    if single_candidates:
        return min(single_candidates, key=lambda row: row[:2])[2]
    if retainer_candidates:
        return min(retainer_candidates, key=lambda row: row[:2])[2]
    raise ContractError("continuation_cursor_unavailable")


def continuation_state(
    gate_result_path: Path,
    ledger_path: Path,
    context_path: Path,
    pass_id: str,
) -> tuple[bool, int, int]:
    try:
        gate_lines = gate_result_path.read_text(encoding="utf-8").splitlines()
        gate = json.loads(gate_lines[-1])
    except (OSError, IndexError, json.JSONDecodeError) as exc:
        raise ContractError("gate_result_unreadable") from exc
    errors = gate.get("errors") if isinstance(gate, dict) else None
    if not isinstance(errors, list) or not all(isinstance(error, str) for error in errors):
        raise ContractError("gate_errors_invalid")
    under_target = "under_target_search_not_exhausted"
    recoverable_volume = under_target in errors and all(
        error == under_target
        or error in {
            "marketplace_url_invalid",
            "marketplace_live_dom_url_mismatch",
        }
        or error.startswith("application_count_mismatch:")
        or error.startswith("under_target_inspection_quantity_too_low:")
        or error.startswith("search_source_")
        or error.startswith("search_sources_")
        or error.startswith("continuation_cursor_")
        or error.startswith("eligible_already_applied:")
        or error.startswith("inspected_request_duplicate:")
        for error in errors
    )
    context = _read_object(context_path, "context")
    target = _integer(
        context.get("target_applications"),
        "target_applications",
        minimum=1,
    )
    target_retainer = _integer(
        context.get("target_retainer_applications"),
        "target_retainer_applications",
        minimum=0,
    )
    verified: set[str] = set()
    verified_retainers: set[str] = set()
    try:
        ledger_lines = ledger_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        ledger_lines = []
    except OSError as exc:
        raise ContractError("application_ledger_unreadable") from exc
    for raw in ledger_lines:
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        request_id = str(row.get("requestId") or row.get("request_id") or "")
        if (
            str(row.get("pass_id") or "") == pass_id
            and _valid_request_id(request_id)
            and row.get("submit_verified") is True
            and row.get("applied_page_verified") is True
        ):
            verified.add(request_id)
            if not request_id.isdigit():
                verified_retainers.add(request_id)
    retainer_recoverable_errors = {
        "retainer_application_missing",
        "retainer_search_not_exhausted",
    }
    recoverable_retainer = (
        len(verified) >= target
        and len(verified_retainers) < target_retainer
        and any(error in retainer_recoverable_errors for error in errors)
        and all(
            error in retainer_recoverable_errors
            or error.startswith("search_source_")
            or error.startswith("search_sources_")
            or error.startswith("continuation_cursor_")
            for error in errors
        )
    )
    allowed = (
        recoverable_volume and len(verified) < target
    ) or recoverable_retainer
    return allowed, len(verified), target


def _ledger_ids(path: Path) -> set[str]:
    return set(_applied_ids(path))


def _ledger_rows(path: Path) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return found
    for raw in lines:
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict) or "action" in row:
            continue
        request_id = str(row.get("requestId") or row.get("request_id") or "")
        if _valid_request_id(request_id):
            found[request_id] = row
    return found


def _has_fresh_submit_proof(root: Path, request_id: str, min_mtime: float) -> bool:
    try:
        candidates = root.glob(f"gig-*-B2-{request_id}-submitted.png")
        for path in candidates:
            try:
                stat = path.stat()
            except OSError:
                continue
            if path.is_file() and stat.st_size > 0 and stat.st_mtime >= min_mtime:
                return True
    except OSError:
        return False
    return False


def _fresh_submit_ids(root: Path, min_mtime: float) -> set[str]:
    found: set[str] = set()
    try:
        for path in root.glob("gig-*-B2-*-submitted.png"):
            match = re.fullmatch(
                r"gig-.*-B2-([0-9A-Z]+)-submitted\.png",
                path.name,
            )
            if not match:
                continue
            if not _valid_request_id(match.group(1)):
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            if path.is_file() and stat.st_size > 0 and stat.st_mtime >= min_mtime:
                found.add(match.group(1))
    except OSError:
        return found
    return found


def _fresh_submit_intent_ids(root: Path, min_mtime: float) -> set[str]:
    found: set[str] = set()
    try:
        for path in root.rglob("gig-*-B2-*-submitted.intent.json"):
            match = re.fullmatch(
                r"gig-.*-B2-([0-9A-Z]+)-submitted\.intent\.json",
                path.name,
            )
            if not match or not _valid_request_id(match.group(1)):
                continue
            try:
                stat = path.stat()
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            request_id = match.group(1)
            if (
                path.is_file()
                and stat.st_size > 0
                and stat.st_mtime >= min_mtime
                and isinstance(payload, dict)
                and str(payload.get("request_id") or "") == request_id
                and payload.get("state") in {"prepared", "confirmed"}
            ):
                found.add(request_id)
    except OSError:
        return found
    return found


def validate_result(
    *,
    context_path: Path,
    summary_path: Path,
    evidence_dir: Path,
    evidence_root: Path,
    ledger_path: Path,
    min_mtime: float,
    pass_id: str | None = None,
    cursor_contract_path: Path | None = None,
    cursor_min_mtime: float | None = None,
    min_new_inspections: int = 0,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        context = _read_object(context_path, "b2_context")
    except ContractError as exc:
        return False, [str(exc)]
    try:
        summary = _read_object(summary_path, "b2_runner_summary")
    except ContractError as exc:
        return False, [str(exc)]
    if summary.get("status") != "success" or summary.get("task_label") != "gig-B2":
        return False, ["b2_runner_summary_not_success"]
    result_path, result_error = _owned_fresh_file(
        summary.get("result_path"), evidence_dir, min_mtime
    )
    if result_error:
        return False, [f"b2_result_{result_error}"]
    try:
        result = _read_object(result_path, "b2_result")  # type: ignore[arg-type]
    except ContractError as exc:
        return False, [str(exc)]
    if result.get("status") != "ok":
        return False, ["b2_result_invalid"]
    current = result.get("current_b2")
    if not isinstance(current, dict):
        return False, ["current_b2_missing"]

    try:
        bound_context = Path(str(current.get("context_path") or "")).resolve()
        if bound_context != context_path.resolve():
            errors.append("context_path_mismatch")
        if current.get("context_sha256") != sha256_file(context_path):
            errors.append("context_sha256_mismatch")
    except OSError:
        errors.append("context_binding_unreadable")

    marketplace_url = current.get("marketplace_url")
    if not _marketplace_url(marketplace_url):
        errors.append("marketplace_url_invalid")
    _, shot_error = _owned_fresh_file(
        current.get("marketplace_screenshot_path"), evidence_dir, min_mtime
    )
    if shot_error:
        errors.append(f"marketplace_screenshot_{shot_error}")
    dom_path, dom_error = _owned_fresh_file(
        current.get("marketplace_live_dom_path"), evidence_dir, min_mtime
    )
    if dom_error:
        errors.append(f"marketplace_live_dom_{dom_error}")
    if dom_path is not None:
        try:
            dom = _read_object(dom_path, "marketplace_live_dom")
        except ContractError:
            errors.append("marketplace_live_dom_invalid_json")
        else:
            if dom.get("observed") is not True:
                errors.append("marketplace_not_observed")
            if dom.get("not_found") is True:
                errors.append("marketplace_not_found")
            if dom.get("url") != marketplace_url or not _marketplace_url(dom.get("url")):
                errors.append("marketplace_live_dom_url_mismatch")

    inspected = current.get("inspected_requests")
    if not isinstance(inspected, list) or not all(
        isinstance(row, dict) for row in inspected
    ):
        return False, errors + ["inspected_requests_malformed"]

    min_budget = context.get("min_budget_jpy")
    target_applications = context.get("target_applications")
    target_retainer_applications = context.get("target_retainer_applications")
    max_applications = context.get("max_applications")
    if not all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in (
            min_budget,
            target_applications,
            target_retainer_applications,
            max_applications,
        )
    ):
        return False, errors + ["b2_context_thresholds_invalid"]
    already_applied = {
        str(value)
        for value in context.get("already_applied_request_ids", [])
        if str(value)
    }
    ledger_rows = _ledger_rows(ledger_path)
    fresh_submit_intent_ids = _fresh_submit_intent_ids(
        evidence_root,
        min_mtime,
    )
    same_pass_verified_ids = {
        request_id
        for request_id, row in ledger_rows.items()
        if pass_id
        and str(row.get("pass_id") or "") == pass_id
        and row.get("submit_verified") is True
        and row.get("applied_page_verified") is True
    }
    carried_application_ids = same_pass_verified_ids & already_applied

    seen: dict[str, dict[str, Any]] = {}
    eligible_ids: list[str] = []
    deduped_eligible_ids: list[str] = []
    for row in inspected:
        request_id = str(row.get("request_id") or "").strip()
        if not _valid_request_id(request_id):
            errors.append("request_id_invalid")
            continue
        if request_id in seen:
            errors.append(f"inspected_request_duplicate:{request_id}")
            first = seen[request_id]
            if any(
                first.get(field) != row.get(field)
                for field in ("bucket", "url", "outcome")
            ):
                errors.append(f"inspected_request_conflict:{request_id}")
            continue
        seen[request_id] = row
        bucket = row.get("bucket")
        if bucket not in {"single", "retainer"}:
            errors.append(f"request_bucket_invalid:{request_id}")
            continue
        expected_bucket = "single" if request_id.isdigit() else "retainer"
        if bucket != expected_bucket:
            errors.append(f"request_bucket_identity_mismatch:{request_id}")
        if not _request_url(row.get("url"), request_id, bucket):
            errors.append(f"request_url_invalid:{request_id}")
        outcome = row.get("outcome")
        if outcome not in {"eligible", "ineligible"}:
            errors.append(f"request_outcome_invalid:{request_id}")
            continue
        if outcome != "eligible":
            continue
        if request_id in already_applied and request_id not in carried_application_ids:
            errors.append(f"eligible_already_applied:{request_id}")
            deduped_eligible_ids.append(request_id)
            # The frozen ledger is authoritative.  Preserve the diagnostic but
            # remove this model classification from the new-submit cardinality so
            # a safe dedupe does not demand or trigger a duplicate application.
            continue
        eligible_ids.append(request_id)
        if row.get("accepting_applications") is not True:
            errors.append(f"eligible_marketplace_closed:{request_id}")
        budget_max = row.get("budget_max_jpy")
        if (
            bucket == "single"
            and isinstance(budget_max, (int, float))
            and not isinstance(budget_max, bool)
            and budget_max < min_budget
        ):
            errors.append(f"eligible_budget_below_minimum:{request_id}")

    eligible_count = result.get("eligible_count")
    new_eligible_ids = [
        request_id
        for request_id in eligible_ids
        if request_id not in carried_application_ids
    ]
    cumulative_observed_eligible_ids = set(eligible_ids) | carried_application_ids
    if eligible_count is None:
        # OpenAI strict output requires this key but permits null.  The count is
        # redundant: inspected_requests is the code-verifiable source of truth.
        # Derive it instead of converting a healthy under-target pagination result
        # into a non-retryable failure (production pass 1785290401).
        eligible_count = len(eligible_ids)
    elif not isinstance(eligible_count, int) or isinstance(eligible_count, bool):
        errors.append("eligible_count_unavailable")
        eligible_count = 0
    elif eligible_count not in {
        len(eligible_ids),
        len(new_eligible_ids),
        len(cumulative_observed_eligible_ids),
        len(eligible_ids) + len(deduped_eligible_ids),
    }:
        errors.append(
            "eligible_count_mismatch:"
            f"reported={eligible_count}:"
            f"observed_cumulative={len(eligible_ids)}:"
            f"observed_new={len(new_eligible_ids)}"
        )

    raw_applications = result.get("applications")
    applications = [] if raw_applications is None else raw_applications
    if not isinstance(applications, list) or not all(
        isinstance(row, dict) for row in applications
    ):
        return False, errors + ["applications_malformed"]

    application_ids: list[str] = []
    application_buckets: dict[str, str] = {}
    for row in applications:
        request_id = str(row.get("request_id") or "").strip()
        application_ids.append(request_id)
        bucket = str(row.get("bucket") or "")
        application_buckets[request_id] = bucket
        if bucket not in {"single", "retainer"}:
            errors.append(f"application_bucket_invalid:{request_id or 'missing'}")
        elif bucket != ("single" if request_id.isdigit() else "retainer"):
            errors.append(
                f"application_bucket_identity_mismatch:{request_id or 'missing'}"
            )
        if (
            request_id not in eligible_ids
            and request_id not in carried_application_ids
        ):
            errors.append(f"application_not_eligible:{request_id or 'missing'}")
        if not _request_url(row.get("url"), request_id, bucket):
            errors.append(f"application_url_invalid:{request_id or 'missing'}")
    if len(application_ids) != len(set(application_ids)):
        errors.append("application_request_duplicate")

    new_application_ids = [
        request_id
        for request_id in application_ids
        if request_id not in carried_application_ids
    ]
    remaining_capacity = max(
        0,
        max_applications - len(carried_application_ids),
    )
    expected_applications = min(len(new_eligible_ids), remaining_capacity)
    recovered_new_application_ids = (
        same_pass_verified_ids
        & set(new_eligible_ids)
        & fresh_submit_intent_ids
    )
    effective_new_application_ids = set(new_application_ids)
    effective_new_application_ids.update(recovered_new_application_ids)
    if len(effective_new_application_ids) != expected_applications:
        errors.append(
            "application_count_mismatch:"
            f"expected={expected_applications}:actual={len(effective_new_application_ids)}"
        )

    cumulative_application_ids = set(application_ids)
    cumulative_application_ids.update(same_pass_verified_ids)
    cumulative_retainer_ids = {
        request_id
        for request_id in cumulative_application_ids
        if not request_id.isdigit()
    }

    search_sources = current.get("search_sources")
    if not isinstance(search_sources, list) or not all(
        isinstance(row, dict) for row in search_sources
    ):
        search_sources = []
        errors.append("search_sources_malformed")
    source_ids: set[str] = set()
    source_urls: set[str] = set()
    source_rows: dict[str, dict[str, Any]] = {}
    for source in search_sources:
        source_id = str(source.get("source_id") or "")
        prior_source = source_rows.get(source_id)
        if not source_id:
            errors.append(f"search_source_duplicate:{source_id or 'missing'}")
            continue
        if prior_source is not None and not _search_url_advances(
            prior_source.get("url"), source.get("url")
        ):
            errors.append(f"search_source_duplicate:{source_id}")
            continue
        source_ids.add(source_id)
        source_rows[source_id] = source
        source_url = source.get("url")
        if not _search_url(source_url):
            errors.append(f"search_source_url_invalid:{source_id}")
        normalized_source_url = str(source_url or "")
        if normalized_source_url in source_urls:
            if "search_source_url_duplicate" not in errors:
                errors.append("search_source_url_duplicate")
        else:
            source_urls.add(normalized_source_url)
        _, source_shot_error = _owned_fresh_file(
            source.get("screenshot_path"), evidence_dir, min_mtime
        )
        if source_shot_error:
            errors.append(f"search_source_screenshot_{source_shot_error}:{source_id}")
        source_dom, source_dom_error = _owned_fresh_file(
            source.get("live_dom_path"), evidence_dir, min_mtime
        )
        if source_dom_error:
            errors.append(f"search_source_live_dom_{source_dom_error}:{source_id}")
        elif source_dom is not None:
            try:
                source_snapshot = _read_object(source_dom, "search_source_live_dom")
            except ContractError:
                errors.append(f"search_source_live_dom_invalid:{source_id}")
            else:
                if (
                    source_snapshot.get("observed") is not True
                    or source_snapshot.get("not_found") is True
                    or source_snapshot.get("url") != source_url
                ):
                    errors.append(f"search_source_not_observed:{source_id}")
        inspected_count = source.get("inspected_count")
        if (
            not isinstance(inspected_count, int)
            or isinstance(inspected_count, bool)
            or inspected_count < 0
        ):
            errors.append(f"search_source_count_invalid:{source_id}")
    all_sources_exhausted = bool(source_rows) and all(
        source.get("exhausted") is True and source.get("has_next") is False
        for source in source_rows.values()
    )

    prior_inspected_request_ids: set[str] = set()
    if cursor_contract_path is not None:
        try:
            cursor_contract = _read_object(
                cursor_contract_path, "continuation_cursor_contract"
            )
        except ContractError as exc:
            errors.append(str(exc))
        else:
            cursor_source_id = str(cursor_contract.get("source_id") or "")
            cursor_next_url = str(cursor_contract.get("next_url") or "")
            raw_prior_ids = cursor_contract.get("prior_inspected_request_ids") or []
            if not isinstance(raw_prior_ids, list) or not all(
                _valid_request_id(value) for value in raw_prior_ids
            ):
                errors.append("continuation_prior_inspected_ids_invalid")
            else:
                prior_inspected_request_ids = {str(value) for value in raw_prior_ids}
            if not cursor_source_id or not _search_url(cursor_next_url):
                errors.append("continuation_cursor_contract_invalid")
            elif (
                cursor_source_id not in source_rows
                or str(source_rows[cursor_source_id].get("url") or "")
                != cursor_next_url
            ):
                errors.append(
                    f"continuation_cursor_not_advanced:{cursor_source_id}"
                )
            elif cursor_min_mtime is None:
                errors.append("continuation_cursor_min_mtime_missing")
            else:
                cursor_source = source_rows[cursor_source_id]
                _, cursor_shot_error = _owned_fresh_file(
                    cursor_source.get("screenshot_path"),
                    evidence_dir,
                    cursor_min_mtime,
                )
                if cursor_shot_error:
                    errors.append(
                        "continuation_cursor_screenshot_"
                        f"{cursor_shot_error}:{cursor_source_id}"
                    )
                _, cursor_dom_error = _owned_fresh_file(
                    cursor_source.get("live_dom_path"),
                    evidence_dir,
                    cursor_min_mtime,
                )
                if cursor_dom_error:
                    errors.append(
                        "continuation_cursor_live_dom_"
                        f"{cursor_dom_error}:{cursor_source_id}"
                    )

    required_source_ids = {
        str(value)
        for value in context.get("required_search_source_ids", [])
        if str(value)
    }
    retainer_source = source_rows.get("retainer:new")
    eligible_retainer_ids = {
        request_id
        for request_id in eligible_ids
        if not request_id.isdigit()
    }
    if len(cumulative_application_ids) < target_applications:
        if source_ids != required_source_ids or not all_sources_exhausted:
            new_inspected_count = len(set(seen) - prior_inspected_request_ids)
            if (
                min_new_inspections > 0
                and new_inspected_count < min_new_inspections
            ):
                errors.append(
                    "under_target_inspection_quantity_too_low:"
                    f"actual={new_inspected_count}:minimum={min_new_inspections}"
                )
            errors.append("under_target_search_not_exhausted")
    elif "single:new" not in source_ids:
        errors.append("newest_search_evidence_missing")
    if len(cumulative_application_ids) >= target_applications:
        if "retainer:new" not in source_ids:
            errors.append("retainer_search_evidence_missing")
        elif len(cumulative_retainer_ids) < target_retainer_applications:
            if eligible_retainer_ids:
                errors.append("retainer_application_missing")
            elif (
                retainer_source is None
                or retainer_source.get("exhausted") is not True
                or retainer_source.get("has_next") is not False
            ):
                errors.append("retainer_search_not_exhausted")

    for request_id in sorted(
        (
            _fresh_submit_ids(evidence_root, min_mtime)
            | fresh_submit_intent_ids
        )
        - cumulative_application_ids
    ):
        errors.append(f"unreported_submit_evidence:{request_id}")
    readback_path = evidence_dir / "code-applied-readback.json"
    readback_ids: set[str] = set()
    readback_paths: set[str] = set()
    if cumulative_application_ids:
        owned_readback, readback_error = _owned_fresh_file(
            readback_path, evidence_dir, min_mtime
        )
        if readback_error:
            owned_readback = None
        if owned_readback is not None:
            try:
                readback = _read_object(owned_readback, "applied_page_readback")
            except ContractError:
                readback = {}
            if (
                readback.get("source") == "code_owned_cdp_readback"
                and readback.get("observed") is True
                and readback.get("not_found") is False
            ):
                readback_paths = {
                    urlsplit(str(value)).path.rstrip("/")
                    for value in (
                        readback.get("urls")
                        or [readback.get("url")]
                    )
                }
                allowed_readback_paths = {
                    "/mypage/job_matching/applied/offers",
                    "/mypage/job_matching/applied/outsource_applications",
                }
                if not readback_paths or not readback_paths.issubset(
                    allowed_readback_paths
                ):
                    readback_paths = set()
                readback_ids = {
                    str(value)
                    for value in (readback.get("request_ids") or [])
                    if _valid_request_id(value)
                }
    for request_id in sorted(cumulative_application_ids):
        row = ledger_rows.get(request_id)
        canonical_intent_recovery = (
            request_id in fresh_submit_intent_ids
            and row is not None
            and row.get("recorded_by") == "application_report_intent_recovery"
            and row.get("submit_verified") is True
            and row.get("applied_page_verified") is True
        )
        if (
            not _has_fresh_submit_proof(evidence_root, request_id, min_mtime)
            and not canonical_intent_recovery
        ):
            errors.append(f"application_submit_evidence_missing:{request_id}")
        if row is None:
            errors.append(f"application_ledger_missing:{request_id}")
        if request_id not in readback_ids:
            errors.append(f"application_applied_page_readback_missing:{request_id}")
        required_readback_path = (
            "/mypage/job_matching/applied/offers"
            if request_id.isdigit()
            else "/mypage/job_matching/applied/outsource_applications"
        )
        if request_id in readback_ids and required_readback_path not in readback_paths:
            errors.append(
                f"application_applied_page_route_missing:{request_id}"
            )
        if row is not None and (
            row.get("submit_verified") is not True
            or row.get("applied_page_verified") is not True
        ):
            errors.append(f"application_ledger_verification_missing:{request_id}")
    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--prep-json", required=True)
    build.add_argument("--applied", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--context", required=True, type=Path)
    validate.add_argument("--runner-summary", required=True, type=Path)
    validate.add_argument("--evidence-dir", required=True, type=Path)
    validate.add_argument("--evidence-root", required=True, type=Path)
    validate.add_argument("--ledger", required=True, type=Path)
    validate.add_argument("--min-mtime", required=True, type=float)
    validate.add_argument("--pass-id")
    validate.add_argument("--cursor-contract", type=Path)
    validate.add_argument("--cursor-min-mtime", type=float)
    validate.add_argument("--min-new-inspections", type=int, default=0)
    continuable = subparsers.add_parser("continuable")
    continuable.add_argument("--gate-result", required=True, type=Path)
    continuable.add_argument("--ledger", required=True, type=Path)
    continuable.add_argument("--context", required=True, type=Path)
    continuable.add_argument("--pass-id", required=True)
    next_cursor = subparsers.add_parser("next-cursor")
    next_cursor.add_argument("--runner-summary", required=True, type=Path)
    next_cursor.add_argument("--context", required=True, type=Path)
    next_cursor.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "build":
            prep = json.loads(args.prep_json)
            context = build_context(prep, args.applied)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(context, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            print(json.dumps({"ok": True, "output": str(args.output)}, separators=(",", ":")))
            return 0
        if args.command == "continuable":
            allowed, verified_count, target = continuation_state(
                gate_result_path=args.gate_result,
                ledger_path=args.ledger,
                context_path=args.context,
                pass_id=args.pass_id,
            )
            print(
                json.dumps(
                    {
                        "continuable": allowed,
                        "verified_count": verified_count,
                        "target": target,
                    },
                    separators=(",", ":"),
                )
            )
            return 0 if allowed else 1
        if args.command == "next-cursor":
            cursor = next_search_cursor(args.runner_summary, args.context)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(cursor, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            print(
                json.dumps(
                    {"ok": True, "output": str(args.output), **cursor},
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
            return 0
        ok, errors = validate_result(
            context_path=args.context,
            summary_path=args.runner_summary,
            evidence_dir=args.evidence_dir,
            evidence_root=args.evidence_root,
            ledger_path=args.ledger,
            min_mtime=args.min_mtime,
            pass_id=args.pass_id,
            cursor_contract_path=args.cursor_contract,
            cursor_min_mtime=args.cursor_min_mtime,
            min_new_inspections=max(0, args.min_new_inspections),
        )
        print(json.dumps({"ok": ok, "errors": errors}, ensure_ascii=False, separators=(",", ":")))
        return 0 if ok else 1
    except (ContractError, json.JSONDecodeError) as exc:
        print(
            json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, separators=(",", ":")),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
