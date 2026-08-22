from __future__ import annotations

import argparse
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


def build_context(*, state_root: Path, profile_path: Path, resume_path: Path, cdp_url: str) -> dict[str, Any]:
    ledger = state_root / "applications.jsonl"
    return {
        "operator_id": os.environ.get("MERCOR_OPERATOR_ID", "default"),
        "state_root": str(state_root.resolve()),
        "profile_path": str(profile_path.expanduser().resolve()),
        "resume_path": str(resume_path.expanduser().resolve()),
        "applications_ledger": str(ledger.resolve()),
        "submitted_listing_ids": _ledger_listing_ids(ledger),
        "cdp_url": cdp_url,
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
        ),
        workdir=args.workdir,
        run_id=args.run_id,
    )
    output = args.evidence_dir / "mercor-pass-summary.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(output, 0o600)
    print(json.dumps({"status": result.get("status"), "result_path": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
