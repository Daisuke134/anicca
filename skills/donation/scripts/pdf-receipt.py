#!/usr/bin/env python3
"""
pdf-receipt.py — render workspace/donation/receipts/YYYY-MM.pdf with
the donor entity, period, total, breakdown, transaction IDs.

Tries reportlab first; if unavailable, falls back to writing a single-page
plain-text "PDF stub" (`.pdf.txt`) so the pipeline doesn't break in
environments without reportlab. The run state is updated to reflect which
backend was used.
"""

from __future__ import annotations

import json
import os
import sys
import datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import (  # noqa: E402
    RECEIPTS_DIR,
    is_dry_run,
    load_env_files,
    load_wizard_config,
    prior_month_period,
    read_run_state,
    write_run_state,
)


def render_with_reportlab(pdf_path: Path, ctx: dict) -> bool:
    try:
        from reportlab.lib.pagesizes import LETTER  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore
        from reportlab.lib.units import inch  # type: ignore
    except Exception as e:
        sys.stderr.write(f"[pdf-receipt] reportlab unavailable: {e}\n")
        return False

    c = canvas.Canvas(str(pdf_path), pagesize=LETTER)
    width, height = LETTER
    y = height - 1.0 * inch

    c.setFont("Helvetica-Bold", 18)
    c.drawString(1.0 * inch, y, f"Donation Receipt — {ctx['period']}")
    y -= 0.4 * inch

    c.setFont("Helvetica", 11)
    c.drawString(1.0 * inch, y, f"Donor: {ctx['tax_entity']}")
    y -= 0.22 * inch
    c.drawString(1.0 * inch, y, f"Generated: {ctx['generated_at']}")
    y -= 0.22 * inch
    c.drawString(1.0 * inch, y, f"Revenue base (prior month): ${ctx['revenue_usd']:.2f}")
    y -= 0.22 * inch
    c.drawString(1.0 * inch, y, f"Donation rate: {ctx['percent']}% (floor $1)")
    y -= 0.22 * inch
    c.drawString(1.0 * inch, y, f"Total donation: ${ctx['total_amount_usd']:.2f}")
    y -= 0.22 * inch
    c.drawString(1.0 * inch, y, f"Mode: {'DRY_RUN' if ctx['dry_run'] else 'LIVE'}")
    y -= 0.4 * inch

    c.setFont("Helvetica-Bold", 12)
    c.drawString(1.0 * inch, y, "Recipient breakdown")
    y -= 0.25 * inch

    c.setFont("Helvetica", 10)
    for t in ctx["transfers"]:
        line = (
            f"  • {t.get('name') or t.get('recipient_id')} — "
            f"${t.get('amount_usd', 0):.2f}   "
            f"transfer_id={t.get('transfer_id')}   status={t.get('status')}"
        )
        c.drawString(1.0 * inch, y, line)
        y -= 0.2 * inch
        if y < 1.0 * inch:
            c.showPage()
            y = height - 1.0 * inch
            c.setFont("Helvetica", 10)

    y -= 0.3 * inch
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(1.0 * inch, y, f"Public ledger: {ctx['receipt_host']}")
    y -= 0.18 * inch
    c.drawString(1.0 * inch, y, f"transfer_group: {ctx.get('transfer_group', '-')}")
    c.showPage()
    c.save()
    return True


def render_text_fallback(stub_path: Path, ctx: dict):
    lines = [
        f"Donation Receipt — {ctx['period']}",
        f"Donor: {ctx['tax_entity']}",
        f"Generated: {ctx['generated_at']}",
        f"Revenue base (prior month): ${ctx['revenue_usd']:.2f}",
        f"Donation rate: {ctx['percent']}% (floor $1)",
        f"Total donation: ${ctx['total_amount_usd']:.2f}",
        f"Mode: {'DRY_RUN' if ctx['dry_run'] else 'LIVE'}",
        "",
        "Recipient breakdown:",
    ]
    for t in ctx["transfers"]:
        lines.append(
            f"  - {t.get('name') or t.get('recipient_id')}: ${t.get('amount_usd', 0):.2f}  "
            f"transfer_id={t.get('transfer_id')}  status={t.get('status')}"
        )
    lines.append("")
    lines.append(f"Public ledger: {ctx['receipt_host']}")
    lines.append(f"transfer_group: {ctx.get('transfer_group', '-')}")
    stub_path.write_text("\n".join(lines))


def main() -> int:
    load_env_files()
    cfg = load_wizard_config()
    period_label, _, _ = prior_month_period()
    state = read_run_state(period_label)
    if not state:
        sys.stderr.write("[pdf-receipt] no run state — run compute-revenue.py + transfer.py first\n")
        return 2

    ctx = {
        "period": period_label,
        "tax_entity": cfg["tax_entity"],
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "revenue_usd": float(state.get("revenue_usd") or 0),
        "percent": cfg["percent"],
        "total_amount_usd": float(state.get("total_amount_usd") or 0),
        "transfers": state.get("transfers") or [],
        "transfer_group": state.get("transfer_group", f"donation-{period_label}"),
        "receipt_host": cfg["receipt_host"],
        "dry_run": bool(state.get("dry_run", is_dry_run())),
    }

    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = RECEIPTS_DIR / f"{period_label}.pdf"
    backend = "reportlab"
    ok = render_with_reportlab(pdf_path, ctx)
    if not ok:
        backend = "text-fallback"
        stub = RECEIPTS_DIR / f"{period_label}.pdf.txt"
        render_text_fallback(stub, ctx)
        pdf_path = stub

    write_run_state(period_label, {
        "receipt_pdf": str(pdf_path),
        "receipt_backend": backend,
    })
    sys.stderr.write(f"[pdf-receipt] wrote {pdf_path} (backend={backend})\n")
    print(json.dumps({"receipt_pdf": str(pdf_path), "backend": backend}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
