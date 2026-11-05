"""Fair, synthetic, reproducible comparison of three ontology-query strategies.

A: Append-only event list scanned for each query.
B: SQLite indexed materialized view, using the same public event fields.
C: Read-only temporal graph projection from P05-1 (NO Graphiti/Neo4j/LLMs).

Tests answer equivalence, temporal leakage, provenance, authority boundaries,
build cost vs read latency. All methods have exactly the same event stream,
allowed information, query semantics, and synthetic ground-truth oracle.
No real users, customer events, credentials, or live effects.

Run: python3 p05_1_three_way_benchmark.py
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from statistics import median
from time import perf_counter_ns
import gc
import json
import random
import sqlite3
import sys

from p05_1_ontology_readonly import (
    EvidenceEdge, existing_state_machine_example, instant, make_event, project,
)

BASE = instant("2026-11-04T08:00:00Z")
LATE = instant("2026-11-05T08:00:00Z")
CUTOFF = "2026-11-04T12:00:00Z"
WORLD_TIME = "2026-11-04T12:00:00Z"
FUTURE_CUTOFF = "2026-11-06T12:00:00Z"
KINDS = (
    ("HAS_GOAL", "Goal", "synthetic_observation"),
    ("HAS_OBSERVATION", "Observation", "synthetic_observation"),
    ("PROPOSED_ACTION", "Action", "synthetic_model_inference"),
)
EMPTY = ("NO_AUTHORITY", "NO_CAUSAL_PROOF")


@dataclass(frozen=True)
class Question:
    name: str
    subject: str
    cutoff: str = CUTOFF
    world_time: str = WORLD_TIME


def synthetic_events(n_subjects: int) -> list[EvidenceEdge]:
    """Generate 5-7 events per synthetic subject, with a few late observations.

    No personal information or data about actual individuals.
    """
    if n_subjects < 10 or n_subjects > 25_000:
        raise ValueError("subjects out of bounded synthetic range")
    result = []
    for i in range(n_subjects):
        subject = f"synthetic:subject-{i:05d}"
        action = f"synthetic:action-{i:05d}"
        timestamp = (BASE + timedelta(seconds=(i % 120))).isoformat()
        late = LATE.isoformat()
        for predicate, kind, source_kind in KINDS:
            suffix = predicate.lower().replace("_", "-")
            obj = action if predicate == "PROPOSED_ACTION" else f"synthetic:{kind.lower()}-{i:05d}"
            result.append(make_event(
                subject=subject, subject_kind="Subject", predicate=predicate,
                object=obj, object_kind=kind,
                source_fact_id=f"synthetic:fact-{suffix}-{i:05d}",
                source_kind=source_kind, observed_at=timestamp,
                recorded_at=timestamp, valid_from=timestamp,
                evidence_text=f"fabricated:{predicate}:{subject}",
                confidence=0.55 if source_kind == "synthetic_model_inference" else None,
            ))
        result.append(make_event(
            subject=f"synthetic:receipt-{i:05d}", subject_kind="Receipt",
            predicate="RECEIPT_FOR", object=action, object_kind="Action",
            source_fact_id=f"synthetic:fact-receipt-{i:05d}",
            source_kind="synthetic_provider_receipt",
            observed_at=timestamp, recorded_at=timestamp, valid_from=timestamp,
            evidence_text=f"fictional receipt {i} not an outcome",
        ))
        if i % 3:
            result.append(make_event(
                subject=f"synthetic:outcome-{i:05d}", subject_kind="Outcome",
                predicate="INDEPENDENT_READBACK_FOR", object=action, object_kind="Action",
                source_fact_id=f"synthetic:fact-readback-{i:05d}",
                source_kind="synthetic_independent_readback",
                observed_at=timestamp, recorded_at=timestamp, valid_from=timestamp,
                evidence_text=f"fictional independent readback {i} not causal proof",
                verifier="synthetic:verifier", executor="synthetic:executor",
            ))
        if i % 7 == 0:
            result.append(make_event(
                subject=subject, subject_kind="Subject",
                predicate="HAS_OBSERVATION",
                object=f"synthetic:observation-late-{i:05d}", object_kind="Observation",
                source_fact_id=f"synthetic:fact-late-{i:05d}",
                source_kind="synthetic_observation",
                observed_at=timestamp, recorded_at=late,
                valid_from=timestamp,
                evidence_text=f"fictional late-arriving observation {i}",
            ))
        if i % 11 == 0:
            result.append(make_event(
                subject=subject, subject_kind="Subject",
                predicate="HAS_OBSERVATION",
                object=f"synthetic:observation-future-{i:05d}", object_kind="Observation",
                source_fact_id=f"synthetic:fact-future-{i:05d}",
                source_kind="synthetic_observation",
                observed_at=late, recorded_at=late,
                valid_from=late,
                evidence_text=f"fictional future-only observation {i}",
            ))
    return result


def subject_action(subject: str) -> str:
    if not subject.startswith("synthetic:subject-"):
        raise ValueError("invalid synthetic subject")
    return subject.replace("subject-", "action-", 1)


def answer_from_edges(edges, question: Question) -> tuple[str, ...]:
    """One fixed query contract across all three backends."""
    q = question.name
    if q == "authority":
        return ("NO_AUTHORITY",)
    if q == "causal_effect":
        return ("NO_CAUSAL_PROOF",)
    if q == "goal":
        return tuple(sorted(e["object"] for e in edges
                            if e["subject"] == question.subject
                            and e["predicate"] == "HAS_GOAL"))
    if q == "observations":
        return tuple(sorted(e["object"] for e in edges
                            if e["subject"] == question.subject
                            and e["predicate"] == "HAS_OBSERVATION"))
    if q == "proposals":
        return tuple(sorted(e["object"] for e in edges
                            if e["subject"] == question.subject
                            and e["predicate"] == "PROPOSED_ACTION"))
    if q == "receipts":
        target = subject_action(question.subject)
        return tuple(sorted(e["subject"] for e in edges
                            if e["object"] == target and e["predicate"] == "RECEIPT_FOR"))
    if q == "readbacks":
        target = subject_action(question.subject)
        return tuple(sorted(e["subject"] for e in edges
                            if e["object"] == target and e["predicate"] == "INDEPENDENT_READBACK_FOR"))
    if q == "trace":
        action_ids = {e["object"] for e in edges
                      if e["subject"] == question.subject
                      and e["predicate"] == "PROPOSED_ACTION"}
        artifacts = {
            ("action", a) for a in action_ids
        } | {
            ("receipt", e["subject"]) for e in edges
            if e["object"] in action_ids and e["predicate"] == "RECEIPT_FOR"
        } | {
            ("readback", e["subject"]) for e in edges
            if e["object"] in action_ids
            and e["predicate"] == "INDEPENDENT_READBACK_FOR"
        }
        return tuple(sorted(f"{kind}:{identifier}" for kind, identifier in artifacts))
    raise ValueError(f"unknown query {q}")


class FlatScan:
    """No index, no graph: scan immutable event records afresh on every query."""
    def __init__(self, events: list[EvidenceEdge]):
        self.events = tuple(events)

    def ask(self, question: Question) -> tuple[str, ...]:
        if question.name in ("authority", "causal_effect"):
            return answer_from_edges((), question)
        cutoff = instant(question.cutoff)
        world = instant(question.world_time)
        eligible = [
            {"subject": e.subject, "predicate": e.predicate, "object": e.object}
            for e in self.events
            if instant(e.recorded_at) <= cutoff and instant(e.valid_from) <= world
        ]
        return answer_from_edges(eligible, question)


class SQLiteIndex:
    """In-memory SQLite query projection. No new production DB or API."""
    def __init__(self, events: list[EvidenceEdge]):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("""CREATE TABLE claims(
          id TEXT PRIMARY KEY, source TEXT, predicate TEXT, target TEXT,
          recorded_at TEXT, valid_from TEXT, source_fact_id TEXT
        )""")
        self.db.executemany(
            "INSERT OR IGNORE INTO claims VALUES(?,?,?,?,?,?,?)",
            [(e.event_id, e.subject, e.predicate, e.object,
              instant(e.recorded_at).isoformat(),
              instant(e.valid_from).isoformat(),
              e.source_fact_id)
             for e in events],
        )
        self.db.execute("CREATE INDEX source_query ON claims(source,predicate,recorded_at,valid_from)")
        self.db.execute("CREATE INDEX target_query ON claims(target,predicate,recorded_at,valid_from)")
        self.db.commit()

    def ask(self, question: Question) -> tuple[str, ...]:
        if question.name in ("authority", "causal_effect"):
            return answer_from_edges((), question)
        cutoff = instant(question.cutoff).isoformat()
        world = instant(question.world_time).isoformat()
        q = question.name
        if q in ("goal", "observations", "proposals"):
            label = {"goal":"HAS_GOAL","observations":"HAS_OBSERVATION",
                     "proposals":"PROPOSED_ACTION"}[q]
            return tuple(sorted(row[0] for row in self.db.execute(
                "SELECT target FROM claims WHERE source=? AND predicate=? "
                "AND recorded_at<=? AND valid_from<=?",
                (question.subject,label,cutoff,world))))
        if q in ("receipts", "readbacks"):
            label = {"receipts":"RECEIPT_FOR",
                     "readbacks":"INDEPENDENT_READBACK_FOR"}[q]
            return tuple(sorted(row[0] for row in self.db.execute(
                "SELECT source FROM claims WHERE target=? AND predicate=? "
                "AND recorded_at<=? AND valid_from<=?",
                (subject_action(question.subject),label,cutoff,world))))
        if q == "trace":
            actions = tuple(row[0] for row in self.db.execute(
                "SELECT target FROM claims WHERE source=? AND predicate='PROPOSED_ACTION' "
                "AND recorded_at<=? AND valid_from<=?",
                (question.subject,cutoff,world)))
            artifacts = {("action",a) for a in actions}
            for a in actions:
                for kind,predicate in (("receipt","RECEIPT_FOR"),
                                       ("readback","INDEPENDENT_READBACK_FOR")):
                    artifacts |= {
                        (kind,row[0]) for row in self.db.execute(
                            "SELECT source FROM claims WHERE target=? AND predicate=? "
                            "AND recorded_at<=? AND valid_from<=?",
                            (a,predicate,cutoff,world))
                    }
            return tuple(sorted(f"{kind}:{identifier}" for kind,identifier in artifacts))
        raise ValueError(f"unknown query {q}")

    def close(self):
        self.db.close()


class GraphProjection:
    """Temporal graph projection from P05-1, indexed for relational traversal.

    Graph projected for a fixed as-of snapshot; intentionally rebuilds for
    a new time pair. Future knowledge does NOT leak into past snapshots.
    """
    def __init__(self, events: list[EvidenceEdge], cutoff=CUTOFF, world_time=WORLD_TIME):
        self.cutoff = cutoff
        self.world_time = world_time
        self.graph = project(events, knowledge_cutoff=cutoff, world_time=world_time)
        self.outward: dict[tuple[str,str],set[str]] = defaultdict(set)
        self.inward: dict[tuple[str,str],set[str]] = defaultdict(set)
        for e in self.graph["edges"]:
            self.outward[(e["source"],e["predicate"])].add(e["target"])
            self.inward[(e["target"],e["predicate"])].add(e["source"])

    def ask(self, question: Question) -> tuple[str, ...]:
        if (question.cutoff, question.world_time) != (self.cutoff, self.world_time):
            raise ValueError("Graph snapshot time mismatch: rebuild explicitly")
        if question.name == "authority":
            assert self.graph["can_authorize_execution"] is False
            return ("NO_AUTHORITY",)
        if question.name == "causal_effect":
            assert self.graph["can_prove_real_world_effect"] is False
            return ("NO_CAUSAL_PROOF",)
        o = self.outward
        i = self.inward
        s = question.subject
        if question.name in ("goal","observations","proposals"):
            label = {"goal":"HAS_GOAL","observations":"HAS_OBSERVATION",
                     "proposals":"PROPOSED_ACTION"}[question.name]
            return tuple(sorted(o.get((s,label),())))
        if question.name in ("receipts","readbacks"):
            label = {"receipts":"RECEIPT_FOR",
                     "readbacks":"INDEPENDENT_READBACK_FOR"}[question.name]
            return tuple(sorted(i.get((subject_action(s),label),())))
        if question.name == "trace":
            actions = o.get((s,"PROPOSED_ACTION"),())
            artifacts = {("action",a) for a in actions}
            for action in actions:
                artifacts.update(("receipt",node)
                                 for node in i.get((action,"RECEIPT_FOR"),()))
                artifacts.update(("readback",node)
                                 for node in i.get((action,"INDEPENDENT_READBACK_FOR"),()))
            return tuple(sorted(f"{kind}:{identifier}" for kind,identifier in artifacts))
        raise ValueError(f"unknown query {question.name}")


class DictIndex(GraphProjection):
    """Simplest alternative: Python dict adjacency, no ontology materialization.

    Reuses GraphProjection's exact query contract and valid-time handling, but
    builds indices directly from the immutable input events (no RDF or graph DB).
    """
    def __init__(self, events: list[EvidenceEdge], cutoff=CUTOFF, world_time=WORLD_TIME):
        self.cutoff = cutoff
        self.world_time = world_time
        self.graph = {"can_authorize_execution": False,
                      "can_prove_real_world_effect": False}
        self.outward = defaultdict(set)
        self.inward = defaultdict(set)
        known = instant(cutoff)
        world = instant(world_time)
        for e in events:
            if instant(e.recorded_at) <= known and instant(e.valid_from) <= world:
                self.outward[(e.subject,e.predicate)].add(e.object)
                self.inward[(e.object,e.predicate)].add(e.subject)


def oracle(n: int, question: Question) -> tuple[str,...]:
    """Ground truth generated directly from the synthetic scenario rules."""
    s = question.subject
    if question.name == "authority":return ("NO_AUTHORITY",)
    if question.name == "causal_effect":return ("NO_CAUSAL_PROOF",)
    if not s.startswith("synthetic:subject-"):return ()
    try:
        i = int(s.rsplit("-",1)[1])
    except (ValueError, IndexError):
        return ()
    if i >= n or i < 0:return ()
    stamp = BASE + timedelta(seconds=(i%120))
    cutoff=instant(question.cutoff)
    world=instant(question.world_time)
    if stamp > world or stamp > cutoff:return ()
    attr = {
        "goal":(f"synthetic:goal-{i:05d}",),
        "observations":(f"synthetic:observation-{i:05d}",),
        "proposals":(f"synthetic:action-{i:05d}",),
        "receipts":(f"synthetic:receipt-{i:05d}",),
        "readbacks":(f"synthetic:outcome-{i:05d}",) if i%3 else (),
    }
    if question.name == "observations":
        v=list(attr["observations"])
        if cutoff >= LATE and world >= stamp and i%7==0:
            v.append(f"synthetic:observation-late-{i:05d}")
        if cutoff >= LATE and world >= LATE and i%11==0:
            v.append(f"synthetic:observation-future-{i:05d}")
        return tuple(sorted(v))
    if question.name == "trace":
        a=attr["proposals"][0]
        v=[f"action:{a}",f"receipt:synthetic:receipt-{i:05d}"]
        if i%3:v.append(f"readback:synthetic:outcome-{i:05d}")
        return tuple(sorted(v))
    if question.name not in attr: raise ValueError(question.name)
    return attr[question.name]


def generate_questions(n: int, seed: int=20261104, how_many: int=800) -> list[Question]:
    rng=random.Random(seed+n)
    names=("goal","observations","proposals","receipts",
           "readbacks","trace","authority","causal_effect")
    questions=[]
    for j in range(how_many):
        idx=rng.randrange(n)
        name=names[j%len(names)]
        questions.append(Question(name=name,subject=f"synthetic:subject-{idx:05d}"))
    rng.shuffle(questions)
    return questions


def quantile_us(numbers: list[int], q: float) -> float:
    s=sorted(numbers)
    return round(s[min(len(s)-1,round((len(s)-1)*q))]/1000,4)


def run_size(n_subjects: int, queries: int=800) -> dict:
    t=perf_counter_ns()
    events=synthetic_events(n_subjects)
    generation_ms=round((perf_counter_ns()-t)/1e6,3)
    questions=generate_questions(n_subjects,how_many=queries)
    methods={}
    build_times={}
    t=perf_counter_ns()
    methods["flat_scan"]=FlatScan(events)
    build_times["flat_scan"]=(perf_counter_ns()-t)/1e6
    t=perf_counter_ns()
    methods["dict_index"]=DictIndex(events)
    build_times["dict_index"]=(perf_counter_ns()-t)/1e6
    t=perf_counter_ns()
    methods["sqlite_index"]=SQLiteIndex(events)
    build_times["sqlite_index"]=(perf_counter_ns()-t)/1e6
    t=perf_counter_ns()
    methods["graph_projection"]=GraphProjection(events)
    build_times["graph_projection"]=(perf_counter_ns()-t)/1e6

    # Validate EVERY question before performance claims.
    correctness={}
    for name,method in methods.items():
        errors=[]
        for question in questions:
            expected=oracle(n_subjects,question)
            actual=method.ask(question)
            if expected != actual:
                errors.append({
                    "question":question.__dict__,
                    "expected":expected, "actual":actual,
                })
        correctness[name]={"n_queries":len(questions),"errors":len(errors),
                           "examples":errors[:3]}
        if errors:
            raise AssertionError((name,errors[:1]))

    # Explicitly test time-travel and leakage across ALL backends.
    late_subject="synthetic:subject-00000"
    before=Question("observations",late_subject,CUTOFF,WORLD_TIME)
    after=Question("observations",late_subject,FUTURE_CUTOFF,FUTURE_CUTOFF)
    expected_before=oracle(n_subjects,before)
    expected_after=oracle(n_subjects,after)
    for method in (methods["flat_scan"],methods["sqlite_index"]):
        if method.ask(before)!=expected_before or method.ask(after)!=expected_after:
            raise AssertionError("as-of leakage")
    for asof in (before,after):
        for ctor in (DictIndex,GraphProjection):
            v=ctor(events,cutoff=asof.cutoff,world_time=asof.world_time)
            if v.ask(asof)!=oracle(n_subjects,asof):
                raise AssertionError("prebuilt index as-of leakage")

    # Warm-up to reduce one-time interpreter effects. Reuse same shuffled order.
    for name,method in methods.items():
        for q in questions[:20]:
            method.ask(q)
    timings={}
    for name,method in methods.items():
        latencies=[]
        gc.collect()
        for q in questions:
            start=perf_counter_ns()
            method.ask(q)
            latencies.append(perf_counter_ns()-start)
        timings[name]={
            "build_ms":round(build_times[name],3),
            "query_median_us":quantile_us(latencies,.5),
            "query_p95_us":quantile_us(latencies,.95),
            "query_total_ms":round(sum(latencies)/1e6,3),
            "queries":len(latencies),
        }
    methods["sqlite_index"].close()
    return {
        "subjects":n_subjects, "events":len(events), "generation_ms":generation_ms,
        "benchmark_queries":len(questions), "truth_checked":True,
        "correctness":correctness, "timings":timings,
        "time_travel_test":True, "authority_is_outside_graph":True,
        "causal_proof_not_inferred_from_receipt":True,
    }


def run() -> dict:
    sizes=(100, 500, 2500)
    output={
        "benchmark":"P05-1 synthetic: flat scan vs direct Python dict index vs SQLite index vs read-only temporal graph projection",
        "seed":20261104,
        "python":sys.version.split()[0],
        "all_test_data":"100% synthesized, NO user accounts, no model inference or external effects",
        "reuse":"P05-1 typed EvidenceEdge + Manager Core StateMachine; SQLite from stdlib",
        "not_graphiti_runtime":True,
        "index_baseline_included":True,
        "no_new_production_database":True,
        "fairness":"same generated events, same as-of snapshot, same question labels; build time separate from query time",
        "interpretation":"in-memory microbenchmark, no network, real users, semantic search, LLM extraction, multi-tenant workload or concurrency",
        "warmup_queries_per_method":20,
        "n_sizes":len(sizes),
        "results":[run_size(size) for size in sizes],
        "manager_core_safety":existing_state_machine_example(),
    }
    root=Path(__file__).resolve().parents[1]/"evidence"
    root.mkdir(parents=True,exist_ok=True)
    target=root/"P05-1_QUERY_BENCHMARK_SYNTHETIC.json"
    target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return output


if __name__=="__main__":
    result=run()
    for z in result["results"]:
        print(f"synthetic subjects={z['subjects']} events={z['events']} checked_queries={z['benchmark_queries']}")
        for name,row in z["timings"].items():
            print(f"  {name:16} build_ms={row['build_ms']:.3f} median_us={row['query_median_us']:.3f} p95_us={row['query_p95_us']:.3f} query_total_ms={row['query_total_ms']:.3f}")
    print("saved P05-1_QUERY_BENCHMARK_SYNTHETIC.json")
