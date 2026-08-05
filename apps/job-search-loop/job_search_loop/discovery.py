from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from .state import canonical_job_id, canonical_url


@dataclass(frozen=True)
class Provider:
    name: str
    command: tuple[str, ...]


def _results(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    candidates = payload.get("results")
    if not isinstance(candidates, list):
        data = payload.get("data")
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
            candidates = data.get("results")
    if not isinstance(candidates, list):
        return []
    normalized = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        row = dict(candidate)
        description = row.get("description") or row.get("markdown")
        if isinstance(description, str):
            row["description"] = description[:4_000]
            row.pop("markdown", None)
        normalized.append(row)
    return normalized


def search_jobs(
    query: str,
    *,
    providers: Sequence[Provider],
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise ValueError("query is required")
    attempts = []
    combined_by_url: dict[str, dict[str, Any]] = {}
    for provider in providers:
        try:
            completed = subprocess.run(
                list(provider.command),
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            attempts.append(
                {
                    "name": provider.name,
                    "status": "failed",
                    "count": 0,
                    "error": f"timed out after {timeout_seconds}s",
                    "results": [],
                }
            )
            continue
        if completed.returncode != 0:
            attempts.append(
                {
                    "name": provider.name,
                    "status": "failed",
                    "count": 0,
                    "error": (
                        completed.stderr.strip()[-500:]
                        or f"provider returned rc={completed.returncode}"
                    ),
                    "results": [],
                }
            )
            continue
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            attempts.append(
                {
                    "name": provider.name,
                    "status": "failed",
                    "count": 0,
                    "error": "provider returned invalid JSON",
                    "results": [],
                }
            )
            continue
        rows = _results(payload)
        enriched_rows = []
        for row in rows:
            company = str(row.get("company", "")).strip()
            title = str(row.get("title", "")).strip()
            url = str(row.get("url", "")).strip()
            if not company or not title or not url:
                continue
            normalized_url = canonical_url(url)
            enriched = {
                **row,
                "canonical_url": normalized_url,
                "canonical_job_id": canonical_job_id(company, title, normalized_url),
                "discovery_provider": provider.name,
            }
            existing = combined_by_url.get(normalized_url)
            if existing is None or (
                existing.get("source_kind") != "official"
                and enriched.get("source_kind") == "official"
            ):
                combined_by_url[normalized_url] = enriched
            enriched_rows.append(enriched)
        attempts.append(
            {
                "name": provider.name,
                "status": "success" if enriched_rows else "empty",
                "count": len(enriched_rows),
                "error": None,
                "results": enriched_rows,
            }
        )
    combined = list(combined_by_url.values())
    total = len(combined)
    needs_browser = total == 0
    return {
        "version": 1,
        "query": query,
        "status": "browser_fallback_required" if needs_browser else "usable",
        "requires_browser_fallback": needs_browser,
        "usable_result_count": total,
        "results": combined,
        "providers": attempts,
    }


def _default_providers(
    query: str, *, app_root: Path, framework_root: Path
) -> tuple[Provider, ...]:
    return (
        Provider(
            "firecrawl",
            ("/bin/zsh", str(app_root / "scripts" / "firecrawl-search.sh"), query),
        ),
    )


def _ensure_framework(app_root: Path, framework_root: Path) -> str | None:
    required = (
        framework_root / ".agents/skills/freehire-search/cli/src/cli.ts",
        framework_root / ".agents/skills/linkedin-search/cli/src/cli.ts",
    )
    if all(path.is_file() for path in required):
        return None
    completed = subprocess.run(
        ["/bin/zsh", str(app_root / "scripts" / "bootstrap-framework.sh")],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode == 0 and all(path.is_file() for path in required):
        return None
    return (
        completed.stderr.strip()[-500:]
        or f"framework bootstrap returned rc={completed.returncode}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--framework-root",
        type=Path,
        default=Path(
            os.environ.get(
                "JOB_SEARCH_FRAMEWORK_ROOT",
                Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
                / "anicca/job-search/framework",
            )
        ),
    )
    args = parser.parse_args()
    app_root = Path(__file__).resolve().parents[1]
    framework_root = args.framework_root.expanduser().resolve()
    bootstrap_error = None
    result = search_jobs(
        args.query,
        providers=_default_providers(
            args.query, app_root=app_root, framework_root=framework_root
        ),
    )
    result["framework_bootstrap_error"] = bootstrap_error
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        args.output.write_text(encoded, encoding="utf-8")
        os.chmod(args.output, 0o600)
    print(encoded, end="")


if __name__ == "__main__":
    main()
