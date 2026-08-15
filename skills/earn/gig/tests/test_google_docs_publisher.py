from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "google_docs_publisher.py"


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("google_docs_publisher", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def completed(returncode: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(args=["gog"], returncode=returncode, stdout=stdout, stderr=stderr)


class FakeRunner:
    """Records every argv it was called with and returns queued CompletedProcess rows,
    the same subprocess-boundary mocking shape as retainer_lane.py's ``runner`` param.
    """

    def __init__(self, responses: list[subprocess.CompletedProcess]) -> None:
        self.responses = list(responses)
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        return self.responses.pop(0)


def test_create_path_uploads_then_shares_and_returns_the_link(tmp_path) -> None:
    m = load_module()
    src = tmp_path / "guide.md"
    src.write_text("# hello", encoding="utf-8")
    runner = FakeRunner([
        completed(0, stdout='{"file":{"id":"F1","mimeType":"application/vnd.google-apps.document","webViewLink":"https://docs.google.com/document/d/F1/edit"}}'),
        completed(0, stdout='{"link":"https://docs.google.com/document/d/F1/edit","permission":{"role":"commenter"}}'),
    ])
    result = m.publish(input_path=src, title="capability-test", runner=runner)
    assert result == {
        "ok": True, "file_id": "F1",
        "link": "https://docs.google.com/document/d/F1/edit", "replaced": False,
    }
    upload_argv, share_argv = runner.calls
    assert upload_argv[:3] == ["gog", "drive", "upload"]
    assert "--convert-to" in upload_argv and "doc" in upload_argv
    assert "--name" in upload_argv and "capability-test" in upload_argv
    assert share_argv[:3] == ["gog", "drive", "share"]
    assert "commenter" in share_argv
    assert "anyone" in share_argv


def test_a_gog_upload_failure_is_fail_closed(tmp_path) -> None:
    m = load_module()
    src = tmp_path / "guide.md"
    src.write_text("# hello", encoding="utf-8")
    runner = FakeRunner([completed(1, stderr="quota exceeded")])
    result = m.publish(input_path=src, title="capability-test", runner=runner)
    assert result == {"ok": False, "reason": "quota exceeded"}
    assert len(runner.calls) == 1  # never reaches the share call


def test_a_gog_share_failure_is_fail_closed_but_reports_the_created_file(tmp_path) -> None:
    m = load_module()
    src = tmp_path / "guide.md"
    src.write_text("# hello", encoding="utf-8")
    runner = FakeRunner([
        completed(0, stdout='{"file":{"id":"F1","webViewLink":"https://docs.google.com/document/d/F1/edit"}}'),
        completed(1, stderr="permission denied"),
    ])
    result = m.publish(input_path=src, title="capability-test", runner=runner)
    assert result == {"ok": False, "reason": "permission denied", "file_id": "F1"}


def test_missing_input_never_calls_gog(tmp_path) -> None:
    m = load_module()
    runner = FakeRunner([])
    result = m.publish(input_path=tmp_path / "nope.md", title="t", runner=runner)
    assert result == {"ok": False, "reason": f"missing_or_empty_input:{tmp_path / 'nope.md'}"}
    assert runner.calls == []


def test_empty_input_never_calls_gog(tmp_path) -> None:
    m = load_module()
    src = tmp_path / "empty.md"
    src.write_text("", encoding="utf-8")
    runner = FakeRunner([])
    result = m.publish(input_path=src, title="t", runner=runner)
    assert result["ok"] is False
    assert runner.calls == []


def test_replace_path_skips_the_share_call_and_uses_replace_flag(tmp_path) -> None:
    m = load_module()
    src = tmp_path / "guide-v2.md"
    src.write_text("# updated", encoding="utf-8")
    runner = FakeRunner([
        completed(0, stdout='{"file":{"id":"F1","webViewLink":"https://docs.google.com/document/d/F1/edit"}}'),
    ])
    result = m.publish(input_path=src, title="capability-test", replace="F1", runner=runner)
    assert result == {
        "ok": True, "file_id": "F1",
        "link": "https://docs.google.com/document/d/F1/edit", "replaced": True,
    }
    assert len(runner.calls) == 1
    assert "--replace" in runner.calls[0] and "F1" in runner.calls[0]
    assert "--convert-to" not in runner.calls[0]


def test_replace_against_an_already_converted_google_doc_is_fail_closed(tmp_path) -> None:
    # Live-verified 2026-08-09: gog refuses this outright. The real stderr must surface,
    # not a made-up one.
    m = load_module()
    src = tmp_path / "guide-v2.md"
    src.write_text("# updated", encoding="utf-8")
    runner = FakeRunner([
        completed(
            1,
            stderr="cannot replace content for Google Workspace files "
                   "(mimeType=application/vnd.google-apps.document)",
        ),
    ])
    result = m.publish(input_path=src, title="capability-test", replace="F1", runner=runner)
    assert result["ok"] is False
    assert "Google Workspace files" in result["reason"]


def test_gog_output_that_is_not_json_is_fail_closed(tmp_path) -> None:
    m = load_module()
    src = tmp_path / "guide.md"
    src.write_text("# hello", encoding="utf-8")
    runner = FakeRunner([completed(0, stdout="not json")])
    result = m.publish(input_path=src, title="t", runner=runner)
    assert result["ok"] is False
    assert "gog_output_not_json" in result["reason"]


def test_main_exits_nonzero_on_failure_and_prints_one_json_line(tmp_path, capsys) -> None:
    m = load_module()
    missing = tmp_path / "nope.md"
    rc = m.main(["--input", str(missing), "--title", "t"])
    out = capsys.readouterr().out.strip()
    assert rc != 0
    assert out.count("\n") == 0
    import json
    payload = json.loads(out)
    assert payload["ok"] is False
