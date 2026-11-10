"""Tool, hook, and command behavior on top of the pure engine."""

from __future__ import annotations

import json

try:
    from . import engine
except ImportError:  # loaded as a plain module in unit tests
    import engine

TOOLS = (
    "life_manager_status",
    "life_manager_commit",
    "life_manager_complete",
    "life_manager_drop",
    "life_manager_defer",
    "life_manager_checkin",
)

_CADENCE = {
    "everyday": "daily",
    "daily": "daily",
    "weekly": "weekly",
    "none": "none",
}

USAGE = "Usage: /commitments status | add <text> | done <ref> | drop <ref> | defer <ref> <YYYY-MM-DD>"
CLI_USAGE = "Usage: hermes life-manager status | add <text> | done <ref> | drop <ref> | defer <ref> <YYYY-MM-DD> | checkin"


class CtxStore:
    """Profile-scoped plugin state. Never touches the install directory."""

    KEY = "board"

    def __init__(self, ctx):
        self.ctx = ctx

    def load(self):
        raw = self.ctx.state.get(self.KEY, None)
        if not isinstance(raw, dict) or "commitments" not in raw:
            return engine.blank_state()
        return raw

    def save(self, data):
        self.ctx.state.set(self.KEY, data)


def ingest_user_message(store, message, *, today, session_id, capture=True, max_open=30):
    state = store.load()
    original_nudged = list(state.get("nudged_sessions") or [])
    captured = []
    store_words = capture and not engine.message_has_secret(message or "")
    if store_words:
        for spec in engine.extract_statements(message, today):
            state, item, created = engine.add_commitment(
                state,
                text=spec["text"],
                kind=spec["kind"],
                cadence=spec["cadence"],
                due_on=spec["due_on"],
                source="stated",
                today=today,
                max_open=max_open,
            )
            if created and item:
                captured.append(item)
    snapshot = engine.board(state, today)
    context, nudged = engine.render_context(snapshot, captured, session_id or "", original_nudged)
    state["nudged_sessions"] = nudged
    if captured or nudged != original_nudged:
        store.save(state)
    return context


def hook_context(store, message, *, session_id, today, capture, max_open):
    text = ingest_user_message(
        store,
        message,
        today=today,
        session_id=session_id,
        capture=capture,
        max_open=max_open,
    )
    if not text:
        return None
    return {"context": text}


def tool_commit(store, args, *, today, max_open=30):
    text = " ".join(str(args.get("text") or "").split())
    if not text:
        return {"ok": False, "error": "text is required"}
    if engine.message_has_secret(text):
        return {"ok": False, "error": "refusing to store credential-like text"}
    kind = args.get("kind")
    cadence = _CADENCE.get(str(args.get("cadence") or "").strip().lower())
    due = args.get("due_on") or None
    spec = None
    extracted = engine.extract_statements(f"I commit to {text}", today)
    if extracted:
        spec = extracted[0]
    if kind not in ("task", "habit"):
        kind = spec["kind"] if spec else "task"
    if kind == "habit":
        if cadence not in ("daily", "weekly"):
            cadence = (spec or {}).get("cadence")
        due = None
    else:
        cadence = None
        if not args.get("due_on") and spec:
            due = spec.get("due_on")
    state = store.load()
    state, item, created = engine.add_commitment(
        state,
        text=text,
        kind=kind,
        cadence=cadence,
        due_on=due,
        source="tool",
        today=today,
        max_open=max_open,
    )
    store.save(state)
    if not item:
        return {"ok": False, "error": "not stored"}
    return {"ok": True, "created": created, "commitment": engine.public(item, today)}


def tool_complete(store, args, *, today):
    state, result = engine.complete(store.load(), ref=_ref(args), today=today)
    if result.get("ok"):
        store.save(state)
    return result


def tool_drop(store, args, *, today):
    state, result = engine.drop(store.load(), ref=_ref(args), today=today)
    if result.get("ok"):
        store.save(state)
    return result


def tool_defer(store, args, *, today):
    state, result = engine.defer(
        store.load(), ref=_ref(args), due_on=args.get("due_on"), today=today
    )
    if result.get("ok"):
        store.save(state)
    return result


def tool_status(store, *, today):
    snapshot = engine.board(store.load(), today)
    return {"ok": True, **snapshot, "open_count": len(snapshot["open"])}


def tool_checkin(store, *, today, unattended, execution_id):
    state = store.load()
    snapshot = engine.board(state, today)
    if unattended:
        state["last_checkin"] = {
            "on": today.isoformat(),
            "execution_id": execution_id,
            "unattended": True,
        }
        store.save(state)
    return {
        "ok": True,
        "unattended": bool(unattended),
        "overdue": snapshot["overdue"],
        "due_today": snapshot["due_today"],
        "habits": snapshot["habits"],
        "open_count": len(snapshot["open"]),
    }


def handle_tool(store, name, args, *, today, unattended=False, execution_id=None, max_open=30):
    try:
        args = args or {}
        if name == "life_manager_commit":
            payload = tool_commit(store, args, today=today, max_open=max_open)
        elif name == "life_manager_complete":
            payload = tool_complete(store, args, today=today)
        elif name == "life_manager_drop":
            payload = tool_drop(store, args, today=today)
        elif name == "life_manager_defer":
            payload = tool_defer(store, args, today=today)
        elif name == "life_manager_status":
            payload = tool_status(store, today=today)
        elif name == "life_manager_checkin":
            payload = tool_checkin(
                store, today=today, unattended=unattended, execution_id=execution_id
            )
        else:
            payload = {"ok": False, "error": "unknown tool"}
        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return json.dumps({"ok": False, "error": "internal error"})


def normalize_tool_request(tool_name, args, **kwargs):
    if tool_name not in TOOLS or not isinstance(args, dict):
        return None
    new = dict(args)
    changed = False
    if isinstance(new.get("text"), str):
        collapsed = " ".join(new["text"].split())
        if collapsed != new["text"]:
            new["text"] = collapsed
            changed = True
    cadence = new.get("cadence")
    if isinstance(cadence, str):
        mapped = _CADENCE.get(cadence.strip().lower())
        if mapped and mapped != cadence:
            new["cadence"] = mapped
            changed = True
    if not changed:
        return None
    return {
        "args": new,
        "source": "life-manager",
        "reason": "normalize commitment fields",
    }


def slash(store, raw, *, today, max_open=30):
    text = (raw or "").strip()
    if not text or text == "status":
        return format_status(store, today)
    parts = text.split(maxsplit=1)
    cmd, rest = parts[0], parts[1] if len(parts) > 1 else ""
    if cmd == "add":
        if not rest:
            return USAGE
        result = tool_commit(store, {"text": rest}, today=today, max_open=max_open)
        if not result["ok"]:
            return result["error"]
        return f"Recorded: {result['commitment']['text']} ({result['commitment']['id']})"
    if cmd == "done":
        result = tool_complete(store, {"ref": rest}, today=today)
        return _ack(result)
    if cmd == "drop":
        result = tool_drop(store, {"ref": rest}, today=today)
        return _ack(result)
    if cmd == "defer":
        bits = rest.split(maxsplit=1)
        if len(bits) != 2:
            return USAGE
        result = tool_defer(store, {"ref": bits[0], "due_on": bits[1]}, today=today)
        return _ack(result)
    return USAGE


def cli_dispatch(store, argv, *, today, write, max_open=30):
    argv = list(argv or [])
    if not argv or argv[0] in ("-h", "--help", "help"):
        write(CLI_USAGE)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "status":
        write(format_status(store, today))
        return 0
    if cmd == "add":
        result = tool_commit(store, {"text": " ".join(rest)}, today=today, max_open=max_open)
    elif cmd == "done":
        result = tool_complete(store, {"ref": " ".join(rest)}, today=today)
    elif cmd == "drop":
        result = tool_drop(store, {"ref": " ".join(rest)}, today=today)
    elif cmd == "defer":
        if len(rest) < 2:
            write(CLI_USAGE)
            return 0
        result = tool_defer(store, {"ref": rest[0], "due_on": rest[1]}, today=today)
    elif cmd == "checkin":
        result = tool_checkin(store, today=today, unattended=True, execution_id="cli")
    else:
        write(CLI_USAGE)
        return 0
    write(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


def format_status(store, today):
    snapshot = engine.board(store.load(), today)
    if not snapshot["open"]:
        return "Life Manager: nothing open."
    lines = ["Life Manager"]
    for label, key in (("Overdue", "overdue"), ("Due today", "due_today"), ("Habits", "habits")):
        if snapshot[key]:
            lines.append(label + ": " + ", ".join(item["text"] for item in snapshot[key]))
    later = [
        item for item in snapshot["open"]
        if not item["overdue"] and not item["due_today"] and item["kind"] != "habit"
    ]
    if later:
        lines.append("Open: " + ", ".join(item["text"] for item in later))
    return "\n".join(lines)


def _ref(args):
    return str(args.get("ref") or args.get("id") or args.get("text") or "")


def _ack(result):
    if not result.get("ok"):
        return result.get("error") or "not stored"
    item = result["commitment"]
    return f"{item['status']}: {item['text']} ({item['id']})"
