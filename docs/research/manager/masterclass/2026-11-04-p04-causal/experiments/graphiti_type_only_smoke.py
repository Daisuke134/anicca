"""Run the REAL Graphiti 0.31.2 package without a database, LLM or internet.

Validates node/edge data models only. This is NOT Graphiti graph ingestion,
hybrid retrieval, memory performance, semantic linking or production deployment.

Isolated Python 3.12:
  /tmp/manager-graphiti-isolated-20261104/bin/python graphiti_type_only_smoke.py
Graphiti install required one explicit 'httpx' package after official base install.
"""
from __future__ import annotations

from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch
import json

from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge

def run() -> dict:
    now=datetime(2026,11,4,tzinfo=timezone.utc)
    with patch("socket.socket.connect",side_effect=RuntimeError("Network forbidden")):
        source=EntityNode(
            name="synthetic:person-x",
            uuid="synthetic:person-x",
            group_id="synthetic-research",
            created_at=now,
        )
        target=EntityNode(
            name="synthetic:goal-x",
            uuid="synthetic:goal-x",
            group_id="synthetic-research",
            created_at=now,
        )
        edge=EntityEdge(
            uuid="synthetic:edge-x",
            source_node_uuid=source.uuid,
            target_node_uuid=target.uuid,
            name="HAS_GOAL",
            fact="This is a fabricated relation for package model validation",
            group_id="synthetic-research",
            created_at=now,
            valid_at=now,
        )
        dumped=[source.model_dump(mode="json"),target.model_dump(mode="json"),edge.model_dump(mode="json")]
    assert edge.source_node_uuid==source.uuid and edge.target_node_uuid==target.uuid
    assert edge.valid_at==now
    return {
        "library":"getzep/graphiti",
        "installed_version":version("graphiti-core"),
        "scope":"offline data model instantiation ONLY; no Graphiti retrieval / add_episode / add_triplet",
        "nodes":len(dumped)-1,"edges":1,
        "class_names":["EntityNode","EntityEdge"],
        "edge_temporal_fields":sorted([k for k in dumped[-1] if "at" in k]),
        "third_party_database_running":False,
        "remote_llm_calls":0,
        "socket_connect_blocked":True,
        "manual_missing_dependency_installed":"httpx",
        "note":"Graphiti full runtime requires a supported graph backend and embedding/LLM configuration",
        "license":"Apache-2.0 (upstream repository LICENSE)",
        "real_human_claim":False,
    }

if __name__=="__main__":
    report=run()
    target=Path(__file__).resolve().parent.parent/"evidence/GRAPHITI_REAL_PACKAGE_TYPE_SMOKE.json"
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
