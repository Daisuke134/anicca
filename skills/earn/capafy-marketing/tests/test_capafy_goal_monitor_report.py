import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from test_capafy_event_projection import fixture_events


SCRIPT = Path(__file__).parents[1] / "scripts" / "capafy_outcome.py"
OWNER_SCRIPT = Path(__file__).parents[1] / "scripts" / "capafy_owner_report.py"


def company_state_payload(*, paid_orders: object, orders: object = 5) -> dict:
    return {
        "schema_version": 1,
        "kind": "company_state",
        "as_of": "2026-08-13T12:00:00Z",
        "date": "2026-08-13",
        "last_event_id": "capafy:order.received:test",
        "projection_id": "sha256:" + "d" * 64,
        "inventory": {"online": 1, "under_review": 0, "draft": 0, "rejected": 0},
        "orders": orders,
        "paid_orders": paid_orders,
        "gross_usd": "19.98",
        "pending_usd": "0.00",
        "realized_usd": "0.00",
        "mrr_usd": "0.00",
        "cost_usd": "0.00",
        "contribution_usd": "0.00",
        "account": {
            "handle": "no-active-account",
            "lifecycle_status": "unknown",
            "capability": "none",
            "session_established": False,
            "post_write_session_verified": False,
            "account_status": "clean",
        },
        "marketing": {"public_post_url": None, "campaign_url": None},
        "metrics": {},
        "incident": None,
        "listing_url": None,
        "dashboard_url": "https://capafy-skills-daily.netlify.app/company/",
    }


def render(payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "render"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def owner_report(command: str, payload: dict, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(OWNER_SCRIPT), command, *args],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def owner_state(**changes: object) -> dict:
    state = {
        "schema_version": 1,
        "kind": "company_state",
        "as_of": "2026-08-13T08:00:00Z",
        "date": "2026-08-13",
        "last_event_id": "capafy:metrics.read:2026-08-13",
        "projection_id": "sha256:" + "e" * 64,
        "inventory": {"online": 21, "under_review": 0, "draft": 2, "rejected": 9},
        "orders": 5,
        "paid_orders": 2,
        "gross_usd": "19.98",
        "pending_usd": "8.00",
        "realized_usd": "0.00",
        "mrr_usd": "0.00",
        "cost_usd": "4.78",
        "contribution_usd": "-4.78",
        "account": {
            "handle": "capafy.skills8m4q2z",
            "lifecycle_status": "commercial_ready",
            "capability": "commercial_post",
            "session_established": True,
            "post_write_session_verified": True,
            "account_status": "clean",
        },
        "marketing": {
            "state": "reach_observing",
            "public_post_url": "https://www.instagram.com/reel/DbhCWLhorxy/",
            "campaign_url": None,
        },
        "metrics": {"views": 121, "likes": 0, "comments": 0, "clicks": 1},
        "incident": None,
        "listing_url": "https://capafy.ai/agent/5051239796",
        "dashboard_url": "https://capafy-skills-daily.netlify.app/company/",
        "sources": {
            "money": {"observed_at": "2026-08-13T08:00:00Z", "freshness": "fresh"},
            "inventory": {"observed_at": "2026-08-13T08:00:00Z", "freshness": "fresh"},
            "account": {"observed_at": "2026-08-13T08:00:00Z", "freshness": "fresh"},
            "marketing": {"observed_at": "2026-08-13T08:00:00Z", "freshness": "fresh"},
            "cost": {"observed_at": "2026-08-13T08:00:00Z", "freshness": "fresh"},
        },
    }
    for key, value in changes.items():
        state[key] = value
    return state


def report_envelope(
    state: dict | None = None,
    previous: dict | None = None,
    *,
    report_kind: str = "hourly",
    period_key: str = "2026-08-13T17",
    event_reason: str | None = None,
) -> dict:
    envelope = {
        "schema_version": 1,
        "report_kind": report_kind,
        "period_key": period_key,
        "company_state": state or owner_state(),
        "previous_company_state": previous,
    }
    if event_reason is not None:
        envelope["event_reason"] = event_reason
    return envelope


FORBIDDEN = (
    "reach_observing", "commercial_ready", "repair_started", "unresolved",
    "/Users/", "Traceback", "{{", "}}", "trial", "subscription",
)


GOLDEN_BODY = (
    "Capafy 時間レポート（2026-08-13 17時）\n"
    "売上: 累計5件（有料2件）、総売上$19.98、受取待ち$8.00、入金済み$0.00、MRR $0.00。\n"
    "収支: 計測コスト$4.78、記録済みコスト差引後-$4.78。\n"
    "データ鮮度: 売上、商品在庫、Instagramアカウント、マーケティング、コストは最新。\n"
    "Builder: 公開21件、審査中0件、下書き2件、却下9件。\n"
    "Marketer: @capafy.skills8m4q2z。公開Reelを確認済み。閲覧121、いいね0、コメント0、計測クリック1。\n"
    "修復: 現在対応が必要な問題はありません。\n"
    "次の対応: 次回の定期確認で売上、公開状況、修復状態を再確認する。\n"
    "検証ID: eeeeeeeeeeee\n"
    "Capafy: https://capafy.ai/agent/5051239796\n"
    "Reel: https://www.instagram.com/reel/DbhCWLhorxy/\n"
    "ダッシュボード: https://capafy-skills-daily.netlify.app/company/\n"
)


GOLDEN_CASES = [
        ("healthy", report_envelope()),
        ("unchanged", report_envelope(previous=owner_state())),
        ("stale_metrics", report_envelope(
            state=owner_state(
                sources={
                    "money": {"observed_at": "2026-08-13T08:00:00Z", "freshness": "fresh"},
                    "inventory": {"observed_at": "2026-08-01T08:00:00Z", "freshness": "stale"},
                    "account": {"observed_at": "2026-08-01T08:00:00Z", "freshness": "stale"},
                    "marketing": {"observed_at": "2026-08-01T08:00:00Z", "freshness": "stale"},
                    "cost": {"observed_at": "2026-08-01T08:00:00Z", "freshness": "stale"},
                }
            )
        )),
        ("sale", report_envelope(
            state=owner_state(orders=6, paid_orders=3, gross_usd="29.97"),
            previous=owner_state(orders=5, paid_orders=2, gross_usd="19.98"),
            event_reason="sale",
        )),
        ("published", report_envelope(
            previous=owner_state(marketing={"state": "not_published", "public_post_url": None, "campaign_url": None}),
            event_reason="published",
        )),
        ("repair_closed", report_envelope(
            previous=owner_state(incident={"incident_id": "i", "owner": "marketer", "summary": "old", "phase": "repair_started", "next_retry_at": "2026-08-13T08:50:00Z"}),
            event_reason="repair_closed",
        )),
        ("unresolved", report_envelope(
            state=owner_state(
                account={"handle": "capafy.skills8m4q2z", "lifecycle_status": "unknown_raw", "capability": "unknown_raw", "session_established": False, "post_write_session_verified": False, "account_status": "unknown_raw"},
                incident={"incident_id": "i", "owner": "marketer", "summary": "/Users/private/Traceback raw unresolved", "phase": "unresolved", "next_retry_at": "2026-08-13T08:50:00Z"},
            ),
            event_reason="unresolved",
        )),
]

GOLDEN_EXPECTED = {
    "healthy": GOLDEN_BODY,
    "unchanged": GOLDEN_BODY.replace(
        "次の対応: 次回の定期確認で売上、公開状況、修復状態を再確認する。",
        "次の対応: 前回から変更なし。次回の定期確認を待つ。",
    ),
    "stale_metrics": GOLDEN_BODY.replace(
        "データ鮮度: 売上、商品在庫、Instagramアカウント、マーケティング、コストは最新。",
        "データ鮮度: 売上は最新。商品在庫、Instagramアカウント、マーケティング、コストは古いため要更新。",
    ),
    "sale": GOLDEN_BODY.replace(
        "累計5件（有料2件）、総売上$19.98",
        "累計6件（有料3件）、総売上$29.97",
    ).replace(
        "次の対応: 次回の定期確認で売上、公開状況、修復状態を再確認する。",
        "次の対応: 新しい注文の受取状況を確認する。",
    ),
    "published": GOLDEN_BODY.replace(
        "次の対応: 次回の定期確認で売上、公開状況、修復状態を再確認する。",
        "次の対応: 公開Reelの閲覧・反応・クリック計測を確認する。",
    ),
    "repair_closed": GOLDEN_BODY.replace(
        "修復: 現在対応が必要な問題はありません。",
        "修復: 直前の問題は解決済み。現在対応が必要な問題はありません。",
    ).replace(
        "次の対応: 次回の定期確認で売上、公開状況、修復状態を再確認する。",
        "次の対応: 修復後のMarketer実ブラウザ状態を再確認する。",
    ),
    "unresolved": GOLDEN_BODY.replace(
        "修復: 現在対応が必要な問題はありません。",
        "修復: Marketerの問題は未解決。次回確認は2026-08-13 17:50 JST。",
    ).replace(
        "次の対応: 次回の定期確認で売上、公開状況、修復状態を再確認する。",
        "次の対応: MarketerがInstagramの実ブラウザ状態を再取得する。",
    ),
}


@pytest.mark.parametrize("name,case", GOLDEN_CASES)
def test_japanese_owner_report_golden_cases(name: str, case: dict) -> None:
    result = owner_report("render", case)
    assert result.returncode == 0, result.stderr
    assert result.stdout == GOLDEN_EXPECTED[name]
    assert not any(token in result.stdout for token in FORBIDDEN)


@pytest.mark.parametrize(
    ("kind", "period", "expected"),
    [
        ("hourly", "2026-08-13T17", "hourly:2026-08-13T17"),
        ("morning", "2026-08-13", "morning:2026-08-13"),
        ("daily_close", "2026-08-13", "daily_close:2026-08-13"),
    ],
)
def test_owner_report_period_delivery_key(kind: str, period: str, expected: str) -> None:
    result = owner_report("delivery-key", report_envelope(report_kind=kind, period_key=period))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected


def test_owner_report_event_delivery_key_uses_reason_and_immutable_event() -> None:
    result = owner_report(
        "delivery-key",
        report_envelope(
            report_kind="event",
            period_key="ignored",
            event_reason="sale",
            state=owner_state(last_event_id="capafy:order.received:2026-08-13"),
        ),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "event:sale:capafy:order.received:2026-08-13"


def test_owner_report_event_delivery_key_derives_supported_reason() -> None:
    current = owner_state()
    current["last_event_id"] = "capafy:marketing.published:2026-08-13"
    old = owner_state(marketing={"state": "not_published", "public_post_url": None, "campaign_url": None})
    envelope = report_envelope(report_kind="event", period_key="event-period", state=current, previous=old)
    result = owner_report("delivery-key", envelope)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "event:published:capafy:marketing.published:2026-08-13"


def test_owner_report_unset_kind_defaults_to_morning() -> None:
    envelope = report_envelope()
    envelope.pop("report_kind")
    envelope.pop("period_key")
    result = owner_report("delivery-key", envelope)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("morning:")


def test_owner_report_rejects_invalid_event_reason() -> None:
    result = owner_report(
        "delivery-key",
        report_envelope(report_kind="event", event_reason="other"),
    )
    assert result.returncode != 0
    assert "event_reason" in result.stderr


@pytest.mark.parametrize("kind", ["", "weekly", "EVENT", "hourly:bad"])
def test_owner_report_rejects_invalid_report_kind(kind: str) -> None:
    result = owner_report("delivery-key", report_envelope(report_kind=kind))
    assert result.returncode != 0
    assert "report_kind" in result.stderr


def test_owner_report_delivery_state_migrates_legacy_and_retains_256(tmp_path: Path) -> None:
    state = tmp_path / "delivery.json"
    state.write_text(json.dumps({"schema_version": 1, "projection_id": "sha256:" + "a" * 64}))
    envelope = report_envelope()
    key = "hourly:2026-08-13T17"
    result = owner_report("delivered", envelope, "--state", str(state), "--key", key)
    assert result.returncode == 1
    for index in range(260):
        result = subprocess.run(
            [sys.executable, str(OWNER_SCRIPT), "record-delivery", "--state", str(state),
             "--key", f"hourly:{index}", "--projection-id", "sha256:" + "b" * 64,
             "--message-id", str(index + 1)],
            text=True, capture_output=True, check=False,
        )
        assert result.returncode == 0, result.stderr
    payload = json.loads(state.read_text())
    assert payload["schema_version"] == 2
    assert len(payload["deliveries"]) == 256
    assert oct(stat.S_IMODE(state.stat().st_mode)) == "0o600"
    assert "hourly:0" not in {row["delivery_key"] for row in payload["deliveries"]}
    assert "hourly:259" in {row["delivery_key"] for row in payload["deliveries"]}


def test_owner_report_corrupt_delivery_state_fails_closed(tmp_path: Path) -> None:
    state = tmp_path / "delivery.json"
    state.write_text("not-json")
    result = owner_report("delivered", report_envelope(), "--state", str(state), "--key", "hourly:2026-08-13T17")
    assert result.returncode == 2
    result = subprocess.run(
        [sys.executable, str(OWNER_SCRIPT), "record-delivery", "--state", str(state),
         "--key", "hourly:2026-08-13T17", "--projection-id", "sha256:" + "b" * 64, "--message-id", "1"],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 2


def test_owner_report_rejects_non_numeric_message_id(tmp_path: Path) -> None:
    state = tmp_path / "delivery.json"
    result = subprocess.run(
        [sys.executable, str(OWNER_SCRIPT), "record-delivery", "--state", str(state),
         "--key", "hourly:2026-08-13T17", "--projection-id", "sha256:" + "b" * 64, "--message-id", "abc"],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode != 0
    assert not state.exists()


def _goal_monitor_fixture(tmp_path: Path) -> tuple[dict[str, str], Path, Path, Path]:
    home = tmp_path / "home"
    state = home / ".openclaw/state"
    ledger = state / "capafy-revenue-events.jsonl"
    evidence = state / "capafy-revenue-evidence"
    scratch = tmp_path / "scratch"
    for directory in (
        state,
        home / ".openclaw/logs",
        home / "anicca/skills/self/capafy-loop/state",
        home / ".openclaw/skills/capafy-autopublish/vendor/capafy-publisher",
        scratch,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    events = fixture_events()
    ledger.write_text("\n".join(json.dumps(event) for event in events) + "\n")
    (home / "anicca/skills/self/capafy-loop/state/capafy-earn-ledger.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"ts": 1782172800, "source": "capafy-sales", "date": "2026-06-23", "orders": 1, "gross_usd": 9.99},
                {"ts": 1784330227, "source": "capafy-payout", "date": "2026-07-18", "balance_payout_usd": 8.0, "total_payout_usd": 0.0},
            )
        )
        + "\n"
    )
    (home / ".openclaw/logs/capafy-loop-daily.log").write_text(
        json.dumps({"provider": "openrouter", "total_usage_usd": 4.776}) + "\n"
    )
    (state / "capafy-ig-lifecycle.json").write_text(json.dumps({
        "handle": "capafy.skills8m4q2z", "status": "commercial_ready", "capability": "commercial_post",
        "session_established": True, "post_write_session_verified": True, "replacement_requested": False,
    }))
    (state / "capafy-marketing-terminal.json").write_text(json.dumps({"outcome": {
        "kind": "marketing_published", "reel_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
        "campaign_url": "https://capafy-skills-daily.netlify.app/go/4866150011?utm_source=instagram",
    }}))
    (home / ".openclaw/skills/capafy-autopublish/vendor/capafy-publisher/packager.py").write_text(
        'import json\nprint(json.dumps({"agents":{"list":[{"agentStatus":"online"}]}}))\n'
    )
    account_helper = tmp_path / "account_state.sh"
    account_helper.write_text(
        "capafy_ig_accounts_file() { printf '%s\\n' \"$HOME/accounts.jsonl\"; }\n"
        "resolve_capafy_ig_handle() { printf '%s\\n' capafy.skills8m4q2z; }\n"
        "resolve_capafy_ig_port() { printf '%s\\n' 65063; }\n"
    )
    event_sync = tmp_path / "sync.py"
    event_sync.write_text("raise SystemExit(0)\n")
    sent = tmp_path / "telegram.txt"
    sender = tmp_path / "send.sh"
    sender.write_text(
        'if [ "${FAKE_SEND_FAIL:-0}" = 1 ]; then exit 1; fi\n'
        'printf "%s\\n" "$1" >> "$FAKE_SENT"\n'
        'printf "TELEGRAM_SENT=true MSGID=%s\\n" "${FAKE_MSGID:-777}"\n'
    )
    delivery = state / "capafy-goal-monitor-delivery.json"
    env = os.environ | {
        "HOME": str(home),
        "CAPAFY_ACCOUNT_STATE_HELPER": str(account_helper),
        "CAPAFY_IG_LIFECYCLE_STATE": str(state / "capafy-ig-lifecycle.json"),
        "CAPAFY_EVENT_LEDGER": str(ledger),
        "CAPAFY_EVENT_EVIDENCE_DIR": str(evidence),
        "CAPAFY_EVENT_SYNC": str(event_sync),
        "CAPAFY_EVENT_PROJECTION": str(SCRIPT.parent / "capafy_event_projection.py"),
        "CAPAFY_COMPANY_DASHBOARD_BUILDER": str(SCRIPT.parent / "build_company_dashboard.py"),
        "CAPAFY_COMPANY_DASHBOARD_DIR": str(tmp_path / "site/company"),
        "CAPAFY_GOAL_MONITOR_TMP_DIR": str(scratch),
        "CAPAFY_TELEGRAM_SENDER": str(sender),
        "CAPAFY_GOAL_MONITOR_DELIVERY_STATE": str(delivery),
        "FAKE_SENT": str(sent),
    }
    return env, SCRIPT.parent.parent / "capafy-goal-monitor.sh", sent, delivery


def _run_monitor(env: dict[str, str], script: Path, *, kind: str, period: str, reason: str | None = None) -> subprocess.CompletedProcess[str]:
    run_env = dict(env, CAPAFY_REPORT_KIND=kind, CAPAFY_REPORT_PERIOD_KEY=period)
    if reason is not None:
        run_env["CAPAFY_EVENT_REASON"] = reason
    else:
        run_env.pop("CAPAFY_EVENT_REASON", None)
    return subprocess.run(["bash", str(script)], env=run_env, text=True, capture_output=True, check=False)


def test_goal_monitor_failed_send_does_not_record_delivery(tmp_path: Path) -> None:
    env, script, _, delivery = _goal_monitor_fixture(tmp_path)
    env["FAKE_SEND_FAIL"] = "1"
    result = _run_monitor(env, script, kind="hourly", period="2026-08-13T17")
    assert result.returncode == 1
    assert not delivery.exists()


def test_goal_monitor_period_retry_and_event_do_not_duplicate_or_evict(tmp_path: Path) -> None:
    env, script, sent, delivery = _goal_monitor_fixture(tmp_path)
    first = _run_monitor(env, script, kind="hourly", period="2026-08-13T17")
    assert first.returncode == 0, first.stderr
    first_sent, first_state = sent.read_bytes(), delivery.read_bytes()
    retry = _run_monitor(env, script, kind="hourly", period="2026-08-13T17")
    assert retry.returncode == 0, retry.stderr
    assert sent.read_bytes() == first_sent
    assert delivery.read_bytes() == first_state
    event = _run_monitor(env, script, kind="event", period="event-period", reason="sale")
    assert event.returncode == 0, event.stderr
    event_state = json.loads(delivery.read_text())
    assert {row["delivery_key"] for row in event_state["deliveries"]} >= {
        "hourly:2026-08-13T17",
        "event:sale:capafy:cost.measured:openrouter:1785539400",
    }
    retry_after_event = _run_monitor(env, script, kind="hourly", period="2026-08-13T17")
    assert retry_after_event.returncode == 0, retry_after_event.stderr
    assert sent.read_text().count("レポート（") == 2
    next_period = _run_monitor(env, script, kind="hourly", period="2026-08-13T18")
    assert next_period.returncode == 0, next_period.stderr
    assert sent.read_text().count("レポート（") == 3
    keys = {row["delivery_key"] for row in json.loads(delivery.read_text())["deliveries"]}
    assert {"hourly:2026-08-13T17", "hourly:2026-08-13T18"} <= keys


def test_company_state_render_shows_paid_count_or_unknown() -> None:
    known = render(company_state_payload(paid_orders=2))
    unknown = render(company_state_payload(paid_orders=None))

    assert known.returncode == 0, known.stderr
    assert "Sales: 5 lifetime orders / 2 paid / $19.98 gross." in known.stdout
    assert unknown.returncode == 0, unknown.stderr
    assert "Sales: 5 lifetime orders / paid count unavailable / $19.98 gross." in unknown.stdout


@pytest.mark.parametrize("paid_orders", [True, -1, 1.0, "1", 6])
def test_company_state_rejects_invalid_paid_count(paid_orders: object) -> None:
    result = render(company_state_payload(paid_orders=paid_orders))

    assert result.returncode != 0
    assert "paid_orders" in result.stderr


@pytest.mark.parametrize("orders", [True, -1, 1.0, "5"])
def test_company_state_rejects_invalid_order_count(orders: object) -> None:
    result = render(company_state_payload(paid_orders=0, orders=orders))

    assert result.returncode != 0
    assert "orders" in result.stderr


def test_august_first_company_state_is_natural_and_truthful() -> None:
    payload = {
        "schema_version": 1,
        "kind": "company_state",
        "as_of": "2026-08-01T20:32:53Z",
        "date": "2026-08-01",
        "last_event_id": "capafy:incident.repair_started:test",
        "projection_id": "sha256:" + "a" * 64,
        "inventory": {"online": 27, "under_review": 1, "draft": 2, "rejected": 1},
        "orders": 1,
        "paid_orders": 1,
        "gross_usd": 9.99,
        "pending_usd": 8.0,
        "realized_usd": 0.0,
        "mrr_usd": 0.0,
        "cost_usd": 4.777,
        "contribution_usd": -4.777,
        "account": {
            "handle": "capafy.skills10491",
            "lifecycle_status": "publish_probe_ready",
            "capability": "publish_probe",
            "session_established": True,
            "post_write_session_verified": False,
            "account_status": "clean",
        },
        "marketing": {"scheduler_loaded": True, "public_post_url": None},
        "metrics": {"views": 121, "clicks": 0},
        "incident": {
            "summary": "The Instagram agent runner timed out at 180 seconds",
            "phase": "repair_started",
            "next_retry_at": "2026-08-01T16:00:00+09:00",
        },
        "listing_url": "https://capafy.ai/developer/createAgent?source=temp-link&token=2082974745565622272&page=review",
        "dashboard_url": "https://capafy-skills-daily.netlify.app",
    }

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "render"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = result.stdout
    assert "27 online, 1 under review, 2 drafts" in report
    assert "1 lifetime order / 1 paid / $9.99 gross" in report
    assert "Pending seller balance: $8.00" in report
    assert "Realized bank payout: $0.00" in report
    assert "MRR: $0.00" in report
    assert "Model/tool cost: $4.78" in report
    assert "Contribution after recorded cost: -$4.78" in report
    assert "publish_probe_ready" in report
    assert "posting session is established" in report
    assert "Account status: clean" in report
    assert "calendar" not in report.lower()
    assert "warmup" not in report.lower()
    assert "Marketing is scheduled" in report
    assert "no public post is verified" in report
    assert "repair_started" in report
    assert payload["listing_url"] in report
    assert payload["dashboard_url"] in report
    assert "Projection: aaaaaaaaaaaa" in report
    assert "Views: 121" in report
    assert "Attributed clicks: 0" in report
    assert "goal(a)" not in report
    assert "already_live" not in report
    assert "goal(d) health" not in report


def test_singular_inventory_nouns_are_grammatical() -> None:
    payload = {
        "schema_version": 1,
        "kind": "company_state",
        "as_of": "2026-08-01T20:32:53Z",
        "date": "2026-08-01",
        "last_event_id": "capafy:order.received:test",
        "projection_id": "sha256:" + "b" * 64,
        "inventory": {"online": 1, "under_review": 1, "draft": 1, "rejected": 1},
        "orders": 0,
        "paid_orders": 0,
        "gross_usd": 0,
        "pending_usd": 0,
        "realized_usd": 0,
        "mrr_usd": 0,
        "cost_usd": 0,
        "contribution_usd": 0,
        "account": {"handle": "no-active-account", "lifecycle_status": "replacement_requested", "capability": "none", "session_established": False, "post_write_session_verified": False, "account_status": "replacement requested"},
        "marketing": {"scheduler_loaded": True, "public_post_url": None},
        "metrics": {},
        "incident": None,
        "listing_url": None,
        "dashboard_url": "https://capafy-skills-daily.netlify.app",
    }
    result = subprocess.run([sys.executable, str(SCRIPT), "render"], input=json.dumps(payload), text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    assert "1 online, 1 under review, 1 draft, 1 rejected" in result.stdout
    assert "1 drafts" not in result.stdout


def test_projection_report_contains_identical_business_values_and_public_links() -> None:
    payload = {
        "schema_version": 1,
        "kind": "company_state",
        "as_of": "2026-08-02T12:00:00Z",
        "date": "2026-08-02",
        "last_event_id": "capafy:incident.unresolved:incident-1",
        "projection_id": "sha256:" + "c" * 64,
        "inventory": {"online": 1, "under_review": 0, "draft": 0, "rejected": 0},
        "orders": 1,
        "paid_orders": 1,
        "gross_usd": "9.99",
        "pending_usd": "8.00",
        "realized_usd": "0.00",
        "mrr_usd": "0.00",
        "cost_usd": "4.78",
        "contribution_usd": "-4.78",
        "account": {
            "handle": "capafy.skills8m4q2z",
            "lifecycle_status": "reach_observing",
            "capability": "publish_probe",
            "session_established": True,
            "post_write_session_verified": True,
            "account_status": "clean",
        },
        "marketing": {
            "state": "reach_observing",
            "public_post_url": "https://www.instagram.com/reel/DbgsvEbo5kd/",
            "campaign_url": "https://capafy-skills-daily.netlify.app/go/4866150011?utm_source=instagram",
        },
        "metrics": {"views": 121, "likes": 2, "comments": 1, "clicks": 3},
        "incident": {
            "incident_id": "incident-1",
            "owner": "marketer",
            "summary": "Metric readback failed once.",
            "phase": "unresolved",
            "next_retry_at": "2026-08-02T12:05:00Z",
        },
        "listing_url": "https://capafy.ai/agent/4866150011",
        "dashboard_url": "https://capafy-skills-daily.netlify.app/company/",
    }

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "render"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    for value in (
        "$9.99",
        "$8.00",
        "$0.00",
        "$4.78",
        "-$4.78",
        "capafy.skills8m4q2z",
        "cccccccccccc",
        payload["marketing"]["public_post_url"],
        payload["marketing"]["campaign_url"],
        payload["listing_url"],
        payload["dashboard_url"],
        "Metric readback failed once.",
    ):
        assert value in result.stdout
