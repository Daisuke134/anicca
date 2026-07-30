import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from job_search_loop.ledger import FenceError, Ledger


class OutcomeAttributionTests(unittest.TestCase):
    def test_attribution_cli_migrates_and_rebuilds_with_a_redacted_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "ledger.sqlite3"
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE applications (
                    id TEXT PRIMARY KEY,
                    company TEXT NOT NULL,
                    title TEXT NOT NULL,
                    canonical_url TEXT NOT NULL,
                    current_state TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                INSERT INTO applications VALUES
                  ('app-1', 'Private Employer', 'Secret Role',
                   'https://private.example/1', 'submitted',
                   '2026-07-01T00:00:00+00:00'),
                  ('app-2', 'Other Employer', 'Hidden Role',
                   'https://private.example/2', 'not_submitted',
                   '2026-07-02T00:00:00+00:00');
                """
            )
            connection.close()
            database.chmod(0o600)

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "job_search_loop.attribution",
                    "--ledger",
                    str(database),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(database.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                json.loads(result.stdout),
                {
                    "applications": 2,
                    "assignments": 2,
                    "capture_status": {"legacy_unavailable": 2},
                    "funnel_outcomes": 0,
                    "integrity": "ok",
                    "projection_rows": 0,
                    "strategy_generations": 1,
                    "unassigned_applications": 0,
                },
            )
            encoded = result.stdout.casefold()
            for private_value in (
                "private employer",
                "secret role",
                "https://",
            ):
                self.assertNotIn(private_value, encoded)

    def test_plain_application_gets_a_legacy_assignment_immediately(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            application_id = ledger.add_application(
                "Legacy",
                "AI Engineer",
                "https://jobs.example.com/immediate-legacy",
            )
            try:
                assignment = ledger.strategy_assignment(application_id)
            except KeyError:
                self.fail("application was committed without a strategy assignment")
            ledger.close()

            self.assertEqual(
                assignment["capture_status"],
                "legacy_unavailable",
            )
            self.assertEqual(
                assignment["strategy_generation_id"],
                "strategy-"
                "cfe167540848b3c22e5e8a77cc72004cd85e750da9c1ff92ea0ff1d42f821bf6",
            )

    def test_authoritative_funnel_outcome_is_content_addressed_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            generation_id = ledger.record_strategy_generation(
                {"auto_apply_threshold": 75}
            )
            application_id = ledger.add_attributed_application(
                "Example",
                "AI Engineer",
                "https://jobs.example.com/outcome",
                strategy_generation_id=generation_id,
                source="ashby",
                query_family="remote-ai",
                rank_config={"threshold": 75},
                role_family="applied_ai",
                material_variant="engineering_en_v2",
                message_variant="direct_en_v1",
                model_route="gpt-5.6-terra",
                prompt_sha256="a" * 64,
                material_sha256="b" * 64,
            )
            identity = {
                "application_id": application_id,
                "funnel_stage": "recruiter_response",
                "disposition": "positive",
                "evidence_source": "gmail",
                "evidence_sha256": "c" * 64,
                "occurred_at": "2026-07-30T01:00:00+00:00",
                "observed_at": "2026-07-30T01:05:00+00:00",
                "observation_policy_version": None,
            }
            expected_hash = hashlib.sha256(
                json.dumps(
                    identity,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            recorder = getattr(ledger, "record_funnel_outcome", None)
            self.assertIsNotNone(recorder)

            first = recorder(**identity)
            second = recorder(**identity)
            outcomes = ledger.funnel_outcomes(application_id)
            projection = ledger.strategy_outcome_projection()
            ledger.close()

            self.assertEqual(first, f"outcome-{expected_hash}")
            self.assertEqual(second, first)
            self.assertEqual(
                outcomes,
                [{"outcome_id": first, **identity}],
            )
            self.assertEqual(
                projection,
                [
                    {
                        "strategy_generation_id": generation_id,
                        "funnel_stage": "recruiter_response",
                        "positive_count": 1,
                        "negative_count": 0,
                        "resolved_count": 1,
                    }
                ],
            )

    def test_negative_outcome_requires_a_versioned_observation_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            application_id = ledger.add_application(
                "Example",
                "AI Engineer",
                "https://jobs.example.com/negative-window",
            )
            values = {
                "application_id": application_id,
                "funnel_stage": "recruiter_response",
                "disposition": "negative",
                "evidence_source": "gmail",
                "evidence_sha256": "d" * 64,
                "occurred_at": "2026-07-01T00:00:00+00:00",
                "observed_at": "2026-07-30T00:00:00+00:00",
            }

            with self.assertRaisesRegex(
                ValueError, "versioned observation policy"
            ):
                ledger.record_funnel_outcome(**values)
            outcome_id = ledger.record_funnel_outcome(
                **values,
                observation_policy_version="recruiter-silence-30d-v1",
            )
            outcomes = ledger.funnel_outcomes(application_id)
            ledger.close()

            self.assertEqual(len(outcomes), 1)
            self.assertEqual(outcomes[0]["outcome_id"], outcome_id)
            self.assertEqual(
                outcomes[0]["observation_policy_version"],
                "recruiter-silence-30d-v1",
            )

    def test_external_evidence_cannot_be_rebound_or_outcome_mutated(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            application_id = ledger.add_application(
                "Example",
                "AI Engineer",
                "https://jobs.example.com/immutable-outcome",
            )
            values = {
                "application_id": application_id,
                "funnel_stage": "screen",
                "disposition": "positive",
                "evidence_source": "calendar",
                "evidence_sha256": "e" * 64,
                "occurred_at": "2026-07-30T02:00:00+00:00",
                "observed_at": "2026-07-30T02:01:00+00:00",
            }
            outcome_id = ledger.record_funnel_outcome(**values)
            other_application_id = ledger.add_application(
                "Other",
                "AI Product Manager",
                "https://jobs.example.com/other-evidence-owner",
            )

            with self.assertRaises(FenceError):
                ledger.record_funnel_outcome(
                    **{**values, "application_id": other_application_id}
                )
            with self.assertRaises(sqlite3.IntegrityError):
                ledger.connection.execute(
                    """
                    UPDATE funnel_outcomes
                    SET funnel_stage = 'interview'
                    WHERE outcome_id = ?
                    """,
                    (outcome_id,),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                ledger.connection.execute(
                    "DELETE FROM funnel_outcomes WHERE outcome_id = ?",
                    (outcome_id,),
                )
            ledger.close()

    def test_one_external_receipt_can_prove_multiple_stages_for_one_application(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            application_id = ledger.add_application(
                "Example",
                "AI Engineer",
                "https://jobs.example.com/multi-stage-receipt",
            )
            common = {
                "application_id": application_id,
                "disposition": "positive",
                "evidence_source": "gmail",
                "evidence_sha256": "f" * 64,
                "occurred_at": "2026-07-30T03:00:00+00:00",
                "observed_at": "2026-07-30T03:01:00+00:00",
            }
            ledger.record_funnel_outcome(
                **common,
                funnel_stage="recruiter_response",
            )
            try:
                ledger.record_funnel_outcome(
                    **common,
                    funnel_stage="screen",
                )
            except FenceError as error:
                self.fail(f"one receipt could not prove two funnel stages: {error}")
            outcomes = ledger.funnel_outcomes(application_id)
            ledger.close()

            self.assertEqual(
                sorted(outcome["funnel_stage"] for outcome in outcomes),
                ["recruiter_response", "screen"],
            )

    def test_single_evidence_unique_schema_migrates_without_losing_outcomes(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "ledger.sqlite3"
            ledger = Ledger(database)
            application_id = ledger.add_application(
                "Example",
                "AI Engineer",
                "https://jobs.example.com/constraint-migration",
            )
            common = {
                "application_id": application_id,
                "disposition": "positive",
                "evidence_source": "gmail",
                "evidence_sha256": "f" * 64,
                "occurred_at": "2026-07-30T03:00:00+00:00",
                "observed_at": "2026-07-30T03:01:00+00:00",
            }
            ledger.record_funnel_outcome(
                **common,
                funnel_stage="recruiter_response",
            )
            ledger.close()

            connection = sqlite3.connect(database)
            connection.executescript(
                """
                DROP TRIGGER funnel_outcomes_no_update;
                DROP TRIGGER funnel_outcomes_no_delete;
                ALTER TABLE funnel_outcomes RENAME TO funnel_outcomes_current;
                CREATE TABLE funnel_outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    application_id TEXT NOT NULL REFERENCES applications(id),
                    funnel_stage TEXT NOT NULL,
                    disposition TEXT NOT NULL,
                    evidence_source TEXT NOT NULL,
                    evidence_sha256 TEXT NOT NULL UNIQUE,
                    occurred_at TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    observation_policy_version TEXT,
                    created_at TEXT NOT NULL
                );
                INSERT INTO funnel_outcomes
                SELECT * FROM funnel_outcomes_current;
                DROP TABLE funnel_outcomes_current;
                """
            )
            connection.close()

            migrated = Ledger(database)
            try:
                migrated.record_funnel_outcome(
                    **common,
                    funnel_stage="screen",
                )
            except sqlite3.IntegrityError as error:
                self.fail(f"single-evidence UNIQUE constraint survived migration: {error}")
            outcomes = migrated.funnel_outcomes(application_id)
            integrity = migrated.connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
            migrated.close()

            self.assertEqual(integrity, "ok")
            self.assertEqual(len(outcomes), 2)

    def test_strategy_outcome_projection_rebuilds_deterministically(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            baseline = ledger.record_strategy_generation(
                {"auto_apply_threshold": 75}
            )
            candidate = ledger.record_strategy_generation(
                {"auto_apply_threshold": 80},
                parent_generation_id=baseline,
                changed_field="auto_apply_threshold",
            )
            applications = []
            for index, generation_id in enumerate((baseline, candidate), start=1):
                applications.append(
                    ledger.add_attributed_application(
                        f"Example {index}",
                        "AI Engineer",
                        f"https://jobs.example.com/projection-{index}",
                        strategy_generation_id=generation_id,
                        source="ashby",
                        query_family="remote-ai",
                        rank_config={"threshold": 75 if index == 1 else 80},
                        role_family="applied_ai",
                        material_variant="engineering_en_v2",
                        message_variant="direct_en_v1",
                        model_route="gpt-5.6-terra",
                        prompt_sha256=f"{index}" * 64,
                        material_sha256=f"{index + 2}" * 64,
                    )
                )
            ledger.record_funnel_outcome(
                application_id=applications[0],
                funnel_stage="recruiter_response",
                disposition="positive",
                evidence_source="gmail",
                evidence_sha256="a" * 64,
                occurred_at="2026-07-01T00:00:00+00:00",
                observed_at="2026-07-01T00:01:00+00:00",
            )
            ledger.record_funnel_outcome(
                application_id=applications[1],
                funnel_stage="recruiter_response",
                disposition="negative",
                evidence_source="gmail",
                evidence_sha256="b" * 64,
                occurred_at="2026-07-01T00:00:00+00:00",
                observed_at="2026-07-30T00:00:00+00:00",
                observation_policy_version="recruiter-silence-30d-v1",
            )
            rebuild = getattr(
                ledger, "rebuild_strategy_outcome_projection", None
            )
            self.assertIsNotNone(rebuild)

            first = rebuild()
            ledger.connection.execute(
                """
                UPDATE strategy_outcome_projection
                SET positive_count = 999, resolved_count = 999
                """
            )
            second = rebuild()
            persisted = ledger.strategy_outcome_projection()
            ledger.close()

            expected_by_generation = {
                baseline: {
                    "positive_count": 1,
                    "negative_count": 0,
                    "resolved_count": 1,
                },
                candidate: {
                    "positive_count": 0,
                    "negative_count": 1,
                    "resolved_count": 1,
                },
            }
            expected = [
                {
                    "strategy_generation_id": generation_id,
                    "funnel_stage": "recruiter_response",
                    **expected_by_generation[generation_id],
                }
                for generation_id in sorted(expected_by_generation)
            ]
            self.assertEqual(first, expected)
            self.assertEqual(second, expected)
            self.assertEqual(persisted, expected)

    def test_attributed_application_persists_exact_strategy_values_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            generation_id = ledger.record_strategy_generation(
                {
                    "auto_apply_threshold": 75,
                    "role_families": ["applied_ai"],
                }
            )
            add_attributed = getattr(ledger, "add_attributed_application", None)
            self.assertIsNotNone(add_attributed)

            application_id = add_attributed(
                "Example",
                "Applied AI Engineer",
                "https://jobs.example.com/attributed",
                strategy_generation_id=generation_id,
                source="ashby",
                query_family="remote-applied-ai",
                rank_config={"threshold": 75, "weights_version": 3},
                role_family="applied_ai",
                material_variant="engineering_en_v2",
                message_variant="direct_en_v1",
                model_route="gpt-5.6-terra",
                prompt_sha256="a" * 64,
                material_sha256="b" * 64,
            )
            assignment = ledger.strategy_assignment(application_id)
            ledger.close()

            self.assertEqual(
                assignment,
                {
                    "application_id": application_id,
                    "strategy_generation_id": generation_id,
                    "capture_status": "captured",
                    "source": "ashby",
                    "query_family": "remote-applied-ai",
                    "rank_config": {"threshold": 75, "weights_version": 3},
                    "role_family": "applied_ai",
                    "material_variant": "engineering_en_v2",
                    "message_variant": "direct_en_v1",
                    "model_route": "gpt-5.6-terra",
                    "prompt_sha256": "a" * 64,
                    "material_sha256": "b" * 64,
                },
            )

    def test_assignment_replay_is_idempotent_and_conflicting_rebind_is_fenced(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            generation_id = ledger.record_strategy_generation(
                {"auto_apply_threshold": 75}
            )
            arguments = {
                "strategy_generation_id": generation_id,
                "source": "ashby",
                "query_family": "remote-ai",
                "rank_config": {"threshold": 75},
                "role_family": "applied_ai",
                "material_variant": "engineering_en_v2",
                "message_variant": "direct_en_v1",
                "model_route": "gpt-5.6-terra",
                "prompt_sha256": "a" * 64,
                "material_sha256": "b" * 64,
            }
            first = ledger.add_attributed_application(
                "Example",
                "AI Engineer",
                "https://jobs.example.com/idempotent",
                **arguments,
            )
            try:
                second = ledger.add_attributed_application(
                    "Example",
                    "AI Engineer",
                    "https://jobs.example.com/idempotent?utm_source=replay",
                    **arguments,
                )
            except sqlite3.IntegrityError as error:
                self.fail(f"exact assignment replay was not idempotent: {error}")

            with self.assertRaises(FenceError):
                ledger.add_attributed_application(
                    "Example",
                    "AI Engineer",
                    "https://jobs.example.com/idempotent",
                    **{**arguments, "source": "workday"},
                )
            assignment_count = ledger.connection.execute(
                """
                SELECT COUNT(*)
                FROM application_strategy_assignments
                WHERE application_id = ?
                """,
                (first,),
            ).fetchone()[0]
            ledger.close()

            self.assertEqual(second, first)
            self.assertEqual(assignment_count, 1)

    def test_strategy_assignments_cannot_be_updated_or_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            generation_id = ledger.record_strategy_generation(
                {"auto_apply_threshold": 75}
            )
            application_id = ledger.add_attributed_application(
                "Example",
                "AI Engineer",
                "https://jobs.example.com/immutable-assignment",
                strategy_generation_id=generation_id,
                source="ashby",
                query_family="remote-ai",
                rank_config={"threshold": 75},
                role_family="applied_ai",
                material_variant="engineering_en_v2",
                message_variant="direct_en_v1",
                model_route="gpt-5.6-terra",
                prompt_sha256="a" * 64,
                material_sha256="b" * 64,
            )

            with self.assertRaises(sqlite3.IntegrityError):
                ledger.connection.execute(
                    """
                    UPDATE application_strategy_assignments
                    SET source = 'workday'
                    WHERE application_id = ?
                    """,
                    (application_id,),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                ledger.connection.execute(
                    """
                    DELETE FROM application_strategy_assignments
                    WHERE application_id = ?
                    """,
                    (application_id,),
                )
            ledger.close()

    def test_strategy_generation_is_content_addressed_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            strategy = {
                "auto_apply_threshold": 75,
                "role_families": ["applied_ai", "ai_product_management"],
            }
            encoded = json.dumps(
                strategy,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            expected_sha256 = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
            recorder = getattr(ledger, "record_strategy_generation", None)
            self.assertIsNotNone(recorder)

            first = recorder(strategy)
            second = recorder(dict(reversed(list(strategy.items()))))
            row = ledger.connection.execute(
                """
                SELECT
                  strategy_generation_id,
                  parent_generation_id,
                  changed_field,
                  strategy_json,
                  strategy_sha256
                FROM strategy_generations
                WHERE strategy_generation_id = ?
                """,
                (first,),
            ).fetchone()
            ledger.close()

            self.assertEqual(first, f"strategy-{expected_sha256}")
            self.assertEqual(second, first)
            self.assertEqual(
                tuple(row),
                (first, None, None, encoded, expected_sha256),
            )

    def test_candidate_generation_records_exactly_one_declared_parent_change(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            baseline = ledger.record_strategy_generation(
                {
                    "auto_apply_threshold": 75,
                    "model_route": "gpt-5.6-terra",
                }
            )
            try:
                candidate = ledger.record_strategy_generation(
                    {
                        "auto_apply_threshold": 80,
                        "model_route": "gpt-5.6-terra",
                    },
                    parent_generation_id=baseline,
                    changed_field="auto_apply_threshold",
                )
            except TypeError as error:
                self.fail(f"candidate lineage is not supported: {error}")
            row = ledger.connection.execute(
                """
                SELECT parent_generation_id, changed_field
                FROM strategy_generations
                WHERE strategy_generation_id = ?
                """,
                (candidate,),
            ).fetchone()
            with self.assertRaisesRegex(
                ValueError, "exactly the declared strategy field"
            ):
                ledger.record_strategy_generation(
                    {
                        "auto_apply_threshold": 80,
                        "model_route": "codex",
                    },
                    parent_generation_id=baseline,
                    changed_field="auto_apply_threshold",
                )
            ledger.close()

            self.assertEqual(
                tuple(row),
                (baseline, "auto_apply_threshold"),
            )

    def test_strategy_generations_cannot_be_updated_or_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite3")
            generation_id = ledger.record_strategy_generation(
                {"auto_apply_threshold": 75}
            )

            with self.assertRaises(sqlite3.IntegrityError):
                ledger.connection.execute(
                    """
                    UPDATE strategy_generations
                    SET strategy_json = '{"auto_apply_threshold":80}'
                    WHERE strategy_generation_id = ?
                    """,
                    (generation_id,),
                )
            with self.assertRaises(sqlite3.IntegrityError):
                ledger.connection.execute(
                    """
                    DELETE FROM strategy_generations
                    WHERE strategy_generation_id = ?
                    """,
                    (generation_id,),
                )
            ledger.close()

    def test_legacy_migration_assigns_every_application_without_changing_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "ledger.sqlite3"
            ledger = Ledger(database)
            first = ledger.add_application(
                "Legacy One", "AI Engineer", "https://jobs.example.com/legacy-1"
            )
            second = ledger.add_application(
                "Legacy Two", "AI Product", "https://jobs.example.com/legacy-2"
            )
            with ledger._transaction():
                ledger.connection.execute(
                    "UPDATE applications SET current_state = 'submitted' WHERE id = ?",
                    (first,),
                )
                ledger.connection.execute(
                    "UPDATE applications SET current_state = 'not_submitted' WHERE id = ?",
                    (second,),
                )
            before = dict(
                ledger.connection.execute(
                    """
                    SELECT current_state, COUNT(*)
                    FROM applications
                    GROUP BY current_state
                    """
                ).fetchall()
            )
            ledger.close()

            migrated = Ledger(database)
            tables = {
                row[0]
                for row in migrated.connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertTrue(
                {
                    "strategy_generations",
                    "application_strategy_assignments",
                    "funnel_outcomes",
                    "strategy_outcome_projection",
                }.issubset(tables)
            )
            assignments = migrated.connection.execute(
                """
                SELECT
                  capture_status,
                  source,
                  query_family,
                  role_family,
                  material_variant,
                  message_variant,
                  model_route,
                  prompt_sha256,
                  material_sha256
                FROM application_strategy_assignments
                ORDER BY application_id
                """
            ).fetchall()
            after = dict(
                migrated.connection.execute(
                    """
                    SELECT current_state, COUNT(*)
                    FROM applications
                    GROUP BY current_state
                    """
                ).fetchall()
            )
            migrated.close()

            self.assertEqual(before, {"not_submitted": 1, "submitted": 1})
            self.assertEqual(after, before)
            self.assertEqual(len(assignments), 2)
            self.assertTrue(
                all(row["capture_status"] == "legacy_unavailable" for row in assignments)
            )
            for row in assignments:
                self.assertEqual(
                    tuple(row)[1:],
                    (
                        "legacy_unavailable",
                        "legacy_unavailable",
                        "legacy_unavailable",
                        "legacy_unavailable",
                        "legacy_unavailable",
                        "legacy_unavailable",
                        None,
                        None,
                    ),
                )


if __name__ == "__main__":
    unittest.main()
