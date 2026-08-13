#!/usr/bin/env python3
"""Render the public Capafy company dashboard from one canonical projection."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from capafy_outcome import validate_outcome


PROJECTION_FIELDS = {
    "schema_version",
    "kind",
    "as_of",
    "date",
    "last_event_id",
    "projection_id",
    "inventory",
    "gross_usd",
    "pending_usd",
    "realized_usd",
    "mrr_usd",
    "cost_usd",
    "contribution_usd",
    "orders",
    "paid_orders",
    "account",
    "marketing",
    "metrics",
    "incident",
    "experiment",
    "listing_url",
    "dashboard_url",
    "sources",
}
SOURCE_NAMES = ("money", "inventory", "account", "marketing", "cost")
FRESHNESS_VALUES = {"fresh", "stale", "unknown"}
PRIVATE_PREFIXES = ("/Users/", "/private/", "~/", "file:")


@dataclass(frozen=True)
class DashboardBuild:
    index_path: Path
    state_path: Path
    projection_id: str


def _walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _is_rfc3339(value: Any) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return False
    return isinstance(value, str) and "T" in value and parsed.utcoffset() is not None


def validate_public_projection(projection: dict) -> list[str]:
    if not isinstance(projection, dict):
        return ["projection must be an object"]
    errors = validate_outcome(projection)
    unknown = sorted(set(projection) - PROJECTION_FIELDS)
    if unknown:
        errors.append(f"unsupported projection fields: {', '.join(unknown)}")
    sources = projection.get("sources")
    if not isinstance(sources, dict):
        errors.append("sources must contain money, inventory, account, marketing, and cost")
    else:
        if set(sources) != set(SOURCE_NAMES):
            errors.append("sources must contain money, inventory, account, marketing, and cost")
        for name in SOURCE_NAMES:
            source = sources.get(name)
            if not isinstance(source, dict) or set(source) != {"observed_at", "freshness"}:
                errors.append(f"sources.{name} must contain observed_at and freshness")
                continue
            observed_at = source["observed_at"]
            freshness = source["freshness"]
            if observed_at is not None and not _is_rfc3339(observed_at):
                errors.append(f"sources.{name}.observed_at must be RFC3339 or null")
            if freshness not in FRESHNESS_VALUES:
                errors.append(f"sources.{name}.freshness must be fresh, stale, or unknown")
            elif (freshness == "unknown") != (observed_at is None):
                errors.append(f"sources.{name} freshness does not match observed_at")
    if any(
        isinstance(value, str) and value.startswith(PRIVATE_PREFIXES)
        for value in _walk(projection)
    ):
        errors.append("projection contains a private path")
    return errors


def _money(value: Any) -> str:
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    return f"-${abs(amount):.2f}" if amount < 0 else f"${amount:.2f}"


def _link(url: str | None, label: str) -> str:
    if not url:
        return '<span class="muted">Not yet verified</span>'
    escaped = html.escape(url, quote=True)
    return f'<a href="{escaped}" rel="noopener noreferrer">{html.escape(label)}</a>'


def render_html(projection: dict) -> str:
    errors = validate_public_projection(projection)
    if errors:
        raise ValueError("; ".join(errors))
    inv = projection["inventory"]
    account = projection["account"]
    marketing = projection["marketing"]
    metrics = projection["metrics"]
    sources = projection["sources"]
    paid_text = (
        f"{projection['paid_orders']} paid"
        if projection["paid_orders"] is not None
        else "paid count unavailable"
    )
    short_id = projection["projection_id"].removeprefix("sha256:")[:12]
    metric_cards = "".join(
        f'<div class="metric"><span>{html.escape(label)}</span><strong>{metrics.get(field, "—")}</strong></div>'
        for field, label in (
            ("views", "Views"),
            ("likes", "Likes"),
            ("comments", "Comments"),
            ("clicks", "Attributed clicks"),
        )
    )
    incident = projection.get("incident")
    if isinstance(incident, dict):
        incident_html = (
            '<section class="panel incident"><h2>Active repair</h2>'
            f'<p><strong>{html.escape(str(incident.get("phase", "unknown")))}</strong> · '
            f'{html.escape(str(incident.get("summary", "Unspecified incident")))}</p>'
            f'<p class="muted">Owner: {html.escape(str(incident.get("owner", "unknown")))} · '
            f'Next retry: {html.escape(str(incident.get("next_retry_at") or "automatic"))}</p></section>'
        )
    else:
        incident_html = (
            '<section class="panel healthy"><h2>Repair status</h2>'
            '<p>No active incident in the canonical ledger.</p></section>'
        )
    experiment = projection.get("experiment")
    if isinstance(experiment, dict):
        observed = experiment.get("observed_contribution_usd")
        observed_text = _money(observed) if observed is not None else "not measured"
        experiment_status = str(experiment.get("status") or "unknown")
        experiment_heading = "Active revenue experiment" if experiment_status == "active" else "Stopped revenue experiment"
        stop_reason = experiment.get("stop_reason")
        stop_reason_html = f'<br>Reason: {html.escape(str(stop_reason))}' if stop_reason else ""
        experiment_html = (
            f'<section class="panel"><h2>{experiment_heading}</h2>'
            f'<p><strong>{html.escape(str(experiment.get("purchase_model", "unknown")))}</strong> · '
            f'{_money(experiment.get("price_usd") or 0)} price hypothesis</p>'
            f'<p>{_money(experiment.get("projected_contribution_usd") or 0)} projected · not realized. '
            f'Observed contribution: {html.escape(observed_text)}.</p>'
            f'<p>{_link(experiment.get("public_url"), "Open the experiment product")}</p>'
            f'<p class="muted">Success: {html.escape(str(experiment.get("success_metric") or "not specified"))}<br>'
            f'Stop: {html.escape(str(experiment.get("stop_condition") or "not specified"))}{stop_reason_html}</p></section>'
        )
    else:
        experiment_html = '<section class="panel"><h2>Revenue experiment</h2><p>No active experiment.</p></section>'
    source_rows = []
    for name in SOURCE_NAMES:
        source = sources[name]
        freshness = source["freshness"]
        status, note = {"fresh": ("FRESH", "current"), "stale": ("STALE", "not current"), "unknown": ("UNKNOWN", "not observed")}[freshness]
        observed_at = source["observed_at"] or "not observed"
        source_rows.append(
            f'<div class="source {freshness}"><strong>{html.escape(name)}</strong>'
            f'<span class="source-status">{status}</span>'
            f'<span class="muted">Observed: {html.escape(observed_at)} · {note}</span></div>'
        )
    sources_html = (
        '<section class="panel"><h2>Source freshness</h2>'
        '<div class="source-grid">' + "".join(source_rows) + "</div></section>"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Live, evidence-backed operating state for Capafy.">
  <title>Capafy company state</title>
  <style>
    :root {{ color-scheme: dark; --bg:#07110d; --panel:#102019; --line:#294537; --text:#f2fff8; --muted:#9fc2ae; --mint:#66f0aa; --amber:#ffc86b; }}
    * {{ box-sizing:border-box; }} body {{ margin:0; background:radial-gradient(circle at top,#173628 0,var(--bg) 42%); color:var(--text); font:16px/1.55 ui-sans-serif,system-ui,sans-serif; }}
    main {{ width:min(1080px,calc(100% - 32px)); margin:0 auto; padding:56px 0 72px; }}
    header {{ margin-bottom:28px; }} .eyebrow {{ color:var(--mint); font-weight:700; letter-spacing:.12em; text-transform:uppercase; }}
    h1 {{ margin:.25rem 0; font-size:clamp(2.4rem,7vw,5rem); line-height:1; }} h2 {{ margin-top:0; }}
    .muted {{ color:var(--muted); }} .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:14px; margin:14px 0; }}
    .panel,.metric {{ border:1px solid var(--line); border-radius:18px; background:color-mix(in srgb,var(--panel) 92%,transparent); padding:20px; }}
    .metric span {{ display:block; color:var(--muted); }} .metric strong {{ display:block; margin-top:5px; font-size:1.65rem; }}
    .money strong {{ color:var(--mint); }} .incident {{ border-color:#70542c; }} .incident strong {{ color:var(--amber); }} .healthy {{ border-color:#2f7653; }}
    .source-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:10px; }} .source {{ display:grid; gap:2px; border:1px solid var(--line); border-radius:12px; padding:12px; }} .source-status {{ font-weight:800; letter-spacing:.08em; }} .source.fresh .source-status {{ color:var(--mint); }} .source.stale,.source.unknown {{ border-color:var(--amber); }} .source.stale .source-status,.source.unknown .source-status {{ color:var(--amber); }}
    a {{ color:var(--mint); overflow-wrap:anywhere; }} a:focus-visible {{ outline:3px solid var(--amber); outline-offset:3px; }}
    footer {{ margin-top:28px; color:var(--muted); font-size:.9rem; }}
    @media (prefers-reduced-motion:reduce) {{ * {{ scroll-behavior:auto!important; }} }}
  </style>
</head>
<body><main>
  <header><div class="eyebrow">Evidence-backed company loop</div><h1>Capafy</h1><p>One Builder. One Marketer. One shared revenue ledger.</p><p class="muted">As of {html.escape(projection['as_of'])} · Projection {short_id}</p></header>
  <section class="grid money" aria-label="Money">
    <div class="metric"><span>Gross revenue</span><strong>{_money(projection['gross_usd'])}</strong></div>
    <div class="metric"><span>Pending balance</span><strong>{_money(projection['pending_usd'])}</strong></div>
    <div class="metric"><span>Realized payout</span><strong>{_money(projection['realized_usd'])}</strong></div>
    <div class="metric"><span>MRR</span><strong>{_money(projection['mrr_usd'])}</strong></div>
    <div class="metric"><span>Model/tool cost</span><strong>{_money(projection['cost_usd'])}</strong></div>
    <div class="metric"><span>Contribution</span><strong>{_money(projection['contribution_usd'])}</strong></div>
  </section>
  <section class="grid" aria-label="Business state">
    <div class="panel"><h2>Sales & inventory</h2><p>{projection['orders']} lifetime orders · {paid_text}</p><p>{inv['online']} online · {inv['under_review']} under review · {inv['draft']} draft · {inv['rejected']} rejected</p></div>
    <div class="panel"><h2>Instagram owner</h2><p><strong>@{html.escape(account['handle'])}</strong></p><p>{html.escape(str(account['lifecycle_status']))} · {html.escape(str(account['capability']))}</p><p class="muted">Session: {'verified' if account['session_established'] else 'not verified'} · Account: {html.escape(str(account['account_status']))}</p></div>
    <div class="panel"><h2>Public evidence</h2><p>{_link(marketing.get('public_post_url'), 'Open the verified Reel')}</p><p>{_link(projection.get('listing_url'), 'Open the Capafy skill')}</p><p>{_link(marketing.get('campaign_url'), 'Open the attributed campaign')}</p></div>
  </section>
  <section class="panel"><h2>Latest marketing measurements</h2><div class="grid">{metric_cards}</div></section>
  {sources_html}
  {experiment_html}
  {incident_html}
  <footer>Projection {html.escape(projection['projection_id'])} · Last event {html.escape(str(projection['last_event_id']))}</footer>
</main></body></html>
"""


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_dashboard(projection: dict, output_dir: Path) -> DashboardBuild:
    errors = validate_public_projection(projection)
    if errors:
        raise ValueError("; ".join(errors))
    output_dir = Path(output_dir)
    index_path = output_dir / "index.html"
    state_path = output_dir / "state.json"
    state = json.dumps(
        projection, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8") + b"\n"
    rendered = render_html(projection).encode("utf-8")
    _atomic_write(state_path, state)
    _atomic_write(index_path, rendered)
    return DashboardBuild(index_path, state_path, projection["projection_id"])


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projection", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.projection:
            projection = json.loads(args.projection.read_text(encoding="utf-8"))
        else:
            projection = json.load(sys.stdin)
        result = build_dashboard(projection, args.output_dir)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "index_path": str(result.index_path),
                "state_path": str(result.state_path),
                "projection_id": result.projection_id,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
