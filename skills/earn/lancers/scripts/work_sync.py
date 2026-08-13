#!/usr/bin/env python3
"""Bounded, read-only canonical Lancers sales-source observer."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Optional, Sequence
from urllib.parse import quote, urlencode

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("application_tick_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


application_tick = _load("anicca_lancers_work_sync_tick", HERE / "application_tick.py")
CDP_URL, DEFAULT_STATE_PATH = application_tick.CDP_URL, application_tick.DEFAULT_STATE_PATH
MAX_BOARD_PAGES = MAX_MESSAGE_PAGES = 20


class SourceFailure(RuntimeError): pass


def _id(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
        raise SourceFailure("provider_response_invalid")
    return str(value).strip()


def _digest(value: Any) -> str:
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    except (TypeError, ValueError):
        raise SourceFailure("provider_response_invalid") from None
    return hashlib.sha256(encoded).hexdigest()


def _fetch(page: Any, path: str) -> Any:
    value = page.evaluate(
        """async (path) => { const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 20000); try { const response = await fetch(path, {method: "GET", credentials: "same-origin", signal: controller.signal}); const text = await response.text(); return response.ok && text.length <= 1048576 ? {ok: true, body: JSON.parse(text)} : {ok: false}; } catch (_) { return {ok: false}; } finally { clearTimeout(timer); } }""",
        path,
    )
    if not isinstance(value, Mapping) or value.get("ok") is not True:
        raise SourceFailure("provider_response_invalid")
    return value.get("body")


def _pages(fetch: Callable[[str], Any], route: Callable[[Optional[str]], str], check: Callable[[Mapping[str, Any]], tuple[str, str]], maximum: int, errors: tuple[str, str, str]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []; seen: set[str] = set(); cursor: Optional[str] = None
    for _ in range(maximum):
        page = fetch(route(cursor))
        if not isinstance(page, list) or not all(isinstance(row, Mapping) for row in page): raise SourceFailure("provider_response_invalid")
        if not page: return rows
        for row in page:
            identity, _ = check(row)
            if identity in seen: raise SourceFailure(errors[0])
            seen.add(identity); rows.append(row)
        next_cursor = check(page[-1])[1]
        if next_cursor == cursor: raise SourceFailure(errors[1])
        cursor = next_cursor
    raise SourceFailure(errors[2])


def _messages(fetch: Callable[[str], Any], board_id: str) -> list[dict[str, str]]:
    def check(message: Mapping[str, Any]) -> tuple[str, str]:
        message_id = _id(message.get("id"))
        if _id(message.get("board_id")) != board_id or not isinstance(message.get("is_required_reply"), bool) or "send_user" not in message or "modified" not in message: raise SourceFailure("provider_response_invalid")
        _id(message["modified"]); return message_id, message_id
    route = lambda cursor: f"/v1/message_api/boards/{quote(board_id, safe='')}/messages?{urlencode({'limit': 20, **({'message_id': cursor, 'direction': 'prev'} if cursor else {})})}"
    return sorted(({"message_id": _id(row["id"]), "content_sha256": _digest(row)} for row in _pages(fetch, route, check, MAX_MESSAGE_PAGES, ("duplicate_message_id", "message_cursor_stalled", "message_page_limit_reached"))), key=lambda row: row["message_id"])


def _snapshot(fetch: Callable[[str], Any]) -> dict[str, Any]:
    def check(board: Mapping[str, Any]) -> tuple[str, str]:
        board_id = _id(board.get("id")); unread = board.get("unread_count")
        if not isinstance(board.get("is_required_reply"), bool) or isinstance(unread, bool) or not isinstance(unread, int) or unread < 0 or "modified" not in board: raise SourceFailure("provider_response_invalid")
        return board_id, _id(board["modified"])
    boards = _pages(fetch, lambda cursor: f"/v1/message_api/boards/?{urlencode({'limit': 20, **({'modified': cursor} if cursor else {})})}", check, MAX_BOARD_PAGES, ("duplicate_board_id", "board_cursor_stalled", "board_page_limit_reached"))

    output, replies, unread, applications, storefront = [], 0, 0, 0, 0
    for board in boards:
        board_id = _id(board["id"])
        detail = fetch(f"/v1/message_api/boards/{quote(board_id, safe='')}")
        if not isinstance(detail, Mapping) or _id(detail.get("id")) != board_id:
            raise SourceFailure("provider_response_invalid")
        with_value = detail.get("with", {})
        if not isinstance(with_value, Mapping):
            raise SourceFailure("provider_response_invalid")
        relations = []
        for key in ("proposal", "job", "serviceItemContract"):
            related = with_value.get(key)
            if related is not None and not isinstance(related, Mapping): raise SourceFailure("provider_response_invalid")
            relations.append(None if related is None or "id" not in related else _id(related["id"]))
        proposal, job, contract = relations
        messages = _messages(fetch, board_id)
        replies += int(board["is_required_reply"]); unread += board["unread_count"]
        applications += int(proposal is not None); storefront += int(contract is not None)
        output.append({"board_id": board_id, "content_sha256": _digest({"board": board, "detail": detail}), "message_ids": [row["message_id"] for row in messages], "messages": messages})
    return {"ok": True, "logged_in": True, "source_complete": True, "board_count": len(boards), "required_reply_count": replies, "unread_count": unread, "application_board_count": applications, "storefront_contract_candidate_count": storefront, "boards": sorted(output, key=lambda row: row["board_id"])}


def _cleanup(page: Any, browser: Any) -> bool:
    try: page_ok = page is None or bool(application_tick._close_owned_page(page))
    except Exception: page_ok = False
    try: getattr(getattr(browser, "_anicca_playwright_runtime", None), "stop", lambda: None)()
    except Exception: return False
    return page_ok


def _failed(error: str, logged_in: bool = False) -> dict[str, Any]:
    return {"ok": False, "logged_in": logged_in, "source_complete": False, "error": error}


def run_tick(*, state_path: Path = DEFAULT_STATE_PATH, browser_factory: Optional[Callable[[str], Any]] = None) -> dict[str, Any]:
    browser = page = None
    logged_in = False
    result = _failed("observer_unavailable")
    try:
        with application_tick.account_lock(Path(state_path).with_name("work-sync.json")):
            browser = (browser_factory or application_tick._default_browser_factory)(CDP_URL)
            page = application_tick._new_owned_page(browser)
            if not application_tick._production_account_ready(page):
                raise SourceFailure("account_unavailable")
            logged_in = True
            result = _snapshot(lambda path: _fetch(page, path))
    except SourceFailure as error:
        result = _failed(str(error), logged_in)
    except Exception as error:
        result = _failed("account_lock_busy" if type(error).__name__ == "_AccountLockBusy" else "observer_unavailable", logged_in)
    finally:
        if not _cleanup(page, browser):
            result = _failed("cleanup_failed", logged_in)
    return result


def main(argv: Optional[Sequence[str]] = None, *, output_stream: Any = None, browser_factory: Optional[Callable[[str], Any]] = None) -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--json", action="store_true", required=True)
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    args = parser.parse_args(argv)
    result = run_tick(state_path=Path(args.state_path), browser_factory=browser_factory)
    output = output_stream or sys.stdout
    output.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    output.flush()
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
