"""P05-3/4/5: existing ManagerCore authority, durable outbox, reconciliation,
independent readback and SHADOW-only comparison; *no live customer actions*.

One deliberately bounded OfflineFixtureAdapter send is performed using an
explicit test-only grant, in a temporary SQLite database. Other requests
simulate expiry, revocation, cross-agent scope, transport uncertainty and
reconciliation without retries. A disabled-owned-provider shadow proves it
does not initialize a paid model or perform a website edit.

Do not import/use this module as a production tool adapter.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from unittest.mock import patch
import json
import sys

REPO = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO / "products" / "manager"))

from manager_core.authority import AuthorityVerifier, Grant
from manager_core.outbox import DurableOutbox
from manager_core.adapters.fixtures import OfflineFixtureAdapter, OfflineFixtureSensor
from manager_core.reconcile import Reconciler
from manager_core.verifier import verify_outcome
from manager_core.evaluator import evaluate_outcome
from manager_core.state_machine import State, StateMachine
from manager_core.owned_provider_shadow import compare_prepared_catalog_shadow
from manager_core.owned_provider_shadow import public_catalog_shadow_summary

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
FIXTURE_KEY = b"synthetic_fixture_signing_key_only_2026_no_real_credentials"
FIXTURE_ISSUER = "synthetic-issuer"
ACTION = "synthetic_observation"
TARGET = "synthetic:target-0001"
DOMAIN = "opportunity"
COST = 0.01


def grant_scope(*, revoked: bool = False, expired: bool = False,
                target: str = TARGET, limit: float = 0.05):
    """Return a signed OFFLINE fixture grant, never a real publisher grant."""
    authority = AuthorityVerifier(
        {FIXTURE_ISSUER: FIXTURE_KEY},
        revoked=("grant-synthetic-01",) if revoked else (),
    )
    grant = Grant(
        grant_id="grant-synthetic-01",
        issuer=FIXTURE_ISSUER,
        domain=DOMAIN,
        action=ACTION,
        target=target,
        limit=limit,
        not_before=NOW - timedelta(days=3),
        expires_at=NOW - timedelta(minutes=1) if expired
                   else NOW + timedelta(days=1),
    )
    signature = authority.sign_for_fixture(grant)
    return authority, grant, signature


def p05_3_authority_and_roles():
    """Separate agent proposal from bounded executor authority."""
    verifier, grant, signature = grant_scope()
    authorized = verifier.authorize(grant, signature, DOMAIN, ACTION, TARGET, COST, NOW)
    failures = {}

    def check(name, fn):
        try:
            fn()
        except PermissionError:
            failures[name] = "DENIED"
        else:
            raise AssertionError(f"{name}: authority escalation erroneously permitted")

    check("planner_cannot_choose_another_target",
          lambda: verifier.authorize(grant, signature, DOMAIN, ACTION,
                                     "synthetic:other-target", COST, NOW))
    check("planner_cannot_select_money_domain",
          lambda: verifier.authorize(grant, signature, "finance", ACTION,
                                     TARGET, COST, NOW))
    check("planner_cannot_exceed_single_grant",
          lambda: verifier.authorize(grant, signature, DOMAIN, ACTION,
                                     TARGET, 1.0, NOW))
    check("forged_signature",
          lambda: verifier.authorize(grant, "0"*64, DOMAIN, ACTION, TARGET, COST, NOW))
    check("expired", lambda: (
        lambda a, g, sig: a.authorize(g, sig, DOMAIN, ACTION, TARGET, COST, NOW)
    )(*grant_scope(expired=True)))
    check("revoked", lambda: (
        lambda a, g, sig: a.authorize(g, sig, DOMAIN, ACTION, TARGET, COST, NOW)
    )(*grant_scope(revoked=True)))

    return {
        "topic": "P05-3 role and authority",
        "authority_system": "EXISTING manager_core.authority.AuthorityVerifier",
        "fixture_grant_accepted": authorized,
        "negative_authority_cases": failures,
        "negative_cases_count": len(failures),
        "credential_used": "constant synthetic test key only",
        "planner_can_issue_real_authority": False,
        "live_provider_supported": False,
    }


def p05_4_outbox_recovery():
    """One fake provider effect, replay, uncertainty, reconciliation, readback.

    All SQLite files are created inside TemporaryDirectory; all provider
    adapters are exact OfflineFixtureAdapter, not real network implementations.
    """
    verifier, grant, signature = grant_scope()

    with TemporaryDirectory(prefix="manager-p05-safe-") as root:
        durable = DurableOutbox(Path(root) / "outbox.sqlite")
        fixture = OfflineFixtureAdapter(DOMAIN, ACTION, TARGET)

        first = durable.execute(
            "synthetic-effect-001", grant, signature, verifier, fixture, COST, NOW)
        second = durable.execute(
            "synthetic-effect-001", grant, signature, verifier, fixture, COST, NOW)
        assert first == second
        assert fixture.send_calls == 1
        assert first.status == "SUBMITTED"

        sensor = OfflineFixtureSensor(fixture)
        independent = sensor.readback(first.key, NOW + timedelta(seconds=15))
        verified = verify_outcome(first, independent)
        assert verified.status == "VERIFIED_FIXTURE_ONLY"
        assert verified.proof_level == "P0"

        # Receipt alone, or even an independent *fixture* readback is not
        # a randomized causal assessment of real human welfare.
        welfare = evaluate_outcome(
            effect=0, ci_lower=0, ci_upper=0, cost=COST,
            harm=None, comparator=None, metric_type="welfare")
        assert welfare.net_effect is None and welfare.status == "NO_COMPARATOR"

    with TemporaryDirectory(prefix="manager-p05-unknown-") as root:
        durable = DurableOutbox(Path(root) / "outbox.sqlite")
        fixture = OfflineFixtureAdapter(
            DOMAIN, ACTION, TARGET, timeout_after_effect=True)
        started = durable.execute(
            "synthetic-unknown-001", grant, signature, verifier, fixture, COST, NOW)
        assert started.status == "UNKNOWN" and fixture.send_calls == 1
        fixture.lookup_fails = True
        uncertain = Reconciler(durable).reconcile(started.key, fixture)
        assert uncertain.status == "UNKNOWN"
        replay = durable.execute(
            "synthetic-unknown-001", grant, signature, verifier, fixture, COST, NOW)
        assert fixture.send_calls == 1 and replay.status == "UNKNOWN"
        fixture.lookup_fails = False
        resolved = Reconciler(durable).reconcile(started.key, fixture)
        assert resolved.status == "PRESENT"
        no_retry = durable.execute(
            "synthetic-unknown-001", grant, signature, verifier, fixture, COST, NOW)
        assert no_retry.status == "PRESENT" and fixture.send_calls == 1

    return {
        "topic": "P05-4 independent verification and recovery",
        "outbox_class": "EXISTING manager_core.outbox.DurableOutbox",
        "reconciler_class": "EXISTING manager_core.reconcile.Reconciler",
        "verifier": "EXISTING manager_core.verifier.verify_outcome",
        "one_explicit_fixture_effect": {
            "first_status": first.status,
            "replayed_status": second.status,
            "provider_send_calls": 1,
            "result": verified.status,
            "proof_level": verified.proof_level,
            "human_effect": "NOT_MEASURED",
        },
        "uncertain_then_reconciled_fixture_effect": {
            "initial_status": started.status,
            "provider_lookup_failed_status": uncertain.status,
            "retry_send_calls": 0,
            "reconciled_status": resolved.status,
            "final_record_status": no_retry.status,
        },
        "independent_field_outcome_measured": False,
        "net_welfare_estimated": welfare.net_effect,
        "net_welfare_status": welfare.status,
        "all_mutations_within_temporary_fixture_sqlite": True,
    }


def p05_5_shadow_only():
    """Call the existing disabled shadow entrypoint, not a copied engine."""
    with patch(
        "manager_core.owned_provider_shadow.owned_catalog_planner.plan_catalog_change",
        side_effect=AssertionError("shadow must not trigger a new plan"),
    ), patch(
        "manager_core.owned_provider_shadow.CheckpointedProvider.__init__",
        side_effect=AssertionError("shadow must not initialize provider"),
    ):
        result = compare_prepared_catalog_shadow(
            checkpoint=None,
            prepared=None,
            now=NOW,
            run_id="515",
            enabled=False,
            deadline_monotonic=monotonic()+4,
            client_factory=lambda: (_ for _ in ()).throw(
                AssertionError("LLM must not be initialized")),
        )
    assert result["status"] == "SKIPPED" and result["reason"] == "DISABLED"
    # Existing public projection intentionally does not include provider raw text.
    projection = public_catalog_shadow_summary(result)
    return {
        "topic": "P05-5 shadow/inert release gate",
        "existing_shadow": "manager_core.owned_provider_shadow.compare_prepared_catalog_shadow",
        "status": result["status"],
        "reason": result["reason"],
        "public_projection_keys": sorted(projection),
        "llm_or_provider_calls": 0,
        "planned_real_limited_execution": "NOT AUTHORIZED OR PERFORMED",
        "shadow_candidate_quality": "NOT EVALUATED",
        "production_installation": False,
    }


def p05_5_state_machine():
    """No-action demonstration; never claims actual independent human proof."""
    m = StateMachine()
    m.transition(State.HYPOTHESIZED)
    m.transition(State.NO_ACTION)
    try:
        m.transition(State.EXECUTED)
    except ValueError:
        blocked = True
    else:
        raise AssertionError("terminal NO_ACTION incorrectly transitioned to live execution")
    return {
        "state_history": [state.value for state in m.history],
        "no_action_terminal": blocked,
        "live_authority_issued": False,
    }


def run():
    return {
        "suite": "P05-3–P05-5 existing Manager Core offline fixture",
        "source": "2026-11-04",
        "P05_3": p05_3_authority_and_roles(),
        "P05_4": p05_4_outbox_recovery(),
        "P05_5": p05_5_shadow_only(),
        "terminal_no_action": p05_5_state_machine(),
        "real_people_affected": 0,
        "real_external_service_mutations": 0,
        "real_company_decisions_delegated": 0,
        "actual_model_weights_trained": False,
        "external_field_RCT_completed": False,
        "production_feature_gate_accepted": False,
    }


if __name__ == "__main__":
    evidence = REPO / "docs/research/manager/masterclass/2026-11-04-p04-causal/evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    result = run()
    (evidence / "P05-3_5_EXISTING_CORE_OFFLINE_RESULTS.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
