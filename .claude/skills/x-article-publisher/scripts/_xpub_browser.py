"""Shared browser primitives for x-article-publisher scripts.

Currently exposes one helper:

  delete_image_block(page, img_index: int) -> bool

which hovers an image in the X Articles composer and clicks the top-right
✕ overlay to remove its Draft.js atomic block. Backspace is NOT used
(unreliable on atomic blocks; see 2026-06-28 lesson).

Used by:
  - publish_md_to_x.py  → WARN-retry path (delete wrongly-placed image,
                          then fall through to FAIL-retry path)
  - replace_image_in_draft.py → targeted single-image replacement
"""
from __future__ import annotations
import re
import time


def delete_image_block(page, img_index: int = -1) -> bool:
    """Delete the Nth image in the composer body (0-indexed, negative allowed
    e.g. -1 for last). Returns True on apparent success (composer-img count
    decreased by 1), False otherwise. NEVER raises — caller decides handling.

    Method: locate img → scroll into view → hover image center → click the
    ✕ overlay at top-right (offset 18px from corner) → confirm any
    "Delete media?" dialog. NEVER uses Backspace (Draft.js atomic blocks
    silently swallow it).
    """
    try:
        before = page.evaluate(
            '() => document.querySelectorAll(\'div[data-testid="composer"] img\').length'
        )
        rect = page.evaluate(
            """(idx) => {
                const imgs = document.querySelectorAll('div[data-testid="composer"] img');
                if (!imgs.length) return null;
                const i = idx < 0 ? imgs.length + idx : idx;
                if (i < 0 || i >= imgs.length) return null;
                const img = imgs[i];
                img.scrollIntoView({block: 'center'});
                const r = img.getBoundingClientRect();
                return {x: r.x + r.width/2, y: r.y + r.height/2,
                        rightX: r.right - 18, topY: r.top + 18};
            }""",
            img_index,
        )
        if not rect:
            return False
        page.mouse.move(rect["x"], rect["y"])
        time.sleep(0.4)
        page.mouse.click(rect["rightX"], rect["topY"])
        time.sleep(0.8)
        # X may surface a "Delete media?" confirm dialog
        try:
            page.get_by_role(
                "button",
                name=re.compile(r"^(Delete|Remove|削除)$", re.I),
            ).first.click(timeout=1500)
            time.sleep(0.6)
        except Exception:
            pass
        after = page.evaluate(
            '() => document.querySelectorAll(\'div[data-testid="composer"] img\').length'
        )
        return after < before
    except Exception:
        return False
