#!/usr/bin/env python3
"""Deciding whether a paid order says what to build, before building it.

Both projects here are real. 91000001 (買い手A, 「架空ゲーム動画の企画・台本作成ができる方を募集します」)
is the order that on 2026-08-07 23:36 got a general guide to the game built for it in two
and a half minutes and came one step from formal delivery; its entire specification is a
題材 and a delivery format. 91000002 (買い手B) is the opposite: a posting, a DM thread
with four concrete requests, our own agreement to them, and two attached images.

★ The reverse case is the point of half of this file. ★ A gate that only ever says "ask"
is a loop that never earns anything, so the sufficient order has to keep reaching the
builder untouched.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

import ask_buyer  # noqa: E402
import ask_buyer_pass  # noqa: E402
import first_contact  # noqa: E402
import paid_work_evidence  # noqa: E402

STUB_RUNNER = Path(__file__).resolve().parent / "fixtures" / "first_contact_stub_runner.py"

# ---------------------------------------------------------------------------
# The two real orders
# ---------------------------------------------------------------------------

PURECO_MESSAGE = (
    "よろしくお願いします。\n\n\n題材\n\n『パズルクエストX』\n\n"
    "Switch版：20XX年配信\nスマホ版：20XX年配信\n基本プレイ無料\n＝＝＝\n\n"
    "納品はGoogleドキュメントでお願いします。"
)
PURECO_SHA = "8643236ef2c2b66bde6325dc10e22c006fc6355ba85766971fc1016fad72e7a8"
PURECO_TITLE = "架空ゲーム動画の企画・台本作成ができる方を募集します"

SHINTAMAGO_MESSAGE = (
    "「募集内容を拝見し、Canvaで作成済みの4枚の画像を加工し編集しやすいテンプレートへ整える件に...」"
    "ついて質問です。\n\nこちらの依頼は、この画像データを文字も画像も編集できるCanva形式にして"
    "仕上げていただきたいです！！\n\n1枚目は3コマ、4コマ、5コマをまとめて\n2枚目はそのままで\n\n対応いただけますか？"
)
SHINTAMAGO_SHA = "57b8719d5bd8ff77a7f68614d9fe9e6a4dbc35411094f43fd82891a103bdcfda"


def _project(tmp_path: Path, *, request_id: str, feedback_text: str, feedback_sha: str,
             sources: list[str], posting: str = "", commitments: list[str] | None = None,
             attachments: list[str] | None = None) -> Path:
    root = tmp_path / "gig" / "projects" / request_id
    (root / "requirements").mkdir(parents=True, exist_ok=True)
    (root / "context").mkdir(parents=True, exist_ok=True)
    requirements = root / "requirements" / "live-buyer-reply.json"
    requirements.write_text(json.dumps({
        "version": 1,
        "feedback_sha256": feedback_sha,
        "feedback_text": feedback_text,
    }, ensure_ascii=False), encoding="utf-8")
    combined: dict = {
        "sources_present": sources,
        "requirements": {
            "path": str(requirements),
            "feedback_sha256": feedback_sha,
            "current_request": feedback_text,
            "everything_the_buyer_has_asked_for": [{"text": feedback_text, "attachments": []}],
        },
    }
    if posting:
        combined["posting"] = {"text": posting}
    if commitments:
        combined["our_commitments"] = [{"text": row} for row in commitments]
    if attachments:
        combined["buyer_attachments"] = [{"path": f"/tmp/{name}"} for name in attachments]
    (root / "context" / "current.json").write_text(json.dumps({
        "version": 1,
        "project_root": str(root),
        "project_context_sha256": feedback_sha,
        "combined_context": combined,
    }, ensure_ascii=False), encoding="utf-8")
    return root


def pureco(tmp_path: Path) -> Path:
    """91000001 as it actually stood: a 題材, a delivery format, and nothing else."""
    return _project(
        tmp_path, request_id="91000001", feedback_text=PURECO_MESSAGE,
        feedback_sha=PURECO_SHA, sources=["requirements", "talkroom"],
    )


def 買い手B(tmp_path: Path) -> Path:
    """91000002 as it actually stands: posting, DM, our agreement, and the material."""
    return _project(
        tmp_path, request_id="91000002", feedback_text=SHINTAMAGO_MESSAGE,
        feedback_sha=SHINTAMAGO_SHA,
        sources=["dm", "our_commitments", "posting", "requirements", "talkroom"],
        posting="Canvaで作成済みの4枚の既存画像の加工と編集しやすいテンプレートへの整形",
        commitments=[
            "承知いたしました。1枚目は3・4・5コマ目をそれぞれ1枚ごとに、編集可能なCanva形式で仕上げ、"
            "2枚目は現在のレイアウトをそのまま活かしつつ、文字と画像を差し替えられるテンプレートに仕立てます。"
        ],
        attachments=["IMG_0001.jpeg", "IMG_0002.jpeg"],
    )


def item(root: Path, *, title: str, request_id: str, sha: str, **extra) -> dict:
    payload = {
        "request_id": request_id,
        "title": title,
        "delivery_action": "work_required",
        "delivery_date": "2026-08-20",
        "price_jpy": 5000,
        "buyer_feedback_sha256": sha,
        "buyer_feedback_requirements_path": str(root / "requirements" / "live-buyer-reply.json"),
        "seller_message_observed": False,
        "contact_deadline": "2026-08-09T23:00:00+09:00",
        "queue_class": "buyer_feedback_or_revision",
    }
    payload.update(extra)
    return payload


def decide(root: Path, queue_item: dict, tmp_path: Path, monkeypatch, *, stub: str,
           ledger: Path | None = None, evidence_root: Path | None = None,
           allow_model_call: bool = True) -> dict:
    monkeypatch.setenv("GIG_FIRST_CONTACT_STUB", stub)
    return first_contact.decide(
        project_root=root,
        queue_item=queue_item,
        ask_ledger=str(ledger or (tmp_path / "ask-buyer.jsonl")),
        evidence_dir=tmp_path / "evidence" / "agent-FIRST_CONTACT",
        evidence_root=evidence_root or (tmp_path / "evidence-root"),
        runner=STUB_RUNNER,
        allow_model_call=allow_model_call,
    )


# ---------------------------------------------------------------------------
# The order that produced the wrong artifact
# ---------------------------------------------------------------------------

def test_the_order_that_never_said_what_to_make_produces_a_question(tmp_path, monkeypatch):
    root = pureco(tmp_path)
    result = decide(root, item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA),
                    tmp_path, monkeypatch, stub="ask")
    assert result["decision"] == first_contact.ASK
    assert result["blocked_record_written"] is True
    # And the record has to be one the send gate will act on, not merely a file on disk:
    # paid_work_fresh_blocked moves only on `fresh`.
    verdict, state = paid_work_evidence.blocked_evidence_verdict(root)
    assert verdict == paid_work_evidence.BLOCK_FRESH
    assert ask_buyer.blocker_key(state) == PURECO_SHA


def test_the_question_is_about_the_job_that_was_bought(tmp_path, monkeypatch):
    """The title never reaches the builder. It has to reach the question."""
    root = pureco(tmp_path)
    decide(root, item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA),
           tmp_path, monkeypatch, stub="ask")
    state = ask_buyer.blocked_state(root)
    assert state["order_title"] == PURECO_TITLE
    prompt = ask_buyer.question_prompt(state=state, conversation=PURECO_MESSAGE)
    assert PURECO_TITLE in prompt
    # The three things nobody had written down.
    assert "何本" in prompt and "尺" in prompt


def test_a_blocked_record_without_a_title_is_unchanged(tmp_path):
    """Records the builder writes have no title, and must behave exactly as before."""
    prompt = ask_buyer.question_prompt(
        state={"status": "BLOCKED", "checks": [{"result": "素材の指定なし"}]},
        conversation="よろしくお願いします",
    )
    assert "購入されたのは" not in prompt


# ---------------------------------------------------------------------------
# The reverse: a specified order must still be built
# ---------------------------------------------------------------------------

def test_an_order_with_real_requirements_goes_to_the_builder(tmp_path, monkeypatch):
    root = 買い手B(tmp_path)
    result = decide(
        root,
        item(root, title="Canva画像4枚の編集・テンプレート化", request_id="91000002", sha=SHINTAMAGO_SHA),
        tmp_path, monkeypatch, stub="build",
    )
    assert result["decision"] == first_contact.BUILD
    assert result["blocked_record_written"] is False
    assert not (root / ask_buyer.BLOCKED_EVIDENCE).exists()
    assert paid_work_evidence.blocked_evidence_verdict(root)[0] == paid_work_evidence.BLOCK_ABSENT


def test_a_room_we_have_spoken_in_is_never_diverted_by_a_guess(tmp_path, monkeypatch):
    """★ The measurement that shaped this gate. ★

    Five real runs of the decider per order, 2026-08-08: the order nobody had spoken to
    answered ``ask`` 5/5, and 買い手B -- a DM thread, our own written agreement, a
    delivery already sent -- answered build/build/ask/build/ask. The brief requires that
    second order to reach the builder, and no single stochastic call delivers that.

    So the judgement is not made there at all. A stub that would answer ``ask`` if it ran
    proves the model is not consulted, not merely overruled.
    """
    root = 買い手B(tmp_path)
    result = decide(
        root,
        item(root, title="Canva画像4枚の編集・テンプレート化", request_id="91000002",
             sha=SHINTAMAGO_SHA, seller_message_observed=True, contact_deadline=None),
        tmp_path, monkeypatch, stub="ask",
    )
    assert result["decision"] == first_contact.BUILD
    assert result["source"] == "already_in_conversation"
    assert not (root / ask_buyer.BLOCKED_EVIDENCE).exists()


def test_the_builders_own_diagnosis_still_reaches_a_room_we_have_spoken_in(tmp_path, monkeypatch):
    """Not consulting the model there is not the same as abandoning the order.

    A BLOCKED record is a fact the builder wrote, not a guess, so it opens the ask path on
    any order -- which is the behaviour that existed before this file and must survive it.
    """
    root = 買い手B(tmp_path)
    (root / "evidence").mkdir(parents=True, exist_ok=True)
    (root / ask_buyer.BLOCKED_EVIDENCE).write_text(json.dumps({
        "version": 1, "status": "BLOCKED",
        "requirements_path": str(root / "requirements" / "live-buyer-reply.json"),
        "feedback_sha256": SHINTAMAGO_SHA,
        "checks": [{"command": "find", "result": "元画像の対応関係が不明"}],
        "blocker": "どの画像をどのテンプレートにするかが決まっていないため",
    }, ensure_ascii=False), encoding="utf-8")
    result = decide(
        root,
        item(root, title="Canva画像4枚の編集・テンプレート化", request_id="91000002",
             sha=SHINTAMAGO_SHA, seller_message_observed=True),
        tmp_path, monkeypatch, stub="build",
    )
    assert result["decision"] == first_contact.ASK
    assert result["source"] == "existing_blocked_record"


def test_the_judges_verdict_reaches_a_room_we_have_spoken_in_too(tmp_path, monkeypatch):
    root = 買い手B(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    _transaction_ledger(evidence_root, "gig-pass-1", root,
                        failure_reason=first_contact.JUDGE_ASK_ERROR_FALLBACK)
    result = decide(
        root,
        item(root, title="Canva画像4枚の編集・テンプレート化", request_id="91000002",
             sha=SHINTAMAGO_SHA, seller_message_observed=True),
        tmp_path, monkeypatch, stub="build", evidence_root=evidence_root)
    assert result["decision"] == first_contact.ASK
    assert result["source"] == "artifact_judge"


def test_the_specified_order_shows_the_decider_what_it_has(tmp_path):
    """A decision made without the posting, the agreement and the material is a guess."""
    root = 買い手B(tmp_path)
    brief = first_contact.order_brief(
        root, item(root, title="Canva画像4枚の編集・テンプレート化", request_id="91000002",
                   sha=SHINTAMAGO_SHA))
    prompt = first_contact.decision_prompt(brief)
    assert "Canvaで作成済みの4枚の既存画像" in prompt
    assert "1枚目は3・4・5コマ目" in prompt
    assert "IMG_0001.jpeg" in prompt


def test_the_unspecified_order_is_shown_what_is_absent(tmp_path):
    """★ Absence is evidence. ★ Silence about a missing posting reads as a specification."""
    root = pureco(tmp_path)
    brief = first_contact.order_brief(
        root, item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA))
    prompt = first_contact.decision_prompt(brief)
    assert PURECO_TITLE in prompt
    assert "ファイルが存在しません" in prompt
    assert "1件もありません" in prompt


# ---------------------------------------------------------------------------
# One question per order per situation
# ---------------------------------------------------------------------------

def test_the_same_order_over_two_passes_asks_once(tmp_path, monkeypatch):
    root = pureco(tmp_path)
    queue_item = item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA)
    ledger = tmp_path / "ask-buyer.jsonl"

    first = decide(root, queue_item, tmp_path, monkeypatch, stub="ask", ledger=ledger)
    assert first["decision"] == first_contact.ASK

    # The pass sends the question and the ask lane records it -- only after the browser
    # confirmed the send, which is what ask_buyer_pass.record does.
    ledger.write_text(json.dumps(
        {"talkroom_id": "90000001", "blocker_key": PURECO_SHA}, ensure_ascii=False) + "\n",
        encoding="utf-8")

    second = decide(root, queue_item, tmp_path, monkeypatch, stub="ask", ledger=ledger)
    assert second["decision"] == first_contact.AWAIT
    assert second["source"] == "already_asked"
    assert second["blocked_record_written"] is False


def test_the_ask_lane_itself_refuses_a_second_question(tmp_path, monkeypatch):
    """The queue the send path reads must be empty on the second pass, not merely ignored."""
    root = pureco(tmp_path)
    decide(root, item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA),
           tmp_path, monkeypatch, stub="ask")
    ledger = tmp_path / "ask-buyer.jsonl"
    output = tmp_path / "ask-buyer-queue.json"

    import argparse
    args = argparse.Namespace(project_root=str(root), talkroom_id="90000001",
                              ledger=str(ledger), output=str(output))
    assert ask_buyer_pass.build(args) == 0
    planned = json.loads(output.read_text(encoding="utf-8"))
    assert planned["status"] == "ready"
    assert len(planned["items"]) == 1

    ledger.write_text(json.dumps(
        {"talkroom_id": "90000001", "blocker_key": PURECO_SHA}, ensure_ascii=False) + "\n",
        encoding="utf-8")
    assert ask_buyer_pass.build(args) == 0
    replanned = json.loads(output.read_text(encoding="utf-8"))
    assert replanned["items"] == []
    assert replanned["already_asked"] == PURECO_SHA


def test_a_buyers_answer_reopens_the_decision(tmp_path, monkeypatch):
    """A new message is a new situation, so it earns a new decision and may earn a question."""
    root = pureco(tmp_path)
    queue_item = item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA)
    ledger = tmp_path / "ask-buyer.jsonl"
    decide(root, queue_item, tmp_path, monkeypatch, stub="ask", ledger=ledger)
    ledger.write_text(json.dumps(
        {"talkroom_id": "90000001", "blocker_key": PURECO_SHA}, ensure_ascii=False) + "\n",
        encoding="utf-8")

    answered_sha = "a" * 64
    (root / "requirements" / "live-buyer-reply.json").write_text(json.dumps({
        "version": 1, "feedback_sha256": answered_sha,
        "feedback_text": "3本、各5分、YouTube通常動画でお願いします。",
    }, ensure_ascii=False), encoding="utf-8")
    answered_item = dict(queue_item, buyer_feedback_sha256=answered_sha)

    result = decide(root, answered_item, tmp_path, monkeypatch, stub="build", ledger=ledger)
    assert result["decision"] == first_contact.BUILD


# ---------------------------------------------------------------------------
# Cost
# ---------------------------------------------------------------------------

def test_an_unchanged_order_does_not_pay_twice(tmp_path, monkeypatch):
    root = 買い手B(tmp_path)
    queue_item = item(root, title="Canva画像4枚の編集・テンプレート化",
                      request_id="91000002", sha=SHINTAMAGO_SHA)
    first = decide(root, queue_item, tmp_path, monkeypatch, stub="build")
    assert (first["decision"], first["source"]) == (first_contact.BUILD, "model")
    # A runner that would crash if it ran at all: the cached answer must not reach it.
    second = decide(root, queue_item, tmp_path, monkeypatch, stub="crash")
    assert (second["decision"], second["source"]) == (first_contact.BUILD, "cache")


def test_a_pass_with_no_model_budget_still_answers(tmp_path, monkeypatch):
    root = pureco(tmp_path)
    result = decide(root, item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA),
                    tmp_path, monkeypatch, stub="ask", allow_model_call=False)
    assert result["decision"] == first_contact.BUILD
    assert result["source"] == "no_budget"


# ---------------------------------------------------------------------------
# Failing to build, never failing to ask
# ---------------------------------------------------------------------------

def test_every_unreadable_answer_leaves_the_loop_where_it_was(tmp_path, monkeypatch):
    for stub in ("crash", "malformed", "no_result", "unknown", "ask_without_missing"):
        root = pureco(tmp_path / stub)
        result = decide(root, item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA),
                        tmp_path / stub, monkeypatch, stub=stub)
        assert result["decision"] == first_contact.BUILD, stub
        assert not (root / ask_buyer.BLOCKED_EVIDENCE).exists(), stub


def test_a_check_that_never_ran_does_not_report_a_verdict(tmp_path, monkeypatch):
    """★ Zero has to record how it looked. ★

    Measured 2026-08-08: the runner path did not exist, no provider was launched, and the
    result came back reporting source=model -- a check that never happened, indistinguishable
    from one that answered "this order is fine". Both return ``build``; only one of them may
    say a model said so, and only one of them may be remembered.
    """
    root = pureco(tmp_path)
    queue_item = item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA)
    result = first_contact.decide(
        project_root=root, queue_item=queue_item,
        ask_ledger=str(tmp_path / "ask-buyer.jsonl"),
        evidence_dir=tmp_path / "evidence",
        evidence_root=tmp_path / "evidence-root",
        runner=tmp_path / "no-such-runner.py",
    )
    assert result["decision"] == first_contact.BUILD
    assert result["source"].startswith("degraded:runner_missing")
    assert not (root / first_contact.CACHE_RELATIVE).exists()


def test_a_missing_schema_is_named_too(tmp_path, monkeypatch):
    root = pureco(tmp_path)
    decision, _missing, _blocker, status = first_contact.run_decider(
        first_contact.order_brief(root, item(root, title=PURECO_TITLE, request_id="91000001",
                                             sha=PURECO_SHA)),
        evidence_dir=tmp_path / "evidence",
        runner=STUB_RUNNER,
        schema=tmp_path / "no-such-schema.json",
    )
    assert (decision, status.split(":")[0]) == (first_contact.BUILD, "schema_missing")


def test_a_provider_that_answered_is_reported_as_one(tmp_path, monkeypatch):
    monkeypatch.setenv("GIG_FIRST_CONTACT_STUB", "build")
    root = 買い手B(tmp_path)
    decision, _missing, _blocker, status = first_contact.run_decider(
        first_contact.order_brief(root, item(root, title="x", request_id="91000002",
                                             sha=SHINTAMAGO_SHA)),
        evidence_dir=tmp_path / "evidence", runner=STUB_RUNNER,
    )
    assert (decision, status) == (first_contact.BUILD, "answered")


def test_an_unknown_decision_string_is_not_a_question():
    """agent_runner's schema validator does not implement enum, so this is the enforcement."""
    assert first_contact.parse_decision({"decision": "probably ask", "missing": ["x"],
                                         "blocker": "y"})[0] == first_contact.BUILD
    assert first_contact.parse_decision(None)[0] == first_contact.BUILD
    assert first_contact.parse_decision({"decision": "ask", "missing": [],
                                         "blocker": "y"})[0] == first_contact.BUILD


def test_a_question_that_cannot_name_its_reason_still_gets_one():
    decision, missing, blocker = first_contact.parse_decision(
        {"decision": "ask", "missing": ["何本必要でしょうか"], "blocker": ""})
    assert decision == first_contact.ASK
    assert missing == ["何本必要でしょうか"]
    assert blocker


# ---------------------------------------------------------------------------
# The contract with the artifact judge (A8) -- consumed, never required
# ---------------------------------------------------------------------------

def _transaction_ledger(evidence_root: Path, name: str, project_root: Path, **fields) -> None:
    directory = evidence_root / name
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"project_root": str(project_root), "finished_at": "2026-08-07T15:00:00+00:00"}
    payload.update(fields)
    (directory / "paid-work-transaction.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_the_judges_ask_the_buyer_verdict_is_honoured_without_a_second_opinion(tmp_path, monkeypatch):
    root = pureco(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    _transaction_ledger(evidence_root, "gig-pass-1", root,
                        failure_reason=first_contact.JUDGE_ASK_ERROR_FALLBACK)
    # A runner that would crash if it ran: the judge's answer must be enough.
    result = decide(root, item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA),
                    tmp_path, monkeypatch, stub="crash", evidence_root=evidence_root)
    assert result["decision"] == first_contact.ASK
    assert result["source"] == "artifact_judge"
    assert paid_work_evidence.blocked_evidence_verdict(root)[0] == paid_work_evidence.BLOCK_FRESH


def test_the_verdict_is_recognised_with_its_reason_attached(tmp_path, monkeypatch):
    root = pureco(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    _transaction_ledger(
        evidence_root, "gig-pass-1", root,
        validation={"errors": [f"{first_contact.JUDGE_ASK_ERROR_FALLBACK}:注文に指定がない"]})
    result = decide(root, item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA),
                    tmp_path, monkeypatch, stub="crash", evidence_root=evidence_root)
    assert result["decision"] == first_contact.ASK
    assert result["source"] == "artifact_judge"


def _trajectory(evidence_root: Path, name: str, rows: list[dict]) -> None:
    directory = evidence_root / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "trajectory.jsonl").write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_the_verdict_is_found_where_it_was_actually_written(tmp_path, monkeypatch):
    """★ Measured live 2026-08-08 00:05 JST, and it was not where the code looked. ★

    Order 91000001 reached the pass with delivery_action=formal, so gig_pass.sh skipped
    run_paid_work, no transaction ledger was ever opened, and the judge fired from inside
    the delivery browser. The only record of the refusal anywhere in that pass was one
    trajectory line keyed talkroom:90000001.
    """
    root = pureco(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    _trajectory(evidence_root, "gig-pass-1786114920-71583", [
        {"ts": 1786115133.455, "stage": "PAID_QUEUE_DELIVERY", "lane": "delivery",
         "resource_key": "talkroom:90000001", "action": "judge", "result": "refused",
         "ok": False, "reason": first_contact.JUDGE_ASK_ERROR_FALLBACK},
    ])
    queue_item = item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA,
                      talkroom_id="90000001")
    result = decide(root, queue_item, tmp_path, monkeypatch, stub="crash",
                    evidence_root=evidence_root)
    assert result["decision"] == first_contact.ASK
    assert result["source"] == "artifact_judge"


def test_a_judge_row_for_someone_elses_talkroom_does_not_travel(tmp_path, monkeypatch):
    root = pureco(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    _trajectory(evidence_root, "gig-pass-1", [
        {"ts": 1.0, "resource_key": "talkroom:99999999", "action": "judge", "ok": False,
         "reason": first_contact.JUDGE_ASK_ERROR_FALLBACK},
    ])
    assert first_contact.judge_already_said_ask(
        root, evidence_root, {"talkroom:90000001", "project:91000001"}) == (False, "")


def test_a_judge_row_that_passed_is_not_a_reason_to_ask(tmp_path):
    root = pureco(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    _trajectory(evidence_root, "gig-pass-1", [
        {"ts": 1.0, "resource_key": "talkroom:90000001", "action": "judge", "ok": True,
         "reason": ""},
    ])
    assert first_contact.judge_already_said_ask(
        root, evidence_root, {"talkroom:90000001"}) == (False, "")


def test_an_ordinary_failure_is_not_a_reason_to_ask(tmp_path, monkeypatch):
    root = 買い手B(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    _transaction_ledger(evidence_root, "gig-pass-1", root,
                        failure_reason="acceptance_contract_failed")
    result = decide(
        root,
        item(root, title="Canva画像4枚の編集・テンプレート化", request_id="91000002", sha=SHINTAMAGO_SHA),
        tmp_path, monkeypatch, stub="build", evidence_root=evidence_root)
    assert result["decision"] == first_contact.BUILD
    assert result["source"] == "model"


def test_a_running_attempt_is_not_read_as_history(tmp_path, monkeypatch):
    """A ledger without finished_at is this pass's own row, opened before anything ran."""
    root = 買い手B(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    directory = evidence_root / "gig-pass-now"
    directory.mkdir(parents=True)
    (directory / "paid-work-transaction.json").write_text(json.dumps({
        "project_root": str(root),
        "failure_reason": first_contact.JUDGE_ASK_ERROR_FALLBACK,
    }, ensure_ascii=False), encoding="utf-8")
    assert first_contact.judge_already_said_ask(root, evidence_root) == (False, "")


def test_another_projects_verdict_does_not_travel(tmp_path, monkeypatch):  # noqa: D103
    root = 買い手B(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    _transaction_ledger(evidence_root, "gig-pass-1", tmp_path / "somewhere-else",
                        failure_reason=first_contact.JUDGE_ASK_ERROR_FALLBACK)
    assert first_contact.judge_already_said_ask(root, evidence_root) == (False, "")


def test_the_contract_degrades_when_the_judge_is_not_there(tmp_path, monkeypatch):
    """Their file is not committed yet. A missing module may not break a paid lane."""
    monkeypatch.setattr(first_contact, "_artifact_judge_module", lambda: None)
    assert first_contact.JUDGE_ASK_ERROR_FALLBACK in first_contact.judge_ask_error_ids()
    root = 買い手B(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    _transaction_ledger(evidence_root, "gig-pass-1", root, failure_reason="something_else")
    assert first_contact.judge_already_said_ask(root, evidence_root) == (False, "")


def test_the_ids_this_module_expects_are_the_ids_the_judge_declares():
    """Pins the two halves together. Skips rather than fails while A8 is uncommitted."""
    module = first_contact._artifact_judge_module()
    declared = getattr(module, "ERROR_NEEDS_BUYER_INPUT", None) if module else None
    if not isinstance(declared, str):
        import pytest
        pytest.skip("artifact_judge does not declare an ask-the-buyer error id yet")
    assert declared in first_contact.judge_ask_error_ids()


# ---------------------------------------------------------------------------
# A10: the judge's refusal redirects instead of dead-ending
# ---------------------------------------------------------------------------
#
# Measured 2026-08-08 00:33 on the live queue: order 91000001 sat at
# delivery_action=formal, formal_delivery_checkbox=true, priority -1. gig_pass.sh enters
# run_paid_work only when TOP_ACTION != "formal", so the A7 gate could never see it. A8's
# judge refused the armed artifact every pass; ~/gig/ask-buyer.jsonl stayed at two rows.

BUYER_SPOKE_AT = "2026-08-07T14:31:10.637882+00:00"
# Not hand-computed: the first version of this constant was, and it was 16 hours out.
BUYER_SPOKE_EPOCH = datetime(2026, 8, 7, 14, 31, 10, 637882, tzinfo=timezone.utc).timestamp()


def formal_item(root: Path, **extra) -> dict:
    """91000001 as the live queue actually presented it after the wrong build."""
    payload = item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA,
                   talkroom_id="90000001")
    payload.update({
        "delivery_action": "formal",
        "formal_delivery_checkbox": True,
        "priority": -1,
        "blockers": ["formal_delivery_not_confirmed"],
        "delivery_evidence": {"package_sha256": "0303955" + "5" * 57},
    })
    payload.update(extra)
    return payload


def timed_pureco(tmp_path: Path) -> Path:
    root = pureco(tmp_path)
    path = root / "requirements" / "live-buyer-reply.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["observed_at"] = BUYER_SPOKE_AT
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return root


def judge_refusal(evidence_root: Path, *, at: float,
                  resource_key: str = "talkroom:90000001") -> None:
    _trajectory(evidence_root, f"gig-pass-{int(at)}", [
        {"ts": at, "stage": "PAID_QUEUE_DELIVERY", "lane": "delivery",
         "resource_key": resource_key, "action": "judge", "result": "refused",
         "ok": False, "reason": first_contact.JUDGE_ASK_ERROR_FALLBACK},
    ])


def test_a_formal_order_the_judge_refused_leaves_the_delivery_path(tmp_path):
    root = timed_pureco(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    judge_refusal(evidence_root, at=BUYER_SPOKE_EPOCH + 3600)
    result = first_contact.redirect_on_judge_refusal(
        project_root=root, queue_item=formal_item(root),
        ask_ledger=str(tmp_path / "ask-buyer.jsonl"), evidence_root=evidence_root)
    assert result["decision"] == first_contact.ASK
    assert result["blocked_record_written"] is True
    # The record must be one the ask lane will act on, not merely a file on disk.
    verdict, state = paid_work_evidence.blocked_evidence_verdict(root)
    assert verdict == paid_work_evidence.BLOCK_FRESH
    assert state["order_title"] == PURECO_TITLE


def test_the_artifact_is_left_exactly_where_it_was(tmp_path):
    """★ Do not unarm it. ★ Rebuilding produced the same wrong thing; this reroutes only."""
    root = timed_pureco(tmp_path)
    (root / "artifacts").mkdir(parents=True, exist_ok=True)
    artifact = root / "artifacts" / "sample-game-guide-v1.docx"
    artifact.write_bytes(b"the wrong deliverable")
    evidence_root = tmp_path / "evidence-root"
    judge_refusal(evidence_root, at=BUYER_SPOKE_EPOCH + 3600)
    first_contact.redirect_on_judge_refusal(
        project_root=root, queue_item=formal_item(root),
        ask_ledger=str(tmp_path / "ask-buyer.jsonl"), evidence_root=evidence_root)
    assert artifact.read_bytes() == b"the wrong deliverable"


def test_a_formal_order_with_no_refusal_is_never_touched(tmp_path):
    """★ The dangerous direction. ★ Kitty and 買い手B must still deliver."""
    root = 買い手B(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    _trajectory(evidence_root, "gig-pass-1", [
        {"ts": 2.0, "resource_key": "talkroom:90000002", "action": "judge", "ok": True,
         "reason": ""},
    ])
    result = first_contact.redirect_on_judge_refusal(
        project_root=root,
        queue_item=item(root, title="Canva画像4枚の編集・テンプレート化", request_id="91000002",
                        sha=SHINTAMAGO_SHA, talkroom_id="90000002", delivery_action="formal",
                        formal_delivery_checkbox=True),
        ask_ledger=str(tmp_path / "ask-buyer.jsonl"), evidence_root=evidence_root)
    assert result["decision"] == "none"
    assert not (root / ask_buyer.BLOCKED_EVIDENCE).exists()


def test_an_empty_evidence_tree_never_diverts(tmp_path):
    root = 買い手B(tmp_path)
    result = first_contact.redirect_on_judge_refusal(
        project_root=root,
        queue_item=item(root, title="x", request_id="91000002", sha=SHINTAMAGO_SHA,
                        talkroom_id="90000002", delivery_action="formal"),
        ask_ledger=str(tmp_path / "ask-buyer.jsonl"),
        evidence_root=tmp_path / "does-not-exist")
    assert result["decision"] == "none"


def test_one_question_per_order_across_the_redirect(tmp_path):
    root = timed_pureco(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    judge_refusal(evidence_root, at=BUYER_SPOKE_EPOCH + 3600)
    ledger = tmp_path / "ask-buyer.jsonl"
    queue_item = formal_item(root)

    first = first_contact.redirect_on_judge_refusal(
        project_root=root, queue_item=queue_item, ask_ledger=str(ledger),
        evidence_root=evidence_root)
    assert first["decision"] == first_contact.ASK

    ledger.write_text(json.dumps(
        {"talkroom_id": "90000001", "blocker_key": PURECO_SHA}, ensure_ascii=False) + "\n",
        encoding="utf-8")

    second = first_contact.redirect_on_judge_refusal(
        project_root=root, queue_item=queue_item, ask_ledger=str(ledger),
        evidence_root=evidence_root)
    # Still diverted -- the wrong artifact must not be delivered -- but no second question.
    assert second["decision"] == first_contact.AWAIT
    assert second["source"] == "already_asked"


def test_the_ask_lane_plans_exactly_one_question_after_the_redirect(tmp_path):
    """The queue the send path reads, not just our own bookkeeping."""
    import argparse
    root = timed_pureco(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    judge_refusal(evidence_root, at=BUYER_SPOKE_EPOCH + 3600)
    ledger = tmp_path / "ask-buyer.jsonl"
    output = tmp_path / "ask-buyer-queue.json"
    first_contact.redirect_on_judge_refusal(
        project_root=root, queue_item=formal_item(root), ask_ledger=str(ledger),
        evidence_root=evidence_root)
    args = argparse.Namespace(project_root=str(root), talkroom_id="90000001",
                              ledger=str(ledger), output=str(output))
    assert ask_buyer_pass.build(args) == 0
    assert len(json.loads(output.read_text(encoding="utf-8"))["items"]) == 1
    ledger.write_text(json.dumps(
        {"talkroom_id": "90000001", "blocker_key": PURECO_SHA}, ensure_ascii=False) + "\n",
        encoding="utf-8")
    assert ask_buyer_pass.build(args) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["items"] == []


# --- the verdict has to expire, or one refusal locks the order out forever ---

def test_a_verdict_the_buyer_has_answered_is_spent(tmp_path):
    """★ Without this, one refusal is permanent. ★

    Order refused as underspecified, we ask, the buyer answers in full, the builder is
    ready -- and the same row on disk would send it straight back to asking, forever.
    """
    root = timed_pureco(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    judge_refusal(evidence_root, at=BUYER_SPOKE_EPOCH - 3600)  # recorded BEFORE they wrote
    result = first_contact.redirect_on_judge_refusal(
        project_root=root, queue_item=formal_item(root),
        ask_ledger=str(tmp_path / "ask-buyer.jsonl"), evidence_root=evidence_root)
    assert result["decision"] == "none"
    assert not (root / ask_buyer.BLOCKED_EVIDENCE).exists()


def test_a_verdict_recorded_after_the_buyer_spoke_still_counts(tmp_path):
    root = timed_pureco(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    judge_refusal(evidence_root, at=BUYER_SPOKE_EPOCH + 1)
    result = first_contact.redirect_on_judge_refusal(
        project_root=root, queue_item=formal_item(root),
        ask_ledger=str(tmp_path / "ask-buyer.jsonl"), evidence_root=evidence_root)
    assert result["decision"] == first_contact.ASK


def test_the_pre_build_gate_uses_the_same_expiry(tmp_path, monkeypatch):
    """Otherwise the gate asks again the moment the buyer finally answers."""
    root = timed_pureco(tmp_path)
    evidence_root = tmp_path / "evidence-root"
    judge_refusal(evidence_root, at=BUYER_SPOKE_EPOCH - 3600)
    result = decide(root, item(root, title=PURECO_TITLE, request_id="91000001",
                               sha=PURECO_SHA, talkroom_id="90000001"),
                    tmp_path, monkeypatch, stub="build", evidence_root=evidence_root)
    assert result["source"] == "model"


def test_an_undateable_verdict_is_not_silently_dropped(tmp_path):
    """A verdict we cannot date is still a verdict; the ask ledger bounds the damage."""
    assert first_contact._verdict_still_open(None, BUYER_SPOKE_EPOCH) is True
    assert first_contact._verdict_still_open(BUYER_SPOKE_EPOCH, None) is True
    assert first_contact.iso_epoch(BUYER_SPOKE_AT) == BUYER_SPOKE_EPOCH
    assert first_contact.iso_epoch("not a date") is None
    assert first_contact.iso_epoch("") is None


# ---------------------------------------------------------------------------
# Nothing internal reaches the buyer
# ---------------------------------------------------------------------------

def test_what_is_written_down_carries_no_internal_tokens(tmp_path, monkeypatch):
    """Everything in the record is quoted into the buyer's message by question_prompt."""
    import buyer_voice
    root = pureco(tmp_path)
    decide(root, item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA),
           tmp_path, monkeypatch, stub="ask")
    state = ask_buyer.blocked_state(root)
    quoted = "\n".join([str(state.get("blocker") or ""), *ask_buyer.missing_items(state),
                        str(state.get("order_title") or "")])
    assert buyer_voice.check_style(quoted) == []


def test_the_records_own_path_stays_inside_the_project(tmp_path, monkeypatch):
    root = pureco(tmp_path)
    decide(root, item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA),
           tmp_path, monkeypatch, stub="ask")
    state = ask_buyer.blocked_state(root)
    assert Path(state["requirements_path"]).resolve().is_relative_to(root.resolve())


# ---------------------------------------------------------------------------
# The 48-hour clock
# ---------------------------------------------------------------------------

def test_an_uncontacted_order_at_the_queue_head_reaches_this_path(tmp_path, monkeypatch):
    """A5 promotes it; this is what finally speaks in the room before it is cancelled."""
    sys.path.insert(0, str(SKILL / "scripts"))
    import delivery_queue
    from datetime import datetime, timezone

    root = pureco(tmp_path)
    queue_item = item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA)
    now = datetime(2026, 8, 7, 14, 40, tzinfo=timezone.utc)
    assert delivery_queue.first_contact_at_risk(queue_item, now) is True

    result = decide(root, queue_item, tmp_path, monkeypatch, stub="ask")
    assert result["decision"] == first_contact.ASK

    # And once we have spoken, the clock is no longer running.
    spoken = dict(queue_item, seller_message_observed=True)
    assert delivery_queue.first_contact_at_risk(spoken, now) is False


def test_the_gate_only_looks_at_orders_with_nothing_built(tmp_path):
    """delivery_action is the loop's own name for "the buyer is waiting on an artifact"."""
    root = pureco(tmp_path)
    brief = first_contact.order_brief(
        root, item(root, title=PURECO_TITLE, request_id="91000001", sha=PURECO_SHA))
    assert brief["delivery_action"] == "work_required"
    assert brief["seller_message_observed"] is False
    assert brief["contact_deadline"] == "2026-08-09T23:00:00+09:00"
