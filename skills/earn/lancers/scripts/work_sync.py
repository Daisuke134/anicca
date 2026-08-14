#!/usr/bin/env python3
"""Bounded, read-only canonical Lancers sales-source observer."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
from typing import Any, Callable, Mapping, Optional, Sequence
from urllib.parse import quote, urlencode

HERE = Path(__file__).resolve().parent
SKILLS_ROOT = HERE.parents[2]
AGENT_RUNNER = SKILLS_ROOT / "agent-runner" / "agent_runner.py"
REPLY_SCHEMA = SKILLS_ROOT / "gig-work" / "schemas" / "reply_composition.schema.json"


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
TICK_TIMEOUT_SECONDS = 120


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


def _sales_state(path: Path) -> dict[str, Any]:
    if not path.exists(): return {"handled": [], "pending": None}
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError): raise SourceFailure("sales_state_invalid") from None
    if not isinstance(value, Mapping) or set(value) != {"handled", "pending"} or not isinstance(value["handled"], list) or any(not isinstance(item, str) for item in value["handled"]) or value["pending"] is not None and not isinstance(value["pending"], Mapping):
        raise SourceFailure("sales_state_invalid")
    return {"handled": list(value["handled"]), "pending": value["pending"]}


def _write_sales_state(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True); path.parent.chmod(0o700)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":")); handle.write("\n")
        os.replace(temporary, path); path.chmod(0o600)
    finally:
        try: os.unlink(temporary)
        except FileNotFoundError: pass


def _compose_reply(board: Mapping[str, Any], messages: Sequence[Mapping[str, Any]], state_path: Path) -> str:
    conversation = []
    for row in sorted(messages, key=lambda item: int(_id(item.get("id"))))[-20:]:
        body = row.get("description")
        if not isinstance(body, str) or not body.strip() or len(body) > 10000: raise SourceFailure("provider_response_invalid")
        conversation.append({"side": "buyer" if row.get("is_required_reply") is True else "seller", "body": body[:4000]})
    prompt = """Lancersの購入前会話へ、今すぐ送信できる日本語返信を1件作る。Coconalaで実運用する返信規則をそのまま使う。\n必須:\n- 最新のbuyer発言の質問・依頼へ冒頭から直接答え、明示された質問を省略しない。\n- 会話と案件にある検証済み事実だけを使う。価格、納期、実績、対応能力を作らない。答えに必要な未確定事項だけ質問を1つまで含める。\n- 最新発言への回答だけで完結するならCTA、見積り、納期、質問を自発的に追加しない。購入を催促しない。\n- 動画/animation制作、物理/現地作業、必須の顔・声・電話/live call、AI明示禁止、違法危険、未保有の法的資格、虚偽属性が依頼全体に必須なら、代替提案や質問を付けず正直かつ丁寧に辞退する。フィギュアの塗装・リペイント・カスタムは物理作業である。辞退時は「対応できません」を明言し、実績がないという説明だけで終えない。単語が出ただけ、任意作業、難しさ、低予算、実績不足では辞退しない。\n- 外部連絡先、内部用語、未依頼の成果物を含めない。1000文字以内。schemaどおりreply_bodyだけを返す。\nCONTEXT:\n""" + json.dumps({"board": {"title": board.get("title"), "description": board.get("description")}, "conversation": conversation}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with tempfile.TemporaryDirectory(prefix=".lancers-reply-", dir=state_path.parent) as temporary:
        evidence = Path(temporary) / "evidence"
        completed = subprocess.run([sys.executable, str(AGENT_RUNNER), "--task-class", "composition-agent", "--prompt-stdin", "--schema", str(REPLY_SCHEMA), "--evidence-dir", str(evidence), "--task-label", "lancers-sales-reply", "--loop", "lancers-sales", "--workdir", str(SKILLS_ROOT.parent)], input=prompt, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90, check=False)
        if completed.returncode != 0: raise SourceFailure("reply_composer_failed")
        try:
            summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8")); result_path = Path(str(summary["result_path"])).resolve(); result_path.relative_to(evidence.resolve())
            result = json.loads(result_path.read_text(encoding="utf-8")); body = result.get("reply_body") if isinstance(result, Mapping) else None
        except (OSError, KeyError, TypeError, ValueError): raise SourceFailure("reply_composer_failed") from None
    if not isinstance(body, str) or not body.strip() or len(body.strip()) > 1000: raise SourceFailure("reply_contract_invalid")
    return body.strip()


def _verified_proposals(state_path: Path) -> set[str]:
    ledger = Path(state_path).with_name("marketplace-ledger.sqlite3")
    if not ledger.is_file(): raise SourceFailure("application_receipts_unavailable")
    connection = None
    try:
        connection = sqlite3.connect(ledger.resolve().as_uri() + "?mode=ro", uri=True)
        rows = connection.execute("SELECT external_id FROM marketplace_events WHERE platform=? AND event_type=?", ("lancers", "application_verified")).fetchall()
        values = [_id(row[0]) for row in rows]
    except (IndexError, TypeError, SourceFailure, sqlite3.Error, OSError):
        raise SourceFailure("application_receipts_unavailable") from None
    finally:
        if connection is not None:
            try: connection.close()
            except sqlite3.Error: pass
    if len(values) != len(set(values)): raise SourceFailure("application_receipts_conflict")
    return set(values)


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


def _message_rows(fetch: Callable[[str], Any], board_id: str) -> list[Mapping[str, Any]]:
    def check(message: Mapping[str, Any]) -> tuple[str, str]:
        message_id = _id(message.get("id"))
        if _id(message.get("board_id")) != board_id or not isinstance(message.get("is_required_reply"), bool) or "send_user" not in message or "modified" not in message: raise SourceFailure("provider_response_invalid")
        _id(message["modified"]); return message_id, message_id
    route = lambda cursor: f"/v1/message_api/boards/{quote(board_id, safe='')}/messages?{urlencode({'limit': 20, **({'message_id': cursor, 'direction': 'prev'} if cursor else {})})}"
    return _pages(fetch, route, check, MAX_MESSAGE_PAGES, ("duplicate_message_id", "message_cursor_stalled", "message_page_limit_reached"))


def _messages(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    return sorted(({"message_id": _id(row["id"]), "content_sha256": _digest(row)} for row in rows), key=lambda row: row["message_id"])


def _post_reply(page: Any, board_id: str, body: str) -> str:
    value = page.evaluate("""async ({path, body}) => { const form = new FormData(); form.append("description", body); form.append("rich_description", body); const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 20000); try { const response = await fetch(path, {method:"POST", credentials:"same-origin", body:form, signal:controller.signal}); const text = await response.text(); if (!response.ok || text.length > 1048576) return {ok:false}; let parsed={}; try { parsed=JSON.parse(text); } catch (_) {} return {ok:true, body:parsed}; } catch (_) { return {ok:false}; } finally { clearTimeout(timer); } }""", {"path": f"/v1/message_api/boards/{quote(board_id, safe='')}/messages", "body": body})
    if not isinstance(value, Mapping) or value.get("ok") is not True: raise SourceFailure("reply_submission_uncertain")
    response = value.get("body")
    if isinstance(response, Mapping) and isinstance(response.get("data"), Mapping): response = response["data"]
    if not isinstance(response, Mapping): raise SourceFailure("reply_submission_uncertain")
    return _id(response.get("id"))


def _readback(rows: Sequence[Mapping[str, Any]], board_id: str, body: str, provider_id: Optional[str]) -> Optional[str]:
    for row in rows:
        if _id(row.get("board_id")) == board_id and row.get("description") == body:
            message_id = _id(row.get("id"))
            if provider_id is None or provider_id == message_id: return message_id
    return None


def _sales_action(page: Any, state_path: Path, boards: Sequence[tuple[Mapping[str, Any], Mapping[str, Any], Sequence[Mapping[str, Any]]]]) -> dict[str, Any]:
    path = state_path.with_name("sales.json"); state = _sales_state(path); pending = state["pending"]
    if pending is not None:
        try: board_id, body = _id(pending.get("board_id")), str(pending["reply_body"]); provider_id = pending.get("provider_message_id")
        except (KeyError, TypeError, SourceFailure): raise SourceFailure("sales_state_invalid") from None
        rows = next((rows for board, _detail, rows in boards if _id(board.get("id")) == board_id), None)
        if rows is None: rows = _message_rows(lambda route: _fetch(page, route), board_id)
        verified = _readback(rows, board_id, body, provider_id if isinstance(provider_id, str) else None)
        if verified is None: return {"status": "reply_uncertain", "board_id": board_id, "content_sha256": _digest(body)}
        event_key = str(pending.get("event_key")); handled = list(dict.fromkeys([*state["handled"], event_key]))[-1000:]
        _write_sales_state(path, {"handled": handled, "pending": None})
        return {"status": "reply_verified", "board_id": board_id, "provider_message_id": verified, "content_sha256": _digest(body)}

    candidate = next(((board, detail, rows) for board, detail, rows in boards if board.get("is_required_reply") is True and rows), None)
    if candidate is None: return {"status": "no_reply_required"}
    board, _detail, rows = candidate; latest = max(rows, key=lambda row: int(_id(row.get("id"))))
    if latest.get("is_required_reply") is not True: return {"status": "seller_last"}
    board_id, message_id = _id(board.get("id")), _id(latest.get("id")); event_key = f"{board_id}:{message_id}"
    if event_key in state["handled"]: return {"status": "already_handled", "board_id": board_id}
    body = _compose_reply(board, rows, state_path)
    pending = {"board_id": board_id, "event_key": event_key, "reply_body": body, "content_sha256": _digest(body), "provider_message_id": None}
    _write_sales_state(path, {"handled": state["handled"], "pending": pending})
    provider_id = _post_reply(page, board_id, body); pending["provider_message_id"] = provider_id
    _write_sales_state(path, {"handled": state["handled"], "pending": pending})
    readback_rows = _message_rows(lambda route: _fetch(page, route), board_id)
    verified = _readback(readback_rows, board_id, body, provider_id)
    if verified is None: return {"status": "reply_uncertain", "board_id": board_id, "provider_message_id": provider_id, "content_sha256": _digest(body)}
    handled = list(dict.fromkeys([*state["handled"], event_key]))[-1000:]
    _write_sales_state(path, {"handled": handled, "pending": None})
    return {"status": "reply_verified", "board_id": board_id, "provider_message_id": verified, "content_sha256": _digest(body)}


def _snapshot(fetch: Callable[[str], Any], verified_proposals: set[str], private_boards: Optional[list[Any]] = None) -> dict[str, Any]:
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
        raw_messages = _message_rows(fetch, board_id); messages = _messages(raw_messages)
        if private_boards is not None: private_boards.append((board, detail, raw_messages))
        replies += int(board["is_required_reply"]); unread += board["unread_count"]
        applications += int(proposal in verified_proposals); storefront += int(contract is not None)
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
        verified_proposals = _verified_proposals(Path(state_path))
        with application_tick.account_lock(Path(state_path).with_name("work-sync.json")):
            browser = (browser_factory or application_tick._default_browser_factory)(CDP_URL)
            page = application_tick._new_owned_page(browser)
            if not application_tick._production_account_ready(page):
                raise SourceFailure("account_unavailable")
            logged_in = True
            private_boards: list[Any] = []
            result = _snapshot(lambda path: _fetch(page, path), verified_proposals, private_boards)
            result["reply_action"] = _sales_action(page, Path(state_path), private_boards)
    except SourceFailure as error:
        result = _failed(str(error), logged_in)
    except Exception as error:
        result = _failed("account_lock_busy" if type(error).__name__ == "_AccountLockBusy" else "observer_unavailable", logged_in)
    finally:
        if not _cleanup(page, browser):
            result = _failed("cleanup_failed", logged_in)
    return result


def _watchdog(command: Sequence[str], timeout: float) -> dict[str, Any]:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_group(process)
        try:
            process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
        return _failed("tick_timeout")
    _kill_group(process)
    if stderr or len(stdout.splitlines()) != 1:
        return _failed("worker_failed")
    try: result = json.loads(stdout)
    except (TypeError, ValueError): return _failed("worker_failed")
    if not isinstance(result, Mapping) or type(result.get("ok")) is not bool:
        return _failed("worker_failed")
    if process.returncode != (0 if result["ok"] else 1):
        return _failed("worker_failed")
    return result


def _kill_group(process: subprocess.Popen[str]) -> None:
    try: os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError: return
    try: process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        try: process.wait(timeout=1)
        except subprocess.TimeoutExpired: pass


def main(argv: Optional[Sequence[str]] = None, *, output_stream: Any = None, browser_factory: Optional[Callable[[str], Any]] = None, worker_command: Optional[Sequence[str]] = None, timeout: float = TICK_TIMEOUT_SECONDS) -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--json", action="store_true", required=True)
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH))
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    result = run_tick(state_path=Path(args.state_path), browser_factory=browser_factory) if args.worker else _watchdog(worker_command or [sys.executable, str(Path(__file__).resolve()), "--worker", "--json", "--state-path", args.state_path], timeout)
    output = output_stream or sys.stdout
    output.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    output.flush()
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
