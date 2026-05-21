"""
Blotato API Wrapper
SNS投稿を統一的に管理

アカウントキー:
- x_xg2grb: @aniccaxxx (Build in Public JP)
- x_nudges: @aniccaen (Marketing EN)
- ig_anicca_ai: @anicca.ai (Marketing EN)
- ig_anicca_japan: @anicca.japan (Marketing JP)
- ig_anicca_daily: @anicca.daily (Marketing EN, sub)
- tt_anicca_ai: @anicca.ai (Marketing EN)
- tt_anicca_japan: @anicca.japan (Marketing JP)
- tt_anicca57: @anicca57 (Marketing EN, sub)
- youtube_en: Daisuke Narita (Marketing EN)
- youtube_jp: @anicca.jp (Marketing JP)
- threads_japan: @anicca.japan (Marketing JP)
- pinterest: @aniccaai (pending - needs verification)
"""
import requests
from typing import Optional, List, Dict, Any
from config import BLOTATO_API_KEY, BLOTATO_BASE_URL, ACCOUNTS, DEFAULT_LINK


class BlotatoClient:
    """Blotato API Client"""

    def __init__(self, api_key: str = BLOTATO_API_KEY):
        self.api_key = api_key
        self.base_url = BLOTATO_BASE_URL
        self.headers = {
            "blotato-api-key": api_key,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # User & Account Management
    # =========================================================================
    def get_user(self) -> Dict[str, Any]:
        """Get current user info"""
        return self._request("GET", "/users/me")

    def list_accounts(self) -> Dict[str, Any]:
        """List all connected accounts (returns dict with 'items' key)"""
        return self._request("GET", "/users/me/accounts")

    # =========================================================================
    # Media Upload
    # =========================================================================
    def upload_media(self, url: str) -> Dict[str, Any]:
        """Upload media from URL"""
        return self._request("POST", "/media", json={"url": url})

    # =========================================================================
    # Post Creation - X (Twitter)
    # =========================================================================
    def post_to_x(
        self,
        text: str,
        media_urls: Optional[List[str]] = None,
        scheduled_time: Optional[str] = None,
        account: str = "x_xg2grb",
    ) -> Dict[str, Any]:
        """Post to X (Twitter)
        
        Args:
            account: 
                "x_xg2grb" - @xg2grb (Build in Public EN) [default]
                "x_nudges" - @AniccaNudges (Marketing EN)
        """
        account_data = ACCOUNTS.get(account, ACCOUNTS["x_xg2grb"])
        payload = {
            "post": {
                "accountId": account_data["id"],
                "content": {
                    "text": text,
                    "mediaUrls": media_urls or [],
                    "platform": "twitter",
                },
                "target": {"targetType": "twitter"},
            }
        }
        if scheduled_time:
            payload["scheduledTime"] = scheduled_time
        return self._request("POST", "/posts", json=payload)

    # =========================================================================
    # Post Creation - Instagram
    # =========================================================================
    def post_to_instagram(
        self,
        text: str,
        media_urls: List[str],
        media_type: str = "reel",
        scheduled_time: Optional[str] = None,
        account: str = "ig_anicca_ai",
    ) -> Dict[str, Any]:
        """Post to Instagram (requires media)
        
        Args:
            account:
                "ig_anicca_ai" - @anicca.ai (Marketing EN) [default]
                "ig_anicca_japan" - @anicca.japan (Marketing JP)
                "ig_anicca_daily" - @anicca.daily (Marketing EN, sub)
        """
        if not media_urls:
            raise ValueError("Instagram requires at least one media URL")

        account_data = ACCOUNTS.get(account, ACCOUNTS["ig_anicca_ai"])
        payload = {
            "post": {
                "accountId": account_data["id"],
                "content": {
                    "text": text,
                    "mediaUrls": media_urls,
                    "platform": "instagram",
                },
                "target": {
                    "targetType": "instagram",
                    "mediaType": media_type,
                },
            }
        }
        if scheduled_time:
            payload["scheduledTime"] = scheduled_time
        return self._request("POST", "/posts", json=payload)

    # =========================================================================
    # Post Creation - TikTok
    # =========================================================================
    def post_to_tiktok(
        self,
        text: str,
        media_urls: List[str],
        is_ai_generated: bool = True,
        scheduled_time: Optional[str] = None,
        account: str = "tt_anicca_ai",
    ) -> Dict[str, Any]:
        """Post to TikTok (requires media)
        
        Args:
            account:
                "tt_anicca_ai" - @anicca.ai (Marketing EN) [default]
                "tt_anicca_japan" - @anicca.japan (Marketing JP)
                "tt_anicca57" - @anicca57 (Marketing EN, sub)
        """
        if not media_urls:
            raise ValueError("TikTok requires at least one media URL")

        account_data = ACCOUNTS.get(account, ACCOUNTS["tt_anicca_ai"])
        payload = {
            "post": {
                "accountId": account_data["id"],
                "content": {
                    "text": text,
                    "mediaUrls": media_urls,
                    "platform": "tiktok",
                },
                "target": {
                    "targetType": "tiktok",
                    "privacyLevel": "PUBLIC_TO_EVERYONE",
                    "disabledComments": False,
                    "disabledDuet": False,
                    "disabledStitch": False,
                    "isBrandedContent": False,
                    "isYourBrand": False,
                    "isAiGenerated": is_ai_generated,
                },
            }
        }
        if scheduled_time:
            payload["scheduledTime"] = scheduled_time
        return self._request("POST", "/posts", json=payload)

    # =========================================================================
    # Post Creation - YouTube
    # =========================================================================
    def post_to_youtube(
        self,
        description: str,
        media_urls: List[str],
        title: str,
        privacy_status: str = "public",
        notify_subscribers: bool = True,
        made_for_kids: bool = False,
        scheduled_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post to YouTube (requires video)"""
        if not media_urls:
            raise ValueError("YouTube requires at least one video URL")

        payload = {
            "post": {
                "accountId": ACCOUNTS["youtube"]["id"],
                "content": {
                    "text": description,
                    "mediaUrls": media_urls,
                    "platform": "youtube",
                },
                "target": {
                    "targetType": "youtube",
                    "title": title,
                    "privacyStatus": privacy_status,
                    "shouldNotifySubscribers": notify_subscribers,
                    "isMadeForKids": made_for_kids,
                },
            }
        }
        if scheduled_time:
            payload["scheduledTime"] = scheduled_time
        return self._request("POST", "/posts", json=payload)

    # =========================================================================
    # Post Creation - Threads
    # =========================================================================
    def post_to_threads(
        self,
        text: str,
        media_urls: Optional[List[str]] = None,
        scheduled_time: Optional[str] = None,
        account: str = "threads_japan",
    ) -> Dict[str, Any]:
        """Post to Threads
        
        Args:
            account: 
                "threads_japan" - @anicca.japan (Marketing JP) [default]
        """
        account_data = ACCOUNTS.get(account, ACCOUNTS["threads_japan"])
        payload = {
            "post": {
                "accountId": account_data["id"],
                "content": {
                    "text": text,
                    "mediaUrls": media_urls or [],
                    "platform": "threads",
                },
                "target": {"targetType": "threads"},
            }
        }
        if scheduled_time:
            payload["scheduledTime"] = scheduled_time
        return self._request("POST", "/posts", json=payload)

    # =========================================================================
    # Post Creation - Pinterest
    # =========================================================================
    def post_to_pinterest(
        self,
        description: str,
        media_urls: List[str],
        title: str,
        board_id: Optional[str] = None,
        link: str = DEFAULT_LINK,
        scheduled_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Post to Pinterest (requires media and board_id)"""
        if not media_urls:
            raise ValueError("Pinterest requires at least one media URL")
        
        board = board_id or ACCOUNTS["pinterest"].get("board_id")
        if not board:
            raise ValueError("Pinterest requires a board_id")

        payload = {
            "post": {
                "accountId": ACCOUNTS["pinterest"]["id"],
                "content": {
                    "text": description,
                    "mediaUrls": media_urls,
                    "platform": "pinterest",
                },
                "target": {
                    "targetType": "pinterest",
                    "boardId": board,
                    "title": title,
                    "link": link,
                },
            }
        }
        if scheduled_time:
            payload["scheduledTime"] = scheduled_time
        return self._request("POST", "/posts", json=payload)

    # =========================================================================
    # Generic Post (by account key)
    # =========================================================================
    def post(
        self,
        account_key: str,
        text: str,
        media_urls: Optional[List[str]] = None,
        scheduled_time: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generic post by account key
        
        Example:
            client.post("ig_anicca_japan", "Hello!", ["https://..."])
        """
        account = ACCOUNTS.get(account_key)
        if not account:
            raise ValueError(f"Unknown account: {account_key}")
        
        platform = account["platform"]
        
        if platform == "twitter":
            return self.post_to_x(text, media_urls, scheduled_time, account_key)
        elif platform == "instagram":
            return self.post_to_instagram(text, media_urls, "reel", scheduled_time, account_key)
        elif platform == "tiktok":
            return self.post_to_tiktok(text, media_urls, True, scheduled_time, account_key)
        elif platform == "youtube":
            title = kwargs.get("title", text[:50])
            return self.post_to_youtube(text, media_urls, title, scheduled_time=scheduled_time)
        elif platform == "threads":
            return self.post_to_threads(text, media_urls, scheduled_time, account_key)
        elif platform == "pinterest":
            title = kwargs.get("title", text[:50])
            return self.post_to_pinterest(text, media_urls, title, scheduled_time=scheduled_time)
        else:
            raise ValueError(f"Unsupported platform: {platform}")


# =============================================================================
# Quick Access Functions
# =============================================================================
_client = None


def get_client() -> BlotatoClient:
    """Get singleton client instance"""
    global _client
    if _client is None:
        _client = BlotatoClient()
    return _client


def post(account_key: str, text: str, media_urls: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
    """Quick post by account key"""
    return get_client().post(account_key, text, media_urls, **kwargs)


def upload_media(url: str) -> Dict[str, Any]:
    """Quick media upload"""
    return get_client().upload_media(url)


if __name__ == "__main__":
    # Test: List accounts
    client = BlotatoClient()
    print("=== Blotato Accounts ===")
    response = client.list_accounts()
    accounts = response.get("items", [])
    for acc in accounts:
        print(f"- {acc.get('platform', 'unknown')}: {acc.get('id')} ({acc.get('username') or acc.get('fullname', 'N/A')})")
