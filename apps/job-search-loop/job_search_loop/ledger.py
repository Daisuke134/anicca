from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

from .ats import evaluate_snapshot
from .dedup import company_role_key
from .portfolio import PORTFOLIO_LIMITS
from .state import canonical_job_id, canonical_url, validate_transition
from .telemetry import Telemetry


LEGACY_STRATEGY = {"capture_status": "legacy_unavailable"}
LEGACY_STRATEGY_JSON = json.dumps(
    LEGACY_STRATEGY, ensure_ascii=False, sort_keys=True, separators=(",", ":")
)
LEGACY_STRATEGY_SHA256 = hashlib.sha256(
    LEGACY_STRATEGY_JSON.encode("utf-8")
).hexdigest()
LEGACY_STRATEGY_GENERATION_ID = f"strategy-{LEGACY_STRATEGY_SHA256}"
FUNNEL_STAGES = frozenset(
    {
        "confirmed_application",
        "recruiter_response",
        "screen",
        "interview",
        "final_round",
        "offer",
        "accepted",
        "declined",
        "started",
    }
)
FUNNEL_DISPOSITIONS = frozenset({"positive", "negative"})
AUTHORITATIVE_EVIDENCE_SOURCES = frozenset(
    {"ats", "gmail", "calendar", "employer_portal", "signed_document"}
)
APPLICATION_ARTIFACT_KINDS = frozenset(
    {
        "posting",
        "company_research",
        "resume_draft",
        "cover_letter_draft",
        "answers_draft",
    }
)
APPLICATION_OWNERS = frozenset({"agent", "dais_manual", "recruiter"})
OUTREACH_TRUTH_CORRECTION_REASON = "outreach_only_delivery_correction"
ASHBY_GRAPHQL_VISIBLE_SUCCESS_SOURCE = "ashby_graphql_plus_visible_success"
ASHBY_GRAPHQL_VISIBLE_SUCCESS_TERMINAL_SHA256 = (
    "e73a212752d3ca020b16bae36ca19578ba437dcf434b054daff414e467cb430b"
)


def _has_immutable_outreach_delivery(
    connection: sqlite3.Connection,
    *,
    application_id: str,
    route_id: str,
    provider_id: str,
    evidence_sha256: str,
) -> bool:
    route = connection.execute(
        """
        SELECT route_id
        FROM application_routes
        WHERE route_id = ?
          AND application_id = ?
          AND route_kind = 'recruiting_outreach'
          AND recipient_acceptance = 'outreach_only'
          AND delivery_state = 'delivered'
          AND provider_id = ?
          AND delivery_evidence_sha256 = ?
        """,
        (route_id, application_id, provider_id, evidence_sha256),
    ).fetchone()
    if route is None:
        return False
    delivery_events = connection.execute(
        """
        SELECT payload_json
        FROM application_route_events
        WHERE route_id = ?
          AND from_state = 'action_started'
          AND to_state = 'delivered'
        ORDER BY rowid
        """,
        (route_id,),
    ).fetchall()
    for delivery_event in delivery_events:
        try:
            payload = json.loads(str(delivery_event["payload_json"]))
        except (json.JSONDecodeError, TypeError):
            continue
        if (
            isinstance(payload, dict)
            and payload.get("provider_id") == provider_id
            and payload.get("evidence_sha256") == evidence_sha256
        ):
            return True
    return False


def _is_authoritative_submission_event(
    connection: sqlite3.Connection,
    application_id: str,
    event: Mapping[str, Any],
) -> bool:
    try:
        if str(event["to_state"]) != "submitted":
            return False
        payload = json.loads(str(event["payload_json"]))
    except (KeyError, json.JSONDecodeError, TypeError):
        return False
    return isinstance(payload, dict) and (
        all(payload.get(key) for key in (
            "message_id", "thread_id", "evidence_sha256", "received_at"
        ))
        or is_authoritative_ashby_browser_confirmation(
            connection, application_id, event
        )
    )


def _has_authoritative_submission_before(
    connection: sqlite3.Connection,
    application_id: str,
    event: Mapping[str, Any],
) -> bool:
    submission = connection.execute(
        "SELECT rowid AS event_rowid, from_state, to_state, payload_json "
        "FROM events WHERE application_id = ? AND rowid < ? "
        "ORDER BY rowid DESC LIMIT 1",
        (application_id, int(event["event_rowid"])),
    ).fetchone()
    return submission is not None and _is_authoritative_submission_event(
        connection, application_id, submission
    )


def is_outreach_truth_correction(
    connection: sqlite3.Connection,
    application_id: str,
    correction_event: Mapping[str, Any],
) -> bool:
    """Return whether one immutable event corrects an outreach-only regression."""
    try:
        correction_rowid = int(correction_event["event_rowid"])
    except (KeyError, TypeError, ValueError):
        return False
    correction = connection.execute(
        """
        SELECT rowid AS event_rowid, from_state, to_state, payload_json
        FROM events
        WHERE application_id = ? AND rowid = ?
        """,
        (application_id, correction_rowid),
    ).fetchone()
    if correction is None or str(correction["to_state"]) != "submit_unknown":
        return False
    correction_from = str(correction["from_state"])
    if correction_from not in {"submitted", "email_sent"}:
        return False
    try:
        payload = json.loads(str(correction["payload_json"]))
    except (json.JSONDecodeError, TypeError):
        return False
    if (
        not isinstance(payload, dict)
        or payload.get("reason") != OUTREACH_TRUTH_CORRECTION_REASON
    ):
        return False
    route_id = payload.get("route_id")
    provider_id = payload.get("provider_id")
    evidence_sha256 = payload.get("evidence_sha256")
    if not all(
        isinstance(value, str) and value
        for value in (route_id, provider_id, evidence_sha256)
    ):
        return False
    previous = connection.execute(
        """
        SELECT rowid AS event_rowid, from_state, to_state, payload_json
        FROM events
        WHERE application_id = ? AND rowid < ?
        ORDER BY rowid DESC
        LIMIT 1
        """,
        (application_id, correction_rowid),
    ).fetchone()
    expected_previous = (
        ("submit_unknown", "submitted")
        if correction_from == "submitted"
        else ("submitted", "email_sent")
    )
    if previous is None or (
        str(previous["from_state"]), str(previous["to_state"])
    ) != expected_previous:
        return False
    try:
        previous_payload = json.loads(str(previous["payload_json"]))
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(previous_payload, dict):
        return False
    if (
        previous_payload.get("route_id") != route_id
        or previous_payload.get("provider_id") != provider_id
        or previous_payload.get("channel") != "recruiting_outreach"
    ):
        return False
    if correction_from == "submitted" and all(
        previous_payload.get(key)
        for key in ("message_id", "thread_id", "evidence_sha256", "received_at")
    ):
        return False
    if correction_from == "email_sent" and (
        "evidence_sha256" in previous_payload
        and previous_payload.get("evidence_sha256") != evidence_sha256
    ):
        return False
    if correction_from == "email_sent" and _has_authoritative_submission_before(
        connection, application_id, previous
    ):
        return False
    return _has_immutable_outreach_delivery(
        connection,
        application_id=application_id,
        route_id=route_id,
        provider_id=provider_id,
        evidence_sha256=evidence_sha256,
    )


def is_authoritative_ashby_browser_confirmation(
    connection: sqlite3.Connection,
    application_id: str,
    confirmation_event: Mapping[str, Any],
) -> bool:
    """Return whether an immutable event is bound to the observed Ashby success."""
    try:
        event_rowid = int(confirmation_event["event_rowid"])
    except (KeyError, TypeError, ValueError):
        return False
    event = connection.execute(
        """
        SELECT from_state, to_state, payload_json
        FROM events
        WHERE application_id = ? AND rowid = ?
        """,
        (application_id, event_rowid),
    ).fetchone()
    if (
        event is None
        or str(event["from_state"]) != "submit_unknown"
        or str(event["to_state"]) != "submitted"
    ):
        return False
    try:
        payload = json.loads(str(event["payload_json"]))
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(payload, dict):
        return False
    intent_id = payload.get("intent_id")
    fence = payload.get("fence")
    evidence_sha256 = payload.get("evidence_sha256")
    if (
        payload.get("evidence_source") != ASHBY_GRAPHQL_VISIBLE_SUCCESS_SOURCE
        or not isinstance(intent_id, str)
        or not intent_id
        or isinstance(fence, bool)
        or not isinstance(fence, int)
        or fence <= 0
        or not isinstance(evidence_sha256, str)
        or evidence_sha256 != ASHBY_GRAPHQL_VISIBLE_SUCCESS_TERMINAL_SHA256
    ):
        return False
    bound = connection.execute(
        """
        SELECT 1
        FROM submit_intents AS intents
        JOIN submission_attempts AS attempts
          ON attempts.intent_id = intents.intent_id
         AND attempts.fence = intents.fence
         AND attempts.application_id = intents.application_id
        JOIN submission_material_receipts AS materials
          ON materials.intent_id = intents.intent_id
         AND materials.fence = intents.fence
         AND materials.application_id = intents.application_id
        JOIN submission_click_phases AS click_phases
          ON click_phases.intent_id = intents.intent_id
         AND click_phases.fence = intents.fence
        JOIN submission_transport_phases AS transport_phases
          ON transport_phases.intent_id = intents.intent_id
         AND transport_phases.fence = intents.fence
        WHERE intents.intent_id = ?
          AND intents.application_id = ?
          AND intents.fence = ?
          AND intents.status = 'submitted'
          AND attempts.status = 'submitted'
          AND click_phases.phase = 'confirmed'
          AND transport_phases.phase = 'request_started'
        """,
        (
            intent_id,
            application_id,
            fence,
        ),
    ).fetchone()
    return bound is not None


FOUNDER_OUTREACH_TRANSITIONS = {
    "researched": frozenset({"contribution_ready", "proposal_ready", "closed"}),
    "contribution_ready": frozenset({"outreach_sent", "closed"}),
    "outreach_sent": frozenset({"replied", "closed"}),
    "replied": frozenset(
        {"proposal_ready", "paid_trial", "contract", "employment", "closed"}
    ),
    "proposal_ready": frozenset({"outreach_sent", "closed"}),
    "paid_trial": frozenset({"contract", "employment", "closed"}),
    "contract": frozenset({"employment", "closed"}),
}


class FenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class SubmitIntent:
    intent_id: str
    application_id: str
    fence: int
    payload_hash: str
    resume_path: str
    resume_sha256: str
    ats_snapshot_path: str
    ats_snapshot_sha256: str
    fill_receipt_path: str
    fill_receipt_sha256: str
    japan_day: str
    slot: int


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    def __init__(self, path: Path, telemetry: Any = None):
        self.path = Path(path)
        self.telemetry = telemetry or Telemetry()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        self.connection = sqlite3.connect(
            self.path, timeout=10, isolation_level=None
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                canonical_url TEXT NOT NULL,
                owner TEXT NOT NULL DEFAULT 'agent'
                    CHECK (owner IN ('agent', 'dais_manual', 'recruiter')),
                current_state TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS applications_canonical_url_unique
            ON applications(canonical_url);
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL REFERENCES applications(id),
                from_state TEXT,
                to_state TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS submit_intents (
                intent_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL UNIQUE REFERENCES applications(id),
                fence INTEGER NOT NULL,
                payload_hash TEXT NOT NULL,
                resume_path TEXT,
                resume_sha256 TEXT,
                ats_snapshot_path TEXT,
                ats_snapshot_sha256 TEXT,
                fill_receipt_path TEXT,
                fill_receipt_sha256 TEXT,
                japan_day TEXT NOT NULL,
                slot INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS daily_slots (
                japan_day TEXT NOT NULL,
                slot INTEGER NOT NULL,
                application_id TEXT NOT NULL UNIQUE REFERENCES applications(id),
                portfolio_bucket TEXT NOT NULL DEFAULT 'legacy_unallocated',
                status TEXT NOT NULL,
                PRIMARY KEY (japan_day, slot)
            );
            CREATE TABLE IF NOT EXISTS daily_quota_events (
                event_id TEXT PRIMARY KEY,
                japan_day TEXT NOT NULL,
                confirmed_count INTEGER NOT NULL,
                deficit_count INTEGER NOT NULL,
                portfolio_confirmed_json TEXT NOT NULL,
                portfolio_deficit_json TEXT NOT NULL,
                reason TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL UNIQUE,
                observed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS external_application_imports (
                application_id TEXT PRIMARY KEY REFERENCES applications(id),
                owner TEXT NOT NULL CHECK (owner IN ('dais_manual', 'recruiter')),
                source TEXT NOT NULL,
                source_message_id TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL UNIQUE,
                posting_alias TEXT NOT NULL UNIQUE,
                imported_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS founder_outreach_targets (
                target_id TEXT PRIMARY KEY,
                company TEXT NOT NULL,
                relationship_url TEXT NOT NULL UNIQUE,
                current_state TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS founder_outreach_events (
                event_id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL REFERENCES founder_outreach_targets(target_id),
                from_state TEXT,
                to_state TEXT NOT NULL,
                evidence_source TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (target_id, evidence_source, evidence_id, evidence_sha256)
            );
            CREATE TABLE IF NOT EXISTS submission_attempts (
                intent_id TEXT NOT NULL REFERENCES submit_intents(intent_id),
                fence INTEGER NOT NULL,
                application_id TEXT NOT NULL REFERENCES applications(id),
                payload_hash TEXT NOT NULL,
                resume_path TEXT,
                resume_sha256 TEXT,
                ats_snapshot_path TEXT,
                ats_snapshot_sha256 TEXT,
                fill_receipt_path TEXT,
                fill_receipt_sha256 TEXT,
                japan_day TEXT NOT NULL,
                slot INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                PRIMARY KEY (intent_id, fence)
            );
            CREATE TABLE IF NOT EXISTS submission_material_receipts (
                intent_id TEXT NOT NULL,
                fence INTEGER NOT NULL,
                application_id TEXT NOT NULL REFERENCES applications(id),
                resume_path TEXT NOT NULL,
                resume_sha256 TEXT NOT NULL,
                cover_letter TEXT,
                employer_answers_json TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL UNIQUE,
                recorded_at TEXT NOT NULL,
                PRIMARY KEY (intent_id, fence),
                FOREIGN KEY (intent_id, fence)
                    REFERENCES submission_attempts(intent_id, fence)
            );
            CREATE TABLE IF NOT EXISTS submission_click_phases (
                intent_id TEXT NOT NULL,
                fence INTEGER NOT NULL,
                phase TEXT NOT NULL CHECK (phase IN
                    ('pre_click', 'clicked', 'confirmed')),
                updated_at TEXT NOT NULL,
                PRIMARY KEY (intent_id, fence),
                FOREIGN KEY (intent_id, fence)
                    REFERENCES submission_attempts(intent_id, fence)
            );
            CREATE TABLE IF NOT EXISTS submission_transport_phases (
                intent_id TEXT NOT NULL,
                fence INTEGER NOT NULL,
                phase TEXT NOT NULL CHECK (phase IN
                    ('pre_request', 'request_started')),
                updated_at TEXT NOT NULL,
                PRIMARY KEY (intent_id, fence),
                FOREIGN KEY (intent_id, fence)
                    REFERENCES submission_attempts(intent_id, fence)
            );
            CREATE TABLE IF NOT EXISTS submission_client_block_receipts (
                intent_id TEXT NOT NULL,
                fence INTEGER NOT NULL,
                blocker TEXT NOT NULL CHECK (blocker IN
                    ('ashby_recaptcha_before_submit_request')),
                evidence_sha256 TEXT NOT NULL UNIQUE,
                recorded_at TEXT NOT NULL,
                PRIMARY KEY (intent_id, fence),
                FOREIGN KEY (intent_id, fence)
                    REFERENCES submission_attempts(intent_id, fence)
            );
            CREATE TABLE IF NOT EXISTS submission_confirmations (
                message_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                intent_id TEXT NOT NULL UNIQUE
                    REFERENCES submit_intents(intent_id),
                evidence_sha256 TEXT NOT NULL,
                received_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS submission_evidence_bundles (
                intent_id TEXT NOT NULL,
                fence INTEGER NOT NULL,
                application_id TEXT NOT NULL REFERENCES applications(id),
                pre_submit_path TEXT NOT NULL,
                pre_submit_sha256 TEXT NOT NULL,
                post_action_path TEXT NOT NULL,
                post_action_sha256 TEXT NOT NULL,
                terminal_path TEXT NOT NULL,
                terminal_sha256 TEXT NOT NULL,
                confirmation_path TEXT NOT NULL,
                confirmation_sha256 TEXT NOT NULL,
                confirmation_source TEXT NOT NULL CHECK
                    (confirmation_source IN ('ats', 'gmail')),
                confirmation_id TEXT NOT NULL,
                bundle_sha256 TEXT NOT NULL UNIQUE,
                recorded_at TEXT NOT NULL,
                PRIMARY KEY (intent_id, fence),
                FOREIGN KEY (intent_id, fence)
                    REFERENCES submission_attempts(intent_id, fence)
            );
            CREATE TABLE IF NOT EXISTS application_routes (
                route_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL REFERENCES applications(id),
                cross_route_key TEXT NOT NULL,
                ordinal INTEGER NOT NULL CHECK (ordinal > 0),
                route_kind TEXT NOT NULL CHECK (route_kind IN
                    ('canonical_ats', 'alternate_official',
                     'recruiting_email', 'recruiting_outreach')),
                endpoint TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                recipient_acceptance TEXT NOT NULL CHECK (recipient_acceptance IN
                    ('not_applicable', 'accepts_applications', 'outreach_only')),
                delivery_state TEXT NOT NULL CHECK (delivery_state IN
                    ('eligible', 'action_started', 'failed', 'delivered',
                     'delivery_unknown', 'replied')),
                actor TEXT,
                fence INTEGER,
                message_path TEXT,
                message_sha256 TEXT,
                resume_path TEXT,
                resume_sha256 TEXT,
                provider_id TEXT,
                delivery_evidence_sha256 TEXT,
                reply_provider_id TEXT,
                reply_evidence_sha256 TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (application_id, route_kind, endpoint),
                UNIQUE (cross_route_key, ordinal)
            );
            DROP INDEX IF EXISTS application_routes_one_live_action;
            CREATE UNIQUE INDEX IF NOT EXISTS application_routes_one_live_action_per_class
            ON application_routes(
                cross_route_key,
                CASE
                    WHEN route_kind IN ('canonical_ats', 'alternate_official')
                    THEN 'ats'
                    ELSE 'email'
                END
            )
            WHERE delivery_state IN
                ('action_started', 'delivered', 'delivery_unknown', 'replied');
            CREATE TABLE IF NOT EXISTS application_route_events (
                event_id TEXT PRIMARY KEY,
                route_id TEXT NOT NULL REFERENCES application_routes(route_id),
                from_state TEXT,
                to_state TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TRIGGER IF NOT EXISTS application_route_events_no_update
            BEFORE UPDATE ON application_route_events
            BEGIN
                SELECT RAISE(ABORT, 'application route events are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS application_route_events_no_delete
            BEFORE DELETE ON application_route_events
            BEGIN
                SELECT RAISE(ABORT, 'application route events are immutable');
            END;
            CREATE TABLE IF NOT EXISTS gmail_application_matches (
                message_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                application_id TEXT NOT NULL REFERENCES applications(id),
                evidence_sha256 TEXT NOT NULL,
                identifier_sha256 TEXT NOT NULL,
                received_at TEXT NOT NULL,
                matched_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS gmail_match_decisions (
                message_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                application_id TEXT REFERENCES applications(id),
                status TEXT NOT NULL CHECK (status IN
                    ('matched', 'no_match', 'ambiguous', 'insufficient_evidence')),
                evidence_sha256 TEXT NOT NULL,
                identifier_sha256 TEXT NOT NULL,
                received_at TEXT NOT NULL,
                decided_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS strategy_generations (
                strategy_generation_id TEXT PRIMARY KEY,
                parent_generation_id TEXT
                    REFERENCES strategy_generations(strategy_generation_id),
                changed_field TEXT,
                strategy_json TEXT NOT NULL,
                strategy_sha256 TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS application_strategy_assignments (
                application_id TEXT PRIMARY KEY
                    REFERENCES applications(id),
                strategy_generation_id TEXT NOT NULL
                    REFERENCES strategy_generations(strategy_generation_id),
                capture_status TEXT NOT NULL,
                source TEXT NOT NULL,
                query_family TEXT NOT NULL,
                rank_config_json TEXT,
                role_family TEXT NOT NULL,
                material_variant TEXT NOT NULL,
                message_variant TEXT NOT NULL,
                model_route TEXT NOT NULL,
                prompt_sha256 TEXT,
                material_sha256 TEXT,
                assigned_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS funnel_outcomes (
                outcome_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL
                    REFERENCES applications(id),
                funnel_stage TEXT NOT NULL,
                disposition TEXT NOT NULL,
                evidence_source TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                observation_policy_version TEXT,
                created_at TEXT NOT NULL,
                UNIQUE (application_id, funnel_stage, evidence_sha256)
            );
            CREATE TABLE IF NOT EXISTS strategy_outcome_projection (
                strategy_generation_id TEXT NOT NULL
                    REFERENCES strategy_generations(strategy_generation_id),
                funnel_stage TEXT NOT NULL,
                positive_count INTEGER NOT NULL,
                negative_count INTEGER NOT NULL,
                resolved_count INTEGER NOT NULL,
                PRIMARY KEY (strategy_generation_id, funnel_stage)
            );
            CREATE TABLE IF NOT EXISTS strategy_experiments (
                experiment_id TEXT PRIMARY KEY,
                baseline_generation_id TEXT NOT NULL
                    REFERENCES strategy_generations(strategy_generation_id),
                candidate_generation_id TEXT NOT NULL UNIQUE
                    REFERENCES strategy_generations(strategy_generation_id),
                changed_field TEXT NOT NULL,
                metric_stage TEXT NOT NULL,
                replay_manifest_sha256 TEXT NOT NULL,
                replay_case_count INTEGER NOT NULL,
                replay_violations INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS strategy_learning_control (
                scope TEXT PRIMARY KEY,
                active_generation_id TEXT NOT NULL
                    REFERENCES strategy_generations(strategy_generation_id),
                experiment_id TEXT
                    REFERENCES strategy_experiments(experiment_id),
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS learning_execution_events (
                event_id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL
                    REFERENCES strategy_experiments(experiment_id),
                candidate_generation_id TEXT NOT NULL
                    REFERENCES strategy_generations(strategy_generation_id),
                outcome TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (experiment_id, evidence_sha256)
            );
            CREATE TABLE IF NOT EXISTS learning_decisions (
                decision_id TEXT PRIMARY KEY,
                experiment_id TEXT NOT NULL
                    REFERENCES strategy_experiments(experiment_id),
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                metric_stage TEXT NOT NULL,
                active_before_generation_id TEXT NOT NULL
                    REFERENCES strategy_generations(strategy_generation_id),
                active_after_generation_id TEXT NOT NULL
                    REFERENCES strategy_generations(strategy_generation_id),
                snapshot_sha256 TEXT NOT NULL UNIQUE,
                receipt_sha256 TEXT NOT NULL UNIQUE,
                report_json TEXT NOT NULL,
                decided_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS application_artifacts (
                artifact_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL REFERENCES applications(id),
                kind TEXT NOT NULL,
                path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                fact_ids_json TEXT NOT NULL,
                source_urls_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (application_id, kind, sha256)
            );
            CREATE TABLE IF NOT EXISTS application_ranked_gaps (
                application_id TEXT PRIMARY KEY REFERENCES applications(id),
                score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
                gaps_json TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS application_followups (
                followup_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL REFERENCES applications(id),
                ordinal INTEGER NOT NULL CHECK (ordinal IN (1, 2)),
                sent_at TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (application_id, ordinal)
            );
            CREATE TRIGGER IF NOT EXISTS application_artifacts_no_update
            BEFORE UPDATE ON application_artifacts
            BEGIN
                SELECT RAISE(ABORT, 'application artifacts are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS daily_quota_events_no_update
            BEFORE UPDATE ON daily_quota_events
            BEGIN
                SELECT RAISE(ABORT, 'daily quota events are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS daily_quota_events_no_delete
            BEFORE DELETE ON daily_quota_events
            BEGIN
                SELECT RAISE(ABORT, 'daily quota events are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS applications_owner_no_update
            BEFORE UPDATE OF owner ON applications
            WHEN NEW.owner != OLD.owner
            BEGIN
                SELECT RAISE(ABORT, 'application owner is immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS external_application_imports_no_update
            BEFORE UPDATE ON external_application_imports
            BEGIN
                SELECT RAISE(ABORT, 'external application imports are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS external_application_imports_no_delete
            BEFORE DELETE ON external_application_imports
            BEGIN
                SELECT RAISE(ABORT, 'external application imports are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS founder_outreach_events_no_update
            BEFORE UPDATE ON founder_outreach_events
            BEGIN
                SELECT RAISE(ABORT, 'founder outreach events are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS founder_outreach_events_no_delete
            BEFORE DELETE ON founder_outreach_events
            BEGIN
                SELECT RAISE(ABORT, 'founder outreach events are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS application_artifacts_no_delete
            BEFORE DELETE ON application_artifacts
            BEGIN
                SELECT RAISE(ABORT, 'application artifacts are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS application_ranked_gaps_no_update
            BEFORE UPDATE ON application_ranked_gaps
            BEGIN
                SELECT RAISE(ABORT, 'application ranked gaps are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS application_ranked_gaps_no_delete
            BEFORE DELETE ON application_ranked_gaps
            BEGIN
                SELECT RAISE(ABORT, 'application ranked gaps are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS application_followups_no_update
            BEFORE UPDATE ON application_followups
            BEGIN
                SELECT RAISE(ABORT, 'application followups are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS application_followups_no_delete
            BEFORE DELETE ON application_followups
            BEGIN
                SELECT RAISE(ABORT, 'application followups are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS strategy_generations_no_update
            BEFORE UPDATE ON strategy_generations
            BEGIN
                SELECT RAISE(ABORT, 'strategy generations are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS strategy_generations_no_delete
            BEFORE DELETE ON strategy_generations
            BEGIN
                SELECT RAISE(ABORT, 'strategy generations are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS strategy_assignments_no_update
            BEFORE UPDATE ON application_strategy_assignments
            BEGIN
                SELECT RAISE(ABORT, 'strategy assignments are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS strategy_assignments_no_delete
            BEFORE DELETE ON application_strategy_assignments
            BEGIN
                SELECT RAISE(ABORT, 'strategy assignments are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS funnel_outcomes_no_update
            BEFORE UPDATE ON funnel_outcomes
            BEGIN
                SELECT RAISE(ABORT, 'funnel outcomes are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS funnel_outcomes_no_delete
            BEFORE DELETE ON funnel_outcomes
            BEGIN
                SELECT RAISE(ABORT, 'funnel outcomes are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS strategy_experiments_no_update
            BEFORE UPDATE ON strategy_experiments
            BEGIN
                SELECT RAISE(ABORT, 'strategy experiments are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS strategy_experiments_no_delete
            BEFORE DELETE ON strategy_experiments
            BEGIN
                SELECT RAISE(ABORT, 'strategy experiments are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS learning_execution_events_no_update
            BEFORE UPDATE ON learning_execution_events
            BEGIN
                SELECT RAISE(ABORT, 'learning execution events are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS learning_execution_events_no_delete
            BEFORE DELETE ON learning_execution_events
            BEGIN
                SELECT RAISE(ABORT, 'learning execution events are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS learning_decisions_no_update
            BEFORE UPDATE ON learning_decisions
            BEGIN
                SELECT RAISE(ABORT, 'learning decisions are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS learning_decisions_no_delete
            BEFORE DELETE ON learning_decisions
            BEGIN
                SELECT RAISE(ABORT, 'learning decisions are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS gmail_application_matches_no_update
            BEFORE UPDATE ON gmail_application_matches
            BEGIN
                SELECT RAISE(ABORT, 'Gmail application matches are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS submission_material_receipts_no_update
            BEFORE UPDATE ON submission_material_receipts
            BEGIN
                SELECT RAISE(ABORT, 'submission material receipts are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS submission_material_receipts_no_delete
            BEFORE DELETE ON submission_material_receipts
            BEGIN
                SELECT RAISE(ABORT, 'submission material receipts are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS events_no_update
            BEFORE UPDATE ON events
            BEGIN
                SELECT RAISE(ABORT, 'application events are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS events_no_delete
            BEFORE DELETE ON events
            BEGIN
                SELECT RAISE(ABORT, 'application events are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS applications_identity_no_update
            BEFORE UPDATE OF company, title, canonical_url ON applications
            BEGIN
                SELECT RAISE(ABORT, 'application identity is immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS applications_state_requires_event
            BEFORE UPDATE OF current_state ON applications
            WHEN NEW.current_state != (
                SELECT to_state FROM events
                WHERE application_id = OLD.id ORDER BY rowid DESC LIMIT 1
            )
            BEGIN
                SELECT RAISE(ABORT, 'application state requires matching event');
            END;
            CREATE TRIGGER IF NOT EXISTS gmail_application_matches_no_delete
            BEFORE DELETE ON gmail_application_matches
            BEGIN
                SELECT RAISE(ABORT, 'Gmail application matches are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS gmail_match_decisions_no_update
            BEFORE UPDATE ON gmail_match_decisions
            BEGIN
                SELECT RAISE(ABORT, 'Gmail match decisions are immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS gmail_match_decisions_no_delete
            BEFORE DELETE ON gmail_match_decisions
            BEGIN
                SELECT RAISE(ABORT, 'Gmail match decisions are immutable');
            END;
            """
        )
        self._migrate_funnel_outcome_evidence_constraint()
        application_columns = {
            str(row["name"])
            for row in self.connection.execute("PRAGMA table_info(applications)")
        }
        if "owner" not in application_columns:
            self.connection.execute(
                "ALTER TABLE applications ADD COLUMN owner TEXT NOT NULL "
                "DEFAULT 'agent' CHECK (owner IN "
                "('agent', 'dais_manual', 'recruiter'))"
            )
        intent_columns = {
            str(row["name"])
            for row in self.connection.execute("PRAGMA table_info(submit_intents)")
        }
        if "resume_path" not in intent_columns:
            self.connection.execute(
                "ALTER TABLE submit_intents ADD COLUMN resume_path TEXT"
            )
        if "resume_sha256" not in intent_columns:
            self.connection.execute(
                "ALTER TABLE submit_intents ADD COLUMN resume_sha256 TEXT"
            )
        if "ats_snapshot_path" not in intent_columns:
            self.connection.execute(
                "ALTER TABLE submit_intents ADD COLUMN ats_snapshot_path TEXT"
            )
        if "ats_snapshot_sha256" not in intent_columns:
            self.connection.execute(
                "ALTER TABLE submit_intents ADD COLUMN ats_snapshot_sha256 TEXT"
            )
        if "fill_receipt_path" not in intent_columns:
            self.connection.execute(
                "ALTER TABLE submit_intents ADD COLUMN fill_receipt_path TEXT"
            )
        if "fill_receipt_sha256" not in intent_columns:
            self.connection.execute(
                "ALTER TABLE submit_intents ADD COLUMN fill_receipt_sha256 TEXT"
            )
        attempt_columns = {
            str(row["name"])
            for row in self.connection.execute("PRAGMA table_info(submission_attempts)")
        }
        if "fill_receipt_path" not in attempt_columns:
            self.connection.execute(
                "ALTER TABLE submission_attempts ADD COLUMN fill_receipt_path TEXT"
            )
        if "fill_receipt_sha256" not in attempt_columns:
            self.connection.execute(
                "ALTER TABLE submission_attempts ADD COLUMN fill_receipt_sha256 TEXT"
            )
        slot_columns = {
            str(row["name"])
            for row in self.connection.execute("PRAGMA table_info(daily_slots)")
        }
        if "portfolio_bucket" not in slot_columns:
            self.connection.execute(
                "ALTER TABLE daily_slots ADD COLUMN portfolio_bucket TEXT "
                "NOT NULL DEFAULT 'legacy_unallocated'"
            )
        for table in (
            "events", "application_route_events", "submission_evidence_bundles"
        ):
            correlation_columns = {
                str(row["name"])
                for row in self.connection.execute(f"PRAGMA table_info({table})")
            }
            for column in ("trace_id", "span_id"):
                if column not in correlation_columns:
                    self.connection.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} TEXT"
                    )
        self.connection.execute(
            """
            INSERT OR IGNORE INTO submission_attempts
              (intent_id, fence, application_id, payload_hash, resume_path,
               resume_sha256, ats_snapshot_path, ats_snapshot_sha256,
               fill_receipt_path, fill_receipt_sha256,
               japan_day, slot, status, created_at, completed_at)
            SELECT
              intent_id, fence, application_id, payload_hash, resume_path,
              resume_sha256, ats_snapshot_path, ats_snapshot_sha256,
              fill_receipt_path, fill_receipt_sha256,
              japan_day, slot, status, created_at, completed_at
            FROM submit_intents
            """
        )
        self.connection.execute(
            """
            INSERT OR IGNORE INTO submission_click_phases
              (intent_id, fence, phase, updated_at)
            SELECT intent_id, fence,
              CASE status
                WHEN 'submitted' THEN 'confirmed'
                WHEN 'submit_unknown' THEN 'clicked'
                ELSE 'pre_click'
              END,
              COALESCE(completed_at, created_at)
            FROM submission_attempts
            """
        )
        self.connection.execute(
            """
            INSERT OR IGNORE INTO submission_transport_phases
              (intent_id, fence, phase, updated_at)
            SELECT intent_id, fence,
              CASE status
                WHEN 'submitted' THEN 'request_started'
                WHEN 'submit_unknown' THEN 'request_started'
                ELSE 'pre_request'
              END,
              COALESCE(completed_at, created_at)
            FROM submission_attempts
            """
        )
        migration_time = _now()
        self.connection.execute(
            """
            INSERT OR IGNORE INTO strategy_generations
              (strategy_generation_id, parent_generation_id, changed_field,
               strategy_json, strategy_sha256, created_at)
            VALUES (?, NULL, NULL, ?, ?, ?)
            """,
            (
                LEGACY_STRATEGY_GENERATION_ID,
                LEGACY_STRATEGY_JSON,
                LEGACY_STRATEGY_SHA256,
                migration_time,
            ),
        )
        self.connection.execute(
            """
            INSERT OR IGNORE INTO application_strategy_assignments
              (application_id, strategy_generation_id, capture_status, source,
               query_family, rank_config_json, role_family, material_variant,
               message_variant, model_route, prompt_sha256, material_sha256,
               assigned_at)
            SELECT
              applications.id, ?, 'legacy_unavailable', 'legacy_unavailable',
              'legacy_unavailable', NULL, 'legacy_unavailable',
              'legacy_unavailable', 'legacy_unavailable', 'legacy_unavailable',
              NULL, NULL, applications.created_at
            FROM applications
            """,
            (LEGACY_STRATEGY_GENERATION_ID,),
        )
        if self.path.exists():
            os.chmod(self.path, 0o600)

    def _migrate_funnel_outcome_evidence_constraint(self) -> None:
        has_single_evidence_unique = False
        for index in self.connection.execute(
            "PRAGMA index_list(funnel_outcomes)"
        ).fetchall():
            if not bool(index["unique"]):
                continue
            index_name = str(index["name"]).replace("'", "''")
            columns = [
                str(row["name"])
                for row in self.connection.execute(
                    f"PRAGMA index_info('{index_name}')"
                ).fetchall()
            ]
            if columns == ["evidence_sha256"]:
                has_single_evidence_unique = True
                break
        if not has_single_evidence_unique:
            return
        self.connection.executescript(
            """
            BEGIN IMMEDIATE;
            DROP TRIGGER IF EXISTS funnel_outcomes_no_update;
            DROP TRIGGER IF EXISTS funnel_outcomes_no_delete;
            ALTER TABLE funnel_outcomes
              RENAME TO funnel_outcomes_single_evidence_unique;
            CREATE TABLE funnel_outcomes (
                outcome_id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL
                    REFERENCES applications(id),
                funnel_stage TEXT NOT NULL,
                disposition TEXT NOT NULL,
                evidence_source TEXT NOT NULL,
                evidence_sha256 TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                observation_policy_version TEXT,
                created_at TEXT NOT NULL,
                UNIQUE (application_id, funnel_stage, evidence_sha256)
            );
            INSERT INTO funnel_outcomes
              (outcome_id, application_id, funnel_stage, disposition,
               evidence_source, evidence_sha256, occurred_at, observed_at,
               observation_policy_version, created_at)
            SELECT
              outcome_id, application_id, funnel_stage, disposition,
              evidence_source, evidence_sha256, occurred_at, observed_at,
              observation_policy_version, created_at
            FROM funnel_outcomes_single_evidence_unique;
            DROP TABLE funnel_outcomes_single_evidence_unique;
            CREATE TRIGGER funnel_outcomes_no_update
            BEFORE UPDATE ON funnel_outcomes
            BEGIN
                SELECT RAISE(ABORT, 'funnel outcomes are immutable');
            END;
            CREATE TRIGGER funnel_outcomes_no_delete
            BEFORE DELETE ON funnel_outcomes
            BEGIN
                SELECT RAISE(ABORT, 'funnel outcomes are immutable');
            END;
            COMMIT;
            """
        )

    def close(self) -> None:
        self.connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def _append_event(
        self,
        application_id: str,
        from_state: str | None,
        to_state: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        correlation = self._current_correlation()
        self.connection.execute(
            """
            INSERT INTO events
              (event_id, application_id, from_state, to_state, payload_json, created_at,
               trace_id, span_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                application_id,
                from_state,
                to_state,
                json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
                _now(),
                correlation["trace_id"], correlation["span_id"],
            ),
        )

    def _current_correlation(self) -> dict[str, str | None]:
        getter = getattr(self.telemetry, "current_correlation", None)
        try:
            value = getter() if callable(getter) else {}
        except Exception:
            value = {}
        trace_id, span_id = value.get("trace_id"), value.get("span_id")
        return {
            "trace_id": trace_id if re.fullmatch(r"[a-f0-9]{32}", str(trace_id or "")) else None,
            "span_id": span_id if re.fullmatch(r"[a-f0-9]{16}", str(span_id or "")) else None,
        }

    def add_application(
        self,
        company: str,
        title: str,
        url: str,
        *,
        owner: str = "agent",
    ) -> str:
        if owner not in APPLICATION_OWNERS:
            raise ValueError("owner must be agent, dais_manual, or recruiter")
        normalized_url = canonical_url(url)
        application_id = canonical_job_id(company, title, normalized_url)
        posting_alias = self._posting_alias(company, title)
        with self._transaction():
            imported = self.connection.execute(
                "SELECT application_id, owner FROM external_application_imports "
                "WHERE posting_alias = ?",
                (posting_alias,),
            ).fetchone()
            if imported is not None:
                imported_owner = str(imported["owner"])
                if imported_owner != owner:
                    raise FenceError(
                        f"canonical posting is already owned by {imported_owner}"
                    )
                return str(imported["application_id"])
            existing_alias = next(
                (
                    row
                    for row in self.connection.execute(
                        "SELECT id, owner, company, title, canonical_url FROM applications"
                    )
                    if self._posting_alias(str(row["company"]), str(row["title"]))
                    == posting_alias
                    and (
                        normalized_url.startswith("evidence://")
                        or str(row["canonical_url"]).startswith("evidence://")
                    )
                ),
                None,
            )
            if existing_alias is not None:
                existing_owner = str(existing_alias["owner"])
                if existing_owner != owner:
                    raise FenceError(
                        f"canonical posting is already owned by {existing_owner}"
                    )
                return str(existing_alias["id"])
            existing_url = self.connection.execute(
                "SELECT id, owner FROM applications WHERE canonical_url = ?",
                (normalized_url,),
            ).fetchone()
            if existing_url is not None:
                existing_owner = str(existing_url["owner"])
                if existing_owner != owner:
                    raise FenceError(
                        f"canonical posting is already owned by {existing_owner}"
                    )
                application_id = str(existing_url["id"])
            existing = self.connection.execute(
                "SELECT id FROM applications WHERE id = ?", (application_id,)
            ).fetchone()
            if existing is None:
                created_at = _now()
                self.connection.execute(
                    """
                    INSERT INTO applications
                      (id, company, title, canonical_url, owner, current_state, created_at)
                    VALUES (?, ?, ?, ?, ?, 'discovered', ?)
                    """,
                    (
                        application_id,
                        company.strip(),
                        title.strip(),
                        normalized_url,
                        owner,
                        created_at,
                    ),
                )
                self._append_event(application_id, None, "discovered")
            self.connection.execute(
                """
                INSERT OR IGNORE INTO application_strategy_assignments
                  (application_id, strategy_generation_id, capture_status, source,
                   query_family, rank_config_json, role_family, material_variant,
                   message_variant, model_route, prompt_sha256, material_sha256,
                   assigned_at)
                SELECT
                  applications.id, ?, 'legacy_unavailable', 'legacy_unavailable',
                  'legacy_unavailable', NULL, 'legacy_unavailable',
                  'legacy_unavailable', 'legacy_unavailable', 'legacy_unavailable',
                  NULL, NULL, applications.created_at
                FROM applications
                WHERE applications.id = ?
                """,
                (LEGACY_STRATEGY_GENERATION_ID, application_id),
            )
        return application_id

    def record_application_artifact(
        self,
        *,
        application_id: str,
        kind: str,
        path: Path,
        sha256: str,
        fact_ids: list[str],
        source_urls: list[str],
    ) -> str:
        if kind not in APPLICATION_ARTIFACT_KINDS:
            raise ValueError("unsupported application artifact kind")
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_file():
            raise ValueError("application artifact file does not exist")
        if resolved.stat().st_mode & 0o077:
            raise ValueError("application artifact must be private")
        actual_sha256 = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if not re.fullmatch(r"[a-f0-9]{64}", sha256) or sha256 != actual_sha256:
            raise ValueError("application artifact SHA-256 mismatch")
        if not isinstance(fact_ids, list) or not all(
            isinstance(value, str) and value.strip() for value in fact_ids
        ):
            raise ValueError("fact_ids must be a list of non-empty strings")
        if not isinstance(source_urls, list) or not all(
            isinstance(value, str) and value.startswith("https://")
            for value in source_urls
        ):
            raise ValueError("source_urls must contain only HTTPS URLs")
        if kind in {"posting", "company_research"} and not source_urls:
            raise ValueError(f"{kind} requires at least one source URL")
        if kind.endswith("_draft") and not fact_ids:
            raise ValueError(f"{kind} requires approved fact IDs")

        fact_ids_json = json.dumps(
            fact_ids, ensure_ascii=False, separators=(",", ":")
        )
        source_urls_json = json.dumps(
            source_urls, ensure_ascii=False, separators=(",", ":")
        )
        identity = "\n".join((application_id, kind, sha256))
        artifact_id = f"artifact-{hashlib.sha256(identity.encode()).hexdigest()}"
        with self._transaction():
            application = self.connection.execute(
                "SELECT id FROM applications WHERE id = ?", (application_id,)
            ).fetchone()
            if application is None:
                raise KeyError(application_id)
            existing = self.connection.execute(
                "SELECT artifact_id, path, fact_ids_json, source_urls_json "
                "FROM application_artifacts WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()
            expected = (artifact_id, str(resolved), fact_ids_json, source_urls_json)
            if existing is not None:
                if tuple(existing) == expected:
                    return artifact_id
                raise FenceError("artifact identity is already bound to other metadata")
            self.connection.execute(
                """
                INSERT INTO application_artifacts
                  (artifact_id, application_id, kind, path, sha256,
                   fact_ids_json, source_urls_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact_id,
                    application_id,
                    kind,
                    str(resolved),
                    sha256,
                    fact_ids_json,
                    source_urls_json,
                    _now(),
                ),
            )
        return artifact_id

    def application_artifact_chain(self, application_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT artifact_id, kind, path, sha256, fact_ids_json,
                   source_urls_json, created_at
            FROM application_artifacts
            WHERE application_id = ?
            ORDER BY rowid
            """,
            (application_id,),
        ).fetchall()
        return [
            {
                "artifact_id": str(row["artifact_id"]),
                "kind": str(row["kind"]),
                "path": str(row["path"]),
                "sha256": str(row["sha256"]),
                "fact_ids": json.loads(str(row["fact_ids_json"])),
                "source_urls": json.loads(str(row["source_urls_json"])),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def record_ranked_gaps(
        self,
        *,
        application_id: str,
        score: int,
        gaps: list[str],
        evidence_sha256: str,
    ) -> None:
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
            raise ValueError("score must be an integer from 0 to 100")
        if not isinstance(gaps, list) or not all(
            isinstance(gap, str) and gap.strip() for gap in gaps
        ):
            raise ValueError("gaps must be a list of non-empty strings")
        normalized_gaps = list(dict.fromkeys(gap.strip() for gap in gaps))
        if not re.fullmatch(r"[a-f0-9]{64}", evidence_sha256):
            raise ValueError("evidence_sha256 must be a lowercase SHA-256")
        gaps_json = json.dumps(
            normalized_gaps, ensure_ascii=False, separators=(",", ":")
        )
        with self._transaction():
            if self.connection.execute(
                "SELECT id FROM applications WHERE id=?", (application_id,)
            ).fetchone() is None:
                raise KeyError(application_id)
            existing = self.connection.execute(
                "SELECT score,gaps_json,evidence_sha256 FROM application_ranked_gaps "
                "WHERE application_id=?",
                (application_id,),
            ).fetchone()
            expected = (score, gaps_json, evidence_sha256)
            if existing is not None:
                if tuple(existing) == expected:
                    return
                raise FenceError("ranked gaps are already fixed for this application")
            self.connection.execute(
                "INSERT INTO application_ranked_gaps "
                "(application_id,score,gaps_json,evidence_sha256,created_at) "
                "VALUES(?,?,?,?,?)",
                (application_id, score, gaps_json, evidence_sha256, _now()),
            )

    def upskill_projection(self, *, profile_skills: list[str]) -> dict[str, Any]:
        if not isinstance(profile_skills, list) or not all(
            isinstance(skill, str) and skill.strip() for skill in profile_skills
        ):
            raise ValueError("profile_skills must be a list of non-empty strings")
        known = [skill.casefold().strip() for skill in profile_skills]
        rows = self.connection.execute(
            "SELECT application_id,score,gaps_json,evidence_sha256 "
            "FROM application_ranked_gaps ORDER BY application_id"
        ).fetchall()
        totals: dict[str, dict[str, Any]] = {}
        for row in rows:
            weight = (100 - int(row["score"])) / 100
            for gap in json.loads(str(row["gaps_json"])):
                folded = str(gap).casefold()
                if any(skill in folded or folded in skill for skill in known):
                    continue
                key = folded.strip()
                item = totals.setdefault(
                    key,
                    {"gap": str(gap), "job_count": 0, "weighted_score": 0.0},
                )
                item["job_count"] += 1
                item["weighted_score"] += weight
        gaps = sorted(
            (
                {
                    **item,
                    "weighted_score": round(float(item["weighted_score"]), 6),
                }
                for item in totals.values()
            ),
            key=lambda item: (-item["weighted_score"], -item["job_count"], item["gap"].casefold()),
        )
        total_applications = int(
            self.connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        )
        value: dict[str, Any] = {
            "version": 1,
            "analysed_jobs": len(rows),
            "jobs_without_recorded_gaps": total_applications - len(rows),
            "gaps": gaps,
        }
        value["projection_sha256"] = hashlib.sha256(
            json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return value

    def due_followups(self, as_of: str) -> list[dict[str, Any]]:
        try:
            current = datetime.fromisoformat(as_of)
        except ValueError as error:
            raise ValueError("as_of must be RFC3339") from error
        if current.tzinfo is None:
            raise ValueError("as_of must include a timezone")
        rows = self.connection.execute(
            """
            SELECT applications.id, applications.company, applications.title,
                   MIN(events.created_at) AS submitted_at
            FROM applications
            JOIN events ON events.application_id = applications.id
            WHERE events.to_state = 'submitted'
              AND NOT EXISTS (
                SELECT 1 FROM funnel_outcomes
                WHERE funnel_outcomes.application_id = applications.id
              )
            GROUP BY applications.id
            ORDER BY applications.created_at, applications.id
            """
        ).fetchall()
        due: list[dict[str, Any]] = []
        for row in rows:
            followups = self.connection.execute(
                """
                SELECT ordinal, sent_at FROM application_followups
                WHERE application_id = ? ORDER BY ordinal
                """,
                (row["id"],),
            ).fetchall()
            if len(followups) >= 2:
                continue
            anchor = datetime.fromisoformat(
                str(followups[-1]["sent_at"] if followups else row["submitted_at"])
            )
            due_at = anchor + timedelta(days=10)
            if current >= due_at:
                due.append(
                    {
                        "application_id": str(row["id"]),
                        "company": str(row["company"]),
                        "title": str(row["title"]),
                        "ordinal": len(followups) + 1,
                        "due_at": due_at.isoformat(),
                    }
                )
        return due

    def record_followup(
        self,
        *,
        application_id: str,
        ordinal: int,
        sent_at: str,
        evidence_sha256: str,
    ) -> str:
        if ordinal not in {1, 2}:
            raise ValueError("followup ordinal must be 1 or 2")
        if not re.fullmatch(r"[a-f0-9]{64}", evidence_sha256):
            raise ValueError("followup evidence_sha256 must be a lowercase SHA-256")
        identity = "\n".join(
            (application_id, str(ordinal), sent_at, evidence_sha256)
        )
        followup_id = f"followup-{hashlib.sha256(identity.encode()).hexdigest()}"
        existing = self.connection.execute(
            """
            SELECT followup_id, sent_at, evidence_sha256
            FROM application_followups
            WHERE application_id = ? AND ordinal = ?
            """,
            (application_id, ordinal),
        ).fetchone()
        if existing is not None:
            if (
                str(existing["followup_id"]) == followup_id
                and str(existing["sent_at"]) == sent_at
                and str(existing["evidence_sha256"]) == evidence_sha256
            ):
                return followup_id
            raise FenceError("followup ordinal is already bound to other evidence")
        eligible = {
            (item["application_id"], item["ordinal"])
            for item in self.due_followups(sent_at)
        }
        if (application_id, ordinal) not in eligible:
            raise FenceError("followup is not due or application already has an outcome")
        with self._transaction():
            self.connection.execute(
                """
                INSERT INTO application_followups
                  (followup_id, application_id, ordinal, sent_at,
                   evidence_sha256, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    followup_id,
                    application_id,
                    ordinal,
                    sent_at,
                    evidence_sha256,
                    _now(),
                ),
            )
        return followup_id

    def application_archive(self, application_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            """
            SELECT id, company, title, canonical_url, current_state, created_at
            FROM applications WHERE id = ?
            """,
            (application_id,),
        ).fetchone()
        if row is None:
            raise KeyError(application_id)
        followups = self.connection.execute(
            """
            SELECT followup_id, ordinal, sent_at, evidence_sha256
            FROM application_followups
            WHERE application_id = ? ORDER BY ordinal
            """,
            (application_id,),
        ).fetchall()
        return {
            "application": {key: row[key] for key in row.keys()},
            "artifacts": self.application_artifact_chain(application_id),
            "outcomes": self.funnel_outcomes(application_id),
            "followups": [
                {key: item[key] for key in item.keys()} for item in followups
            ],
        }

    def add_attributed_application(
        self,
        company: str,
        title: str,
        url: str,
        *,
        strategy_generation_id: str,
        source: str,
        query_family: str,
        rank_config: Mapping[str, Any],
        role_family: str,
        material_variant: str,
        message_variant: str,
        model_route: str,
        prompt_sha256: str,
        material_sha256: str,
    ) -> str:
        text_values = {
            "strategy_generation_id": strategy_generation_id,
            "source": source,
            "query_family": query_family,
            "role_family": role_family,
            "material_variant": material_variant,
            "message_variant": message_variant,
            "model_route": model_route,
        }
        for name, value in text_values.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(rank_config, Mapping):
            raise ValueError("rank_config must be a mapping")
        for name, value in {
            "prompt_sha256": prompt_sha256,
            "material_sha256": material_sha256,
        }.items():
            if not re.fullmatch(r"[a-f0-9]{64}", value):
                raise ValueError(f"{name} must be a lowercase SHA-256")

        normalized_url = canonical_url(url)
        application_id = canonical_job_id(company, title, normalized_url)
        posting_alias = self._posting_alias(company, title)
        rank_config_json = json.dumps(
            dict(rank_config),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with self._transaction():
            imported = self.connection.execute(
                "SELECT owner FROM external_application_imports "
                "WHERE posting_alias = ?",
                (posting_alias,),
            ).fetchone()
            if imported is not None:
                raise FenceError(
                    f"canonical posting is already owned by {str(imported['owner'])}"
                )
            generation = self.connection.execute(
                """
                SELECT strategy_generation_id
                FROM strategy_generations
                WHERE strategy_generation_id = ?
                """,
                (strategy_generation_id,),
            ).fetchone()
            if generation is None:
                raise ValueError("strategy generation does not exist")
            existing_url = self.connection.execute(
                "SELECT id, owner FROM applications WHERE canonical_url = ?",
                (normalized_url,),
            ).fetchone()
            if existing_url is not None:
                existing_owner = str(existing_url["owner"])
                if existing_owner != "agent":
                    raise FenceError(
                        f"canonical posting is already owned by {existing_owner}"
                    )
                application_id = str(existing_url["id"])
            application = self.connection.execute(
                "SELECT id FROM applications WHERE id = ?", (application_id,)
            ).fetchone()
            if application is None:
                created_at = _now()
                self.connection.execute(
                    """
                    INSERT INTO applications
                      (id, company, title, canonical_url, owner, current_state, created_at)
                    VALUES (?, ?, ?, ?, 'agent', 'discovered', ?)
                    """,
                    (
                        application_id,
                        company.strip(),
                        title.strip(),
                        normalized_url,
                        created_at,
                    ),
                )
                self._append_event(application_id, None, "discovered")
            existing_assignment = self.connection.execute(
                """
                SELECT
                  strategy_generation_id, capture_status, source, query_family,
                  rank_config_json, role_family, material_variant,
                  message_variant, model_route, prompt_sha256, material_sha256
                FROM application_strategy_assignments
                WHERE application_id = ?
                """,
                (application_id,),
            ).fetchone()
            expected_assignment = (
                strategy_generation_id,
                "captured",
                source.strip(),
                query_family.strip(),
                rank_config_json,
                role_family.strip(),
                material_variant.strip(),
                message_variant.strip(),
                model_route.strip(),
                prompt_sha256,
                material_sha256,
            )
            if existing_assignment is not None:
                if tuple(existing_assignment) == expected_assignment:
                    return application_id
                raise FenceError(
                    "application already has a different immutable strategy assignment"
                )
            self.connection.execute(
                """
                INSERT INTO application_strategy_assignments
                  (application_id, strategy_generation_id, capture_status, source,
                   query_family, rank_config_json, role_family, material_variant,
                   message_variant, model_route, prompt_sha256, material_sha256,
                   assigned_at)
                VALUES (?, ?, 'captured', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    application_id,
                    strategy_generation_id,
                    source.strip(),
                    query_family.strip(),
                    rank_config_json,
                    role_family.strip(),
                    material_variant.strip(),
                    message_variant.strip(),
                    model_route.strip(),
                    prompt_sha256,
                    material_sha256,
                    _now(),
                ),
            )
        return application_id

    @staticmethod
    def _posting_alias(company: str, title: str) -> str:
        normalized = "\n".join(
            re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
            for value in (company, title)
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def import_external_application(
        self,
        *,
        company: str,
        title: str,
        owner: str,
        source: str,
        source_message_id: str,
        applied_at: str,
        evidence_sha256: str,
    ) -> dict[str, str]:
        if owner not in {"dais_manual", "recruiter"}:
            raise ValueError("external owner must be dais_manual or recruiter")
        values = {
            "company": company,
            "title": title,
            "source": source,
            "source_message_id": source_message_id,
        }
        for name, value in values.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        try:
            applied = datetime.fromisoformat(applied_at)
        except ValueError as error:
            raise ValueError("applied_at must be RFC3339") from error
        if applied.tzinfo is None:
            raise ValueError("applied_at must include timezone")
        if not re.fullmatch(r"[a-f0-9]{64}", evidence_sha256):
            raise ValueError("evidence_sha256 must be a lowercase SHA-256")
        source_message_id = source_message_id.strip()
        evidence_url = f"evidence://{source.strip().casefold()}/{source_message_id}"
        application_id = canonical_job_id(company, title, evidence_url)
        posting_alias = self._posting_alias(company, title)
        with self._transaction():
            existing = self.connection.execute(
                "SELECT * FROM external_application_imports "
                "WHERE source_message_id = ?",
                (source_message_id,),
            ).fetchone()
            if existing is not None:
                expected = (
                    owner,
                    source.strip(),
                    applied_at,
                    evidence_sha256,
                    posting_alias,
                )
                recorded = (
                    str(existing["owner"]),
                    str(existing["source"]),
                    str(existing["applied_at"]),
                    str(existing["evidence_sha256"]),
                    str(existing["posting_alias"]),
                )
                if recorded != expected:
                    raise FenceError("source message is already bound to another import")
                return {
                    "status": "already_imported",
                    "application_id": str(existing["application_id"]),
                }
            alias_existing = self.connection.execute(
                "SELECT owner FROM external_application_imports WHERE posting_alias = ?",
                (posting_alias,),
            ).fetchone()
            if alias_existing is not None:
                raise FenceError(
                    "posting alias is already owned by "
                    f"{str(alias_existing['owner'])}"
                )
            created_at = _now()
            self.connection.execute(
                "INSERT INTO applications "
                "(id, company, title, canonical_url, owner, current_state, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'submitted', ?)",
                (
                    application_id,
                    company.strip(),
                    title.strip(),
                    evidence_url,
                    owner,
                    created_at,
                ),
            )
            self._append_event(
                application_id,
                None,
                "submitted",
                {
                    "external_import": True,
                    "source": source.strip(),
                    "source_message_id": source_message_id,
                    "applied_at": applied_at,
                    "evidence_sha256": evidence_sha256,
                },
            )
            self.connection.execute(
                "INSERT INTO external_application_imports "
                "(application_id, owner, source, source_message_id, applied_at, "
                "evidence_sha256, posting_alias, imported_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    application_id,
                    owner,
                    source.strip(),
                    source_message_id,
                    applied_at,
                    evidence_sha256,
                    posting_alias,
                    created_at,
                ),
            )
            self.connection.execute(
                "INSERT INTO application_strategy_assignments "
                "(application_id, strategy_generation_id, capture_status, source, "
                "query_family, rank_config_json, role_family, material_variant, "
                "message_variant, model_route, prompt_sha256, material_sha256, "
                "assigned_at) VALUES (?, ?, 'legacy_unavailable', ?, "
                "'external_import', NULL, 'legacy_unavailable', 'legacy_unavailable', "
                "'none', 'external_import', NULL, NULL, ?)",
                (application_id, LEGACY_STRATEGY_GENERATION_ID, source.strip(), created_at),
            )
        return {"status": "imported", "application_id": application_id}

    def external_application_imports(self) -> list[dict[str, str]]:
        rows = self.connection.execute(
            "SELECT * FROM external_application_imports ORDER BY imported_at, application_id"
        ).fetchall()
        return [{key: str(row[key]) for key in row.keys()} for row in rows]

    def add_founder_outreach_target(
        self,
        *,
        company: str,
        relationship_url: str,
        evidence_source: str,
        evidence_id: str,
        evidence_sha256: str,
    ) -> str:
        text_values = {
            "company": company,
            "relationship_url": relationship_url,
            "evidence_source": evidence_source,
            "evidence_id": evidence_id,
        }
        for name, value in text_values.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if not re.fullmatch(r"[a-f0-9]{64}", evidence_sha256):
            raise ValueError("evidence_sha256 must be a lowercase SHA-256")
        normalized_url = canonical_url(relationship_url)
        target_id = hashlib.sha256(
            f"{company.strip().casefold()}\n{normalized_url}".encode("utf-8")
        ).hexdigest()
        event_payload = "\n".join(
            (target_id, "researched", evidence_source.strip(), evidence_id.strip(), evidence_sha256)
        )
        event_id = f"founder-event-{hashlib.sha256(event_payload.encode('utf-8')).hexdigest()}"
        with self._transaction():
            existing = self.connection.execute(
                "SELECT target_id, company FROM founder_outreach_targets "
                "WHERE relationship_url = ?",
                (normalized_url,),
            ).fetchone()
            if existing is not None:
                if str(existing["target_id"]) != target_id:
                    raise FenceError("relationship URL is already bound to another target")
                recorded = self.connection.execute(
                    "SELECT event_id FROM founder_outreach_events WHERE event_id = ?",
                    (event_id,),
                ).fetchone()
                if recorded is None:
                    raise FenceError("founder target research evidence conflicts")
                return target_id
            created_at = _now()
            self.connection.execute(
                "INSERT INTO founder_outreach_targets "
                "(target_id, company, relationship_url, current_state, created_at) "
                "VALUES (?, ?, ?, 'researched', ?)",
                (target_id, company.strip(), normalized_url, created_at),
            )
            self.connection.execute(
                "INSERT INTO founder_outreach_events "
                "(event_id, target_id, from_state, to_state, evidence_source, "
                "evidence_id, evidence_sha256, created_at) "
                "VALUES (?, ?, NULL, 'researched', ?, ?, ?, ?)",
                (
                    event_id,
                    target_id,
                    evidence_source.strip(),
                    evidence_id.strip(),
                    evidence_sha256,
                    created_at,
                ),
            )
        return target_id

    def transition_founder_outreach(
        self,
        *,
        target_id: str,
        to_state: str,
        evidence_source: str,
        evidence_id: str,
        evidence_sha256: str,
    ) -> str:
        if not re.fullmatch(r"[a-f0-9]{64}", evidence_sha256):
            raise ValueError("evidence_sha256 must be a lowercase SHA-256")
        for name, value in {
            "to_state": to_state,
            "evidence_source": evidence_source,
            "evidence_id": evidence_id,
        }.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        event_payload = "\n".join(
            (target_id, to_state, evidence_source.strip(), evidence_id.strip(), evidence_sha256)
        )
        event_id = f"founder-event-{hashlib.sha256(event_payload.encode('utf-8')).hexdigest()}"
        with self._transaction():
            replay = self.connection.execute(
                "SELECT event_id FROM founder_outreach_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
            if replay is not None:
                return event_id
            target = self.connection.execute(
                "SELECT current_state FROM founder_outreach_targets WHERE target_id = ?",
                (target_id,),
            ).fetchone()
            if target is None:
                raise KeyError(target_id)
            from_state = str(target["current_state"])
            if to_state not in FOUNDER_OUTREACH_TRANSITIONS.get(from_state, frozenset()):
                raise ValueError(
                    f"invalid founder outreach transition: {from_state} -> {to_state}"
                )
            created_at = _now()
            self.connection.execute(
                "UPDATE founder_outreach_targets SET current_state = ? WHERE target_id = ?",
                (to_state, target_id),
            )
            self.connection.execute(
                "INSERT INTO founder_outreach_events "
                "(event_id, target_id, from_state, to_state, evidence_source, "
                "evidence_id, evidence_sha256, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    target_id,
                    from_state,
                    to_state,
                    evidence_source.strip(),
                    evidence_id.strip(),
                    evidence_sha256,
                    created_at,
                ),
            )
        return event_id

    def founder_outreach_status(self, target_id: str) -> dict[str, str]:
        row = self.connection.execute(
            "SELECT * FROM founder_outreach_targets WHERE target_id = ?", (target_id,)
        ).fetchone()
        if row is None:
            raise KeyError(target_id)
        return {key: str(row[key]) for key in row.keys()}

    def founder_outreach_events(self, target_id: str) -> list[dict[str, str | None]]:
        rows = self.connection.execute(
            "SELECT * FROM founder_outreach_events WHERE target_id = ? "
            "ORDER BY created_at, rowid",
            (target_id,),
        ).fetchall()
        return [
            {key: (str(row[key]) if row[key] is not None else None) for key in row.keys()}
            for row in rows
        ]

    def strategy_assignment(self, application_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            """
            SELECT
              application_id, strategy_generation_id, capture_status, source,
              query_family, rank_config_json, role_family, material_variant,
              message_variant, model_route, prompt_sha256, material_sha256
            FROM application_strategy_assignments
            WHERE application_id = ?
            """,
            (application_id,),
        ).fetchone()
        if row is None:
            raise KeyError(application_id)
        return {
            "application_id": str(row["application_id"]),
            "strategy_generation_id": str(row["strategy_generation_id"]),
            "capture_status": str(row["capture_status"]),
            "source": str(row["source"]),
            "query_family": str(row["query_family"]),
            "rank_config": (
                json.loads(str(row["rank_config_json"]))
                if row["rank_config_json"] is not None
                else None
            ),
            "role_family": str(row["role_family"]),
            "material_variant": str(row["material_variant"]),
            "message_variant": str(row["message_variant"]),
            "model_route": str(row["model_route"]),
            "prompt_sha256": (
                str(row["prompt_sha256"])
                if row["prompt_sha256"] is not None
                else None
            ),
            "material_sha256": (
                str(row["material_sha256"])
                if row["material_sha256"] is not None
                else None
            ),
        }

    def record_funnel_outcome(
        self,
        *,
        application_id: str,
        funnel_stage: str,
        disposition: str,
        evidence_source: str,
        evidence_sha256: str,
        occurred_at: str,
        observed_at: str,
        observation_policy_version: str | None = None,
    ) -> str:
        if funnel_stage not in FUNNEL_STAGES:
            raise ValueError("invalid funnel stage")
        if disposition not in FUNNEL_DISPOSITIONS:
            raise ValueError("invalid funnel disposition")
        if evidence_source not in AUTHORITATIVE_EVIDENCE_SOURCES:
            raise ValueError("outcome evidence source is not authoritative")
        if not re.fullmatch(r"[a-f0-9]{64}", evidence_sha256):
            raise ValueError("evidence_sha256 must be a lowercase SHA-256")
        if disposition == "negative" and (
            not isinstance(observation_policy_version, str)
            or not observation_policy_version.strip()
        ):
            raise ValueError(
                "negative outcomes require a versioned observation policy"
            )
        parsed_times: dict[str, datetime] = {}
        for name, value in {
            "occurred_at": occurred_at,
            "observed_at": observed_at,
        }.items():
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError as error:
                raise ValueError(f"{name} must be RFC3339") from error
            if parsed.tzinfo is None:
                raise ValueError(f"{name} must include a timezone")
            parsed_times[name] = parsed
        if parsed_times["observed_at"] < parsed_times["occurred_at"]:
            raise ValueError("observed_at cannot predate occurred_at")

        identity = {
            "application_id": application_id,
            "funnel_stage": funnel_stage,
            "disposition": disposition,
            "evidence_source": evidence_source,
            "evidence_sha256": evidence_sha256,
            "occurred_at": occurred_at,
            "observed_at": observed_at,
            "observation_policy_version": observation_policy_version,
        }
        encoded = json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        outcome_id = f"outcome-{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"
        with self._transaction():
            recorded = self._record_funnel_outcome_in_transaction(
                outcome_id=outcome_id,
                **identity,
            )
            self._rebuild_strategy_outcome_projection_in_transaction()
            return recorded

    def _record_funnel_outcome_in_transaction(
        self,
        *,
        outcome_id: str,
        application_id: str,
        funnel_stage: str,
        disposition: str,
        evidence_source: str,
        evidence_sha256: str,
        occurred_at: str,
        observed_at: str,
        observation_policy_version: str | None,
    ) -> str:
        application = self.connection.execute(
            "SELECT id FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()
        if application is None:
            raise KeyError(application_id)
        bound_applications = {
            str(row["application_id"])
            for row in self.connection.execute(
                """
                SELECT DISTINCT application_id
                FROM funnel_outcomes
                WHERE evidence_sha256 = ?
                """,
                (evidence_sha256,),
            ).fetchall()
        }
        if bound_applications and bound_applications != {application_id}:
            raise FenceError(
                "external evidence is already bound to a different application"
            )
        existing = self.connection.execute(
            """
            SELECT
              outcome_id, application_id, funnel_stage, disposition,
              evidence_source, evidence_sha256, occurred_at, observed_at,
              observation_policy_version
            FROM funnel_outcomes
            WHERE application_id = ?
              AND funnel_stage = ?
              AND evidence_sha256 = ?
            """,
            (application_id, funnel_stage, evidence_sha256),
        ).fetchone()
        expected = (
            outcome_id,
            application_id,
            funnel_stage,
            disposition,
            evidence_source,
            evidence_sha256,
            occurred_at,
            observed_at,
            observation_policy_version,
        )
        if existing is not None:
            if tuple(existing) == expected:
                return outcome_id
            raise FenceError(
                "external evidence is already bound to a different outcome"
            )
        self.connection.execute(
            """
            INSERT INTO funnel_outcomes
              (outcome_id, application_id, funnel_stage, disposition,
               evidence_source, evidence_sha256, occurred_at, observed_at,
               observation_policy_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*expected, _now()),
        )
        return outcome_id

    def funnel_outcomes(self, application_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
              outcome_id, application_id, funnel_stage, disposition,
              evidence_source, evidence_sha256, occurred_at, observed_at,
              observation_policy_version
            FROM funnel_outcomes
            WHERE application_id = ?
            ORDER BY occurred_at, outcome_id
            """,
            (application_id,),
        ).fetchall()
        return [
            {
                "outcome_id": str(row["outcome_id"]),
                "application_id": str(row["application_id"]),
                "funnel_stage": str(row["funnel_stage"]),
                "disposition": str(row["disposition"]),
                "evidence_source": str(row["evidence_source"]),
                "evidence_sha256": str(row["evidence_sha256"]),
                "occurred_at": str(row["occurred_at"]),
                "observed_at": str(row["observed_at"]),
                "observation_policy_version": (
                    str(row["observation_policy_version"])
                    if row["observation_policy_version"] is not None
                    else None
                ),
            }
            for row in rows
        ]

    def rebuild_strategy_outcome_projection(self) -> list[dict[str, Any]]:
        with self._transaction():
            self._rebuild_strategy_outcome_projection_in_transaction()
        return self.strategy_outcome_projection()

    def _rebuild_strategy_outcome_projection_in_transaction(self) -> None:
        self.connection.execute("DELETE FROM strategy_outcome_projection")
        self.connection.execute(
            """
            INSERT INTO strategy_outcome_projection
              (strategy_generation_id, funnel_stage, positive_count,
               negative_count, resolved_count)
            SELECT
              assignments.strategy_generation_id,
              outcomes.funnel_stage,
              SUM(CASE WHEN outcomes.disposition = 'positive' THEN 1 ELSE 0 END),
              SUM(CASE WHEN outcomes.disposition = 'negative' THEN 1 ELSE 0 END),
              COUNT(*)
            FROM funnel_outcomes AS outcomes
            JOIN application_strategy_assignments AS assignments
              ON assignments.application_id = outcomes.application_id
            WHERE NOT (
              outcomes.funnel_stage = 'confirmed_application'
              AND EXISTS (
                SELECT 1
                FROM application_routes AS routes
                WHERE routes.application_id = outcomes.application_id
                  AND routes.delivery_state = 'delivered'
                  AND routes.recipient_acceptance = 'outreach_only'
                  AND routes.delivery_evidence_sha256 = outcomes.evidence_sha256
              )
            )
            GROUP BY assignments.strategy_generation_id, outcomes.funnel_stage
            """
        )

    def strategy_outcome_projection(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
              strategy_generation_id, funnel_stage, positive_count,
              negative_count, resolved_count
            FROM strategy_outcome_projection
            ORDER BY strategy_generation_id, funnel_stage
            """
        ).fetchall()
        return [
            {
                "strategy_generation_id": str(row["strategy_generation_id"]),
                "funnel_stage": str(row["funnel_stage"]),
                "positive_count": int(row["positive_count"]),
                "negative_count": int(row["negative_count"]),
                "resolved_count": int(row["resolved_count"]),
            }
            for row in rows
        ]

    def current_state(self, application_id: str) -> str:
        row = self.connection.execute(
            "SELECT current_state FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()
        if row is None:
            raise KeyError(application_id)
        return str(row["current_state"])

    def application_owner(self, application_id: str) -> str:
        row = self.connection.execute(
            "SELECT owner FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()
        if row is None:
            raise KeyError(application_id)
        return str(row["owner"])

    def daily_slot_count(self, japan_day: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM daily_slots WHERE japan_day = ?",
            (japan_day,),
        ).fetchone()
        return int(row["count"])

    def daily_portfolio(self, japan_day: str) -> dict[str, int]:
        counts = {bucket: 0 for bucket in PORTFOLIO_LIMITS}
        rows = self.connection.execute(
            "SELECT portfolio_bucket, COUNT(*) AS count FROM daily_slots "
            "WHERE japan_day = ? GROUP BY portfolio_bucket",
            (japan_day,),
        ).fetchall()
        for row in rows:
            bucket = str(row["portfolio_bucket"])
            if bucket in counts:
                counts[bucket] = int(row["count"])
        return counts

    def confirmed_daily_portfolio(self, japan_day: str) -> dict[str, int]:
        counts = {bucket: 0 for bucket in PORTFOLIO_LIMITS}
        rows = self.connection.execute(
            "SELECT portfolio_bucket, COUNT(*) AS count FROM daily_slots "
            "WHERE japan_day = ? AND status = 'submitted' "
            "GROUP BY portfolio_bucket",
            (japan_day,),
        ).fetchall()
        for row in rows:
            bucket = str(row["portfolio_bucket"])
            if bucket in counts:
                counts[bucket] = int(row["count"])
        return counts

    def confirmed_daily_count(self, japan_day: str) -> int:
        row = self.connection.execute(
            "SELECT COUNT(*) AS count FROM daily_slots "
            "WHERE japan_day = ? AND status = 'submitted'",
            (japan_day,),
        ).fetchone()
        return int(row["count"])

    def record_quota_deficit(
        self,
        *,
        japan_day: str,
        confirmed_count: int,
        portfolio_confirmed: Mapping[str, int],
        portfolio_deficit: Mapping[str, int],
        reason: str,
    ) -> dict[str, Any]:
        payload = {
            "japan_day": japan_day,
            "confirmed_count": confirmed_count,
            "deficit_count": 10 - confirmed_count,
            "portfolio_confirmed": dict(portfolio_confirmed),
            "portfolio_deficit": dict(portfolio_deficit),
            "reason": reason,
        }
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload_sha256 = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        event_id = f"quota-deficit-{payload_sha256}"
        with self._transaction():
            self.connection.execute(
                "INSERT OR IGNORE INTO daily_quota_events "
                "(event_id, japan_day, confirmed_count, deficit_count, "
                "portfolio_confirmed_json, portfolio_deficit_json, reason, "
                "payload_sha256, observed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_id,
                    japan_day,
                    confirmed_count,
                    10 - confirmed_count,
                    json.dumps(dict(portfolio_confirmed), sort_keys=True),
                    json.dumps(dict(portfolio_deficit), sort_keys=True),
                    reason,
                    payload_sha256,
                    _now(),
                ),
            )
        return {"event_id": event_id, **payload, "payload_sha256": payload_sha256}

    def quota_deficit_events(self, japan_day: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM daily_quota_events"
        parameters: tuple[str, ...] = ()
        if japan_day is not None:
            query += " WHERE japan_day = ?"
            parameters = (japan_day,)
        query += " ORDER BY observed_at, event_id"
        rows = self.connection.execute(query, parameters).fetchall()
        return [
            {
                "event_id": str(row["event_id"]),
                "japan_day": str(row["japan_day"]),
                "confirmed_count": int(row["confirmed_count"]),
                "deficit_count": int(row["deficit_count"]),
                "portfolio_confirmed": json.loads(row["portfolio_confirmed_json"]),
                "portfolio_deficit": json.loads(row["portfolio_deficit_json"]),
                "reason": str(row["reason"]),
                "payload_sha256": str(row["payload_sha256"]),
                "observed_at": str(row["observed_at"]),
            }
            for row in rows
        ]

    def _transition_in_transaction(
        self,
        application_id: str,
        to_state: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        from_state = self.current_state(application_id)
        validate_transition(from_state, to_state)
        self._append_event(application_id, from_state, to_state, payload)
        self.connection.execute(
            "UPDATE applications SET current_state = ? WHERE id = ?",
            (to_state, application_id),
        )

    def transition(
        self,
        application_id: str,
        to_state: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self._transaction():
            self._transition_in_transaction(application_id, to_state, payload)

    def events(self, application_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT event_id, from_state, to_state, payload_json, created_at
            FROM events WHERE application_id = ? ORDER BY rowid
            """,
            (application_id,),
        ).fetchall()
        return [
            {
                "event_id": row["event_id"],
                "from_state": row["from_state"],
                "to_state": row["to_state"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def record_strategy_generation(
        self,
        strategy: Mapping[str, Any],
        *,
        parent_generation_id: str | None = None,
        changed_field: str | None = None,
    ) -> str:
        if not isinstance(strategy, Mapping) or not strategy:
            raise ValueError("strategy generation must be a non-empty mapping")
        if (parent_generation_id is None) != (changed_field is None):
            raise ValueError(
                "parent_generation_id and changed_field must be provided together"
            )
        strategy_json = json.dumps(
            dict(strategy),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        strategy_sha256 = hashlib.sha256(strategy_json.encode("utf-8")).hexdigest()
        generation_id = f"strategy-{strategy_sha256}"
        with self._transaction():
            if parent_generation_id is not None:
                parent = self.connection.execute(
                    """
                    SELECT strategy_json
                    FROM strategy_generations
                    WHERE strategy_generation_id = ?
                    """,
                    (parent_generation_id,),
                ).fetchone()
                if parent is None:
                    raise ValueError("parent strategy generation does not exist")
                parent_strategy = json.loads(str(parent["strategy_json"]))
                changed = {
                    key
                    for key in set(parent_strategy) | set(strategy)
                    if parent_strategy.get(key) != strategy.get(key)
                }
                if changed != {changed_field}:
                    raise ValueError(
                        "candidate must change exactly the declared strategy field"
                    )
            self.connection.execute(
                """
                INSERT OR IGNORE INTO strategy_generations
                  (strategy_generation_id, parent_generation_id, changed_field,
                   strategy_json, strategy_sha256, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    generation_id,
                    parent_generation_id,
                    changed_field,
                    strategy_json,
                    strategy_sha256,
                    _now(),
                ),
            )
            recorded = self.connection.execute(
                """
                SELECT parent_generation_id, changed_field
                FROM strategy_generations
                WHERE strategy_generation_id = ?
                """,
                (generation_id,),
            ).fetchone()
            if (
                recorded["parent_generation_id"] != parent_generation_id
                or recorded["changed_field"] != changed_field
            ):
                raise FenceError(
                    "strategy content is already bound to different lineage"
                )
        return generation_id

    def application_summary_rows(self) -> list[dict[str, str | None]]:
        rows = self.connection.execute(
            """
            SELECT
              applications.canonical_url,
              applications.owner,
              applications.current_state,
              submit_intents.status AS submission_state
            FROM applications
            LEFT JOIN submit_intents
              ON submit_intents.application_id = applications.id
            ORDER BY applications.created_at, applications.rowid
            """
        ).fetchall()
        return [
            {
                "canonical_url": str(row["canonical_url"]),
                "owner": str(row["owner"]),
                "current_state": str(row["current_state"]),
                "submission_state": (
                    str(row["submission_state"])
                    if row["submission_state"] is not None
                    else None
                ),
            }
            for row in rows
        ]

    def event_summary_rows(self) -> list[dict[str, Any]]:
        applications = self.connection.execute(
            "SELECT id, canonical_url, owner FROM applications ORDER BY created_at, rowid"
        ).fetchall()
        projection: list[dict[str, Any]] = []
        for application in applications:
            rows = self.connection.execute(
                "SELECT rowid AS event_rowid, from_state, to_state, "
                "payload_json FROM events "
                "WHERE application_id = ? ORDER BY rowid",
                (application["id"],),
            ).fetchall()
            if not rows or rows[0]["from_state"] is not None:
                raise FenceError("application event chain lacks a valid origin")
            first_state = str(rows[0]["to_state"])
            first_payload = json.loads(str(rows[0]["payload_json"]))
            external_origin = first_state == "submitted" and (
                first_payload.get("external_import") is True
                and all(first_payload.get(key) for key in (
                    "applied_at", "source", "source_message_id", "evidence_sha256"
                ))
            )
            if first_state != "discovered" and not external_origin:
                raise FenceError("application event chain lacks a valid origin")
            previous = first_state
            ever_submitted = first_state == "submitted"
            submission_attempted = first_state in {"submitted", "submit_unknown"}
            for index, event in enumerate(rows[1:], start=1):
                to_state = str(event["to_state"])
                if str(event["from_state"]) != previous:
                    raise FenceError("application event chain is discontinuous")
                paired_correction = False
                if to_state == "submitted" and index + 2 < len(rows):
                    next_event = rows[index + 1]
                    paired_correction = (
                        str(next_event["from_state"]) == "submitted"
                        and str(next_event["to_state"]) == "email_sent"
                        and is_outreach_truth_correction(
                            self.connection,
                            str(application["id"]),
                            rows[index + 2],
                        )
                    )
                if previous == "submit_unknown" and to_state == "submitted":
                    payload = json.loads(str(event["payload_json"]))
                    if not isinstance(payload, dict):
                        raise FenceError("late confirmation event lacks evidence")
                    has_gmail_confirmation = all(payload.get(key) for key in (
                        "message_id", "thread_id", "evidence_sha256", "received_at"
                    ))
                    has_authoritative_ashby_confirmation = (
                        is_authoritative_ashby_browser_confirmation(
                            self.connection,
                            str(application["id"]),
                            event,
                        )
                    )
                    if index + 1 < len(rows):
                        paired_correction = paired_correction or is_outreach_truth_correction(
                            self.connection, str(application["id"]), rows[index + 1]
                        )
                    if (
                        not has_gmail_confirmation
                        and not has_authoritative_ashby_confirmation
                        and not paired_correction
                    ):
                        raise FenceError("late confirmation event lacks evidence")
                elif previous == "email_sent" and to_state == "submit_unknown":
                    if not is_outreach_truth_correction(
                        self.connection,
                        str(application["id"]),
                        event,
                    ):
                        raise FenceError("email-sent application lacks valid correction")
                elif previous == "submitted":
                    if to_state == "submit_unknown":
                        if not is_outreach_truth_correction(
                            self.connection,
                            str(application["id"]),
                            event,
                        ):
                            raise FenceError("submitted application lacks valid correction")
                    elif to_state == "email_sent":
                        if index + 1 >= len(rows) or not is_outreach_truth_correction(
                            self.connection,
                            str(application["id"]),
                            rows[index + 1],
                        ):
                            raise FenceError(
                                "submitted application has uncorrected email regression"
                            )
                        paired_correction = True
                    else:
                        validate_transition(previous, to_state)
                else:
                    validate_transition(previous, to_state)
                previous = to_state
                ever_submitted = ever_submitted or (
                    to_state == "submitted"
                    and not paired_correction
                )
                submission_attempted = submission_attempted or to_state in {
                    "submitted", "submit_unknown"
                }
            positive_stages = {
                str(row["funnel_stage"])
                for row in self.connection.execute(
                    """
                    SELECT outcomes.funnel_stage
                    FROM funnel_outcomes AS outcomes
                    WHERE outcomes.application_id = ?
                      AND outcomes.disposition = 'positive'
                      AND NOT (
                        outcomes.funnel_stage = 'confirmed_application'
                        AND EXISTS (
                          SELECT 1
                          FROM application_routes AS routes
                          WHERE routes.application_id = outcomes.application_id
                            AND routes.delivery_state = 'delivered'
                            AND routes.recipient_acceptance = 'outreach_only'
                            AND routes.delivery_evidence_sha256 = outcomes.evidence_sha256
                        )
                      )
                    """,
                    (application["id"],),
                ).fetchall()
            }
            projection.append(
                {
                    "application_id": str(application["id"]),
                    "canonical_url": str(application["canonical_url"]),
                    "owner": str(application["owner"]),
                    "current_state": previous,
                    "ever_submitted": ever_submitted,
                    "submission_attempted": submission_attempted,
                    "positive_funnel_stages": sorted(positive_stages),
                }
            )
        return projection

    def retryable_applications(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
              applications.id AS application_id,
              applications.company,
              applications.title,
              applications.canonical_url,
              submit_intents.intent_id,
              submit_intents.fence
            FROM submit_intents
            JOIN applications ON applications.id = submit_intents.application_id
            WHERE submit_intents.status = 'not_submitted'
              AND applications.current_state = 'not_submitted'
            ORDER BY submit_intents.completed_at, submit_intents.rowid
            """
        ).fetchall()
        return [
            {
                "application_id": str(row["application_id"]),
                "company": str(row["company"]),
                "title": str(row["title"]),
                "canonical_url": str(row["canonical_url"]),
                "intent_id": str(row["intent_id"]),
                "fence": int(row["fence"]),
            }
            for row in rows
        ]

    def submission_attempts(self, application_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT
              intent_id, fence, payload_hash, resume_path, resume_sha256,
              ats_snapshot_path, ats_snapshot_sha256,
              fill_receipt_path, fill_receipt_sha256, japan_day, slot,
              status, created_at, completed_at
            FROM submission_attempts
            WHERE application_id = ?
            ORDER BY fence
            """,
            (application_id,),
        ).fetchall()
        return [
            {
                "intent_id": str(row["intent_id"]),
                "fence": int(row["fence"]),
                "payload_hash": str(row["payload_hash"]),
                "resume_path": row["resume_path"],
                "resume_sha256": row["resume_sha256"],
                "ats_snapshot_path": row["ats_snapshot_path"],
                "ats_snapshot_sha256": row["ats_snapshot_sha256"],
                "fill_receipt_path": row["fill_receipt_path"],
                "fill_receipt_sha256": row["fill_receipt_sha256"],
                "japan_day": str(row["japan_day"]),
                "slot": int(row["slot"]),
                "status": str(row["status"]),
                "created_at": str(row["created_at"]),
                "completed_at": row["completed_at"],
            }
            for row in rows
        ]

    def claim_submission(
        self,
        application_id: str,
        japan_day: str,
        payload_hash: str,
        *,
        resume_path: Path,
        resume_sha256: str,
        ats_snapshot_path: Path,
        ats_snapshot_sha256: str,
        fill_receipt_path: Path | None = None,
        fill_receipt_sha256: str | None = None,
        portfolio_bucket: str | None = None,
        user_authorized_overflow: bool = False,
        overflow_reason: str | None = None,
    ) -> SubmitIntent | None:
        if user_authorized_overflow and not str(overflow_reason or "").strip():
            raise ValueError("user-authorized overflow requires a reason")
        if not user_authorized_overflow and overflow_reason is not None:
            raise ValueError("overflow reason requires user authorization")
        if portfolio_bucket is not None and portfolio_bucket not in PORTFOLIO_LIMITS:
            raise ValueError("portfolio_bucket is invalid")
        resolved_resume = Path(resume_path).expanduser().resolve()
        if not resolved_resume.is_file():
            raise ValueError(f"resume is not a file: {resolved_resume}")
        actual_resume_sha256 = hashlib.sha256(resolved_resume.read_bytes()).hexdigest()
        if actual_resume_sha256 != resume_sha256:
            raise ValueError("resume SHA-256 does not match the selected file")
        resolved_snapshot = Path(ats_snapshot_path).expanduser().resolve()
        if not resolved_snapshot.is_file():
            raise ValueError(
                f"ATS snapshot SHA-256 cannot be verified: not a file: {resolved_snapshot}"
            )
        snapshot_bytes = resolved_snapshot.read_bytes()
        actual_snapshot_sha256 = hashlib.sha256(snapshot_bytes).hexdigest()
        if actual_snapshot_sha256 != ats_snapshot_sha256:
            raise ValueError("ATS snapshot SHA-256 does not match the selected file")
        try:
            snapshot = json.loads(snapshot_bytes)
            snapshot_evaluation = evaluate_snapshot(snapshot)
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"ATS snapshot is invalid: {error}") from error
        if not snapshot_evaluation["ready"]:
            blockers = ",".join(snapshot_evaluation["blockers"])
            raise ValueError(f"ATS snapshot is not ready: {blockers}")
        if not snapshot_evaluation["claim_ready"]:
            raise ValueError("ATS snapshot is not claim-ready: application form not open")
        application_before_claim = self.connection.execute(
            "SELECT canonical_url FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()
        if application_before_claim is None:
            raise KeyError(application_id)
        if canonical_url(snapshot["url"]) != str(application_before_claim["canonical_url"]):
            raise ValueError("ATS snapshot URL does not match the application")
        if fill_receipt_path is None or fill_receipt_sha256 is None:
            raise ValueError("claim-ready fill receipt is required")
        resolved_fill_receipt = Path(fill_receipt_path).expanduser().resolve()
        if not resolved_fill_receipt.is_file():
            raise ValueError("fill receipt SHA-256 cannot be verified: file is missing")
        fill_receipt_bytes = resolved_fill_receipt.read_bytes()
        actual_fill_receipt_sha256 = hashlib.sha256(fill_receipt_bytes).hexdigest()
        if actual_fill_receipt_sha256 != fill_receipt_sha256:
            raise ValueError("fill receipt SHA-256 does not match the selected file")
        try:
            fill_receipt = json.loads(fill_receipt_bytes)
        except json.JSONDecodeError as error:
            raise ValueError("fill receipt is invalid JSON") from error
        if fill_receipt.get("status") != "claim_ready":
            raise ValueError("fill receipt is not claim-ready")
        if fill_receipt.get("submit_clicked") is not False:
            raise ValueError("fill receipt must prove Submit was not clicked")
        if fill_receipt.get("blockers") != []:
            raise ValueError("fill receipt contains unresolved blockers")
        if fill_receipt.get("snapshot_sha256") != ats_snapshot_sha256:
            raise ValueError("fill receipt does not match the ATS snapshot")
        if fill_receipt.get("resume_sha256") != resume_sha256:
            raise ValueError("fill receipt does not match the selected resume")
        if not isinstance(fill_receipt.get("owner_lease_id"), str) or not fill_receipt["owner_lease_id"]:
            raise ValueError("fill receipt browser owner lease is missing")
        if not isinstance(fill_receipt.get("owner_fence"), int) or fill_receipt["owner_fence"] <= 0:
            raise ValueError("fill receipt browser owner fence is missing")
        with self.telemetry.span(
            "submit.intent", {"application.id": application_id}
        ), self._transaction():
            application = self.connection.execute(
                "SELECT canonical_url FROM applications WHERE id = ?",
                (application_id,),
            ).fetchone()
            if application is None:
                raise KeyError(application_id)
            if canonical_url(str(fill_receipt.get("job_url") or "")) != str(
                application["canonical_url"]
            ):
                raise ValueError("fill receipt URL does not match the application")
            existing = self.connection.execute(
                "SELECT * FROM submit_intents WHERE application_id = ?",
                (application_id,),
            ).fetchone()
            current_state = self.current_state(application_id)
            reopening = (
                existing is not None
                and str(existing["status"]) == "not_submitted"
                and current_state == "not_submitted"
            )
            if existing is not None and not reopening:
                return None
            if existing is None and current_state != "materials_ready":
                return None
            stored_bucket = portfolio_bucket or "legacy_unallocated"
            if portfolio_bucket is not None:
                bucket_count = self.connection.execute(
                    "SELECT COUNT(*) AS count FROM daily_slots "
                    "WHERE japan_day = ? AND portfolio_bucket = ?",
                    (japan_day, portfolio_bucket),
                ).fetchone()
                if int(bucket_count["count"]) >= PORTFOLIO_LIMITS[portfolio_bucket]:
                    return None
            used = {
                int(row["slot"])
                for row in self.connection.execute(
                    "SELECT slot FROM daily_slots WHERE japan_day = ?",
                    (japan_day,),
                ).fetchall()
            }
            slot = next((candidate for candidate in range(1, 11) if candidate not in used), None)
            if slot is None and user_authorized_overflow:
                slot = max(used, default=10) + 1
            if slot is None:
                return None
            claimed_at = _now()
            intent = SubmitIntent(
                intent_id=(
                    str(existing["intent_id"]) if reopening else uuid.uuid4().hex
                ),
                application_id=application_id,
                fence=(int(existing["fence"]) + 1 if reopening else 1),
                payload_hash=payload_hash,
                resume_path=str(resolved_resume),
                resume_sha256=resume_sha256,
                ats_snapshot_path=str(resolved_snapshot),
                ats_snapshot_sha256=ats_snapshot_sha256,
                fill_receipt_path=str(resolved_fill_receipt),
                fill_receipt_sha256=fill_receipt_sha256,
                japan_day=japan_day,
                slot=slot,
            )
            self.connection.execute(
                """
                INSERT INTO daily_slots
                  (japan_day, slot, application_id, portfolio_bucket, status)
                VALUES (?, ?, ?, ?, 'claimed')
                """,
                (japan_day, slot, application_id, stored_bucket),
            )
            if reopening:
                self.connection.execute(
                    """
                    UPDATE submit_intents
                    SET fence = ?, payload_hash = ?, resume_path = ?,
                        resume_sha256 = ?, ats_snapshot_path = ?,
                        ats_snapshot_sha256 = ?, fill_receipt_path = ?,
                        fill_receipt_sha256 = ?, japan_day = ?, slot = ?,
                        status = 'submit_claimed', created_at = ?,
                        completed_at = NULL
                    WHERE intent_id = ? AND fence = ? AND status = 'not_submitted'
                    """,
                    (
                        intent.fence,
                        intent.payload_hash,
                        intent.resume_path,
                        intent.resume_sha256,
                        intent.ats_snapshot_path,
                        intent.ats_snapshot_sha256,
                        intent.fill_receipt_path,
                        intent.fill_receipt_sha256,
                        intent.japan_day,
                        intent.slot,
                        claimed_at,
                        intent.intent_id,
                        int(existing["fence"]),
                    ),
                )
            else:
                self.connection.execute(
                    """
                    INSERT INTO submit_intents
                      (intent_id, application_id, fence, payload_hash, resume_path,
                       resume_sha256, ats_snapshot_path, ats_snapshot_sha256,
                       fill_receipt_path, fill_receipt_sha256,
                       japan_day, slot, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'submit_claimed', ?)
                    """,
                    (
                        intent.intent_id,
                        intent.application_id,
                        intent.fence,
                        intent.payload_hash,
                        intent.resume_path,
                        intent.resume_sha256,
                        intent.ats_snapshot_path,
                        intent.ats_snapshot_sha256,
                        intent.fill_receipt_path,
                        intent.fill_receipt_sha256,
                        intent.japan_day,
                        intent.slot,
                        claimed_at,
                    ),
                )
            self.connection.execute(
                """
                INSERT INTO submission_attempts
                  (intent_id, fence, application_id, payload_hash, resume_path,
                   resume_sha256, ats_snapshot_path, ats_snapshot_sha256,
                   fill_receipt_path, fill_receipt_sha256,
                   japan_day, slot, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'submit_claimed', ?)
                """,
                (
                    intent.intent_id,
                    intent.fence,
                    intent.application_id,
                    intent.payload_hash,
                    intent.resume_path,
                    intent.resume_sha256,
                    intent.ats_snapshot_path,
                    intent.ats_snapshot_sha256,
                    intent.fill_receipt_path,
                    intent.fill_receipt_sha256,
                    intent.japan_day,
                    intent.slot,
                    claimed_at,
                ),
            )
            self.connection.execute(
                """
                INSERT INTO submission_click_phases
                  (intent_id, fence, phase, updated_at)
                VALUES (?, ?, 'pre_click', ?)
                """,
                (intent.intent_id, intent.fence, claimed_at),
            )
            self.connection.execute(
                """
                INSERT INTO submission_transport_phases
                  (intent_id, fence, phase, updated_at)
                VALUES (?, ?, 'pre_request', ?)
                """,
                (intent.intent_id, intent.fence, claimed_at),
            )
            self._transition_in_transaction(
                application_id,
                "submit_claimed",
                {
                    "intent_id": intent.intent_id,
                    "fence": intent.fence,
                    "payload_hash": payload_hash,
                    "resume_sha256": resume_sha256,
                    "ats_snapshot_sha256": ats_snapshot_sha256,
                    "fill_receipt_sha256": fill_receipt_sha256,
                    "user_authorized_overflow": user_authorized_overflow,
                    "overflow_reason": overflow_reason,
                },
            )
            return intent

    def record_submission_materials(
        self,
        *,
        intent_id: str,
        fence: int,
        resume_path: Path,
        resume_sha256: str,
        cover_letter: str | None,
        employer_answers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        resolved_resume = Path(resume_path).expanduser().resolve()
        if not resolved_resume.is_file():
            raise ValueError("submission resume is not a file")
        if not re.fullmatch(r"[a-f0-9]{64}", resume_sha256):
            raise ValueError("submission resume SHA-256 is invalid")
        if hashlib.sha256(resolved_resume.read_bytes()).hexdigest() != resume_sha256:
            raise ValueError("submission resume SHA-256 does not match the file")
        if cover_letter is not None and (
            not isinstance(cover_letter, str) or not cover_letter.strip()
        ):
            raise ValueError("cover letter must be null or non-empty exact text")
        if not isinstance(employer_answers, list):
            raise ValueError("employer answers must be an array")
        normalized_answers: list[dict[str, Any]] = []
        for answer in employer_answers:
            if not isinstance(answer, dict) or set(answer) != {
                "question", "answer", "fact_ids"
            }:
                raise ValueError("employer answer has invalid fields")
            question = answer.get("question")
            value = answer.get("answer")
            fact_ids = answer.get("fact_ids")
            if not isinstance(question, str) or not question.strip():
                raise ValueError("employer question must be exact non-empty text")
            if not isinstance(value, str) or not value.strip():
                raise ValueError("employer answer must be exact non-empty text")
            if (
                not isinstance(fact_ids, list)
                or len(fact_ids) != len(set(fact_ids))
                or any(not isinstance(item, str) or not item for item in fact_ids)
            ):
                raise ValueError("employer answer fact IDs are invalid")
            normalized_answers.append(
                {"question": question, "answer": value, "fact_ids": fact_ids}
            )
        answers_json = json.dumps(
            normalized_answers,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        payload = {
            "intent_id": intent_id,
            "fence": fence,
            "resume_path": str(resolved_resume),
            "resume_sha256": resume_sha256,
            "cover_letter": cover_letter,
            "employer_answers": normalized_answers,
        }
        payload_sha256 = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        with self._transaction():
            attempt = self.connection.execute(
                "SELECT * FROM submission_attempts WHERE intent_id = ? AND fence = ?",
                (intent_id, fence),
            ).fetchone()
            if attempt is None:
                raise FenceError("submission material receipt fence does not exist")
            if (
                str(attempt["resume_path"]) != str(resolved_resume)
                or str(attempt["resume_sha256"]) != resume_sha256
            ):
                raise FenceError("submission material resume differs from intent")
            existing = self.connection.execute(
                "SELECT * FROM submission_material_receipts "
                "WHERE intent_id = ? AND fence = ?",
                (intent_id, fence),
            ).fetchone()
            if existing is not None:
                if str(existing["payload_sha256"]) != payload_sha256:
                    raise FenceError("submission material receipt cannot be rebound")
                return {"payload_sha256": payload_sha256, **payload}
            if str(attempt["status"]) != "submit_claimed":
                raise FenceError("submission material receipt fence is not active")
            self.connection.execute(
                """
                INSERT INTO submission_material_receipts
                  (intent_id, fence, application_id, resume_path, resume_sha256,
                   cover_letter, employer_answers_json, payload_sha256, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    intent_id, fence, str(attempt["application_id"]),
                    str(resolved_resume), resume_sha256, cover_letter,
                    answers_json, payload_sha256, _now(),
                ),
            )
        return {"payload_sha256": payload_sha256, **payload}

    def submission_click_phase(self, intent_id: str, fence: int) -> str:
        row = self.connection.execute(
            "SELECT phase FROM submission_click_phases "
            "WHERE intent_id = ? AND fence = ?",
            (intent_id, fence),
        ).fetchone()
        if row is None:
            raise FenceError("submission click phase fence does not exist")
        return str(row["phase"])

    def submission_transport_phase(self, intent_id: str, fence: int) -> str:
        row = self.connection.execute(
            "SELECT phase FROM submission_transport_phases "
            "WHERE intent_id = ? AND fence = ?",
            (intent_id, fence),
        ).fetchone()
        if row is None:
            raise FenceError("submission transport phase fence does not exist")
        return str(row["phase"])

    def mark_submission_request_started(self, intent_id: str, fence: int) -> str:
        with self._transaction():
            attempt = self.connection.execute(
                "SELECT status FROM submission_attempts "
                "WHERE intent_id = ? AND fence = ?",
                (intent_id, fence),
            ).fetchone()
            if attempt is None or str(attempt["status"]) != "submit_claimed":
                raise FenceError("submission transport fence is not active")
            if self.submission_click_phase(intent_id, fence) != "clicked":
                raise FenceError("submit request requires a committed click")
            if self.submission_transport_phase(intent_id, fence) != "pre_request":
                raise FenceError("submit request has already started")
            self.connection.execute(
                "UPDATE submission_transport_phases "
                "SET phase = 'request_started', updated_at = ? "
                "WHERE intent_id = ? AND fence = ? AND phase = 'pre_request'",
                (_now(), intent_id, fence),
            )
        return "request_started"

    def complete_client_blocked_submission(
        self,
        *,
        intent_id: str,
        fence: int,
        blocker: str,
        evidence_sha256: str,
    ) -> str:
        if blocker != "ashby_recaptcha_before_submit_request":
            raise ValueError("unsupported client submission blocker")
        if not re.fullmatch(r"[a-f0-9]{64}", evidence_sha256):
            raise ValueError("client blocker evidence must be a lowercase SHA-256")
        with self._transaction():
            attempt = self.connection.execute(
                "SELECT status FROM submission_attempts "
                "WHERE intent_id = ? AND fence = ?",
                (intent_id, fence),
            ).fetchone()
            if attempt is None or str(attempt["status"]) != "submit_claimed":
                raise FenceError("client blocker fence is not active")
            if self.submission_click_phase(intent_id, fence) != "clicked":
                raise FenceError("client blocker requires a committed click")
            if self.submission_transport_phase(intent_id, fence) != "pre_request":
                raise FenceError("submit request already started")
            receipt = self.connection.execute(
                "SELECT 1 FROM submission_material_receipts "
                "WHERE intent_id = ? AND fence = ?",
                (intent_id, fence),
            ).fetchone()
            if receipt is None:
                raise FenceError("submission material receipt is required")
            self.connection.execute(
                """
                INSERT INTO submission_client_block_receipts
                  (intent_id, fence, blocker, evidence_sha256, recorded_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (intent_id, fence, blocker, evidence_sha256, _now()),
            )
        self.complete_submission(intent_id, fence, "not_submitted")
        return "not_submitted"

    def mark_submission_click_phase(
        self, intent_id: str, fence: int, phase: str
    ) -> str:
        if phase not in {"clicked", "confirmed"}:
            raise ValueError("submission click phase must be clicked or confirmed")
        with self._transaction():
            attempt = self.connection.execute(
                "SELECT status FROM submission_attempts "
                "WHERE intent_id = ? AND fence = ?",
                (intent_id, fence),
            ).fetchone()
            if attempt is None or str(attempt["status"]) != "submit_claimed":
                raise FenceError("submission click phase fence is not active")
            receipt = self.connection.execute(
                "SELECT 1 FROM submission_material_receipts "
                "WHERE intent_id = ? AND fence = ?",
                (intent_id, fence),
            ).fetchone()
            if receipt is None:
                raise FenceError("submission material receipt is required")
            current = self.submission_click_phase(intent_id, fence)
            allowed = {
                "pre_click": "clicked",
                "clicked": "confirmed",
                "confirmed": "confirmed",
            }
            if allowed[current] != phase:
                raise FenceError(
                    f"invalid submission click phase: {current} -> {phase}"
                )
            if current != phase:
                self.connection.execute(
                    "UPDATE submission_click_phases SET phase = ?, updated_at = ? "
                    "WHERE intent_id = ? AND fence = ? AND phase = ?",
                    (phase, _now(), intent_id, fence, current),
                )
        return phase

    def reconcile_interrupted_submission(
        self, intent_id: str, fence: int
    ) -> str:
        phase = self.submission_click_phase(intent_id, fence)
        outcome = "not_submitted" if phase == "pre_click" else "submit_unknown"
        self.complete_submission(intent_id, fence, outcome)
        return outcome

    def complete_submission(
        self, intent_id: str, fence: int, outcome: str
    ) -> None:
        if outcome not in {"submitted", "submit_unknown", "not_submitted"}:
            raise ValueError(f"invalid submission outcome: {outcome}")
        with self._transaction():
            row = self.connection.execute(
                "SELECT * FROM submit_intents WHERE intent_id = ?", (intent_id,)
            ).fetchone()
            if row is None or int(row["fence"]) != fence:
                raise FenceError("submission fence does not match")
            if row["status"] != "submit_claimed":
                raise FenceError("submission intent is already completed")
            if outcome in {"submitted", "submit_unknown"}:
                receipt = self.connection.execute(
                    "SELECT 1 FROM submission_material_receipts "
                    "WHERE intent_id = ? AND fence = ?",
                    (intent_id, fence),
                ).fetchone()
                if receipt is None:
                    raise FenceError("submission material receipt is required")
            completed_at = _now()
            self.connection.execute(
                """
                UPDATE submit_intents SET status = ?, completed_at = ?
                WHERE intent_id = ? AND fence = ?
                """,
                (outcome, completed_at, intent_id, fence),
            )
            self.connection.execute(
                """
                UPDATE submission_attempts SET status = ?, completed_at = ?
                WHERE intent_id = ? AND fence = ?
                """,
                (outcome, completed_at, intent_id, fence),
            )
            self.connection.execute(
                """
                UPDATE daily_slots SET status = ?
                WHERE japan_day = ? AND slot = ? AND application_id = ?
                """,
                (outcome, row["japan_day"], row["slot"], row["application_id"]),
            )
            self._transition_in_transaction(
                str(row["application_id"]),
                outcome,
                {"intent_id": intent_id, "fence": fence},
            )
            if outcome == "not_submitted":
                self.connection.execute(
                    """
                    DELETE FROM daily_slots
                    WHERE japan_day = ? AND slot = ? AND application_id = ?
                    """,
                    (row["japan_day"], row["slot"], row["application_id"]),
                )

    def reconcile_submission_confirmation(
        self,
        *,
        intent_id: str,
        message_id: str,
        thread_id: str,
        evidence_sha256: str,
        received_at: str,
    ) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", message_id):
            raise ValueError("invalid Gmail message ID")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", thread_id):
            raise ValueError("invalid Gmail thread ID")
        if not re.fullmatch(r"[a-f0-9]{64}", evidence_sha256):
            raise ValueError("invalid confirmation evidence hash")
        try:
            received = datetime.fromisoformat(received_at)
        except ValueError as error:
            raise ValueError("received_at must be RFC3339") from error
        if received.tzinfo is None:
            raise ValueError("received_at must include a timezone")

        with self._transaction():
            existing_message = self.connection.execute(
                """
                SELECT thread_id, intent_id, evidence_sha256, received_at
                FROM submission_confirmations
                WHERE message_id = ?
                """,
                (message_id,),
            ).fetchone()
            if existing_message is not None:
                expected = (
                    thread_id,
                    intent_id,
                    evidence_sha256,
                    received_at,
                )
                actual = (
                    str(existing_message["thread_id"]),
                    str(existing_message["intent_id"]),
                    str(existing_message["evidence_sha256"]),
                    str(existing_message["received_at"]),
                )
                if actual != expected:
                    raise FenceError(
                        "Gmail message ID is already bound to different evidence"
                    )
                return "duplicate"

            existing_intent = self.connection.execute(
                """
                SELECT message_id
                FROM submission_confirmations
                WHERE intent_id = ?
                """,
                (intent_id,),
            ).fetchone()
            if existing_intent is not None:
                raise FenceError(
                    "submission intent already has a different confirmation"
                )

            row = self.connection.execute(
                """
                SELECT
                  submit_intents.*,
                  applications.current_state
                FROM submit_intents
                JOIN applications
                  ON applications.id = submit_intents.application_id
                WHERE submit_intents.intent_id = ?
                """,
                (intent_id,),
            ).fetchone()
            if row is None:
                raise FenceError("submission intent does not exist")
            if (
                str(row["status"]) != "submit_unknown"
                or str(row["current_state"]) != "submit_unknown"
            ):
                raise FenceError(
                    "only a submit_unknown application can be reconciled"
                )
            intent_created = datetime.fromisoformat(str(row["created_at"]))
            if received < intent_created:
                raise FenceError("confirmation predates the submission intent")

            created_at = _now()
            self.connection.execute(
                """
                INSERT INTO submission_confirmations
                  (message_id, thread_id, intent_id, evidence_sha256,
                   received_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    thread_id,
                    intent_id,
                    evidence_sha256,
                    received_at,
                    created_at,
                ),
            )
            intent_update = self.connection.execute(
                """
                UPDATE submit_intents
                SET status = 'submitted'
                WHERE intent_id = ? AND status = 'submit_unknown'
                """,
                (intent_id,),
            )
            attempt_update = self.connection.execute(
                """
                UPDATE submission_attempts
                SET status = 'submitted'
                WHERE intent_id = ? AND fence = ? AND status = 'submit_unknown'
                """,
                (intent_id, int(row["fence"])),
            )
            slot_update = self.connection.execute(
                """
                UPDATE daily_slots
                SET status = 'submitted'
                WHERE japan_day = ? AND slot = ? AND application_id = ?
                  AND status = 'submit_unknown'
                """,
                (
                    str(row["japan_day"]),
                    int(row["slot"]),
                    str(row["application_id"]),
                ),
            )
            if (
                intent_update.rowcount != 1
                or attempt_update.rowcount != 1
                or slot_update.rowcount != 1
            ):
                raise FenceError("submission confirmation state is inconsistent")
            application_id = str(row["application_id"])
            self._append_event(
                application_id,
                "submit_unknown",
                "submitted",
                {
                    "intent_id": intent_id,
                    "message_id": message_id,
                    "thread_id": thread_id,
                    "evidence_sha256": evidence_sha256,
                    "received_at": received_at,
                },
            )
            application_update = self.connection.execute(
                """
                UPDATE applications
                SET current_state = 'submitted'
                WHERE id = ? AND current_state = 'submit_unknown'
                """,
                (application_id,),
            )
            if application_update.rowcount != 1:
                raise FenceError("application confirmation state is inconsistent")
            outcome_identity = {
                "application_id": application_id,
                "funnel_stage": "confirmed_application",
                "disposition": "positive",
                "evidence_source": "gmail",
                "evidence_sha256": evidence_sha256,
                "occurred_at": received_at,
                "observed_at": received_at,
                "observation_policy_version": None,
            }
            encoded_outcome = json.dumps(
                outcome_identity,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            self._record_funnel_outcome_in_transaction(
                outcome_id=(
                    "outcome-"
                    + hashlib.sha256(
                        encoded_outcome.encode("utf-8")
                    ).hexdigest()
                ),
                **outcome_identity,
            )
            self._rebuild_strategy_outcome_projection_in_transaction()
            return "reconciled"

    def _append_application_route_event(
        self,
        route_id: str,
        from_state: str | None,
        to_state: str,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        correlation = self._current_correlation()
        self.connection.execute(
            """
            INSERT INTO application_route_events
              (event_id, route_id, from_state, to_state, payload_json, created_at,
               trace_id, span_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                route_id,
                from_state,
                to_state,
                json.dumps(dict(payload or {}), ensure_ascii=False, sort_keys=True),
                _now(),
                correlation["trace_id"], correlation["span_id"],
            ),
        )

    def register_application_route(
        self,
        application_id: str,
        *,
        route_kind: str,
        endpoint: str,
        ordinal: int,
        source_url: str,
        source_sha256: str,
        recipient_acceptance: str,
    ) -> str:
        route_kinds = {
            "canonical_ats",
            "alternate_official",
            "recruiting_email",
            "recruiting_outreach",
        }
        acceptances = {"not_applicable", "accepts_applications", "outreach_only"}
        if route_kind not in route_kinds:
            raise ValueError("application route kind is invalid")
        if recipient_acceptance not in acceptances:
            raise ValueError("recipient acceptance is invalid")
        if not isinstance(ordinal, int) or ordinal <= 0:
            raise ValueError("application route ordinal is invalid")
        if re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None:
            raise ValueError("application route source SHA-256 is invalid")
        normalized_source = canonical_url(source_url)
        endpoint_value = endpoint.strip()
        if not endpoint_value:
            raise ValueError("application route endpoint is empty")
        row = self.connection.execute(
            "SELECT company, title FROM applications WHERE id = ?", (application_id,)
        ).fetchone()
        if row is None:
            raise ValueError("application does not exist")
        cross_key = company_role_key(row["company"], row["title"])
        route_id = "route-" + hashlib.sha256(
            f"{application_id}\0{route_kind}\0{endpoint_value}".encode("utf-8")
        ).hexdigest()
        now = _now()
        with self._transaction():
            existing = self.connection.execute(
                "SELECT * FROM application_routes WHERE route_id = ?", (route_id,)
            ).fetchone()
            if existing is not None:
                expected = (
                    application_id,
                    cross_key,
                    ordinal,
                    route_kind,
                    endpoint_value,
                    normalized_source,
                    source_sha256,
                    recipient_acceptance,
                )
                actual = tuple(
                    existing[key]
                    for key in (
                        "application_id",
                        "cross_route_key",
                        "ordinal",
                        "route_kind",
                        "endpoint",
                        "source_url",
                        "source_sha256",
                        "recipient_acceptance",
                    )
                )
                if actual != expected:
                    raise FenceError("application route replay does not match")
                return route_id
            self.connection.execute(
                """
                INSERT INTO application_routes
                  (route_id, application_id, cross_route_key, ordinal, route_kind,
                   endpoint, source_url, source_sha256, recipient_acceptance,
                   delivery_state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'eligible', ?, ?)
                """,
                (
                    route_id,
                    application_id,
                    cross_key,
                    ordinal,
                    route_kind,
                    endpoint_value,
                    normalized_source,
                    source_sha256,
                    recipient_acceptance,
                    now,
                    now,
                ),
            )
            self._append_application_route_event(route_id, None, "eligible")
        return route_id

    def claim_application_route(
        self,
        route_id: str,
        *,
        actor: str,
        fence: int,
        message_path: str,
        message_sha256: str,
        resume_path: str,
        resume_sha256: str,
    ) -> None:
        if actor != "resident_worker":
            raise FenceError("only resident worker may claim application route")
        for value in (message_sha256, resume_sha256):
            if re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ValueError("route material SHA-256 is invalid")
        if fence <= 0:
            raise ValueError("route fence is invalid")
        with self._transaction():
            row = self.connection.execute(
                "SELECT * FROM application_routes WHERE route_id = ?", (route_id,)
            ).fetchone()
            if row is None:
                raise ValueError("application route does not exist")
            if row["delivery_state"] != "eligible":
                raise FenceError("application route is not eligible")
            action_class_kinds = (
                ("canonical_ats", "alternate_official")
                if row["route_kind"] in {"canonical_ats", "alternate_official"}
                else ("recruiting_email", "recruiting_outreach")
            )
            live = self.connection.execute(
                """
                SELECT route_id FROM application_routes
                WHERE cross_route_key = ? AND route_id != ?
                  AND route_kind IN (?, ?)
                  AND delivery_state IN
                    ('action_started', 'delivered', 'delivery_unknown', 'replied')
                """,
                (row["cross_route_key"], route_id, *action_class_kinds),
            ).fetchone()
            if live is not None:
                raise FenceError("application route action class is already fenced")
            now = _now()
            self.connection.execute(
                """
                UPDATE application_routes
                SET delivery_state = 'action_started', actor = ?, fence = ?,
                    message_path = ?, message_sha256 = ?, resume_path = ?,
                    resume_sha256 = ?, updated_at = ?
                WHERE route_id = ?
                """,
                (
                    actor,
                    fence,
                    message_path,
                    message_sha256,
                    resume_path,
                    resume_sha256,
                    now,
                    route_id,
                ),
            )
            self._append_application_route_event(
                route_id,
                "eligible",
                "action_started",
                {"actor": actor, "fence": fence},
            )

    def complete_application_route(
        self,
        route_id: str,
        *,
        fence: int,
        state: str,
        provider_id: str,
        evidence_sha256: str,
    ) -> None:
        if state not in {"failed", "delivered", "delivery_unknown"}:
            raise ValueError("application route completion state is invalid")
        if re.fullmatch(r"[0-9a-f]{64}", evidence_sha256) is None:
            raise ValueError("application route evidence SHA-256 is invalid")
        with self._transaction():
            row = self.connection.execute(
                "SELECT * FROM application_routes WHERE route_id = ?",
                (route_id,),
            ).fetchone()
            if row is None or row["delivery_state"] != "action_started" or int(row["fence"]) != fence:
                raise FenceError("application route completion fence does not match")
            now = _now()
            self.connection.execute(
                """
                UPDATE application_routes
                SET delivery_state = ?, provider_id = ?,
                    delivery_evidence_sha256 = ?, updated_at = ?
                WHERE route_id = ?
                """,
                (state, provider_id, evidence_sha256, now, route_id),
            )
            self._append_application_route_event(
                route_id,
                "action_started",
                state,
                {"provider_id": provider_id, "evidence_sha256": evidence_sha256},
            )
            if state == "delivered":
                self._project_delivered_application_route_in_transaction(
                    row={**dict(row), "updated_at": now},
                    provider_id=provider_id,
                    evidence_sha256=evidence_sha256,
                )

    def _project_delivered_application_route_in_transaction(
        self,
        *,
        row: Mapping[str, Any],
        provider_id: str,
        evidence_sha256: str,
    ) -> None:
        if str(row["recipient_acceptance"]) == "outreach_only":
            return
        application_id = str(row["application_id"])
        route_id = str(row["route_id"])
        current = self.current_state(application_id)
        paths = {
            "discovered": ("qualified", "materials_ready", "submit_claimed", "submitted"),
            "qualified": ("materials_ready", "submit_claimed", "submitted"),
            "materials_ready": ("submit_claimed", "submitted"),
            "not_submitted": ("submit_claimed", "submitted"),
            "submit_claimed": ("submitted",),
        }
        payload = {
            "route_id": route_id,
            "provider_id": provider_id,
            "channel": str(row["route_kind"]),
        }
        if current == "submit_unknown":
            self._append_event(application_id, current, "submitted", payload)
            self.connection.execute(
                "UPDATE applications SET current_state = 'submitted' WHERE id = ?",
                (application_id,),
            )
        else:
            for target in paths.get(current, ()):
                self._transition_in_transaction(application_id, target, payload)

        delivered_at = datetime.fromisoformat(str(row["updated_at"]))
        japan_day = delivered_at.astimezone(timezone(timedelta(hours=9))).date().isoformat()
        existing_slot = self.connection.execute(
            "SELECT japan_day, slot FROM daily_slots WHERE application_id = ?",
            (application_id,),
        ).fetchone()
        if existing_slot is None:
            used = {
                int(slot["slot"])
                for slot in self.connection.execute(
                    "SELECT slot FROM daily_slots WHERE japan_day = ?", (japan_day,)
                ).fetchall()
            }
            slot = next(value for value in range(1, len(used) + 2) if value not in used)
            self.connection.execute(
                "INSERT INTO daily_slots "
                "(japan_day, slot, application_id, portfolio_bucket, status) "
                "VALUES (?, ?, ?, 'legacy_unallocated', 'submitted')",
                (japan_day, slot, application_id),
            )
        else:
            self.connection.execute(
                "UPDATE daily_slots SET status = 'submitted' WHERE application_id = ?",
                (application_id,),
            )

        evidence_source = (
            "ats"
            if str(row["route_kind"]) in {"canonical_ats", "alternate_official"}
            else "gmail"
        )
        identity = {
            "application_id": application_id,
            "funnel_stage": "confirmed_application",
            "disposition": "positive",
            "evidence_source": evidence_source,
            "evidence_sha256": evidence_sha256,
            "occurred_at": str(row["updated_at"]),
            "observed_at": str(row["updated_at"]),
            "observation_policy_version": None,
        }
        encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        self._record_funnel_outcome_in_transaction(
            outcome_id=f"outcome-{hashlib.sha256(encoded.encode()).hexdigest()}",
            **identity,
        )
        self._rebuild_strategy_outcome_projection_in_transaction()

    def reconcile_delivered_application_routes(self) -> dict[str, int]:
        with self._transaction():
            rows = self.connection.execute(
                "SELECT * FROM application_routes WHERE delivery_state = 'delivered'"
            ).fetchall()
            for row in rows:
                self._project_delivered_application_route_in_transaction(
                    row=row,
                    provider_id=str(row["provider_id"]),
                    evidence_sha256=str(row["delivery_evidence_sha256"]),
                )
            corrected = self._reconcile_outreach_truth_in_transaction()
        return {
            "delivered_route_count": len(rows),
            "outreach_correction_count": int(corrected),
        }

    def _reconcile_outreach_truth_in_transaction(self) -> int:
        routes = self.connection.execute(
            """
            SELECT routes.*
            FROM application_routes AS routes
            JOIN applications ON applications.id = routes.application_id
            WHERE routes.route_kind = 'recruiting_outreach'
              AND routes.delivery_state = 'delivered'
              AND routes.recipient_acceptance = 'outreach_only'
            ORDER BY routes.updated_at, routes.route_id
            """
        ).fetchall()
        corrected = 0
        for route in routes:
            application_id = str(route["application_id"])
            current = self.current_state(application_id)
            if current not in {"submitted", "email_sent"}:
                continue
            route_id = str(route["route_id"])
            provider_id = str(route["provider_id"] or "")
            evidence_sha256 = str(route["delivery_evidence_sha256"] or "")
            if not provider_id or not evidence_sha256 or not _has_immutable_outreach_delivery(
                self.connection,
                application_id=application_id,
                route_id=route_id,
                provider_id=provider_id,
                evidence_sha256=evidence_sha256,
            ):
                continue
            event = self.connection.execute(
                "SELECT rowid AS event_rowid, from_state, to_state, payload_json FROM events "
                "WHERE application_id = ? ORDER BY rowid DESC LIMIT 1",
                (application_id,),
            ).fetchone()
            if event is None:
                continue
            try:
                payload = json.loads(str(event["payload_json"]))
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(payload, dict):
                continue
            from_state = str(event["from_state"])
            to_state = str(event["to_state"])
            if current == "submitted":
                correction_from, expected = "submitted", ("submit_unknown", "submitted")
            else:
                correction_from, expected = "email_sent", ("submitted", "email_sent")
            if (
                (from_state, to_state) != expected
                or payload.get("route_id") != route_id
                or payload.get("provider_id") != provider_id
                or payload.get("channel") != "recruiting_outreach"
            ):
                continue
            if correction_from == "submitted" and all(
                payload.get(key)
                for key in ("message_id", "thread_id", "evidence_sha256", "received_at")
            ):
                continue
            if correction_from == "email_sent" and (
                (
                    "evidence_sha256" in payload
                    and payload.get("evidence_sha256") != evidence_sha256
                )
                or _has_authoritative_submission_before(
                    self.connection, application_id, event
                )
            ):
                continue
            self._append_event(
                application_id,
                correction_from,
                "submit_unknown",
                {
                    "route_id": route_id,
                    "provider_id": provider_id,
                    "evidence_sha256": evidence_sha256,
                    "reason": OUTREACH_TRUTH_CORRECTION_REASON,
                },
            )
            self.connection.execute(
                "UPDATE applications SET current_state = 'submit_unknown' WHERE id = ?",
                (application_id,),
            )
            self.connection.execute(
                """
                UPDATE daily_slots
                SET status = 'submit_unknown'
                WHERE application_id = ? AND status = 'submitted'
                """,
                (application_id,),
            )
            corrected += 1
        if corrected:
            self._rebuild_strategy_outcome_projection_in_transaction()
        return corrected

    def record_application_route_reply(
        self,
        route_id: str,
        *,
        provider_id: str,
        evidence_sha256: str,
    ) -> None:
        if re.fullmatch(r"[0-9a-f]{64}", evidence_sha256) is None:
            raise ValueError("application route reply SHA-256 is invalid")
        with self._transaction():
            row = self.connection.execute(
                "SELECT delivery_state FROM application_routes WHERE route_id = ?",
                (route_id,),
            ).fetchone()
            if row is None or row["delivery_state"] != "delivered":
                raise FenceError("only a delivered route may record a reply")
            self.connection.execute(
                """
                UPDATE application_routes
                SET delivery_state = 'replied', reply_provider_id = ?,
                    reply_evidence_sha256 = ?, updated_at = ?
                WHERE route_id = ?
                """,
                (provider_id, evidence_sha256, _now(), route_id),
            )
            self._append_application_route_event(
                route_id,
                "delivered",
                "replied",
                {"provider_id": provider_id, "evidence_sha256": evidence_sha256},
            )

    def application_routes(self, application_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM application_routes WHERE application_id = ? ORDER BY ordinal",
            (application_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def application_route_events(self, route_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT * FROM application_route_events WHERE route_id = ? ORDER BY rowid",
            (route_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def submitted_resume_reports(self) -> list[dict[str, str]]:
        rows = self.connection.execute(
            """
            SELECT
              applications.id AS application_id,
              applications.company,
              applications.title,
              applications.canonical_url,
              submit_intents.resume_path,
              submit_intents.resume_sha256
            FROM submit_intents
            JOIN applications ON applications.id = submit_intents.application_id
            WHERE submit_intents.status = 'submitted'
              AND submit_intents.resume_path IS NOT NULL
              AND submit_intents.resume_sha256 IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM submission_evidence_bundles
                WHERE submission_evidence_bundles.intent_id = submit_intents.intent_id
                  AND submission_evidence_bundles.fence = submit_intents.fence
              )
            ORDER BY submit_intents.completed_at, submit_intents.rowid
            """
        ).fetchall()
        return [
            {
                "application_id": str(row["application_id"]),
                "company": str(row["company"]),
                "title": str(row["title"]),
                "canonical_url": str(row["canonical_url"]),
                "resume_path": str(row["resume_path"]),
                "resume_sha256": str(row["resume_sha256"]),
            }
            for row in rows
        ]

    def record_submission_evidence_bundle(
        self,
        *,
        intent_id: str,
        fence: int,
        pre_submit_path: Path,
        pre_submit_sha256: str,
        post_action_path: Path,
        post_action_sha256: str,
        terminal_path: Path,
        terminal_sha256: str,
        confirmation_path: Path,
        confirmation_sha256: str,
        confirmation_source: str,
        confirmation_id: str,
    ) -> str:
        if confirmation_source not in {"ats", "gmail"}:
            raise ValueError("confirmation source is not authoritative")
        if not confirmation_id.strip():
            raise ValueError("confirmation ID is required")
        artifacts = (
            ("pre_submit", Path(pre_submit_path), pre_submit_sha256),
            ("post_action", Path(post_action_path), post_action_sha256),
            ("terminal", Path(terminal_path), terminal_sha256),
            ("confirmation", Path(confirmation_path), confirmation_sha256),
        )
        normalized: dict[str, str] = {}
        for name, path, claimed in artifacts:
            resolved = path.expanduser().resolve()
            if not resolved.is_file():
                raise ValueError(f"{name} evidence file is missing")
            if not re.fullmatch(r"[a-f0-9]{64}", claimed):
                raise ValueError(f"{name} evidence hash is invalid")
            actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
            if actual != claimed:
                raise ValueError(f"{name} evidence hash mismatch")
            normalized[f"{name}_path"] = str(resolved)
            normalized[f"{name}_sha256"] = claimed
        payload = {
            "intent_id": intent_id,
            "fence": fence,
            **normalized,
            "confirmation_source": confirmation_source,
            "confirmation_id": confirmation_id,
        }
        bundle_sha256 = hashlib.sha256(
            json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        correlation = self._current_correlation()
        with self._transaction():
            intent = self.connection.execute(
                "SELECT application_id, fence, status FROM submit_intents "
                "WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if intent is None or int(intent["fence"]) != fence:
                raise FenceError("submission evidence fence mismatch")
            if str(intent["status"]) != "submitted":
                raise FenceError("submission evidence requires submitted intent")
            existing = self.connection.execute(
                "SELECT bundle_sha256 FROM submission_evidence_bundles "
                "WHERE intent_id = ? AND fence = ?",
                (intent_id, fence),
            ).fetchone()
            if existing is not None:
                if str(existing["bundle_sha256"]) != bundle_sha256:
                    raise FenceError("submission evidence bundle is already bound")
                return bundle_sha256
            self.connection.execute(
                """
                INSERT INTO submission_evidence_bundles
                  (intent_id, fence, application_id,
                   pre_submit_path, pre_submit_sha256,
                   post_action_path, post_action_sha256,
                   terminal_path, terminal_sha256,
                   confirmation_path, confirmation_sha256,
                   confirmation_source, confirmation_id, bundle_sha256, recorded_at,
                   trace_id, span_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    intent_id, fence, str(intent["application_id"]),
                    normalized["pre_submit_path"], normalized["pre_submit_sha256"],
                    normalized["post_action_path"], normalized["post_action_sha256"],
                    normalized["terminal_path"], normalized["terminal_sha256"],
                    normalized["confirmation_path"], normalized["confirmation_sha256"],
                    confirmation_source, confirmation_id, bundle_sha256, _now(),
                    correlation["trace_id"], correlation["span_id"],
                ),
            )
        return bundle_sha256

    def submitted_evidence_reports(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT applications.id AS application_id, applications.company,
                   applications.title, applications.canonical_url,
                   submit_intents.intent_id, submit_intents.fence,
                   submit_intents.resume_path, submit_intents.resume_sha256,
                   submission_evidence_bundles.*
            FROM submission_evidence_bundles
            JOIN submit_intents
              ON submit_intents.intent_id = submission_evidence_bundles.intent_id
             AND submit_intents.fence = submission_evidence_bundles.fence
            JOIN applications
              ON applications.id = submission_evidence_bundles.application_id
            WHERE submit_intents.status = 'submitted'
            ORDER BY submission_evidence_bundles.recorded_at,
                     submission_evidence_bundles.rowid
            """
        ).fetchall()
        return [dict(row) for row in rows]
