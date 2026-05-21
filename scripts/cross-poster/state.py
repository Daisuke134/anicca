"""
State Management

Tracks processed TikTok post IDs to prevent duplicate cross-posting.
Uses a JSON file that is cached by GitHub Actions (actions/cache).
"""
import json
from pathlib import Path

STATE_FILE = Path(__file__).parent / "processed_ids.json"


def load_processed_ids() -> set[str]:
    """Load previously processed TikTok post IDs."""
    if not STATE_FILE.exists():
        return set()
    data = json.loads(STATE_FILE.read_text())
    return set(data.get("processed", []))


def save_processed_id(tiktok_id: str) -> None:
    """Add a TikTok post ID to the processed set."""
    ids = load_processed_ids()
    ids.add(tiktok_id)
    STATE_FILE.write_text(json.dumps({"processed": sorted(ids)}, indent=2))


def save_all_processed_ids(ids: set[str]) -> None:
    """Overwrite the processed IDs set."""
    STATE_FILE.write_text(json.dumps({"processed": sorted(ids)}, indent=2))
