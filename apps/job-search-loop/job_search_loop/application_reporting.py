from __future__ import annotations

import argparse
import hashlib
import json
import os
import zipfile
from pathlib import Path
from typing import Callable

from .ledger import Ledger
from .telegram import send_document_once


def validated_correlation(value: dict[str, object]) -> dict[str, str | None]:
    trace_id = value.get("trace_id")
    span_id = value.get("span_id")
    valid = (
        isinstance(trace_id, str)
        and len(trace_id) == 32
        and all(character in "0123456789abcdef" for character in trace_id)
        and isinstance(span_id, str)
        and len(span_id) == 16
        and all(character in "0123456789abcdef" for character in span_id)
    )
    return {
        "trace_id": trace_id if valid else None,
        "span_id": span_id if valid else None,
    }


def build_submission_evidence_archive(
    report: dict[str, object], output_root: Path
) -> Path:
    root = Path(output_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    bundle_sha256 = str(report.get("bundle_sha256") or "")
    if len(bundle_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in bundle_sha256
    ):
        raise ValueError("submission bundle hash is invalid")
    artifacts = {
        "resume.pdf": "resume",
        "pre-submit.png": "pre_submit",
        "post-action.png": "post_action",
        "terminal.png": "terminal",
        "confirmation.json": "confirmation",
    }
    contents: dict[str, bytes] = {}
    hashes: dict[str, str] = {}
    for archive_name, field in artifacts.items():
        source = Path(str(report.get(f"{field}_path") or "")).expanduser().resolve()
        claimed = str(report.get(f"{field}_sha256") or "")
        if not source.is_file():
            raise ValueError(f"{field} evidence file is missing")
        data = source.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if claimed != actual:
            raise ValueError(f"{field} evidence hash mismatch")
        contents[archive_name] = data
        hashes[archive_name] = actual
    correlation = validated_correlation(report)
    manifest = {
        "version": 1,
        "application_id": str(report.get("application_id") or ""),
        "company": str(report.get("company") or ""),
        "title": str(report.get("title") or ""),
        "canonical_url": str(report.get("canonical_url") or ""),
        "intent_id": str(report.get("intent_id") or ""),
        "fence": int(report.get("fence") or 0),
        "bundle_sha256": bundle_sha256,
        "confirmation_source": str(report.get("confirmation_source") or ""),
        "confirmation_id": str(report.get("confirmation_id") or ""),
        **correlation,
        "artifacts": hashes,
    }
    contents["manifest.json"] = (
        json.dumps(
            manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        + b"\n"
    )
    target = root / f"application-evidence-{bundle_sha256[:16]}.zip"
    temporary = root / f".{target.name}.{os.getpid()}.tmp"
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED) as bundle:
            for name in sorted(contents):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o600 << 16
                bundle.writestr(info, contents[name])
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def deliver_submitted_resumes(
    *,
    ledger_path: Path,
    outbox_path: Path,
    media_root: Path,
    sender: Callable[..., dict[str, str | None]] = send_document_once,
) -> list[dict[str, str | None]]:
    ledger = Ledger(ledger_path)
    try:
        reports = ledger.submitted_resume_reports()
    finally:
        ledger.close()

    deliveries = []
    for report in reports:
        message = (
            "📎 Resume used for submitted application\n"
            f"{report['company']} — {report['title']}\n"
            f"{report['canonical_url']}"
        )
        delivery = sender(
            database=outbox_path,
            event_key=(
                f"application-resume:{report['application_id']}:"
                f"{report['resume_sha256']}"
            ),
            message=message,
            document=Path(report["resume_path"]),
            media_root=media_root,
        )
        deliveries.append(
            {
                "application_id": report["application_id"],
                "status": delivery["status"],
                "message_id": delivery["message_id"],
            }
        )
    return deliveries


def deliver_submitted_evidence_bundles(
    *,
    ledger_path: Path,
    outbox_path: Path,
    media_root: Path,
    sender: Callable[..., dict[str, str | None]] = send_document_once,
    report_reader: Callable[[Path], list[dict[str, object]]] | None = None,
) -> list[dict[str, str | None]]:
    if report_reader is None:
        ledger = Ledger(ledger_path)
        try:
            reports = ledger.submitted_evidence_reports()
        finally:
            ledger.close()
    else:
        reports = report_reader(Path(ledger_path))
    deliveries = []
    for report in reports:
        correlation = validated_correlation(report)
        archive = build_submission_evidence_archive(report, media_root)
        trace_display = (
            f"{correlation['trace_id']}/{correlation['span_id']}"
            if correlation["trace_id"] is not None
            else "unavailable"
        )
        message = (
            "✅ Confirmed application evidence\n"
            f"{report['company']} — {report['title']}\n"
            f"{report['canonical_url']}\n"
            f"Confirmation: {report['confirmation_source']} / "
            f"{report['confirmation_id']}\n"
            f"Trace: {trace_display}"
        )
        delivery = sender(
            database=outbox_path,
            event_key=(
                f"application-evidence:{report['application_id']}:"
                f"{report['bundle_sha256']}"
            ),
            message=message,
            document=archive,
            media_root=media_root,
        )
        deliveries.append(
            {
                "application_id": str(report["application_id"]),
                "status": delivery["status"],
                "message_id": delivery["message_id"],
                **correlation,
            }
        )
    return deliveries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("deliver",))
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--outbox", type=Path, required=True)
    parser.add_argument("--media-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    evidence_deliveries = deliver_submitted_evidence_bundles(
        ledger_path=args.ledger,
        outbox_path=args.outbox,
        media_root=args.media_root,
    )
    resume_deliveries = deliver_submitted_resumes(
        ledger_path=args.ledger,
        outbox_path=args.outbox,
        media_root=args.media_root,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(
        json.dumps(
            {
                "evidence_deliveries": evidence_deliveries,
                "resume_deliveries": resume_deliveries,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    os.chmod(args.output, 0o600)


if __name__ == "__main__":
    main()
