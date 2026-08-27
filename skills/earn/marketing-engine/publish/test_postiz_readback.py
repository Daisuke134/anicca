import json
import pathlib
import sys

import jsonschema

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from publish_cli import run_postiz_readback
from test_reconcile import published_post, setup


class FakeReadPostiz:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def list_posts(self, start, end):
        self.calls.append((start, end))
        return self.rows


def test_postiz_readback_writes_only_exact_stored_post(tmp_path):
    store, intent, _ = setup(tmp_path)
    client = FakeReadPostiz([published_post(intent)])
    output = tmp_path / "post.json"
    report = tmp_path / "report.json"
    result = run_postiz_readback(
        db_path=store.path, publish_key=intent["publish_key"], output_path=output,
        report_path=report, client=client)
    assert result["status"] == "post_found"
    assert result["posts_observed"] == 1
    assert result["external_mutations"] == 0
    assert json.loads(output.read_text())["id"] == "post-123"
    assert json.loads(report.read_text())["stored_post_id"] == "post-123"
    schema = json.loads((HERE.parent / "schemas/postiz-readback.schema.json").read_text())
    jsonschema.validate(json.loads(report.read_text()), schema)
    assert len(client.calls) == 1


def test_postiz_readback_zero_match_stays_pending_without_receipt_file(tmp_path):
    store, intent, _ = setup(tmp_path)
    output = tmp_path / "post.json"
    result = run_postiz_readback(
        db_path=store.path, publish_key=intent["publish_key"], output_path=output,
        report_path=None, client=FakeReadPostiz([]))
    assert result["status"] == "pending_provider_receipt"
    assert result["posts_observed"] == 0
    assert not output.exists()
