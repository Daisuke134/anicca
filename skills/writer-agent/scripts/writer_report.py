#!/usr/bin/env python3
"""One receipt-backed snapshot for Writer Web UI and Telegram reports."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from money_ledger import MoneyLedger  # noqa: E402


JST = ZoneInfo("Asia/Tokyo")


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("report time must include timezone")
    return value.isoformat()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _atomic(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return parsed


def _title(state_dir: Path, run_id: str, lang: str, fallback: str) -> str:
    path = state_dir / "runs" / run_id / f"article-{lang}.md"
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return fallback
    if source.startswith("---"):
        frontmatter = source.split("---", 2)[1]
        match = re.search(r"(?m)^title:\s*['\"]?(.+?)['\"]?\s*$", frontmatter)
        if match:
            return match.group(1).strip()
    match = re.search(r"(?m)^#\s+(.+?)\s*$", source)
    return match.group(1).strip() if match else fallback


def _latest_account_metric(connection: sqlite3.Connection, metric: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT value,unit,status,reason,observed_at,source_url "
        "FROM metric_observations WHERE scope='account' AND metric=? "
        "ORDER BY datetime(observed_at) DESC LIMIT 1",
        (metric,),
    ).fetchone()
    if row is None:
        return {"status": "unknown", "value": None, "unit": None,
                "reason": f"{metric} has no external observation"}
    return dict(row)


def _pending_payout(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = list(connection.execute(
        "SELECT gross_amount,currency FROM payouts WHERE status='pending' AND test=0"
    ))
    if not rows:
        return {
            "status": "unknown", "by_currency": {},
            "reason": "pending payout has no verified platform observation",
        }
    totals: dict[str, float] = {}
    for row in rows:
        totals[str(row["currency"])] = totals.get(str(row["currency"]), 0.0) + float(
            row["gross_amount"]
        )
    return {"status": "verified", "by_currency": totals}


def _payout_receipts(connection: sqlite3.Connection) -> list[dict[str, str]]:
    return [
        {
            "id": str(row["external_receipt_id"]),
            "status": str(row["status"]),
            "url": str(row["source_url"]),
            "occurred_at": str(row["occurred_at"]),
        }
        for row in connection.execute(
            "SELECT external_receipt_id,status,source_url,occurred_at FROM payouts "
            "WHERE test=0 ORDER BY datetime(occurred_at) DESC LIMIT 20"
        )
    ]


def _article_money(connection: sqlite3.Connection, artifact_id: str) -> dict[str, Any]:
    gross: dict[str, float] = {}
    refunds: dict[str, float] = {}
    fees: dict[str, float] = {}
    receipts: list[dict[str, str]] = []
    for row in connection.execute(
        "SELECT kind,amount,currency,external_receipt_id,source_url FROM money_events "
        "WHERE artifact_id=? AND test=0 "
        "AND ((status='verified_received' AND kind!='refund') OR "
        "(status='refunded' AND kind='refund'))",
        (artifact_id,),
    ):
        target = refunds if row["kind"] == "refund" else gross
        currency = str(row["currency"])
        target[currency] = target.get(currency, 0.0) + float(row["amount"])
        receipts.append({
            "kind": str(row["kind"]), "id": str(row["external_receipt_id"]),
            "url": str(row["source_url"]),
        })
    for row in connection.execute(
        "SELECT f.amount,f.currency,f.external_receipt_id,f.source_url "
        "FROM money_fees f JOIN money_events e "
        "ON e.event_id=f.event_id WHERE e.artifact_id=? AND e.test=0 AND f.status='verified'",
        (artifact_id,),
    ):
        currency = str(row["currency"])
        fees[currency] = fees.get(currency, 0.0) + float(row["amount"])
        receipts.append({
            "kind": "fee", "id": str(row["external_receipt_id"]),
            "url": str(row["source_url"]),
        })
    for row in connection.execute(
        "SELECT external_contract_id,source_url FROM subscription_contracts "
        "WHERE acquisition_artifact_id=? AND test=0",
        (artifact_id,),
    ):
        receipts.append({
            "kind": "subscription", "id": str(row["external_contract_id"]),
            "url": str(row["source_url"]),
        })
    currencies = set(gross) | set(refunds) | set(fees)
    net = {
        currency: gross.get(currency, 0.0) - refunds.get(currency, 0.0) - fees.get(currency, 0.0)
        for currency in sorted(currencies)
    }
    unique = {
        (item["kind"], item["id"], item["url"]): item for item in receipts
    }
    return {
        "gross": gross, "refunds": refunds, "fees": fees, "net": net,
        "receipts": [unique[key] for key in sorted(unique)],
    }


def _latest_metrics(connection: sqlite3.Connection, artifact_id: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for row in connection.execute(
        "SELECT metric,value,unit,status,reason,observed_at FROM metric_observations "
        "WHERE artifact_id=? ORDER BY datetime(observed_at) DESC",
        (artifact_id,),
    ):
        result.setdefault(str(row["metric"]), {
            "value": row["value"], "unit": row["unit"], "status": row["status"],
            "reason": row["reason"], "observed_at": row["observed_at"],
        })
    return result


def _offer(article: dict[str, Any]) -> str | None:
    price = article.get("metrics", {}).get("price", {})
    paywall = article.get("metrics", {}).get("paywall_active", {})
    if (
        price.get("status") == "verified"
        and price.get("unit") == "JPY"
        and isinstance(price.get("value"), (int, float))
        and paywall.get("status") == "verified"
        and paywall.get("value") == 1
    ):
        return f"¥{price['value']:,.0f}買い切り・有料状態確認済み"
    paid_post = article.get("metrics", {}).get("paid_post_active", {})
    if paid_post.get("status") == "verified" and paid_post.get("value") == 1:
        return "有料購読者限定・paywall確認済み"
    return None


def _opportunities(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"counts": {}, "active": [], "status": "unavailable"}
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            rows = list(connection.execute(
                "SELECT publisher,state,next_action,updated_at FROM opportunities "
                "ORDER BY datetime(updated_at) DESC"
            ))
    except sqlite3.Error:
        return {"counts": {}, "active": [], "status": "unavailable"}
    counts: dict[str, int] = {}
    active = []
    for row in rows:
        state = str(row["state"])
        counts[state] = counts.get(state, 0) + 1
        if state in {"PITCH_READY", "SUBMITTED", "ACCEPTED", "DRAFTING", "ARTICLE_SUBMITTED", "PUBLISHED"}:
            active.append(dict(row))
    return {"counts": dict(sorted(counts.items())), "active": active[:10], "status": "verified"}


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _latest_entity(
    connection: sqlite3.Connection, table: str, opportunity_id: str,
    parent: tuple[str, str] | None = None,
) -> dict[str, Any] | None:
    if not _table_exists(connection, table):
        return None
    columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
    entity_ids = {
        "opportunity_applications": "application_id",
        "opportunity_contracts": "contract_id",
        "opportunity_assignments": "assignment_id",
        "opportunity_deliveries": "delivery_id",
        "opportunity_publications": "publication_id",
    }
    entity_id = entity_ids.get(table, "rowid")
    revision_order = (
        "revision_number DESC, "
        if table == "opportunity_deliveries" and "revision_number" in columns else ""
    )
    order = (
        f" ORDER BY datetime(updated_at) DESC, {revision_order}{entity_id} DESC"
        if "updated_at" in columns else f" ORDER BY {revision_order}{entity_id} DESC"
    )
    filters = "opportunity_id=?"
    values: list[str] = [opportunity_id]
    if parent is not None:
        parent_column, parent_id = parent
        if parent_column not in columns:
            return None
        filters += f" AND {parent_column}=?"
        values.append(parent_id)
    row = connection.execute(
        f"SELECT * FROM {table} WHERE {filters}{order} LIMIT 1",
        values,
    ).fetchone()
    return dict(row) if row is not None else None


def _commercial(state_dir: Path, money: sqlite3.Connection) -> dict[str, Any]:
    path = state_dir / "opportunities.sqlite3"
    if not path.is_file():
        return {"active": [], "status": "unavailable"}
    payments: dict[str, list[dict[str, Any]]] = {}
    if _table_exists(money, "commercial_payment_bindings"):
        for row in money.execute(
            "SELECT * FROM commercial_payment_bindings "
            "ORDER BY datetime(received_at),payment_id"
        ):
            payments.setdefault(str(row["opportunity_id"]), []).append(dict(row))
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as opportunity:
            opportunity.row_factory = sqlite3.Row
            columns = {
                str(row[1]) for row in opportunity.execute("PRAGMA table_info(opportunities)")
            }
            if "opportunity_id" not in columns:
                return {"active": [], "status": "unavailable"}
            commercial_states = (
                "PITCH_READY", "SUBMITTED", "ACCEPTED", "DRAFTING",
                "ARTICLE_SUBMITTED", "PUBLISHED", "RECEIVED",
            )
            roots = list(opportunity.execute(
                "SELECT opportunity_id,publisher,state,next_action FROM opportunities "
                "WHERE state IN (?,?,?,?,?,?,?) ORDER BY datetime(updated_at) DESC, "
                "opportunity_id DESC",
                commercial_states,
            ))
            active: list[dict[str, Any]] = []
            for root in roots:
                opportunity_id = str(root["opportunity_id"])
                application = _latest_entity(
                    opportunity, "opportunity_applications", opportunity_id
                )
                contract = _latest_entity(
                    opportunity, "opportunity_contracts", opportunity_id,
                    ("application_id", str(application["application_id"]))
                ) if application else None
                assignment = _latest_entity(
                    opportunity, "opportunity_assignments", opportunity_id,
                    ("contract_id", str(contract["contract_id"])),
                ) if contract else None
                delivery = _latest_entity(
                    opportunity, "opportunity_deliveries", opportunity_id,
                    ("assignment_id", str(assignment["assignment_id"])),
                ) if assignment else None
                publication = _latest_entity(
                    opportunity, "opportunity_publications", opportunity_id,
                    ("delivery_id", str(delivery["delivery_id"])),
                ) if delivery else None
                evidence: dict[str, str] = {}
                for label, entity, field in (
                    ("submission", application, "submission_evidence_id"),
                    ("terms", contract, "terms_evidence_id"),
                    ("assignment", assignment, "assignment_evidence_id"),
                    ("delivery", delivery, "delivery_evidence_id"),
                    ("publication", publication, "publication_evidence_id"),
                ):
                    if entity and entity.get(field):
                        evidence[label] = str(entity[field])
                gross: dict[str, float] = {}
                fees: dict[str, float] = {}
                net: dict[str, float] = {}
                mrr: dict[str, float] = {}
                payment_evidence_ids: list[str] = []
                recurring_contracts: set[str] = set()
                for payment in payments.get(opportunity_id, []):
                    currency = str(payment["currency"])
                    gross[currency] = gross.get(currency, 0.0) + float(payment["gross_amount"])
                    fees[currency] = fees.get(currency, 0.0) + float(payment["fee_amount"])
                    net[currency] = net.get(currency, 0.0) + float(payment["net_amount"])
                    payment_evidence_ids.append(str(payment["payment_evidence_id"]))
                    evidence.setdefault("trigger", str(payment["trigger_evidence_id"]))
                    if payment["revenue_type"] == "RECURRING_RETAINER":
                        recurring_id = str(payment["recurring_contract_id"])
                        if recurring_id in recurring_contracts:
                            continue
                        recurring_contracts.add(recurring_id)
                        contract_row = money.execute(
                            "SELECT amount,currency,interval_name,status FROM subscription_contracts "
                            "WHERE external_contract_id=? AND test=0",
                            (payment["recurring_contract_id"],),
                        ).fetchone()
                        if contract_row is not None and contract_row["status"] == "active":
                            monthly = float(contract_row["amount"])
                            if contract_row["interval_name"] == "year":
                                monthly /= 12
                            mrr[str(contract_row["currency"])] = (
                                mrr.get(str(contract_row["currency"]), 0.0) + monthly
                            )
                unknown_terms: list[str] = []
                if contract is None:
                    unknown_terms = ["contract"]
                elif contract.get("blocking_terms_json"):
                    try:
                        parsed = json.loads(str(contract["blocking_terms_json"]))
                    except json.JSONDecodeError:
                        parsed = []
                    if isinstance(parsed, list):
                        unknown_terms = sorted(str(value) for value in parsed)
                active.append({
                    "opportunity_id": opportunity_id,
                    "publisher": str(root["publisher"]),
                    "states": {
                        "opportunity": str(root["state"]),
                        "application": application.get("status") if application else None,
                        "contract": contract.get("status") if contract else None,
                        "assignment": assignment.get("status") if assignment else None,
                        "delivery": delivery.get("status") if delivery else None,
                        "publication": publication.get("status") if publication else None,
                    },
                    "unknown_terms": unknown_terms,
                    "evidence_ids": evidence,
                    "money": {
                        "status": "verified" if payments.get(opportunity_id) else "unknown",
                        "gross": gross, "fees": fees, "net": net, "mrr": mrr,
                        "mrr_status": "verified" if payments.get(opportunity_id) else "unknown",
                        "payment_evidence_ids": sorted(payment_evidence_ids),
                    },
                    "next_action": str(root["next_action"]),
                })
    except sqlite3.Error:
        return {"active": [], "status": "unavailable"}
    return {"active": active, "status": "verified"}


def _json_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _descriptive_quality_diff(metrics_root: Path) -> dict[str, Any]:
    snapshots = []
    for path in metrics_root.glob("*.json"):
        value = _json_object(path)
        if value is None or not isinstance(value.get("observed_at"), str):
            continue
        try:
            observed = _parse_time(value["observed_at"])
        except ValueError:
            continue
        snapshots.append((observed, value))
    snapshots.sort(key=lambda item: item[0])
    if len(snapshots) < 2:
        return {
            "status": "insufficient",
            "causal": False,
            "reason": "two comparable run snapshots are not available",
            "deltas": {},
        }
    before = snapshots[-2][1]
    after = snapshots[-1][1]
    deltas: dict[str, dict[str, float]] = {}
    for language in ("ja", "en"):
        old = before.get("quality", {}).get(language, {})
        new = after.get("quality", {}).get(language, {})
        if not isinstance(old, dict) or not isinstance(new, dict):
            continue
        lane = {}
        for metric in sorted(set(old) & set(new)):
            if (
                isinstance(old[metric], (int, float))
                and not isinstance(old[metric], bool)
                and isinstance(new[metric], (int, float))
                and not isinstance(new[metric], bool)
            ):
                lane[metric] = float(new[metric]) - float(old[metric])
        if lane:
            deltas[language] = lane
    return {
        "status": "descriptive",
        "causal": False,
        "reason": "consecutive runs may differ in topic and audience",
        "from_run_id": before.get("run_id"),
        "to_run_id": after.get("run_id"),
        "deltas": deltas,
    }


def _latest_learning_experiment(experiments_root: Path) -> dict[str, Any] | None:
    candidates = []
    for directory in experiments_root.iterdir() if experiments_root.is_dir() else ():
        if not directory.is_dir():
            continue
        manifest = _json_object(directory / "manifest.json")
        if manifest is None or manifest.get("schema_version") != 2:
            continue
        try:
            created = _parse_time(str(manifest["created_at"]))
        except (KeyError, ValueError):
            continue
        candidates.append((created, directory, manifest))
    if not candidates:
        return None
    _created, directory, manifest = max(candidates, key=lambda item: item[0])
    decision = _json_object(directory / "decision.json") or {}
    promotion = _json_object(directory / "promotion.json")
    consumptions = [
        value for value in (
            _json_object(path)
            for path in sorted((directory / "consumptions").glob("*.json"))
        )
        if value is not None
    ]
    return {
        "experiment_id": manifest.get("experiment_id"),
        "created_at": manifest.get("created_at"),
        "changed_field": manifest.get("changed_field"),
        "text_diff": manifest.get("text_diff", {}),
        "baseline_strategy_sha256": manifest.get("baseline_strategy_sha256"),
        "candidate_strategy_sha256": manifest.get("candidate_strategy_sha256"),
        "decision": decision.get("decision", "INCONCLUSIVE"),
        "reason": decision.get("reason", "comparison has no decision receipt"),
        "canary_deltas": decision.get("canary_deltas", {}),
        "evidence_refs": decision.get("evidence_refs", []),
        "rollback_strategy_sha256": (
            promotion.get("rollback_strategy_sha256") if promotion else None
        ),
        "consumed_by_run_id": consumptions[-1].get("run_id") if consumptions else None,
    }


def _learning(state_dir: Path) -> dict[str, Any]:
    root = state_dir / "learning"
    return {
        "day_diff": _descriptive_quality_diff(root / "metrics"),
        "latest_experiment": _latest_learning_experiment(root / "experiments"),
    }


def _incident_cause(reason: str) -> str:
    lowered = reason.lower()
    if "expected_receipt_missing" in lowered:
        return "missing_receipt"
    if "invalid_receipt" in lowered:
        return "state_corruption"
    if "stale" in lowered:
        return "state_contract"
    if "s3" in lowered or "403" in lowered:
        return "dependency_or_credential"
    if any(token in lowered for token in ("editor", "anchor", "selector", "dom")):
        return "dom_selector"
    if "timeout" in lowered:
        return "process_timeout"
    return "unclassified"


def _incident_timeline(state_dir: Path, money: dict[str, Any]) -> dict[str, Any] | None:
    candidates: list[tuple[str, Path, dict[str, Any]]] = []
    for path in (state_dir / "runs").glob("*/observability/evidence-index.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict) or value.get("schema") != "writer.observability.evidence-index":
            continue
        candidates.append((str(value.get("observed_at") or ""), path, value))
    if not candidates:
        return None
    _observed_at, _path, index = max(candidates, key=lambda item: (item[0], str(item[1])))
    run_id = str(index.get("run_id") or "")
    public_rows = [
        row for row in _read_jsonl(state_dir / "articles.jsonl")
        if str(row.get("run_id")) == run_id
        and row.get("published") is True
        and isinstance(row.get("live_url"), str)
        and row["live_url"].strip()
    ]
    incidents = []
    for item in index.get("incidents", []):
        if not isinstance(item, dict):
            continue
        reason = str(item.get("reason") or "unknown")
        incidents.append({
            "incident_id": str(item.get("incident_id") or ""),
            "phase": str(item.get("phase") or "unknown"),
            "reason": reason,
            "cause_class": _incident_cause(reason),
            "owner": "writer-self-heal",
            "next_automatic_action": "classify_and_enqueue_repair",
            "next_automatic_action_status": "not_implemented",
            "evidence_status": str(item.get("evidence_status") or "unknown"),
            "source_receipt": item.get("source_receipt"),
        })
    return {
        "run_id": run_id,
        "observed_at": index.get("observed_at"),
        "incident_count": len(incidents),
        "incidents": incidents,
        "publication_truth": {
            "public_count": len(public_rows),
            "live_urls": [str(row["live_url"]) for row in public_rows],
        },
        "verified_money_truth": {
            "gross": money["today"]["verified_gross_by_currency"],
            "mrr": money["mrr"],
            "mrr_status": "verified" if money["mrr"] else "unknown",
        },
    }


def build_snapshot(*, state_dir: Path, now: datetime) -> dict[str, Any]:
    state_dir = Path(state_dir)
    if now.tzinfo is None:
        raise ValueError("now must include timezone")
    local_now = now.astimezone(JST)
    today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    month = today.replace(day=1)
    week = today - timedelta(days=today.weekday())
    previous_week = week - timedelta(days=7)
    ledger = MoneyLedger(state_dir / "money.sqlite3")
    summaries = {
        "today": ledger.summary(start=_iso(today), end=_iso(local_now + timedelta(microseconds=1))),
        "month": ledger.summary(start=_iso(month), end=_iso(local_now + timedelta(microseconds=1))),
        "week": ledger.summary(start=_iso(week), end=_iso(local_now + timedelta(microseconds=1))),
        "previous_week": ledger.summary(start=_iso(previous_week), end=_iso(week)),
    }
    with ledger._connect() as connection:
        artifacts = []
        article_context = {
            f"{row.get('run_id')}__{row.get('platform')}__{row.get('lang') or row.get('language')}": row
            for row in _read_jsonl(state_dir / "articles.jsonl")
            if row.get("published") is True and row.get("live_url")
        }
        for row in connection.execute(
            "SELECT * FROM money_artifacts ORDER BY datetime(published_at) DESC"
        ):
            item = dict(row)
            context = article_context.get(str(row["artifact_id"]), {})
            contract = ledger.revenue_surfaces["destinations"].get(str(row["platform"]), {})
            item.update({
                "topic_id": context.get("topic_id") or context.get("topic"),
                "title": _title(
                    state_dir, str(row["run_id"]), str(row["lang"]),
                    str(context.get("topic_id") or context.get("topic") or row["artifact_id"]),
                ),
                "revenue_capable": contract.get("revenue_capable") is True,
                "metrics": _latest_metrics(connection, str(row["artifact_id"])),
                "money": _article_money(connection, str(row["artifact_id"])),
                "headline_image": (
                    f"../runs/{row['run_id']}/headline-image.png"
                    if (state_dir / "runs" / str(row["run_id"]) / "headline-image.png").is_file()
                    else None
                ),
            })
            artifacts.append(item)
        balance = _latest_account_metric(connection, "available_balance")
        pending = _pending_payout(connection)
        payout_receipts = _payout_receipts(connection)
        unknown_count = connection.execute(
            "SELECT COUNT(*) FROM metric_observations WHERE status='unknown'"
        ).fetchone()[0]
        commercial = _commercial(state_dir, connection)
    latest_run = artifacts[0]["run_id"] if artifacts else None
    today_articles = [
        row for row in artifacts
        if _parse_time(str(row["published_at"])).astimezone(JST).date() == local_now.date()
    ]
    report_articles = today_articles or [row for row in artifacts if row["run_id"] == latest_run]
    snapshot = {
        "schema_version": 1,
        "generated_at": _iso(local_now),
        "timezone": "Asia/Tokyo",
        "money": {
            **summaries,
            "mrr": summaries["month"]["verified_mrr_by_currency"],
            "available_balance": balance,
            "pending_payout": pending,
            "payout_receipts": payout_receipts,
        },
        "articles": artifacts,
        "report_articles": report_articles,
        "opportunities": _opportunities(state_dir / "opportunities.sqlite3"),
        "commercial": commercial,
        "learning": _learning(state_dir),
        "measurement_unknown_count": int(unknown_count),
    }
    snapshot["incident_timeline"] = _incident_timeline(state_dir, snapshot["money"])
    return snapshot


def _money(amounts: dict[str, float]) -> str:
    if not amounts:
        return "¥0 / $0"
    parts = []
    for currency, value in sorted(amounts.items()):
        if currency == "JPY":
            parts.append(f"¥{value:,.0f}")
        elif currency == "USD":
            parts.append(f"${value:,.2f}")
        else:
            parts.append(f"{currency} {value:,.2f}")
    return " / ".join(parts)


def _stream_lines(summary: dict[str, Any]) -> list[str]:
    streams = summary.get("verified_gross_by_stream", {})
    labels = {
        "self_owned_article": "自前ブログ買い切り",
        "self_owned_subscription": "自前アーカイブ購読",
        "note_paid_article": "note買い切り",
        "substack_subscription": "Substack購読",
        "editorial_fee": "寄稿料",
    }
    return [
        f"• {labels.get(stream, stream)}: {_money(values)}"
        for stream, values in sorted(streams.items())
    ]


def _signed(value: float) -> str:
    return f"{value:+.3g}"


def _learning_lines(snapshot: dict[str, Any]) -> list[str]:
    learning = snapshot.get("learning", {})
    day = learning.get("day_diff", {})
    lines = ["", "昨日→今日（説明差分・因果ではない）:"]
    if day.get("status") == "descriptive":
        lines.append(f"• {day.get('from_run_id')} → {day.get('to_run_id')}")
        for language, metrics in day.get("deltas", {}).items():
            lines.append(
                f"  {language.upper()}: "
                + " / ".join(f"{name} {_signed(value)}" for name, value in metrics.items())
            )
    else:
        lines.append("• 比較できる2 runの証拠がまだありません。")
    experiment = learning.get("latest_experiment")
    if not isinstance(experiment, dict):
        lines.extend(["", "自己改善: baseline/candidate比較はまだありません。"])
        return lines
    lines.extend([
        "",
        f"自己改善 #{experiment.get('experiment_id')} — {experiment.get('decision')}",
        "変えたのは1つだけ:",
        f"{experiment.get('changed_field')}: "
        f"「{experiment.get('text_diff', {}).get('before', '')}」→"
        f"「{experiment.get('text_diff', {}).get('after', '')}」",
    ])
    deltas = experiment.get("canary_deltas", {})
    if isinstance(deltas, dict) and deltas:
        lines.append(
            "本番canary差分: "
            + " / ".join(f"{name} {_signed(value)}" for name, value in deltas.items())
        )
    lines.append(f"判断理由: {experiment.get('reason')}")
    consumed = experiment.get("consumed_by_run_id")
    lines.append(
        f"次のrunで使用確認: {consumed}"
        if consumed else "次のrunでのstrategy使用receipt: まだありません"
    )
    return lines


def _commercial_lines(snapshot: dict[str, Any]) -> list[str]:
    lines = ["", "商流:"]
    active = snapshot.get("commercial", {}).get("active", [])
    if not active:
        return lines + ["• 証拠付きの進行中商流はありません。"]
    for item in active:
        states = " → ".join(
            f"{name}={value if value is not None else '未到達'}"
            for name, value in item["states"].items()
        )
        unknown = ", ".join(item["unknown_terms"]) or "なし"
        evidence = ", ".join(
            f"{name}={value}" for name, value in sorted(item["evidence_ids"].items())
        ) or "なし"
        money = item["money"]
        if money.get("status") == "verified":
            money_text = (
                f"{_money(money['gross'])} / 手数料: {_money(money['fees'])} / "
                f"手取: {_money(money['net'])}"
            )
        else:
            money_text = "外部receipt未確認（0ではなく不明）"
        mrr_text = _money(money["mrr"]) if money.get("mrr_status") == "verified" else "不明"
        lines.extend([
            f"• {item['publisher']}: {states}",
            f"  未確定条件: {unknown}",
            f"  証拠ID: {evidence}",
            f"  入金: {money_text} / MRR: {mrr_text}",
            f"  payment証拠ID: {', '.join(money['payment_evidence_ids']) or 'なし'}",
            f"  次: {item['next_action']}",
        ])
    return lines


def _incident_lines(snapshot: dict[str, Any]) -> list[str]:
    timeline = snapshot.get("incident_timeline")
    if not isinstance(timeline, dict):
        return ["", "最新runのincident timeline: 証拠indexなし"]
    publication = timeline["publication_truth"]
    verified = timeline["verified_money_truth"]
    lines = [
        "",
        f"最新runのincident timeline: {timeline['run_id']}",
        f"公開URL: {publication['public_count']}件",
        f"確認済み売上: {_money(verified['gross'])}",
        "確認済みMRR: " + (
            _money(verified["mrr"])
            if verified.get("mrr_status") == "verified"
            else "不明（外部契約receiptなし）"
        ),
    ]
    for item in timeline["incidents"]:
        lines.extend([
            f"• {item['phase']}: {item['reason']}",
            f"  原因class: {item['cause_class']} / owner: {item['owner']}",
            f"  次の自動処理: {item['next_automatic_action']} "
            f"({item['next_automatic_action_status']})",
        ])
    return lines


def render_message(snapshot: dict[str, Any], *, cadence: str) -> str:
    if cadence not in {"immediate", "hourly", "daily", "weekly"}:
        raise ValueError("unsupported report cadence")
    stamp = _parse_time(snapshot["generated_at"]).astimezone(JST)
    period = snapshot["money"]["week" if cadence == "weekly" else "today"]
    month = snapshot["money"]["month"]
    lines = [f"Writer — {stamp.month}月{stamp.day}日 {stamp:%H:%M}", ""]
    if period["verified_revenue_event_count"]:
        received = _money(period["verified_gross_by_currency"])
        net = _money(period["verified_net_by_currency"])
    else:
        received = "0件（外部receipt付きの受取はまだありません）"
        net = "確定できる受取なし"
    lines.extend([
        f"当社が受取済み: {received}",
        f"手数料後: {net}",
        f"今月: {_money(month['verified_gross_by_currency'])}",
        "MRR: " + (
            _money(snapshot["money"]["mrr"])
            if snapshot["money"]["mrr"]
            else "現在の外部契約receiptでは確認できない"
        ),
    ])
    balance = snapshot["money"]["available_balance"]
    if balance.get("status") == "verified":
        lines.append(f"利用可能残高: {_money({balance['unit']: balance['value']})}")
    else:
        lines.append("利用可能残高: 現在の外部receiptでは確認できない")
    for payout in snapshot["money"].get("payout_receipts", []):
        lines.append(f"Stripe payout receipt ({payout['status']}): {payout['url']}")
    lines.extend(["", "入金元:"])
    lines.extend(_stream_lines(period) or ["• 外部receipt付きの受取はまだありません"])
    lines.extend(["", "記事:"])
    for article in snapshot["report_articles"]:
        metric = article["metrics"].get("views", {})
        views = (
            f"{metric['value']:,.0f}表示"
            if metric.get("status") == "verified" and isinstance(metric.get("value"), (int, float))
            else "表示数は不明"
        )
        money = _money(article["money"]["gross"])
        surface = money if article["revenue_capable"] else "売上対象外"
        offer = _offer(article)
        offer_text = f" / {offer}" if offer else ""
        lines.append(f"• {article['platform']}: {surface} / {views}{offer_text}")
        lines.append(f"  {article['title']}")
        lines.append(f"  {article['live_url']}")
        for receipt in article["money"].get("receipts", []):
            lines.append(f"  Stripe receipt ({receipt['kind']}): {receipt['url']}")
    active = snapshot["opportunities"]["active"]
    lines.extend(["", "機会:"])
    if active:
        for item in active[:3]:
            lines.append(f"• {item['publisher']}: {item['state']} — {item['next_action']}")
    else:
        lines.append("• 応募・審査中の有償案件はありません。探索workerが継続確認します。")
    lines.extend(_commercial_lines(snapshot))
    lines.extend(_incident_lines(snapshot))
    lines.extend(_learning_lines(snapshot))
    if period["verified_revenue_event_count"]:
        interpretation = "閲覧数ではなく、外部receiptで確認できた受取だけを収益として集計しました。"
    else:
        interpretation = "公開は動いていますが、外部receipt付きの受取はまだ0です。閲覧数を収益とは数えていません。"
    lines.extend(["", f"解釈: {interpretation}", "次: Writerが公開・機会探索・収益確認を継続します。", "あなたの操作: なし。"])
    return "\n".join(lines)


def _card(label: str, value: str, status: str) -> str:
    return (
        f'<article class="money-card {html.escape(status)}">'
        f'<span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></article>'
    )


def render_html(snapshot: dict[str, Any]) -> str:
    today = snapshot["money"]["today"]
    month = snapshot["money"]["month"]
    balance = snapshot["money"]["available_balance"]
    today_known = today["verified_revenue_event_count"] > 0
    month_known = month["verified_revenue_event_count"] > 0
    mrr_known = bool(snapshot["money"]["mrr"])
    cards = "".join([
        _card(
            "Verified today", _money(today["verified_gross_by_currency"])
            if today_known else "0 external receipts",
            "verified" if today_known else "insufficient",
        ),
        _card(
            "Month to date", _money(month["verified_gross_by_currency"])
            if month_known else "0 external receipts",
            "verified" if month_known else "insufficient",
        ),
        _card(
            "Verified net", _money(month["verified_net_by_currency"])
            if month_known else "Not established",
            "verified" if month_known else "insufficient",
        ),
        _card(
            "MRR", _money(snapshot["money"]["mrr"])
            if mrr_known else "Unknown — no contract receipt",
            "verified" if mrr_known else "unknown",
        ),
        _card(
            "Available balance",
            _money({str(balance.get("unit")): balance["value"]})
            if balance.get("status") == "verified" else "Unknown — no receipt",
            "verified" if balance.get("status") == "verified" else "unknown",
        ),
    ])
    streams = month.get("verified_gross_by_stream", {})
    stream_labels = {
        "self_owned_article": "Self-owned article",
        "self_owned_subscription": "Self-owned archive",
        "note_paid_article": "note paid article",
        "substack_subscription": "Substack subscription",
        "editorial_fee": "Editorial fee",
    }
    stream_rows = "".join(
        f'<div class="stream"><span>{html.escape(stream_labels.get(name, name))}</span><b>{html.escape(_money(values))}</b></div>'
        for name, values in sorted(streams.items())
    ) or '<p class="empty">No external receipt-backed revenue yet.</p>'
    payout_links = "".join(
        f'<div class="stream"><span>Stripe payout ({html.escape(item["status"])})</span>'
        f'<b><a href="{html.escape(item["url"], quote=True)}">receipt ↗</a></b></div>'
        for item in snapshot["money"].get("payout_receipts", [])
    ) or '<p class="empty">No verified payout receipt yet.</p>'
    def article_row(row: dict[str, Any]) -> str:
        image = (
            f'<img class="thumb" src="{html.escape(row["headline_image"], quote=True)}" alt="">'
            if row.get("headline_image") else ""
        )
        offer = _offer(row)
        role = "revenue capable" if row["revenue_capable"] else "reach only"
        if offer and row["platform"] == "note":
            role += f'<small>¥{row["metrics"]["price"]["value"]:,.0f} one-time · paywall verified</small>'
        elif offer:
            role += '<small>paid subscribers only · paywall verified</small>'
        receipts = "".join(
            f'<small><a href="{html.escape(item["url"], quote=True)}">'
            f'{html.escape(item["kind"])} receipt ↗</a></small>'
            for item in row["money"].get("receipts", [])
        )
        return (
            "<tr>"
            f'<td><div class="article-title">{image}<div>{html.escape(row["title"])}'
            f'<small>{html.escape(row["artifact_id"])}</small></div></div></td>'
            f"<td>{html.escape(row['platform'])}</td>"
            f"<td>{role}</td>"
            f"<td>{html.escape(_money(row['money']['gross']))}{receipts}</td>"
            f'<td><a href="{html.escape(row["live_url"], quote=True)}">open ↗</a></td>'
            "</tr>"
        )
    article_rows = "".join(article_row(row) for row in snapshot["report_articles"])
    history_rows = "".join(article_row(row) for row in snapshot["articles"])
    commercial_text = "\n".join(_commercial_lines(snapshot)).strip()
    learning_text = "\n".join(_learning_lines(snapshot)).strip()
    return f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WRITER MONEY CONTROL</title><style>
:root{{--ink:#171611;--paper:#f3efe3;--lime:#c9ee55;--amber:#ffae45;--muted:#8e887c;--line:#3b3931}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--ink);color:var(--paper);font:14px ui-monospace,monospace}}
main{{width:min(1400px,calc(100% - 32px));margin:auto;padding:42px 0 90px}}h1{{font:500 clamp(44px,8vw,104px) Georgia,serif;line-height:.84;margin:12px 0 48px}}
.kicker{{color:var(--amber);letter-spacing:.18em}}.cards{{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:var(--line)}}
.money-card{{min-height:150px;padding:16px;background:#1d1c17;display:flex;flex-direction:column}}.money-card span{{color:var(--muted)}}
.money-card strong{{margin-top:auto;font:400 30px Georgia,serif}}.money-card.verified strong{{color:var(--lime)}}.money-card.unknown{{border:1px dashed var(--amber)}}.money-card.insufficient strong{{color:var(--muted)}}
section{{margin-top:64px}}h2{{font:400 34px Georgia,serif}}.stream{{display:flex;justify-content:space-between;border-top:1px solid var(--line);padding:16px 4px}}
table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:14px 8px;border-bottom:1px solid var(--line)}}td small{{display:block;color:var(--muted);margin-top:5px}}a{{color:var(--amber)}}.empty{{color:var(--muted)}}
.article-title{{display:flex;align-items:center;gap:12px}}.thumb{{width:72px;height:48px;object-fit:cover;border:1px solid var(--line)}}details{{margin-top:24px}}summary{{cursor:pointer;color:var(--amber);padding:12px 0}}
@media(max-width:900px){{
main{{width:calc(100% - 20px);padding-top:28px}}h1{{font-size:50px;margin-bottom:36px}}.cards{{grid-template-columns:1fr 1fr}}
.money-card{{min-height:132px}}section{{margin-top:48px}}h2{{font-size:30px}}
table,tbody,tr,td{{display:block;width:100%}}thead{{display:none}}tr{{display:grid;grid-template-columns:1.3fr 1fr 1fr 1fr;border-bottom:1px solid var(--line);padding:14px 0;gap:8px}}
td{{border:0;padding:2px 4px;font-size:12px}}td:first-child{{grid-column:1/-1}}.thumb{{width:84px;height:56px}}
}}
</style></head><body><main><div class="kicker">RECEIPT-BACKED · VERIFIED ≠ ESTIMATED</div><h1>WRITER<br>MONEY CONTROL</h1>
<div class="cards">{cards}</div><section><h2>Revenue by stream</h2>{stream_rows}</section>
<section><h2>Payout receipts</h2>{payout_links}</section>
<section><h2>Current publication run</h2><table><thead><tr><th>Article</th><th>Platform</th><th>Role</th><th>Gross</th><th>Public URL</th></tr></thead><tbody>{article_rows}</tbody></table>
<details><summary>Full publication history ({len(snapshot['articles'])} artifacts)</summary><table><tbody>{history_rows}</tbody></table></details></section>
<section><h2>Commercial pipeline</h2><p>{html.escape(commercial_text).replace(chr(10), '<br>')}</p></section>
<section><h2>Observable improvement</h2><p>{html.escape(learning_text).replace(chr(10), '<br>')}</p></section>
<section><h2>Agent explanation</h2><p>{html.escape(render_message(snapshot, cadence='daily')).replace(chr(10), '<br>')}</p></section>
</main></body></html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=SCRIPT_DIR.parent / "state")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--html-out", type=Path)
    parser.add_argument("--cadence", choices=("immediate", "hourly", "daily", "weekly"))
    parser.add_argument("--now")
    args = parser.parse_args(argv)
    now = _parse_time(args.now) if args.now else datetime.now(JST)
    snapshot = build_snapshot(state_dir=args.state_dir, now=now)
    if args.json_out:
        _atomic(args.json_out, json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    if args.html_out:
        _atomic(args.html_out, render_html(snapshot))
    if args.cadence:
        print(render_message(snapshot, cadence=args.cadence))
    else:
        print(json.dumps(snapshot, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
