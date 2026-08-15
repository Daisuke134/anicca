import importlib.util
import json
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _checkpoint_module(name: str):
    return load(SCRIPTS / "checkpoint_via_tg.py", name)


def _outbox(tmp_path, name="checkpoint-outbox"):
    outbox_module = load(SCRIPTS / "telegram_outbox.py", f"{name}-outbox")
    return outbox_module.TelegramOutbox(tmp_path / "telegram.sqlite3")


def _context(**overrides):
    base = {
        "request_summary": "ロゴデザイン(3案・AI形式)の依頼",
        "deliverable_ref": "~/gig/projects/91000002/artifacts/v3.zip",
        "recommendation": "やり直し(網羅性が低いため再生成を推奨)",
    }
    base.update(overrides)
    return base


def test_send_checkpoint_writes_pending_state_and_sends_once(tmp_path):
    checkpoint = _checkpoint_module("checkpoint_send_pending")
    outbox = _outbox(tmp_path)
    sent = []
    transport = lambda message: (sent.append(message), "tg-1")[1]

    record = checkpoint.send_checkpoint(
        gig_dir=tmp_path,
        checkpoint_id="fixture-1",
        question="この取引をキャンセルして返金する?",
        options=["はい", "いいえ"],
        context=_context(),
        outbox=outbox,
        transport=transport,
        now_epoch=1000,
    )

    assert record["status"] == "pending"
    assert record["checkpoint_id"] == "fixture-1"
    assert record["send_status"] == "sent"
    assert record["message_id"] == "tg-1"
    assert len(sent) == 1
    assert "はい / いいえ" in sent[0]
    # The three decision-context fields must all appear in the message itself.
    assert "依頼内容: ロゴデザイン(3案・AI形式)の依頼" in sent[0]
    assert "対象: ~/gig/projects/91000002/artifacts/v3.zip" in sent[0]
    assert "ループの推奨: やり直し(網羅性が低いため再生成を推奨)" in sent[0]

    on_disk = json.loads((tmp_path / "checkpoints" / "fixture-1.json").read_text())
    assert on_disk["status"] == "pending"
    assert on_disk["context"]["request_summary"].startswith("ロゴデザイン")


def test_send_checkpoint_is_idempotent_and_never_resends(tmp_path):
    checkpoint = _checkpoint_module("checkpoint_send_idempotent")
    outbox = _outbox(tmp_path)
    sent = []
    transport = lambda message: (sent.append(message), "tg-1")[1]

    first = checkpoint.send_checkpoint(
        gig_dir=tmp_path, checkpoint_id="fixture-2", question="q?", options=["はい"],
        context=_context(), outbox=outbox, transport=transport, now_epoch=1000,
    )
    second = checkpoint.send_checkpoint(
        gig_dir=tmp_path, checkpoint_id="fixture-2", question="q?", options=["はい"],
        context=_context(), outbox=outbox, transport=transport, now_epoch=2000,
    )

    assert first == second
    assert len(sent) == 1  # a second call must never re-send


def test_send_refuses_missing_or_empty_decision_context(tmp_path):
    """A question without its decision context is noise Dais cannot act on."""
    checkpoint = _checkpoint_module("checkpoint_send_missing_context")
    outbox = _outbox(tmp_path)
    sent = []
    transport = lambda message: (sent.append(message), "tg-1")[1]

    for bad_context in (
        {},  # nothing at all
        _context(request_summary=""),
        _context(deliverable_ref="   "),
        _context(recommendation=None),
        "not a dict",
    ):
        with pytest.raises(ValueError):
            checkpoint.send_checkpoint(
                gig_dir=tmp_path, checkpoint_id="fixture-bad", question="q?",
                options=["はい"], context=bad_context,
                outbox=outbox, transport=transport, now_epoch=1000,
            )
    assert sent == []  # fail-closed: nothing left the machine
    assert not (tmp_path / "checkpoints").exists()  # and no pending state either


def test_send_refuses_placeholder_context_the_live_test_message_had(tmp_path):
    """Pins the exact 2026-08-08 failure: the live wiring-test message reached Dais
    with 不明点/project unfilled ('不明' where the score should be, no usable
    project reference). Any required field carrying a recognizable placeholder
    must refuse to send.
    """
    checkpoint = _checkpoint_module("checkpoint_send_placeholder")
    outbox = _outbox(tmp_path)
    sent = []
    transport = lambda message: (sent.append(message), "tg-1")[1]

    for placeholder in ("不明", "不明点", "TBD", "n/a", "unknown", "-", "?"):
        with pytest.raises(ValueError, match="empty or placeholder"):
            checkpoint.send_checkpoint(
                gig_dir=tmp_path, checkpoint_id="fixture-ph", question="q?",
                options=["はい"], context=_context(request_summary=placeholder),
                outbox=outbox, transport=transport, now_epoch=1000,
            )
        with pytest.raises(ValueError, match="empty or placeholder"):
            checkpoint.send_checkpoint(
                gig_dir=tmp_path, checkpoint_id="fixture-ph", question="q?",
                options=["はい"], context=_context(deliverable_ref=placeholder),
                outbox=outbox, transport=transport, now_epoch=1000,
            )
    assert sent == []
    assert not (tmp_path / "checkpoints").exists()


def test_poll_unknown_checkpoint_returns_none(tmp_path):
    checkpoint = _checkpoint_module("checkpoint_poll_unknown")
    result = checkpoint.poll_checkpoint_reply(
        gig_dir=tmp_path, checkpoint_id="never-asked", read_bubbles=lambda: [],
    )
    assert result is None


def test_poll_stays_pending_when_newest_bubble_is_not_dais(tmp_path):
    checkpoint = _checkpoint_module("checkpoint_poll_not_owner")
    outbox = _outbox(tmp_path)
    checkpoint.send_checkpoint(
        gig_dir=tmp_path, checkpoint_id="fixture-3", question="q?", options=["はい", "いいえ"],
        context=_context(), outbox=outbox, transport=lambda message: "tg-1", now_epoch=1000,
    )

    result = checkpoint.poll_checkpoint_reply(
        gig_dir=tmp_path, checkpoint_id="fixture-3",
        read_bubbles=lambda: [{"from": "peer", "text": "はい"}],
    )

    assert result["status"] == "pending"


def test_poll_ignores_a_reply_that_matches_no_option(tmp_path):
    checkpoint = _checkpoint_module("checkpoint_poll_no_match")
    outbox = _outbox(tmp_path)
    checkpoint.send_checkpoint(
        gig_dir=tmp_path, checkpoint_id="fixture-4", question="q?", options=["はい", "いいえ"],
        context=_context(), outbox=outbox, transport=lambda message: "tg-1", now_epoch=1000,
    )

    result = checkpoint.poll_checkpoint_reply(
        gig_dir=tmp_path, checkpoint_id="fixture-4",
        read_bubbles=lambda: [{"from": "dais", "text": "了解、あとで見る"}],
    )

    assert result["status"] == "pending"


def test_poll_resolves_to_answered_on_the_newest_owner_bubble(tmp_path):
    checkpoint = _checkpoint_module("checkpoint_poll_answered")
    outbox = _outbox(tmp_path)
    checkpoint.send_checkpoint(
        gig_dir=tmp_path, checkpoint_id="fixture-5", question="q?", options=["はい", "いいえ"],
        context=_context(), outbox=outbox, transport=lambda message: "tg-1", now_epoch=1000,
    )

    result = checkpoint.poll_checkpoint_reply(
        gig_dir=tmp_path, checkpoint_id="fixture-5",
        read_bubbles=lambda: [
            {"from": "peer", "text": "❓ この取引をキャンセルして返金する?"},
            {"from": "dais", "text": "はい、進めて"},
        ],
        now_epoch=1500,
    )

    assert result["status"] == "answered"
    assert result["matched_option"] == "はい"
    assert result["reply_text"] == "はい、進めて"
    assert result["answered_at"] == 1500

    on_disk = json.loads((tmp_path / "checkpoints" / "fixture-5.json").read_text())
    assert on_disk["status"] == "answered"


def test_poll_on_an_already_answered_checkpoint_is_a_noop(tmp_path):
    checkpoint = _checkpoint_module("checkpoint_poll_already_answered")
    outbox = _outbox(tmp_path)
    checkpoint.send_checkpoint(
        gig_dir=tmp_path, checkpoint_id="fixture-6", question="q?", options=["はい", "いいえ"],
        context=_context(), outbox=outbox, transport=lambda message: "tg-1", now_epoch=1000,
    )
    checkpoint.poll_checkpoint_reply(
        gig_dir=tmp_path, checkpoint_id="fixture-6",
        read_bubbles=lambda: [{"from": "dais", "text": "はい"}],
        now_epoch=1500,
    )

    calls = []
    result = checkpoint.poll_checkpoint_reply(
        gig_dir=tmp_path, checkpoint_id="fixture-6",
        read_bubbles=lambda: calls.append(1) or [{"from": "dais", "text": "いいえ"}],
        now_epoch=9999,
    )

    assert result["status"] == "answered"
    assert result["matched_option"] == "はい"  # first answer wins, never overwritten
    assert calls == []  # already resolved: no reason to call the reader again


def test_no_consumer_is_wired_anywhere():
    """The hard rule in the module docstring, enforced: no delivery-path file may
    import or call this module, and the rejected quality-gate consumer
    (notify_predelivery_score_low) must not exist at all. Quality issues are
    never a human question -- the loop rebuilds instead (Dais 2026-08-09).
    """
    module_source = (SCRIPTS / "checkpoint_via_tg.py").read_text(encoding="utf-8")
    assert "def notify_predelivery_score_low" not in module_source

    for browser in ("coconala_formal_delivery_browser.py", "coconala_paid_progress_browser.py"):
        source = (SCRIPTS / browser).read_text(encoding="utf-8")
        assert "checkpoint_via_tg" not in source, f"{browser} must not consume the checkpoint"
        assert "notify_predelivery_score_low" not in source
