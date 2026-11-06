"""Expected Parrot EDSL REAL library smoke test, test model ONLY.

No credentials, remote LLM, Listen Labs, survey participants, or paid API.
Isolated runtime: Python 3.12 and edsl==1.0.9.
The fixed canned responses demonstrate EDSL orchestration, NOT human prediction.

Run:
  /tmp/manager-edsl-isolated-20261104/bin/python edsl_local_smoke.py
"""
from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch
import json

from edsl import Agent, AgentList, Model, QuestionFreeText, Survey

def run() -> dict:
    agents = AgentList([
        Agent(traits={"group": "synthetic_one", "category": "fictional"}),
        Agent(traits={"group": "synthetic_two", "category": "fictional"}),
        Agent(traits={"group": "synthetic_three", "category": "fictional"}),
    ])
    question = QuestionFreeText(
        question_name="synthetic_feedback",
        question_text="What could improve an entirely fictional service?",
    )
    survey = Survey([question])
    test_model = Model("test", canned_response="OFFLINE_TEST_MODEL_NOT_HUMAN")
    # Defense in depth: refuse all network socket connections during the run.
    with patch("socket.socket.connect", side_effect=RuntimeError("network forbidden")):
        results = survey.by(agents).by(test_model).run(
            disable_remote_inference=True,
            disable_remote_cache=True,
            cache=False,
        )
    answers=results.select("answer.synthetic_feedback").to_dicts()
    if len(answers)!=3 or not all(
        a["synthetic_feedback"]=="OFFLINE_TEST_MODEL_NOT_HUMAN" for a in answers
    ):
        raise AssertionError("EDSL offline test behavior changed")
    return {
        "library": "expectedparrot/edsl",
        "installed_version": version("edsl"),
        "mode": "REAL EDSL PACKAGE; SYNTHETIC CANNED TEST MODEL",
        "n_fake_agents": len(agents),
        "questions": 1,
        "canned_model_answers": answers,
        "external_model_requests": 0,
        "remote_inference": False,
        "remote_cache": False,
        "tokens_billed": 0,
        "network_socket_connect_forbidden": True,
        "human_validity_claim": False,
        "license": "MIT (repository checked separately)",
    }

if __name__ == "__main__":
    report = run()
    out = Path(__file__).resolve().parent.parent/"evidence/EDSL_OFFLINE_REAL_PACKAGE_SMOKE.json"
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
