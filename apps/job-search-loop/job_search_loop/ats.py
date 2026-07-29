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
