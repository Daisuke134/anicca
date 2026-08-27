"""Allowlisted, read-only HTML projection over Marketing Engine ledgers."""

from __future__ import annotations

import html
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


_FIELDS = {
    "runs": (
        "run_id",
        "product_id",
        "channel_id",
        "status",
        "started_at",
        "updated_at",
    ),
    "publications": (
        "run_id",
        "artifact_id",
        "platform",
        "status",
        "public_url",
        "readback_status",
    ),
    "metrics": (
        "artifact_id",
        "status",
        "window",
        "observed_at",
    ),
    "experiments": (
        "experiment_id",
        "status",
        "reward",
        "opponent",
        "before_hash",
        "after_hash",
    ),
    "observations": (
        "observation_id",
        "product_id",
        "channel_id",
        "kind",
        "due_at",
        "terminal_at",
        "status",
        "reward_effect",
        "observed_count",
    ),
}


def _objects(paths: list[Path], fields: tuple[str, ...]) -> tuple[list[dict], int]:
    rows = []
    errors = 0
    for path in sorted(paths)[-100:]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors += 1
            continue
        if not isinstance(value, dict):
            errors += 1
            continue
        rows.append({field: value.get(field) for field in fields})
    return rows, errors


def _counts(rows: list[dict]) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get("status") or "unknown") for row in rows).items()))


def build_snapshot(
    *,
    runtime_root: Path,
    generated_at: str,
) -> dict[str, Any]:
    """Read bounded, allowlisted fields; never mutate the runtime root."""

    root = Path(runtime_root)
    runs, run_errors = _objects(
        list((root / "runs").glob("*/manifest.json")),
        _FIELDS["runs"],
    )
    publications, publication_errors = _objects(
        list((root / "receipts").rglob("*.json")),
        _FIELDS["publications"],
    )
    metrics, metric_errors = _objects(
        list((root / "metrics").rglob("*.json")),
        _FIELDS["metrics"],
    )
    experiments, experiment_errors = _objects(
        list((root / "experiments").rglob("*.json")),
        _FIELDS["experiments"],
    )
    terminal, terminal_errors = _objects(
        list((root / "observations/terminal").glob("*.json")),
        _FIELDS["observations"],
    )
    terminal_ids = {row.get("observation_id") for row in terminal}
    pending, pending_errors = _objects(
        list((root / "observations/open").glob("*.json")),
        _FIELDS["observations"],
    )
    pending = [
        {**row, "status": "pending"}
        for row in pending
        if row.get("observation_id") not in terminal_ids
    ]
    observations = terminal + pending
    sections = {
        "runs": runs,
        "publications": publications,
        "metrics": metrics,
        "experiments": experiments,
        "observations": observations,
    }
    return {
        "title": "ANICCA MARKETING CONTROL",
        "generated_at": generated_at,
        "summary": {
            name: _counts(rows)
            for name, rows in sections.items()
        },
        "projection_errors": sum(
            (
                run_errors,
                publication_errors,
                metric_errors,
                experiment_errors,
                terminal_errors,
                pending_errors,
            )
        ),
        **sections,
    }


def _value(value: Any, *, field: str) -> str:
    if value is None:
        return "—"
    text = str(value)
    if field.endswith("_hash") and len(text) > 12:
        text = text[:12]
    escaped = html.escape(text)
    if field == "public_url" and text.startswith("https://"):
        return (
            f'<a href="{html.escape(text, quote=True)}" '
            'target="_blank" rel="noreferrer">open ↗</a>'
        )
    return escaped


def _table(title: str, rows: list[dict], fields: tuple[str, ...]) -> str:
    header = "".join(f"<th>{html.escape(field.replace('_', ' '))}</th>" for field in fields)
    if rows:
        body = "".join(
            "<tr>"
            + "".join(
                f'<td data-field="{html.escape(field)}">{_value(row.get(field), field=field)}</td>'
                for field in fields
            )
            + "</tr>"
            for row in rows
        )
    else:
        body = f'<tr><td class="empty" colspan="{len(fields)}">No ledger entries yet.</td></tr>'
    return (
        '<section class="ledger">'
        f'<div class="section-index">{html.escape(title[:2].upper())}</div>'
        f"<h2>{html.escape(title)}</h2>"
        '<div class="table-shell"><table>'
        f"<thead><tr>{header}</tr></thead><tbody>{body}</tbody>"
        "</table></div></section>"
    )


def render_dashboard(snapshot: dict[str, Any]) -> str:
    """Render a standalone, script-free dashboard."""

    summary = snapshot["summary"]
    cards = []
    for name in ("runs", "publications", "metrics", "experiments", "observations"):
        counts = summary[name]
        total = sum(counts.values())
        detail = " · ".join(f"{key} {value}" for key, value in counts.items()) or "waiting"
        cards.append(
            '<article class="signal">'
            f'<span class="signal-name">{html.escape(name)}</span>'
            f'<strong>{total}</strong><small>{html.escape(detail)}</small>'
            "</article>"
        )
    tables = "".join(
        _table(name, snapshot[name], _FIELDS[name])
        for name in ("runs", "publications", "metrics", "experiments", "observations")
    )
    generated = html.escape(str(snapshot["generated_at"]))
    errors = int(snapshot.get("projection_errors", 0))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ANICCA MARKETING CONTROL</title>
  <style>
    :root {{
      --ink:#13110e; --paper:#eee9dc; --paper-2:#dcd4c3;
      --signal:#f1a33b; --acid:#b8d94a; --muted:#766f64; --line:#3a352e;
    }}
    * {{ box-sizing:border-box; }}
    body {{
      margin:0; color:var(--paper); background:
        linear-gradient(rgba(255,255,255,.018) 1px,transparent 1px),
        linear-gradient(90deg,rgba(255,255,255,.018) 1px,transparent 1px),
        var(--ink);
      background-size:28px 28px;
      font-family:"Courier New",monospace;
    }}
    body::before {{
      content:""; position:fixed; inset:0; pointer-events:none; opacity:.18;
      background:radial-gradient(circle at 72% 12%,var(--signal),transparent 26%);
      mix-blend-mode:screen;
    }}
    main {{ width:min(1440px,calc(100% - 40px)); margin:0 auto; padding:48px 0 96px; }}
    header {{ display:grid; grid-template-columns:1fr auto; gap:24px; border-top:8px solid var(--paper); padding-top:20px; }}
    .kicker {{ color:var(--signal); letter-spacing:.22em; text-transform:uppercase; font-size:11px; }}
    h1 {{ margin:10px 0 0; max-width:900px; font-family:"Iowan Old Style","Palatino Linotype",serif; font-size:clamp(44px,8vw,116px); line-height:.82; letter-spacing:-.055em; font-weight:500; }}
    .stamp {{ border:1px solid var(--line); padding:12px; align-self:start; color:var(--paper-2); font-size:11px; line-height:1.6; }}
    .signals {{ display:grid; grid-template-columns:repeat(5,1fr); gap:1px; margin:50px 0 84px; background:var(--line); border:1px solid var(--line); }}
    .signal {{ min-height:150px; padding:16px; background:var(--ink); display:flex; flex-direction:column; }}
    .signal-name {{ color:var(--muted); text-transform:uppercase; letter-spacing:.12em; font-size:10px; }}
    .signal strong {{ margin-top:auto; font-family:"Iowan Old Style","Palatino Linotype",serif; color:var(--acid); font-size:54px; font-weight:400; }}
    .signal small {{ color:var(--paper-2); min-height:28px; line-height:1.4; }}
    .ledger {{ position:relative; margin-top:72px; }}
    .section-index {{ position:absolute; left:-4px; top:-38px; color:var(--signal); font-size:11px; letter-spacing:.2em; }}
    h2 {{ font-family:"Iowan Old Style","Palatino Linotype",serif; font-size:36px; font-weight:400; margin:0 0 16px; text-transform:capitalize; }}
    .table-shell {{ overflow:auto; border-top:1px solid var(--paper-2); }}
    table {{ width:100%; min-width:760px; border-collapse:collapse; }}
    th {{ color:var(--muted); font-size:9px; letter-spacing:.12em; text-align:left; text-transform:uppercase; padding:12px 10px; border-bottom:1px solid var(--line); }}
    td {{ padding:15px 10px; border-bottom:1px solid var(--line); font-size:12px; vertical-align:top; }}
    td[data-field="status"] {{ color:var(--acid); font-weight:700; text-transform:uppercase; }}
    a {{ color:var(--signal); }}
    .empty {{ color:var(--muted); font-family:"Iowan Old Style","Palatino Linotype",serif; font-size:18px; padding:30px 10px; }}
    footer {{ margin-top:80px; padding-top:14px; border-top:1px solid var(--line); color:var(--muted); font-size:10px; letter-spacing:.08em; }}
    @media (max-width:900px) {{
      header {{ grid-template-columns:1fr; }} .signals {{ grid-template-columns:1fr 1fr; }}
      .signal:last-child {{ grid-column:1 / -1; }} main {{ width:min(100% - 24px,1440px); }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div><div class="kicker">Receipt-backed / read-only projection</div><h1>ANICCA<br>MARKETING CONTROL</h1></div>
      <div class="stamp">GENERATED<br>{generated}<br>PROJECTION ERRORS {errors}</div>
    </header>
    <section class="signals">{''.join(cards)}</section>
    {tables}
    <footer>NO INDEPENDENT STATE · SOURCE: ANICCA MARKETING LEDGERS · SAFE TO DELETE AND REBUILD</footer>
  </main>
</body>
</html>
"""


def write_dashboard(path: Path, html_text: str) -> None:
    """Atomically write only the requested derived artifact."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(html_text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
