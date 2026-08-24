from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from .agent_runner import AgentRunner, wrap_untrusted
from .state import is_excluded_employer


_FIELDS = {"company", "host", "tenant", "site"}


def validate_sources(value: dict[str, Any]) -> tuple[dict[str, str], ...]:
    rows = value.get("sources") if isinstance(value, dict) else None
    if not isinstance(rows, list):
        raise ValueError("sources must be an array")
    accepted = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != _FIELDS:
            raise ValueError("source fields do not match the contract")
        source = {key: str(row[key]).strip() for key in _FIELDS}
        host = source["host"].casefold()
        if (
            not source["company"]
            or is_excluded_employer(source["company"])
            or not host.endswith(".myworkdayjobs.com")
            or "/" in host
            or not re.fullmatch(r"[A-Za-z0-9_-]+", source["tenant"])
            or not re.fullmatch(r"[A-Za-z0-9_-]+", source["site"])
        ):
            continue
        source["host"] = host
        identity = (host, source["tenant"], source["site"])
        if identity in seen:
            continue
        seen.add(identity)
        accepted.append(source)
    if not accepted:
        raise ValueError("model returned no valid non-excluded Workday sources")
    return tuple(accepted)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-memory", required=True, type=Path)
    parser.add_argument("--runner", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--evidence-root", required=True, type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    previous = ""
    if args.previous and args.previous.is_file():
        previous = args.previous.read_text(encoding="utf-8")
    memory = args.candidate_memory.read_text(encoding="utf-8")
    prompt = (
        "Act as the source-discovery agent for a Tokyo-based autonomous job hunter. "
        "Use available internet/search tools now. Find diverse companies currently "
        "hiring in Tokyo, Japan-remote, or Japan-compatible global remote through "
        "official Workday career sites. Do not choose jobs or judge candidate fit. "
        "Return the exact CXS source identity needed to query each official site: "
        "company, myworkdayjobs host, tenant, and site. Validate each against its "
        "official HTTPS Workday page or CXS endpoint. Do not return excluded employers "
        "from candidate memory. Do not limit results to companies seen previously. "
        "Return only the schema.\n\n"
        + wrap_untrusted("candidate_memory", memory)
        + ("\n\n" + wrap_untrusted("previous_sources", previous) if previous else "")
    )
    runner = AgentRunner(evidence_root=args.evidence_root, runner_path=args.runner)
    result = runner.run(
        task="improve",
        prompt=prompt,
        schema_path=args.schema,
        workdir=args.workdir,
        run_id=f"workday-sources-{uuid.uuid4().hex}",
    )
    sources = validate_sources(result)
    output = {"version": 1, "sources": list(sources)}
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(args.output, 0o600)
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
