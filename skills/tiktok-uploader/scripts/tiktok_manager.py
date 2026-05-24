"""
TikTok content manager — convenience wrapper around tiktok-uploader.

This script can be used standalone or imported by the OpenClaw skill.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from tiktok_uploader.upload import TikTokUploader

SUPPORTED_FORMATS = {
    ".mp4", ".mov", ".avi", ".wmv", ".flv",
    ".webm", ".mkv", ".m4v", ".3gp", ".3g2", ".gif",
}

Visibility = Literal["everyone", "friends", "only_you"]


# ── Auth helpers ────────────────────────────────────────────────────────

def load_cookies(path: str) -> str:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Cookie file not found: {p}")
    return str(p)


def cookies_from_sessionid(session_id: str) -> list[dict]:
    return [{"name": "sessionid", "value": session_id, "domain": ".tiktok.com", "path": "/"}]


# ── Schedule helper ─────────────────────────────────────────────────────

def make_schedule_time(dt: datetime | str) -> datetime:
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if dt < now + timedelta(minutes=20):
        raise ValueError("Schedule must be at least 20 minutes in the future")
    if dt > now + timedelta(days=10):
        raise ValueError("Schedule must be within 10 days from now")
    remainder = dt.minute % 5
    if remainder:
        dt = dt.replace(minute=dt.minute + (5 - remainder), second=0, microsecond=0)
    return dt


# ── Manager ─────────────────────────────────────────────────────────────

class TikTokManager:
    """High-level TikTok content manager."""

    def __init__(
        self,
        *,
        cookies: str | None = None,
        sessionid: str | None = None,
        cookies_list: list[dict] | None = None,
        headless: bool = True,
        {{profile.lateness.stakeholders.channel}}: str = "chrome",
        proxy: dict | None = None,
    ):
        self._kwargs: dict[str, Any] = {"headless": headless, "{{profile.lateness.stakeholders.channel}}": {{profile.lateness.stakeholders.channel}}}
        if cookies:
            self._kwargs["cookies"] = load_cookies(cookies)
        elif sessionid:
            self._kwargs["cookies_list"] = cookies_from_sessionid(sessionid)
        elif cookies_list:
            self._kwargs["cookies_list"] = cookies_list
        else:
            raise ValueError("Provide one of: cookies, sessionid, or cookies_list")
        if proxy:
            self._kwargs["proxy"] = proxy

    def upload(
        self,
        video: str,
        description: str = "",
        *,
        schedule: datetime | str | None = None,
        visibility: Visibility = "everyone",
        comment: bool = True,
        stitch: bool = True,
        duet: bool = True,
        cover: str | None = None,
        num_retries: int = 1,
    ) -> bool:
        video_path = Path(video).expanduser().resolve()
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        if video_path.suffix.lower() not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format '{video_path.suffix}'")
        sched_dt = make_schedule_time(schedule) if schedule else None
        with TikTokUploader(**self._kwargs) as uploader:
            return uploader.upload_video(
                filename=str(video_path),
                description=description,
                schedule=sched_dt,
                visibility=visibility,
                comment=comment,
                stitch=stitch,
                duet=duet,
                cover=cover,
                num_retries=num_retries,
            )

    def upload_batch(
        self,
        videos: list[dict],
        *,
        num_retries: int = 1,
        on_complete: Callable | None = None,
    ) -> list[dict]:
        prepared: list[dict] = []
        for v in videos:
            entry: dict[str, Any] = {}
            p = Path(v["path"]).expanduser().resolve()
            if not p.exists():
                raise FileNotFoundError(f"Video not found: {p}")
            entry["path"] = str(p)
            if "description" in v:
                entry["description"] = v["description"]
            if "schedule" in v and v["schedule"]:
                entry["schedule"] = make_schedule_time(v["schedule"])
            if "visibility" in v:
                entry["visibility"] = v["visibility"]
            if "cover" in v:
                entry["cover"] = v["cover"]
            prepared.append(entry)
        with TikTokUploader(**self._kwargs) as uploader:
            return uploader.upload_videos(videos=prepared, num_retries=num_retries, on_complete=on_complete)

    @staticmethod
    def scan_videos(directory: str, recursive: bool = False) -> list[dict]:
        root = Path(directory).expanduser().resolve()
        if not root.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")
        pattern = "**/*" if recursive else "*"
        results = []
        for f in sorted(root.glob(pattern)):
            if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS:
                results.append({
                    "path": str(f),
                    "name": f.name,
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    "format": f.suffix.lower(),
                })
        return results
