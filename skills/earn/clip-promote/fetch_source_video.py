"""fetch_source_video.py — CLIP (REQ-2): read the selected campaign's detail page and extract a
usable source video URL for producer.sh to clip.

Verified live 2026-07-04 on two real campaigns' detail pages:
- crocs (TikTok-only, excluded by the SELECT platform filter but useful as a negative case):
  "provided content" links to a Google Drive folder — NOT auto-clippable, no direct video URL.
- thomas-rhett-content (Instagram-eligible): "Podcast 1"/"Podcast 2" links are REAL YouTube URLs
  (https://www.youtube.com/watch?v=WDjp6aA9Wcc etc.) — directly usable by the EXISTING
  producer.sh --url <youtube_url> pipeline (yt_dlp-based, no new download code needed).

Campaign detail pages vary in structure (this is a marketplace with many different brands each
writing their own campaign description), so this is a best-effort DETERMINISTIC extractor: it
finds the first youtube.com/youtu.be link on the page. If none exists (e.g. crocs' Google-Drive-
only case), it returns None — CLIP then reports "no-usable-source-video" rather than fabricating
a video (HARD RULE 0.24, no fake runs). A campaign with no auto-extractable source is skipped;
picking a DIFFERENT eligible campaign (one that does have a YouTube link) is SELECT's job on a
later wake, not this module's.
"""
import json
import re

_YT_LINK = re.compile(r"(https?://(?:www\.)?(?:youtube\.com/watch\?v=[\w-]+|youtu\.be/[\w-]+)[^\s\"'<>]*)")


def extract_youtube_url(raw_links):
    """Given [{href,t}] anchors from the campaign detail page, return the FIRST youtube.com/
    youtu.be URL found, or None. PURE + deterministic."""
    for a in raw_links or []:
        href = a.get("href") or ""
        m = _YT_LINK.search(href)
        if m:
            return m.group(1)
    return None


def fetch_live(tid, cdp, campaign_slug):
    """Live read of a campaign's detail page; returns the extracted YouTube URL or None."""
    import time
    cdp.navigate(tid, f"https://www.promote.fun/campaigns/{campaign_slug}")
    time.sleep(4)
    js = (
        "JSON.stringify(Array.from(document.querySelectorAll('a[href]'))"
        ".slice(0,80).map(function(a){return {href:a.href};}))"
    )
    raw = cdp.evaluate(tid, js)
    try:
        links = json.loads(raw)
    except Exception:
        links = []
    return extract_youtube_url(links)


if __name__ == "__main__":  # CLI: prints the extracted URL (or "" if none), needs a live CDP tab
    import os
    import sys
    cdp_dir = os.environ.get("CDP_DIR", os.path.expanduser("~/.claude/skills/ig-account-create/scripts"))
    sys.path.insert(0, cdp_dir)
    import cdp  # noqa: E402
    tid = os.environ.get("PF_TID", "")
    slug = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CAMPAIGN_SLUG", "")
    url = fetch_live(tid, cdp, slug)
    print(url or "")
