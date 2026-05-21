"""
Postiz API Wrapper
SNS投稿を統一的に管理（Blotato から 2026-05-07 に移行）

旧 BlotatoClient と同じ関数シグネチャを保つ（既存呼び出し側を変更しない）。
内部では Postiz API (https://api.postiz.com/public/v1) を叩く。

Integration ID source of truth:
  ~/.openclaw/state/postiz-integrations.json
  → handle-based lookup（platform + handle で integration ID を解決）

Account key → Postiz handle mapping は config.py の ACCOUNTS["postiz_handle"] を参照する。
"""
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests

from config import (
    POSTIZ_API_KEY,
    POSTIZ_BASE_URL,
    ACCOUNTS,
    DEFAULT_LINK,
    POSTIZ_INTEGRATIONS_PATH,
    MIGRATION_DRY_RUN,
)


def _load_integrations() -> List[Dict[str, Any]]:
    """Load Postiz integration index from ~/.openclaw/state/postiz-integrations.json."""
    path = Path(os.path.expanduser(str(POSTIZ_INTEGRATIONS_PATH)))
    if not path.exists():
        raise FileNotFoundError(
            f"Postiz integration index missing: {path}. "
            "This file is the source of truth for integration IDs."
        )
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("integrations", [])


def resolve_integration_id(platform: str, handle: str) -> str:
    """Resolve a Postiz integration ID by platform + handle.

    Args:
        platform: "x" | "tiktok" | "instagram" | "youtube" | "threads" | "pinterest"
        handle:   e.g. "@aniccaxxx", "@anicca.monk", "anicca-en-card-1"

    Raises ValueError if no active integration matches.
    """
    integrations = _load_integrations()
    for it in integrations:
        if (
            it.get("platform") == platform
            and it.get("handle") == handle
            and it.get("active", True)
        ):
            return it["id"]
    raise ValueError(
        f"No active Postiz integration for platform={platform!r}, handle={handle!r}. "
        f"Add it to ~/.openclaw/state/postiz-integrations.json or check the handle."
    )


def _account_to_integration_id(account_key: str) -> str:
    """Resolve a legacy ACCOUNTS key (e.g. 'x_aniccaxxx') to a Postiz integration ID.

    Bug fix (2026-05-07): the old blotato.py defaulted unknown keys to ACCOUNTS["x_xg2grb"],
    which was never present in ACCOUNTS — masking key typos with KeyError. This rewrite
    raises ValueError with the unknown key, so typos surface immediately.
    """
    account = ACCOUNTS.get(account_key)
    if not account:
        raise ValueError(
            f"Unknown account key: {account_key!r}. "
            f"Known keys: {sorted(ACCOUNTS.keys())}"
        )
    handle = account.get("postiz_handle")
    platform = _platform_for_postiz(account.get("platform", ""))
    if not handle:
        raise ValueError(
            f"ACCOUNTS[{account_key!r}] is missing 'postiz_handle'. "
            f"Add it to config.py — required after Blotato → Postiz migration."
        )
    return resolve_integration_id(platform, handle)


def _platform_for_postiz(legacy_platform: str) -> str:
    """Map old Blotato platform string to Postiz platform key."""
    return {"twitter": "x"}.get(legacy_platform, legacy_platform)


def _platform_settings(platform: str, **kwargs) -> Dict[str, Any]:
    """Per-platform Postiz `settings` block, mirroring the runtime skill conventions."""
    if platform == "x":
        return {"__type": "x", "who_can_reply_post": "everyone"}
    if platform == "instagram":
        return {
            "__type": "instagram-standalone",
            "post_type": kwargs.get("media_type", "reel"),
        }
    if platform == "tiktok":
        return {
            "__type": "tiktok",
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "content_posting_method": "DIRECT_POST",
            "video_made_with_ai": kwargs.get("is_ai_generated", False),
            "autoAddMusic": "no",
            "duet": False,
            "stitch": False,
            "comment": False,
            "brand_content_toggle": False,
            "brand_organic_toggle": False,
        }
    if platform == "youtube":
        return {
            "__type": "youtube",
            "title": kwargs.get("title", ""),
            "selfDeclaredMadeForKids": "yes" if kwargs.get("made_for_kids") else "no",
            "privacy": kwargs.get("privacy_status", "public"),
        }
    if platform == "threads":
        return {"__type": "threads"}
    if platform == "pinterest":
        return {
            "__type": "pinterest",
            "title": kwargs.get("title", ""),
            "boardId": kwargs.get("board_id"),
            "link": kwargs.get("link", DEFAULT_LINK),
        }
    return {"__type": platform}


class PostizClient:
    """Postiz API client. Drop-in replacement for the old BlotatoClient."""

    def __init__(self, api_key: str = POSTIZ_API_KEY):
        self.api_key = api_key
        self.base_url = POSTIZ_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        if MIGRATION_DRY_RUN:
            body = kwargs.get("json")
            print(f"[DRY_RUN] {method} {url}")
            print(f"[DRY_RUN] headers: Authorization=Bearer ***, Content-Type=application/json")
            if body is not None:
                print(f"[DRY_RUN] body: {json.dumps(body, ensure_ascii=False, indent=2)}")
            curl = (
                f"curl -X {method} '{url}' "
                f"-H 'Authorization: Bearer ${{POSTIZ_API_KEY}}' "
                f"-H 'Content-Type: application/json' "
                f"-d '{json.dumps(body, ensure_ascii=False) if body is not None else ''}'"
            )
            print(f"[DRY_RUN] curl: {curl}")
            return {"dry_run": True, "url": url, "method": method, "body": body}
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}

    def _build_post(
        self,
        integration_id: str,
        platform: str,
        text: str,
        media_urls: Optional[List[str]] = None,
        scheduled_time: Optional[str] = None,
        **settings_kwargs,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "type": "schedule" if scheduled_time else "now",
            "shortLink": False,
            "tags": [],
            "posts": [
                {
                    "integration": {"id": integration_id},
                    "value": [
                        {
                            "content": text,
                            **({"image": [{"url": u} for u in media_urls]} if media_urls else {}),
                        }
                    ],
                    "settings": _platform_settings(platform, **settings_kwargs),
                }
            ],
        }
        if scheduled_time:
            body["date"] = scheduled_time
        return body

    # =========================================================================
    # User & Account Management — Postiz exposes /integrations/list
    # =========================================================================
    def get_user(self) -> Dict[str, Any]:
        """Get the integration index — Postiz analogue of Blotato's GET /users/me."""
        return self._request("GET", "/integrations/list")

    def list_accounts(self) -> Dict[str, Any]:
        """List integrations (Postiz analogue of Blotato's GET /users/me/accounts)."""
        return self._request("GET", "/integrations/list")

    # =========================================================================
    # Media Upload — Postiz lets you pass an external URL inline; explicit upload
    # is only needed for binary uploads. Keep the signature for back-compat.
    # =========================================================================
    def upload_media(self, url: str) -> Dict[str, Any]:
        return {"url": url, "note": "Postiz accepts external URLs inline; no upload step required."}

    # =========================================================================
    # Post Creation — X (Twitter)
    # =========================================================================
    def post_to_x(
        self,
        text: str,
        media_urls: Optional[List[str]] = None,
        scheduled_time: Optional[str] = None,
        account: str = "x_aniccaxxx",
    ) -> Dict[str, Any]:
        integration_id = _account_to_integration_id(account)
        body = self._build_post(integration_id, "x", text, media_urls, scheduled_time)
        return self._request("POST", "/posts", json=body)

    def post_to_instagram(
        self,
        text: str,
        media_urls: List[str],
        media_type: str = "reel",
        scheduled_time: Optional[str] = None,
        account: str = "ig_anicca_ai",
    ) -> Dict[str, Any]:
        if not media_urls:
            raise ValueError("Instagram requires at least one media URL")
        integration_id = _account_to_integration_id(account)
        body = self._build_post(
            integration_id, "instagram", text, media_urls, scheduled_time,
            media_type=media_type,
        )
        return self._request("POST", "/posts", json=body)

    def post_to_tiktok(
        self,
        text: str,
        media_urls: List[str],
        is_ai_generated: bool = True,
        scheduled_time: Optional[str] = None,
        account: str = "tt_anicca_ai",
    ) -> Dict[str, Any]:
        if not media_urls:
            raise ValueError("TikTok requires at least one media URL")
        integration_id = _account_to_integration_id(account)
        body = self._build_post(
            integration_id, "tiktok", text, media_urls, scheduled_time,
            is_ai_generated=is_ai_generated,
        )
        return self._request("POST", "/posts", json=body)

    def post_to_youtube(
        self,
        description: str,
        media_urls: List[str],
        title: str,
        privacy_status: str = "public",
        notify_subscribers: bool = True,
        made_for_kids: bool = False,
        scheduled_time: Optional[str] = None,
        account: str = "youtube_en",
    ) -> Dict[str, Any]:
        if not media_urls:
            raise ValueError("YouTube requires at least one video URL")
        integration_id = _account_to_integration_id(account)
        body = self._build_post(
            integration_id, "youtube", description, media_urls, scheduled_time,
            title=title,
            privacy_status=privacy_status,
            made_for_kids=made_for_kids,
        )
        return self._request("POST", "/posts", json=body)

    def post_to_threads(
        self,
        text: str,
        media_urls: Optional[List[str]] = None,
        scheduled_time: Optional[str] = None,
        account: str = "threads_japan",
    ) -> Dict[str, Any]:
        integration_id = _account_to_integration_id(account)
        body = self._build_post(integration_id, "threads", text, media_urls, scheduled_time)
        return self._request("POST", "/posts", json=body)

    def post_to_pinterest(
        self,
        description: str,
        media_urls: List[str],
        title: str,
        board_id: Optional[str] = None,
        link: str = DEFAULT_LINK,
        scheduled_time: Optional[str] = None,
        account: str = "pinterest",
    ) -> Dict[str, Any]:
        if not media_urls:
            raise ValueError("Pinterest requires at least one media URL")
        if not board_id:
            board_id = ACCOUNTS.get(account, {}).get("board_id")
        if not board_id:
            raise ValueError("Pinterest requires a board_id")
        integration_id = _account_to_integration_id(account)
        body = self._build_post(
            integration_id, "pinterest", description, media_urls, scheduled_time,
            title=title, board_id=board_id, link=link,
        )
        return self._request("POST", "/posts", json=body)

    # =========================================================================
    # Generic post (by account key) — Postiz analogue of old Blotato `post()`.
    # =========================================================================
    def post(
        self,
        account_key: str,
        text: str,
        media_urls: Optional[List[str]] = None,
        scheduled_time: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        account = ACCOUNTS.get(account_key)
        if not account:
            raise ValueError(f"Unknown account: {account_key}")
        platform = account["platform"]
        if platform == "twitter":
            return self.post_to_x(text, media_urls, scheduled_time, account_key)
        if platform == "instagram":
            return self.post_to_instagram(text, media_urls, "reel", scheduled_time, account_key)
        if platform == "tiktok":
            return self.post_to_tiktok(text, media_urls, True, scheduled_time, account_key)
        if platform == "youtube":
            title = kwargs.get("title", text[:50])
            return self.post_to_youtube(
                text, media_urls or [], title, scheduled_time=scheduled_time, account=account_key,
            )
        if platform == "threads":
            return self.post_to_threads(text, media_urls, scheduled_time, account_key)
        if platform == "pinterest":
            title = kwargs.get("title", text[:50])
            return self.post_to_pinterest(
                text, media_urls or [], title, scheduled_time=scheduled_time, account=account_key,
            )
        raise ValueError(f"Unsupported platform: {platform}")

    # =========================================================================
    # Analytics — Postiz GET /analytics/post/<id>
    # =========================================================================
    def get_post_analytics(self, post_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/analytics/post/{post_id}")


# =============================================================================
# Quick Access Functions
# =============================================================================
_client: Optional[PostizClient] = None


def get_client() -> PostizClient:
    global _client
    if _client is None:
        _client = PostizClient()
    return _client


def post(account_key: str, text: str, media_urls: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
    return get_client().post(account_key, text, media_urls, **kwargs)


def upload_media(url: str) -> Dict[str, Any]:
    return get_client().upload_media(url)


if __name__ == "__main__":
    client = PostizClient()
    print("=== Postiz Integrations (active only) ===")
    integrations = _load_integrations()
    for it in integrations:
        if it.get("active", True):
            print(
                f"- {it['platform']:>9} | {it['handle']:<48} → {it['id']} "
                f"(owner={it.get('owner_skill','?')}, phase={it.get('warmup_phase','?')})"
            )
