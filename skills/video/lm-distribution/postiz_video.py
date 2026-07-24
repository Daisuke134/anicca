#!/usr/bin/env python3
"""Post one existing MP4 to TikTok through the existing Postiz integration."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import mimetypes
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


BASE_URL = "https://api.postiz.com/public/v1"


class PostizError(RuntimeError):
    pass


def build_payload(
    *,
    integration: str,
    caption: str,
    title: str,
    upload_id: str,
    upload_path: str,
    now_iso: str,
) -> dict:
    return {
        "type": "now",
        "date": now_iso,
        "shortLink": False,
        "tags": [],
        "posts": [
            {
                "integration": {"id": integration},
                "value": [{"content": caption, "image": [{"id": upload_id, "path": upload_path}]}],
                "settings": {
                    "__type": "tiktok",
                    "title": title,
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "duet": False,
                    "stitch": False,
                    "comment": True,
                    "autoAddMusic": "yes",
                    "brand_content_toggle": False,
                    "brand_organic_toggle": False,
                    "video_made_with_ai": True,
                    "content_posting_method": "DIRECT_POST",
                },
            }
        ],
    }


def extract_post_id(response) -> str:
    if isinstance(response, list) and response and isinstance(response[0], dict):
        post_id = response[0].get("postId")
        if isinstance(post_id, str) and post_id:
            return post_id
    raise PostizError("Postiz create response did not contain postId")


def find_post(response, post_id: str) -> dict:
    posts = response.get("posts", []) if isinstance(response, dict) else response
    if not isinstance(posts, list):
        raise PostizError("Postiz list response has no posts array")
    match = next((row for row in posts if isinstance(row, dict) and row.get("id") == post_id), None)
    if not match:
        return {"state": "UNKNOWN", "post_url": None}
    state = match.get("state") or "UNKNOWN"
    url = match.get("releaseURL") or match.get("releaseUrl")
    if state == "PUBLISHED" and (not isinstance(url, str) or not url.startswith("https://")):
        raise PostizError("Postiz marked PUBLISHED without a public release URL")
    return {"state": state, "post_url": url if isinstance(url, str) else None}


def _request_json(request: urllib.request.Request, timeout: int = 90):
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        status = getattr(exc, "code", None)
        suffix = f" HTTP {status}" if status else ""
        raise PostizError(f"Postiz request failed{suffix}") from exc


def upload_video(video: Path, api_key: str) -> tuple[str, str]:
    boundary = "----life-manager-" + uuid.uuid4().hex
    filename = video.name.replace('"', "")
    mime = mimetypes.guess_type(filename)[0] or "video/mp4"
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode()
    body = head + video.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    request = urllib.request.Request(
        f"{BASE_URL}/upload",
        data=body,
        method="POST",
        headers={
            "Authorization": api_key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    response = _request_json(request)
    upload_id = response.get("id") if isinstance(response, dict) else None
    upload_path = response.get("path") if isinstance(response, dict) else None
    if not isinstance(upload_id, str) or not upload_id or not isinstance(upload_path, str) or not upload_path:
        raise PostizError("Postiz upload response is missing id/path")
    return upload_id, upload_path


def create_post(payload: dict, api_key: str) -> str:
    request = urllib.request.Request(
        f"{BASE_URL}/posts",
        data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={"Authorization": api_key, "Content-Type": "application/json"},
    )
    return extract_post_id(_request_json(request))


def read_publish_state(post_id: str, api_key: str) -> dict:
    now = datetime.now(timezone.utc)
    query = urllib.parse.urlencode(
        {
            "startDate": (now - timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
            "endDate": (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
            "limit": "100",
        }
    )
    request = urllib.request.Request(
        f"{BASE_URL}/posts?{query}",
        headers={"Authorization": api_key},
    )
    return find_post(_request_json(request), post_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--caption-file", type=Path, required=True)
    parser.add_argument("--integration", required=True)
    parser.add_argument("--title", default="Life Manager")
    args = parser.parse_args()

    api_key = os.environ.get("POSTIZ_API_KEY", "")
    if not api_key:
        raise PostizError("POSTIZ_API_KEY is unavailable")
    if not args.video.is_file() or args.video.stat().st_size == 0:
        raise PostizError("video is missing or empty")
    caption = args.caption_file.read_text(encoding="utf-8").strip()
    if not caption:
        raise PostizError("caption is empty")

    upload_id, upload_path = upload_video(args.video, api_key)
    payload = build_payload(
        integration=args.integration,
        caption=caption,
        title=args.title,
        upload_id=upload_id,
        upload_path=upload_path,
        now_iso=datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
    )
    post_id = create_post(payload, api_key)
    state = {"state": "QUEUE", "post_url": None}
    for _ in range(18):
        time.sleep(10)
        state = read_publish_state(post_id, api_key)
        if state["state"] in {"PUBLISHED", "ERROR"}:
            break
    result = {"post_id": post_id, **state}
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    if state["state"] != "PUBLISHED":
        raise PostizError(f"Postiz terminal state is {state['state']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PostizError as exc:
        print(json.dumps({"state": "ERROR", "error": str(exc)}, separators=(",", ":")))
        raise SystemExit(1)
