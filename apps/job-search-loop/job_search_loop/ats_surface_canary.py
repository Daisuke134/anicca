"""Installed three-ATS no-send canary for the resident CloakBrowser owner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .ats import build_non_submit_fill_plan, detect_provider
from .ats_page_classifier import classify_ats_page
from .playwright_ats import capture_snapshot, grounded_profile_answers
from .resume_routing import select_resume


REQUIRED_PROVIDERS = frozenset({"ashby", "greenhouse", "workday"})


def _private_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _targets(request: Mapping[str, Any]) -> list[dict[str, str]]:
    values = request.get("targets")
    if not isinstance(values, list) or len(values) != 3:
        raise ValueError("ATS canary requires exactly three targets")
    targets: list[dict[str, str]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise ValueError("ATS canary target must be an object")
        provider = str(value.get("provider") or "").strip()
        url = str(value.get("url") or "").strip()
        parsed = urlsplit(url)
        if (
            provider not in REQUIRED_PROVIDERS
            or parsed.scheme != "https"
            or not parsed.hostname
            or detect_provider(url) != provider
        ):
            raise ValueError("ATS canary target provider or URL is invalid")
        targets.append({"provider": provider, "url": url})
    if {target["provider"] for target in targets} != REQUIRED_PROVIDERS:
        raise ValueError("ATS canary requires Ashby, Greenhouse, and Workday")
    return targets


def run_surface_canary(
    *,
    request: Mapping[str, Any],
    owner_receipt: Mapping[str, Any],
    profile: dict[str, Any],
    materials_root: Path,
    evidence_dir: Path,
    playwright: Any,
    snapshotter: Callable[..., dict[str, Any]] = capture_snapshot,
    resume_selector: Callable[..., dict[str, Any]] = select_resume,
) -> dict[str, Any]:
    targets = _targets(request)
    request_id = str(request.get("request_id") or "").strip()
    if not request_id:
        raise ValueError("ATS canary request_id is required")
    if owner_receipt.get("status") != "ready":
        raise ValueError("browser owner is not ready")
    endpoint = str(owner_receipt.get("endpoint") or "")
    endpoint_parts = urlsplit(endpoint)
    if endpoint_parts.scheme not in {"http", "ws"} or endpoint_parts.hostname not in {
        "127.0.0.1", "localhost", "::1",
    }:
        raise ValueError("browser owner endpoint must be loopback")
    lease_id = owner_receipt.get("lease_id")
    fence = owner_receipt.get("fence")
    if not isinstance(lease_id, str) or not lease_id:
        raise ValueError("browser owner lease is missing")
    if isinstance(fence, bool) or not isinstance(fence, int) or fence <= 0:
        raise ValueError("browser owner fence is missing")
    browser = playwright.chromium.connect_over_cdp(endpoint)
    if not browser.contexts:
        raise RuntimeError("resident CloakBrowser context is missing")
    context = browser.contexts[0]
    routed = resume_selector(
        posting_text="", role_family="applied_ai",
        materials_root=materials_root, posting_language="en",
    )
    answers = grounded_profile_answers(profile)
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipts: list[dict[str, Any]] = []
    for target in targets:
        page = context.new_page()
        provider = target["provider"]
        target_dir = evidence_dir / provider
        target_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            page.goto(target["url"], wait_until="commit", timeout=45_000)
            if hasattr(page, "wait_for_timeout"):
                page.wait_for_timeout(3_000)
            snapshot = snapshotter(page, navigation_committed=True)
            classification = classify_ats_page(snapshot)
            plan = build_non_submit_fill_plan(
                snapshot,
                answers=answers,
                resume_path=routed["resume_path"],
                resume_sha256=routed["resume_sha256"],
            )
            if plan.get("submit_action_included") is not False:
                raise RuntimeError("no-send canary produced a Submit action")
            screenshot = target_dir / "surface.png"
            page.screenshot(path=str(screenshot), full_page=True)
            os.chmod(screenshot, 0o600)
            artifact = {
                "provider": provider,
                "url": target["url"],
                "snapshot": snapshot,
                "classification": classification,
                "grounded_plan": plan,
                "screenshot_path": str(screenshot),
                "screenshot_sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest(),
            }
            _private_write(target_dir / "receipt.json", artifact)
            receipts.append({
                "provider": provider,
                "classification": classification["classification"],
                "next_route": classification["next_route"],
                "grounded_action_count": len(plan["actions"]),
                "blocker_count": len(plan["blockers"]),
                "artifact_path": str(target_dir / "receipt.json"),
            })
        except Exception as error:
            receipts.append({
                "provider": provider,
                "classification": "observation_error",
                "next_route": "gmail_fallback_required",
                "grounded_action_count": 0,
                "blocker_count": 1,
                "error_type": type(error).__name__,
            })
        finally:
            page.close()
    observed = {
        receipt["provider"] for receipt in receipts if "error_type" not in receipt
    }
    return {
        "version": 1,
        "status": "complete" if observed == REQUIRED_PROVIDERS else "failed",
        "request_id": request_id,
        "owner_lease_id": lease_id,
        "owner_fence": fence,
        "provider_count": len(observed),
        "navigation_count": len(receipts),
        "submit_count": 0,
        "email_send_count": 0,
        "targets": receipts,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--owner-receipt", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--materials-root", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    owner = json.loads(args.owner_receipt.read_text(encoding="utf-8"))
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        receipt = run_surface_canary(
            request=request, owner_receipt=owner, profile=profile,
            materials_root=args.materials_root, evidence_dir=args.evidence_dir,
            playwright=playwright,
        )
    _private_write(args.output, receipt)
    print(json.dumps({
        "status": receipt["status"], "provider_count": receipt["provider_count"],
        "submit_count": 0, "email_send_count": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
