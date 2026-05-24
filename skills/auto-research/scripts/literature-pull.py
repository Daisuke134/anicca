#!/usr/bin/env python3
"""literature-pull.py — pull arXiv + Semantic Scholar + OpenAlex for a project.

Calls into K-Dense `paper-lookup` and `database-lookup` (via the AutoResearchClaw chassis
adapters at researchclaw.literature). In DRY_RUN mode it prints the planned queries
and writes a stub literature JSON.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

WORKSPACE = Path(os.path.expanduser("~/.openclaw/workspace/auto-research"))
DRY_RUN = os.environ.get("AUTO_RESEARCH_DRY_RUN", "false").lower() == "true"
CHASSIS = Path(os.path.expanduser("~/.openclaw/workspace/AutoResearchClaw"))


def main(project: dict) -> int:
    pid = project["id"]
    cats = project.get("arxiv_categories") or []
    out_dir = WORKSPACE / "literature" / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    out_path = out_dir / f"{today}.json"

    queries = [
        {"source": "arxiv", "categories": cats, "query": project.get("title", pid)},
        {"source": "semantic_scholar", "query": project.get("title", pid), "limit": 25},
        {"source": "openalex", "filter": f"concepts.display_name.search:{project.get('title', pid)}"},
    ]

    if DRY_RUN:
        print(f"literature-pull[{pid}][DRY_RUN]: would issue {len(queries)} queries:")
        for q in queries:
            print(f"  - {q['source']}: {q}")
        out_path.write_text(json.dumps({"project": pid, "queries": queries, "results": [], "stub": True}, indent=2))
        print(f"literature-pull[{pid}][DRY_RUN]: wrote stub {out_path}")
        return 0

    # Live path: use the chassis's search_papers (unified search across arXiv + S2 + OpenAlex).
    sys.path.insert(0, str(CHASSIS))
    try:
        from researchclaw.literature import search_papers  # type: ignore
    except Exception as e:
        print(f"literature-pull[{pid}]: chassis import failed ({e}). Writing query plan only.")
        out_path.write_text(json.dumps({"project": pid, "queries": queries, "error": str(e)}, indent=2))
        return 1

    results = []
    title = project.get("title", pid)
    try:
        papers = search_papers(query=title, limit=25)
        results = [
            {
                "title": getattr(p, "title", None),
                "authors": [getattr(a, "name", str(a)) for a in (getattr(p, "authors", []) or [])],
                "year": getattr(p, "year", None),
                "abstract": getattr(p, "abstract", None),
                "doi": getattr(p, "doi", None),
                "openalex_id": getattr(p, "openalex_id", None),
                "arxiv_id": getattr(p, "arxiv_id", None),
                "source": getattr(p, "source", None),
            }
            for p in (papers or [])
        ]
    except Exception as e:
        print(f"literature-pull[{pid}]: search_papers failed ({e}). Writing query plan only.")
        out_path.write_text(json.dumps({"project": pid, "queries": queries, "error": str(e)}, indent=2))
        return 1

    out_path.write_text(json.dumps({"project": pid, "queries": queries, "results": results}, indent=2, ensure_ascii=False))
    print(f"literature-pull[{pid}]: wrote {len(results)} records → {out_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: literature-pull.py <project-json>", file=sys.stderr); raise SystemExit(64)
    blob = json.loads(sys.argv[1])
    raise SystemExit(main(blob["project"]))
