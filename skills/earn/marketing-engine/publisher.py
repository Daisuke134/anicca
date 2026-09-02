#!/usr/bin/env python3
"""Official Meta publisher adapter shared by every marketing product."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request


PUBLISHER = "meta_graph"


def health(account=None, *, opener=urllib.request.urlopen, env=None):
    env = os.environ if env is None else env
    account = account or {}
    token = env.get("META_ACCESS_TOKEN", "")
    user_id = account.get("publisher_account_id") or env.get("META_IG_USER_ID", "")
    if not token or not user_id:
        return {"ok": False, "publisher": PUBLISHER, "error": "missing Meta publisher credentials"}
    version = env.get("META_GRAPH_VERSION", "v24.0")
    query = urllib.parse.urlencode({"fields": "id,username,media_count", "access_token": token})
    request = urllib.request.Request(f"https://graph.facebook.com/{version}/{user_id}?{query}")
    try:
        with opener(request, timeout=15) as response:
            payload = json.load(response)
        if str(payload.get("id", "")) != str(user_id):
            raise ValueError("publisher account id mismatch")
        return {
            "ok": True,
            "publisher": PUBLISHER,
            "publisher_account_id": str(user_id),
            "username": payload.get("username"),
        }
    except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {"ok": False, "publisher": PUBLISHER, "error": f"{type(exc).__name__}: {exc}"}
