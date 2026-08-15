"""A5-①: an application that does not record the market is not recordable.

Measured before this change: `bid_jpy` was on 0 of 311 rows of ~/gig/applied.jsonl
and `price_jpy` on 95 (30%). All 90 loss rows carried no price at all, so the 8
joinable (price, outcome) pairs were all losses and no pricing model could be fitted
-- not badly, but at all. The B2 prompt has asked for `price_jpy` since X8b and the
compliance is what it is. Prompting failed, so this is code.

The rule enforced here is the one `application_report` already applies to identity:
THE MODEL REPORTS, THE CODE WRITES THE LEDGER. The market is not taken from the
model's report at all -- it is read from the evidence the submit path wrote at the
moment of the irreversible click, off the page itself.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REQUEST_ID = "91000062"


def write_eligibility_evidence(
    directory: Path,
    *,
    request_id: str = REQUEST_ID,
    market: dict | None = None,
) -> Path:
    """Write the sidecar the real submit path writes, in its real shape."""
    snapshot = load("market_snapshot")
    payload = {
        "version": 1,
        "allowed": True,
        "reason_codes": [],
        "signals": {},
        "request_id": request_id,
        "bucket": "single",
        "opportunity_url": f"https://coconala.com/requests/{request_id}",
        "market": market if market is not None else snapshot.parse_market(
            "予算\n1万円\n〜\n3万円\n"
            "募集期限\n締切日 2026年8月7日 / 掲載日 2026年7月28日\n"
            "応募状況\n応募人数 26\n契約人数 0\n閲覧数 348\n"
            "募集者情報\ntyogvii\n発注実績\n7\n発注件数\n61%\n発注率\n100%\n取引完了率\n"
            "認証状況\n",
            now=1_785_000_000.0,
            bid_jpy=18_000,
        ),
    }
    path = directory / f"gig-72130-B2-{request_id}-submitted.eligibility.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_a_recorded_application_carries_the_market_it_bid_into(tmp_path) -> None:
    report = load("application_report")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    write_eligibility_evidence(evidence)

    rows, _stats = report.plan(
        report=[{"request_id": REQUEST_ID, "category": "自動化ツール作成"}],
        existing_rows=[],
        proven={REQUEST_ID},
        dom_categories={},
        now=1_785_000_100.0,
        pass_id="72130",
        markets=report.read_markets(evidence, evidence),
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["bid_jpy"] == 18_000
    assert row["budget_lo_jpy"] == 10_000
    assert row["budget_hi_jpy"] == 30_000
    assert row["budget_is_quote_request"] is False
    assert row["applicants_at_bid"] == 26
    assert row["client_order_rate"] == 61
    assert row["client_order_count"] == 7
    assert row["views"] == 348
    assert row["market_source"] == "submit_evidence"
    assert row["market_missing"] == {}


def test_no_application_row_can_exist_without_the_market_keys(tmp_path) -> None:
    """The structural claim: every write path stamps the full field set.

    Not "the happy path stamps it" -- the reported row, the row the model already
    wrote itself, the row recovered from a screenshot after a silent model, and the
    row recovered from a lost-ACK intent. Any one of them omitting the keys is a
    row no learner can join, which is the entire failure being fixed.
    """
    report = load("application_report")
    required = set(report.MARKET_LEDGER_FIELDS)
    evidence = tmp_path / "evidence"
    evidence.mkdir()

    reported, _stats = report.plan(
        report=[{"request_id": REQUEST_ID}],
        existing_rows=[],
        proven={REQUEST_ID},
        dom_categories={},
        now=1_785_000_100.0,
        pass_id="72130",
        markets={},
    )
    enriched, _stats2 = report.plan(
        report=[{"request_id": REQUEST_ID, "category": "自動化ツール作成"}],
        existing_rows=[{"requestId": REQUEST_ID, "status": "applied"}],
        proven={REQUEST_ID},
        dom_categories={},
        now=1_785_000_100.0,
        pass_id="72130",
        markets={},
    )
    recovered, _count = report.recover_from_proofs(
        existing_rows=[],
        request_ids={"91000060"},
        now=1_785_000_100.0,
        pass_id="72130",
        markets={},
    )
    from_intent, _count2 = report.recover_from_intents(
        existing_rows=[],
        intents={
            "91000061": {
                "request_id": "91000061",
                "url": "https://coconala.com/requests/91000061",
                "title": "t",
                "evidence": "gig-72130-B2-91000061-submitted.intent.json",
            }
        },
        now=1_785_000_100.0,
        pass_id="72130",
        markets={},
    )

    for label, rows in (
        ("reported", reported),
        ("enriched", enriched),
        ("proof_recovered", recovered),
        ("intent_recovered", from_intent),
    ):
        assert rows, label
        for row in rows:
            assert required <= set(row), (label, sorted(required - set(row)))


def test_an_unrecorded_market_is_an_explicit_null_with_a_reason(tmp_path) -> None:
    """Silence about the market is not allowed to look like a market of nothing."""
    report = load("application_report")

    rows, _stats = report.plan(
        report=[{"request_id": REQUEST_ID}],
        existing_rows=[],
        proven={REQUEST_ID},
        dom_categories={},
        now=1_785_000_100.0,
        pass_id="72130",
        markets={},
    )

    row = rows[0]
    assert row["bid_jpy"] is None
    assert row["client_order_rate"] is None
    assert row["market_source"] is None
    for field in report.MARKET_LEDGER_FIELDS:
        if field in {"market_source", "market_missing"}:
            continue
        assert row["market_missing"][field] == "submit_evidence_absent"


def test_a_field_the_page_did_not_state_is_null_with_its_own_reason(
    tmp_path,
) -> None:
    """A 見積り希望 budget is a stated absence and must not read as an absent row."""
    report = load("application_report")
    snapshot = load("market_snapshot")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    write_eligibility_evidence(
        evidence,
        market=snapshot.parse_market(
            "予算\n見積り希望\n"
            "募集期限\n締切日 2026年8月7日 / 掲載日 2026年7月28日\n"
            "応募状況\n応募人数 12\n契約人数 0\n"
            "募集者情報\nx\n発注実績\n162\n発注件数\n69%\n発注率\n77%\n取引完了率\n認証状況\n",
            now=1_785_000_000.0,
            bid_jpy=None,
        ),
    )

    rows, _stats = report.plan(
        report=[{"request_id": REQUEST_ID}],
        existing_rows=[],
        proven={REQUEST_ID},
        dom_categories={},
        now=1_785_000_100.0,
        pass_id="72130",
        markets=report.read_markets(evidence, evidence),
    )

    row = rows[0]
    assert row["budget_is_quote_request"] is True
    assert row["budget_hi_jpy"] is None
    assert row["market_missing"]["budget_hi_jpy"] == "budget_is_quote_request"
    # 閲覧数 was not on this page at all -- a different reason from the budget's.
    assert row["views"] is None
    assert row["market_missing"]["views"] == "field_absent_from_page"
    # The bid was never observed on the form. That is stated too.
    assert row["bid_jpy"] is None
    assert row["market_missing"]["bid_jpy"] == "field_absent_from_page"
    assert row["client_order_rate"] == 69


def test_market_evidence_is_bound_to_the_request_it_was_written_for(
    tmp_path,
) -> None:
    """A sidecar names its own request_id. A filename is never trusted for identity."""
    report = load("application_report")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    path = write_eligibility_evidence(evidence)
    payload = json.loads(path.read_text())
    payload["request_id"] = "9999999"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    markets = report.read_markets(evidence, evidence)

    assert REQUEST_ID not in markets
    assert "9999999" in markets


def test_the_bid_travels_from_the_form_to_the_ledger_without_the_model(
    tmp_path,
) -> None:
    """The whole chain, end to end: price input -> sidecar -> ledger row.

    Each half of this is covered above, but the seam is the part that has failed
    before: X8b's `applications` contract was correct and the ledger still got no
    price, because nothing carried the value across. Here the model reports only a
    request_id and the bid still lands.
    """
    import asyncio  # noqa: PLC0415
    from unittest import mock  # noqa: PLC0415

    import test_cdp_nav_snapshot_observe as harness  # noqa: PLC0415

    report = load("application_report")
    request_id = "91000026"
    form_url = f"https://coconala.com/offers/add/{request_id}"

    class PricedForm(harness.FakeSocket):
        """The same fake, plus the number a filled 応募 form actually holds."""

        async def send(self, raw: str) -> None:
            await super().send(raw)
            if not self.pending:
                return
            try:
                payload = json.loads(self.pending[-1])
                state = json.loads(payload["result"]["result"]["value"])
            except (KeyError, TypeError, ValueError):
                return
            if not isinstance(state, dict) or "form_filled" not in state:
                return
            state["bid_jpy"] = "24000"
            payload["result"]["result"]["value"] = json.dumps(
                state, ensure_ascii=False
            )
            self.pending[-1] = json.dumps(payload)

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    page = PricedForm(form_url, application_submission=True)
    with mock.patch.object(
        harness.module.websockets,
        "connect",
        return_value=harness.FakeConnection(page),
    ):
        asyncio.run(harness.module.submit_application(
            "ws://127.0.0.1:9223/devtools/page/leased-target",
            request_id,
            evidence / f"gig-72130-B2-{request_id}-submitted.png",
            evidence / f"gig-72130-B2-{request_id}-submitted.json",
            wait_seconds=0,
            opportunity_brief=harness.ELIGIBLE_BRIEF,
        ))

    rows, _stats = report.plan(
        report=[{"request_id": request_id}],
        existing_rows=[],
        proven={request_id},
        dom_categories={},
        now=1_785_000_100.0,
        pass_id="72130",
        markets=report.read_markets(evidence, evidence),
    )

    assert rows[0]["bid_jpy"] == 24_000
    assert rows[0]["budget_hi_jpy"] == 30_000
    assert rows[0]["client_order_rate"] == 61
    assert rows[0]["market_source"] == "submit_evidence"


def test_the_application_proof_recovery_path_is_untouched(tmp_path) -> None:
    """normalize_applied's screenshot glob is what stops re-applying to won jobs."""
    report = load("application_report")
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / f"gig-72130-B2-{REQUEST_ID}-submitted.png").write_bytes(b"png")

    assert REQUEST_ID in report._proven_ids(evidence)
    assert REQUEST_ID in report._fresh_proven_ids(evidence, 0.0)
