"""
Railway Admin API Client
Handles all HTTP calls to the backend Admin API.
"""
import requests
from config import API_BASE_URL, API_AUTH_TOKEN


class AdminAPIClient:
    """Client for Railway Admin API endpoints"""

    def __init__(self):
        self.base_url = API_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {API_AUTH_TOKEN}",
            "Content-Type": "application/json",
        }

    def _get(self, path, params=None):
        url = f"{self.base_url}/api/admin{path}"
        resp = requests.get(url, headers=self.headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, json_data=None):
        url = f"{self.base_url}/api/admin{path}"
        resp = requests.post(url, headers=self.headers, json=json_data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _put(self, path, json_data=None):
        url = f"{self.base_url}/api/admin{path}"
        resp = requests.put(url, headers=self.headers, json=json_data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # EP-1
    def get_recent_posts(self, days=1):
        return self._get("/tiktok/recent-posts", params={"days": days})

    # EP-2
    def get_hook_candidates(self, limit=20, sort_by="app_tap_rate", strategy=None):
        params = {"limit": limit, "sort_by": sort_by}
        if strategy:
            params["strategy"] = strategy
        return self._get("/hook-candidates", params=params)

    # EP-3
    def save_post_record(self, blotato_post_id, caption, hook_candidate_id=None, agent_reasoning=None, scheduled_time=None, slot=None):
        data = {
            "blotato_post_id": blotato_post_id,
            "caption": caption,
        }
        if hook_candidate_id:
            data["hook_candidate_id"] = hook_candidate_id
        if agent_reasoning:
            data["agent_reasoning"] = agent_reasoning[:10000]
        if scheduled_time:
            data["scheduled_time"] = scheduled_time
        if slot:
            data["slot"] = slot
        return self._post("/tiktok/posts", json_data=data)

    # EP-4
    def update_post_metrics(self, post_id, metrics, tiktok_video_id=None):
        data = {
            "view_count": metrics.get("view_count", 0),
            "like_count": metrics.get("like_count", 0),
            "share_count": metrics.get("share_count", 0),
            "comment_count": metrics.get("comment_count", 0),
        }
        if tiktok_video_id:
            data["tiktok_video_id"] = tiktok_video_id
        return self._put(f"/tiktok/posts/{post_id}/metrics", json_data=data)

    # EP-5
    def get_pending_metrics_posts(self):
        return self._get("/tiktok/posts", params={"metrics_pending": "true"})

    # EP-6
    def refresh_tiktok_stats(self):
        return self._post("/hook-candidates/refresh-tiktok-stats")

    # OPS-1 (1.6.2): record ops events (SSOT is agent_audit_logs) + optional Slack notify.
    def record_ops_event(self, event_type, platform=None, payload=None):
        data = {
            "eventType": event_type,
            "platform": platform,
            "payload": payload or {},
        }
        return self._post("/ops/events", json_data=data)
