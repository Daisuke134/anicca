#!/usr/bin/env python3
"""Read what Dais actually said, from the Telegram Web tab that is already logged in.

Three attempts on 2026-08-06 concluded this was impossible. Each was wrong, and each was
wrong for the same reason -- a refusal from one entrance was read as a wall:

  openclaw message read   Unsupported Telegram action: read   (the gateway owns that token)
  getUpdates              Conflict: webhook is active         (Mr.bot owns that one)
  cookie inspection       0 rows for telegram                 (the session lives in IndexedDB)

The daily-driver profile is logged in. So the text is readable with no token at all, and
without touching either receive path that production depends on.

Two facts here were measured rather than assumed, and both cost a round trip to learn:

``.chatlist-chat`` is the row, not ``ul.chatlist li`` -- that selector belongs to an older
build of the client and matches nothing today.

**A chat only opens on a real mouse event.** ``element.click()`` and ``location.hash = ...``
both leave the message pane empty; the client's router does not listen to either. The
caller must dispatch ``Input.dispatchMouseEvent`` at the row's centre.

This reader does **not** exist to ask permission. The loop's whole value is that it earns
with no human in it, and a send that waits for a reply is a send that never happens on a
workday; what a message may contain is decided by ``followup_draft.check_draft``, which is
code and answers instantly. Reading runs the other direction -- picking up an instruction
Dais typed on his own ("this thread is dead, stop") without him having to be asked.

Orientation of authorship is the opposite of the naive reading: the browser is logged in as
Dais, so ``is-out`` marks *Dais's* messages, and the bot's replies are incoming. A caller
that got this backwards would obey the loop's own report as if Dais had written it, so
``owner`` is attached here rather than left to the caller's memory.
"""
from __future__ import annotations

import json
from typing import Any

TELEGRAM_HOST = "web.telegram.org"

# The account owner. Only text attributed here was actually typed by Dais.
OWNER = "dais"
PEER = "peer"


def logged_in_targets(targets: Any) -> list[dict[str, Any]]:
    """Debuggable Telegram pages, newest listing order preserved.

    Shared workers and service workers carry the same origin and outnumber the pages 8 to 1,
    and a target without a websocket url cannot be driven at all. Both are dropped here so
    the caller never has to discover that by timing out.
    """
    pages: list[dict[str, Any]] = []
    if not isinstance(targets, (list, tuple)):
        return pages
    for target in targets:
        if not isinstance(target, dict):
            continue
        if target.get("type") != "page":
            continue
        if TELEGRAM_HOST not in str(target.get("url") or ""):
            continue
        if not target.get("webSocketDebuggerUrl"):
            continue
        pages.append(target)
    return pages


def chat_count_script() -> str:
    """Rows in the chat list. Zero means this tab is the logged-out QR one."""
    return "document.querySelectorAll('.chatlist-chat').length"


def chat_row_script(title: str) -> str:
    """Centre of the row named ``title``, scrolled into view, as JSON -- or null.

    Returns coordinates instead of clicking because the click has to come from CDP; a
    click issued inside the page does not open the chat.
    """
    return (
        "(() => {"
        "  const rows = [...document.querySelectorAll('.chatlist-chat')];"
        "  const row = rows.find(r =>"
        f"    (r.querySelector('.peer-title')?.textContent || '') === {json.dumps(title)});"
        "  if (!row) return JSON.stringify(null);"
        "  row.scrollIntoView({block: 'center'});"
        "  const box = row.getBoundingClientRect();"
        "  return JSON.stringify({"
        "    x: Math.round(box.x + box.width / 2),"
        "    y: Math.round(box.y + box.height / 2)});"
        "})()"
    )


def read_bubbles_script(limit: int = 20) -> str:
    """The last ``limit`` message bubbles as JSON.

    The send time lives *inside* ``.message``, so a plain ``innerText`` returns
    ``"/panel core8d\\n\\n04:54 PM"``. The clock is stripped from a clone rather than the
    live node: this script runs in Dais's own open tab, and a reader must not edit what it
    is reading.
    """
    count = max(1, int(limit or 1))
    return (
        "(() => {"
        f" const bubbles = [...document.querySelectorAll('.bubble')].slice(-{count});"
        "  const body = b => {"
        "    const node = b.querySelector('.message');"
        "    if (!node) return '';"
        "    const copy = node.cloneNode(true);"
        "    copy.querySelectorAll('.time, .message-time').forEach(t => t.remove());"
        "    return copy.innerText || '';"
        "  };"
        "  return JSON.stringify({"
        "    hash: location.hash,"
        "    total: document.querySelectorAll('.bubble').length,"
        "    bubbles: bubbles.map(b => ({"
        "      outgoing: b.classList.contains('is-out'),"
        "      text: body(b)})) });"
        "})()"
    )


def parse_bubbles(payload: Any, *, owner: str = OWNER) -> list[dict[str, Any]]:
    """Bubbles as ``{"from", "text"}`` rows, ordered oldest to newest.

    Service bubbles (date separators, "unread messages") carry no ``.message`` node and are
    dropped: an empty string cannot approve anything, and keeping them would make a caller
    that counts messages disagree with a caller that reads them.
    """
    data = payload
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            return []
    if not isinstance(data, dict):
        return []
    rows: list[dict[str, Any]] = []
    for bubble in data.get("bubbles") or []:
        if not isinstance(bubble, dict):
            continue
        text = str(bubble.get("text") or "").strip()
        if not text:
            continue
        rows.append({
            "from": owner if bubble.get("outgoing") else PEER,
            "text": text,
        })
    return rows
