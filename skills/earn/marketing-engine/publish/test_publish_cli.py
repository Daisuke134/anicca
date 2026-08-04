import json
import pathlib
import subprocess
import sys

import jsonschema

HERE = pathlib.Path(__file__).resolve().parent
ENGINE = HERE.parent
sys.path.insert(0, str(HERE))

from test_intent_store import fixture_intent


def test_publication_intent_schema_accepts_canonical_intent(tmp_path):
    schema = json.loads((ENGINE / "schemas/publication-intent.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(fixture_intent(tmp_path), schema)


def test_lm_publish_shadow_is_durable_and_has_zero_external_effects(tmp_path):
    intent_path = tmp_path / "intent.json"
    intent_path.write_text(json.dumps(fixture_intent(tmp_path)))
    db_path = tmp_path / "publish.sqlite3"
    result = subprocess.run([
        str(ENGINE / "bin/lm"), "publish", "shadow",
        "--intent", str(intent_path), "--db", str(db_path),
        "--approvals", str(tmp_path / "missing-approvals.jsonl"),
        "--owner", "shadow-test", "--now", "2026-08-02T00:00:00Z",
    ], capture_output=True, text=True, check=True)
    payload = json.loads(result.stdout)
    assert payload["status"] == "shadow_valid"
    assert payload["dispatchable"] is False
    assert payload["preflight_blocker"] == "account is not approved_active"
    assert payload["external_effects"] == []
    assert db_path.is_file()


def test_lm_publish_shadow_exact_replay_does_not_create_second_intent(tmp_path):
    intent_path = tmp_path / "intent.json"
    intent_path.write_text(json.dumps(fixture_intent(tmp_path)))
    db_path = tmp_path / "publish.sqlite3"
    command = [str(ENGINE / "bin/lm"), "publish", "shadow",
               "--intent", str(intent_path), "--db", str(db_path),
               "--approvals", str(tmp_path / "missing.jsonl"),
               "--owner", "shadow-test", "--now", "2026-08-02T00:00:00Z"]
    first = json.loads(subprocess.run(command, capture_output=True, text=True, check=True).stdout)
    second = json.loads(subprocess.run(command, capture_output=True, text=True, check=True).stdout)
    assert first["publish_key"] == second["publish_key"]
    assert first["intent_created"] is True
    assert second["intent_created"] is False
