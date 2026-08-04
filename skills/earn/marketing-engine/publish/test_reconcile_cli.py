import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from publish_cli import run_reconcile
from test_reconcile import native_candidate, published_post, setup


def test_reconcile_cli_uses_registry_handle_and_writes_real_identity(tmp_path):
    store, intent, ledger = setup(tmp_path)
    post_path = tmp_path / "post.json"
    native_path = tmp_path / "native.json"
    post_path.write_text(json.dumps(published_post(intent)))
    native_path.write_text(json.dumps([native_candidate(intent)]))
    result = run_reconcile(
        db_path=store.path, publish_key=intent["publish_key"], post_path=post_path,
        native_path=native_path, ledger_path=ledger,
        observed_at="2026-08-02T01:05:00Z", engine=HERE.parent)
    assert result["status"] == "published_native_verified"
    assert result["native_post_id"] == "native-123"
    assert len(ledger.read_text().splitlines()) == 1
