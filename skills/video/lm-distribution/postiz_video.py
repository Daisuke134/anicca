#!/usr/bin/env python3
"""Post one existing MP4 to TikTok or YouTube through Postiz."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


BASE_URL = "https://api.postiz.com/public/v1"
PUBLIC_POST_DETAILS_URL = "https://api.postiz.com/public/posts"


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
    platform: str = "tiktok",
) -> dict:
    if platform == "youtube":
        settings = {
            "__type": "youtube",
            "title": title,
            "type": "public",
            "selfDeclaredMadeForKids": "no",
            "thumbnail": None,
            "tags": [],
        }
    elif platform == "instagram":
        settings = {
            "__type": "instagram-standalone",
            "post_type": "post",
            "is_trial_reel": False,
            "collaborators": [],
        }
    elif platform == "tiktok":
        settings = {
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
        }
    else:
        raise PostizError("Postiz platform is invalid")
    return {
        "type": "now",
        "date": now_iso,
        "shortLink": False,
        "tags": [],
        "posts": [
            {
                "integration": {"id": integration},
                "value": [{"content": caption, "image": [{"id": upload_id, "path": upload_path}]}],
                "settings": settings,
            }
        ],
    }


def extract_post_id(response) -> str:
    if isinstance(response, list) and response and isinstance(response[0], dict):
        post_id = response[0].get("postId")
        if isinstance(post_id, str) and post_id:
            return post_id
    raise PostizError("Postiz create response did not contain postId")


def _valid_public_url(platform: str, value: str | None) -> bool:
    if platform == "instagram":
        return bool(re.fullmatch(r"https://www\.instagram\.com/(?:reel|p)/[A-Za-z0-9_-]+/?", value or ""))
    if platform == "tiktok":
        return bool(re.fullmatch(r"https://www\.tiktok\.com/@[^/]+/video/[0-9]+/?", value or ""))
    if platform == "youtube":
        return bool(re.fullmatch(
            r"https://www\.youtube\.com/(?:shorts/[A-Za-z0-9_-]+|watch\?v=[A-Za-z0-9_-]+(?:&[^#]+)?)/?",
            value or "",
        ))
    return False


def find_post(response, post_id: str, platform: str = "tiktok") -> dict:
    posts = response.get("posts", []) if isinstance(response, dict) else response
    if not isinstance(posts, list):
        raise PostizError("Postiz list response has no posts array")
    match = next((row for row in posts if isinstance(row, dict) and row.get("id") == post_id), None)
    if not match:
        return {"state": "UNKNOWN", "post_url": None}
    state = match.get("state") or "UNKNOWN"
    url = match.get("releaseURL") or match.get("releaseUrl")
    # Postiz's TikTok ``releaseId`` is an internal publication identifier, not
    # the native TikTok video id.  It can look numeric and still resolve to a
    # different public video (the provider profile is the authority).  Keep a
    # profile URL here so the caller must perform a public profile/caption/time
    # readback before it can record a direct artifact URL.
    if state == "PUBLISHED" and platform == "youtube" and not _valid_public_url(platform, url):
        # Postiz may expose a channel URL while the provider row carries the
        # authoritative YouTube video id. Construct only from that exact id;
        # the caller still requires a direct URL before recording a receipt.
        release_id = str(match.get("releaseId") or "")
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", release_id):
            url = f"https://www.youtube.com/watch?v={release_id}"
    if state == "PUBLISHED" and (not isinstance(url, str) or not url.startswith("https://")):
        raise PostizError("Postiz marked PUBLISHED without a public release URL")
    return {"state": state, "post_url": url if isinstance(url, str) else None}


def find_existing_post(
    response,
    *,
    integration: str,
    caption: str,
    video_sha256: str,
    platform: str = "tiktok",
) -> dict | None:
    posts = response.get("posts", []) if isinstance(response, dict) else response
    if not isinstance(posts, list):
        raise PostizError("Postiz list response has no posts array")
    for row in reversed(posts):
        if not isinstance(row, dict):
            continue
        row_integration = row.get("integration")
        integration_id = (
            row_integration.get("id") if isinstance(row_integration, dict) else row.get("integrationId")
        )
        # Caption equality cannot identify a publication effect: scheduled lanes
        # legitimately reuse copy for different video bytes. Postiz's normal list
        # response does not carry this Life Manager digest, so it fails closed and
        # the exact creative/video/caption local ledger remains the only reuse path.
        if (
            integration_id != integration
            or _normalized(str(row.get("content") or "")) != _normalized(caption)
            or row.get("lifeManagerVideoSha256") != video_sha256
        ):
            continue
        post_id = row.get("id")
        if not isinstance(post_id, str) or not post_id:
            continue
        state = find_post([row], post_id, platform)
        if state["state"] != "PUBLISHED":
            continue
        if _valid_public_url(platform, state.get("post_url")):
            return {"post_id": post_id, **state, "reconciled": True}
        if platform == "tiktok":
            published_at = row.get("publishDate") or row.get("date")
            try:
                posted_after = int(datetime.fromisoformat(
                    str(published_at).replace("Z", "+00:00"),
                ).timestamp())
            except (TypeError, ValueError, OverflowError):
                posted_after = int(time.time()) - 7200
            resolved = resolve_profile_release_url(
                str(state.get("post_url") or ""),
                caption,
                posted_after=posted_after,
            )
            if resolved:
                return {
                    "post_id": post_id,
                    "state": "PUBLISHED",
                    "post_url": resolved,
                    "reconciled": True,
                }
    return None


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _matching_profile_url(rows, caption_prefix: str, posted_after: int) -> str | None:
    candidates = []
    for row in rows if isinstance(rows, list) else []:
        url = row.get("href") if isinstance(row, dict) else None
        alt = row.get("alt") if isinstance(row, dict) else ""
        match = re.fullmatch(r"https://www\.tiktok\.com/@[^/]+/video/([0-9]+)/?", url or "")
        if (
            match
            and caption_prefix
            and caption_prefix in _normalized(str(alt))
            and (int(match.group(1)) >> 32) >= posted_after - 5
        ):
            candidates.append((int(match.group(1)), url))
    return max(candidates)[1] if candidates else None


def resolve_profile_release_url(
    profile_url: str,
    caption: str,
    *,
    posted_after: int,
    runner=subprocess.run,
    browser_resolver=None,
) -> str | None:
    if not re.fullmatch(r"https://www\.tiktok\.com/@[^/]+/?", profile_url):
        return None
    caption_prefix = _normalized(caption)[:24].strip()
    try:
        proc = runner(
            [
                "yt-dlp",
                "--flat-playlist",
                "--playlist-end",
                "12",
                "--dump-single-json",
                profile_url,
            ],
            text=True,
            capture_output=True,
            timeout=60,
        )
    except OSError:
        proc = None
    if proc is not None and proc.returncode == 0:
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            data = None
        entries = data.get("entries", []) if isinstance(data, dict) else []
        candidates = []
        for row in entries:
            if not isinstance(row, dict):
                continue
            url = row.get("url")
            title = row.get("title") or row.get("description") or ""
            timestamp = row.get("timestamp")
            if (
                isinstance(url, str)
                and re.fullmatch(r"https://www\.tiktok\.com/@[^/]+/video/[0-9]+/?", url)
                and isinstance(timestamp, (int, float))
                and timestamp >= posted_after - 5
                and _normalized(str(title)).startswith(caption_prefix)
            ):
                candidates.append((timestamp, url))
        if candidates:
            return max(candidates)[1]
    resolver = browser_resolver or _resolve_profile_release_url_browser
    return resolver(profile_url, caption, posted_after=posted_after, caption_prefix=caption_prefix)


def _resolve_profile_release_url_browser(
    profile_url: str,
    caption: str,
    *,
    posted_after: int,
    caption_prefix: str | None = None,
) -> str | None:
    """Read the newest profile DOM when yt-dlp cannot read TikTok's JS page."""
    del caption
    try:
        import websockets
    except ImportError:
        return None
    prefix = caption_prefix or ""

    async def read_profile():
        host = os.environ.get("CDP_HOST", "127.0.0.1")
        port = os.environ.get("CDP_PORT", "9222")
        version = json.loads(urllib.request.urlopen(
            f"http://{host}:{port}/json/version", timeout=8,
        ).read())
        websocket_url = version["webSocketDebuggerUrl"]
        async with websockets.connect(
            websocket_url, open_timeout=10, ping_interval=None, max_size=64 * 1024 * 1024,
        ) as socket:
            sequence = 0

            async def call(method, params=None, session_id=None):
                nonlocal sequence
                sequence += 1
                request = {"id": sequence, "method": method, "params": params or {}}
                if session_id:
                    request["sessionId"] = session_id
                await socket.send(json.dumps(request))
                while True:
                    response = json.loads(await asyncio.wait_for(socket.recv(), timeout=15))
                    if response.get("id") == sequence:
                        if response.get("error"):
                            raise RuntimeError("TikTok profile CDP read failed")
                        return response.get("result", {})

            target_id = (await call("Target.createTarget", {"url": profile_url}))["targetId"]
            try:
                session_id = (await call(
                    "Target.attachToTarget", {"targetId": target_id, "flatten": True},
                ))["sessionId"]
                await asyncio.sleep(8)
                expression = "JSON.stringify([...document.querySelectorAll('a[href*=\"/video/\"]')].slice(0,20).map(e=>({href:e.href,alt:e.querySelector('img')?.alt||''})))"
                result = await call(
                    "Runtime.evaluate", {"expression": expression, "returnByValue": True}, session_id,
                )
                value = result.get("result", {}).get("value")
                return _matching_profile_url(json.loads(value), prefix, posted_after) if isinstance(value, str) else None
            finally:
                await call("Target.closeTarget", {"targetId": target_id})

    try:
        return asyncio.run(read_profile())
    except Exception:
        return None


def _request_json(request: urllib.request.Request, timeout: int = 90):
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        status = getattr(exc, "code", None)
        suffix = f" HTTP {status}" if status else ""
        raise PostizError(f"Postiz request failed{suffix}") from exc


def read_post_error(post_id: str, api_key: str) -> str | None:
    """Read the provider-owned terminal reason without exposing credentials.

    The public v1 list intentionally omits Postiz's ``error`` column.  The
    public preview endpoint still returns that field for one post, so only
    terminal ERROR states make this extra read.  A missing detail is kept as
    unknown rather than being converted into success or zero.
    """
    request = urllib.request.Request(
        f"{PUBLIC_POST_DETAILS_URL}/{urllib.parse.quote(post_id, safe='')}",
        headers={"Authorization": api_key},
    )
    try:
        response = _request_json(request)
    except PostizError:
        return None
    rows = response if isinstance(response, list) else []
    row = rows[0] if rows and isinstance(rows[0], dict) else None
    reason = row.get("error") if row else None
    return reason.strip() if isinstance(reason, str) and reason.strip() else None


def upload_video(video: Path, api_key: str) -> tuple[str, str]:
    boundary = "----life-manager-" + uuid.uuid4().hex
    filename = video.name.replace('"', "")
    if not Path(filename).suffix:
        filename = f"{filename}.mp4"
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


def read_publish_state(post_id: str, api_key: str, platform: str = "tiktok") -> dict:
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
    state = find_post(_request_json(request), post_id, platform)
    if state.get("state") == "ERROR":
        reason = read_post_error(post_id, api_key)
        if reason:
            state["error"] = reason
    return state


def read_recent_posts(api_key: str, hours: int = 6):
    now = datetime.now(timezone.utc)
    query = urllib.parse.urlencode(
        {
            "startDate": (now - timedelta(hours=hours)).isoformat().replace("+00:00", "Z"),
            "endDate": (now + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            "limit": "100",
        }
    )
    request = urllib.request.Request(
        f"{BASE_URL}/posts?{query}",
        headers={"Authorization": api_key},
    )
    return _request_json(request)


def is_reconciled_state(state: dict, platform: str = "tiktok") -> bool:
    return (
        isinstance(state, dict)
        and state.get("state") == "PUBLISHED"
        and _valid_public_url(platform, state.get("post_url"))
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--caption-file", type=Path, required=True)
    parser.add_argument("--integration", required=True)
    parser.add_argument("--title", default="Life Manager")
    parser.add_argument("--platform", choices=("instagram", "tiktok", "youtube"), default="tiktok")
    args = parser.parse_args()

    api_key = os.environ.get("POSTIZ_API_KEY", "")
    if not api_key:
        raise PostizError("POSTIZ_API_KEY is unavailable")
    if not args.video.is_file() or args.video.stat().st_size == 0:
        raise PostizError("video is missing or empty")
    caption = args.caption_file.read_text(encoding="utf-8").strip()
    if not caption:
        raise PostizError("caption is empty")

    title = args.title
    if args.platform == "youtube" and title == "Life Manager":
        title = next((line.strip() for line in caption.splitlines() if line.strip()), title)
    title = title[:100]
    if len(title) < 2:
        raise PostizError("Postiz title is too short")

    existing = find_existing_post(
        read_recent_posts(api_key),
        integration=args.integration,
        caption=caption,
        video_sha256=hashlib.sha256(args.video.read_bytes()).hexdigest(),
        platform=args.platform,
    )
    if existing:
        print(json.dumps(existing, ensure_ascii=False, separators=(",", ":")))
        return 0

    posted_after = int(time.time())
    upload_id, upload_path = upload_video(args.video, api_key)
    payload = build_payload(
        integration=args.integration,
        caption=caption,
        title=title,
        upload_id=upload_id,
        upload_path=upload_path,
        now_iso=datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        platform=args.platform,
    )
    post_id = create_post(payload, api_key)
    state = {"state": "QUEUE", "post_url": None}
    for _ in range(18):
        time.sleep(10)
        state = read_publish_state(post_id, api_key, args.platform)
        if state["state"] == "PUBLISHED" and state["post_url"]:
            if _valid_public_url(args.platform, state["post_url"]):
                break
            if args.platform == "tiktok":
                resolved = resolve_profile_release_url(
                    state["post_url"],
                    caption,
                    posted_after=posted_after,
                )
                if resolved:
                    state["post_url"] = resolved
                    break
        if state["state"] == "ERROR":
            break
    # Postiz's PUBLISHED state plus an exact /video/<id> URL is the provider
    # readback required by Life Manager; preserve that provenance in the
    # publication receipt instead of silently downgrading it to false.
    result = {
        "post_id": post_id,
        **state,
        "reconciled": is_reconciled_state(state, args.platform),
    }
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    if state["state"] != "PUBLISHED" or not _valid_public_url(args.platform, state.get("post_url")):
        reason = state.get("error")
        suffix = f": {reason}" if isinstance(reason, str) and reason else ""
        raise PostizError(f"Postiz terminal state is {state['state']}{suffix}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PostizError as exc:
        print(json.dumps({"state": "ERROR", "error": str(exc)}, separators=(",", ":")))
        raise SystemExit(1)
