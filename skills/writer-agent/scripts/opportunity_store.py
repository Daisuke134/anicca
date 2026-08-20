#!/usr/bin/env python3
"""Durable paid-writing opportunities, evidence, pitches, and transitions."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from claim_store import SHA256_RE, _text, _timestamp, canonicalize_url  # noqa: E402


STATES = frozenset(
    {
        "DISCOVERED", "VERIFIED_OPEN", "POLICY_CLEAR", "PITCH_READY",
        "SUBMITTED", "ACCEPTED", "DRAFTING", "ARTICLE_SUBMITTED",
        "PUBLISHED", "RECEIVED", "CLOSED", "REJECTED_POLICY", "DECLINED",
        "EXPIRED", "VALUE_UNKNOWN",
    }
)
INTAKE_STATES = frozenset({"OPEN", "CLOSED", "PAUSED", "STALE", "UNKNOWN"})
AI_POLICIES = frozenset(
    {"ALLOWED", "ALLOWED_WITH_DISCLOSURE", "PROHIBITED", "UNKNOWN"}
)
FEE_BASES = frozenset({"accepted_article", "published_article", "recurring", "unknown"})
EVIDENCE_KINDS = frozenset(
    {
        "official", "policy", "submission", "acceptance", "article_submission",
        "publication", "payment", "rejection", "closure",
    }
)
ALLOWED_TRANSITIONS = {
    "DISCOVERED": {"VERIFIED_OPEN", "CLOSED", "REJECTED_POLICY", "VALUE_UNKNOWN", "EXPIRED"},
    "VERIFIED_OPEN": {"POLICY_CLEAR", "CLOSED", "REJECTED_POLICY", "VALUE_UNKNOWN"},
    "POLICY_CLEAR": {"PITCH_READY", "CLOSED", "DECLINED", "VALUE_UNKNOWN"},
    "PITCH_READY": {"SUBMITTED", "DECLINED", "EXPIRED"},
    "SUBMITTED": {"ACCEPTED", "DECLINED", "EXPIRED"},
    "ACCEPTED": {"DRAFTING", "DECLINED"},
    "DRAFTING": {"ARTICLE_SUBMITTED", "DECLINED"},
    "ARTICLE_SUBMITTED": {"PUBLISHED", "DECLINED"},
    "PUBLISHED": {"RECEIVED"},
    "RECEIVED": set(),
    "CLOSED": {"DISCOVERED"},
    "REJECTED_POLICY": {"DISCOVERED"},
    "DECLINED": set(),
    "EXPIRED": {"DISCOVERED"},
    "VALUE_UNKNOWN": {"DISCOVERED", "VERIFIED_OPEN"},
}
REQUIRED_EVIDENCE_KIND = {
    "VERIFIED_OPEN": "official",
    "POLICY_CLEAR": "policy",
    "SUBMITTED": "submission",
    "ACCEPTED": "acceptance",
    "ARTICLE_SUBMITTED": "article_submission",
    "PUBLISHED": "publication",
    "RECEIVED": "payment",
    "CLOSED": "official",
    "REJECTED_POLICY": "official",
}
STATE_NEXT_ACTION = {
    "POLICY_CLEAR": "Prepare one claim-bound, nonduplicate pitch from verified evidence.",
    "PITCH_READY": "Submit the active pitch through the verified publisher intake and capture its receipt.",
    "SUBMITTED": "Monitor the publisher response channel and record acceptance or rejection evidence.",
    "ACCEPTED": "Draft the contracted article against the accepted pitch and publisher requirements.",
    "DRAFTING": "Complete and quality-check the contracted article before submission.",
    "ARTICLE_SUBMITTED": "Monitor editorial review and record publication or rejection evidence.",
    "PUBLISHED": "Monitor the verified payout rail until a non-test payment receipt arrives.",
    "RECEIVED": "Reconcile received money, fees, cost, and artifact attribution.",
    "CLOSED": "Do not submit; recheck the official program page on the closed-program cadence.",
    "REJECTED_POLICY": (
        "Do not submit while the official AI-authorship policy is incompatible; "
        "recheck only for a policy change."
    ),
    "VALUE_UNKNOWN": (
        "Clarify missing compensation, payout, and AI-authorship terms from the "
        "publisher before pitching."
    ),
    "DECLINED": "Do not resubmit the same pitch; record the rejection and change the proposal.",
    "EXPIRED": "Do not submit after the deadline; re-enter only from new official evidence.",
}

COMMERCIAL_ENTITY_CONFIG = {
    "application": {
        "table": "opportunity_applications", "id": "application_id",
        "transitions": {
            "SUBMITTED": {"ACCEPTED": "acceptance", "DECLINED": "rejection", "EXPIRED": None},
        },
    },
    "contract": {
        "table": "opportunity_contracts", "id": "contract_id",
        "transitions": {"PUBLISHER_PENDING": {"TERMS_COMPLETE": "acceptance"}},
    },
    "assignment": {
        "table": "opportunity_assignments", "id": "assignment_id",
        "transitions": {
            "READY": {"DRAFTING": None},
            "DRAFTING": {"DELIVERED": "article_submission", "CLOSED": "rejection"},
            "DELIVERED": {"CLOSED": "closure"},
        },
    },
    "delivery": {
        "table": "opportunity_deliveries", "id": "delivery_id",
        "transitions": {
            "SUBMITTED": {"ACCEPTED": "acceptance", "REJECTED": "rejection"},
        },
    },
    "publication": {
        "table": "opportunity_publications", "id": "publication_id",
        "transitions": {"PUBLISHED": {"REMOVED": "closure"}},
    },
}

CONTRACT_TRANSITION_FIELDS = frozenset({
    "rate_amount", "currency", "rights_terms", "exclusivity_terms",
    "ai_disclosure_policy", "delivery_channel", "payout_rail", "payment_trigger",
    "terms_evidence_id", "blocking_terms_json",
})


class TransitionError(ValueError):
    pass


def _normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", " ".join(value.split())).casefold()


def _program_url_identity(value: str) -> tuple[str, str]:
    parsed = urlsplit(value)
    host = parsed.netloc.casefold()
    path = parsed.path.rstrip("/") or "/"
    if host == "blog.appsignal.com" and path in {"/write-for-us", "/write-for-us.html"}:
        path = "/write-for-us"
    return host, path


def _json_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{field} must be a string list")
    return [_text(item, field) for item in value]


def _canonical_url(value: Any, field: str, *, optional: bool = False) -> str | None:
    if optional and (value is None or value == ""):
        return None
    try:
        return canonicalize_url(value, "rss")
    except ValueError as error:
        raise ValueError(f"{field}: {error}") from error


class OpportunityStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS opportunities (
                    opportunity_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL UNIQUE,
                    publisher TEXT NOT NULL,
                    official_program_url TEXT NOT NULL,
                    application_url TEXT,
                    contact_email TEXT,
                    supporting_urls_json TEXT NOT NULL DEFAULT '[]',
                    state TEXT NOT NULL,
                    intake_state TEXT NOT NULL,
                    fee_min REAL,
                    fee_max REAL,
                    currency TEXT,
                    fee_basis TEXT NOT NULL,
                    topics_json TEXT NOT NULL,
                    originality_terms TEXT NOT NULL,
                    exclusivity_terms TEXT NOT NULL,
                    editorial_steps_json TEXT NOT NULL,
                    expected_delay TEXT NOT NULL,
                    payout_rail TEXT NOT NULL,
                    requirements_json TEXT NOT NULL,
                    ai_policy TEXT NOT NULL,
                    fit_evidence TEXT NOT NULL,
                    next_action TEXT NOT NULL,
                    active_pitch_id TEXT,
                    submission_id TEXT,
                    response_recipient TEXT,
                    received_amount REAL,
                    received_currency TEXT,
                    first_observed_at TEXT NOT NULL,
                    last_verified_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS opportunity_evidence (
                    evidence_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id),
                    kind TEXT NOT NULL,
                    url TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    retrieved_sha256 TEXT NOT NULL,
                    excerpt TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    UNIQUE(opportunity_id,kind,url,observed_at,retrieved_sha256)
                );
                CREATE TABLE IF NOT EXISTS opportunity_pitches (
                    pitch_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id),
                    fingerprint TEXT NOT NULL,
                    title TEXT NOT NULL,
                    angle TEXT NOT NULL,
                    claim_id TEXT,
                    claim_url TEXT,
                    claim_sha256 TEXT,
                    reader_job TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(opportunity_id,fingerprint)
                );
                CREATE TABLE IF NOT EXISTS opportunity_transitions (
                    transition_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id),
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    evidence_id TEXT REFERENCES opportunity_evidence(evidence_id),
                    pitch_id TEXT REFERENCES opportunity_pitches(pitch_id),
                    reason TEXT NOT NULL,
                    UNIQUE(opportunity_id,from_state,to_state,observed_at)
                );
                CREATE TABLE IF NOT EXISTS opportunity_inbound_messages (
                    gmail_message_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id),
                    thread_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    retrieved_sha256 TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    evidence_id TEXT REFERENCES opportunity_evidence(evidence_id),
                    observed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS opportunity_applications (
                    application_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id),
                    pitch_id TEXT REFERENCES opportunity_pitches(pitch_id),
                    provider_submission_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_recipient TEXT,
                    submission_evidence_id TEXT NOT NULL REFERENCES opportunity_evidence(evidence_id),
                    submitted_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(opportunity_id,provider_submission_id)
                );
                CREATE TABLE IF NOT EXISTS opportunity_schema_migrations (
                    schema_name TEXT NOT NULL,
                    from_version INTEGER NOT NULL,
                    to_version INTEGER NOT NULL,
                    applied_at TEXT NOT NULL,
                    source_rows INTEGER NOT NULL,
                    migrated_rows INTEGER NOT NULL,
                    receipt_sha256 TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(schema_name,to_version)
                );
                CREATE UNIQUE INDEX IF NOT EXISTS opportunity_applications_parent_key
                    ON opportunity_applications(application_id,opportunity_id);
                CREATE UNIQUE INDEX IF NOT EXISTS opportunity_evidence_parent_key
                    ON opportunity_evidence(evidence_id,opportunity_id);
                CREATE TABLE IF NOT EXISTS opportunity_contracts (
                    contract_id TEXT PRIMARY KEY,
                    application_id TEXT NOT NULL UNIQUE,
                    opportunity_id TEXT NOT NULL,
                    status TEXT NOT NULL
                        CHECK(status IN ('PUBLISHER_PENDING','TERMS_COMPLETE')),
                    rate_amount REAL CHECK(rate_amount IS NULL OR rate_amount > 0),
                    currency TEXT,
                    rights_terms TEXT,
                    exclusivity_terms TEXT,
                    ai_disclosure_policy TEXT,
                    delivery_channel TEXT,
                    payout_rail TEXT,
                    payment_trigger TEXT,
                    terms_evidence_id TEXT,
                    blocking_terms_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(application_id,opportunity_id)
                        REFERENCES opportunity_applications(application_id,opportunity_id),
                    FOREIGN KEY(terms_evidence_id,opportunity_id)
                        REFERENCES opportunity_evidence(evidence_id,opportunity_id),
                    CHECK(
                        status='PUBLISHER_PENDING' OR (
                            rate_amount IS NOT NULL
                            AND typeof(rate_amount) IN ('integer','real')
                            AND rate_amount > 0
                            AND currency IS NOT NULL
                            AND length(currency)=3
                            AND currency=upper(currency)
                            AND currency GLOB '[A-Z][A-Z][A-Z]'
                            AND rights_terms IS NOT NULL
                            AND length(trim(rights_terms)) > 0
                            AND exclusivity_terms IS NOT NULL
                            AND length(trim(exclusivity_terms)) > 0
                            AND ai_disclosure_policy IS NOT NULL
                            AND length(trim(ai_disclosure_policy)) > 0
                            AND delivery_channel IS NOT NULL
                            AND length(trim(delivery_channel)) > 0
                            AND payout_rail IS NOT NULL
                            AND length(trim(payout_rail)) > 0
                            AND payment_trigger IS NOT NULL
                            AND length(trim(payment_trigger)) > 0
                            AND terms_evidence_id IS NOT NULL
                            AND blocking_terms_json='[]'
                        )
                    )
                );
                CREATE TRIGGER IF NOT EXISTS opportunity_contracts_json_insert
                BEFORE INSERT ON opportunity_contracts
                WHEN NOT json_valid(NEW.blocking_terms_json)
                     OR json_type(NEW.blocking_terms_json) != 'array'
                BEGIN
                    SELECT RAISE(ABORT,'contract blocking terms must be a JSON array');
                END;
                CREATE TRIGGER IF NOT EXISTS opportunity_contracts_json_update
                BEFORE UPDATE ON opportunity_contracts
                WHEN NOT json_valid(NEW.blocking_terms_json)
                     OR json_type(NEW.blocking_terms_json) != 'array'
                BEGIN
                    SELECT RAISE(ABORT,'contract blocking terms must be a JSON array');
                END;
                CREATE TRIGGER IF NOT EXISTS opportunity_contracts_terms_insert
                BEFORE INSERT ON opportunity_contracts
                WHEN json_valid(NEW.blocking_terms_json) AND NOT (
                    NOT EXISTS (
                        SELECT 1 FROM json_each(NEW.blocking_terms_json)
                        WHERE type != 'text' OR value NOT IN (
                            'rate_amount','currency','rights_terms','exclusivity_terms',
                            'ai_disclosure_policy','delivery_channel','payout_rail',
                            'payment_trigger','terms_evidence_id'
                        )
                    )
                    AND (SELECT COUNT(*) FROM json_each(NEW.blocking_terms_json)) =
                        (SELECT COUNT(DISTINCT value) FROM json_each(NEW.blocking_terms_json))
                    AND ((NEW.rate_amount IS NULL OR typeof(NEW.rate_amount) NOT IN ('integer','real')
                          OR NEW.rate_amount <= 0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='rate_amount'))
                    AND ((NEW.currency IS NULL OR length(NEW.currency) != 3
                          OR NEW.currency != upper(NEW.currency)
                          OR NEW.currency NOT GLOB '[A-Z][A-Z][A-Z]') = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='currency'))
                    AND ((NEW.rights_terms IS NULL OR length(trim(NEW.rights_terms))=0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='rights_terms'))
                    AND ((NEW.exclusivity_terms IS NULL OR length(trim(NEW.exclusivity_terms))=0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='exclusivity_terms'))
                    AND ((NEW.ai_disclosure_policy IS NULL OR length(trim(NEW.ai_disclosure_policy))=0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='ai_disclosure_policy'))
                    AND ((NEW.delivery_channel IS NULL OR length(trim(NEW.delivery_channel))=0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='delivery_channel'))
                    AND ((NEW.payout_rail IS NULL OR length(trim(NEW.payout_rail))=0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='payout_rail'))
                    AND ((NEW.payment_trigger IS NULL OR length(trim(NEW.payment_trigger))=0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='payment_trigger'))
                    AND ((NEW.terms_evidence_id IS NULL) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='terms_evidence_id'))
                    AND ((NEW.status='PUBLISHER_PENDING' AND json_array_length(NEW.blocking_terms_json)>0)
                         OR (NEW.status='TERMS_COMPLETE' AND json_array_length(NEW.blocking_terms_json)=0))
                )
                BEGIN
                    SELECT RAISE(ABORT,'contract blocking terms do not match missing terms');
                END;
                CREATE TRIGGER IF NOT EXISTS opportunity_contracts_terms_update
                BEFORE UPDATE ON opportunity_contracts
                WHEN json_valid(NEW.blocking_terms_json) AND NOT (
                    NOT EXISTS (
                        SELECT 1 FROM json_each(NEW.blocking_terms_json)
                        WHERE type != 'text' OR value NOT IN (
                            'rate_amount','currency','rights_terms','exclusivity_terms',
                            'ai_disclosure_policy','delivery_channel','payout_rail',
                            'payment_trigger','terms_evidence_id'
                        )
                    )
                    AND (SELECT COUNT(*) FROM json_each(NEW.blocking_terms_json)) =
                        (SELECT COUNT(DISTINCT value) FROM json_each(NEW.blocking_terms_json))
                    AND ((NEW.rate_amount IS NULL OR typeof(NEW.rate_amount) NOT IN ('integer','real')
                          OR NEW.rate_amount <= 0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='rate_amount'))
                    AND ((NEW.currency IS NULL OR length(NEW.currency) != 3
                          OR NEW.currency != upper(NEW.currency)
                          OR NEW.currency NOT GLOB '[A-Z][A-Z][A-Z]') = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='currency'))
                    AND ((NEW.rights_terms IS NULL OR length(trim(NEW.rights_terms))=0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='rights_terms'))
                    AND ((NEW.exclusivity_terms IS NULL OR length(trim(NEW.exclusivity_terms))=0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='exclusivity_terms'))
                    AND ((NEW.ai_disclosure_policy IS NULL OR length(trim(NEW.ai_disclosure_policy))=0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='ai_disclosure_policy'))
                    AND ((NEW.delivery_channel IS NULL OR length(trim(NEW.delivery_channel))=0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='delivery_channel'))
                    AND ((NEW.payout_rail IS NULL OR length(trim(NEW.payout_rail))=0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='payout_rail'))
                    AND ((NEW.payment_trigger IS NULL OR length(trim(NEW.payment_trigger))=0) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='payment_trigger'))
                    AND ((NEW.terms_evidence_id IS NULL) = EXISTS(
                        SELECT 1 FROM json_each(NEW.blocking_terms_json) WHERE value='terms_evidence_id'))
                    AND ((NEW.status='PUBLISHER_PENDING' AND json_array_length(NEW.blocking_terms_json)>0)
                         OR (NEW.status='TERMS_COMPLETE' AND json_array_length(NEW.blocking_terms_json)=0))
                )
                BEGIN
                    SELECT RAISE(ABORT,'contract blocking terms do not match missing terms');
                END;
                CREATE UNIQUE INDEX IF NOT EXISTS opportunity_contracts_assignment_parent_key
                    ON opportunity_contracts(contract_id,status,opportunity_id);
                CREATE UNIQUE INDEX IF NOT EXISTS opportunity_pitches_assignment_parent_key
                    ON opportunity_pitches(pitch_id,opportunity_id);
                CREATE UNIQUE INDEX IF NOT EXISTS opportunity_evidence_assignment_parent_key
                    ON opportunity_evidence(evidence_id,opportunity_id,kind);
                CREATE TABLE IF NOT EXISTS opportunity_assignments (
                    assignment_id TEXT NOT NULL PRIMARY KEY,
                    contract_id TEXT NOT NULL,
                    contract_status TEXT NOT NULL CHECK(contract_status='TERMS_COMPLETE'),
                    opportunity_id TEXT NOT NULL,
                    pitch_id TEXT NOT NULL,
                    topic TEXT NOT NULL CHECK(length(trim(topic)) > 0),
                    approved_outline_json TEXT NOT NULL
                        CHECK(json_valid(approved_outline_json)
                              AND json_type(approved_outline_json)='array'
                              AND json_array_length(approved_outline_json) > 0),
                    format_requirements TEXT NOT NULL
                        CHECK(length(trim(format_requirements)) > 0),
                    language TEXT NOT NULL CHECK(length(trim(language)) > 0),
                    deadline_at TEXT CHECK(deadline_at IS NULL OR length(trim(deadline_at)) > 0),
                    assignment_evidence_id TEXT NOT NULL,
                    assignment_evidence_kind TEXT NOT NULL
                        CHECK(assignment_evidence_kind='acceptance'),
                    status TEXT NOT NULL
                        CHECK(status IN ('READY','DRAFTING','DELIVERED','CLOSED')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(contract_id,contract_status,opportunity_id)
                        REFERENCES opportunity_contracts(contract_id,status,opportunity_id),
                    FOREIGN KEY(pitch_id,opportunity_id)
                        REFERENCES opportunity_pitches(pitch_id,opportunity_id),
                    FOREIGN KEY(assignment_evidence_id,opportunity_id,assignment_evidence_kind)
                        REFERENCES opportunity_evidence(evidence_id,opportunity_id,kind),
                    UNIQUE(pitch_id),
                    UNIQUE(assignment_evidence_id)
                );
                CREATE TRIGGER IF NOT EXISTS opportunity_assignments_outline_insert
                BEFORE INSERT ON opportunity_assignments
                WHEN json_valid(NEW.approved_outline_json) AND EXISTS (
                    SELECT 1 FROM json_each(NEW.approved_outline_json)
                    WHERE type != 'text' OR length(trim(value))=0
                )
                BEGIN
                    SELECT RAISE(ABORT,'assignment outline items must be nonempty text');
                END;
                CREATE TRIGGER IF NOT EXISTS opportunity_assignments_outline_update
                BEFORE UPDATE ON opportunity_assignments
                WHEN json_valid(NEW.approved_outline_json) AND EXISTS (
                    SELECT 1 FROM json_each(NEW.approved_outline_json)
                    WHERE type != 'text' OR length(trim(value))=0
                )
                BEGIN
                    SELECT RAISE(ABORT,'assignment outline items must be nonempty text');
                END;
                CREATE UNIQUE INDEX IF NOT EXISTS opportunity_assignments_delivery_parent_key
                    ON opportunity_assignments(assignment_id,opportunity_id);
                CREATE TABLE IF NOT EXISTS opportunity_deliveries (
                    delivery_id TEXT NOT NULL PRIMARY KEY,
                    assignment_id TEXT NOT NULL,
                    opportunity_id TEXT NOT NULL,
                    revision_number INTEGER NOT NULL
                        CHECK(typeof(revision_number)='integer' AND revision_number > 0),
                    artifact_uri TEXT NOT NULL CHECK(length(trim(artifact_uri)) > 0),
                    artifact_sha256 TEXT NOT NULL
                        CHECK(typeof(artifact_sha256)='text'
                              AND length(artifact_sha256)=64
                              AND artifact_sha256 NOT GLOB '*[^0-9a-f]*'),
                    delivery_channel TEXT NOT NULL CHECK(length(trim(delivery_channel)) > 0),
                    provider_delivery_id TEXT NOT NULL
                        CHECK(length(trim(provider_delivery_id)) > 0),
                    delivery_evidence_id TEXT NOT NULL,
                    delivery_evidence_kind TEXT NOT NULL
                        CHECK(delivery_evidence_kind='article_submission'),
                    delivered_at TEXT NOT NULL,
                    status TEXT NOT NULL
                        CHECK(status IN ('SUBMITTED','ACCEPTED','REJECTED')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(assignment_id,opportunity_id)
                        REFERENCES opportunity_assignments(assignment_id,opportunity_id),
                    FOREIGN KEY(delivery_evidence_id,opportunity_id,delivery_evidence_kind)
                        REFERENCES opportunity_evidence(evidence_id,opportunity_id,kind),
                    UNIQUE(assignment_id,revision_number),
                    UNIQUE(assignment_id,artifact_sha256),
                    UNIQUE(opportunity_id,provider_delivery_id),
                    UNIQUE(delivery_evidence_id)
                );
                CREATE TRIGGER IF NOT EXISTS opportunity_deliveries_receipt_insert
                BEFORE INSERT ON opportunity_deliveries
                WHEN NOT EXISTS (
                    SELECT 1 FROM opportunity_evidence e
                    WHERE e.evidence_id=NEW.delivery_evidence_id
                      AND e.opportunity_id=NEW.opportunity_id
                      AND e.kind=NEW.delivery_evidence_kind
                      AND json_valid(e.payload_json)
                      AND typeof(json_extract(e.payload_json,'$.revision_number'))='integer'
                      AND json_extract(e.payload_json,'$.revision_number')=NEW.revision_number
                      AND json_extract(e.payload_json,'$.artifact_sha256')=NEW.artifact_sha256
                      AND json_extract(e.payload_json,'$.provider_delivery_id')=NEW.provider_delivery_id
                )
                BEGIN
                    SELECT RAISE(ABORT,'delivery receipt does not bind exact delivery');
                END;
                CREATE TRIGGER IF NOT EXISTS opportunity_deliveries_receipt_update
                BEFORE UPDATE ON opportunity_deliveries
                WHEN NOT EXISTS (
                    SELECT 1 FROM opportunity_evidence e
                    WHERE e.evidence_id=NEW.delivery_evidence_id
                      AND e.opportunity_id=NEW.opportunity_id
                      AND e.kind=NEW.delivery_evidence_kind
                      AND json_valid(e.payload_json)
                      AND typeof(json_extract(e.payload_json,'$.revision_number'))='integer'
                      AND json_extract(e.payload_json,'$.revision_number')=NEW.revision_number
                      AND json_extract(e.payload_json,'$.artifact_sha256')=NEW.artifact_sha256
                      AND json_extract(e.payload_json,'$.provider_delivery_id')=NEW.provider_delivery_id
                )
                BEGIN
                    SELECT RAISE(ABORT,'delivery receipt does not bind exact delivery');
                END;
                CREATE UNIQUE INDEX IF NOT EXISTS opportunity_deliveries_publication_parent_key
                    ON opportunity_deliveries(delivery_id,opportunity_id,artifact_sha256);
                CREATE TABLE IF NOT EXISTS opportunity_publications (
                    publication_id TEXT NOT NULL PRIMARY KEY,
                    delivery_id TEXT NOT NULL UNIQUE,
                    opportunity_id TEXT NOT NULL,
                    artifact_sha256 TEXT NOT NULL
                        CHECK(typeof(artifact_sha256)='text'
                              AND length(artifact_sha256)=64
                              AND artifact_sha256 NOT GLOB '*[^0-9a-f]*'),
                    public_url TEXT NOT NULL
                        CHECK(typeof(public_url)='text'
                              AND substr(public_url,1,8)='https://'
                              AND instr(public_url,' ')=0
                              AND instr(public_url,char(9))=0
                              AND instr(public_url,char(10))=0
                              AND instr(public_url,char(11))=0
                              AND instr(public_url,char(12))=0
                              AND instr(public_url,char(13))=0
                              AND length(CASE
                                  WHEN instr(substr(public_url,9),'/')=0 THEN substr(public_url,9)
                                  ELSE substr(public_url,9,instr(substr(public_url,9),'/')-1)
                              END) > 0
                              AND CASE
                                  WHEN instr(substr(public_url,9),'/')=0 THEN substr(public_url,9)
                                  ELSE substr(public_url,9,instr(substr(public_url,9),'/')-1)
                              END GLOB '*.*'
                              AND CASE
                                  WHEN instr(substr(public_url,9),'/')=0 THEN substr(public_url,9)
                                  ELSE substr(public_url,9,instr(substr(public_url,9),'/')-1)
                              END NOT GLOB '*[^A-Za-z0-9.-]*'
                              AND substr(CASE
                                  WHEN instr(substr(public_url,9),'/')=0 THEN substr(public_url,9)
                                  ELSE substr(public_url,9,instr(substr(public_url,9),'/')-1)
                              END,1,1) GLOB '[A-Za-z0-9]'
                              AND substr(CASE
                                  WHEN instr(substr(public_url,9),'/')=0 THEN substr(public_url,9)
                                  ELSE substr(public_url,9,instr(substr(public_url,9),'/')-1)
                              END,-1,1) GLOB '[A-Za-z0-9]'
                              AND instr(CASE
                                  WHEN instr(substr(public_url,9),'/')=0 THEN substr(public_url,9)
                                  ELSE substr(public_url,9,instr(substr(public_url,9),'/')-1)
                              END,'..')=0
                              AND instr(CASE
                                  WHEN instr(substr(public_url,9),'/')=0 THEN substr(public_url,9)
                                  ELSE substr(public_url,9,instr(substr(public_url,9),'/')-1)
                              END,'.-')=0
                              AND instr(CASE
                                  WHEN instr(substr(public_url,9),'/')=0 THEN substr(public_url,9)
                                  ELSE substr(public_url,9,instr(substr(public_url,9),'/')-1)
                              END,'-.')=0),
                    readback_sha256 TEXT NOT NULL
                        CHECK(typeof(readback_sha256)='text'
                              AND length(readback_sha256)=64
                              AND readback_sha256 NOT GLOB '*[^0-9a-f]*'),
                    publication_evidence_id TEXT NOT NULL UNIQUE,
                    publication_evidence_kind TEXT NOT NULL
                        CHECK(publication_evidence_kind='publication'),
                    published_at TEXT NOT NULL
                        CHECK(typeof(published_at)='text'
                              AND published_at GLOB '????-??-??T??:??:??*'
                              AND datetime(published_at) IS NOT NULL
                              AND (substr(published_at,-1)='Z'
                                   OR substr(published_at,-6) GLOB
                                      '[+-][0-9][0-9]:[0-9][0-9]')),
                    status TEXT NOT NULL CHECK(status IN ('PUBLISHED','REMOVED')),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(delivery_id,opportunity_id,artifact_sha256)
                        REFERENCES opportunity_deliveries(delivery_id,opportunity_id,artifact_sha256),
                    FOREIGN KEY(publication_evidence_id,opportunity_id,publication_evidence_kind)
                        REFERENCES opportunity_evidence(evidence_id,opportunity_id,kind),
                    UNIQUE(public_url)
                );
                CREATE TRIGGER IF NOT EXISTS opportunity_publications_receipt_insert
                BEFORE INSERT ON opportunity_publications
                WHEN NOT EXISTS (
                    SELECT 1 FROM opportunity_evidence e
                    WHERE e.evidence_id=NEW.publication_evidence_id
                      AND e.opportunity_id=NEW.opportunity_id
                      AND e.kind=NEW.publication_evidence_kind
                      AND e.url=NEW.public_url
                      AND e.retrieved_sha256=NEW.readback_sha256
                      AND json_valid(e.payload_json)
                      AND json_extract(e.payload_json,'$.delivery_id')=NEW.delivery_id
                      AND json_extract(e.payload_json,'$.artifact_sha256')=NEW.artifact_sha256
                      AND json_extract(e.payload_json,'$.public_url')=NEW.public_url
                      AND json_extract(e.payload_json,'$.readback_sha256')=NEW.readback_sha256
                      AND json_extract(e.payload_json,'$.published_at')=NEW.published_at
                )
                BEGIN
                    SELECT RAISE(ABORT,'publication receipt does not bind exact public readback');
                END;
                CREATE TRIGGER IF NOT EXISTS opportunity_publications_receipt_update
                BEFORE UPDATE ON opportunity_publications
                WHEN NOT EXISTS (
                    SELECT 1 FROM opportunity_evidence e
                    WHERE e.evidence_id=NEW.publication_evidence_id
                      AND e.opportunity_id=NEW.opportunity_id
                      AND e.kind=NEW.publication_evidence_kind
                      AND e.url=NEW.public_url
                      AND e.retrieved_sha256=NEW.readback_sha256
                      AND json_valid(e.payload_json)
                      AND json_extract(e.payload_json,'$.delivery_id')=NEW.delivery_id
                      AND json_extract(e.payload_json,'$.artifact_sha256')=NEW.artifact_sha256
                      AND json_extract(e.payload_json,'$.public_url')=NEW.public_url
                      AND json_extract(e.payload_json,'$.readback_sha256')=NEW.readback_sha256
                      AND json_extract(e.payload_json,'$.published_at')=NEW.published_at
                )
                BEGIN
                    SELECT RAISE(ABORT,'publication receipt does not bind exact public readback');
                END;
                CREATE TABLE IF NOT EXISTS opportunity_commercial_transitions (
                    transition_id TEXT NOT NULL PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    opportunity_id TEXT NOT NULL REFERENCES opportunities(opportunity_id),
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    evidence_id TEXT REFERENCES opportunity_evidence(evidence_id),
                    observed_at TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    UNIQUE(entity_type,entity_id,from_state,to_state,observed_at)
                );
                """
            )
            pitch_columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(opportunity_pitches)")
            }
            for name in ("claim_id", "claim_url", "claim_sha256", "reader_job"):
                if name not in pitch_columns:
                    connection.execute(f"ALTER TABLE opportunity_pitches ADD COLUMN {name} TEXT")
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS opportunity_pitches_claim_once "
                "ON opportunity_pitches(claim_id) WHERE claim_id IS NOT NULL"
            )
            opportunity_columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(opportunities)")
            }
            if "contact_email" not in opportunity_columns:
                connection.execute("ALTER TABLE opportunities ADD COLUMN contact_email TEXT")
            if "supporting_urls_json" not in opportunity_columns:
                connection.execute(
                    "ALTER TABLE opportunities ADD COLUMN supporting_urls_json "
                    "TEXT NOT NULL DEFAULT '[]'"
                )
            if "response_recipient" not in opportunity_columns:
                connection.execute(
                    "ALTER TABLE opportunities ADD COLUMN response_recipient TEXT"
                )
            connection.execute(
                "UPDATE opportunities SET application_url=NULL "
                "WHERE application_url=official_program_url"
            )
            self._migrate_intake_v1_in_connection(connection)

    def _migrate_intake_v1_in_connection(self, connection: sqlite3.Connection) -> None:
        if connection.execute(
            "SELECT 1 FROM opportunity_schema_migrations "
            "WHERE schema_name='opportunity_intake' AND to_version=1"
        ).fetchone() is not None:
            return
        source_rows = connection.execute(
            "SELECT opportunity_id,submission_id,response_recipient FROM opportunities "
            "WHERE submission_id IS NOT NULL ORDER BY opportunity_id"
        ).fetchall()
        application_ids: list[str] = []
        for row in source_rows:
            transition = connection.execute(
                "SELECT t.pitch_id,t.evidence_id,t.observed_at,e.payload_json "
                "FROM opportunity_transitions t JOIN opportunity_evidence e "
                "ON e.evidence_id=t.evidence_id AND e.opportunity_id=t.opportunity_id "
                "AND e.kind='submission' WHERE t.opportunity_id=? AND t.to_state='SUBMITTED' "
                "ORDER BY t.observed_at DESC,t.transition_id DESC LIMIT 1",
                (row["opportunity_id"],),
            ).fetchone()
            if transition is None or not transition["pitch_id"]:
                raise TransitionError("legacy submission evidence is incomplete")
            if connection.execute(
                "SELECT 1 FROM opportunity_pitches WHERE pitch_id=? AND opportunity_id=?",
                (transition["pitch_id"], row["opportunity_id"]),
            ).fetchone() is None:
                raise TransitionError("legacy submission pitch belongs to another opportunity")
            try:
                evidence_payload = json.loads(transition["payload_json"])
            except (TypeError, json.JSONDecodeError) as error:
                raise TransitionError("legacy submission evidence payload is invalid") from error
            provider_submission_id = str(row["submission_id"])
            if not provider_submission_id.strip():
                raise TransitionError("legacy submission ID is empty")
            if evidence_payload.get("submission_id") != provider_submission_id:
                raise TransitionError("legacy submission evidence ID does not match")
            application_id = self._record_application_in_connection(
                connection, opportunity_id=str(row["opportunity_id"]),
                pitch_id=str(transition["pitch_id"]),
                provider_submission_id=provider_submission_id,
                response_recipient=row["response_recipient"],
                submission_evidence_id=str(transition["evidence_id"]),
                submitted_at=str(transition["observed_at"]),
                updated_at=str(transition["observed_at"]),
            )
            application_ids.append(application_id)
        application_ids.sort()
        payload_json = json.dumps(
            {"application_ids": application_ids}, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        )
        source_count = len(source_rows)
        migrated_count = len(application_ids)
        receipt_sha256 = hashlib.sha256(
            f"opportunity_intake\n0\n1\n{source_count}\n{migrated_count}\n{payload_json}".encode("utf-8")
        ).hexdigest()
        applied_at = str(
            connection.execute(
                "SELECT COALESCE(MAX(updated_at),'1970-01-01T00:00:00Z') FROM opportunities"
            ).fetchone()[0]
        )
        connection.execute(
            "INSERT INTO opportunity_schema_migrations(schema_name,from_version,to_version,"
            "applied_at,source_rows,migrated_rows,receipt_sha256,payload_json) "
            "VALUES('opportunity_intake',0,1,?,?,?,?,?)",
            (applied_at, source_count, migrated_count, receipt_sha256, payload_json),
        )

    def _record_application_in_connection(
        self, connection: sqlite3.Connection, *, opportunity_id: str, pitch_id: str,
        provider_submission_id: str, response_recipient: str | None,
        submission_evidence_id: str, submitted_at: str, updated_at: str,
    ) -> str:
        application_id = "app_" + hashlib.sha256(
            f"{opportunity_id}\n{provider_submission_id}".encode("utf-8")
        ).hexdigest()[:24]
        connection.execute(
            "INSERT OR IGNORE INTO opportunity_applications(application_id,opportunity_id,"
            "pitch_id,provider_submission_id,status,response_recipient,submission_evidence_id,"
            "submitted_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                application_id, opportunity_id, pitch_id, provider_submission_id, "SUBMITTED",
                response_recipient, submission_evidence_id, submitted_at, submitted_at, updated_at,
            ),
        )
        application = connection.execute(
            "SELECT opportunity_id,pitch_id,provider_submission_id,submission_evidence_id,"
            "submitted_at FROM opportunity_applications WHERE application_id=?",
            (application_id,),
        ).fetchone()
        expected = (
            opportunity_id, pitch_id, provider_submission_id, submission_evidence_id, submitted_at,
        )
        if application is None or tuple(application) != expected:
            raise TransitionError("application receipt conflicts with durable submission")
        connection.execute(
            "UPDATE opportunity_applications SET response_recipient=COALESCE(response_recipient,?),"
            "updated_at=? WHERE application_id=?",
            (response_recipient, updated_at, application_id),
        )
        return application_id

    def discover(self, candidate: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(candidate, dict):
            raise ValueError("opportunity must be an object")
        publisher = _text(candidate.get("publisher"), "publisher")
        official_url = str(_canonical_url(candidate.get("official_program_url"), "official_program_url"))
        application_url = _canonical_url(candidate.get("application_url"), "application_url", optional=True)
        if application_url == official_url:
            application_url = None
        contact_email = candidate.get("contact_email")
        if contact_email in (None, ""):
            contact_email = None
        else:
            contact_email = _text(contact_email, "contact_email").lower()
            if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contact_email) is None:
                raise ValueError("contact_email must be an email address")
        supporting_urls = candidate.get("supporting_urls", [])
        if not isinstance(supporting_urls, list) or len(supporting_urls) > 4:
            raise ValueError("supporting_urls must be a list of at most four URLs")
        supporting_urls = [
            str(_canonical_url(url, "supporting_url")) for url in supporting_urls
        ]
        if official_url in supporting_urls or len(set(supporting_urls)) != len(supporting_urls):
            raise ValueError("supporting_urls must be unique and differ from official_program_url")
        intake_state = _text(candidate.get("intake_state"), "intake_state").upper()
        if intake_state not in INTAKE_STATES:
            raise ValueError("intake_state is invalid")
        fee_basis = _text(candidate.get("fee_basis"), "fee_basis").lower()
        if fee_basis not in FEE_BASES:
            raise ValueError("fee_basis is invalid")
        fee_min = candidate.get("fee_min")
        fee_max = candidate.get("fee_max")
        if fee_min is not None and (not isinstance(fee_min, (int, float)) or isinstance(fee_min, bool) or fee_min < 0):
            raise ValueError("fee_min must be a nonnegative number or null")
        if fee_max is not None and (not isinstance(fee_max, (int, float)) or isinstance(fee_max, bool) or fee_max < 0):
            raise ValueError("fee_max must be a nonnegative number or null")
        if fee_min is not None and fee_max is not None and fee_min > fee_max:
            raise ValueError("fee_min cannot exceed fee_max")
        currency = candidate.get("currency")
        if fee_min is not None or fee_max is not None:
            currency = _text(currency, "currency").upper()
            if re.fullmatch(r"[A-Z]{3}", currency) is None:
                raise ValueError("currency must be a three-letter code")
        elif currency not in (None, ""):
            currency = _text(currency, "currency").upper()
        else:
            currency = None
        topics = _json_list(candidate.get("topics"), "topics")
        steps = _json_list(candidate.get("editorial_steps"), "editorial_steps")
        requirements = candidate.get("requirements")
        required_requirement_keys = {"account", "kyc", "tax", "contract", "geography"}
        if not isinstance(requirements, dict) or set(requirements) != required_requirement_keys:
            raise ValueError("requirements fields are invalid")
        requirements = {key: _text(value, f"requirements.{key}") for key, value in requirements.items()}
        ai_policy = _text(candidate.get("ai_policy"), "ai_policy").upper()
        if ai_policy not in AI_POLICIES:
            raise ValueError("ai_policy is invalid")
        observed_at = str(_timestamp(candidate.get("observed_at"), "observed_at"))
        retrieved_sha256 = _text(candidate.get("retrieved_sha256"), "retrieved_sha256").lower()
        if SHA256_RE.fullmatch(retrieved_sha256) is None:
            raise ValueError("retrieved_sha256 must be a SHA-256 digest")
        evidence_excerpt = _text(candidate.get("evidence_excerpt"), "evidence_excerpt")
        fields = {
            "originality_terms": _text(candidate.get("originality_terms"), "originality_terms"),
            "exclusivity_terms": _text(candidate.get("exclusivity_terms"), "exclusivity_terms"),
            "expected_delay": _text(candidate.get("expected_delay"), "expected_delay"),
            "payout_rail": _text(candidate.get("payout_rail"), "payout_rail"),
            "fit_evidence": _text(candidate.get("fit_evidence"), "fit_evidence"),
            "next_action": _text(candidate.get("next_action"), "next_action"),
        }
        fingerprint = hashlib.sha256(
            f"{_normalized(publisher)}\n{official_url}".encode("utf-8")
        ).hexdigest()
        opportunity_id = f"opp_{fingerprint[:24]}"
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            alias = next(
                (
                    row for row in connection.execute(
                        "SELECT opportunity_id,fingerprint,publisher,official_program_url "
                        "FROM opportunities ORDER BY "
                        "CASE WHEN submission_id IS NOT NULL THEN 0 "
                        "WHEN state IN ('SUBMITTED','ACCEPTED','DRAFTING','ARTICLE_SUBMITTED',"
                        "'PUBLISHED','RECEIVED') THEN 1 ELSE 2 END,"
                        "first_observed_at,opportunity_id"
                    )
                    if _normalized(str(row["publisher"])) == _normalized(publisher)
                    and _program_url_identity(str(row["official_program_url"]))
                    == _program_url_identity(official_url)
                ),
                None,
            )
            if alias is not None:
                fingerprint = str(alias["fingerprint"])
                opportunity_id = str(alias["opportunity_id"])
            inserted = connection.execute(
                """
                INSERT OR IGNORE INTO opportunities(
                    opportunity_id,fingerprint,publisher,official_program_url,application_url,contact_email,
                    supporting_urls_json,
                    state,intake_state,fee_min,fee_max,currency,fee_basis,topics_json,
                    originality_terms,exclusivity_terms,editorial_steps_json,expected_delay,
                    payout_rail,requirements_json,ai_policy,fit_evidence,next_action,
                    first_observed_at,last_verified_at,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,'DISCOVERED',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    opportunity_id, fingerprint, publisher, official_url, application_url, contact_email,
                    json.dumps(supporting_urls, ensure_ascii=False),
                    intake_state, fee_min, fee_max, currency, fee_basis,
                    json.dumps(topics, ensure_ascii=False), fields["originality_terms"],
                    fields["exclusivity_terms"], json.dumps(steps, ensure_ascii=False),
                    fields["expected_delay"], fields["payout_rail"],
                    json.dumps(requirements, ensure_ascii=False, sort_keys=True), ai_policy,
                    fields["fit_evidence"], fields["next_action"], observed_at,
                    observed_at, observed_at, observed_at,
                ),
            ).rowcount == 1
            row = connection.execute(
                "SELECT opportunity_id FROM opportunities WHERE fingerprint=?", (fingerprint,)
            ).fetchone()
            if row is None:
                raise RuntimeError("opportunity insert did not produce a row")
            durable_id = str(row["opportunity_id"])
            evidence_id = self._record_evidence_in_connection(
                connection, durable_id, kind="official", url=official_url,
                observed_at=observed_at, retrieved_sha256=retrieved_sha256,
                excerpt=evidence_excerpt, payload=candidate,
            )
            connection.execute(
                "UPDATE opportunities SET application_url=?,contact_email=?,supporting_urls_json=?,"
                "intake_state=?,fee_min=?,fee_max=?,"
                "currency=?,fee_basis=?,topics_json=?,originality_terms=?,exclusivity_terms=?,"
                "editorial_steps_json=?,expected_delay=?,payout_rail=?,requirements_json=?,"
                "ai_policy=?,fit_evidence=?,"
                "next_action=CASE WHEN state IN ('DISCOVERED','VERIFIED_OPEN','POLICY_CLEAR',"
                "'CLOSED','REJECTED_POLICY','VALUE_UNKNOWN') THEN ? ELSE next_action END,"
                "last_verified_at=?,updated_at=? "
                "WHERE opportunity_id=? AND last_verified_at<=?",
                (
                    application_url, contact_email, json.dumps(supporting_urls, ensure_ascii=False),
                    intake_state, fee_min, fee_max, currency, fee_basis,
                    json.dumps(topics, ensure_ascii=False), fields["originality_terms"],
                    fields["exclusivity_terms"], json.dumps(steps, ensure_ascii=False),
                    fields["expected_delay"], fields["payout_rail"],
                    json.dumps(requirements, ensure_ascii=False, sort_keys=True), ai_policy,
                    fields["fit_evidence"], fields["next_action"], observed_at, observed_at,
                    durable_id, observed_at,
                ),
            )
        return {"opportunity_id": durable_id, "inserted": inserted}

    def _record_evidence_in_connection(
        self, connection: sqlite3.Connection, opportunity_id: str, *, kind: str,
        url: str, observed_at: str, retrieved_sha256: str, excerpt: str,
        payload: dict[str, Any],
    ) -> str:
        identity = f"{opportunity_id}\n{kind}\n{url}\n{observed_at}\n{retrieved_sha256}"
        evidence_id = f"ev_{hashlib.sha256(identity.encode()).hexdigest()[:24]}"
        connection.execute(
            "INSERT OR IGNORE INTO opportunity_evidence(evidence_id,opportunity_id,kind,url,"
            "observed_at,retrieved_sha256,excerpt,payload_json) VALUES(?,?,?,?,?,?,?,?)",
            (
                evidence_id, opportunity_id, kind, url, observed_at, retrieved_sha256,
                excerpt, json.dumps(payload, ensure_ascii=False, sort_keys=True),
            ),
        )
        return evidence_id

    def record_evidence(
        self, opportunity_id: str, *, kind: str, url: str, observed_at: str,
        retrieved_sha256: str, excerpt: str, payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if kind not in EVIDENCE_KINDS:
            raise ValueError("evidence kind is invalid")
        canonical_url = str(_canonical_url(url, "evidence.url"))
        observed_at = str(_timestamp(observed_at, "observed_at"))
        retrieved_sha256 = _text(retrieved_sha256, "retrieved_sha256").lower()
        if SHA256_RE.fullmatch(retrieved_sha256) is None:
            raise ValueError("retrieved_sha256 must be a SHA-256 digest")
        excerpt = _text(excerpt, "excerpt")
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError("evidence payload must be an object")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute(
                "SELECT 1 FROM opportunities WHERE opportunity_id=?", (opportunity_id,)
            ).fetchone() is None:
                raise KeyError(opportunity_id)
            evidence_id = self._record_evidence_in_connection(
                connection, opportunity_id, kind=kind, url=canonical_url,
                observed_at=observed_at, retrieved_sha256=retrieved_sha256,
                excerpt=excerpt, payload=payload,
            )
        return {"evidence_id": evidence_id}

    def recover_submission(
        self, opportunity_id: str, *, title: str, angle: str, submitted_at: str,
        recovered_at: str, response_recipient: str, evidence_id: str, reason: str,
    ) -> dict[str, Any]:
        """Import a pre-ledger submission from an exact external confirmation.

        This is deliberately separate from ``advance``: it records what already
        happened without pretending the current policy/rate gate was passed.
        New submissions must still follow the normal POLICY_CLEAR -> PITCH_READY
        path.
        """
        title = _text(title, "title")
        angle = _text(angle, "angle")
        submitted_at = str(_timestamp(submitted_at, "submitted_at"))
        recovered_at = str(_timestamp(recovered_at, "recovered_at"))
        response_recipient = _text(response_recipient, "response_recipient").lower()
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", response_recipient) is None:
            raise ValueError("response_recipient must be an email address")
        evidence_id = _text(evidence_id, "evidence_id")
        reason = _text(reason, "reason")
        fingerprint = hashlib.sha256(
            f"{_normalized(title)}\n{_normalized(angle)}".encode("utf-8")
        ).hexdigest()
        pitch_identity = hashlib.sha256(
            f"{opportunity_id}\n{fingerprint}".encode("utf-8")
        ).hexdigest()
        pitch_id = f"pitch_{pitch_identity[:24]}"

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT * FROM opportunities WHERE opportunity_id=?", (opportunity_id,)
            ).fetchone()
            if current is None:
                raise KeyError(opportunity_id)
            evidence = connection.execute(
                "SELECT * FROM opportunity_evidence WHERE evidence_id=? AND opportunity_id=?",
                (evidence_id, opportunity_id),
            ).fetchone()
            if evidence is None or evidence["kind"] != "submission":
                raise TransitionError("recovery requires matching submission evidence")
            if str(evidence["observed_at"]) != submitted_at:
                raise TransitionError("submission time does not match confirmation evidence")
            try:
                payload = json.loads(evidence["payload_json"])
            except (TypeError, json.JSONDecodeError) as error:
                raise TransitionError("submission evidence payload is invalid") from error
            submission_id = payload.get("submission_id")
            confirmation_sha256 = payload.get("confirmation_sha256")
            source_session_sha256 = payload.get("source_session_sha256")
            if payload.get("historical_recovery") is not True:
                raise TransitionError("submission evidence is not marked for historical recovery")
            if (
                not isinstance(confirmation_sha256, str)
                or confirmation_sha256 != evidence["retrieved_sha256"]
            ):
                raise TransitionError("confirmation digest does not bind submission evidence")
            if (
                not isinstance(source_session_sha256, str)
                or SHA256_RE.fullmatch(source_session_sha256.lower()) is None
            ):
                raise TransitionError("source session digest is invalid")
            if not isinstance(submission_id, str) or not submission_id.strip():
                raise TransitionError("submission evidence requires submission_id")
            submission_id = submission_id.strip()

            if current["state"] == "SUBMITTED":
                transition = connection.execute(
                    "SELECT transition_id,from_state,to_state FROM opportunity_transitions "
                    "WHERE opportunity_id=? AND to_state='SUBMITTED' AND evidence_id=? "
                    "AND pitch_id=? ORDER BY observed_at LIMIT 1",
                    (opportunity_id, evidence_id, pitch_id),
                ).fetchone()
                if (
                    transition is None
                    or current["submission_id"] != submission_id
                    or current["response_recipient"] not in (None, response_recipient)
                ):
                    raise TransitionError("opportunity is already SUBMITTED from different evidence")
                if current["response_recipient"] is None:
                    connection.execute(
                        "UPDATE opportunities SET response_recipient=?,updated_at=? "
                        "WHERE opportunity_id=?",
                        (response_recipient, recovered_at, opportunity_id),
                    )
                self._record_application_in_connection(
                    connection, opportunity_id=opportunity_id, pitch_id=pitch_id,
                    provider_submission_id=submission_id,
                    response_recipient=response_recipient,
                    submission_evidence_id=evidence_id, submitted_at=submitted_at,
                    updated_at=recovered_at,
                )
                return {
                    "transition_id": str(transition["transition_id"]),
                    "from_state": str(transition["from_state"]),
                    "to_state": str(transition["to_state"]),
                    "pitch_id": pitch_id,
                    "evidence_id": evidence_id,
                    "replayed": True,
                }
            if current["state"] != "VALUE_UNKNOWN":
                raise TransitionError(
                    "historical submission recovery requires VALUE_UNKNOWN state"
                )
            if current["active_pitch_id"] or current["submission_id"]:
                raise TransitionError("historical submission recovery found conflicting state")

            connection.execute(
                "INSERT OR IGNORE INTO opportunity_pitches(pitch_id,opportunity_id,fingerprint,"
                "title,angle,claim_id,claim_url,claim_sha256,reader_job,created_at) "
                "VALUES(?,?,?,?,?,NULL,NULL,NULL,NULL,?)",
                (pitch_id, opportunity_id, fingerprint, title, angle, submitted_at),
            )
            pitch = connection.execute(
                "SELECT pitch_id FROM opportunity_pitches WHERE opportunity_id=? AND fingerprint=?",
                (opportunity_id, fingerprint),
            ).fetchone()
            if pitch is None or str(pitch["pitch_id"]) != pitch_id:
                raise TransitionError("recovered pitch conflicts with durable pitch")

            from_state = str(current["state"])
            transition_identity = (
                f"{opportunity_id}\n{from_state}\nSUBMITTED\n{submitted_at}\n"
                f"{evidence_id}\n{pitch_id}"
            )
            transition_id = (
                f"tr_{hashlib.sha256(transition_identity.encode()).hexdigest()[:24]}"
            )
            connection.execute(
                "INSERT INTO opportunity_transitions(transition_id,opportunity_id,from_state,"
                "to_state,observed_at,evidence_id,pitch_id,reason) VALUES(?,?,?,?,?,?,?,?)",
                (
                    transition_id, opportunity_id, from_state, "SUBMITTED", submitted_at,
                    evidence_id, pitch_id, reason,
                ),
            )
            connection.execute(
                "UPDATE opportunities SET state='SUBMITTED',active_pitch_id=?,submission_id=?,"
                "response_recipient=?,next_action=?,updated_at=? WHERE opportunity_id=?",
                (
                    pitch_id, submission_id, response_recipient, STATE_NEXT_ACTION["SUBMITTED"],
                    recovered_at, opportunity_id,
                ),
            )
            self._record_application_in_connection(
                connection, opportunity_id=opportunity_id, pitch_id=pitch_id,
                provider_submission_id=submission_id, response_recipient=response_recipient,
                submission_evidence_id=evidence_id, submitted_at=submitted_at,
                updated_at=recovered_at,
            )
        return {
            "transition_id": transition_id,
            "from_state": from_state,
            "to_state": "SUBMITTED",
            "pitch_id": pitch_id,
            "evidence_id": evidence_id,
        }

    def first_evidence_id(self, opportunity_id: str) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT evidence_id FROM opportunity_evidence WHERE opportunity_id=? "
                "ORDER BY observed_at,evidence_id LIMIT 1", (opportunity_id,)
            ).fetchone()
        if row is None:
            raise KeyError(opportunity_id)
        return str(row["evidence_id"])

    def create_pitch(
        self, opportunity_id: str, *, title: str, angle: str, claim_id: str,
        claim_url: str, claim_sha256: str, reader_job: str, created_at: str,
    ) -> dict[str, Any]:
        title = _text(title, "title")
        angle = _text(angle, "angle")
        claim_id = _text(claim_id, "claim_id").lower()
        if re.fullmatch(r"clm_[0-9a-f]{24}", claim_id) is None:
            raise ValueError("claim_id must be a durable claim identifier")
        claim_url = str(_canonical_url(claim_url, "claim_url"))
        claim_sha256 = _text(claim_sha256, "claim_sha256").lower()
        if SHA256_RE.fullmatch(claim_sha256) is None:
            raise ValueError("claim_sha256 must be a SHA-256 digest")
        reader_job = _text(reader_job, "reader_job")
        created_at = str(_timestamp(created_at, "created_at"))
        fingerprint = hashlib.sha256(
            f"{_normalized(title)}\n{_normalized(angle)}".encode("utf-8")
        ).hexdigest()
        pitch_identity = hashlib.sha256(f"{opportunity_id}\n{fingerprint}".encode()).hexdigest()
        pitch_id = f"pitch_{pitch_identity[:24]}"
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT state FROM opportunities WHERE opportunity_id=?", (opportunity_id,)
            ).fetchone()
            if row is None:
                raise KeyError(opportunity_id)
            if row["state"] != "POLICY_CLEAR":
                raise TransitionError("pitch requires POLICY_CLEAR state")
            inserted = connection.execute(
                "INSERT OR IGNORE INTO opportunity_pitches(pitch_id,opportunity_id,fingerprint,"
                "title,angle,claim_id,claim_url,claim_sha256,reader_job,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    pitch_id, opportunity_id, fingerprint, title, angle, claim_id,
                    claim_url, claim_sha256, reader_job, created_at,
                ),
            ).rowcount == 1
            durable = connection.execute(
                "SELECT pitch_id FROM opportunity_pitches WHERE opportunity_id=? AND fingerprint=?",
                (opportunity_id, fingerprint),
            ).fetchone()
            if durable is None:
                owner = connection.execute(
                    "SELECT pitch_id FROM opportunity_pitches WHERE claim_id=?", (claim_id,)
                ).fetchone()
                if owner is not None:
                    raise TransitionError("claim already belongs to a different durable pitch")
                raise RuntimeError("pitch insert produced no durable row")
        return {"pitch_id": str(durable["pitch_id"]), "inserted": inserted}

    def get_pitch(self, pitch_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM opportunity_pitches WHERE pitch_id=?", (pitch_id,)
            ).fetchone()
        if row is None:
            raise KeyError(pitch_id)
        return dict(row)

    def used_pitch_claim_ids(self) -> set[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT claim_id FROM opportunity_pitches WHERE claim_id IS NOT NULL"
            ).fetchall()
        return {str(row["claim_id"]) for row in rows}

    def record_inbound_message(
        self, opportunity_id: str, *, gmail_message_id: str, thread_id: str,
        sender: str, subject: str, received_at: str, retrieved_sha256: str,
        classification: str, observed_at: str, evidence_id: str | None = None,
    ) -> bool:
        gmail_message_id = _text(gmail_message_id, "gmail_message_id")
        thread_id = _text(thread_id, "thread_id")
        sender = _text(sender, "sender")
        subject = _text(subject, "subject")
        received_at = str(_timestamp(received_at, "received_at"))
        observed_at = str(_timestamp(observed_at, "observed_at"))
        retrieved_sha256 = _text(retrieved_sha256, "retrieved_sha256").lower()
        if SHA256_RE.fullmatch(retrieved_sha256) is None:
            raise ValueError("retrieved_sha256 must be a SHA-256 digest")
        classification = _text(classification, "classification").upper()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute(
                "SELECT 1 FROM opportunities WHERE opportunity_id=?", (opportunity_id,)
            ).fetchone() is None:
                raise KeyError(opportunity_id)
            if evidence_id is not None and connection.execute(
                "SELECT 1 FROM opportunity_evidence WHERE evidence_id=? AND opportunity_id=?",
                (evidence_id, opportunity_id),
            ).fetchone() is None:
                raise ValueError("evidence_id does not belong to opportunity")
            return connection.execute(
                "INSERT OR IGNORE INTO opportunity_inbound_messages("
                "gmail_message_id,opportunity_id,thread_id,sender,subject,received_at,"
                "retrieved_sha256,classification,evidence_id,observed_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    gmail_message_id, opportunity_id, thread_id, sender, subject,
                    received_at, retrieved_sha256, classification, evidence_id, observed_at,
                ),
            ).rowcount == 1

    def inbound_message_seen(self, gmail_message_id: str) -> bool:
        gmail_message_id = _text(gmail_message_id, "gmail_message_id")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM opportunity_inbound_messages WHERE gmail_message_id=?",
                (gmail_message_id,),
            ).fetchone()
        return row is not None

    def transition_commercial(
        self, entity_type: str, entity_id: str, to_state: str, *,
        evidence_id: str | None, observed_at: str, reason: str,
        fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entity_type = _text(entity_type, "entity_type").lower()
        entity_id = _text(entity_id, "entity_id")
        to_state = _text(to_state, "to_state").upper()
        observed_at = str(_timestamp(observed_at, "observed_at"))
        reason = _text(reason, "reason")
        config = COMMERCIAL_ENTITY_CONFIG.get(entity_type)
        if config is None:
            raise TransitionError("commercial entity type is invalid")
        if fields is None:
            fields = {}
        if not isinstance(fields, dict):
            raise TransitionError("commercial transition fields must be an object")
        if entity_type != "contract" and fields:
            raise TransitionError("transition fields are allowed only for contracts")
        unknown_fields = set(fields) - CONTRACT_TRANSITION_FIELDS
        if unknown_fields:
            raise TransitionError("contract transition fields are invalid")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                f"SELECT * FROM {config['table']} WHERE {config['id']}=?", (entity_id,)
            ).fetchone()
            if row is None:
                raise KeyError(entity_id)
            from_state = str(row["status"])
            if from_state == to_state:
                replay = connection.execute(
                    "SELECT transition_id,from_state,to_state,evidence_id "
                    "FROM opportunity_commercial_transitions "
                    "WHERE entity_type=? AND entity_id=? AND to_state=? "
                    "AND evidence_id IS ? ORDER BY observed_at LIMIT 1",
                    (entity_type, entity_id, to_state, evidence_id),
                ).fetchone()
                fields_match = not fields
                if entity_type == "contract" and to_state == "TERMS_COMPLETE":
                    replay_evidence = connection.execute(
                        "SELECT kind,payload_json FROM opportunity_evidence "
                        "WHERE evidence_id=? AND opportunity_id=?",
                        (evidence_id, row["opportunity_id"]),
                    ).fetchone()
                    try:
                        replay_payload = json.loads(replay_evidence["payload_json"])
                    except (TypeError, json.JSONDecodeError):
                        replay_payload = None
                    receipt_terms = (
                        "rate_amount", "currency", "rights_terms", "exclusivity_terms",
                        "ai_disclosure_policy", "delivery_channel", "payout_rail",
                        "payment_trigger",
                    )
                    fields_match = (
                        set(fields) == set(CONTRACT_TRANSITION_FIELDS)
                        and all(row[key] == fields[key] for key in CONTRACT_TRANSITION_FIELDS)
                        and replay_evidence is not None
                        and replay_evidence["kind"] == "acceptance"
                        and isinstance(replay_payload, dict)
                        and replay_payload.get("contract_id") == entity_id
                        and replay_payload.get("application_id") == row["application_id"]
                        and fields.get("terms_evidence_id") == evidence_id
                        and fields.get("blocking_terms_json") == "[]"
                        and all(
                            replay_payload.get(key) == fields.get(key)
                            for key in receipt_terms
                        )
                    )
                if replay is None or not fields_match:
                    raise TransitionError(
                        "commercial replay requires exact transition evidence and fields"
                    )
                return {
                    "transition_id": str(replay["transition_id"]),
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "from_state": str(replay["from_state"]),
                    "to_state": str(replay["to_state"]),
                    "evidence_id": replay["evidence_id"],
                    "replayed": True,
                }
            allowed = config["transitions"].get(from_state, {})
            if to_state not in allowed:
                raise TransitionError(
                    f"commercial transition {from_state} -> {to_state} is not allowed"
                )
            required_kind = allowed[to_state]
            evidence = None
            payload: dict[str, Any] = {}
            if required_kind is not None:
                evidence = connection.execute(
                    "SELECT * FROM opportunity_evidence WHERE evidence_id=? "
                    "AND opportunity_id=? AND kind=?",
                    (evidence_id, row["opportunity_id"], required_kind),
                ).fetchone()
                if evidence is None:
                    raise TransitionError(
                        f"{to_state} requires matching {required_kind} evidence"
                    )
                try:
                    payload = json.loads(evidence["payload_json"])
                except (TypeError, json.JSONDecodeError) as error:
                    raise TransitionError("commercial evidence payload is invalid") from error
                if not isinstance(payload, dict):
                    raise TransitionError("commercial evidence payload must be an object")
            elif evidence_id is not None:
                raise TransitionError(f"{from_state} -> {to_state} does not accept evidence")

            if entity_type == "application" and to_state in {"ACCEPTED", "DECLINED"}:
                if (
                    payload.get("application_id") != entity_id
                    or payload.get("provider_submission_id") != row["provider_submission_id"]
                ):
                    raise TransitionError("exact application receipt is required")
            if entity_type == "contract" and to_state == "TERMS_COMPLETE":
                receipt_terms = (
                    "rate_amount", "currency", "rights_terms", "exclusivity_terms",
                    "ai_disclosure_policy", "delivery_channel", "payout_rail",
                    "payment_trigger",
                )
                if (
                    payload.get("contract_id") != entity_id
                    or payload.get("application_id") != row["application_id"]
                    or fields.get("terms_evidence_id") != evidence_id
                    or any(payload.get(key) != fields.get(key) for key in receipt_terms)
                ):
                    raise TransitionError("exact contract terms receipt is required")
            if entity_type == "assignment" and to_state == "DELIVERED":
                delivery = connection.execute(
                    "SELECT 1 FROM opportunity_deliveries WHERE assignment_id=? "
                    "AND opportunity_id=? AND delivery_evidence_id=? AND status='SUBMITTED'",
                    (entity_id, row["opportunity_id"], evidence_id),
                ).fetchone()
                if delivery is None:
                    raise TransitionError("exact delivery receipt is required")
            if entity_type == "assignment" and to_state == "CLOSED":
                if payload.get("assignment_id") != entity_id:
                    raise TransitionError("exact assignment closure receipt is required")
            if entity_type == "delivery" and to_state in {"ACCEPTED", "REJECTED"}:
                if (
                    payload.get("delivery_id") != entity_id
                    or payload.get("artifact_sha256") != row["artifact_sha256"]
                    or payload.get("provider_delivery_id") != row["provider_delivery_id"]
                ):
                    label = "acceptance" if to_state == "ACCEPTED" else "rejection"
                    raise TransitionError(f"exact delivery {label} receipt is required")
            if entity_type == "publication" and to_state == "REMOVED":
                if (
                    payload.get("publication_id") != entity_id
                    or payload.get("public_url") != row["public_url"]
                    or payload.get("readback_sha256") != row["readback_sha256"]
                ):
                    raise TransitionError("exact publication closure receipt is required")

            assignments = ["status=?", "updated_at=?"]
            values: list[Any] = [to_state, observed_at]
            for key in sorted(fields):
                assignments.append(f"{key}=?")
                values.append(fields[key])
            values.append(entity_id)
            try:
                connection.execute(
                    f"UPDATE {config['table']} SET {','.join(assignments)} "
                    f"WHERE {config['id']}=?",
                    values,
                )
            except sqlite3.IntegrityError as error:
                raise TransitionError(str(error)) from error
            transition_identity = (
                f"{entity_type}\n{entity_id}\n{from_state}\n{to_state}\n{observed_at}\n"
                f"{evidence_id or ''}"
            )
            transition_id = "ctr_" + hashlib.sha256(
                transition_identity.encode("utf-8")
            ).hexdigest()[:24]
            connection.execute(
                "INSERT INTO opportunity_commercial_transitions(transition_id,entity_type,"
                "entity_id,opportunity_id,from_state,to_state,evidence_id,observed_at,reason) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    transition_id, entity_type, entity_id, row["opportunity_id"], from_state,
                    to_state, evidence_id, observed_at, reason,
                ),
            )
        return {
            "transition_id": transition_id, "entity_type": entity_type,
            "entity_id": entity_id, "from_state": from_state, "to_state": to_state,
            "evidence_id": evidence_id,
        }

    def advance(
        self, opportunity_id: str, to_state: str, *, observed_at: str,
        reason: str, evidence_id: str | None = None, pitch_id: str | None = None,
    ) -> dict[str, Any]:
        if to_state not in STATES:
            raise TransitionError("target state is invalid")
        observed_at = str(_timestamp(observed_at, "observed_at"))
        reason = _text(reason, "reason")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                "SELECT * FROM opportunities WHERE opportunity_id=?", (opportunity_id,)
            ).fetchone()
            if current is None:
                raise KeyError(opportunity_id)
            from_state = str(current["state"])
            if current["ai_policy"] == "PROHIBITED" and to_state == "POLICY_CLEAR":
                raise TransitionError("official policy prohibits AI-assisted writing")
            if to_state == from_state:
                raise TransitionError(f"opportunity is already {to_state}; duplicate transition refused")
            if to_state not in ALLOWED_TRANSITIONS[from_state]:
                raise TransitionError(f"transition {from_state} -> {to_state} is not allowed")
            if to_state == "VERIFIED_OPEN" and current["intake_state"] != "OPEN":
                raise TransitionError("VERIFIED_OPEN requires intake_state OPEN")
            evidence = None
            required_kind = REQUIRED_EVIDENCE_KIND.get(to_state)
            if required_kind:
                evidence = connection.execute(
                    "SELECT * FROM opportunity_evidence WHERE evidence_id=? AND opportunity_id=?",
                    (evidence_id, opportunity_id),
                ).fetchone()
                if evidence is None or evidence["kind"] != required_kind:
                    label = "policy evidence" if to_state == "POLICY_CLEAR" else f"{required_kind} evidence"
                    raise TransitionError(f"{to_state} requires matching {label}")
            if to_state == "PITCH_READY":
                pitch = connection.execute(
                    "SELECT 1 FROM opportunity_pitches WHERE pitch_id=? AND opportunity_id=?",
                    (pitch_id, opportunity_id),
                ).fetchone()
                if pitch is None:
                    raise TransitionError("PITCH_READY requires a durable nonduplicate pitch")
            if to_state == "SUBMITTED":
                pitch = connection.execute(
                    "SELECT 1 FROM opportunity_pitches WHERE pitch_id=? AND opportunity_id=?",
                    (pitch_id, opportunity_id),
                ).fetchone()
                if pitch is None or current["active_pitch_id"] not in (None, pitch_id):
                    raise TransitionError("SUBMITTED requires the active durable pitch")
                payload = json.loads(evidence["payload_json"])
                submission_id = payload.get("submission_id")
                if not isinstance(submission_id, str) or not submission_id.strip():
                    raise TransitionError("submission evidence requires submission_id")
            else:
                submission_id = current["submission_id"]
            received_amount = current["received_amount"]
            received_currency = current["received_currency"]
            if to_state == "RECEIVED":
                payload = json.loads(evidence["payload_json"])
                amount = payload.get("amount")
                currency = payload.get("currency")
                valid_payment = (
                    isinstance(amount, (int, float)) and not isinstance(amount, bool) and amount > 0
                    and isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency)
                    and payload.get("test") is False
                    and isinstance(payload.get("receipt_id"), str) and payload["receipt_id"].strip()
                    and isinstance(payload.get("received_by"), str) and payload["received_by"].strip()
                )
                if not valid_payment:
                    raise TransitionError("RECEIVED requires a positive non-test payment receipt")
                received_amount = float(amount)
                received_currency = currency
            transition_identity = (
                f"{opportunity_id}\n{from_state}\n{to_state}\n{observed_at}\n"
                f"{evidence_id or ''}\n{pitch_id or ''}"
            )
            transition_id = f"tr_{hashlib.sha256(transition_identity.encode()).hexdigest()[:24]}"
            connection.execute(
                "INSERT INTO opportunity_transitions(transition_id,opportunity_id,from_state,"
                "to_state,observed_at,evidence_id,pitch_id,reason) VALUES(?,?,?,?,?,?,?,?)",
                (
                    transition_id, opportunity_id, from_state, to_state, observed_at,
                    evidence_id, pitch_id, reason,
                ),
            )
            active_pitch = pitch_id if to_state in {"PITCH_READY", "SUBMITTED"} else current["active_pitch_id"]
            next_action = STATE_NEXT_ACTION.get(to_state, current["next_action"])
            connection.execute(
                "UPDATE opportunities SET state=?,active_pitch_id=?,submission_id=?,"
                "received_amount=?,received_currency=?,next_action=?,updated_at=? "
                "WHERE opportunity_id=?",
                (
                    to_state, active_pitch, submission_id, received_amount, received_currency,
                    next_action, observed_at, opportunity_id,
                ),
            )
            if to_state == "SUBMITTED":
                self._record_application_in_connection(
                    connection, opportunity_id=opportunity_id, pitch_id=str(pitch_id),
                    provider_submission_id=str(submission_id), response_recipient=None,
                    submission_evidence_id=str(evidence_id), submitted_at=observed_at,
                    updated_at=observed_at,
                )
        return {"transition_id": transition_id, "from_state": from_state, "to_state": to_state}

    def get(self, opportunity_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT o.*,(SELECT COUNT(*) FROM opportunity_evidence e WHERE "
                "e.opportunity_id=o.opportunity_id) AS evidence_count FROM opportunities o "
                "WHERE opportunity_id=?", (opportunity_id,)
            ).fetchone()
        if row is None:
            raise KeyError(opportunity_id)
        result = dict(row)
        for field in (
            "topics_json", "editorial_steps_json", "requirements_json", "supporting_urls_json"
        ):
            result[field.removesuffix("_json")] = json.loads(result.pop(field))
        return result
