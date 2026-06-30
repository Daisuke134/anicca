#!/usr/bin/env python3
"""note-publish-corgi.py — DRAFT-only publish of the Corgi Cafe JP article to
note.com, using the daily-driver's note cookies (extracted via CDP).

NO tables, NO mermaid in the source — just text + 7 content images + 1 cover.
Cover (IMG_4922) becomes the note 見出し画像 (eyecatch); the 7 content images
become body images at their markdown positions.

NEVER publishes; only update_article (= draft_save). Hand off the draft URL
to Dais for browser verification + manual publish.
"""
from __future__ import annotations
import asyncio, json, os, pathlib, re, sys, time
sys.path.insert(0, "/Users/anicca/.openclaw/external/note-mcp/src")
from note_mcp.models import Session, ArticleInput
from note_mcp.api.articles import create_draft, update_article
from note_mcp.api.images import upload_body_image, upload_eyecatch_image

ART = pathlib.Path("/Users/anicca/anicca-project/docs/articles/corgi-cafe/article-jp.md")
ASSETS = ART.parent / "assets"
COOK_PATH = pathlib.Path.home() / ".cloak/note-work/note-cookies.json"

USER_ID = "14651590"          # Dais's note account id (per skill)
USERNAME = "anicca123"

ck = json.loads(COOK_PATH.read_text())

md = ART.read_text()
title_match = re.search(r"^#\s+(.+)$", md, re.M)
title = title_match.group(1).strip() if title_match else "(no title)"
body = re.sub(r"^#\s+.+$", "", md, count=1, flags=re.M).lstrip()

# Find every ![alt](./assets/FILENAME) reference in markdown order.
img_pattern = re.compile(r"!\[([^\]]*)\]\(\./assets/([^\)]+)\)")
images_in_md = img_pattern.findall(body)  # list of (alt, filename)
print(f"title       = {title}")
print(f"body images = {len(images_in_md)}")
for i, (alt, fn) in enumerate(images_in_md):
    print(f"  [{i}] {fn:20s} alt={alt!r}")

# First image = cover (eyecatch); rest = body content images.
cover_alt, cover_fn = images_in_md[0]
content = images_in_md[1:]
cover_path = ASSETS / cover_fn
if not cover_path.exists():
    sys.exit(f"cover image missing on disk: {cover_path}")
for _, fn in content:
    p = ASSETS / fn
    if not p.exists():
        sys.exit(f"content image missing on disk: {p}")

# Strip the cover image line from body; replace remaining content images
# with @@FIG{n}@@ markers (1-indexed) in their original positions.
body = img_pattern.sub(
    lambda m: "" if m.group(2) == cover_fn else "",  # temp clear all, we re-insert below
    body,
    count=1,
)
# Re-insert FIG markers in order
fig_n = 0
def _to_marker(m):
    global fig_n
    if m.group(2) == cover_fn:
        return ""
    fig_n += 1
    return f"\n@@FIG{fig_n}@@\n"

body = ART.read_text()
body = re.sub(r"^#\s+.+$", "", body, count=1, flags=re.M).lstrip()
fig_n = 0
body = img_pattern.sub(_to_marker, body)
print(f"FIG markers = {fig_n} (= content images, cover excluded)")

# note quirks (from skill):
# - un-blockquote (strip leading `> `)
# - keep h2 as section titles, sub-points as bold (no h3 here, OK)
body = re.sub(r"^>\s?", "", body, flags=re.M)

# Initialize session
sess = Session(
    cookies=ck,
    user_id=USER_ID,
    username=USERNAME,
    created_at=int(time.time()),
)


async def main() -> None:
    # Step 1: create the draft with placeholder body (markers in place but
    # not yet replaced with image URLs — that needs the article_id back).
    # Tags chosen to match the article topic.
    tags = ["AI", "スタートアップ", "サンフランシスコ", "Corgi Cafe", "体験記"]
    initial = ArticleInput(title=title, body=body, tags=tags)
    article = await create_draft(sess, initial)
    article_id = article.id
    article_key = article.key
    print(f"DRAFT CREATED: id={article_id} key={article_key}")

    # Step 2: upload eyecatch (cover)
    try:
        await upload_eyecatch_image(sess, str(cover_path), article_id)
        print(f"  eyecatch OK ({cover_fn})")
    except Exception as e:
        print(f"  eyecatch FAILED: {str(e)[:200]}")

    # Step 3: upload each content image and replace its @@FIG@@ marker
    final_body = body
    for n, (alt, fn) in enumerate(content, 1):
        path = str(ASSETS / fn)
        try:
            img = await upload_body_image(sess, path, article_id)
            md_img = f"![{alt}]({img.url})"
            final_body = final_body.replace(f"@@FIG{n}@@", md_img)
            print(f"  fig{n} OK ({fn})")
        except Exception as e:
            print(f"  fig{n} FAILED ({fn}): {str(e)[:200]}")
            final_body = final_body.replace(f"@@FIG{n}@@", "")

    # Step 4: update with final body (= draft_save under the hood)
    await update_article(
        sess,
        article_id,
        ArticleInput(title=title, body=final_body, tags=tags),
    )
    public_url = f"https://note.com/{USERNAME}/n/{article_key}"
    editor_url = f"https://editor.note.com/notes/{article_id}/edit/"
    print(f"\nDRAFT URL (editor): {editor_url}")
    print(f"DRAFT URL (canonical, public-shape): {public_url}")
    pathlib.Path("/Users/anicca/anicca-project/docs/articles/corgi-cafe/note-draft-url.txt").write_text(
        json.dumps({"article_id": article_id, "article_key": article_key,
                    "editor_url": editor_url, "public_url": public_url}, indent=2)
    )


asyncio.run(main())
