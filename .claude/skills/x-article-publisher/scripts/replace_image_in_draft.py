#!/usr/bin/env python3
"""replace_image_in_draft.py — TARGETED replacement of a single image in an
existing X Articles draft, without touching the rest of the document or
deleting the draft.

USAGE
  python3 replace_image_in_draft.py \
    --draft-url https://x.com/compose/articles/edit/<ID> \
    --index N \
    --src path/to/new-image.jpg \
    --anchor "exact text of the paragraph this image should sit under"
    [--cdp http://localhost:9222]

WHAT IT DOES
  1. Attach to the live CloakBrowser daily-driver via CDP.
  2. Open the draft URL (read-only; never re-creates the draft).
  3. Find the Nth image in the composer (0-indexed).
  4. Scroll it into view, hover, click the ✕ overlay at top-right to delete
     the atomic block. Confirm any "Delete media" dialog. Backspace is NOT
     used (= unreliable on Draft.js atomic blocks, see 2026-06-28 lesson).
  5. Walk the editor text-nodes for the --anchor phrase, scroll the matched
     paragraph into view, click its LAST PIXEL via Range.getClientRects(),
     press End.
  6. Copy the --src image to clipboard via copy_to_clipboard.py (which
     honors EXIF orientation + strips EXIF before clipboard).
  7. Cmd+V, wait for the upload spinner to clear, ArrowDown to step out of
     the new atomic block.
  8. Screenshot before/after into <draft>-replace-screenshots/.

GUARANTEES
  * NEVER calls cleanup_exact_title_duplicates → existing draft survives.
  * NEVER deletes or re-creates the draft.
  * Touches ONLY the one image identified by --index. Other blocks remain.
  * No --publish flag. The script has no publish path. Hand off to Dais.

DESIGN NOTES
  * Index-based locator chosen over src-based because X CDN renames uploaded
    files (src does not contain the original filename).
  * If you have multiple images to replace, run this script in DESCENDING
    --index order so deletes don't shift later indices.
"""
from __future__ import annotations
import argparse, pathlib, re, subprocess, sys, time
from playwright.sync_api import sync_playwright


def log(*a): print("[replace_image_in_draft]", *a, flush=True)


COPY_HELPER = (
    pathlib.Path.home()
    / ".claude/skills/x-article-publisher/scripts/copy_to_clipboard.py"
)


def copy_image(src: pathlib.Path) -> None:
    subprocess.run(
        ["python3", str(COPY_HELPER), "image", str(src), "--quality", "90"],
        check=True,
        capture_output=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--draft-url", required=True,
                    help="https://x.com/compose/articles/edit/<id>")
    ap.add_argument("--index", required=True, type=int,
                    help="0-indexed position of the image in the composer body "
                         "(cover image is in a separate dialog and is NOT counted)")
    ap.add_argument("--src", required=True, type=pathlib.Path,
                    help="Path to the replacement image on disk")
    ap.add_argument("--anchor", required=True,
                    help="Exact text fragment of the paragraph the replacement "
                         "image should sit immediately after")
    ap.add_argument("--cdp", default="http://localhost:9222")
    args = ap.parse_args()

    # ★ URL guard FIRST (= cheap structural check, no disk side-effects).
    # If we check `src.exists()` before this, a missing src masks a bad URL
    # in the test output (= adversary r2 caught this).
    if not args.draft_url.startswith("https://x.com/compose/articles/edit/"):
        sys.exit(f"refusing to operate on non-draft URL: {args.draft_url}")

    src = args.src.resolve()
    if not src.exists():
        sys.exit(f"src image missing: {src}")

    shots = src.parent / f"replace-{src.stem}-screenshots"
    shots.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(args.cdp)
        except Exception as e:
            sys.exit(
                f"could not attach to CDP at {args.cdp}: {e}\n"
                "Start the CloakBrowser daily-driver with --remote-debugging-port=9222."
            )
        if not browser.contexts:
            sys.exit(f"no browser context on CDP target {args.cdp}")
        ctx = browser.contexts[0]
        page = ctx.new_page()
        page.set_default_timeout(20000)
        page.goto(args.draft_url, wait_until="domcontentloaded")
        time.sleep(5)
        page.screenshot(path=str(shots / "00-before.png"))
        log(f"opened draft {args.draft_url}")

        # ---- 1. Locate the image by index, scroll into view
        coords = page.evaluate(
            """(idx) => {
                const imgs = document.querySelectorAll('div[data-testid="composer"] img');
                if (idx < 0 || idx >= imgs.length) return null;
                const img = imgs[idx];
                img.scrollIntoView({block: 'center'});
                const r = img.getBoundingClientRect();
                return {x: r.x + r.width/2, y: r.y + r.height/2,
                        rightX: r.right - 18, topY: r.top + 18,
                        total: imgs.length};
            }""",
            args.index,
        )
        if not coords:
            sys.exit(f"image index {args.index} out of range")
        log(f"image found @ center=({coords['x']:.0f},{coords['y']:.0f}), "
            f"composer-img total={coords['total']}")
        time.sleep(0.5)

        # ---- 2. Delete via shared ✕ overlay helper (Backspace is unreliable).
        # If delete fails, ABORT — we MUST NOT paste a replacement next to
        # the still-present original (= would create a duplicate, the exact
        # incident that triggered this feature).
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        from _xpub_browser import delete_image_block
        if not delete_image_block(page, img_index=args.index):
            page.screenshot(path=str(shots / "01-delete-FAILED.png"))
            sys.exit(
                f"delete_image_block FAILED for index {args.index}; aborting "
                f"without paste so no duplicate is created. Inspect "
                f"{shots / '01-delete-FAILED.png'} and retry."
            )
        page.screenshot(path=str(shots / "01-after-delete.png"))
        new_total = page.evaluate(
            '() => document.querySelectorAll(\'div[data-testid="composer"] img\').length'
        )
        log(f"image count after delete = {new_total} (was {coords['total']})")
        if new_total >= coords["total"]:
            log("WARN: delete did not change image count; paste will still "
                "be attempted but the result may have a duplicate")

        # ---- 3. Click anchor paragraph (last text pixel) so cursor lands
        target = page.evaluate(
            """(text) => {
                const editor = document.querySelector('div[data-testid="composer"]');
                if (!editor) return null;
                const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT);
                let n, found = null;
                while ((n = walker.nextNode())) {
                    if ((n.textContent || '').includes(text)) found = n;
                }
                if (!found) return null;
                (found.parentElement || found).scrollIntoView({block: 'center'});
                const r = document.createRange();
                r.selectNodeContents(found);
                const rects = r.getClientRects();
                if (!rects.length) return null;
                const last = rects[rects.length - 1];
                return {x: Math.min(last.right - 2, window.innerWidth - 4),
                        y: last.top + last.height / 2};
            }""",
            args.anchor,
        )
        if not target:
            sys.exit(f"anchor text not found in editor: {args.anchor!r}")
        log(f"anchor click @ ({target['x']:.0f},{target['y']:.0f})")
        page.keyboard.press("Escape"); time.sleep(0.2)
        page.mouse.click(target["x"], target["y"]); time.sleep(0.3)
        page.mouse.click(target["x"], target["y"]); time.sleep(0.3)
        page.keyboard.press("End"); time.sleep(0.2)

        # ---- 4. Paste replacement
        copy_image(src)
        time.sleep(0.5)
        page.keyboard.press("Meta+v")
        try:
            page.wait_for_selector(
                'text=/uploading|アップロード中|正在上传媒体|업로드/i',
                state="hidden",
                timeout=40000,
            )
        except Exception:
            time.sleep(3)
        time.sleep(2.0)
        page.keyboard.press("ArrowDown"); time.sleep(0.4)
        page.screenshot(path=str(shots / "02-after-paste.png"))
        final_total = page.evaluate(
            '() => document.querySelectorAll(\'div[data-testid="composer"] img\').length'
        )
        log(f"image count after paste = {final_total}")
        log(f"DONE. draft URL: {args.draft_url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
