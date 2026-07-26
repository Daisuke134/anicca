#!/usr/bin/env python3
"""Publish one exact Life Manager creative contract to Instagram and TikTok."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone
from typing import Mapping


class DistributionError(RuntimeError):
    pass


class DistributionConfig:
    def __init__(
        self,
        *,
        creative_id: str,
        video: Path,
        caption: Path,
        ledger: Path,
        instagram_adapter: Path,
        tiktok_adapter: Path,
        instagram_handle: str,
        instagram_accounts: Path,
        tiktok_integration: str,
        approvals: Path,
        env: Mapping[str, str] | None = None,
    ):
        self.creative_id = creative_id
        self.video = Path(video)
        self.caption = Path(caption)
        self.ledger = Path(ledger)
        self.instagram_adapter = Path(instagram_adapter)
        self.tiktok_adapter = Path(tiktok_adapter)
        self.instagram_handle = instagram_handle
        self.instagram_accounts = Path(instagram_accounts)
        self.tiktok_integration = tiktok_integration
        self.approvals = Path(approvals)
        self.env = dict(env or os.environ)


def render_caption(bank: Path, creative_id: str, output: Path) -> Path:
    matches = []
    try:
        lines = Path(bank).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise DistributionError("creative bank is missing") from exc
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DistributionError("creative bank contains invalid JSON") from exc
        if isinstance(row, dict) and row.get("id") == creative_id:
            matches.append(row)
    if len(matches) != 1:
        raise DistributionError("creative id must match exactly one bank row")
    row = matches[0]
    fields = [row.get("pain"), row.get("moment"), row.get("punchline")]
    if any(not isinstance(value, str) or not value.strip() for value in fields):
        raise DistributionError("creative bank row is missing caption fields")
    caption = (
        f"{fields[0]}\n\n"
        f"{fields[1]}\n\n"
        f"{fields[2]}\n\n"
        "Life Manager が、予定に合わせて先回りします。\n"
        "aniccaai.com/life-manager\n\n"
        "#LifeManager #AIAssistant #CalendarAutomation\n"
    )
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(caption, encoding="utf-8")
    os.chmod(output, 0o600)
    return output


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate(config: DistributionConfig) -> tuple[str, str]:
    if not config.creative_id.strip():
        raise DistributionError("creative_id is required")
    for name, path in (("video", config.video), ("caption", config.caption)):
        if not path.is_file() or path.stat().st_size == 0:
            raise DistributionError(f"{name} must be a non-empty file")
    for name, path in (
        ("instagram adapter", config.instagram_adapter),
        ("tiktok adapter", config.tiktok_adapter),
    ):
        if not path.is_file():
            raise DistributionError(f"{name} is missing")
    caption_text = config.caption.read_text(encoding="utf-8").strip()
    if not caption_text:
        raise DistributionError("caption must contain text")
    return _sha256(config.video), _sha256(config.caption)


def _read_ledger(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    rows = []
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DistributionError("distribution ledger contains invalid JSON") from exc
        if not isinstance(row, dict):
            raise DistributionError("distribution ledger row must be an object")
        rows.append(row)
    return rows


def _approved(path: Path, creative_id: str, video_hash: str, caption_hash: str) -> dict | None:
    """Distribution is authorised by a receipt.

    Two shapes exist. A per-video receipt names one creative AND the digests of the exact video and
    caption that were shown for approval, so re-cutting the video or rewriting the caption silently
    invalidates it. A standing receipt (`scope: "standing"`) records the 2026-07-26 Dais ruling that
    removed the preview gate: the daily pipeline's own renders are authorised from then on without a
    per-video receipt. Anything unreadable, unparseable or unmatched is not an approval.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if row.get("scope") == "standing":
            return row
        if (
            row.get("creative_id") == creative_id
            and row.get("video_sha256") == video_hash
            and row.get("caption_sha256") == caption_hash
        ):
            return row
    return None


def _existing(rows: list[dict], platform: str, creative_id: str, video_hash: str, caption_hash: str):
    matches = [
        row
        for row in rows
        if row.get("platform") == platform
        and row.get("creative_id") == creative_id
        and row.get("video_sha256") == video_hash
        and row.get("caption_sha256") == caption_hash
        and _valid_public_url(platform, row.get("public_url"))
        and row.get("status") == "published"
    ]
    return matches[-1] if matches else None


def _valid_public_url(platform: str, value) -> bool:
    if not isinstance(value, str):
        return False
    if platform == "instagram":
        return bool(re.fullmatch(r"https://www\.instagram\.com/(?:reel|p)/[A-Za-z0-9_-]+/?", value))
    if platform == "tiktok":
        return bool(re.fullmatch(r"https://www\.tiktok\.com/@[^/]+/video/[0-9]+/?", value))
    return False


def _run_json(argv: list[str], env: Mapping[str, str]) -> dict:
    proc = subprocess.run(argv, text=True, capture_output=True, env=dict(env), timeout=900)
    if proc.returncode != 0:
        raise DistributionError(f"adapter failed with exit {proc.returncode}")
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise DistributionError("adapter returned no JSON")
    try:
        result = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise DistributionError("adapter returned invalid JSON") from exc
    if not isinstance(result, dict):
        raise DistributionError("adapter JSON must be an object")
    return result


def _append_success(
    config: DistributionConfig,
    *,
    platform: str,
    public_url: str,
    video_hash: str,
    caption_hash: str,
    provider_id: str | None,
    adapter_result: dict | None = None,
) -> dict:
    adapter_result = adapter_result or {}
    route = adapter_result.get("route")
    provider_cost = adapter_result.get("provider_cost_usd")
    logged_out = adapter_result.get("logged_out_readback")
    migration_date = adapter_result.get("migration_date")
    if route == "direct_browser" and not (
        provider_cost == 0
        and logged_out is True
        and isinstance(migration_date, str)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", migration_date)
    ):
        raise DistributionError("direct TikTok result lacks zero-cost logged-out provenance")
    row = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "platform": platform,
        "status": "published",
        "creative_id": config.creative_id,
        "video_path": str(config.video),
        "video_sha256": video_hash,
        "caption_path": str(config.caption),
        "caption_sha256": caption_hash,
        "public_url": public_url,
        "provider_id": provider_id,
        "route": route or ("instagram_file_script" if platform == "instagram" else "postiz"),
        "provider_cost_usd": provider_cost,
        "logged_out_readback": logged_out,
        "migration_date": migration_date,
    }
    config.ledger.parent.mkdir(parents=True, exist_ok=True)
    with config.ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    os.chmod(config.ledger, 0o600)
    return row


def distribute(config: DistributionConfig) -> dict:
    video_hash, caption_hash = _validate(config)
    # Fail closed BEFORE any adapter runs: without an approval for these exact bytes nothing is posted.
    approval = _approved(config.approvals, config.creative_id, video_hash, caption_hash)
    if approval is None:
        raise DistributionError(
            f"no approval receipt for creative {config.creative_id} with this exact video and caption"
        )
    rows = _read_ledger(config.ledger)

    instagram = _existing(rows, "instagram", config.creative_id, video_hash, caption_hash)
    if not instagram:
        result = _run_json(
            [
                str(config.instagram_adapter),
                "--video",
                str(config.video),
                "--caption-file",
                str(config.caption),
                "--handle",
                config.instagram_handle,
                "--accounts-path",
                str(config.instagram_accounts),
                "--live",
            ],
            config.env,
        )
        instagram_url = result.get("post_url")
        if result.get("outcome") != "published" or not _valid_public_url("instagram", instagram_url):
            raise DistributionError("Instagram did not return a published public URL")
        instagram = _append_success(
            config,
            platform="instagram",
            public_url=instagram_url,
            video_hash=video_hash,
            caption_hash=caption_hash,
            provider_id=result.get("code"),
            adapter_result=result,
        )

    rows = _read_ledger(config.ledger)
    tiktok = _existing(rows, "tiktok", config.creative_id, video_hash, caption_hash)
    if not tiktok:
        result = _run_json(
            [
                str(config.tiktok_adapter),
                "--video",
                str(config.video),
                "--caption-file",
                str(config.caption),
                "--integration",
                config.tiktok_integration,
            ],
            config.env,
        )
        tiktok_url = result.get("post_url")
        if result.get("state") != "PUBLISHED" or not _valid_public_url("tiktok", tiktok_url):
            raise DistributionError("TikTok did not return a PUBLISHED public URL")
        tiktok = _append_success(
            config,
            platform="tiktok",
            public_url=tiktok_url,
            video_hash=video_hash,
            caption_hash=caption_hash,
            provider_id=result.get("post_id"),
            adapter_result=result,
        )

    return {
        "creative_id": config.creative_id,
        "video_sha256": video_hash,
        "caption_sha256": caption_hash,
        "instagram_url": instagram["public_url"],
        "tiktok_url": tiktok["public_url"],
    }


def default_tiktok_adapter(here: Path, env: Mapping[str, str]) -> Path:
    if env.get("LM_TIKTOK_DIRECT_MIGRATION") == "1":
        return Path(here) / "tiktok_direct.mjs"
    return Path(here) / "postiz_video.py"


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--creative-id", required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--caption-file", type=Path)
    parser.add_argument(
        "--bank",
        type=Path,
        default=here.parent / "daily-lm-video" / "creative-bank.jsonl",
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path(os.environ.get("LM_DISTRIBUTION_LEDGER", "~/.openclaw/state/lm-video/distribution.jsonl")).expanduser(),
    )
    parser.add_argument(
        "--instagram-adapter",
        type=Path,
        default=here / "instagram_video.sh",
    )
    parser.add_argument(
        "--tiktok-adapter",
        type=Path,
        default=default_tiktok_adapter(here, os.environ),
    )
    parser.add_argument("--instagram-handle", default=os.environ.get("LM_INSTAGRAM_HANDLE", "anicca.affirms2"))
    parser.add_argument(
        "--instagram-accounts",
        type=Path,
        default=Path(
            os.environ.get(
                "LM_INSTAGRAM_ACCOUNTS",
                "~/.cloak/life-manager-instagram-accounts.json",
            )
        ).expanduser(),
    )
    parser.add_argument(
        "--approvals",
        type=Path,
        default=Path(
            os.environ.get(
                "LM_DISTRIBUTION_APPROVALS",
                "~/.openclaw/state/lm-video/distribution-approvals.jsonl",
            )
        ).expanduser(),
    )
    parser.add_argument(
        "--tiktok-integration",
        default=os.environ.get("LM_TIKTOK_INTEGRATION", "cmp9txjdp01c8oh0yb6dhlarr"),
    )
    args = parser.parse_args()

    caption = args.caption_file
    if caption is None:
        caption = Path("~/.openclaw/state/lm-video/captions").expanduser() / f"{args.creative_id}.txt"
        render_caption(args.bank, args.creative_id, caption)
    result = distribute(
        DistributionConfig(
            creative_id=args.creative_id,
            video=args.video,
            caption=caption,
            ledger=args.ledger,
            instagram_adapter=args.instagram_adapter,
            tiktok_adapter=args.tiktok_adapter,
            instagram_handle=args.instagram_handle,
            instagram_accounts=args.instagram_accounts,
            tiktok_integration=args.tiktok_integration,
            approvals=args.approvals,
        )
    )
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DistributionError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, separators=(",", ":")))
        raise SystemExit(1)
