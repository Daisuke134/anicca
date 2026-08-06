from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

from .telegram import send_daily_report


LABELS = (
    ("confirmed_application_rate", "応募確認"),
    ("recruiter_reply_rate", "採用担当返信"),
    ("interview_rate", "面接"),
    ("final_round_rate", "最終面接"),
    ("offer_rate", "オファー"),
    ("acceptance_rate", "承諾"),
)
MATERIAL_BROWSER_FIELDS = (
    "status",
    "attempted_count",
    "verified_link_count",
    "remaining_unverified_count",
    "submitted",
    "submit_unknown",
    "blocked",
)


def _validate(value: dict[str, Any]) -> None:
    claimed = value.get("projection_sha256")
    unsigned = {key: item for key, item in value.items() if key != "projection_sha256"}
    actual = hashlib.sha256(json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    if claimed != actual:
        raise ValueError("summary projection SHA-256 mismatch")
    if value.get("version") != 2 or not isinstance(value.get("day"), str):
        raise ValueError("summary.v2 contract is invalid")
    funnel = value.get("funnel")
    if not isinstance(funnel, dict):
        raise ValueError("summary.v2 funnel is invalid")
    for key, _ in LABELS:
        metric = funnel.get(key)
        if not isinstance(metric, dict) or set(metric) != {
            "numerator", "denominator", "rate"
        }:
            raise ValueError("summary.v2 metric is invalid")


def _metric(label: str, value: dict[str, Any]) -> str:
    numerator = value["numerator"]
    denominator = value["denominator"]
    rate = value["rate"]
    suffix = "母数なし" if rate is None else f"{rate * 100:.1f}%"
    return f"{label}: {numerator}/{denominator} ({suffix})"


def render_pipeline(value: dict[str, Any]) -> str:
    _validate(value)
    lines = [f"📊 Job Hunter 日次進捗 — {value['day']}", ""]
    lines.extend(_metric(label, value["funnel"][key]) for key, label in LABELS)
    owners = value.get("owners", {})
    lines.extend((
        "",
        f"応募owner: Agent {owners.get('agent', 0)} / "
        f"Dais手動 {owners.get('dais_manual', 0)} / "
        f"Recruiter {owners.get('recruiter', 0)}",
        f"Ashby・Workdayの確認済み応募: "
        f"{len(value['ats_progress']['confirmed_adapters'])}/"
        f"{len(value['ats_progress']['required_adapters'])}",
        "",
        "次の重点: 応募確認証拠を増やし、面接conversionを計測可能にする。",
    ))
    return "\n".join(lines)


def _material_digest(
    summary: dict[str, Any], release_manifest_path: Path, browser_result_path: Path
) -> str:
    try:
        release = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("daily material evidence is unavailable") from error
    if browser_result_path.is_file():
        try:
            browser = json.loads(browser_result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("browser material evidence is invalid") from error
    else:
        browser = {"status": "not_started"}
    if not isinstance(release, dict) or not isinstance(release.get("commit"), str):
        raise ValueError("release material evidence is invalid")
    if not isinstance(browser, dict):
        raise ValueError("browser material evidence is invalid")
    material = {
        "projection_sha256": summary["projection_sha256"],
        "release_commit": release["commit"],
        "browser": {key: browser.get(key) for key in MATERIAL_BROWSER_FIELDS},
    }
    return hashlib.sha256(
        json.dumps(
            material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def deliver_pipeline_report(
    *, summary_path: Path, outbox_path: Path,
    release_manifest_path: Path | None = None,
    browser_result_path: Path | None = None,
    sender: Callable[..., dict[str, str | None]] = send_daily_report,
) -> dict[str, str | None]:
    try:
        value = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("private summary.v2 is unavailable") from error
    if not isinstance(value, dict):
        raise ValueError("summary.v2 must be an object")
    message = render_pipeline(value)
    sender_arguments: dict[str, Any] = {
        "database": Path(outbox_path),
        "japan_day": str(value["day"]),
    }
    if release_manifest_path is not None or browser_result_path is not None:
        if release_manifest_path is None or browser_result_path is None:
            raise ValueError("both daily material evidence paths are required")
        digest = _material_digest(value, release_manifest_path, browser_result_path)
        sender_arguments["material_digest"] = digest
        message = f"{message}\n実行証拠: {digest[:12]}"
    sender_arguments["message"] = message
    return sender(**sender_arguments)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("deliver",))
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--outbox", type=Path, required=True)
    parser.add_argument("--release-manifest", type=Path)
    parser.add_argument("--browser-result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = deliver_pipeline_report(
        summary_path=args.summary,
        outbox_path=args.outbox,
        release_manifest_path=args.release_manifest,
        browser_result_path=args.browser_result,
    )
    args.output.write_text(json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
