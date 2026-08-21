"""Deterministic Ashby preflight for the resident job-search browser owner.

This module deliberately handles only fields whose meaning is grounded by a
user-facing label and the private profile.  It never invents answers for an
unlabelled required control, never bypasses CAPTCHA, and never retries a
terminal submission state.  The browser connection belongs to the daily
launchd owner; this process only attaches to its existing CDP endpoint.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from .ats import evaluate_snapshot
from .application_messages import (
    MessageError,
    application_question_kind,
    build_application_question_answer,
)
from .ledger import Ledger
from .resume_routing import select_resume
from .state import canonical_url


CONTROL_SELECTOR = (
    "input, textarea, select, button, a, "
    "[role='combobox'], [role='button'], [role='radio'], [role='checkbox']"
)
FIELD_SELECTOR = (
    "input, textarea, select, [role='combobox'], [role='radio'], [role='checkbox']"
)
EMAIL_RE = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b")
LONG_DIGIT_RE = re.compile(r"\d{7,}")
CONFIRMATION_RE = re.compile(
    r"thank you|thanks for applying|application received|successfully submitted|"
    r"応募情報が送信|応募を受け付け",
    re.IGNORECASE,
)
PROVIDER_LIMIT_RE = re.compile(
    r"application limits|may not apply more than|no more than \d+ times",
    re.IGNORECASE,
)
CAPTCHA_RE = re.compile(
    r"i(?:'|’)m not a robot|verify you are human|captcha challenge|security check",
    re.IGNORECASE,
)
FORM_ERROR_RE = re.compile(
    r"this field is required|answer is required|please enter|invalid email|"
    r"please complete|required field",
    re.IGNORECASE,
)


def _safe_text(value: Any, maximum: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if EMAIL_RE.search(text) or LONG_DIGIT_RE.search(text):
        return "[redacted]"
    return text[:maximum]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def _load_required_field_blockers(path: Path) -> dict[str, dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = value.get("blockers") if isinstance(value, dict) else None
    if not isinstance(rows, dict):
        return {}
    return {
        str(application_id): dict(row)
        for application_id, row in rows.items()
        if isinstance(application_id, str) and isinstance(row, dict)
    }


def _save_required_field_blockers(path: Path, rows: dict[str, dict[str, Any]]) -> None:
    _write_json(path, {"version": 1, "blockers": rows})


async def _snapshot(page: Any) -> dict[str, Any]:
    frames: list[dict[str, Any]] = []
    for frame in page.frames:
        try:
            controls = await frame.locator(CONTROL_SELECTOR).evaluate_all(
                """
                elements => elements.map(element => {
                  const labels = element.labels
                    ? Array.from(element.labels).map(label => (label.innerText || '').trim())
                    : [];
                  return {
                    tag: element.tagName.toLowerCase(),
                    type: element.getAttribute('type'),
                    role: element.getAttribute('role'),
                    label: labels.join(' | '),
                    name: element.getAttribute('name'),
                    text: (element.innerText || '').trim()
                  };
                })
                """
            )
        except Exception:
            controls = []
        frames.append(
            {
                "url": _safe_text(frame.url, 1000),
                "controls": [
                    {
                        key: _safe_text(control.get(key))
                        for key in ("tag", "type", "role", "label", "name", "text")
                    }
                    for control in controls
                    if isinstance(control, dict)
                ],
            }
        )
    return {
        "version": 1,
        "url": page.url,
        "navigation_committed": True,
        "frames": frames,
    }


async def _body_text(page: Any) -> str:
    try:
        await page.wait_for_function(
            "() => document.body && document.body.innerText.length > 0",
            timeout=20_000,
        )
        return await page.locator("body").inner_text(timeout=5_000)
    except Exception:
        return ""


async def _wait_for_surface(page: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    async def ready_control() -> None:
        await page.locator(
            "input[type='email'], input[type='file'], "
            "button:has-text('Apply for this Job'), "
            "button:has-text('Submit Application')"
        ).first.wait_for(timeout=20_000)

    try:
        await ready_control()
    except PlaywrightTimeoutError:
        pass
    snapshot = await _snapshot(page)
    evaluation = evaluate_snapshot(snapshot)
    return snapshot, evaluation


async def _click_apply(page: Any) -> None:
    locator = page.get_by_role("button", name="Apply for this Job", exact=True)
    if await locator.count() == 0:
        locator = page.get_by_text("Apply for this Job", exact=True)
    if await locator.count() == 0:
        raise RuntimeError("Ashby Apply for this Job control was not found")
    await locator.first.click()


async def _field_metadata(page: Any) -> list[dict[str, Any]]:
    locator = page.locator(FIELD_SELECTOR)
    count = await locator.count()
    result: list[dict[str, Any]] = []
    for index in range(count):
        element = locator.nth(index)
        try:
            item = await element.evaluate(
                """
                (element, index) => {
                  const labels = element.labels
                    ? Array.from(element.labels).map(label => (label.innerText || '').trim())
                    : [];
                  let node = element;
                  let context = '';
                  for (let i = 0; i < 5 && node; i += 1) {
                    const text = (node.innerText || '').trim();
                    if (text.length >= 12 && text.length <= 700) {
                      context = text;
                      break;
                    }
                    node = node.parentElement;
                  }
                  return {
                    index,
                    tag: element.tagName.toLowerCase(),
                    type: element.getAttribute('type') || '',
                    role: element.getAttribute('role') || '',
                    name: element.getAttribute('name') || '',
                    id: element.id || '',
                    placeholder: element.getAttribute('placeholder') || '',
                    required: Boolean(
                      element.required
                      || element.getAttribute('aria-required') === 'true'
                      || element.getAttribute('data-required') === 'true'
                      || /\\brequired\\b|(^|\\s)\\*/i.test(
                        (element.labels && Array.from(element.labels)
                          .map(label => (label.innerText || '').trim()).join(' '))
                        + ' ' + context
                      )
                    ),
                    labels,
                    context
                  };
                }
                """,
                index,
            )
            if isinstance(item, dict):
                result.append(item)
        except Exception:
            continue
    return result


def _label(item: dict[str, Any]) -> str:
    return " ".join(str(value) for value in item.get("labels", []) if value).casefold()


def _context(item: dict[str, Any]) -> str:
    return " ".join(
        (
            _label(item),
            str(item.get("placeholder") or ""),
            str(item.get("context") or ""),
        )
    ).casefold()


def _role_family(title: str, posting: str) -> str:
    value = f"{title} {posting}".casefold()
    if re.search(
        r"account executive|account director|account associate|sales|partner|"
        r"business development|customer success|solutions architect|technical account",
        value,
    ):
        return "sales_engineering"
    return "applied_ai"


def _job_source_span(posting_text: str) -> str | None:
    """Select one short, visible job-page sentence for motivation grounding."""

    compact = " ".join(str(posting_text or "").split())
    if not compact:
        return None
    suspicious = (
        "ignore previous",
        "system message",
        "developer message",
        "instructions to the assistant",
    )
    sentences = re.split(r"(?<=[.!?])\s+", compact)
    for sentence in sentences:
        candidate = sentence.strip(" \u00a0\t\r\n")
        if not 40 <= len(candidate) <= 500:
            continue
        if any(token in candidate.casefold() for token in suspicious):
            continue
        if not re.search(
            r"agent|ai|technical|support|customer|developer|platform|automation|engineering",
            candidate,
            re.IGNORECASE,
        ):
            continue
        return candidate
    return None


def _is_free_text_field(item: dict[str, Any]) -> bool:
    tag = str(item.get("tag") or "").casefold()
    kind = str(item.get("type") or "").casefold()
    role = str(item.get("role") or "").casefold()
    if tag == "textarea":
        return True
    if tag != "input" or role in {"checkbox", "radio"}:
        return False
    return kind in {"", "text", "search", "url", "tel", "number", "email"}


def _question_answers(
    fields: list[dict[str, Any]],
    *,
    profile: dict[str, Any],
    company: str,
    role: str,
    posting_text: str,
) -> dict[int, dict[str, Any]]:
    source_span = _job_source_span(posting_text)
    answers: dict[int, dict[str, Any]] = {}
    for item in fields:
        if not _is_free_text_field(item):
            continue
        question = _context(item)
        if application_question_kind(question) is None:
            continue
        try:
            answer = build_application_question_answer(
                profile,
                question_source_span=question,
                company=company,
                role=role,
                job_source_span=source_span,
            )
        except MessageError:
            # The caller will report the field as an unknown required control;
            # no claim is created and no guessed answer reaches the ATS.
            continue
        answers[int(item["index"])] = answer
    return answers


def _known_value(
    item: dict[str, Any],
    profile: dict[str, Any],
    *,
    question_answers: dict[int, dict[str, Any]] | None = None,
) -> str | None:
    index = item.get("index")
    if question_answers is not None and index is not None:
        answer = question_answers.get(int(index))
        if answer is not None:
            return str(answer["answer"])
    candidate = profile.get("candidate", {})
    labels = _label(item)
    context = _context(item)
    romaji_parts = candidate.get("name_romaji_parts") or {}
    if "legal first" in context or "preferred first" in context:
        return str(romaji_parts.get("given") or "")
    if "legal last" in context or "preferred last" in context:
        return str(romaji_parts.get("family") or "")
    if labels in {"name", "full name"} or "legal name" in context:
        return str(candidate.get("name") or "")
    if "preferred name" in context:
        return str(candidate.get("preferred_name") or "")
    if "email" in context:
        return str(candidate.get("application_email") or "")
    if "phone" in context or "telephone" in context:
        return str(candidate.get("phone") or "")
    if "linkedin" in context:
        return str(candidate.get("linkedin_url") or "")
    if "github" in context:
        return str(candidate.get("github_url") or "")
    if "start date" in context or "when can you start" in context:
        return str(candidate.get("start_date") or "")
    if "how did you hear" in context:
        for fact in profile.get("facts", []):
            if fact.get("id") == "application_source_job_board_20260807":
                return "Company website"
    if "current or most recent employer" in context:
        for fact in profile.get("facts", []):
            if fact.get("id") == "muit_role_2025":
                return "Mitsubishi UFJ Information Technology"
    if "where are you currently located" in context or "current location" in context:
        return str(candidate.get("base") or "")
    if "portfolio" in context:
        return str(candidate.get("github_url") or candidate.get("linkedin_url") or "")
    return None


async def _fill_known_fields(
    page: Any,
    fields: list[dict[str, Any]],
    profile: dict[str, Any],
    resume: Path,
    question_answers: dict[int, dict[str, Any]],
) -> list[str]:
    locator = page.locator(FIELD_SELECTOR)
    blockers: list[str] = []
    for item in fields:
        index = int(item["index"])
        element = locator.nth(index)
        kind = str(item.get("type") or "").casefold()
        role = str(item.get("role") or "").casefold()
        label = _label(item)
        if kind == "file" and ("resume" in label or item.get("id") == "_systemfield_resume"):
            await element.set_input_files(str(resume))
            continue
        value = _known_value(
            item,
            profile,
            question_answers=question_answers,
        )
        if value is None:
            if item.get("required"):
                blockers.append(_safe_text(label or item.get("context") or item.get("placeholder") or kind))
            continue
        if not value:
            if item.get("required"):
                blockers.append(_safe_text(label or item.get("placeholder") or kind))
            continue
        if kind in {"checkbox", "radio"} or role in {"checkbox", "radio"}:
            continue
        await element.fill(value)
    return blockers


async def _has_visible_captcha(page: Any) -> bool:
    try:
        text = await page.locator("body").inner_text(timeout=3_000)
    except Exception:
        return False
    return bool(CAPTCHA_RE.search(text))


async def _submitted_confirmation(page: Any) -> bool:
    for _ in range(20):
        try:
            body = await page.locator("body").inner_text(timeout=1_000)
        except Exception:
            body = ""
        if CONFIRMATION_RE.search(body):
            return True
        if "/application" not in page.url.casefold() and "ashbyhq.com" in page.url.casefold():
            return True
        await page.wait_for_timeout(250)
    return False


async def _visible_validation_error(page: Any) -> bool:
    try:
        invalid = page.locator("[aria-invalid='true']")
        if await invalid.count():
            return True
        alerts = await page.locator("[role='alert']").all_inner_texts()
    except Exception:
        return False
    return any(FORM_ERROR_RE.search(text or "") for text in alerts)


def _provider_limit_result(
    *,
    application_id: str,
    company: str,
    title: str,
    ledger: Ledger,
) -> dict[str, Any]:
    """Quarantine an ATS-policy-blocked row so every wake does not repeat it."""

    try:
        ledger.transition(
            application_id,
            "rejected",
            {
                "reason": "provider_application_limit_visible",
                "provider": "ashby",
            },
        )
    except Exception as error:
        return {
            "application_id": application_id,
            "company": company,
            "title": title,
            "status": "blocked",
            "blocker": "provider_application_limit_transition_failed",
            "error_type": type(error).__name__,
        }
    return {
        "application_id": application_id,
        "company": company,
        "title": title,
        "status": "rejected",
        "blocker": "provider_application_limit_visible",
    }


async def _process_one(
    page: Any,
    row: dict[str, Any],
    *,
    profile: dict[str, Any],
    materials_root: Path,
    ledger: Ledger,
    evidence_dir: Path,
    japan_day: str,
) -> dict[str, Any]:
    application_id = str(row["application_id"])
    url = canonical_url(str(row["canonical_url"]))
    if "jobs.ashbyhq.com" not in url and "app.ashbyhq.com" not in url:
        return {"application_id": application_id, "status": "skipped_non_ashby"}

    await page.goto(url, wait_until="commit", timeout=45_000)
    posting_text = await _body_text(page)
    posting_path = evidence_dir / f"posting-{application_id[:16]}.txt"
    posting_path.write_text(posting_text, encoding="utf-8")
    os.chmod(posting_path, 0o600)
    if PROVIDER_LIMIT_RE.search(posting_text):
        return _provider_limit_result(
            application_id=application_id,
            company=str(row["company"]),
            title=str(row["title"]),
            ledger=ledger,
        )
    snapshot, evaluation = await _wait_for_surface(page)
    if evaluation["surface"] == "ashby_job":
        await _click_apply(page)
        snapshot, evaluation = await _wait_for_surface(page)
    form_text = await _body_text(page)
    if PROVIDER_LIMIT_RE.search(form_text):
        return _provider_limit_result(
            application_id=application_id,
            company=str(row["company"]),
            title=str(row["title"]),
            ledger=ledger,
        )
    if not evaluation["claim_ready"]:
        return {
            "application_id": application_id,
            "company": row["company"],
            "title": row["title"],
            "status": "blocked",
            "blocker": ",".join(evaluation.get("blockers", [])) or "application_surface_not_found",
        }
    role_family = _role_family(str(row["title"]), posting_text)
    resume = select_resume(
        posting_text=posting_text,
        role_family=role_family,
        materials_root=materials_root,
    )
    fields = await _field_metadata(page)
    question_answers = _question_answers(
        fields,
        profile=profile,
        company=str(row["company"]),
        role=str(row["title"]),
        posting_text=posting_text,
    )
    captcha_visible = await _has_visible_captcha(page)
    if captcha_visible:
        return {
            "application_id": application_id,
            "company": row["company"],
            "title": row["title"],
            "status": "blocked",
            "blocker": "visible_captcha",
        }
    blockers: list[str] = []
    for item in fields:
        if not item.get("required"):
            continue
        kind = str(item.get("type") or "").casefold()
        label = _label(item)
        if kind == "file" and ("resume" in label or item.get("id") == "_systemfield_resume"):
            continue
        if _known_value(
            item,
            profile,
            question_answers=question_answers,
        ) is None:
            blockers.append(_safe_text(label or item.get("context") or item.get("placeholder") or kind))
    if blockers:
        return {
            "application_id": application_id,
            "company": row["company"],
            "title": row["title"],
            "status": "blocked",
            "blocker": "unknown_required_field",
            "fields": blockers[:12],
        }
    answer_fingerprint = None
    if question_answers:
        answer_fingerprint = hashlib.sha256(
            json.dumps(
                question_answers,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    claim_path = evidence_dir / f"ats-{application_id[:16]}-claim.json"
    _write_json(claim_path, snapshot)
    claim_sha256 = hashlib.sha256(claim_path.read_bytes()).hexdigest()
    payload = {
        "canonical_url": url,
        "resume_sha256": resume["resume_sha256"],
        "role_family": role_family,
    }
    if answer_fingerprint:
        payload["application_answers_sha256"] = answer_fingerprint
    payload_hash = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    intent = ledger.claim_submission(
        application_id,
        japan_day,
        payload_hash,
        resume_path=Path(resume["resume_path"]),
        resume_sha256=resume["resume_sha256"],
        ats_snapshot_path=claim_path,
        ats_snapshot_sha256=claim_sha256,
    )
    if intent is None:
        return {
            "application_id": application_id,
            "company": row["company"],
            "title": row["title"],
            "status": "already_claimed",
        }
    clicked = False
    try:
        fill_blockers = await _fill_known_fields(
            page,
            fields,
            profile,
            Path(resume["resume_path"]),
            question_answers,
        )
        captcha_visible = await _has_visible_captcha(page)
        if fill_blockers or captcha_visible:
            ledger.complete_submission(intent.intent_id, intent.fence, "not_submitted")
            return {
                "application_id": application_id,
                "company": row["company"],
                "title": row["title"],
                "status": "not_submitted",
                "blocker": "visible_captcha" if captcha_visible else "fill_blocked",
                "fields": fill_blockers[:12],
            }
        submit = page.get_by_role("button", name="Submit Application", exact=True)
        if await submit.count() == 0:
            # Some Ashby tenants mark the native button aria-hidden while
            # keeping its user-facing text visibly clickable.  Clicking the
            # visible text span is an ordinary user-facing action; it is not a
            # force click or DOM event dispatch.
            submit = page.get_by_text("Submit Application", exact=True)
        if await submit.count() == 0 or not await submit.first.is_visible():
            ledger.complete_submission(intent.intent_id, intent.fence, "not_submitted")
            return {"application_id": application_id, "status": "not_submitted", "blocker": "submit_control_missing"}
        submit_requests: list[str] = []

        def observe_request(request: Any) -> None:
            if request.method not in {"POST", "PUT"}:
                return
            if "ashbyhq.com" in request.url.casefold():
                submit_requests.append(request.url)

        page.on("request", observe_request)
        await submit.first.click()
        clicked = True
        confirmed = await _submitted_confirmation(page)
        if confirmed:
            outcome = "submitted"
        elif await _visible_validation_error(page):
            outcome = "not_submitted"
        else:
            outcome = "submit_unknown"
        ledger.complete_submission(intent.intent_id, intent.fence, outcome)
        page.remove_listener("request", observe_request)
        return {
            "application_id": application_id,
            "company": row["company"],
            "title": row["title"],
            "status": outcome,
            "url": url,
            "submit_request_observed": bool(submit_requests),
            "answered_fields": [
                _safe_text(
                    fields[index].get("labels")
                    or fields[index].get("context")
                    or fields[index].get("placeholder")
                )
                for index in sorted(question_answers)
                if 0 <= index < len(fields)
            ],
        }
    except Exception as error:
        try:
            page.remove_listener("request", observe_request)
        except Exception:
            pass
        try:
            ledger.complete_submission(
                intent.intent_id,
                intent.fence,
                "submit_unknown" if clicked else "not_submitted",
            )
        except Exception:
            pass
        return {
            "application_id": application_id,
            "company": row["company"],
            "title": row["title"],
            "status": "submit_unknown" if clicked else "not_submitted",
            "blocker": "post_click_exception" if clicked else "pre_click_exception",
            "error_type": type(error).__name__,
        }


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    profile_sha256 = hashlib.sha256(args.profile.read_bytes()).hexdigest()
    mapper_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    required_field_blockers = _load_required_field_blockers(args.blocker_state)
    ledger = Ledger(args.ledger)
    exclusions = profile.get("candidate", {}).get("employer_exclusions", [])
    excluded = ledger.reject_excluded_employers(
        frozenset(str(value) for value in exclusions)
        if isinstance(exclusions, list)
        else None
    )
    # A definite pre-click ``not_submitted`` is retryable: Ledger releases its
    # slot and increments the fence on the next claim.  ``submit_unknown`` is
    # intentionally absent from this list and is reconciled only by inbox/ATS
    # evidence.  Without this union, a safe pre-click Ashby blocker could never
    # be retried by the deterministic path on a later cadence.
    pending = ledger.pending_materials_ready_applications()
    retryable = ledger.retryable_applications()
    rows_by_id = {
        str(row["application_id"]): row
        for row in [*pending, *retryable]
        if "ashbyhq.com" in str(row["canonical_url"])
    }
    skipped_blocked: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for row in rows_by_id.values():
        application_id = str(row["application_id"])
        blocker = required_field_blockers.get(application_id)
        if (
            blocker
            and blocker.get("profile_sha256") == profile_sha256
            and blocker.get("mapper_sha256") == mapper_sha256
        ):
            skipped_blocked.append(
                {
                    "application_id": application_id,
                    "company": row["company"],
                    "title": row["title"],
                    "status": "blocked",
                    "blocker": "unchanged_unknown_required_field",
                    "fields": list(blocker.get("fields") or [])[:12],
                }
            )
            continue
        rows.append(row)
    if args.max_jobs > 0:
        rows = rows[: args.max_jobs]
    result: dict[str, Any] = {
        "status": "no_work" if not rows else "completed",
        "processed": [],
        "skipped_blocked": skipped_blocked,
        "excluded": excluded,
        "owner": "ai.anicca.job-search-daily",
    }
    if not rows:
        _write_json(args.output, result)
        ledger.close()
        return result
    pw = await async_playwright().start()
    browser = None
    page = None
    try:
        browser = await pw.chromium.connect_over_cdp(args.endpoint)
        if not browser.contexts:
            raise RuntimeError("shared CDP browser has no context")
        page = await browser.contexts[0].new_page()
        for row in rows:
            try:
                result["processed"].append(
                    await _process_one(
                        page,
                        row,
                        profile=profile,
                        materials_root=args.materials_root,
                        ledger=ledger,
                        evidence_dir=args.evidence_dir,
                        japan_day=args.japan_day,
                    )
                )
            except Exception as error:
                result["processed"].append(
                    {
                        "application_id": row["application_id"],
                        "company": row["company"],
                        "title": row["title"],
                        "status": "blocked",
                        "blocker": "fast_path_exception",
                        "error_type": type(error).__name__,
                    }
                )
            outcome = result["processed"][-1]
            application_id = str(row["application_id"])
            if outcome.get("blocker") == "unknown_required_field":
                required_field_blockers[application_id] = {
                    "profile_sha256": profile_sha256,
                    "mapper_sha256": mapper_sha256,
                    "fields": list(outcome.get("fields") or [])[:12],
                }
            else:
                required_field_blockers.pop(application_id, None)
    finally:
        if page is not None:
            await page.close()
        await pw.stop()
        ledger.close()
    _save_required_field_blockers(args.blocker_state, required_field_blockers)
    _write_json(args.output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:9222")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--materials-root", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--japan-day", required=True)
    parser.add_argument("--max-jobs", type=int, default=0)
    parser.add_argument(
        "--blocker-state",
        type=Path,
        default=Path.home() / ".local/state/anicca/job-search/ashby-required-field-blockers.json",
    )
    args = parser.parse_args()
    args.evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    print(json.dumps(asyncio.run(_run(args)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
