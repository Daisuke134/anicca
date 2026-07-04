#!/usr/bin/env python3
"""note_browser_common.py -- shared cloakbrowser bootstrap helpers for the note.com Mode-A browser scripts
(lib/note-set-eyecatch.py, lib/note-set-single-price.py).

Sprint-2 contract-review FIND-006 fix: both scripts, authored together for the same PROP-21 fix, duplicated
~20 lines of (1) cookie-file load + cookie-dict-to-cloakbrowser-cookie-list conversion and (2) cloakbrowser
session bootstrap + navigate + "wait up to N seconds for the editor's own 公開に進む button to appear"
polling loop, differing only in a viewport constant and a log string. This module is the single place that
shared logic now lives; both callers import it instead of re-implementing it.

This module is deliberately Mode-A-agnostic: it knows nothing about eyecatch/price/paid-line logic, only
how to load note.com session cookies and get a cloakbrowser page onto a note.com draft editor in a ready
state. Neither caller's own distinct error-message wording changes -- this module never prints/exits by
itself; it returns None/`(ctx, None)` so each caller keeps its own clearly-labeled diagnostic.
"""
import json
import os
import time
from typing import Optional

from cloakbrowser import launch_context


def load_note_cookies(cookies_file: str) -> Optional[list]:
    """Load a note.com cookies JSON file (a flat name->value dict) into the list-of-dicts shape
    cloakbrowser's `ctx.add_cookies()` expects. Returns None if the file does not exist -- the caller
    decides how to report that (each of note-set-eyecatch.py/note-set-single-price.py keeps its own
    distinct stderr message naming itself)."""
    if not os.path.isfile(cookies_file):
        return None
    with open(cookies_file) as f:
        ck = json.load(f)
    return [{"name": k, "value": v, "domain": ".note.com", "path": "/"} for k, v in ck.items()]


def open_editor_ready(cookies: list, note_key: str, viewport: dict, timeout_s: int = 20):
    """Launch a headless cloakbrowser context, add `cookies`, navigate to the note.com editor for
    `note_key`, and poll (up to `timeout_s` seconds, 1s apart) until the editor's own "公開に進む"
    (proceed-to-publish) button text appears in the page body -- the readiness signal both
    note-set-eyecatch.py and note-set-single-price.py already independently polled for before this fix.

    Returns `(ctx, pg)` on success. Returns `(ctx, None)` if the editor never reached the ready state
    within `timeout_s` -- the caller is responsible for `ctx.close()` in BOTH cases (this function never
    closes the context itself, since a caller may still want the context alive for its own diagnostics).
    """
    ctx = launch_context(headless=True, humanize=False)
    ctx.add_cookies(cookies)
    pg = ctx.new_page()
    pg.set_viewport_size(viewport)
    pg.goto(f"https://editor.note.com/notes/{note_key}/edit/", wait_until="domcontentloaded", timeout=45000)
    for _ in range(timeout_s):
        if "公開に進む" in pg.evaluate("()=>document.body.innerText"):
            return ctx, pg
        time.sleep(1)
    return ctx, None
