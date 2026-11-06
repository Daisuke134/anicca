"""End-to-end fixture pipeline: actual EDSL package -> typed evidence -> 4 read-only query backends -> NO_ACTION.

This is an architectural integration test. All agents, survey responses, sources,
receipts and outcomes are synthetic. EDSL uses the canned test model and
socket connections are blocked for the whole pipeline. Manager Core is
imported, not reimplemented. No model "prediction" is empirical evidence.

Run with the isolated EDSL Python3.12 venv:
  /tmp/manager-edsl-isolated-20261104/bin/python p05_1_integrated_offline_demo.py
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import json
from edsl import Agent, QuestionFreeText, Model, Survey
from p05_1_ontology_readonly import make_event,project,as_jsonld,existing_state_machine_example
from p05_1_four_way_benchmark import FlatScan,DictIndex,SQLiteIndex,GraphProjection,Question

STAMP="2026-11-04T08:00:00Z"
END="2026-11-04T09:00:00Z"
PERSON="synthetic:subject-00010"
ACTION="synthetic:action-00010"

def edsl_fixture():
    question=QuestionFreeText(
        question_name="reported_goal",
        question_text="In a completely fictional study, what harmless goal does the imaginary subject report?")
    results=Survey([question]).by(Agent(traits={"identity":"entirely_synthetic"})).by(
        Model("test",canned_response="Finish one fictional practice task")
    ).run(disable_remote_inference=True,disable_remote_cache=True,cache=False)
    answers=results.select("answer.reported_goal").to_dicts()
    assert answers==[{"reported_goal":"Finish one fictional practice task"}]
    return answers[0]["reported_goal"]


def events_from_edsl(answer: str):
    def make(*, subject, subject_kind, predicate, object, object_kind, source_id,
             source_kind, evidence, confidence=None,verifier=None,executor=None):
        return make_event(
            subject=subject,subject_kind=subject_kind,predicate=predicate,
            object=object,object_kind=object_kind,
            source_fact_id=source_id,source_kind=source_kind,
            observed_at=STAMP,recorded_at=STAMP,valid_from=STAMP,
            evidence_text=evidence,confidence=confidence,verifier=verifier,executor=executor
        )
    return [
        make(subject=PERSON,subject_kind="Subject",predicate="HAS_GOAL",
             object="synthetic:goal-00010",object_kind="Goal",
             source_id="synthetic:edsl-result-00010",source_kind="synthetic_observation",
             evidence=f"canned EDSL response: {answer}"),
        make(subject=PERSON,subject_kind="Subject",predicate="HAS_OBSERVATION",
             object="synthetic:observation-00010",object_kind="Observation",
             source_id="synthetic:edsl-observation-00010",source_kind="synthetic_observation",
             evidence="artificial survey observation only"),
        make(subject=PERSON,subject_kind="Subject",predicate="PROPOSED_ACTION",
             object=ACTION,object_kind="Action",source_id="synthetic:proposal-00010",
             source_kind="synthetic_model_inference",
             evidence="simulated candidate; not approved",confidence=.55),
        make(subject="synthetic:receipt-00010",subject_kind="Receipt",predicate="RECEIPT_FOR",
             object=ACTION,object_kind="Action",source_id="synthetic:fake-receipt-00010",
             source_kind="synthetic_provider_receipt",evidence="fabricated receipt, no external message"),
        make(subject="synthetic:outcome-00010",subject_kind="Outcome",
             predicate="INDEPENDENT_READBACK_FOR",object=ACTION,object_kind="Action",
             source_id="synthetic:fake-readback-00010",
             source_kind="synthetic_independent_readback",evidence="fabricated readback, not causal proof",
             verifier="synthetic:observer",executor="synthetic:executor"),
    ]


def run():
    # Deny all socket connections, even if a future code change removes EDSL's
    # remote inference flags. This is NOT a security sandbox for untrusted code.
    with patch("socket.socket.connect",side_effect=RuntimeError("NETWORK_FORBIDDEN")):
        answer=edsl_fixture()
        events=events_from_edsl(answer)
        projection=project(events,knowledge_cutoff=END,world_time=END)
        machines={
            "flat_scan":FlatScan(events),
            "dict_index":DictIndex(events,END,END),
            "sqlite_index":SQLiteIndex(events),
            "graph_projection":GraphProjection(events,END,END),
        }
        questions={
            "goal":("synthetic:goal-00010",),
            "proposals":(ACTION,),
            "receipts":("synthetic:receipt-00010",),
            "readbacks":("synthetic:outcome-00010",),
            "authority":("NO_AUTHORITY",),
            "causal_effect":("NO_CAUSAL_PROOF",),
        }
        answers={}
        for name in machines:
            answers[name]={}
            for q,expected in questions.items():
                result=machines[name].ask(Question(q,PERSON,END,END))
                if result!=expected:raise AssertionError((name,q,result,expected))
                answers[name][q]=list(result)
        machines["sqlite_index"].close()
        no_action=existing_state_machine_example()
        if no_action["causal_unsupported_choice"]!="NO_ACTION":
            raise AssertionError("Core privilege/causal evidence boundary failed")
    return {
        "scope":"synthetic E2E pipeline with real EDSL library and Manager Core",
        "edsl_response":answer,
        "n_events":len(events),
        "query_backends":list(machines),
        "truth_checked_queries":len(questions),
        "answers":answers,
        "epistemic_statuses":sorted({x["epistemic_status"] for x in projection["edges"]}),
        "jsonld_assertion_nodes":len(as_jsonld(projection)["@graph"]),
        "manager_state_machine":no_action,
        "external_calls":0,"real_customers":0,"real_interventions":0,
        "has_external_billing":False,
        "can_authorize_execution":projection["can_authorize_execution"],
        "can_claim_human_effect":projection["can_prove_real_world_effect"],
        "limitations":"EDSL canned response and synthetic receipts do not prove human-behavior forecasting",
    }


if __name__=="__main__":
    out=run()
    target=Path(__file__).resolve().parents[1]/"evidence/P05-1_OFFLINE_END_TO_END_SYNTHETIC.json"
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))
