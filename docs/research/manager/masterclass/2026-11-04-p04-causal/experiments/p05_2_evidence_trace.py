"""P05-2: validated, read-only correlation of existing Manager record contracts.

Research fixture only. NO external effects, real humans, authorization, production
migration, or prediction quality claims. Reuses:
 - runtime/contracts/common-record.schema.json (Draft 2020-12)
 - runtime.loop.runtime_event.validate_runtime_event
 - manager_core.evidence_types.Prediction
 - manager_core.models.intervention.InterventionPlan

Important: `Job.effect_key` is an idempotency key, NOT `Effect.effect_id`.
Links are validated on loop_id/run_id/effect_id/receipt_id/provider/owner.
The correlation output can NEVER authorize execution or certify a causal effect.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Iterable
import json
import re
import sys

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "products" / "manager"))
from runtime.loop.runtime_event import validate_runtime_event  # noqa: E402
from manager_core.evidence_types import Prediction  # noqa: E402
from manager_core.models.intervention import (  # noqa: E402
    InterventionOption, InterventionPlan,
)

SCHEMA_PATH = ROOT / "runtime" / "contracts" / "common-record.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
SCHEMA_SHA256 = sha256(SCHEMA_PATH.read_bytes()).hexdigest()
ALLOWED = frozenset({"job", "effect", "receipt", "runtime_event"})
FIELDS = {
    "job": "job_id",
    "effect": "effect_id",
    "receipt": "receipt_id",
    "runtime_event": "event_id",
}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
STAMP = "2026-11-04T09:00:00+00:00"


def when(value: str) -> datetime:
    if type(value) is not str:
        raise ValueError("offset-aware ISO timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone is required")
    return parsed.astimezone(timezone.utc)


def digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class StampedRecord:
    """An immutable observed source record, with receipt time supplied by reader."""
    kind: str
    record: dict
    known_at: str
    source_ref: str
    record_sha256: str = field(init=False, repr=False)

    def __post_init__(self):
        if self.kind not in ALLOWED:
            raise ValueError("unsupported source record; use existing contract")
        when(self.known_at)
        if not re.fullmatch(r"synthetic://[a-z0-9._:/-]{3,120}", self.source_ref):
            raise ValueError("only nonpersonal synthetic sources in this exercise")
        if type(self.record) is not dict:
            raise ValueError("typed record required")
        VALIDATOR.validate(self.record)  # Existing schema; not a new contract.
        if self.kind == "runtime_event":
            if "event_id" not in self.record:
                raise ValueError("runtime event ID missing")
            validate_runtime_event(self.record)
        elif self.record.get("record_type") != self.kind:
            raise ValueError("source record kind mismatch")
        datefield = {"effect": "attempted_at", "receipt": "recorded_at",
                     "runtime_event": "timestamp"}.get(self.kind)
        if datefield is not None and when(self.record[datefield]) > when(self.known_at):
            raise ValueError("source evidence cannot be known before generated time")
        if not SAFE_ID.fullmatch(self.record[FIELDS[self.kind]]):
            raise ValueError("existing identity invalid")
        object.__setattr__(self, "record_sha256", digest(self.record))

    @property
    def key(self) -> tuple[str, str]:
        return (self.kind, self.record[FIELDS[self.kind]])


def fixture_records(*, include_receipt: bool = True,
                    include_event: bool = True,
                    late_receipt: bool = False) -> tuple[StampedRecord, ...]:
    """Four canonical existing record shapes; all identities artificial."""
    job = {
        "schema_version": 1, "record_type": "job",
        "job_id": "job-synthetic", "tenant_id": "tenant-synthetic",
        "loop_id": "loop-synthetic", "capability": "research-synthetic",
        "effect_class": "message", "effect_key": "idem-synthetic",
        "input_refs": {
            "prediction_ref": "synthetic://prediction-demo",
            "decision_ref": "synthetic://decision-demo",
        },
        "max_attempts": 1,
    }
    effect = {
        "schema_version": 1, "record_type": "effect",
        "effect_id": "effect-synthetic", "loop_id": "loop-synthetic",
        "run_id": "run-synthetic", "effect_class": "message",
        "idempotency_key": "idem-synthetic", "status": "started",
        "provider": "synthetic-provider",
        "attempted_at": STAMP, "evidence_refs": ["synthetic://effect-intent"],
    }
    receipt = {
        "schema_version": 1, "record_type": "receipt",
        "receipt_id": "receipt-synthetic", "effect_id": "effect-synthetic",
        "loop_id": "loop-synthetic", "run_id": "run-synthetic",
        "outcome": "uncertain", "provider": "synthetic-provider",
        "recorded_at": "2026-11-04T09:01:00+00:00",
        "external_ref": None,
        "payload_sha256": "a" * 64,
        "evidence_refs": [],
    }
    event = {
        "version": 1, "event_id": "b" * 64,
        "timestamp": "2026-11-04T09:02:00+00:00",
        "loop_id": "loop-synthetic", "domain": "system",
        "run_id": "run-synthetic", "phase": "verify", "status": "blocked",
        "release_sha": "c" * 40, "provider": "synthetic-provider",
        "profile_alias": None, "effect_class": "message",
        "effect_status": "unknown", "blocker": "no-independent-proof",
        "evidence_refs": ["synthetic://runtime-event"],
        # The runtime's diagnostic fields are all-or-none by existing contract.
        "product_loop_id": "loop-synthetic",
        "job_id": "job-synthetic",
        "owner_id": "tenant-synthetic",
        "wake_id": "wake-synthetic",
        "occurrence_id": "job-synthetic:occurrence-01",
        "loaded_argv_sha256": None,
        "loaded_env_sha256": None,
        "exit_code": 0, "failure_layer": "effect_readback",
        "error_class": None, "retryable": False,
        "next_action": "reconcile-before-retry",
        "provider_receipt_id": "receipt-synthetic" if include_receipt else None,
        "official_readback_ref": None,
    }
    records = [
        StampedRecord("job", job, STAMP, "synthetic://job-ledger"),
        StampedRecord("effect", effect, "2026-11-04T09:00:05+00:00",
                      "synthetic://effect-ledger"),
    ]
    if include_receipt:
        records.append(StampedRecord(
            "receipt", receipt,
            "2026-11-05T12:00:00+00:00" if late_receipt else "2026-11-04T09:01:05+00:00",
            "synthetic://receipt-ledger"))
    if include_event:
        records.append(StampedRecord(
            "runtime_event", event, "2026-11-04T09:02:05+00:00",
            "synthetic://runtime-ledger"))
    return tuple(records)


def research_prediction() -> Prediction:
    """Uses existing strictly P0 ManagerCore Prediction type."""
    return Prediction(source_refs=("synthetic://source-data",),
                      model_id="model-synthetic-v0",
                      distribution=(0.3, 0.7))


def research_decision() -> tuple[str, str]:
    """Strict NO_ACTION from original Manager Core when causality is unsupported."""
    options = InterventionPlan(options=(
        InterventionOption(option_id="none", domain="system",
                           target="synthetic:subject", action="NO_ACTION",
                           cost=0, risk=0, expected_effect=None, no_action=True),
        InterventionOption(option_id="candidate", domain="system",
                           target="synthetic:subject", action="synthetic-reminder",
                           cost=0.01, risk=0.01, expected_effect=(-0.05, 0.15)),
    ))
    chosen = options.choose(supports_causal=False)
    return chosen.action, chosen.option_id


def join_trace(source: Iterable[StampedRecord], *, known_at: str,
               tenant_id: str, run_id: str) -> dict:
    """Read-only, fail-closed trace for ONE tenant/run, using existing record IDs.

    Caller never receives an execution grant or a proof of observed human impact.
    Orphans/conflicts/foreign IDs fail before a trace is returned.
    """
    cutoff = when(known_at)
    if type(tenant_id) is not str or not SAFE_ID.fullmatch(tenant_id):
        raise ValueError("tenant scope required")
    if type(run_id) is not str or not SAFE_ID.fullmatch(run_id):
        raise ValueError("run scope required")

    all_records: dict[tuple[str, str], StampedRecord] = {}
    for item in source:
        if not isinstance(item, StampedRecord):
            raise ValueError("only validated stamped records accepted")
        if digest(item.record) != item.record_sha256:
            raise ValueError("validated source mutated after capture")
        old = all_records.get(item.key)
        if old is not None and old != item:
            raise ValueError("conflicting duplicate source record")
        all_records[item.key] = item
    items = [r for r in all_records.values() if when(r.known_at) <= cutoff]
    by_kind = {kind: [r for r in items if r.kind == kind] for kind in ALLOWED}

    # Jobs lack native timestamps/run IDs. The known_at wrapper is essential.
    # Join to a job only by the effect key and matching loop, never by invented run IDs.
    scoped_effects = [r for r in by_kind["effect"] if r.record["run_id"] == run_id]
    scoped_runtime = [r for r in by_kind["runtime_event"] if r.record["run_id"] == run_id]
    if len(scoped_effects) > 1:
        raise ValueError("ambiguous multiple effects for research run")
    effect = scoped_effects[0].record if scoped_effects else None
    matched_jobs = [
        r for r in by_kind["job"] if effect is not None
        and r.record["effect_key"] == effect["idempotency_key"]
        and r.record["loop_id"] == effect["loop_id"]
    ]
    if len(matched_jobs) > 1:
        raise ValueError("ambiguous job identity")
    job = matched_jobs[0].record if matched_jobs else None
    if effect is not None and job is None:
        raise ValueError("orphan effect or job record not yet known")
    if job is not None and job["tenant_id"] != tenant_id:
        raise ValueError("cross-tenant join refused")
    if effect is not None and effect["effect_class"] != job["effect_class"]:
        raise ValueError("job/effect class mismatch")
    if any(e.record["loop_id"] != job["loop_id"] or
           e.record.get("owner_id") not in (None, tenant_id) or
           e.record.get("job_id") not in (None, job["job_id"]) or
           e.record["provider"] != effect["provider"] for e in scoped_runtime):
        raise ValueError("foreign or cross-owner runtime event")
    # Reject a receipt claiming this exact effect ID but belonging to a foreign
    # run; silently ignoring it would hide an identity collision.
    if effect is not None and any(
        r.record["effect_id"] == effect["effect_id"]
        and r.record["run_id"] != run_id
        for r in by_kind["receipt"]
    ):
        raise ValueError("receipt claims this effect under a different run")
    matched_receipts = [
        r for r in by_kind["receipt"] if r.record["run_id"] == run_id
    ]
    if len(matched_receipts) > 1:
        raise ValueError("ambiguous receipt")
    receipt = matched_receipts[0].record if matched_receipts else None
    if receipt is not None:
        if effect is None or any([
            receipt["effect_id"] != effect["effect_id"],
            receipt["run_id"] != effect["run_id"],
            receipt["loop_id"] != effect["loop_id"],
            receipt["provider"] != effect["provider"],
        ]):
            raise ValueError("foreign receipt or run/effect mismatch")
        if when(receipt["recorded_at"]) < when(effect["attempted_at"]):
            raise ValueError("receipt predates effect attempt")
    # Do not assume a provider's 'verified' means human benefit or causal support.
    for event_record in scoped_runtime:
        ev = event_record.record
        if ev.get("provider_receipt_id") is not None and receipt is not None:
            if ev["provider_receipt_id"] != receipt["receipt_id"]:
                raise ValueError("runtime receipt and signed record disagree")
        elif ev.get("provider_receipt_id") is not None and receipt is None:
            # The event may have arrived before the actual receipt record.
            pass
        if ev.get("official_readback_ref") is not None:
            # Reference is *not* an authenticated, independently measured outcome.
            pass

    # No native source record in this input proves which Prediction/Decision
    # produced this Job. Do NOT attach an unrelated toy model or NO_ACTION
    # decision to a historical synthetic effect: that would be a false join.
    links = {
        "tenant_id": tenant_id,
        "job_id": job["job_id"] if job else None,
        "run_id": run_id,
        "effect_id": effect["effect_id"] if effect else None,
        "idempotency_key": effect["idempotency_key"] if effect else None,
        "receipt_id": receipt["receipt_id"] if receipt else None,
        "experiment_id": None,  # not a native ID in the four existing records
        "prediction_id": None,  # not invented from a source_ref
        "decision_id": None,  # not invented from a source_ref
        "prediction_source_ref": job["input_refs"].get("prediction_ref") if job else None,
        "decision_source_ref": job["input_refs"].get("decision_ref") if job else None,
    }
    statuses = [
        {"id": r.record[FIELDS[r.kind]], "kind": r.kind,
         "source_ref": r.source_ref, "known_at": r.known_at,
         "source_hash": digest(r.record)}
        for r in items if (r.kind == "job" and job is not None and
                           r.record["job_id"] == job["job_id"])
                        or (r.kind == "effect" and effect is not None and
                            r.record["effect_id"] == effect["effect_id"])
                        or (r.kind == "receipt" and receipt is not None and
                            r.record["receipt_id"] == receipt["receipt_id"])
                        or (r.kind == "runtime_event" and r.record["run_id"] == run_id)
    ]
    statuses.sort(key=lambda r: (r["known_at"], r["kind"], r["id"]))
    return {
        "schema": "manager.research.read_only_trace.v0",
        "source_contract_sha256": SCHEMA_SHA256,
        "known_at": known_at, "synthetic_only": True,
        "links": links, "observed_evidence": statuses,
        "n_source_records": len(statuses),
        "producer_linkage": {
            "model_id": None,
            "prediction_id": None,
            "decision_id": None,
            "status": "PREDICTION_AND_DECISION_PRODUCER_NOT_LINKED",
            "note": "A standalone Manager Core safety check must not be joined to another run",
        },
        "effect_tracking": {
            "has_effect_intent": effect is not None,
            "has_provider_receipt": receipt is not None,
            "receipt_outcome": receipt["outcome"] if receipt is not None else "MISSING",
            "has_runtime_event": bool(scoped_runtime),
            "has_confirmed_independent_outcome": False,
            "human_impact": "NOT_MEASURED",
            "causal_attribution": "NOT_ESTABLISHED",
        },
        "action_permission": "NEVER_ISSUED_BY_TRACE",
        "can_execute": False,
        "can_prove_causal_effect": False,
        "unresolved_contract_gaps": [
            "prediction_id_not_in_existing_job_effect_receipt_runtime_event",
            "decision_id_not_in_existing_job_effect_receipt_runtime_event",
            "experiment_id_not_in_existing_job_effect_receipt_runtime_event",
            "independent_outcome_not_authenticated",
        ],
    }


def run() -> dict:
    records = fixture_records()
    early = join_trace(records, known_at="2026-11-04T09:00:00+00:00",
                       tenant_id="tenant-synthetic", run_id="run-synthetic")
    mid = join_trace(records, known_at="2026-11-04T09:00:10+00:00",
                     tenant_id="tenant-synthetic", run_id="run-synthetic")
    after = join_trace(records, known_at="2026-11-04T09:04:00+00:00",
                       tenant_id="tenant-synthetic", run_id="run-synthetic")
    prediction = research_prediction()
    decision, _ = research_decision()
    return {
        "standalone_core_safety_checks": {
            "prediction_proof_level": prediction.proof_level,
            "causal_support": prediction.causal_support,
            "unlinked_no_action_choice": decision,
            "linked_to_synthetic_job": False,
        },
        "study": "P05-2: synthetic sources validating pre-existing common-record schema",
        "source_contract": str(SCHEMA_PATH.relative_to(ROOT)),
        "contract_sha256": SCHEMA_SHA256,
        "pre_effect": early,
        "post_effect_pre_receipt": mid,
        "post_receipt_and_runtime_event": after,
        "new_authoritative_schema_created": False,
        "production_data_ingested": False,
        "real_provider_effect_executed": False,
    }


if __name__ == "__main__":
    out = ROOT / "docs/research/manager/masterclass/2026-11-04-p04-causal/evidence"
    out.mkdir(parents=True, exist_ok=True)
    result = run()
    (out / "P05-2_SYNTHETIC_TRACE_RESULTS.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "pre_effect_records": result["pre_effect"]["n_source_records"],
        "after_effect_records": result["post_effect_pre_receipt"]["n_source_records"],
        "post_receipt_records": result["post_receipt_and_runtime_event"]["n_source_records"],
        "causal_support": result["post_receipt_and_runtime_event"]["can_prove_causal_effect"],
        "existing_contract_reused": True,
    }, ensure_ascii=False))
