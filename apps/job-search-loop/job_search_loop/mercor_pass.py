from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

from .agent_runner import AgentRunner
from .mercor_provider import run_pass


def _ledger_listing_ids(path: Path) -> list[str]:
    if not path.is_file():
        return []
    identifiers: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict):
            continue
        listing_id = value.get("listing_id")
        if isinstance(listing_id, str) and listing_id.strip():
            identifiers.append(listing_id.strip())
    return sorted(set(identifiers))


def persist_verified_submissions(
    result: dict[str, Any], ledger_path: Path, *, run_id: str
) -> int:
    """Append verified model submissions once after evidence validation."""
    submitted = result.get("submitted")
    if not isinstance(submitted, list) or not submitted:
        return 0
    existing_ids = set(_ledger_listing_ids(ledger_path))
    existing_urls: set[str] = set()
    if ledger_path.is_file():
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict) and isinstance(value.get("application_url"), str):
                existing_urls.add(value["application_url"].strip())

    rows: list[dict[str, str]] = []
    for item in submitted:
        if not isinstance(item, dict):
            continue
        listing_id = str(item.get("listing_id", "")).strip()
        application_url = str(item.get("evidence_url") or item.get("url") or "").strip()
        if not listing_id or not application_url:
            continue
        if listing_id in existing_ids or application_url in existing_urls:
            continue
        rows.append(
            {
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "listing_id": listing_id,
                "title": str(item.get("title", "")).strip(),
                "application_url": application_url,
                "status": "submitted_pending_review",
                "evidence_screenshot": str(item.get("evidence_path", "")).strip(),
                "run_id": run_id,
            }
        )
        existing_ids.add(listing_id)
        existing_urls.add(application_url)
    if not rows:
        return 0

    ledger_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(ledger_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        payload = "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
        ).encode("utf-8")
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.chmod(ledger_path, 0o600)
    return len(rows)


def build_context(
    *,
    state_root: Path,
    profile_path: Path,
    resume_path: Path,
    cdp_url: str,
    evidence_dir: Path | None = None,
) -> dict[str, Any]:
    ledger = state_root / "applications.jsonl"
    context = {
        "operator_id": os.environ.get("MERCOR_OPERATOR_ID", "default"),
        "state_root": str(state_root.resolve()),
        "profile_path": str(profile_path.expanduser().resolve()),
        "resume_path": str(resume_path.expanduser().resolve()),
        "applications_ledger": str(ledger.resolve()),
        "submitted_listing_ids": _ledger_listing_ids(ledger),
        "cdp_url": cdp_url,
    }
    if evidence_dir is not None:
        context["evidence_dir"] = str(evidence_dir.expanduser().resolve())
    return context


def validate_evidence_paths(result: dict[str, Any], evidence_root: Path) -> None:
    """Reject model evidence that escapes the private directory for this pass.

    Empty paths are allowed for a read-only pass that produced no artifact. Any
    non-empty path must resolve to an existing regular file beneath the current
    pass root; this prevents stale evidence from an older run being accepted as
    proof for the current run.
    """
    root = evidence_root.expanduser().resolve()
    evidence = result.get("evidence")
    if not isinstance(evidence, dict):
        return

    candidates: list[tuple[str, str]] = []
    for field in ("screenshot_path", "dom_path"):
        value = evidence.get(field)
        if isinstance(value, str) and value.strip():
            candidates.append((f"evidence.{field}", value.strip()))

    submitted = result.get("submitted")
    if isinstance(submitted, list):
        for index, item in enumerate(submitted):
            if not isinstance(item, dict):
                continue
            value = item.get("evidence_path")
            if isinstance(value, str) and value.strip():
                candidates.append((f"submitted[{index}].evidence_path", value.strip()))

    if submitted and not candidates:
        raise ValueError("submitted_result_missing_evidence_path")

    for label, raw_path in candidates:
        resolved = Path(raw_path).expanduser().resolve()
        try:
            resolved.relative_to(root)
        except ValueError as error:
            raise ValueError(f"{label}_outside_current_pass") from error
        if not resolved.is_file():
            raise ValueError(f"{label}_missing")


def _blocked_for_evidence_violation(
    result: dict[str, Any], evidence_dir: Path, error: ValueError
) -> dict[str, Any]:
    """Preserve a rejected model result privately while keeping the wake reportable."""
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(evidence_dir, 0o700)
    violation_path = evidence_dir / "evidence-validation-error.json"
    violation_path.write_text(
        json.dumps({"error": str(error), "agent_result": result}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    os.chmod(violation_path, 0o600)
    evidence = result.get("evidence") if isinstance(result.get("evidence"), dict) else {}
    blocked = result.get("blocked") if isinstance(result.get("blocked"), list) else []
    needs_human = result.get("needs_human") if isinstance(result.get("needs_human"), list) else []
    inspected = result.get("inspected_listings") if isinstance(result.get("inspected_listings"), list) else []
    return {
        "status": "blocked",
        "inspected_listings": inspected,
        "submitted": [],
        "needs_human": needs_human,
        "blocked": [*blocked, f"evidence_validation:{error}"],
        "evidence": {
            "page_url": evidence.get("page_url", ""),
            "screenshot_path": "",
            "dom_path": str(violation_path),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-root", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--resume", required=True, type=Path)
    parser.add_argument("--cdp-url", required=True)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    args.evidence_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    os.chmod(args.evidence_dir, 0o700)
    runner = AgentRunner(evidence_root=args.evidence_dir.parent)
    result = run_pass(
        runner=runner,
        prompt_path=args.prompt,
        schema_path=args.schema,
        context=build_context(
            state_root=args.state_root,
            profile_path=args.profile,
            resume_path=args.resume,
            cdp_url=args.cdp_url,
            evidence_dir=args.evidence_dir.parent / args.run_id,
        ),
        workdir=args.workdir,
        run_id=args.run_id,
    )
    try:
        validate_evidence_paths(result, args.evidence_dir.parent)
    except ValueError as error:
        result = _blocked_for_evidence_violation(result, args.evidence_dir, error)
    persist_verified_submissions(
        result, args.state_root / "applications.jsonl", run_id=args.run_id
    )
    output = args.evidence_dir / "mercor-pass-summary.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(output, 0o600)
    print(json.dumps({"status": result.get("status"), "result_path": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
