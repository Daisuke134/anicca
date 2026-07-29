import concurrent.futures
import hashlib
import importlib.util
import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "connector_outbox.py"
SPEC = importlib.util.spec_from_file_location("connector_outbox", SCRIPT)
outbox_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(outbox_module)


class ConnectorOutboxTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db_path = self.root / "gig.sqlite3"
        source_manifest = Path(__file__).resolve().parents[1] / "config" / "connectors" / "coconala.json"
        self.manifest_path = self.root / "coconala.json"
        self.manifest_path.write_text(source_manifest.read_text(encoding="utf-8"), encoding="utf-8")
        self.outbox = outbox_module.ConnectorOutbox(self.db_path, self.manifest_path)

    def tearDown(self):
        self.temp.cleanup()

    def message_event_key(self, message_id, thread_id="42"):
        return outbox_module.coconala_message_event_key(thread_id, message_id)

    def enqueue(self, message_id="message-1", thread_id="42", observed_at=100):
        return self.outbox.enqueue(
            event_key=self.message_event_key(message_id, thread_id),
            thread_id=thread_id,
            thread_url=f"https://coconala.com/mypage/direct_message/{thread_id}",
            observed_at=observed_at,
        )

    def db_value(self, sql, parameters=()):
        with closing(sqlite3.connect(self.db_path)) as connection:
            return connection.execute(sql, parameters).fetchone()[0]

    def test_normalization_and_sha256_contract(self):
        raw = "  Cafe\u0301\tjob\r\nnext\u00a0  line  "
        normalized = "Caf\u00e9 job\nnext line"
        self.assertEqual(outbox_module.normalize_outgoing_body(raw), normalized)
        self.assertEqual(
            outbox_module.outgoing_sha256(raw),
            hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        )

    def test_intent_origin_is_durable_and_immutable(self):
        action = self.enqueue(observed_at=100)
        claim = self.outbox.claim(owner="origin-worker", now=101, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="origin-worker",
            fencing_token=claim["fencing_token"], outgoing_body="bounded reply",
            now=102, origin_at=90,
        )

        self.assertEqual(intent["origin_at"], 90)
        with self.assertRaises(outbox_module.ImmutableIntent):
            self.outbox.prepare_intent(
                action["action_id"], owner="origin-worker",
                fencing_token=claim["fencing_token"], outgoing_body="bounded reply",
                now=103, origin_at=91,
            )

    def test_thread_url_query_secrets_are_never_persisted(self):
        action = self.outbox.enqueue(
            event_key=self.message_event_key("event-safe-url"),
            thread_id="42",
            thread_url="https://coconala.com/mypage/direct_message/42?token=TOPSECRET#fragment",
            observed_at=100,
        )
        self.assertEqual(action["thread_url"], "https://coconala.com/mypage/direct_message/42")
        with closing(sqlite3.connect(self.db_path)) as connection:
            dump = "\n".join(connection.iterdump())
        self.assertNotIn("TOPSECRET", dump)
        with self.assertRaises(ValueError):
            self.outbox.enqueue(
                event_key="raw customer message body",
                thread_id="42",
                thread_url="https://coconala.com/mypage/direct_message/42",
                observed_at=101,
            )

    def test_thread_url_final_id_must_match_supplied_thread_id(self):
        with self.assertRaises(ValueError):
            self.outbox.enqueue(
                event_key=self.message_event_key("event-thread-mismatch"),
                thread_id="42",
                thread_url="https://coconala.com/mypage/direct_message/43",
                observed_at=102,
            )
        self.assertEqual(self.db_value("SELECT COUNT(*) FROM connector_actions"), 0)
        self.assertEqual(self.db_value("SELECT COUNT(*) FROM connector_events"), 0)

    def test_typed_event_keys_bind_thread_and_fallback_never_persists_raw_body(self):
        raw_body = "yes INBOUND_TOPSECRET_7f35 customer details"
        fallback_key = outbox_module.coconala_fallback_event_key(
            thread_id="42", buyer_sent_at=1_700_000_000, ordinal=3, raw_body=raw_body
        )
        action = self.outbox.enqueue(
            event_key=fallback_key,
            thread_id="42",
            thread_url="https://coconala.com/mypage/direct_message/42",
            observed_at=1_700_000_001,
        )
        self.assertEqual(action["thread_id"], "42")
        with closing(sqlite3.connect(self.db_path)) as connection:
            dump = "\n".join(connection.iterdump())
        self.assertNotIn(raw_body, dump)
        self.assertNotIn("INBOUND_TOPSECRET_7f35", dump)

        message_key = outbox_module.coconala_message_event_key("42", "message-abc")
        with self.assertRaises(ValueError):
            self.outbox.enqueue(
                event_key=message_key,
                thread_id="43",
                thread_url="https://coconala.com/mypage/direct_message/43",
                observed_at=1_700_000_002,
            )
        for raw_key in ("TOPSECRET", "yes", "event-1"):
            with self.subTest(raw_key=raw_key), self.assertRaises(ValueError):
                self.outbox.enqueue(
                    event_key=raw_key,
                    thread_id="42",
                    thread_url="https://coconala.com/mypage/direct_message/42",
                    observed_at=1_700_000_002,
                )

        initial_key = outbox_module.coconala_initial_contact_event_key("order-99")
        initial = self.outbox.enqueue(
            event_key=initial_key,
            thread_id="43",
            thread_url="https://coconala.com/mypage/direct_message/43",
            observed_at=1_700_000_003,
        )
        self.assertEqual(initial["thread_id"], "43")
        before = self.db_value("SELECT COUNT(*) FROM connector_actions")
        with self.assertRaises(outbox_module.OutboxError):
            self.outbox.enqueue(
                event_key=initial_key,
                thread_id="44",
                thread_url="https://coconala.com/mypage/direct_message/44",
                observed_at=1_700_000_004,
            )
        self.assertEqual(self.db_value("SELECT COUNT(*) FROM connector_actions"), before)

    def test_body_hash_boundaries_reject_non_string_values_without_persistence(self):
        for invalid_body in (None, b"bytes body", 123):
            with self.subTest(api="normalize", invalid_body=invalid_body):
                with self.assertRaises(TypeError):
                    outbox_module.normalize_outgoing_body(invalid_body)
            with self.subTest(api="fallback", invalid_body=invalid_body):
                with self.assertRaises(TypeError):
                    outbox_module.coconala_fallback_event_key(
                        thread_id="42", buyer_sent_at=1_700_000_000,
                        ordinal=1, raw_body=invalid_body,
                    )
        self.assertEqual(self.db_value("SELECT COUNT(*) FROM connector_events"), 0)

        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=200, lease_seconds=60)
        with self.assertRaises(TypeError):
            self.outbox.prepare_intent(
                action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
                outgoing_body=None, now=201,
            )
        self.assertEqual(self.db_value("SELECT COUNT(*) FROM connector_intents"), 0)

    def test_duplicate_event_and_two_connection_same_thread_race_coalesce_atomically(self):
        barrier = threading.Barrier(2)

        def race(index):
            independent = outbox_module.ConnectorOutbox(self.db_path, self.manifest_path)
            barrier.wait()
            return independent.enqueue(
                event_key=outbox_module.coconala_message_event_key("99", f"event-race-{index}"),
                thread_id="99",
                thread_url="https://coconala.com/mypage/direct_message/99",
                observed_at=100,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            rows = list(executor.map(race, (1, 2)))

        self.assertEqual(rows[0]["action_id"], rows[1]["action_id"])
        duplicate = self.outbox.enqueue(
            event_key=outbox_module.coconala_message_event_key("99", "event-race-1"),
            thread_id="99",
            thread_url="https://coconala.com/mypage/direct_message/99",
            observed_at=999,
        )
        self.assertEqual(duplicate["action_id"], rows[0]["action_id"])
        self.assertEqual(self.db_value("SELECT COUNT(*) FROM connector_actions"), 1)
        self.assertEqual(self.db_value("SELECT COUNT(*) FROM connector_events"), 2)

    def test_concurrent_legacy_schema_migration_is_atomic_and_backfills_origin(self):
        for round_number in range(5):
            database = self.root / f"legacy-{round_number}.sqlite3"
            legacy_schema = (
                outbox_module.SCHEMA
                .replace("    origin_at INTEGER,\n", "")
                .replace("    rejection_code TEXT,\n", "")
            )
            with closing(sqlite3.connect(database)) as connection:
                connection.executescript(legacy_schema)
                connection.execute(
                    """INSERT INTO connector_actions
                       (platform,thread_id,thread_url,state,revision,created_at,updated_at)
                       VALUES('coconala','42','https://coconala.com/mypage/direct_message/42',
                              'reconcile_pending',1,100,103)"""
                )
                connection.execute(
                    """INSERT INTO connector_intents
                       (action_id,revision,outgoing_hash,owner_id,fencing_token,state,created_at)
                       VALUES(1,1,?,'legacy-worker',1,'reconcile_pending',101)""",
                    ("a" * 64,),
                )
                connection.commit()
            barrier = threading.Barrier(16)

            def initialize(_):
                barrier.wait()
                outbox_module.ConnectorOutbox(database, self.manifest_path)

            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                list(executor.map(initialize, range(16)))

            with closing(sqlite3.connect(database)) as connection:
                columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(connector_intents)")
                }
                self.assertIn("origin_at", columns)
                self.assertIn("rejection_code", columns)
                self.assertEqual(
                    connection.execute(
                        "SELECT origin_at FROM connector_intents WHERE action_id=1"
                    ).fetchone()[0],
                    100,
                )

    def test_duplicate_event_key_requires_same_thread_identity(self):
        original = self.enqueue(message_id="event-stable-identity")
        before = (
            self.db_value("SELECT COUNT(*) FROM connector_actions"),
            self.db_value("SELECT COUNT(*) FROM connector_events"),
        )
        with self.assertRaises(ValueError):
            self.outbox.enqueue(
                event_key=self.message_event_key("event-stable-identity"),
                thread_id="43",
                thread_url="https://coconala.com/mypage/direct_message/43",
                observed_at=103,
            )
        with self.assertRaises(outbox_module.OutboxError):
            self.outbox.enqueue(
                event_key=self.message_event_key("event-stable-identity"),
                thread_id="42",
                thread_url="https://coconala.com/talkrooms/42",
                observed_at=104,
            )
        self.assertEqual(
            (
                self.db_value("SELECT COUNT(*) FROM connector_actions"),
                self.db_value("SELECT COUNT(*) FROM connector_events"),
            ),
            before,
        )
        self.assertEqual(self.outbox.get_action(original["action_id"])["thread_url"], original["thread_url"])

    def test_claim_fence_is_monotonic_and_stale_owner_is_rejected(self):
        action = self.enqueue()
        first = self.outbox.claim(owner="worker-a", now=200, lease_seconds=30)
        self.assertEqual(first["action_id"], action["action_id"])
        self.outbox.record_pre_click_failure(
            action["action_id"], owner="worker-a", fencing_token=first["fencing_token"], now=201
        )
        second = self.outbox.claim(owner="worker-b", now=202, lease_seconds=30)
        self.assertGreater(second["fencing_token"], first["fencing_token"])
        with self.assertRaises(outbox_module.StaleFence):
            self.outbox.prepare_intent(
                action["action_id"], owner="worker-a", fencing_token=first["fencing_token"],
                outgoing_body="stale body", now=203,
            )

    def test_boolean_ids_tokens_revisions_and_leases_never_authorize_state_changes(self):
        action = self.enqueue()
        with self.assertRaises(ValueError):
            self.outbox.get_action(True)
        with self.assertRaises(ValueError):
            self.outbox.claim(owner="worker-a", now=200, lease_seconds=60, action_id=True)
        with self.assertRaises(ValueError):
            self.outbox.claim(owner="worker-a", now=200, lease_seconds=True)
        self.assertEqual(self.outbox.get_action(action["action_id"])["state"], "pending")

        claim = self.outbox.claim(owner="worker-a", now=200, lease_seconds=60)
        with self.assertRaises(ValueError):
            self.outbox.prepare_intent(
                True, owner="worker-a", fencing_token=claim["fencing_token"],
                outgoing_body="must not bind bool action ID", now=201,
            )
        with self.assertRaises(ValueError):
            self.outbox.prepare_intent(
                action["action_id"], owner="worker-a", fencing_token=True,
                outgoing_body="must not bind bool fence", now=201,
            )
        self.assertEqual(self.db_value("SELECT COUNT(*) FROM connector_intents"), 0)

        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="valid intent", now=201,
        )
        with self.assertRaises(ValueError):
            self.outbox.mark_click_started(
                action["action_id"], True, owner="worker-a",
                fencing_token=claim["fencing_token"], now=202,
            )
        with self.assertRaises(ValueError):
            self.outbox.supervisor_recover_stopped_owner(
                action["action_id"], expected_owner="worker-a", expected_fencing_token=True,
                owner_stopped=True, now=202,
            )
        self.assertEqual(intent["state"], "prepared")
        self.assertEqual(self.outbox.get_action(action["action_id"])["state"], "intent_ready")

    def test_expired_pre_click_owner_requires_supervisor_stop_proof_before_requeue(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=210, lease_seconds=10)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="prepared but not clicked", now=211,
        )
        self.assertIsNone(
            self.outbox.claim(
                owner="worker-b", now=221, lease_seconds=10, action_id=action["action_id"]
            )
        )
        with self.assertRaises(outbox_module.InvalidTransition):
            self.outbox.supervisor_recover_stopped_owner(
                action["action_id"], expected_owner="worker-a",
                expected_fencing_token=claim["fencing_token"], owner_stopped=False, now=222,
            )
        with self.assertRaises(outbox_module.StaleFence):
            self.outbox.supervisor_recover_stopped_owner(
                action["action_id"], expected_owner="worker-a",
                expected_fencing_token=claim["fencing_token"] + 1, owner_stopped=True, now=223,
            )
        recovered = self.outbox.supervisor_recover_stopped_owner(
            action["action_id"], expected_owner="worker-a",
            expected_fencing_token=claim["fencing_token"], owner_stopped=True, now=224,
        )
        self.assertEqual((recovered["state"], recovered["owner"]), ("pending", None))
        with self.assertRaises((outbox_module.StaleFence, outbox_module.InvalidTransition)):
            self.outbox.mark_click_started(
                action["action_id"], intent["revision"], owner="worker-a",
                fencing_token=claim["fencing_token"], now=225,
            )

    def test_expired_pre_click_owner_can_only_release_its_own_identity(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=226, lease_seconds=10)
        self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="prepared but expired", now=227,
        )
        with self.assertRaises(outbox_module.StaleFence):
            self.outbox.record_pre_click_failure(
                action["action_id"], owner="worker-a",
                fencing_token=claim["fencing_token"] + 1, now=237,
            )
        unchanged = self.outbox.get_action(action["action_id"])
        self.assertEqual((unchanged["state"], unchanged["owner"]), ("intent_ready", "worker-a"))
        released = self.outbox.record_pre_click_failure(
            action["action_id"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=238,
        )
        self.assertEqual((released["state"], released["owner"]), ("pending", None))

    def test_expired_slot_blocks_other_threads_until_supervisor_resolves_owner(self):
        first = self.enqueue(message_id="event-expired-a", thread_id="expired-a")
        second = self.enqueue(message_id="event-expired-b", thread_id="expired-b")
        claim = self.outbox.claim(
            owner="worker-a", now=230, lease_seconds=10, action_id=first["action_id"]
        )
        with self.assertRaises(outbox_module.ConnectorBusy):
            self.outbox.claim(
                owner="worker-b", now=241, lease_seconds=10, action_id=second["action_id"]
            )
        self.outbox.supervisor_recover_stopped_owner(
            first["action_id"], expected_owner="worker-a",
            expected_fencing_token=claim["fencing_token"], owner_stopped=True, now=242,
        )
        claimed_second = self.outbox.claim(
            owner="worker-b", now=243, lease_seconds=10, action_id=second["action_id"]
        )
        self.assertEqual(claimed_second["action_id"], second["action_id"])

    def test_two_connections_racing_different_threads_get_one_connector_slot(self):
        first_action = self.enqueue(message_id="event-a", thread_id="thread-a")
        second_action = self.enqueue(message_id="event-b", thread_id="thread-b")
        barrier = threading.Barrier(2)

        def race(action_id, owner):
            independent = outbox_module.ConnectorOutbox(self.db_path, self.manifest_path)
            barrier.wait()
            try:
                return independent.claim(owner=owner, now=300, lease_seconds=60, action_id=action_id)
            except outbox_module.ConnectorBusy:
                return "busy"

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(
                lambda args: race(*args),
                ((first_action["action_id"], "worker-a"), (second_action["action_id"], "worker-b")),
            ))

        self.assertEqual(sum(result == "busy" for result in results), 1)
        claimed = [result for result in results if isinstance(result, dict)]
        self.assertEqual(len(claimed), 1)
        self.assertEqual(self.db_value("SELECT COUNT(*) FROM connector_slots WHERE lease_until > 300"), 1)

    def test_disabled_or_revoked_manifest_blocks_claim_and_click_authorization(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=400, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="bounded reply", now=401,
        )
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["revoked_at"] = "revoked"
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(outbox_module.ConnectorDisabled):
            self.outbox.mark_click_started(
                action["action_id"], intent["revision"], owner="worker-a",
                fencing_token=claim["fencing_token"], now=402,
            )
        manifest["revoked_at"] = None
        manifest["enabled"] = False
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(outbox_module.ConnectorDisabled):
            self.outbox.claim(owner="worker-b", now=500, lease_seconds=60)

    def test_manifest_boolean_values_cannot_impersonate_numeric_safety_limits(self):
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        original_window = manifest["max_consistency_window_seconds"]
        manifest["max_consistency_window_seconds"] = True
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(outbox_module.ConnectorDisabled):
            self.enqueue(message_id="event-bool-window")

        manifest["max_consistency_window_seconds"] = original_window
        manifest["rate_limit"]["max_concurrent_browser_tabs"] = True
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(outbox_module.ConnectorDisabled):
            self.enqueue(message_id="event-bool-tabs")

    def test_manifest_requires_authoritative_reply_reconciliation_contract(self):
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["reconciliation_mode"] = "best_effort"
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(outbox_module.ConnectorDisabled):
            self.enqueue(message_id="event-non-authoritative")

        manifest["reconciliation_mode"] = "authoritative_dom_readback"
        manifest["allowed_scope"] = [
            scope for scope in manifest["allowed_scope"] if scope != "reply"
        ]
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(outbox_module.ConnectorDisabled):
            self.enqueue(message_id="event-no-reply-scope")

    def test_intent_owner_fence_are_immutable_and_pre_click_failure_creates_new_revision(self):
        action = self.enqueue()
        first_claim = self.outbox.claim(owner="worker-a", now=600, lease_seconds=60)
        raw_body = "  private customer reply\twith details  "
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=first_claim["fencing_token"],
            outgoing_body=raw_body, now=601,
        )
        self.assertEqual(intent["outgoing_hash"], outbox_module.outgoing_sha256(raw_body))
        with self.assertRaises(outbox_module.ImmutableIntent):
            self.outbox.prepare_intent(
                action["action_id"], owner="worker-a", fencing_token=first_claim["fencing_token"],
                outgoing_body="different reply", now=602,
            )
        failed = self.outbox.record_pre_click_failure(
            action["action_id"], owner="worker-a", fencing_token=first_claim["fencing_token"], now=603
        )
        self.assertEqual((failed["state"], failed["revision"]), ("pending", 2))
        second_claim = self.outbox.claim(owner="worker-b", now=604, lease_seconds=60)
        retry_intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-b", fencing_token=second_claim["fencing_token"],
            outgoing_body=raw_body, now=605,
        )
        self.assertEqual(retry_intent["revision"], 2)
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.row_factory = sqlite3.Row
            audit_rows = [
                dict(row) for row in connection.execute(
                    """SELECT revision,owner_id,fencing_token,state FROM connector_intents
                       WHERE action_id=? ORDER BY revision""",
                    (action["action_id"],),
                )
            ]
        self.assertEqual(
            audit_rows,
            [
                {
                    "revision": 1,
                    "owner_id": "worker-a",
                    "fencing_token": first_claim["fencing_token"],
                    "state": "superseded",
                },
                {
                    "revision": 2,
                    "owner_id": "worker-b",
                    "fencing_token": second_claim["fencing_token"],
                    "state": "prepared",
                },
            ],
        )
        with self.assertRaises(outbox_module.StaleFence):
            self.outbox.mark_click_started(
                action["action_id"], retry_intent["revision"], owner="worker-a",
                fencing_token=first_claim["fencing_token"], now=606,
            )
        self.outbox.mark_click_started(
            action["action_id"], retry_intent["revision"], owner="worker-b",
            fencing_token=second_claim["fencing_token"], now=606,
        )
        with closing(sqlite3.connect(self.db_path)) as connection:
            dump = "\n".join(connection.iterdump())
        self.assertNotIn(raw_body.strip(), dump)
        self.assertNotIn("private customer reply", dump)

    def test_prepare_intent_rejects_body_that_normalizes_to_empty(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=610, lease_seconds=60)
        with self.assertRaises(ValueError):
            self.outbox.prepare_intent(
                action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
                outgoing_body=" \t\r\n\u00a0 ", now=611,
            )
        self.assertEqual(self.db_value("SELECT COUNT(*) FROM connector_intents"), 0)
        self.assertEqual(self.outbox.get_action(action["action_id"])["state"], "claimed")

    def test_new_event_after_pre_click_intent_supersedes_revision_and_stale_fence(self):
        action = self.enqueue(message_id="event-before-intent")
        claim = self.outbox.claim(owner="worker-a", now=650, lease_seconds=60)
        first_intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="reply covering event one", now=651,
        )
        coalesced = self.outbox.enqueue(
            event_key=self.message_event_key("event-arrived-before-click"),
            thread_id="42",
            thread_url=action["thread_url"],
            observed_at=652,
        )
        self.assertEqual(coalesced["action_id"], action["action_id"])
        self.assertEqual((coalesced["state"], coalesced["revision"]), ("pending", 2))
        with self.assertRaises((outbox_module.StaleFence, outbox_module.InvalidTransition)):
            self.outbox.mark_click_started(
                action["action_id"], first_intent["revision"], owner="worker-a",
                fencing_token=claim["fencing_token"], now=653,
            )
        next_claim = self.outbox.claim(owner="worker-b", now=654, lease_seconds=60)
        next_intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-b", fencing_token=next_claim["fencing_token"],
            outgoing_body="reply covering events one and two", now=655,
        )
        self.assertEqual(next_intent["revision"], 2)
        self.assertEqual(
            self.db_value(
                "SELECT state FROM connector_intents WHERE action_id=? AND revision=1",
                (action["action_id"],),
            ),
            "superseded",
        )

    def test_new_event_after_pre_click_failure_supersedes_stale_prepared_intent(self):
        action = self.enqueue(message_id="event-before-pre-click-failure")
        claim = self.outbox.claim(owner="worker-a", now=656, lease_seconds=60)
        first_intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="reply covering only the first event", now=657,
        )
        self.outbox.record_pre_click_failure(
            action["action_id"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=658,
        )
        coalesced = self.outbox.enqueue(
            event_key=self.message_event_key("event-after-pre-click-failure"), thread_id="42",
            thread_url=action["thread_url"], observed_at=659,
        )
        self.assertEqual(coalesced["action_id"], action["action_id"])
        self.assertEqual((coalesced["state"], coalesced["revision"]), ("pending", 3))
        self.assertEqual(
            self.db_value(
                "SELECT state FROM connector_intents WHERE action_id=? AND revision=?",
                (action["action_id"], first_intent["revision"]),
            ),
            "superseded",
        )
        next_claim = self.outbox.claim(owner="worker-b", now=660, lease_seconds=60)
        next_intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-b", fencing_token=next_claim["fencing_token"],
            outgoing_body="reply covering both events", now=661,
        )
        self.assertEqual(next_intent["revision"], 3)

    def test_new_event_after_retry_claim_supersedes_non_current_prepared_intent(self):
        action = self.enqueue(message_id="event-before-retry-claim")
        first_claim = self.outbox.claim(owner="worker-a", now=662, lease_seconds=60)
        first_intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a",
            fencing_token=first_claim["fencing_token"], outgoing_body="stale prepared body", now=663,
        )
        self.outbox.record_pre_click_failure(
            action["action_id"], owner="worker-a",
            fencing_token=first_claim["fencing_token"], now=664,
        )
        retry_claim = self.outbox.claim(owner="worker-b", now=665, lease_seconds=60)
        coalesced = self.outbox.enqueue(
            event_key=self.message_event_key("event-during-retry-claim"), thread_id="42",
            thread_url=action["thread_url"], observed_at=666,
        )
        self.assertEqual((coalesced["state"], coalesced["revision"]), ("pending", 3))
        self.assertEqual(
            self.db_value(
                "SELECT state FROM connector_intents WHERE action_id=? AND revision=?",
                (action["action_id"], first_intent["revision"]),
            ),
            "superseded",
        )
        self.assertEqual(
            self.db_value(
                """SELECT COUNT(*) FROM connector_intents
                   WHERE action_id=? AND state='prepared' AND revision<>?""",
                (action["action_id"], coalesced["revision"]),
            ),
            0,
        )
        with self.assertRaises(outbox_module.StaleFence):
            self.outbox.prepare_intent(
                action["action_id"], owner="worker-b",
                fencing_token=retry_claim["fencing_token"], outgoing_body="stale retry", now=667,
            )

    def test_new_event_after_claim_before_prepare_invalidates_revision_and_fence(self):
        action = self.enqueue(message_id="event-before-claim")
        claim = self.outbox.claim(owner="worker-a", now=660, lease_seconds=60)
        coalesced = self.outbox.enqueue(
            event_key=self.message_event_key("event-after-claim-before-prepare"),
            thread_id="42",
            thread_url=action["thread_url"],
            observed_at=661,
        )
        self.assertEqual((coalesced["state"], coalesced["revision"]), ("pending", 2))
        with self.assertRaises(outbox_module.StaleFence):
            self.outbox.prepare_intent(
                action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
                outgoing_body="stale reply", now=662,
            )
        next_claim = self.outbox.claim(owner="worker-b", now=663, lease_seconds=60)
        self.assertEqual(next_claim["action_id"], action["action_id"])
        self.assertGreater(next_claim["fencing_token"], claim["fencing_token"])

    def test_intent_ready_without_immutable_intent_fails_closed(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=670, lease_seconds=60)
        self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="prepared reply", now=671,
        )
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute("DELETE FROM connector_intents WHERE action_id=?", (action["action_id"],))
            connection.commit()
        with self.assertRaises(outbox_module.InvalidTransition):
            self.outbox.enqueue(
                event_key=self.message_event_key("event-with-corrupt-intent-state"),
                thread_id="42",
                thread_url=action["thread_url"],
                observed_at=672,
            )
        unchanged = self.outbox.get_action(action["action_id"])
        self.assertEqual((unchanged["state"], unchanged["revision"]), ("intent_ready", 1))

    def test_click_started_and_ambiguous_ack_never_blind_resend(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=700, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="reply once", now=701,
        )
        marked = self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=702,
        )
        self.assertEqual(marked["state"], "reconcile_pending")
        with self.assertRaises(outbox_module.InvalidTransition):
            self.outbox.mark_click_started(
                action["action_id"], intent["revision"], owner="worker-a",
                fencing_token=claim["fencing_token"], now=703,
            )
        self.outbox.record_delivery_unknown(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"], now=704
        )
        self.assertIsNone(self.outbox.claim(owner="worker-b", now=705, lease_seconds=60))
        with self.assertRaises((outbox_module.StaleFence, outbox_module.InvalidTransition)):
            self.outbox.mark_click_started(
                action["action_id"], intent["revision"], owner="worker-a",
                fencing_token=claim["fencing_token"], now=706,
            )

    def test_expired_post_click_owner_can_only_quiesce_its_own_identity(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=707, lease_seconds=10)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="clicked but expired", now=708,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=709, lease_seconds=10,
        )
        with self.assertRaises(outbox_module.StaleFence):
            self.outbox.record_delivery_unknown(
                action["action_id"], owner="worker-b",
                fencing_token=claim["fencing_token"], now=720,
            )
        unchanged = self.outbox.get_action(action["action_id"])
        self.assertEqual(
            (unchanged["state"], unchanged["owner"]), ("reconcile_pending", "worker-a")
        )
        released = self.outbox.record_delivery_unknown(
            action["action_id"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=721,
        )
        self.assertEqual((released["state"], released["owner"]), ("reconcile_pending", None))

    def test_backdated_click_and_old_same_hash_evidence_cannot_verify(self):
        action = self.enqueue(observed_at=100)
        claim = self.outbox.claim(owner="worker-a", now=110, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="same hash as an older message", now=120,
        )
        with self.assertRaises(outbox_module.InvalidTransition):
            self.outbox.mark_click_started(
                action["action_id"], intent["revision"], owner="worker-a",
                fencing_token=claim["fencing_token"], now=1,
            )
        unchanged = self.outbox.get_action(action["action_id"])
        self.assertEqual(unchanged["state"], "intent_ready")
        self.assertIsNone(
            self.db_value(
                "SELECT click_started_at FROM connector_intents WHERE action_id=? AND revision=?",
                (action["action_id"], intent["revision"]),
            )
        )
        with self.assertRaises(outbox_module.InvalidTransition):
            self.outbox.reconcile(
                action["action_id"], thread_url=action["thread_url"],
                outgoing_hash=intent["outgoing_hash"], seller_sent_at=2, last_sender="seller",
                observed_at=121, authoritative_absent=False,
            )
        self.assertIsNone(self.outbox.get_action(action["action_id"])["verified_outgoing_hash"])

    def test_lifecycle_timestamps_reject_boolean_values(self):
        with self.assertRaises(ValueError):
            self.enqueue(message_id="event-bool-time", observed_at=True)
        action = self.enqueue()
        with self.assertRaises(ValueError):
            self.outbox.claim(owner="worker-a", now=True, lease_seconds=60)
        self.assertEqual(self.outbox.get_action(action["action_id"])["state"], "pending")

    def test_event_after_click_waits_in_distinct_next_action_until_prior_is_verified(self):
        first_action = self.enqueue(message_id="event-before-click")
        claim = self.outbox.claim(owner="worker-a", now=720, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            first_action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="first reply", now=721,
        )
        self.outbox.mark_click_started(
            first_action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=722,
        )
        next_action = self.outbox.enqueue(
            event_key=self.message_event_key("event-after-click"),
            thread_id="42",
            thread_url=first_action["thread_url"],
            observed_at=723,
        )
        self.assertNotEqual(next_action["action_id"], first_action["action_id"])
        self.assertEqual(next_action["state"], "blocked")
        duplicate = self.outbox.enqueue(
            event_key=self.message_event_key("event-after-click"),
            thread_id="42",
            thread_url=first_action["thread_url"],
            observed_at=724,
        )
        self.assertEqual(duplicate["action_id"], next_action["action_id"])
        self.outbox.record_delivery_unknown(
            first_action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"], now=725
        )
        self.assertIsNone(self.outbox.claim(owner="worker-b", now=726, lease_seconds=60))
        completed = self.outbox.reconcile(
            first_action["action_id"], thread_url=first_action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=723, last_sender="buyer",
            observed_at=727, authoritative_absent=False,
        )
        self.assertEqual(completed["state"], "replied")
        promoted = self.outbox.get_action(next_action["action_id"])
        self.assertEqual(promoted["state"], "pending")
        claimed_next = self.outbox.claim(owner="worker-b", now=728, lease_seconds=60)
        self.assertEqual(claimed_next["action_id"], next_action["action_id"])
        duplicate_after_promotion = self.outbox.enqueue(
            event_key=self.message_event_key("event-after-click"),
            thread_id="42",
            thread_url=first_action["thread_url"],
            observed_at=729,
        )
        self.assertEqual(duplicate_after_promotion["action_id"], next_action["action_id"])

    def test_event_after_authoritative_absence_stays_distinct_from_resend_revision(self):
        first_action = self.enqueue(message_id="event-before-absent")
        claim = self.outbox.claim(owner="worker-a", now=740, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            first_action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="first uncertain reply", now=741,
        )
        self.outbox.mark_click_started(
            first_action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=742,
        )
        self.outbox.record_delivery_unknown(
            first_action["action_id"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=743,
        )
        resend = self.outbox.reconcile(
            first_action["action_id"], thread_url=first_action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender=None,
            observed_at=950, authoritative_absent=True,
        )
        self.assertEqual((resend["state"], resend["revision"]), ("pending", 2))
        next_action = self.outbox.enqueue(
            event_key=self.message_event_key("event-after-absent"), thread_id="42",
            thread_url=first_action["thread_url"], observed_at=951,
        )
        self.assertNotEqual(next_action["action_id"], first_action["action_id"])
        self.assertEqual(next_action["state"], "blocked")
        coalesced = self.outbox.enqueue(
            event_key=self.message_event_key("event-after-absent-2"), thread_id="42",
            thread_url=first_action["thread_url"], observed_at=952,
        )
        self.assertEqual(coalesced["action_id"], next_action["action_id"])
        self.assertEqual(
            (self.outbox.get_action(first_action["action_id"])["state"],
             self.outbox.get_action(first_action["action_id"])["revision"]),
            ("pending", 2),
        )

    def test_absence_requires_authority_and_window_then_creates_only_one_revision(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=800, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="possibly sent", now=801,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=802,
        )
        self.outbox.record_delivery_unknown(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"], now=803
        )
        with self.assertRaises(outbox_module.ConsistencyWindowOpen):
            self.outbox.reconcile(
                action["action_id"], thread_url=action["thread_url"],
                outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender=None,
                observed_at=900, authoritative_absent=True,
            )
        unchanged = self.outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender=None,
            observed_at=1000, authoritative_absent=False,
        )
        self.assertEqual((unchanged["state"], unchanged["revision"]), ("reconcile_pending", 1))
        superseded = self.outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender=None,
            observed_at=1000, authoritative_absent=True,
        )
        repeated = self.outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender=None,
            observed_at=1001, authoritative_absent=True,
        )
        self.assertEqual((superseded["state"], superseded["revision"]), ("pending", 2))
        self.assertEqual(repeated["revision"], 2)
        self.assertEqual(self.db_value("SELECT COUNT(*) FROM connector_intents"), 1)

    def test_server_rejection_blocks_after_window_until_new_event_reactivates_fresh_revision(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=900, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="server rejected reply", now=901,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=902,
        )
        self.outbox.record_delivery_unknown(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            now=903, rejection_code="submit_rejected_sending_unavailable",
        )

        with self.assertRaises(outbox_module.ConsistencyWindowOpen):
            self.outbox.reconcile(
                action["action_id"], thread_url=action["thread_url"],
                outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender="buyer",
                observed_at=1000, authoritative_absent=True,
            )
        blocked = self.outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender="buyer",
            observed_at=1023, authoritative_absent=True,
        )
        self.assertEqual((blocked["state"], blocked["revision"]), ("blocked", 1))
        self.assertIsNone(
            self.outbox.claim(
                owner="blind-retry", now=1024, lease_seconds=60,
                action_id=action["action_id"],
            )
        )
        self.assertEqual(
            self.db_value(
                "SELECT rejection_code FROM connector_intents WHERE action_id=? AND revision=?",
                (action["action_id"], intent["revision"]),
            ),
            "submit_rejected_sending_unavailable",
        )

        duplicate = self.enqueue(message_id="message-1", observed_at=1025)
        self.assertEqual((duplicate["state"], duplicate["revision"]), ("blocked", 1))
        reactivated = self.enqueue(message_id="message-2", observed_at=1026)
        self.assertEqual(reactivated["action_id"], action["action_id"])
        self.assertEqual((reactivated["state"], reactivated["revision"]), ("pending", 2))
        next_claim = self.outbox.claim(
            owner="new-event-worker", now=1027, lease_seconds=60,
            action_id=action["action_id"],
        )
        next_intent = self.outbox.prepare_intent(
            action["action_id"], owner="new-event-worker",
            fencing_token=next_claim["fencing_token"],
            outgoing_body="reply covering the new event", now=1028,
        )
        self.assertEqual(next_intent["revision"], 2)

    def test_new_event_during_rejection_window_reactivates_without_blocked_collision(self):
        action = self.enqueue(message_id="event-before-rejection")
        claim = self.outbox.claim(owner="worker-a", now=1030, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="rejected before a newer buyer event", now=1031,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1032,
        )
        self.outbox.record_delivery_unknown(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            now=1033, rejection_code="submit_rejected_sending_unavailable",
        )
        successor = self.outbox.enqueue(
            event_key=self.message_event_key("event-during-rejection-window"),
            thread_id="42", thread_url=action["thread_url"], observed_at=1034,
        )
        self.assertNotEqual(successor["action_id"], action["action_id"])
        self.assertEqual(successor["state"], "blocked")

        reactivated = self.outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender="buyer",
            observed_at=1153, authoritative_absent=True,
        )

        self.assertEqual(
            (reactivated["state"], reactivated["revision"], reactivated["new_event_reactivated"]),
            ("pending", 2, True),
        )
        self.assertEqual(
            self.db_value(
                "SELECT COUNT(*) FROM connector_actions WHERE platform='coconala' AND thread_id='42'"
            ),
            1,
        )
        self.assertEqual(
            self.db_value(
                "SELECT COUNT(*) FROM connector_events WHERE action_id=?",
                (action["action_id"],),
            ),
            2,
        )
        self.assertEqual(
            self.db_value(
                "SELECT state FROM connector_intents WHERE action_id=? AND revision=1",
                (action["action_id"],),
            ),
            "superseded",
        )
        next_claim = self.outbox.claim(
            owner="new-event-worker", now=1154, lease_seconds=60,
            action_id=action["action_id"],
        )
        self.assertEqual((next_claim["state"], next_claim["revision"]), ("claimed", 2))

    def test_stale_rejection_read_cannot_consume_a_later_successor_event(self):
        action = self.enqueue(message_id="event-before-stale-read")
        claim = self.outbox.claim(owner="worker-a", now=1160, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="rejected before a future event", now=1161,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1162,
        )
        self.outbox.record_delivery_unknown(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            now=1163, rejection_code="submit_rejected_sending_unavailable",
        )
        successor = self.outbox.enqueue(
            event_key=self.message_event_key("event-after-authoritative-read"),
            thread_id="42", thread_url=action["thread_url"], observed_at=1284,
        )
        coalesced = self.outbox.enqueue(
            event_key=self.message_event_key("later-event-after-authoritative-read"),
            thread_id="42", thread_url=action["thread_url"], observed_at=1285,
        )
        self.assertEqual(coalesced["action_id"], successor["action_id"])
        self.assertEqual(coalesced["updated_at"], 1285)

        with self.assertRaises(outbox_module.InvalidTransition):
            self.outbox.reconcile(
                action["action_id"], thread_url=action["thread_url"],
                outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender="buyer",
                observed_at=1284, authoritative_absent=True,
            )

        self.assertEqual(
            self.outbox.get_action(action["action_id"])["state"],
            "reconcile_pending",
        )
        self.assertEqual(self.outbox.get_action(successor["action_id"])["state"], "blocked")
        self.assertEqual(
            self.db_value(
                "SELECT state FROM connector_intents WHERE action_id=? AND revision=1",
                (action["action_id"],),
            ),
            "reconcile_pending",
        )
        self.assertEqual(
            self.db_value(
                "SELECT action_id FROM connector_events WHERE event_key=?",
                (self.message_event_key("event-after-authoritative-read"),),
            ),
            successor["action_id"],
        )

    def test_server_rejection_code_is_bounded_and_raw_text_is_never_persisted(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=1050, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="bounded rejection", now=1051,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1052,
        )
        raw = "現在メッセージを送信することができません SECRET"
        with self.assertRaises(ValueError):
            self.outbox.record_delivery_unknown(
                action["action_id"], owner="worker-a",
                fencing_token=claim["fencing_token"], now=1053,
                rejection_code=raw,
            )
        with closing(sqlite3.connect(self.db_path)) as connection:
            dump = "\n".join(connection.iterdump())
        self.assertNotIn(raw, dump)

    def test_authoritative_absent_requires_exact_boolean_and_rolls_back(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=1000, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="boolean boundary reply", now=1001,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1002,
        )
        self.outbox.record_delivery_unknown(
            action["action_id"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1003,
        )
        for invalid_flag in ("false", 1):
            with self.subTest(invalid_flag=invalid_flag), self.assertRaises(ValueError):
                self.outbox.reconcile(
                    action["action_id"], thread_url=action["thread_url"],
                    outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender=None,
                    observed_at=1123, authoritative_absent=invalid_flag,
                )
            unchanged = self.outbox.get_action(action["action_id"])
            self.assertEqual((unchanged["state"], unchanged["revision"]), ("reconcile_pending", 1))

    def test_matching_hash_thread_and_seller_time_completes_even_when_buyer_is_now_last(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=1100, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="verified reply", now=1101,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1102,
        )
        completed = self.outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=1103, last_sender="buyer",
            observed_at=1104, authoritative_absent=False,
        )
        self.assertEqual(completed["state"], "replied")
        self.assertEqual(completed["verified_outgoing_hash"], intent["outgoing_hash"])
        self.assertEqual(completed["seller_sent_at"], 1103)
        self.assertEqual(completed["last_sender"], "buyer")

    def test_reconcile_canonicalizes_thread_url_and_never_persists_query_secret(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=1150, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="canonical evidence", now=1151,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1152,
        )
        completed = self.outbox.reconcile(
            action["action_id"],
            thread_url=action["thread_url"] + "?token=RECONCILE_SECRET#fragment",
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=1153, last_sender="seller",
            observed_at=1154, authoritative_absent=False,
        )
        self.assertEqual(completed["state"], "replied")
        self.assertEqual(completed["verified_thread_url"], action["thread_url"])
        with closing(sqlite3.connect(self.db_path)) as connection:
            dump = "\n".join(connection.iterdump())
        self.assertNotIn("RECONCILE_SECRET", dump)

    def test_matching_hash_with_seller_time_before_click_does_not_verify_current_intent(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=1200, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="new reply with repeated hash", now=1201,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1202,
        )
        stale_presence = self.outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=1201, last_sender="seller",
            observed_at=1203, authoritative_absent=False,
        )
        self.assertEqual(stale_presence["state"], "reconcile_pending")
        current_presence = self.outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=1202, last_sender="buyer",
            observed_at=1204, authoritative_absent=False,
        )
        self.assertEqual(current_presence["state"], "replied")

    def test_matching_hash_with_seller_time_after_observation_does_not_verify(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=1300, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="future timestamp evidence", now=1301,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1302,
        )
        future_presence = self.outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=1305, last_sender="seller",
            observed_at=1304, authoritative_absent=False,
        )
        self.assertEqual(future_presence["state"], "reconcile_pending")
        current_presence = self.outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=1304, last_sender="seller",
            observed_at=1304, authoritative_absent=False,
        )
        self.assertEqual(current_presence["state"], "replied")

    def test_authoritative_absence_requires_executor_quiescence_after_click(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=1400, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="late click protected", now=1401,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1402,
        )
        with self.assertRaises(outbox_module.ExecutorStillActive):
            self.outbox.reconcile(
                action["action_id"], thread_url=action["thread_url"],
                outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender=None,
                observed_at=1600, authoritative_absent=True,
            )
        unchanged = self.outbox.get_action(action["action_id"])
        self.assertEqual(unchanged["state"], "reconcile_pending")
        self.outbox.supervisor_recover_stopped_owner(
            action["action_id"], expected_owner="worker-a",
            expected_fencing_token=claim["fencing_token"], owner_stopped=True, now=1601,
        )
        retry = self.outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender=None,
            observed_at=1721, authoritative_absent=True,
        )
        self.assertEqual((retry["state"], retry["revision"]), ("pending", 2))
        next_claim = self.outbox.claim(
            owner="worker-b", now=1722, lease_seconds=60, action_id=action["action_id"]
        )
        self.assertGreater(next_claim["fencing_token"], claim["fencing_token"])
        with self.assertRaises((outbox_module.StaleFence, outbox_module.InvalidTransition)):
            self.outbox.mark_click_started(
                action["action_id"], intent["revision"], owner="worker-a",
                fencing_token=claim["fencing_token"], now=1723,
            )

    def test_authoritative_absence_observation_cannot_predate_executor_quiescence(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=1500, lease_seconds=200)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="stale absence evidence", now=1501,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1502,
        )
        self.outbox.supervisor_recover_stopped_owner(
            action["action_id"], expected_owner="worker-a",
            expected_fencing_token=claim["fencing_token"], owner_stopped=True, now=1601,
        )
        with self.assertRaises(outbox_module.InvalidTransition):
            self.outbox.reconcile(
                action["action_id"], thread_url=action["thread_url"],
                outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender=None,
                observed_at=1520, authoritative_absent=True,
            )
        self.assertEqual(self.outbox.get_action(action["action_id"])["state"], "reconcile_pending")

    def test_late_executor_quiescence_restarts_authoritative_absence_window(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=1400, lease_seconds=300)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="late stop window", now=1401,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1402,
        )
        self.outbox.supervisor_recover_stopped_owner(
            action["action_id"], expected_owner="worker-a",
            expected_fencing_token=claim["fencing_token"], owner_stopped=True, now=1601,
        )
        with self.assertRaises(outbox_module.ConsistencyWindowOpen):
            self.outbox.reconcile(
                action["action_id"], thread_url=action["thread_url"],
                outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender=None,
                observed_at=1602, authoritative_absent=True,
            )
        retry = self.outbox.reconcile(
            action["action_id"], thread_url=action["thread_url"],
            outgoing_hash=intent["outgoing_hash"], seller_sent_at=None, last_sender=None,
            observed_at=1721, authoritative_absent=True,
        )
        self.assertEqual((retry["state"], retry["revision"]), ("pending", 2))

    def test_supervisor_stopped_owner_releases_slot_but_never_requeues_clicked_action(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=1700, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="ambiguous after crash", now=1701,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1702,
        )
        recovered = self.outbox.supervisor_recover_stopped_owner(
            action["action_id"], expected_owner="worker-a",
            expected_fencing_token=claim["fencing_token"], owner_stopped=True, now=1703,
        )
        self.assertEqual((recovered["state"], recovered["owner"]), ("reconcile_pending", None))
        self.assertIsNone(
            self.outbox.claim(
                owner="worker-b", now=1704, lease_seconds=60, action_id=action["action_id"]
            )
        )
        self.assertIsNotNone(
            self.db_value(
                "SELECT executor_quiesced_at FROM connector_intents WHERE action_id=? AND revision=?",
                (action["action_id"], intent["revision"]),
            )
        )

    def test_executor_quiescence_timestamp_cannot_precede_click(self):
        action = self.enqueue()
        claim = self.outbox.claim(owner="worker-a", now=1800, lease_seconds=60)
        intent = self.outbox.prepare_intent(
            action["action_id"], owner="worker-a", fencing_token=claim["fencing_token"],
            outgoing_body="monotonic lifecycle evidence", now=1801,
        )
        self.outbox.mark_click_started(
            action["action_id"], intent["revision"], owner="worker-a",
            fencing_token=claim["fencing_token"], now=1802,
        )
        with self.assertRaises(outbox_module.InvalidTransition):
            self.outbox.record_delivery_unknown(
                action["action_id"], owner="worker-a",
                fencing_token=claim["fencing_token"], now=1801,
            )
        with self.assertRaises(outbox_module.InvalidTransition):
            self.outbox.supervisor_recover_stopped_owner(
                action["action_id"], expected_owner="worker-a",
                expected_fencing_token=claim["fencing_token"], owner_stopped=True, now=1801,
            )
        self.assertEqual(self.outbox.get_action(action["action_id"])["state"], "reconcile_pending")
        self.assertIsNone(
            self.db_value(
                "SELECT executor_quiesced_at FROM connector_intents WHERE action_id=? AND revision=?",
                (action["action_id"], intent["revision"]),
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
