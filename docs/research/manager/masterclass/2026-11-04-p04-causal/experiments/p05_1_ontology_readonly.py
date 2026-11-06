"""P05-1: immutable synthetic evidence -> read-only ontology projection.

This is an EDUCATIONAL projection, NOT a new authority database, NOT a
digital twin validated on people, and NOT an executor. It deliberately uses
the pre-existing Manager state machine and checks its import without copying
or altering operational grants, effects, receipts or private ledgers.

Sources for design: skills/graph-engineering/SKILL.md, W3C PROV-O, JSON-LD,
CloudEvents, BCIO/JITAI and products/manager/manager_core.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Iterable
import json
import re
import sys

# Read-only reuse of existing Manager Core. Not a second state machine.
_REPO = Path(__file__).resolve().parents[6]
_MANAGER = _REPO / "products" / "manager"
if not (_MANAGER / "manager_core" / "state_machine.py").exists():
    raise RuntimeError("Manager Core missing; do not invent a duplicate")
sys.path.insert(0, str(_MANAGER))
from manager_core.state_machine import State, StateMachine  # noqa: E402
from manager_core.models.intervention import InterventionPlan, InterventionOption  # noqa: E402

NS = "https://aniccaai.com/ns/manager/v0#"
PRIVACY = "synthetic_nonpersonal"
SOURCE_KINDS = frozenset({
    "synthetic_observation", "synthetic_model_inference",
    "synthetic_provider_receipt", "synthetic_independent_readback",
})
PREDICATES = frozenset({
    "HAS_GOAL", "HAS_OBSERVATION", "PROPOSED_ACTION",
    "RECEIPT_FOR", "INDEPENDENT_READBACK_FOR", "SUPERSEDES",
})
KINDS = frozenset({"Subject", "Goal", "Observation", "Action", "Receipt", "Outcome"})
SAFE_ID = re.compile(r"^synthetic:[a-z][a-z0-9-]{2,80}$")
SHA = re.compile(r"^[a-f0-9]{64}$")
EVENT_ID = re.compile(r"^[a-f0-9]{24,64}$")


def instant(value: str) -> datetime:
    """Require an offset-aware datetime, normalized to UTC."""
    if type(value) is not str or not value:
        raise ValueError("timestamp string required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError("invalid ISO-8601 timestamp") from e
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def canonical(obj: dict) -> bytes:
    """Deterministic serialization for reproducible IDs (not an authority seal)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class EvidenceEdge:
    """Explicit claim record; the graph never upgrades a claim to a permission."""
    event_id: str
    subject: str
    subject_kind: str
    predicate: str
    object: str
    object_kind: str
    source_fact_id: str
    source_kind: str
    observed_at: str
    recorded_at: str
    valid_from: str
    evidence_sha256: str
    privacy_class: str
    confidence: float | None
    verifier: str | None = None
    executor: str | None = None

    def __post_init__(self):
        if not EVENT_ID.fullmatch(self.event_id):
            raise ValueError("event_id must be hash-like")
        for k in ("subject", "object"):
            if not SAFE_ID.fullmatch(getattr(self, k)):
                raise ValueError(f"{k} requires a synthetic ID")
        if self.subject_kind not in KINDS or self.object_kind not in KINDS:
            raise ValueError("unknown kind")
        if self.predicate not in PREDICATES:
            raise ValueError("unknown predicate; do not auto-invent semantics")
        if not SAFE_ID.fullmatch(self.source_fact_id):
            raise ValueError("source_fact_id is required")
        if self.source_kind not in SOURCE_KINDS:
            raise ValueError("unapproved source kind")
        if not SHA.fullmatch(self.evidence_sha256):
            raise ValueError("source content hash missing")
        if self.privacy_class != PRIVACY:
            raise ValueError("public exercise refuses personal/private input")
        if self.confidence is not None and (
            type(self.confidence) not in (float, int)
            or not 0 <= self.confidence <= 1
        ):
            raise ValueError("confidence must be null or 0..1")
        t0, t1, t2 = (instant(getattr(self, k))
                      for k in ("observed_at", "recorded_at", "valid_from"))
        if t2 > t0:
            raise ValueError("valid_from cannot exceed observed_at")
        if t1 < t0:
            # Late arrivals are okay, impossible time travel in this adapter is not.
            raise ValueError("recorded_at must be no earlier than observed_at")
        if self.source_kind == "synthetic_independent_readback":
            if (self.predicate != "INDEPENDENT_READBACK_FOR"
                    or not self.verifier or not self.executor
                    or self.verifier == self.executor):
                raise ValueError("readback must be independently sourced")
        elif self.verifier is not None or self.executor is not None:
            raise ValueError("verification fields only on independent readbacks")
        if self.predicate == "INDEPENDENT_READBACK_FOR" and (
            self.source_kind != "synthetic_independent_readback"
        ):
            raise ValueError("receipt or prediction is not independent readback")
        if self.predicate == "RECEIPT_FOR" and self.source_kind != "synthetic_provider_receipt":
            raise ValueError("receipts need a provider source")


def make_event(*, subject: str, subject_kind: str, predicate: str, object: str,
               object_kind: str, source_fact_id: str, source_kind: str,
               observed_at: str, recorded_at: str, valid_from: str,
               evidence_text: str, privacy_class: str = PRIVACY,
               confidence: float | None = None,
               verifier: str | None = None, executor: str | None = None) -> EvidenceEdge:
    """Fixture builder; no connected data ingestion, no permissions or writes."""
    if type(evidence_text) is not str or not evidence_text:
        raise ValueError("nonempty source evidence required")
    raw = {
        "subject": subject, "subject_kind": subject_kind, "predicate": predicate,
        "object": object, "object_kind": object_kind,
        "source_fact_id": source_fact_id, "source_kind": source_kind,
        "observed_at": observed_at, "recorded_at": recorded_at,
        "valid_from": valid_from,
        "evidence_sha256": sha256(evidence_text.encode("utf-8")).hexdigest(),
        "privacy_class": privacy_class, "confidence": confidence,
        "verifier": verifier, "executor": executor,
    }
    eid = sha256(canonical(raw)).hexdigest()
    return EvidenceEdge(event_id=eid, **raw)


def project(events: Iterable[EvidenceEdge], *, knowledge_cutoff: str,
            world_time: str) -> dict:
    """Bitemporal, deterministic, non-mutating graph VIEW of immutable claims.

    Filtering by BOTH recorded_at and valid_from prevents later-learned facts
    from leaking into earlier decision-time simulations.
    """
    known = instant(knowledge_cutoff)
    valid = instant(world_time)
    all_events: dict[str, EvidenceEdge] = {}
    for edge in events:
        if not isinstance(edge, EvidenceEdge):
            raise ValueError("typed edges required")
        if edge.event_id in all_events and all_events[edge.event_id] != edge:
            raise ValueError("duplicate id with different payload")
        all_events[edge.event_id] = edge
    visible = [
        e for e in all_events.values()
        if instant(e.recorded_at) <= known and instant(e.valid_from) <= valid
    ]
    visible.sort(key=lambda e: (instant(e.valid_from), e.event_id))
    nodes: dict[str, dict] = {}
    for e in visible:
        for identifier, kind in ((e.subject, e.subject_kind), (e.object, e.object_kind)):
            old = nodes.get(identifier)
            if old and old["kind"] != kind:
                raise ValueError("conflicting node kinds")
            nodes[identifier] = {"id": identifier, "kind": kind, "privacy_class": PRIVACY}
    entries = [
        {
            "source": e.subject, "predicate": e.predicate, "target": e.object,
            "source_fact_id": e.source_fact_id, "event_id": e.event_id,
            "source_kind": e.source_kind, "recorded_at": e.recorded_at,
            "valid_from": e.valid_from, "observed_at": e.observed_at,
            "evidence_sha256": e.evidence_sha256, "confidence": e.confidence,
            "epistemic_status": (
                "INFERRED_NOT_VERIFIED" if e.source_kind == "synthetic_model_inference"
                else "INDEPENDENT_READBACK_SYNTHETIC"
                if e.source_kind == "synthetic_independent_readback"
                else "PROVIDER_RECEIPT_NOT_OUTCOME"
                if e.source_kind == "synthetic_provider_receipt"
                else "OBSERVED_SYNTHETIC"
            ),
        }
        for e in visible
    ]
    return {
        "version": "manager.synthetic.graph-projection.v0",
        "knowledge_cutoff": knowledge_cutoff, "world_time": world_time,
        "synthetic_only": True, "can_authorize_execution": False,
        "can_prove_real_world_effect": False,
        "n_source_events": len(visible),
        "nodes": [nodes[k] for k in sorted(nodes)],
        "edges": entries,
    }


def as_jsonld(projection: dict) -> dict:
    """A simple JSON-LD interchange sketch, NOT a PROV-O reasoner."""
    if not projection.get("synthetic_only") or projection.get("can_authorize_execution"):
        raise ValueError("cannot serialize non-synthetic/authoritative projection")
    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "mgr": NS,
            "sourceFact": {"@id": "mgr:sourceFact", "@type": "@id"},
            "subject": {"@id": "mgr:subject", "@type": "@id"},
            "target": {"@id": "mgr:target", "@type": "@id"},
            "predicate": "mgr:predicate",
            "validFrom": {"@id": "mgr:validFrom", "@type": "http://www.w3.org/2001/XMLSchema#dateTime"},
        },
        "@graph": [
            {
                "@id": f"urn:manager:claim:{e['event_id']}",
                "@type": "prov:Entity",
                "subject": f"urn:manager:{e['source']}",
                "predicate": e["predicate"],
                "target": f"urn:manager:{e['target']}",
                "sourceFact": f"urn:manager:{e['source_fact_id']}",
                "validFrom": e["valid_from"],
                "prov:generatedAtTime": e["recorded_at"],
                "mgr:epistemicStatus": e["epistemic_status"],
            }
            for e in projection["edges"]
        ],
    }


def existing_state_machine_example() -> dict:
    """Reuse Manager Core, do NOT create a new execution state machine."""
    m = StateMachine()
    m.transition(State.HYPOTHESIZED)
    m.transition(State.NO_ACTION)
    no_action = InterventionOption(
        option_id="synthetic-none", domain="synthetic",
        target="synthetic:subject-01", action="NO_ACTION",
        cost=0.0, risk=0.0, expected_effect=None, no_action=True
    )
    proposal = InterventionOption(
        option_id="synthetic-prompt", domain="synthetic",
        target="synthetic:subject-01", action="EDUCATIONAL_PROMPT",
        cost=0.01, risk=0.02, expected_effect=(-0.1, 0.2),
        no_action=False,
    )
    p = InterventionPlan((no_action, proposal))
    chosen = p.choose(supports_causal=False)
    return {
        "manager_core_reused": True,
        "state_history": [x.value for x in m.history],
        "causal_unsupported_choice": chosen.action,
        "executed_real_action": False,
    }


def fixtures() -> list[EvidenceEdge]:
    """Deterministic synthetic scenario, NOT a model of any real person."""
    t = "2026-11-04T08:00:00+00:00"
    rows = [
        dict(subject="synthetic:subject-01", subject_kind="Subject",
             predicate="HAS_GOAL", object="synthetic:goal-01", object_kind="Goal",
             source_fact_id="synthetic:fact-goal", source_kind="synthetic_observation",
             evidence_text="imaginary goal described in fabricated test data"),
        dict(subject="synthetic:subject-01", subject_kind="Subject",
             predicate="HAS_OBSERVATION", object="synthetic:observation-01", object_kind="Observation",
             source_fact_id="synthetic:fact-observation", source_kind="synthetic_observation",
             evidence_text="fabricated self-report value; not psychological truth"),
        dict(subject="synthetic:subject-01", subject_kind="Subject",
             predicate="PROPOSED_ACTION", object="synthetic:action-01", object_kind="Action",
             source_fact_id="synthetic:fact-model", source_kind="synthetic_model_inference",
             evidence_text="imaginary model proposed one intervention", confidence=0.55),
        dict(subject="synthetic:receipt-01", subject_kind="Receipt",
             predicate="RECEIPT_FOR", object="synthetic:action-01", object_kind="Action",
             source_fact_id="synthetic:fact-receipt", source_kind="synthetic_provider_receipt",
             evidence_text="fabricated receipt: no real provider called"),
        dict(subject="synthetic:outcome-01", subject_kind="Outcome",
             predicate="INDEPENDENT_READBACK_FOR", object="synthetic:action-01",
             object_kind="Action", source_fact_id="synthetic:fact-readback",
             source_kind="synthetic_independent_readback",
             evidence_text="fabricated independent readback; no real human effect",
             verifier="synthetic:observer", executor="synthetic:executor"),
    ]
    return [make_event(**r,observed_at=t,recorded_at=t,valid_from=t) for r in rows]


def run() -> dict:
    events = fixtures()
    before = project(events, knowledge_cutoff="2026-11-04T07:59:59Z",
                     world_time="2026-11-04T08:01:00Z")
    current = project(events, knowledge_cutoff="2026-11-04T08:01:00Z",
                      world_time="2026-11-04T08:01:00Z")
    return {
        "state_machine": existing_state_machine_example(),
        "before_recorded": before, "after_recorded": current,
        "jsonld_sketch": as_jsonld(current),
        "limitations": {
            "no_real_users": True, "no_execution": True,
            "no_live_receipt": True, "no_human_effect": True,
            "not_an_authority_registry": True,
            "full_OWL_reasoning_implemented": False,
            "SHACL_validation_implemented": False,
        },
    }


if __name__ == "__main__":
    output = Path(__file__).resolve().parent.parent / "evidence"
    output.mkdir(parents=True, exist_ok=True)
    path = output / "P05-1_READONLY_SYNTHETIC_PROJECTION.json"
    path.write_text(json.dumps(run(), ensure_ascii=False, indent=2)+"\n",
                    encoding="utf-8")
    print(f"written={path} synthetic-only")
