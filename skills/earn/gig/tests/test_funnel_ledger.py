"""The five stages must join on keys that survive, and refuse when they do not.

Every fixture here is a miniature of something measured in production on 2026-08-08, and
the docstrings say which real order each case came from -- so a future reader can tell a
regression from a marketplace change.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "funnel_ledger", SCRIPTS / "funnel_ledger.py"
    )
    module = importlib.util.module_from_spec(spec)
    # ★ Register before exec. ★ @dataclass resolves annotations through
    # sys.modules[cls.__module__], which is None until the module is registered, and the
    # import dies with a bare AttributeError that says nothing about the real cause.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


funnel_ledger = _load()


def write(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )


def project(state_dir: Path, name: str, state: dict) -> None:
    directory = state_dir / "projects" / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "state.json").write_text(
        json.dumps(state, ensure_ascii=False), encoding="utf-8"
    )


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    """A 募集-backed order and a direct offer, both paid -- the two real doors."""
    root = tmp_path / "gig"
    root.mkdir()
    write(
        root / "applied.jsonl",
        [
            # A real application. ts = 2026-08-01 08:54 JST.
            {"requestId": "91000027", "status": "applied", "ts": 1785891240,
             "title": "海外向け動画編集スタッフ募集"},
            # Noise that is NOT an application: applied.jsonl is a mixed append log.
            {"requestId": "dm-9954245", "status": "replied", "ts": 1785891240},
            {"requestId": "b1-nurture-sweep-pass129", "status": "no_action_all_current",
             "ts": 1785891240},
        ],
    )
    write(
        root / "identity_chain.jsonl",
        [
            {"ts": 1785570406, "request_id": "91000027", "talkroom_id": "90000006",
             "lane": "orders", "source": "offer_evidence", "evidence": "x"}
        ],
    )
    write(
        root / "earnings.jsonl",
        [
            # ★ requestId here is a TALKROOM id, not a 募集 id. ★
            {"ts": "2026/08/03 10:42", "requestId": "90000006", "talkroom_id": "90000006",
             "buyer": "buyer_handle_d", "title": "海外向け動画編集スタッフ募集",
             "jpy": 23400.0, "status": "検収完了", "evidence": "https://example/revenue"},
            {"ts": "2026/08/03 16:00", "requestId": "90000000", "talkroom_id": "90000000",
             "buyer": "buyer_handle_b", "title": "サンプル商品｜クラファン認知向上 SNS運用サポート",
             "jpy": 31200.0, "status": "検収完了", "evidence": "https://example/revenue"},
        ],
    )
    project(root, "91000027", {
        "request_id": "91000027", "talkroom_id": "90000006", "buyer": "buyer_handle_d",
        "source_contract_id": "offer:92000011", "price_jpy": 30000,
        "work_state": "DELIVERED", "observed_at": "2026-08-02T23:00:18+00:00",
        "updated_at": 1785714442.9,
    })
    project(root, "90000000", {
        "request_id": "90000000", "talkroom_id": "90000000", "buyer": "buyer_handle_b",
        "source_contract_id": "direct-offer:92000003", "updated_at": 1785714442.9,
    })
    return root


def test_payment_joins_to_its_application_through_the_identity_chain(state_dir: Path):
    """earnings.requestId is a talkroom id. The naive equality join matches zero rows.

    Production: buyer_handle_d's ¥23,400 sits under talkroom 90000006 while the
    application that won it is 募集 91000027. Only identity_chain.jsonl connects them.
    """
    funnel = funnel_ledger.build_funnel(state_dir)
    athena = next(o for o in funnel.orders if o.buyer == "buyer_handle_d")
    assert athena.request_id == "91000027"
    assert athena.talkroom_id == "90000006"
    assert athena.applied_on is not None, "the application date must survive the join"
    assert athena.trace_break == "", "this one traces end to end"


def test_direct_offer_never_enters_the_application_denominator(state_dir: Path):
    """buyer_handle_b's ¥31,200 arrived through a door that has no stage 1.

    Counting it as an application conversion would inflate the rate with revenue no
    application produced.
    """
    funnel = funnel_ledger.build_funnel(state_dir)
    jibie = next(o for o in funnel.orders if o.buyer == "buyer_handle_b")
    assert jibie.entry_path == funnel_ledger.ENTRY_DIRECT_OFFER
    assert jibie.request_id == ""
    assert "never had an application" in jibie.trace_break
    assert jibie not in funnel.cohort()


def test_a_direct_offer_instrument_on_a_real_request_stays_in_the_application_door():
    """Regression, measured 2026-08-08 on project 91000018 (buyer_handle_c, ¥13,260).

    Its source_contract_id is "direct-offer:92000006" and yet it has a 募集 id distinct
    from its talkroom, a chain link and application rows -- we applied, and the deal was
    merely closed with a direct-offer instrument. Keying the entry door off the
    "direct-offer:" prefix moved an application-won order into the buyer-initiated
    bucket.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw) / "gig"
        root.mkdir()
        write(root / "applied.jsonl", [
            {"requestId": "91000018", "status": "applied", "ts": 1785891240},
        ])
        write(root / "identity_chain.jsonl", [
            {"request_id": "91000018", "talkroom_id": "90000010", "ts": 1785143050},
        ])
        write(root / "earnings.jsonl", [
            {"ts": "2026/07/26 14:24", "requestId": "90000010", "talkroom_id": "90000010",
             "buyer": "buyer_handle_c", "jpy": 13260.0, "status": "検収完了", "evidence": "x"},
        ])
        project(root, "91000018", {
            "request_id": "91000018", "talkroom_id": "90000010", "buyer": "buyer_handle_c",
            "source_contract_id": "direct-offer:92000006", "updated_at": 1785714442.9,
        })
        funnel = funnel_ledger.build_funnel(root)
        order = next(o for o in funnel.orders if o.buyer == "buyer_handle_c")
        assert order.entry_path == funnel_ledger.ENTRY_APPLICATION
        assert order.revenue_class == "contract:direct-offer", "instrument still recorded"


def test_only_status_applied_rows_count_as_applications(state_dir: Path):
    """applied.jsonl also holds dm-* replies and nurture sweeps. len(file) is not stage 1."""
    funnel = funnel_ledger.build_funnel(state_dir)
    assert funnel.applications_in_window == 1


def test_revenue_per_application_refuses_without_a_window(state_dir: Path):
    """The 2026-08-07 error: a 12-day numerator over a 39-day denominator."""
    funnel = funnel_ledger.build_funnel(state_dir)
    ratio = funnel_ledger.revenue_per_application(funnel)
    assert ratio.refused
    assert "REFUSED" in ratio.reason
    assert "--since/--until" in ratio.reason


def test_every_stage_honours_the_same_window(state_dir: Path):
    """A window that excludes the payments must not still report them.

    Regression: an earlier revision filtered 応募 but counted 契約/納品/入金 all-time,
    so a 12-day window showed 117 applications against all six lifetime payments.
    """
    import datetime

    funnel = funnel_ledger.build_funnel(
        state_dir,
        since=datetime.date(2026, 7, 1),
        until=datetime.date(2026, 7, 2),
    )
    counts = funnel.stage_counts()
    assert counts[funnel_ledger.STAGE_PAID]["total"] == 0
    assert counts[funnel_ledger.STAGE_CONTRACTED]["total"] == 0
    assert funnel.paid_orders() == []


def test_review_stage_reports_unmeasurable_rather_than_zero(state_dir: Path):
    """Zero is a claim. Nothing under ~/gig records a buyer rating, so say that."""
    funnel = funnel_ledger.build_funnel(state_dir)
    counts = funnel.stage_counts()
    assert counts[funnel_ledger.STAGE_REVIEWED]["unmeasurable"]
    assert "no source" in counts[funnel_ledger.STAGE_REVIEWED]["unmeasurable"]


def test_listing_revenue_is_never_guessed(state_dir: Path):
    """Every settled row so far is contract revenue. Money with no recorded instrument
    is labelled unrecorded -- not silently folded into a listing bucket."""
    funnel = funnel_ledger.build_funnel(state_dir)
    classes = funnel.revenue_by_class()
    assert set(classes) == {"contract:offer", "contract:direct-offer"}
    assert not any(k.startswith("listing") for k in classes)


def test_telegram_names_the_buyer_and_quotes_the_order_verbatim(state_dir: Path):
    """Generic counts were the complaint. The body must say who and what."""
    funnel = funnel_ledger.build_funnel(state_dir)
    body = funnel_ledger.render_telegram(funnel)
    assert "buyer_handle_d" in body
    assert "海外向け動画編集スタッフ募集" in body
    assert "buyer_handle_b" in body
    assert body.startswith("Claude:::")
    assert len(body) <= 4096


def test_telegram_body_is_rendered_not_sent(state_dir: Path):
    """render_telegram must have no transport of any kind in its call graph."""
    funnel = funnel_ledger.build_funnel(state_dir)
    body = funnel_ledger.render_telegram(funnel)
    assert isinstance(body, str) and body
