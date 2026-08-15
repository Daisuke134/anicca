#!/usr/bin/env python3
"""The question leaves through the talkroom the buyer actually paid in.

reply_lane --ask-buyer drives the DM browser. On this paid talkroom that browser landed
somewhere else and died with collector_unhealthy:unexpected_title, so the one branch built
to break the deadlock delivered nothing. The question is now written as the answer payload
the paid-progress browser already accepts -- the same send path, not a third one.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

import ask_buyer  # noqa: E402
import ask_buyer_pass  # noqa: E402

REAL_BLOCKED = {
    "version": 1,
    "status": "BLOCKED",
    "feedback_sha256": "57b8719d5bd8ff77a7f68614fd9e9e6a4dbc35411094f43fd82891a103bdcfda",
    "checks": [{"command": "find .", "result": "成果物の種類、内容、素材、仕様の指定なし。"}],
    "blocker": "制作指示がありません。",
}

GOOD_QUESTION = (
    "ご購入ありがとうございます。着手が遅れており申し訳ありません。"
    "制作したい物の種類、参考にしたいデザイン、掲載したい文章、使用する写真、"
    "希望の仕上がり日をお知らせいただけますでしょうか。"
)


def _fake_runner(tmp_path: Path, body: str) -> Path:
    """A runner that answers with a fixed reply_body, in the real evidence shape."""
    runner = tmp_path / "fake_runner.py"
    runner.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "evidence = Path(args[args.index('--evidence-dir') + 1])\n"
        "evidence.mkdir(parents=True, exist_ok=True)\n"
        "sys.stdin.read()\n"
        f"body = {body!r}\n"
        "result = evidence / 'result.json'\n"
        "result.write_text(json.dumps({'reply_body': body}), encoding='utf-8')\n"
        "(evidence / 'summary.json').write_text(\n"
        "    json.dumps({'result_path': str(result)}), encoding='utf-8')\n",
        encoding="utf-8",
    )
    return runner


def _queue(tmp_path: Path) -> Path:
    path = tmp_path / "ask-buyer-queue.json"
    path.write_text(
        json.dumps({
            "status": "ready",
            "items": [{
                "talkroom_id": "90000002",
                "talkroom_url": "https://coconala.com/talkrooms/90000002",
                "blocker_key": REAL_BLOCKED["feedback_sha256"],
                "blocked_state": REAL_BLOCKED,
            }],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def _run(tmp_path: Path, body: str) -> tuple[int, Path]:
    output = tmp_path / "paid-answer.json"
    code = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "ask_buyer_pass.py"), "compose",
         "--queue", str(_queue(tmp_path)),
         "--runner", str(_fake_runner(tmp_path, body)),
         "--schema", str(SKILL / "schemas" / "reply_composition.schema.json"),
         "--workdir", str(tmp_path),
         "--output", str(output)],
        capture_output=True, text=True, check=False, env=dict(os.environ),
    ).returncode
    return code, output


BUYER_WORDS = "よろしくお願いいたします！！\n\nかしこまりました！"


def _project(tmp_path: Path, *, feedback_text: str | None = BUYER_WORDS) -> Path:
    """A project root whose requirements file holds the buyer's current message."""
    root = tmp_path / "projects" / "91000002"
    (root / "requirements").mkdir(parents=True)
    payload = {"feedback_sha256": REAL_BLOCKED["feedback_sha256"]}
    if feedback_text is not None:
        payload["feedback_text"] = feedback_text
    (root / "requirements" / "live-buyer-reply.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return root


def test_the_buyers_own_words_reach_the_prompt(tmp_path):
    """Otherwise the question is written from the blocker alone and reads like a form."""
    root = _project(tmp_path)
    state = dict(REAL_BLOCKED, requirements_path=str(root / "requirements" / "live-buyer-reply.json"))
    text = ask_buyer_pass._buyer_feedback_text(state, str(root))
    assert text == BUYER_WORDS
    assert BUYER_WORDS in ask_buyer.question_prompt(state=state, conversation=text)


def test_a_requirements_path_outside_the_project_is_ignored(tmp_path):
    """The blocked record is model-written; the path it names is trusted only in-project."""
    root = _project(tmp_path)
    outsider = tmp_path / "elsewhere.json"
    outsider.write_text(json.dumps({"feedback_text": "他人の会話"}), encoding="utf-8")
    state = dict(REAL_BLOCKED, requirements_path=str(outsider))
    assert ask_buyer_pass._buyer_feedback_text(state, str(root)) is None


def test_a_missing_feedback_text_is_simply_absent(tmp_path):
    root = _project(tmp_path, feedback_text=None)
    state = dict(REAL_BLOCKED, requirements_path=str(root / "requirements" / "live-buyer-reply.json"))
    assert ask_buyer_pass._buyer_feedback_text(state, str(root)) is None


def test_the_question_is_reported_to_dais(tmp_path, monkeypatch):
    """A question to a paying customer must not become invisible to Dais."""
    sent: dict[str, str] = {}

    class _Transport:
        def __init__(self, *, target):
            sent["target"] = target

        def send_report(self, message, *, event_key):
            sent["message"] = message
            sent["event_key"] = event_key
            return "42"

    import telegram_report

    monkeypatch.setattr(telegram_report, "OpenClawTelegramTransport", _Transport)
    answer = tmp_path / "paid-answer.json"
    answer.write_text(json.dumps({"version": 1, "status": "answer", "message": GOOD_QUESTION},
                                 ensure_ascii=False), encoding="utf-8")
    args = ask_buyer_pass.argparse.Namespace(
        queue=str(_queue(tmp_path)), answer=str(answer), target="42")
    assert ask_buyer_pass.report(args) == 0
    # The three facts Dais needs: which talkroom, what we asked, why we were stuck.
    assert "https://coconala.com/talkrooms/90000002" in sent["message"]
    assert GOOD_QUESTION in sent["message"]
    assert REAL_BLOCKED["blocker"] in sent["message"]
    assert sent["event_key"].startswith("coconala:ask-buyer:v1:90000002:")


def test_a_failed_report_does_not_claim_success(tmp_path, monkeypatch):
    class _Broken:
        def __init__(self, *, target):
            pass

        def send_report(self, message, *, event_key):
            raise RuntimeError("Telegram ACK has no message ID")

    import telegram_report

    monkeypatch.setattr(telegram_report, "OpenClawTelegramTransport", _Broken)
    answer = tmp_path / "paid-answer.json"
    answer.write_text(json.dumps({"version": 1, "status": "answer", "message": GOOD_QUESTION},
                                 ensure_ascii=False), encoding="utf-8")
    args = ask_buyer_pass.argparse.Namespace(
        queue=str(_queue(tmp_path)), answer=str(answer), target="42")
    assert ask_buyer_pass.report(args) == 1


def test_the_question_is_written_as_a_paid_answer_payload(tmp_path):
    code, output = _run(tmp_path, GOOD_QUESTION)
    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    # Exactly what coconala_paid_progress_browser.validate_answer_contract() accepts.
    assert payload["version"] == 1
    assert payload["status"] == "answer"
    assert payload["message"] == GOOD_QUESTION


def test_the_payload_survives_the_contract_the_browser_enforces(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "coconala_paid_progress_browser",
        SKILL / "scripts" / "coconala_paid_progress_browser.py",
    )
    browser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(browser)
    _, output = _run(tmp_path, GOOD_QUESTION)
    contract = browser.validate_answer_contract(
        {"talkroom_id": "90000002", "talkroom_url": "https://coconala.com/talkrooms/90000002"},
        json.loads(output.read_text(encoding="utf-8")),
    )
    assert contract.message == GOOD_QUESTION


def test_a_third_empty_acknowledgement_is_not_written(tmp_path):
    """The two messages this buyer already got were polite and asked nothing."""
    code, output = _run(tmp_path, "確認のうえ、あらためてご連絡いたします。")
    assert code == 1
    assert not output.exists()


def test_an_empty_queue_writes_nothing(tmp_path):
    output = tmp_path / "paid-answer.json"
    queue = tmp_path / "queue.json"
    queue.write_text(json.dumps({"status": "queue_empty", "items": []}), encoding="utf-8")
    args = ask_buyer_pass.argparse.Namespace(
        queue=str(queue), runner="/nonexistent", schema="/nonexistent",
        workdir=str(tmp_path), output=str(output),
    )
    assert ask_buyer_pass.compose(args) == 1
    assert not output.exists()


# ---------------------------------------------------------------------------
# One decision about "is this order blocked", shared with the gate that sends.
#
# The planner read ask_buyer.blocked_state(), which tolerates a record about feedback the
# buyer has already replaced. The send gate reads blocked_evidence_verdict() and moves only
# on `fresh`. Measured 2026-08-07 12:41 on order 91000002: a question was composed against
# digest 57b8719d while the buyer's open message hashed to 43981596, and the gate threw it
# away. The model call was spent, the pass failed, and the buyer heard nothing.

CURRENT_SHA = "43981596b5ca66c70fcb638949507f95b6a90ca19828c3f0d9fadcf1815940ea"


def _blocked_project(tmp_path: Path, *, blocked_sha: str | None, current_sha: str = CURRENT_SHA,
                     corrupt: bool = False) -> Path:
    """A project root shaped exactly like ~/gig/projects/91000002."""
    root = tmp_path / "projects" / "91000002"
    (root / "requirements").mkdir(parents=True)
    (root / "evidence").mkdir(parents=True)
    requirements = root / "requirements" / "live-buyer-reply.json"
    requirements.write_text(
        json.dumps({"feedback_sha256": current_sha,
                    "feedback_text": "どちらを確認すればよいでしょうか？"}, ensure_ascii=False),
        encoding="utf-8")
    record = root / "evidence" / "acceptance-blocked.json"
    if corrupt:
        record.write_text('{"version":1,"status":"BLOC', encoding="utf-8")
    elif blocked_sha is not None:
        record.write_text(json.dumps(
            dict(REAL_BLOCKED, feedback_sha256=blocked_sha, requirements_path=str(requirements)),
            ensure_ascii=False), encoding="utf-8")
    return root


def _build(tmp_path: Path, root: Path) -> dict:
    output = tmp_path / "ask-buyer-queue.json"
    args = ask_buyer_pass.argparse.Namespace(
        project_root=str(root), talkroom_id="90000002",
        ledger=str(tmp_path / "ask-buyer.jsonl"), output=str(output))
    assert ask_buyer_pass.build(args) == 0
    return json.loads(output.read_text(encoding="utf-8"))


def test_a_stale_blocked_record_produces_no_composed_question(tmp_path):
    """The exact 12:41 shape: blocked about 57b8719d, buyer now asking about 43981596."""
    root = _blocked_project(tmp_path, blocked_sha=REAL_BLOCKED["feedback_sha256"])
    queue = _build(tmp_path, root)
    assert queue["items"] == []
    assert queue["blocked_verdict"] == "stale"

    # And the model is never called: a question that cannot be sent must not be paid for.
    called = tmp_path / "runner-was-called"
    runner = tmp_path / "tripwire_runner.py"
    runner.write_text(f"open({str(called)!r}, 'w').close()\n", encoding="utf-8")
    output = tmp_path / "paid-answer.json"
    args = ask_buyer_pass.argparse.Namespace(
        queue=str(tmp_path / "ask-buyer-queue.json"), runner=str(runner),
        schema=str(SKILL / "schemas" / "reply_composition.schema.json"),
        workdir=str(tmp_path), output=str(output), project_root=str(root))
    assert ask_buyer_pass.compose(args) == 1
    assert not called.exists()
    assert not output.exists()


def test_a_fresh_blocked_record_still_plans_a_question(tmp_path):
    """The gate is only as narrow as the send gate -- being stuck must still speak."""
    root = _blocked_project(tmp_path, blocked_sha=CURRENT_SHA)
    queue = _build(tmp_path, root)
    assert len(queue["items"]) == 1
    assert queue["items"][0]["blocker_key"] == CURRENT_SHA


def test_a_project_that_was_never_blocked_plans_nothing(tmp_path):
    root = _blocked_project(tmp_path, blocked_sha=None)
    queue = _build(tmp_path, root)
    assert queue["items"] == []
    assert queue["blocked_verdict"] == "absent"


def test_an_unreadable_blocked_record_plans_nothing(tmp_path):
    """undeterminable, same direction as the send gate: a check that could not run saw nothing."""
    root = _blocked_project(tmp_path, blocked_sha=None, corrupt=True)
    queue = _build(tmp_path, root)
    assert queue["items"] == []
    assert queue["blocked_verdict"] == "undeterminable"


def test_the_dedupe_still_holds_for_a_fresh_block(tmp_path):
    """A paying buyer asked the identical question every hour is a buyer who refunds."""
    root = _blocked_project(tmp_path, blocked_sha=CURRENT_SHA)
    ledger = tmp_path / "ask-buyer.jsonl"
    ledger.write_text(json.dumps({"talkroom_id": "90000002", "blocker_key": CURRENT_SHA}) + "\n",
                      encoding="utf-8")
    output = tmp_path / "ask-buyer-queue.json"
    args = ask_buyer_pass.argparse.Namespace(
        project_root=str(root), talkroom_id="90000002",
        ledger=str(ledger), output=str(output))
    assert ask_buyer_pass.build(args) == 0
    queue = json.loads(output.read_text(encoding="utf-8"))
    assert queue["items"] == []
    assert queue["already_asked"] == CURRENT_SHA
