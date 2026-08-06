from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


SUPPORTED_FILL_PROVIDERS = frozenset(
    {"ashby", "greenhouse", "lever", "workable", "workday"}
)


def detect_provider(url: str) -> str:
    hostname = (urlsplit(url).hostname or "").casefold().rstrip(".")
    if hostname in {"jobs.ashbyhq.com", "app.ashbyhq.com"}:
        return "ashby"
    if hostname in {
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "job-boards.eu.greenhouse.io",
    }:
        return "greenhouse"
    if hostname in {"jobs.lever.co", "jobs.eu.lever.co"}:
        return "lever"
    if hostname == "apply.workable.com":
        return "workable"
    if hostname == "myworkdayjobs.com" or hostname.endswith(".myworkdayjobs.com"):
        return "workday"
    if hostname == "myworkdaysite.com" or hostname.endswith(".myworkdaysite.com"):
        return "workday"
    return "generic"


def _normalized(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip().casefold()


def _control_text(control: dict[str, Any]) -> str:
    return " ".join(
        part
        for part in (
            _normalized(control.get("role")),
            _normalized(control.get("label")),
            _normalized(control.get("name")),
            _normalized(control.get("text")),
        )
        if part
    )


def _field_key(control: dict[str, Any]) -> str | None:
    control_type = _normalized(control.get("type"))
    text = _control_text(control)
    label = _normalized(control.get("label"))
    group_label = _normalized(control.get("group_label"))
    if control_type == "email" or text in {"email", "email address"}:
        return "email"
    if control_type == "file" and any(
        token in text for token in ("resume", "cv", "curriculum vitae")
    ):
        return "resume"
    if "first name" in text or text in {"firstname", "given name"}:
        return "first_name"
    if "last name" in text or text in {"lastname", "family name", "surname"}:
        return "last_name"
    if label in {"name", "full name", "legal name", "preferred name"}:
        return "full_name"
    if control_type == "tel" or "phone number" in group_label or "phone number" in text:
        return "phone"
    if "where are you currently located" in group_label:
        return "location"
    if "linkedin" in group_label or "linkedin" in text:
        return "linkedin"
    if "github" in group_label or "github" in text:
        return "github"
    return None


def _question(control: dict[str, Any]) -> str:
    for key in ("group_label", "label", "name", "text"):
        value = control.get(key)
        if isinstance(value, str) and value.strip():
            return re.sub(r"\s+", " ", value).strip()
    return "unlabeled_required_control"


def build_non_submit_fill_plan(
    snapshot: dict[str, Any],
    *,
    answers: dict[str, dict[str, Any]],
    resume_path: str,
    resume_sha256: str,
) -> dict[str, Any]:
    value = _validate_snapshot(snapshot)
    provider = detect_provider(value["url"])
    if provider not in SUPPORTED_FILL_PROVIDERS:
        raise ValueError("ATS provider is not supported for deterministic fill")
    if not Path(resume_path).is_absolute():
        raise ValueError("resume_path must be absolute")
    if re.fullmatch(r"[0-9a-f]{64}", resume_sha256) is None:
        raise ValueError("resume_sha256 must be lowercase SHA-256")
    actions: list[dict[str, Any]] = []
    blockers: list[str] = []
    for frame_index, frame in enumerate(value["frames"]):
        for control_index, control in enumerate(frame["controls"]):
            if _normalized(control.get("type")) == "submit":
                continue
            field_key = _field_key(control)
            question = _question(control)
            if field_key == "resume":
                actions.append(
                    {
                        "kind": "upload",
                        "field_key": "resume",
                        "frame_index": frame_index,
                        "control_index": control_index,
                        "question": question,
                        "resume_path": resume_path,
                        "resume_sha256": resume_sha256,
                        "fact_ids": [],
                    }
                )
                continue
            answer = answers.get(field_key or "")
            if field_key is not None and isinstance(answer, dict):
                answer_value = answer.get("value")
                fact_ids = answer.get("fact_ids")
                if (
                    isinstance(answer_value, str)
                    and answer_value.strip()
                    and isinstance(fact_ids, list)
                    and fact_ids
                    and all(isinstance(item, str) and item.strip() for item in fact_ids)
                ):
                    actions.append(
                        {
                            "kind": "fill",
                            "field_key": field_key,
                            "frame_index": frame_index,
                            "control_index": control_index,
                            "question": question,
                            "answer": answer_value,
                            "fact_ids": fact_ids,
                        }
                    )
                    continue
            if control.get("required") is True:
                if question not in blockers:
                    blockers.append(question)
    return {
        "version": 1,
        "provider": provider,
        "job_url": value["url"],
        "actions": actions,
        "blockers": blockers,
        "submit_action_included": False,
    }


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_private_json(path: Path, value: dict[str, Any]) -> None:
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


def execute_non_submit_fill_plan(
    plan: dict[str, Any],
    *,
    adapter: Any,
    owner_receipt: dict[str, Any],
    snapshot_sha256: str,
    screenshot_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    if plan.get("submit_action_included") is not False:
        raise ValueError("non-submit plan must explicitly exclude Submit")
    if re.fullmatch(r"[0-9a-f]{64}", snapshot_sha256) is None:
        raise ValueError("snapshot_sha256 must be lowercase SHA-256")
    lease_id = owner_receipt.get("lease_id")
    fence = owner_receipt.get("fence")
    holder_pid = owner_receipt.get("holder_pid")
    if not isinstance(lease_id, str) or not lease_id:
        raise ValueError("browser owner lease_id is required")
    if isinstance(fence, bool) or not isinstance(fence, int) or fence <= 0:
        raise ValueError("browser owner fence is required")
    if isinstance(holder_pid, bool) or not isinstance(holder_pid, int) or holder_pid <= 0:
        raise ValueError("browser owner holder_pid is required")
    answers: list[dict[str, Any]] = []
    resume_sha256: str | None = None
    verified_count = 0
    actions = plan.get("actions")
    if not isinstance(actions, list):
        raise ValueError("fill plan actions must be an array")
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError("fill action must be an object")
        kind = action.get("kind")
        frame_index = action.get("frame_index")
        control_index = action.get("control_index")
        if kind == "fill":
            value = action.get("answer")
            if not isinstance(value, str):
                raise ValueError("fill action answer is required")
            adapter.fill(frame_index, control_index, value)
            if adapter.read_value(frame_index, control_index) != value:
                raise RuntimeError("filled value verification failed")
            answers.append(
                {
                    "question": action.get("question"),
                    "answer": value,
                    "fact_ids": action.get("fact_ids", []),
                }
            )
            verified_count += 1
        elif kind == "upload":
            path = Path(str(action.get("resume_path") or ""))
            expected_sha256 = action.get("resume_sha256")
            if not path.is_file():
                raise ValueError("resume file is missing")
            actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual_sha256 != expected_sha256:
                raise ValueError("resume SHA-256 does not match fill plan")
            adapter.upload(frame_index, control_index, str(path))
            if not adapter.upload_matches(frame_index, control_index, str(path)):
                raise RuntimeError("resume upload verification failed")
            resume_sha256 = actual_sha256
            verified_count += 1
        else:
            raise ValueError("non-submit fill plan contains an unsupported action")
    screenshot_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    adapter.screenshot(str(screenshot_path))
    if not screenshot_path.is_file():
        raise RuntimeError("pre-submit screenshot was not created")
    os.chmod(screenshot_path, 0o600)
    blockers = plan.get("blockers")
    if not isinstance(blockers, list) or any(not isinstance(item, str) for item in blockers):
        raise ValueError("fill plan blockers must be strings")
    receipt = {
        "version": 1,
        "status": "claim_ready" if not blockers else "blocked",
        "provider": plan.get("provider"),
        "job_url": plan.get("job_url"),
        "owner_lease_id": lease_id,
        "owner_fence": fence,
        "owner_holder_pid": holder_pid,
        "snapshot_sha256": snapshot_sha256,
        "plan_sha256": _canonical_sha256(plan),
        "resume_sha256": resume_sha256,
        "screenshot_path": str(screenshot_path),
        "screenshot_sha256": hashlib.sha256(screenshot_path.read_bytes()).hexdigest(),
        "verified_action_count": verified_count,
        "answers": answers,
        "blockers": blockers,
        "submit_clicked": False,
    }
    _write_private_json(receipt_path, receipt)
    return receipt


def _is_application_form(controls: list[dict[str, Any]]) -> bool:
    has_email = any(_normalized(control.get("type")) == "email" for control in controls)
    has_resume = any(_normalized(control.get("type")) == "file" for control in controls)
    has_submit = any(
        "submit application" in _control_text(control)
        or (
            _normalized(control.get("type")) == "submit"
            and "submit" in _control_text(control)
        )
        for control in controls
    )
    return has_email and has_resume and has_submit


def _is_apply_control(control: dict[str, Any]) -> bool:
    text = _control_text(control)
    role = _normalized(control.get("role"))
    tag = _normalized(control.get("tag"))
    return (
        _normalized(control.get("text")) == "apply"
        and (role in {"button", "link"} or tag in {"a", "button"})
        and "application" not in text
    )


def _has_exact_text(controls: list[dict[str, Any]], value: str) -> bool:
    expected = value.casefold()
    return any(_normalized(control.get("text")) == expected for control in controls)


def _is_workday_apply_choice(controls: list[dict[str, Any]]) -> bool:
    return all(
        _has_exact_text(controls, text)
        for text in (
            "Autofill with Resume",
            "Apply Manually",
            "Use My Last Application",
        )
    )


def _is_workday_account_create(controls: list[dict[str, Any]]) -> bool:
    combined = " ".join(_control_text(control) for control in controls)
    password_count = sum(
        _normalized(control.get("type")) == "password" for control in controls
    )
    has_consent = any(
        _normalized(control.get("type")) == "checkbox" for control in controls
    )
    has_create_action = any(
        _normalized(control.get("text")) == "create account"
        and (
            _normalized(control.get("role")) == "button"
            or _normalized(control.get("tag")) == "button"
        )
        for control in controls
    )
    return (
        "email address" in combined
        and "verify new password" in combined
        and password_count >= 2
        and has_consent
        and has_create_action
    )


def _validate_snapshot(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be an object")
    if snapshot.get("version") != 1:
        raise ValueError("snapshot version must be 1")
    if not isinstance(snapshot.get("url"), str) or not snapshot["url"].strip():
        raise ValueError("url must be a non-empty string")
    if not isinstance(snapshot.get("navigation_committed"), bool):
        raise ValueError("navigation_committed must be a boolean")
    frames = snapshot.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("frames must be a non-empty list")
    for frame in frames:
        if not isinstance(frame, dict):
            raise ValueError("each frame must be an object")
        controls = frame.get("controls")
        if not isinstance(controls, list):
            raise ValueError("frame controls must be a list")
        if any(not isinstance(control, dict) for control in controls):
            raise ValueError("each control must be an object")
    return snapshot


def evaluate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    value = _validate_snapshot(snapshot)
    provider = detect_provider(value["url"])
    base = {
        "provider": provider,
        "ready": False,
        "claim_ready": False,
        "surface": "none",
        "frame_index": None,
        "wait_until": "commit",
        "blockers": [],
    }
    if not value["navigation_committed"]:
        base["blockers"] = ["navigation_not_committed"]
        return base

    for frame_index, frame in enumerate(value["frames"]):
        controls = frame["controls"]
        if _is_application_form(controls):
            base.update(
                {
                    "ready": True,
                    "claim_ready": True,
                    "surface": (
                        "ashby_application"
                        if provider == "ashby"
                        else (
                            "workday_application"
                            if provider == "workday"
                            else "generic_application"
                        )
                    ),
                    "frame_index": frame_index,
                }
            )
            return base
        if provider == "workday":
            if _is_workday_apply_choice(controls):
                base.update(
                    {
                        "ready": True,
                        "surface": "workday_apply_choice",
                        "frame_index": frame_index,
                    }
                )
                return base
            if _is_workday_account_create(controls):
                base.update(
                    {
                        "ready": True,
                        "surface": "workday_account_create",
                        "frame_index": frame_index,
                    }
                )
                return base
            if any(_is_apply_control(control) for control in controls):
                base.update(
                    {
                        "ready": True,
                        "surface": "workday_job",
                        "frame_index": frame_index,
                    }
                )
                return base

    base["blockers"] = ["application_surface_not_found"]
    return base


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    print(
        json.dumps(
            evaluate_snapshot(snapshot),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
