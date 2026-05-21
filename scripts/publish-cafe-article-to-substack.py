#!/usr/bin/env python3
"""Publish Anicca cafe article to Substack via substack-mcp's SubstackClient.

Run on Mac mini after substack-mcp-setup completed:
  cd ~/Developer/substack-mcp
  source .venv/bin/activate
  python publish-cafe-article-to-substack.py

This script:
  1. Fetches the cafe article JSON from raw.githubusercontent.com (public anicca-products repo)
  2. Downloads the 4 embedded images to /tmp/anicca-substack/
  3. Rewrites markdown image paths to local absolute paths
  4. Calls substack-mcp's SubstackClient (which uses python-substack internal API)
     -> upload_image (cover)
     -> create_draft (auto-uploads inline images)
     -> set_cover_image
     -> publish_draft
  5. Prints the public URL
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path


REPO_RAW = "https://raw.githubusercontent.com/Daisuke134/anicca-products/main/apps/landing"
ARTICLE_SLUG = "anicca-cafe-tokyo-2026-05-09"
ARTICLE_JSON_URL = f"{REPO_RAW}/data/research/{ARTICLE_SLUG}.json"
PUBLIC_BASE_URL = f"{REPO_RAW}/public"  # /blog/cafe/* maps under /public


def fetch_url(url: str, dest: Path | None = None) -> bytes:
    print(f"  GET {url}")
    with urllib.request.urlopen(url, timeout=60) as r:
        data = r.read()
    if dest is not None:
        dest.write_bytes(data)
        print(f"      -> {dest} ({len(data):,} bytes)")
    return data


def main() -> int:
    try:
        from substack_mcp.client import SubstackClient
    except ImportError:
        print("[ERR] substack_mcp not importable. Activate the venv first:")
        print("      cd ~/Developer/substack-mcp && source .venv/bin/activate")
        return 1

    print("▶ Loading credentials")
    client = SubstackClient.from_env()
    print("  ✓ client ready")

    print(f"\n▶ Fetching article JSON: {ARTICLE_JSON_URL}")
    article = json.loads(fetch_url(ARTICLE_JSON_URL).decode("utf-8"))
    title = article["title"]
    body_md = article["markdown"]
    print(f"  title: {title}")
    print(f"  word_count: {article.get('word_count', '?')}")

    # Use ~/Pictures (normal user dir) — substack-mcp refuses /tmp / /private/var paths
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    work_dir = Path.home() / "Pictures" / f"anicca-substack-{stamp}"
    work_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n▶ Work dir: {work_dir}")

    # Download all embedded images and rewrite paths to local absolute paths.
    img_pattern = re.compile(r"!\[([^\]]*)\]\((/blog/[^)]+)\)")
    matches = img_pattern.findall(body_md)
    print(f"\n▶ Downloading {len(matches)} embedded images")
    for _alt, web_path in matches:
        url = PUBLIC_BASE_URL + web_path
        local = work_dir / Path(web_path).name
        if not local.exists():
            fetch_url(url, local)

    def rewrite(m: re.Match) -> str:
        local = work_dir / Path(m.group(2)).name
        return f"![{m.group(1)}]({local})"

    body_local = img_pattern.sub(rewrite, body_md)

    # Strip the leading H1 since Substack already shows the title separately.
    body_local = re.sub(r"^#\s+.+?\n+", "", body_local, count=1)

    # Pull out the hero image (first image in the article) for cover use.
    hero_local = work_dir / "hero-mango-reset.jpg"
    if not hero_local.exists():
        fetch_url(f"{PUBLIC_BASE_URL}/blog/cafe/hero-mango-reset.jpg", hero_local)

    subtitle = "One bottle. One mango. One reset. A Tokyo ghost-kitchen, opened by an AI."

    print("\n▶ Uploading cover image to Substack CDN")
    cover = client.upload_image(str(hero_local))
    cover_url = cover.get("url") if isinstance(cover, dict) else cover
    print(f"  cover_url: {cover_url}")

    # IMPORTANT: python-substack's from_markdown does NOT auto-upload inline
    # images when paths are absolute. Pre-upload each and rewrite to CDN URLs
    # so they actually render in the published post. (5/9 cafe bug fix.)
    print("\n▶ Pre-uploading inline images to CDN (overrides local-path bug)")
    inline_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    seen: dict[str, str] = {}
    for m in inline_pattern.finditer(body_local):
        path = m.group(2)
        if path.startswith(("http://", "https://")) or path in seen:
            continue
        up = client.upload_image(path)
        seen[path] = up.get("url") if isinstance(up, dict) else up
        print(f"    {Path(path).name} -> {seen[path]}")

    def _rewrite(m: re.Match) -> str:
        return f"![{m.group(1)}]({seen.get(m.group(2), m.group(2))})"

    body_local = inline_pattern.sub(_rewrite, body_local)
    body_local = re.sub(r"^\s*---+\s*$", "", body_local, flags=re.MULTILINE)
    body_local = re.sub(r"\n{3,}", "\n\n", body_local).strip()

    print("\n▶ Creating draft")
    draft = client.create_draft(
        title=title,
        content_markdown=body_local,
        subtitle=subtitle,
        audience="everyone",
    )
    post_id = draft.get("post_id") or draft.get("id")
    print(f"  post_id: {post_id}")
    if "edit_url" in draft:
        print(f"  edit_url: {draft['edit_url']}")

    print("\n▶ Setting cover image")
    client.set_cover_image(post_id=post_id, image_url=cover_url)

    print("\n▶ Publishing")
    published = client.publish_draft(
        post_id=post_id,
        send_email=True,
        share_automatically=False,
    )

    public_url = published.get("public_url") or published.get("canonical_url") or "(check publication home)"
    print("\n" + "=" * 60)
    print(f"✅ PUBLISHED  {public_url}")
    print("=" * 60)
    print(f"  post_id: {post_id}")
    print(f"  send_email: {published.get('send_email', '?')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
