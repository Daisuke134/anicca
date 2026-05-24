#!/usr/bin/env python3
"""
annual-1099.py — December → January rollup for 1099-MISC reporting.

For year Y, reads run-Y-MM.json for MM in 01..12 and produces:
  ~/.openclaw/workspace/donation/1099/Y/<recipient>.pdf  (per recipient)
  ~/.openclaw/workspace/donation/1099/Y/totals.csv       (LLC books)

Per-recipient PDFs include all transfers in the year, with transfer_id +
status, suitable for attachment to a 1099-MISC. The totals.csv lists each
recipient's name, EIN/NPO id, country, and yearly total.

Usage:
  python3 annual-1099.py --year 2026
  (default: prior calendar year)
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import (  # noqa: E402
    ROLLUP_DIR,
    WORKSPACE,
    load_env_files,
    load_recipients,
    load_wizard_config,
)


def collect_year(year: int) -> dict:
    by_recipient: dict = {}
    months_seen: list = []
    for m in range(1, 13):
        label = f"{year}-{m:02d}"
        rp = WORKSPACE / f"run-{label}.json"
        if not rp.exists():
            continue
        try:
            blob = json.loads(rp.read_text())
        except Exception:
            continue
        months_seen.append(label)
        for t in blob.get("transfers") or []:
            rid = t.get("recipient_id") or "unknown"
            entry = by_recipient.setdefault(rid, {"name": t.get("name") or rid, "transfers": [], "total_usd": 0.0})
            entry["transfers"].append({
                "period": label,
                "amount_usd": float(t.get("amount_usd") or 0),
                "transfer_id": t.get("transfer_id"),
                "status": t.get("status"),
            })
            entry["total_usd"] += float(t.get("amount_usd") or 0)
    return {"year": year, "months_with_data": months_seen, "by_recipient": by_recipient}


def render_per_recipient(year: int, rid: str, entry: dict, recipients: list, out_dir: Path):
    meta = next((r for r in recipients if r.get("recipient_id") == rid), {})
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        from reportlab.lib.pagesizes import LETTER  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore
        from reportlab.lib.units import inch  # type: ignore
        pdf_path = out_dir / f"{rid}.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=LETTER)
        width, height = LETTER
        y = height - 1.0 * inch
        c.setFont("Helvetica-Bold", 16)
        c.drawString(1.0 * inch, y, f"Annual Donation Summary — {year}")
        y -= 0.3 * inch
        c.setFont("Helvetica", 11)
        c.drawString(1.0 * inch, y, f"Recipient: {entry['name']}")
        y -= 0.2 * inch
        c.drawString(1.0 * inch, y, f"EIN / NPO id: {meta.get('ein_or_npo_id', '-')}")
        y -= 0.2 * inch
        c.drawString(1.0 * inch, y, f"Country: {meta.get('country', '-')}")
        y -= 0.2 * inch
        c.drawString(1.0 * inch, y, f"Total transferred: ${entry['total_usd']:.2f}")
        y -= 0.4 * inch
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1.0 * inch, y, "Transfers")
        y -= 0.25 * inch
        c.setFont("Helvetica", 10)
        for t in entry["transfers"]:
            line = f"  {t['period']}  ${t['amount_usd']:.2f}  id={t['transfer_id']}  {t['status']}"
            c.drawString(1.0 * inch, y, line)
            y -= 0.2 * inch
            if y < 1.0 * inch:
                c.showPage(); y = height - 1.0 * inch; c.setFont("Helvetica", 10)
        c.showPage(); c.save()
        return pdf_path
    except Exception as e:
        sys.stderr.write(f"[annual-1099] reportlab fallback for {rid}: {e}\n")
        stub = out_dir / f"{rid}.pdf.txt"
        lines = [
            f"Annual Donation Summary — {year}",
            f"Recipient: {entry['name']}",
            f"EIN / NPO id: {meta.get('ein_or_npo_id', '-')}",
            f"Country: {meta.get('country', '-')}",
            f"Total transferred: ${entry['total_usd']:.2f}",
            "",
            "Transfers:",
        ]
        for t in entry["transfers"]:
            lines.append(f"  {t['period']}  ${t['amount_usd']:.2f}  id={t['transfer_id']}  {t['status']}")
        stub.write_text("\n".join(lines))
        return stub


def write_totals_csv(year: int, summary: dict, recipients: list, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    fp = out_dir / "totals.csv"
    with fp.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["recipient_id", "name", "ein_or_npo_id", "country", "total_usd_for_year", "transfers_count"])
        for rid, entry in summary["by_recipient"].items():
            meta = next((r for r in recipients if r.get("recipient_id") == rid), {})
            w.writerow([
                rid,
                entry["name"],
                meta.get("ein_or_npo_id", ""),
                meta.get("country", ""),
                f"{entry['total_usd']:.2f}",
                len(entry["transfers"]),
            ])
    return fp


def main() -> int:
    load_env_files()
    cfg = load_wizard_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=dt.date.today().year - 1)
    args = ap.parse_args()
    year = args.year

    summary = collect_year(year)
    recipients = load_recipients(cfg["recipients_path"])
    out_dir = ROLLUP_DIR / str(year)
    pdfs: list[str] = []
    for rid, entry in summary["by_recipient"].items():
        p = render_per_recipient(year, rid, entry, recipients, out_dir)
        pdfs.append(str(p))
    csv_path = write_totals_csv(year, summary, recipients, out_dir)

    rollup_state = {
        "year": year,
        "months_with_data": summary["months_with_data"],
        "per_recipient_pdfs": pdfs,
        "totals_csv": str(csv_path),
        "recipient_count": len(summary["by_recipient"]),
        "grand_total_usd": round(sum(e["total_usd"] for e in summary["by_recipient"].values()), 2),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "rollup.json").write_text(json.dumps(rollup_state, ensure_ascii=False, indent=2))
    sys.stderr.write(
        f"[annual-1099] year={year} recipients={len(summary['by_recipient'])} "
        f"grand_total=${rollup_state['grand_total_usd']:.2f} -> {out_dir}\n"
    )
    print(json.dumps(rollup_state, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
