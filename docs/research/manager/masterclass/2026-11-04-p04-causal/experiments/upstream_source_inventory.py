"""Auditable inventory of upstream repositories inspected; no source is vendored.

Run with --upstreams pointing to local public clones. Writes only a small JSON
record of licenses, commit hashes and observed source-code entry points.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from subprocess import check_output
from argparse import ArgumentParser
import json

REPOS = {
    "expectedparrot/edsl": {
        "dir": "edsl", "license": "MIT",
        "inspected": ["edsl/agents/Agent.py", "edsl/surveys/Survey.py",
                      "edsl/language_models/Model.py", "pyproject.toml"],
        "actual_run": "EDSL==1.0.9 with canned test model, no remote inference",
        "requires_provider_credentials_for_actual_model": True,
        "licensing_notes": "MIT package; hosted services and external models have independent terms",
    },
    "getzep/graphiti": {
        "dir": "graphiti", "license": "Apache-2.0",
        "inspected": ["graphiti_core/graphiti.py", "graphiti_core/nodes.py",
                      "graphiti_core/edges.py", "pyproject.toml"],
        "actual_run": "graphiti-core==0.31.2 EntityNode/EntityEdge ONLY",
        "full_graph_runtime": "NOT RUN; graph DB plus LLM/embedding required",
        "requires_provider_credentials_for_actual_model": True,
        "licensing_notes": "Apache code; supporting hosted LLM, graph DB and embeddings cost and licenses separate",
    },
    "HumanBehaviourChangeProject/ontologies": {
        "dir": "ontologies", "license": "CC BY 4.0",
        "inspected": ["bcio.owl", "README.md"],
        "actual_run": "parsed official OWL, class count and checked seven ontology labels",
        "requires_provider_credentials_for_actual_model": False,
        "licensing_notes": "CC BY requires attribution; imported ontology components may need notice inspection",
    },
    "666ghj/MiroFish": {
        "dir": "MiroFish", "license": "AGPL-3.0",
        "inspected": ["README.md", "backend/app/services/ontology_generator.py",
                      "backend/app/services/graph_builder.py",
                      "backend/app/services/oasis_profile_generator.py",
                      "backend/app/services/simulation_manager.py",
                      "backend/app/services/simulation_runner.py"],
        "actual_run": "source inspected only; NO Zep/LLM/OASIS simulation executed",
        "requires_provider_credentials_for_actual_model": True,
        "licensing_notes": "AGPLv3 requires legal distribution/network obligations review when modifying/serving",
    },
    "camel-ai/oasis": {
        "dir": "oasis", "license": "Apache-2.0",
        "inspected": ["README.md", "oasis/social_agent/agent.py",
                      "oasis/social_platform/platform.py",
                      "oasis/environment/env.py"],
        "actual_run": "source inspected only; NO multi-agent live simulation",
        "requires_provider_credentials_for_actual_model": True,
        "licensing_notes": "Apache source code; real LLM runtime and datasets independently governed",
    },
    "palantir/foundry-platform-python": {
        "dir": "foundry-platform-python", "license": "Apache-2.0 (SDK only)",
        "inspected": ["README.md", "pyproject.toml", "foundry_sdk"],
        "actual_run": "source/SDK metadata inspected; NO Foundry API request",
        "requires_provider_credentials_for_actual_model": True,
        "licensing_notes": "Open SDK is NOT an open Palantir Ontology backend; tenant and API rights separate",
    },
}

def run(base: Path) -> dict:
    report = {
        "date": "2026-11-04",
        "type": "read-only source and license inventory",
        "not_a_license_opinion": True,
        "no_live_user_data": True,
        "upstreams": {},
        "listen_labs_api": {
            "official_docs": "https://docs.listenlabs.com/api-v2/overview",
            "documented_product": "Study API (draft, launch, responses)",
            "documented_authentication": "x-api-key organization scoped",
            "documented_launch_cost": "wallet project credits",
            "twins_human_prediction_endpoint_publicly_verified": False,
            "credentialed_request_executed": False,
            "anonymous_read_only_get_wallets_http_status": 401,
            "anonymous_error_code": "missing_api_key",
            "no_credential_no_real_interview": True,
            "license": "Proprietary SaaS; verify contract and data-use terms",
        },
    }
    for repo, spec in REPOS.items():
        location=base/spec["dir"]
        revision=check_output(["git","-C",str(location),"rev-parse","HEAD"],
                              text=True).strip()
        original=(location/"LICENSE").read_bytes()
        for path in spec["inspected"]:
            target=location/path
            if not target.exists():
                raise AssertionError((repo,path))
        report["upstreams"][repo]={
            "source":f"https://github.com/{repo}",
            "revision":revision,
            "license":spec["license"],
            "license_sha256":sha256(original).hexdigest(),
            "inspected_files":spec["inspected"],
            **{k:v for k,v in spec.items() if k not in ("dir","license","inspected")},
        }
    return report

if __name__=="__main__":
    parser=ArgumentParser()
    parser.add_argument("--upstreams",type=Path,required=True)
    args=parser.parse_args()
    output=run(args.upstreams)
    evidence=Path(__file__).resolve().parent.parent/"evidence/UPSTREAM_CODE_AND_LICENSE_AUDIT.json"
    evidence.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(output,ensure_ascii=False,indent=2))
