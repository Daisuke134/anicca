from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


def detect_provider(url: str) -> str:
    hostname = (urlsplit(url).hostname or "").casefold().rstrip(".")
    if hostname in {"jobs.ashbyhq.com", "app.ashbyhq.com"}:
        return "ashby"
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


def _is_email_control(control: dict[str, Any]) -> bool:
    control_type = _normalized(control.get("type"))
    if control_type == "email":
        return True
    if control_type not in {"", "text"}:
        return False
    return any(
        marker in _normalized(control.get(field))
        for field in ("label", "name", "text")
        for marker in ("email", "メール")
    )


def _is_application_form(controls: list[dict[str, Any]]) -> bool:
    has_email = any(
        _is_email_control(control)
        for control in controls
    )
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
    visible_text = _normalized(control.get("text"))
    is_apply_text = visible_text in {
        "apply",
        "apply now",
        "apply for this job",
        "apply for this role",
    }
    return (
        is_apply_text
        and (role in {"button", "link"} or tag in {"a", "button"})
        and "submit application" not in text
    )


def _has_exact_text(controls: list[dict[str, Any]], value: str) -> bool:
    expected = value.casefold()
    return any(_normalized(control.get("text")) == expected for control in controls)


def _is_workday_apply_choice(controls: list[dict[str, Any]]) -> bool:
    english_labels = all(
        _has_exact_text(controls, text)
        for text in (
            "Autofill with Resume",
            "Apply Manually",
            "Use My Last Application",
        )
    )
    japanese_labels = all(
        _has_exact_text(controls, text)
        for text in ("手動で応募", "自分の前回の応募情報を使用")
    )
    return english_labels or japanese_labels


def _is_workday_account_create(controls: list[dict[str, Any]]) -> bool:
    password_count = sum(
        _normalized(control.get("type")) == "password" for control in controls
    )
    has_email = any(_is_email_control(control) for control in controls)
    has_password_confirmation = any(
        marker in _control_text(control)
        for control in controls
        for marker in (
            "verify new password",
            "password confirmation",
            "新しいパスワードの確認",
            "パスワードの確認",
        )
    )
    has_create_action = any(
        _normalized(control.get("text")) in {"create account", "アカウントの作成"}
        and (
            _normalized(control.get("role")) == "button"
            or _normalized(control.get("tag")) == "button"
        )
        for control in controls
    )
    return (
        has_email
        and has_password_confirmation
        and password_count >= 2
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
        elif any(_is_apply_control(control) for control in controls):
            base.update(
                {
                    "ready": True,
                    "surface": (
                        "ashby_job" if provider == "ashby" else "generic_job"
                    ),
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
