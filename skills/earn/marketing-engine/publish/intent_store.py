#!/usr/bin/env python3
"""Durable publication intents, leases, fences, and dispatch attempts."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import sqlite3


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def normalize_caption(value: str) -> str:
    return " ".join(value.split())


def caption_sha256(value: str) -> str:
    return hashlib.sha256(normalize_caption(value).encode()).hexdigest()


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_id(prefix: str, values: list[str]) -> str:
    raw = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode()
    return f"{prefix}.{hashlib.sha256(raw).hexdigest()[:24]}"


def _provider_settings_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _intent_causal(intent: dict) -> list[str]:
    return [intent[field] for field in (
        "experiment_id", "creative_id", "product_id", "account_id", "hook_id",
        "renderer_id", "adapter", "asset_sha256", "caption_sha256", "scheduled_at",
        "integration_id", "platform", "native_handle",
    )] + [_provider_settings_json(intent["provider_settings"]), str(intent.get("script_id") or "")]


def validate_intent(intent: dict) -> None:
    require(intent.get("schema_version") == "marketing.publication-intent.v2",
            "intent schema invalid")
    asset = pathlib.Path(intent.get("asset_path") or "")
    require(asset.is_file() and file_sha256(asset) == intent.get("asset_sha256"),
            "asset hash mismatch")
    normalized = normalize_caption(str(intent.get("caption") or ""))
    require(normalized == intent.get("caption") and
            caption_sha256(normalized) == intent.get("caption_sha256"),
            "caption hash mismatch")
    require(str(intent.get("attribution_token") or "") in normalized,
            "attribution token missing from caption")
    require(str(intent.get("visual_approval_id") or "").startswith("visual.accepted."),
            "accepted visual approval required")
    settings = intent.get("provider_settings")
    require(isinstance(settings, dict) and settings.get("__type"),
            "provider settings required")
    _epoch(str(intent.get("scheduled_at") or ""))
    require(intent.get("publish_key") == stable_id("publication", _intent_causal(intent)),
            "publish key mismatch")


def build_intent(*, experiment_id: str, creative_id: str, product_id: str,
                 account_id: str, hook_id: str, renderer_id: str, adapter: str,
                 asset_path: pathlib.Path, caption: str, attribution_token: str,
                 scheduled_at: str, integration_id: str, platform: str,
                 native_handle: str,
                 provider_settings: dict,
                 visual_approval_id: str, script_id: str | None = None) -> dict:
    asset = pathlib.Path(asset_path).resolve()
    require(asset.is_file(), "publication asset missing")
    normalized = normalize_caption(caption)
    require(attribution_token in normalized, "attribution token missing from caption")
    require(visual_approval_id.startswith("visual.accepted."), "accepted visual approval required")
    require(isinstance(native_handle, str) and native_handle.strip(), "native handle required")
    require(isinstance(provider_settings, dict) and provider_settings.get("__type"),
            "provider settings required")
    _epoch(scheduled_at)
    provider_settings_json = _provider_settings_json(provider_settings)
    causal = [experiment_id, creative_id, product_id, account_id, hook_id, renderer_id,
              adapter, file_sha256(asset), caption_sha256(normalized), scheduled_at,
              integration_id, platform, native_handle, provider_settings_json, str(script_id or "")]
    return {
        "schema_version": "marketing.publication-intent.v2",
        "publish_key": stable_id("publication", causal),
        "experiment_id": experiment_id, "creative_id": creative_id,
        "product_id": product_id, "account_id": account_id, "hook_id": hook_id,
        "renderer_id": renderer_id, "adapter": adapter,
        "asset_path": str(asset), "asset_sha256": file_sha256(asset),
        "caption": normalized, "caption_sha256": caption_sha256(normalized),
        "attribution_token": attribution_token, "scheduled_at": scheduled_at,
        "integration_id": integration_id, "platform": platform,
        "native_handle": native_handle,
        "provider_settings": provider_settings,
        "visual_approval_id": visual_approval_id,
        **({"script_id": script_id} if script_id else {}),
    }


def _epoch(value: str) -> float:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timestamp timezone required")
    return parsed.timestamp()


class IntentStore:
    def __init__(self, path: pathlib.Path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _init(self):
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS intents (
                    publish_key TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    scheduled_at TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'registered',
                    provider_media_id TEXT,
                    provider_media_path TEXT,
                    provider_media_receipt_json TEXT,
                    provider_post_id TEXT,
                    provider_receipt_json TEXT,
                    native_post_id TEXT,
                    native_post_url TEXT,
                    lease_owner TEXT,
                    lease_expires_epoch REAL,
                    fence INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    UNIQUE(account_id, scheduled_at)
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    attempt_id TEXT PRIMARY KEY,
                    publish_key TEXT NOT NULL REFERENCES intents(publish_key),
                    operation TEXT NOT NULL,
                    fence INTEGER NOT NULL,
                    request_sha256 TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    response_json TEXT,
                    error TEXT,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    UNIQUE(publish_key, operation)
                );
                CREATE TABLE IF NOT EXISTS browser_preflights (
                    publish_key TEXT PRIMARY KEY REFERENCES intents(publish_key),
                    expected_handle TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(intents)")}
            for name in ("provider_media_id", "provider_media_path", "provider_media_receipt_json"):
                if name not in columns:
                    db.execute(f"ALTER TABLE intents ADD COLUMN {name} TEXT")

    def register(self, intent: dict) -> dict:
        validate_intent(intent)
        payload = json.dumps(intent, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT payload_json FROM intents WHERE publish_key=?",
                                  (intent["publish_key"],)).fetchone()
            if existing:
                require(existing["payload_json"] == payload, "conflicting intent replay")
                return {"created": False, "intent": intent}
            occupied = db.execute("SELECT publish_key FROM intents WHERE account_id=? AND scheduled_at=?",
                                  (intent["account_id"], intent["scheduled_at"])).fetchone()
            require(occupied is None, "account slot already reserved")
            db.execute("INSERT INTO intents(publish_key,payload_json,account_id,scheduled_at) VALUES(?,?,?,?)",
                       (intent["publish_key"], payload, intent["account_id"], intent["scheduled_at"]))
            return {"created": True, "intent": intent}

    def get(self, publish_key: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT * FROM intents WHERE publish_key=?", (publish_key,)).fetchone()
        require(row is not None, "publication intent not found")
        value = dict(row)
        value["intent"] = json.loads(value.pop("payload_json"))
        if value.get("provider_receipt_json"):
            value["provider_receipt"] = json.loads(value["provider_receipt_json"])
        return value

    def acquire(self, publish_key: str, *, owner: str, now: str, ttl_seconds: int) -> dict | None:
        require(owner and ttl_seconds > 0, "lease owner and positive TTL required")
        current = _epoch(now)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT lease_owner,lease_expires_epoch,fence FROM intents WHERE publish_key=?",
                             (publish_key,)).fetchone()
            require(row is not None, "publication intent not found")
            if row["lease_owner"] == owner and (row["lease_expires_epoch"] or 0) > current:
                return {"owner": owner, "fence": row["fence"],
                        "expires_epoch": row["lease_expires_epoch"]}
            if row["lease_owner"] and (row["lease_expires_epoch"] or 0) > current:
                return None
            fence = row["fence"] + 1
            expiry = current + ttl_seconds
            db.execute("UPDATE intents SET lease_owner=?,lease_expires_epoch=?,fence=?,state=CASE WHEN state='registered' THEN 'leased' ELSE state END WHERE publish_key=?",
                       (owner, expiry, fence, publish_key))
            return {"owner": owner, "fence": fence, "expires_epoch": expiry}

    def _assert_lease(self, db, publish_key: str, owner: str, fence: int, now: str):
        row = db.execute("SELECT lease_owner,lease_expires_epoch,fence FROM intents WHERE publish_key=?",
                         (publish_key,)).fetchone()
        require(row is not None, "publication intent not found")
        require(row["lease_owner"] == owner and row["fence"] == fence and
                (row["lease_expires_epoch"] or 0) >= _epoch(now), "stale lease fence")

    def assert_lease(self, publish_key: str, owner: str, fence: int, now: str) -> None:
        with self.connect() as db:
            self._assert_lease(db, publish_key, owner, fence, now)

    def begin_dispatch(self, publish_key: str, *, owner: str, fence: int,
                       operation: str, request: dict, now: str) -> dict:
        request_json = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        request_hash = hashlib.sha256(request_json.encode()).hexdigest()
        attempt_id = stable_id("dispatch", [publish_key, operation])
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._assert_lease(db, publish_key, owner, fence, now)
            existing = db.execute("SELECT * FROM attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
            if existing:
                require(existing["request_sha256"] == request_hash, "conflicting dispatch replay")
                return {**dict(existing), "created": False,
                        "response": json.loads(existing["response_json"]) if existing["response_json"] else None}
            db.execute("INSERT INTO attempts(attempt_id,publish_key,operation,fence,request_sha256,request_json,state,started_at) VALUES(?,?,?,?,?,?,?,?)",
                       (attempt_id, publish_key, operation, fence, request_hash, request_json,
                        "dispatching", now))
            db.execute("UPDATE intents SET state=? WHERE publish_key=?",
                       (f"{operation}_dispatching", publish_key))
            return {"attempt_id": attempt_id, "publish_key": publish_key,
                    "operation": operation, "fence": fence, "request_sha256": request_hash,
                    "request_json": request_json, "state": "dispatching", "started_at": now,
                    "response_json": None, "error": None, "finished_at": None,
                    "created": True, "response": None}

    def mark_uncertain(self, attempt_id: str, error: str, *, now: str) -> dict:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT publish_key FROM attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
            require(row is not None, "dispatch attempt not found")
            db.execute("UPDATE attempts SET state='uncertain',error=?,finished_at=? WHERE attempt_id=?",
                       (error, now, attempt_id))
            db.execute("UPDATE intents SET state='uncertain',last_error=? WHERE publish_key=?",
                       (error, row["publish_key"]))
        return self.attempt(attempt_id)

    def mark_rejected(self, attempt_id: str, error: str, *, now: str,
                      intent_state: str = "provider_rejected") -> dict:
        require(intent_state in {"provider_rejected", "browser_rejected"},
                "invalid rejected intent state")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT publish_key,state FROM attempts WHERE attempt_id=?",
                             (attempt_id,)).fetchone()
            require(row is not None, "dispatch attempt not found")
            require(row["state"] == "dispatching", "only dispatching attempt may be rejected")
            db.execute("UPDATE attempts SET state='rejected',error=?,finished_at=? WHERE attempt_id=?",
                       (error, now, attempt_id))
            db.execute("UPDATE intents SET state=?,last_error=? WHERE publish_key=?",
                       (intent_state, error, row["publish_key"]))
        return self.attempt(attempt_id)

    def attempt(self, attempt_id: str) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT * FROM attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
        require(row is not None, "dispatch attempt not found")
        result = dict(row)
        result["created"] = False
        result["response"] = json.loads(result["response_json"]) if result["response_json"] else None
        return result

    def attempts_for(self, publish_key: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT operation,state,started_at,finished_at FROM attempts "
                "WHERE publish_key=? ORDER BY started_at,operation", (publish_key,)).fetchall()
        return [dict(row) for row in rows]

    def record_response(self, attempt_id: str, response: dict | list, *, now: str) -> dict:
        response_json = json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT publish_key,operation,state,response_json FROM attempts WHERE attempt_id=?",
                             (attempt_id,)).fetchone()
            require(row is not None, "dispatch attempt not found")
            if row["state"] == "accepted":
                require(row["response_json"] == response_json, "conflicting provider response")
                return self.attempt(attempt_id)
            post_id = None
            if row["operation"] == "upload_media":
                require(isinstance(response, dict), "Postiz upload response must be an object")
                media_id = response.get("id")
                media_path = response.get("path")
                require(isinstance(media_id, str) and media_id, "Postiz upload response lacks id")
                require(isinstance(media_path, str) and media_path.startswith("https://"),
                        "Postiz upload response lacks https path")
                db.execute("UPDATE attempts SET state='accepted',response_json=?,finished_at=? WHERE attempt_id=?",
                           (response_json, now, attempt_id))
                db.execute("UPDATE intents SET state='media_uploaded',provider_media_id=?,provider_media_path=?,provider_media_receipt_json=?,last_error=NULL WHERE publish_key=?",
                           (media_id, media_path, response_json, row["publish_key"]))
            elif row["operation"] == "create_draft":
                first = response[0] if isinstance(response, list) and response else response
                post_id = first.get("postId") if isinstance(first, dict) else None
                require(isinstance(post_id, str) and post_id, "Postiz create response lacks postId")
                intent_state = "draft_created"
            elif row["operation"] == "promote":
                current = db.execute("SELECT provider_post_id FROM intents WHERE publish_key=?",
                                     (row["publish_key"],)).fetchone()
                post_id = current["provider_post_id"]
                require(post_id, "cannot promote without stored postId")
                intent_state = "scheduled"
            elif row["operation"] != "upload_media":
                raise ValueError(f"unsupported dispatch operation: {row['operation']}")
            if row["operation"] != "upload_media":
                db.execute("UPDATE attempts SET state='accepted',response_json=?,finished_at=? WHERE attempt_id=?",
                           (response_json, now, attempt_id))
                db.execute("UPDATE intents SET state=?,provider_post_id=?,provider_receipt_json=?,last_error=NULL WHERE publish_key=?",
                           (intent_state, post_id, response_json, row["publish_key"]))
        return self.attempt(attempt_id)

    def reconcile_provider(self, publish_key: str, post: dict) -> dict:
        post_id = str(post.get("id") or post.get("postId") or "")
        require(post_id, "remote post lacks id")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT provider_post_id FROM intents WHERE publish_key=?", (publish_key,)).fetchone()
            require(row is not None, "publication intent not found")
            require(row["provider_post_id"] in {None, post_id}, "remote post conflicts with stored postId")
            state = "published_provider" if post.get("state") == "PUBLISHED" else "reconciled_provider"
            db.execute("UPDATE intents SET provider_post_id=?,provider_receipt_json=?,state=?,last_error=NULL WHERE publish_key=?",
                       (post_id, json.dumps(post, ensure_ascii=False, sort_keys=True,
                                            separators=(",", ":")), state, publish_key))
        return self.get(publish_key)

    def record_browser_preflight(self, publish_key: str, expected_handle: str,
                                 snapshot: dict, observed_at: str) -> dict:
        payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            require(db.execute("SELECT 1 FROM intents WHERE publish_key=?", (publish_key,)).fetchone()
                    is not None, "publication intent not found")
            existing = db.execute("SELECT * FROM browser_preflights WHERE publish_key=?",
                                  (publish_key,)).fetchone()
            if existing:
                require(existing["expected_handle"] == expected_handle and
                        existing["snapshot_json"] == payload, "conflicting browser preflight replay")
                return {**dict(existing), "snapshot": json.loads(existing["snapshot_json"])}
            db.execute("INSERT INTO browser_preflights(publish_key,expected_handle,snapshot_json,observed_at) VALUES(?,?,?,?)",
                       (publish_key, expected_handle, payload, observed_at))
        return {"publish_key": publish_key, "expected_handle": expected_handle,
                "snapshot_json": payload, "snapshot": snapshot,
                "observed_at": observed_at}

    def browser_preflight(self, publish_key: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM browser_preflights WHERE publish_key=?",
                             (publish_key,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["snapshot"] = json.loads(result["snapshot_json"])
        return result

    def record_native_response(self, attempt_id: str, response: dict, *, now: str) -> dict:
        native_id = response.get("native_post_id")
        native_url = response.get("native_post_url")
        require(isinstance(native_id, str) and native_id, "native response lacks post ID")
        require(isinstance(native_url, str) and native_url.startswith("https://"),
                "native response lacks https URL")
        payload = json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            attempt = db.execute("SELECT publish_key,operation,state,response_json FROM attempts WHERE attempt_id=?",
                                 (attempt_id,)).fetchone()
            require(attempt is not None, "dispatch attempt not found")
            require(attempt["operation"] == "browser_submit", "native response operation mismatch")
            if attempt["state"] == "accepted":
                require(attempt["response_json"] == payload, "conflicting native response")
            else:
                db.execute("UPDATE attempts SET state='accepted',response_json=?,finished_at=? WHERE attempt_id=?",
                           (payload, now, attempt_id))
                db.execute("UPDATE intents SET state='published',native_post_id=?,native_post_url=?,last_error=NULL WHERE publish_key=?",
                           (native_id, native_url, attempt["publish_key"]))
        return self.attempt(attempt_id)

    def record_reconciled_native(self, publish_key: str, native: dict) -> dict:
        native_id = native.get("native_post_id")
        native_url = native.get("native_post_url")
        require(isinstance(native_id, str) and native_id, "native receipt lacks post ID")
        require(isinstance(native_url, str) and native_url.startswith("https://"),
                "native receipt lacks https URL")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT native_post_id,native_post_url FROM intents WHERE publish_key=?",
                             (publish_key,)).fetchone()
            require(row is not None, "publication intent not found")
            require(row["native_post_id"] in {None, native_id} and
                    row["native_post_url"] in {None, native_url},
                    "conflicting native receipt")
            db.execute("UPDATE intents SET state='published',native_post_id=?,native_post_url=?,last_error=NULL WHERE publish_key=?",
                       (native_id, native_url, publish_key))
        return self.get(publish_key)

    def mark_provider_error(self, publish_key: str, post: dict) -> dict:
        payload = json.dumps(post, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            require(db.execute("SELECT 1 FROM intents WHERE publish_key=?", (publish_key,)).fetchone()
                    is not None, "publication intent not found")
            db.execute("UPDATE intents SET state='provider_error',provider_receipt_json=?,last_error='provider state ERROR' WHERE publish_key=?",
                       (payload, publish_key))
        return self.get(publish_key)
