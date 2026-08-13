from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable

from .ats import (
    SUPPORTED_FILL_PROVIDERS,
    build_non_submit_fill_plan,
    detect_provider,
    evaluate_snapshot,
    execute_non_submit_fill_plan,
)
from .browser_pages import PageOwnership
from .resume_routing import select_resume
from .workday_credentials import WorkdayCredentialError, fill_account_creation


CONTROL_SELECTOR = (
    "input, textarea, select, button, a, [role=button], [role=alert], [role=status]"
)
EXECUTOR = "cloakbrowser-cdp"


def _private_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def grounded_profile_answers(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidate = profile.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("private profile candidate is missing")
    answers: dict[str, dict[str, Any]] = {}
    name = candidate.get("name")
    if isinstance(name, str) and name.strip():
        normalized_name = " ".join(name.split())
        parts = normalized_name.split(" ")
        answers["full_name"] = {
            "value": normalized_name,
            "fact_ids": ["profile.name"],
        }
        answers["first_name"] = {
            "value": parts[0],
            "fact_ids": ["profile.name"],
        }
        if len(parts) > 1:
            answers["last_name"] = {
                "value": parts[-1],
                "fact_ids": ["profile.name"],
            }
    fields = {
        "email": ("application_email", "profile.application_email"),
        "linkedin": ("linkedin_url", "profile.linkedin_url"),
        "github": ("github_url", "profile.github_url"),
    }
    for field_key, (profile_key, fact_id) in fields.items():
        value = candidate.get(profile_key)
        if isinstance(value, str) and value.strip():
            answers[field_key] = {"value": value.strip(), "fact_ids": [fact_id]}
    base = candidate.get("base")
    if isinstance(base, str) and base.strip():
        answers["location"] = {
            "value": base.strip(),
            "fact_ids": ["profile.current_location_20260807"],
        }
    phone = candidate.get("phone")
    phone_status = candidate.get("phone_status")
    if (
        isinstance(phone_status, str)
        and phone_status.startswith("verified")
        and isinstance(phone, str)
        and phone.strip()
    ):
        answers["phone"] = {
            "value": phone.strip(),
            "fact_ids": ["profile.phone"],
        }
        answers["phone_country_code"] = {
            "value": "Japan (+81)",
            "fact_ids": ["profile.phone"],
        }
    known_fact_ids = {
        str(item.get("id"))
        for item in profile.get("facts", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    verified = {
        "work_authorization": (
            "Yes",
            "legal_japan_work_authorization_20260730",
        ),
        "sponsorship": (
            "No",
            "legal_no_japan_sponsorship_required_20260806",
        ),
        "attestation": (
            "true",
            "ordinary_truthful_application_attestation_20260807",
        ),
        "application_source": ("Job board", "application_source_job_board_20260807"),
        "tokyo_office": ("Yes", "availability_tokyo_office_three_days_20260806"),
    }
    for key, (value, fact_id) in verified.items():
        if fact_id in known_fact_ids:
            answers[key] = {"value": value, "fact_ids": [fact_id]}
    start_date = candidate.get("start_date")
    if isinstance(start_date, str) and start_date.strip():
        answers["start_date"] = {
            "value": start_date.strip(),
            "fact_ids": ["profile.start_date"],
        }
    return answers


def ranked_pre_submit_candidates(
    payload: dict[str, Any], *, limit: int = 3
) -> list[dict[str, Any]]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("prefilter candidates are missing")
    supported = [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict)
        and candidate.get("ranking_ready") is True
        and detect_provider(str(candidate.get("official_url") or ""))
        in SUPPORTED_FILL_PROVIDERS
    ]
    bucket_priority = {"dream": 3, "strong_fit": 2, "adjacent": 1}
    supported.sort(
        key=lambda candidate: (
            bucket_priority.get(str(candidate.get("portfolio_bucket") or ""), 0),
            int((candidate.get("ranking") or {}).get("score", 0)),
            str(candidate.get("official_url") or ""),
        ),
        reverse=True,
    )
    return supported[:limit]


def select_pre_submit_candidate(payload: dict[str, Any]) -> dict[str, Any] | None:
    supported = ranked_pre_submit_candidates(payload, limit=1)
    return supported[0] if supported else None


def attempt_ranked_candidates(
    candidates: list[dict[str, Any]],
    attempt: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    blocked: list[str] = []
    attempt_audit: list[dict[str, Any]] = []
    claim_ready_dossier: dict[str, Any] | None = None
    attempted_count = 0
    for index, candidate in enumerate(candidates, start=1):
        attempted_count += 1
        audit = {
            "candidate_index": index,
            "url_sha256": hashlib.sha256(
                str(candidate.get("official_url") or "").encode("utf-8")
            ).hexdigest(),
            "role_family": str(candidate.get("role_family") or "unknown"),
        }
        try:
            receipt = attempt(candidate)
        except Exception as error:
            audit["outcome"] = f"error:{type(error).__name__}"
            attempt_audit.append(audit)
            blocked.append(f"candidate_{index}:error:{type(error).__name__}")
            continue
        if receipt.get("claim_ready") is True:
            dossier = receipt.get("claim_ready_dossier")
            if isinstance(dossier, dict):
                claim_ready_dossier = dossier
            audit["outcome"] = "claim_ready"
            attempt_audit.append(audit)
            blocked.append("pre_submit_claim_ready_no_submit")
            break
        audit["outcome"] = "blocked"
        attempt_audit.append(audit)
        reasons = list(receipt.get("blockers") or ["application_surface_not_ready"])
        blocked.extend(f"candidate_{index}:{reason}" for reason in reasons)
    return {
        "status": "pending_verification",
        "blocked": blocked or ["no_ranking_ready_candidate"],
        "attempted_count": attempted_count,
        "attempt_audit": attempt_audit,
        "continued_after_failure": len(attempt_audit) > 1
        and attempt_audit[0]["outcome"] != "claim_ready",
        "claim_ready_dossier": claim_ready_dossier,
    }


def _page_targets(session: Any) -> set[str]:
    value = session.send("Target.getTargets")
    return {
        item["targetId"]
        for item in value.get("targetInfos", [])
        if item.get("type") == "page" and isinstance(item.get("targetId"), str)
    }


def capture_snapshot(page: Any, *, navigation_committed: bool) -> dict[str, Any]:
    frames = []
    script = """nodes => nodes.map(n => {
      const clean = value => (value || '').replace(/\\s+/g, ' ').trim();
      const explicit = n.getAttribute('aria-label') || '';
      const associated = n.labels && n.labels.length
        ? Array.from(n.labels).map(x => (x.innerText || x.textContent || '').trim()).join(' ')
        : '';
      const placeholder = n.getAttribute('placeholder') || '';
      const ownText = clean(n.innerText || n.textContent || '');
      let groupLabel = '';
      const role = n.getAttribute('role') || '';
      const tag = (n.tagName || '').toLowerCase();
      const choiceText = ownText.toLowerCase();
      const needsGroup = role === 'combobox' ||
        ((tag === 'button' || role === 'button') && (choiceText === 'yes' || choiceText === 'no'));
      if (needsGroup) {
        let cursor = n.parentElement;
        for (let depth = 0; cursor && depth < 6; depth += 1, cursor = cursor.parentElement) {
          const lines = (cursor.innerText || '').split('\\n').map(clean).filter(Boolean);
          const question = lines.find(line =>
            line !== ownText && line.length <= 1000 && (line.endsWith('*') || line.includes('?'))
          );
          if (question) {
            groupLabel = question;
            break;
          }
        }
      }
      return {
        tag: tag,
        type: n.getAttribute('type') || '',
        role: role,
        automation_id: n.getAttribute('data-automation-id') || '',
        label: explicit || associated || placeholder,
        name: n.getAttribute('name') || '',
        text: ownText,
        group_label: groupLabel,
        required: Boolean(n.required) || n.getAttribute('aria-required') === 'true' || groupLabel.endsWith('*') || groupLabel.includes('?')
      };
    })"""
    for frame in page.frames:
        controls = frame.locator(CONTROL_SELECTOR).evaluate_all(script)
        frames.append({"url": frame.url, "controls": controls})
    return {
        "version": 1,
        "url": page.url,
        "navigation_committed": navigation_committed,
        "frames": frames,
    }


class PlaywrightFillAdapter:
    def __init__(self, page: Any):
        self.page = page

    def _control(self, frame_index: int, control_index: int) -> Any:
        return self.page.frames[frame_index].locator(CONTROL_SELECTOR).nth(control_index)

    def fill(self, frame_index: int, control_index: int, value: str) -> None:
        self._control(frame_index, control_index).fill(value)

    def read_value(self, frame_index: int, control_index: int) -> str:
        return self._control(frame_index, control_index).input_value()

    def upload(self, frame_index: int, control_index: int, path: str) -> None:
        self._control(frame_index, control_index).set_input_files(path)

    def upload_matches(self, frame_index: int, control_index: int, path: str) -> bool:
        value = self._control(frame_index, control_index).input_value()
        return Path(value.replace("\\", "/")).name == Path(path).name

    def select(self, frame_index: int, control_index: int, value: str) -> bool:
        frame = self.page.frames[frame_index]
        labeled = frame.get_by_label(value, exact=True)
        if labeled.count() == 1 and labeled.get_attribute("type") in {
            "radio",
            "checkbox",
        }:
            labeled.check()
            return labeled.is_checked()
        control = self._control(frame_index, control_index)
        if control.evaluate("node => node.tagName.toLowerCase()") == "select":
            control.select_option(label=value)
            return control.locator("option:checked").inner_text().strip() == value
        if control.get_attribute("role") == "combobox":
            control.fill(value)
            option = frame.get_by_role("option", name=value, exact=True)
            if option.count():
                option.first.click()
            else:
                control.press("ArrowDown")
                control.press("Enter")
            return bool(control.input_value().strip())
        control.click()
        return any(
            control.get_attribute(name) in {"true", "checked", "selected", "on"}
            for name in ("aria-checked", "aria-pressed", "data-state")
        )

    def check(self, frame_index: int, control_index: int) -> bool:
        control = self._control(frame_index, control_index)
        control.check()
        return control.is_checked()

    def screenshot(self, path: str) -> None:
        self.page.screenshot(path=path, full_page=True)


def _workday_step_signature(snapshot: dict[str, Any]) -> str:
    controls = [
        control
        for frame in snapshot.get("frames") or []
        for control in frame.get("controls") or []
        if str(control.get("role") or "").casefold() not in {"alert", "status"}
    ]
    return hashlib.sha256(
        json.dumps(controls, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _advance_workday_step(page: Any, snapshot: dict[str, Any]) -> dict[str, Any] | None:
    matches = page.get_by_role("button", name="Save and Continue", exact=True)
    visible = [
        matches.nth(index)
        for index in range(matches.count())
        if matches.nth(index).is_visible()
    ]
    if len(visible) != 1:
        return None
    previous = _workday_step_signature(snapshot)
    visible[0].click(timeout=10_000)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        page.wait_for_timeout(500)
        current = capture_snapshot(page, navigation_committed=True)
        if any(frame.get("controls") for frame in current["frames"]) and _workday_step_signature(current) != previous:
            return current
    return None


def _application_url(url: str, provider: str) -> str:
    if provider == "ashby" and not url.rstrip("/").endswith("/application"):
        return f"{url.rstrip('/')}/application"
    return url


def run_pre_submit(
    *,
    owner_receipt: dict[str, Any],
    prefilter_result: Path,
    profile_path: Path,
    materials_root: Path,
    evidence_dir: Path,
    telemetry: Any = None,
) -> dict[str, Any]:
    candidates = ranked_pre_submit_candidates(
        json.loads(prefilter_result.read_text(encoding="utf-8")), limit=3
    )
    if not candidates:
        return {"status": "pending_verification", "blocked": ["no_ranking_ready_candidate"], "executor": EXECUTOR}
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    owner_endpoint = owner_receipt.get("endpoint")
    if not isinstance(owner_endpoint, str) or not owner_endpoint:
        return {"status": "pending_verification", "blocked": ["browser_owner_endpoint_missing"], "executor": EXECUTOR}
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(owner_endpoint)
            if not browser.contexts:
                raise RuntimeError("CloakBrowser default context is missing")
            context = browser.contexts[0]
            browser_session = browser.new_browser_cdp_session()
            ownership = PageOwnership(
                _page_targets(browser_session),
                evidence_dir / "browser-page-ownership.json",
                str(owner_receipt.get("lease_id") or ""),
                int(owner_receipt.get("fence") or 0),
            )
            page = context.new_page()
            page_session = context.new_cdp_session(page)
            target = page_session.send("Target.getTargetInfo")["targetInfo"]["targetId"]
            ownership.register_created(target)
            owned_page = {
                "target_id": target,
                "lease_id": str(owner_receipt.get("lease_id") or ""),
                "fence": int(owner_receipt.get("fence") or 0),
            }
            try:
                def attempt(candidate: dict[str, Any]) -> dict[str, Any]:
                    url = str(candidate.get("official_url") or "")
                    provider = detect_provider(url)
                    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
                    page.goto(
                        _application_url(url, provider),
                        wait_until="commit",
                        timeout=45_000,
                    )
                    provider_blockers: list[str] = []
                    if provider == "workday":
                        try:
                            credential_receipt = fill_account_creation(
                                job_url=url,
                                profile_path=profile_path,
                                store_path=profile_path.parent / "workday-accounts.json",
                                owner_receipt=owner_receipt,
                                ownership_receipt=json.loads(
                                    ownership.receipt_path.read_text(encoding="utf-8")
                                ),
                                owned_page=owned_page,
                                playwright=playwright,
                                page=page,
                            )
                            _private_write(
                                evidence_dir / f"workday-account-{digest}.json",
                                credential_receipt,
                            )
                        except WorkdayCredentialError as error:
                            stage = next(
                                (
                                    value
                                    for value in (
                                        "job_surface",
                                        "manual_choice",
                                        "native_chooser",
                                        "email_form",
                                        "password_form",
                                    )
                                    if str(error).endswith(f":{value}")
                                ),
                                "native_auth",
                            )
                            provider_blockers.append(f"workday_{stage}_unavailable")
                    else:
                        page.locator("input[type=file]").first.wait_for(
                            state="attached", timeout=20_000
                        )
                    posting_text = " ".join(
                        str(value) for value in candidate.get("source_spans", [])
                    )
                    routed = select_resume(
                        posting_text=posting_text,
                        role_family=str(candidate.get("role_family") or "unknown"),
                        materials_root=materials_root,
                        posting_language=str(candidate.get("language") or "en"),
                    )
                    answers_path = evidence_dir / f"employer-answers-{digest}.json"
                    all_answers: list[dict[str, Any]] = []
                    submission_evidence: tuple[Path, Path] | None = None
                    snapshot: dict[str, Any] | None = None
                    for step in range(1, 11):
                        if snapshot is None:
                            snapshot = capture_snapshot(page, navigation_committed=True)
                        suffix = "" if step == 1 else f"-step-{step:02d}"
                        snapshot_path = evidence_dir / f"ats-snapshot-{digest}{suffix}.json"
                        evaluation_path = evidence_dir / f"ats-evaluation-{digest}{suffix}.json"
                        _private_write(snapshot_path, snapshot)
                        snapshot_sha256 = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
                        evaluation = evaluate_snapshot(snapshot)
                        _private_write(evaluation_path, evaluation)
                        if evaluation.get("surface") == "workday_review":
                            if submission_evidence is None:
                                return {
                                    "claim_ready": False,
                                    "blockers": ["workday_resume_not_verified"],
                                }
                            _private_write(answers_path, all_answers)
                            evidence_snapshot, evidence_receipt = submission_evidence
                            return {
                                "claim_ready": True,
                                "blockers": [],
                                "claim_ready_dossier": {
                                    "company": str(candidate.get("company") or ""),
                                    "title": str(candidate.get("title") or ""),
                                    "official_url": url,
                                    "url_sha256": digest,
                                    "portfolio_bucket": str(candidate.get("portfolio_bucket") or "adjacent"),
                                    "resume_path": routed["resume_path"],
                                    "snapshot_path": str(evidence_snapshot),
                                    "fill_receipt_path": str(evidence_receipt),
                                    "answers_path": str(answers_path),
                                    "review_snapshot_path": str(snapshot_path),
                                    "workday_step_count": step - 1,
                                },
                            }
                        if not evaluation["claim_ready"]:
                            return {
                                "claim_ready": False,
                                "blockers": provider_blockers
                                + list(evaluation.get("blockers") or ["application_surface_not_ready"]),
                            }
                        plan = build_non_submit_fill_plan(
                            snapshot,
                            answers=grounded_profile_answers(profile),
                            resume_path=routed["resume_path"],
                            resume_sha256=routed["resume_sha256"],
                        )
                        screenshot_path = evidence_dir / f"pre-submit-{digest}{suffix}.png"
                        receipt_path = evidence_dir / f"fill-receipt-{digest}{suffix}.json"
                        receipt = execute_non_submit_fill_plan(
                            plan,
                            adapter=PlaywrightFillAdapter(page),
                            owner_receipt=owner_receipt,
                            snapshot_sha256=snapshot_sha256,
                            screenshot_path=screenshot_path,
                            receipt_path=receipt_path,
                        )
                        all_answers.extend(receipt["answers"])
                        _private_write(answers_path, all_answers)
                        if receipt["status"] != "claim_ready":
                            return {
                                "claim_ready": False,
                                "blockers": [
                                    f"pre_submit_blocked:{item}"
                                    for item in receipt.get("blockers", [])
                                ],
                            }
                        if receipt.get("resume_sha256") == routed["resume_sha256"]:
                            submission_evidence = (snapshot_path, receipt_path)
                        if provider != "workday" or evaluation.get("surface") != "workday_application_step":
                            return {
                                "claim_ready": True,
                                "blockers": [],
                                "claim_ready_dossier": {
                                    "company": str(candidate.get("company") or ""),
                                    "title": str(candidate.get("title") or ""),
                                    "official_url": url,
                                    "url_sha256": digest,
                                    "portfolio_bucket": str(candidate.get("portfolio_bucket") or "adjacent"),
                                    "resume_path": routed["resume_path"],
                                    "snapshot_path": str(snapshot_path),
                                    "fill_receipt_path": str(receipt_path),
                                    "answers_path": str(answers_path),
                                },
                            }
                        snapshot = _advance_workday_step(page, snapshot)
                        if snapshot is None:
                            return {
                                "claim_ready": False,
                                "blockers": ["workday_save_and_continue_no_progress"],
                            }
                    return {
                        "claim_ready": False,
                        "blockers": ["workday_step_limit_reached"],
                    }

                return {**attempt_ranked_candidates(candidates, attempt), "executor": EXECUTOR}
            finally:
                current = _page_targets(browser_session)
                for target_id in ownership.closable(current):
                    browser_session.send("Target.closeTarget", {"targetId": target_id})
    except Exception as error:
        return {
            "status": "pending_verification",
            "blocked": [f"pre_submit_error:{type(error).__name__}"],
            "executor": EXECUTOR,
        }
