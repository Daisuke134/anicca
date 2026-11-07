"""P10-2/3/4: fully synthetic Manager capital/control/operations prototype.

This module performs ZERO network, payment, publication, dispatch, or real
authorization operations. It does not handle secrets or personal data.
All outcomes are plans/indicators, NOT permissions or business evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from itertools import combinations
import hashlib
import json

HIGH_EFFECTS = frozenset({"money", "trade", "publish", "message", "account_mutation"})
READ_ONLY_ACTIONS = frozenset({"read_synthetic", "compute_synthetic"})
ALLOWED_STATES = frozenset({"NEW", "DISPATCHING", "UNKNOWN", "PRESENT", "ABSENT", "VERIFIED", "FAILED"})


@dataclass(frozen=True)
class Proposal:
    project_id: str
    cost_minor: int
    conservative_value_minor: int  # a supplied FORECAST, not realized value
    research_value_minor: int = 0   # explicitly assumed monetized learning value
    rights_clear_for_simulation: bool = True


def plan_portfolio(proposals: list[Proposal], cash_minor: int, reserve_minor: int,
                   max_experiment_minor: int) -> dict:
    """Exhaustive small-N *planning* optimization; NEVER authorizes spending."""
    if (any(type(v) is not int or v < 0 for v in
            (cash_minor, reserve_minor, max_experiment_minor))
            or reserve_minor > cash_minor):
        raise ValueError("cash, reserve and cap must be nonnegative integers")
    if len(proposals) > 16 or len({p.project_id for p in proposals}) != len(proposals):
        raise ValueError("bounded unique project list required")
    for p in proposals:
        if (not p.project_id or type(p.cost_minor) is not int or p.cost_minor <= 0
                or type(p.conservative_value_minor) is not int
                or type(p.research_value_minor) is not int
                or p.research_value_minor < 0
                or type(p.rights_clear_for_simulation) is not bool):
            raise ValueError("invalid proposal")
    available = min(cash_minor - reserve_minor, max_experiment_minor)
    best = (0, 0, ())  # (assumed net value, negative committed cost, sorted project ids)
    for n in range(len(proposals) + 1):
        for chosen in combinations(proposals, n):
            if any(not p.rights_clear_for_simulation for p in chosen):
                continue
            spend = sum(p.cost_minor for p in chosen)
            if spend > available:
                continue
            net = sum(p.conservative_value_minor + p.research_value_minor - p.cost_minor
                      for p in chosen)
            ids = tuple(sorted(p.project_id for p in chosen))
            candidate = (net, -spend, ids)
            if (candidate[0] > best[0]
                    or (candidate[0] == best[0] and candidate[1] > best[1])
                    or (candidate[0] == best[0] and candidate[1] == best[1]
                        and candidate[2] < best[2])):
                best = candidate
    return {
        "status": "SYNTHETIC_PROPOSAL_ONLY",
        "selected_project_ids": list(best[2]),
        "spend_minor": -best[1],
        "assumed_net_value_minor": best[0],
        "reserve_preserved_minor": reserve_minor,
        "remaining_experiment_cap_minor": available + best[1],
        "external_authorization": False,
        "real_return_proven": False,
    }


@dataclass(frozen=True)
class PolicyInput:
    actor_id: str
    tenant_id: str
    target_tenant_id: str
    action: str
    scope: frozenset[str]
    expires_at_utc: datetime
    now_utc: datetime
    revoked: bool
    consent_confirmed: bool
    requested_cost_minor: int
    remaining_cap_minor: int
    data_class: str
    policy_version: str
    is_external_effect: bool


def policy_candidate(req: PolicyInput) -> dict:
    """Conservative instructional check; no cryptographic validation/live enable."""
    reasons: list[str] = []
    for attr in ("actor_id", "tenant_id", "target_tenant_id", "action", "policy_version"):
        if not isinstance(getattr(req, attr), str) or not getattr(req, attr).strip():
            reasons.append("MISSING_ID_OR_POLICY")
            break
    if (req.now_utc.tzinfo is None or req.expires_at_utc.tzinfo is None):
        reasons.append("UNTRUSTED_CLOCK")
    else:
        if req.now_utc >= req.expires_at_utc:
            reasons.append("EXPIRED")
    if req.revoked:
        reasons.append("REVOKED")
    if req.tenant_id != req.target_tenant_id:
        reasons.append("TENANT_MISMATCH")
    if req.action not in req.scope:
        reasons.append("OUTSIDE_SCOPE")
    if not req.consent_confirmed:
        reasons.append("NO_CONSENT")
    if (type(req.requested_cost_minor) is not int
            or type(req.remaining_cap_minor) is not int
            or req.requested_cost_minor < 0
            or req.remaining_cap_minor < req.requested_cost_minor):
        reasons.append("BUDGET")
    if req.data_class not in {"synthetic", "public"}:
        reasons.append("PRIVATE_DATA_BLOCKED")
    if (req.is_external_effect or req.action not in READ_ONLY_ACTIONS
            or req.action in HIGH_EFFECTS):
        reasons.append("NO_LIVE_EFFECT_AUTHORITY")
    return {
        "decision": "DENY" if reasons else "SIMULATION_ELIGIBLE_NOT_AUTHORIZED",
        "reasons": sorted(set(reasons)),
        "authority_to_execute": False,
        "policy_version": req.policy_version,
    }


def safe_audit_projection(event: dict) -> dict:
    """Small bounded allowlist. This is NOT immutable audit storage."""
    allowed = {"event_id", "tenant_ref", "run_ref", "phase", "decision",
               "reason_code", "policy_version", "evidence_ref"}
    if (type(event) is not dict or set(event) != allowed
            or any(not isinstance(value, str) or not 0 < len(value) <= 128
                   for value in event.values())):
        raise ValueError("minimal no-PII audit event required")
    if any(any(x in value.lower() for x in
               ("@", "password", "secret", "bearer ", "api_key", "private key"))
           for value in event.values()):
        raise ValueError("possible PII/credential in audit projection")
    normalized = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {"digest_sha256": hashlib.sha256(normalized.encode()).hexdigest(),
            "event": dict(event),
            "audit_status": "UNSIGNED_SYNTHETIC_HASH_NOT_TAMPER_PROOF"}


def recovery_plan(effect_state: str, operation_class: str,
                  transport_error: str | None = None) -> str:
    """No unsafe replay; pending external effect must be reconciled."""
    if effect_state not in ALLOWED_STATES:
        raise ValueError("unknown effect state")
    if operation_class not in {"read_only", "external_effect"}:
        raise ValueError("unknown operation class")
    if effect_state == "VERIFIED":
        return "DONE"
    if operation_class == "external_effect":
        if effect_state in {"DISPATCHING", "UNKNOWN"}:
            return "RECONCILE_ONLY_NO_RESEND"
        if effect_state == "PRESENT":
            return "INDEPENDENT_READBACK"
        return "NO_AUTOMATIC_EXTERNAL_DISPATCH"
    if effect_state == "FAILED" and transport_error == "TRANSIENT":
        return "BOUNDED_READ_ONLY_RETRY"
    if effect_state in {"DISPATCHING", "UNKNOWN"}:
        return "READ_ONLY_REFRESH"
    if effect_state == "PRESENT":
        return "INDEPENDENT_READBACK"
    return "NO_ACTION"


def slo_budget(total: int, failures: int, success_target: Decimal) -> dict:
    """SLI = 1 - failures/eligible work; error budget is a count."""
    if (type(total) is not int or total <= 0 or type(failures) is not int
            or failures < 0 or failures > total
            or type(success_target) is not Decimal
            or not Decimal(0) < success_target < Decimal(1)):
        raise ValueError("invalid SLO inputs")
    allowance = int((Decimal(1) - success_target) * total)
    return {
        "eligible_total": total, "failures": failures, "allowed_failures": allowance,
        "remaining_error_budget": allowance - failures,
        "actual_success_rate": str(Decimal(total - failures) / Decimal(total)),
        "breached": failures > allowance,
        "source": "SYNTHETIC_ONLY",
    }


def runway_projection(cash_minor: int, monthly_net_burn_minor: int) -> dict:
    if (type(cash_minor) is not int or cash_minor < 0 or
            type(monthly_net_burn_minor) is not int):
        raise ValueError("invalid cash or burn")
    if monthly_net_burn_minor <= 0:
        return {"status": "NO_POSITIVE_NET_BURN", "months": None}
    return {"status": "MODELLED_ONLY",
            "months": str(Decimal(cash_minor) / Decimal(monthly_net_burn_minor))}


def cost_reconcile(provider_billed_minor: int, allocated_minor: int,
                   currency: str, source_ref: str) -> dict:
    if (any(type(x) is not int or x < 0 for x in
            (provider_billed_minor, allocated_minor))
            or allocated_minor > provider_billed_minor
            or currency != "USD" or not source_ref):
        raise ValueError("invalid currency/bill/allocation")
    return {
        "status": "COMPLETE" if allocated_minor == provider_billed_minor else "UNALLOCATED_REMAINS",
        "billed_minor": provider_billed_minor,
        "allocated_minor": allocated_minor,
        "unallocated_minor": provider_billed_minor - allocated_minor,
        "source_ref": source_ref,
        "is_real_invoice": False,
    }


def synthetic_demo() -> dict:
    portfolio = plan_portfolio(
        [Proposal("BFM_EVAL", 300, 400, 80),
         Proposal("PRODUCT_PILOT", 180, 320, 20),
         Proposal("UNLICENSED_MODEL", 100, 900, 100, False)],
        cash_minor=1000, reserve_minor=450, max_experiment_minor=500)
    req = PolicyInput(
        actor_id="sim-agent", tenant_id="sim", target_tenant_id="sim",
        action="read_synthetic", scope=frozenset({"read_synthetic"}),
        expires_at_utc=datetime(2026, 11, 8, tzinfo=timezone.utc),
        now_utc=datetime(2026, 11, 7, tzinfo=timezone.utc),
        revoked=False, consent_confirmed=True, requested_cost_minor=0,
        remaining_cap_minor=0, data_class="synthetic",
        policy_version="p10-3-demo-v1", is_external_effect=False)
    return {
        "kind": "ENTIRELY_SYNTHETIC",
        "P10-2": portfolio,
        "P10-3": policy_candidate(req),
        "P10-4": {
            "effect_unknown": recovery_plan("UNKNOWN", "external_effect"),
            "slo": slo_budget(1000, 3, Decimal("0.995")),
            "reconciliation": cost_reconcile(600, 580, "USD", "synthetic:provider-bill"),
            "runway": runway_projection(1000, 250),
        },
        "real_inference_or_external_effects": False,
    }


if __name__ == "__main__":
    print(json.dumps(synthetic_demo(), ensure_ascii=False, indent=2, sort_keys=True))
