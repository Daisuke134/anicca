"""Pinned Browser Use pre-submit runner for the resident CloakBrowser owner."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .ats import build_non_submit_fill_plan, evaluate_snapshot, execute_non_submit_fill_plan
from .browser_use_adapter import AuthorizedBrowserUseAdapter, PinnedBrowserUseBackend
from .playwright_ats import (
    _application_url,
    attempt_ranked_candidates,
    grounded_profile_answers,
    ranked_pre_submit_candidates,
)
from .resume_routing import select_resume


def _private_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def run_pre_submit(
    *,
    owner_receipt: dict[str, Any],
    prefilter_result: Path,
    profile_path: Path,
    materials_root: Path,
    evidence_dir: Path,
    backend_factory: Any = PinnedBrowserUseBackend,
) -> dict[str, Any]:
    candidates = ranked_pre_submit_candidates(
        json.loads(prefilter_result.read_text(encoding="utf-8")), limit=3
    )
    if not candidates:
        return {"status": "pending_verification", "blocked": ["no_ranking_ready_candidate"]}
    endpoint = owner_receipt.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint:
        return {"status": "pending_verification", "blocked": ["browser_owner_endpoint_missing"]}
    domains = sorted(
        {
            str(urlparse(str(candidate.get("official_url") or "")).hostname or "").lower()
            for candidate in candidates
        }
        - {""}
    )
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    backend = backend_factory(endpoint, allowed_domains=domains)
    adapter = AuthorizedBrowserUseAdapter(backend, owner_receipt=owner_receipt)
    try:
        backend.connect()

        def attempt(candidate: dict[str, Any]) -> dict[str, Any]:
            url = str(candidate.get("official_url") or "")
            provider = str(candidate.get("provider") or "")
            if not provider:
                from .ats import detect_provider

                provider = detect_provider(url)
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
            candidate_evidence = evidence_dir / digest
            adapter.navigate(_application_url(url, provider))
            snapshot = adapter.snapshot()
            snapshot_path = candidate_evidence / "ats-snapshot.json"
            _private_write(snapshot_path, snapshot)
            snapshot_sha256 = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
            evaluation = evaluate_snapshot(snapshot)
            _private_write(candidate_evidence / "ats-evaluation.json", evaluation)
            before = adapter.capture_evidence("before", candidate_evidence)
            if not evaluation["claim_ready"]:
                terminal = adapter.capture_evidence("terminal", candidate_evidence)
                _private_write(
                    candidate_evidence / "browser-use-evidence.json",
                    {"before": before, "terminal": terminal},
                )
                return {
                    "claim_ready": False,
                    "blockers": list(evaluation.get("blockers") or ["application_surface_not_ready"]),
                }
            posting_text = " ".join(str(value) for value in candidate.get("source_spans", []))
            routed = select_resume(
                posting_text=posting_text,
                role_family=str(candidate.get("role_family") or "unknown"),
                materials_root=materials_root,
                posting_language=str(candidate.get("language") or "en"),
            )
            plan = build_non_submit_fill_plan(
                snapshot,
                answers=grounded_profile_answers(profile),
                resume_path=routed["resume_path"],
                resume_sha256=routed["resume_sha256"],
            )
            receipt = execute_non_submit_fill_plan(
                plan,
                adapter=adapter,
                owner_receipt=owner_receipt,
                snapshot_sha256=snapshot_sha256,
                screenshot_path=candidate_evidence / "pre-submit.png",
                receipt_path=candidate_evidence / "fill-receipt.json",
            )
            after = adapter.capture_evidence("after", candidate_evidence)
            terminal = adapter.capture_evidence("terminal", candidate_evidence)
            _private_write(
                candidate_evidence / "browser-use-evidence.json",
                {"before": before, "after": after, "terminal": terminal},
            )
            return {
                "claim_ready": receipt["status"] == "claim_ready",
                "blockers": [f"pre_submit_blocked:{item}" for item in receipt.get("blockers", [])],
            }

        return attempt_ranked_candidates(candidates, attempt)
    except Exception as error:
        return {
            "status": "pending_verification",
            "blocked": [f"browser_use_pre_submit_error:{type(error).__name__}"],
        }
    finally:
        backend.close()
