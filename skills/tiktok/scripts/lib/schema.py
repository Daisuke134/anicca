#!/usr/bin/env python3
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid


def now_iso() -> str:
    return datetime.now().isoformat()


def make_content_item(
    item_type: str,
    title: str,
    content: str,
    tags: Optional[List[str]] = None,
    topic: str = "",
    angle: str = "",
    notes: str = ""
) -> Dict[str, Any]:
    return {
        "id": f"TK-{uuid.uuid4().hex[:8].upper()}",
        "type": item_type,
        "title": title,
        "content": content,
        "topic": topic,
        "angle": angle,
        "tags": tags or [],
        "notes": notes,
        "created_at": now_iso()
    }


def make_video_log(
    video_title: str,
    topic: str,
    angle: str,
    hook_type: str,
    views: int,
    likes: int,
    comments: int,
    shares: int,
    completion_rate: float,
    notes: str = ""
) -> Dict[str, Any]:
    return {
        "id": f"VID-{uuid.uuid4().hex[:8].upper()}",
        "video_title": video_title,
        "topic": topic,
        "angle": angle,
        "hook_type": hook_type,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "completion_rate": completion_rate,
        "notes": notes,
        "logged_at": now_iso()
    }
