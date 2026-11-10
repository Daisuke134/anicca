"""Pure commitment and streak rules. No Hermes, disk, network, or clock reads."""

from __future__ import annotations

import copy
import re
from datetime import date, timedelta

_SPLIT = re.compile(r"[\n]+|(?<=[.!?])\s+")
_FRAME = re.compile(
    r"^(?:i\s+commit\s+to|i\s+promise\s+to|i\s+will|i'll)\s+(?P<body>.+?)\s*$",
    re.IGNORECASE,
)
_TIME = re.compile(
    r"\b(?:today|tonight|tomorrow|daily|every\s+day|every\s+morning|every\s+night|"
    r"each\s+day|every\s+week|weekly|this\s+week)\b|"
    r"\bby\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)
_SECRET = re.compile(
    r"(?i)\b(?:api[_ -]?key|token|password|secret|credential|sk-[a-z0-9])\b"
)
_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def clock():
    """Local calendar date. Tests replace this; the plugin never asks the network."""
    return date.today()


def blank_state():
    return {
        "version": 1,
        "commitments": [],
        "nudged_sessions": [],
        "last_checkin": None,
    }


def message_has_secret(text):
    return bool(_SECRET.search(text or ""))


def infer_cadence(text):
    blob = (text or "").lower()
    if re.search(r"every\s+week|\bweekly\b", blob):
        return "weekly"
    if re.search(r"every\s+day|every\s+morning|every\s+night|each\s+day|\bdaily\b", blob):
        return "daily"
    return None


def extract_statements(text, today):
    """High-confidence commitments only. Questions, refusals, and secrets yield nothing."""
    if not text or message_has_secret(text):
        return []
    found = []
    seen = set()
    for raw in _SPLIT.split(text.strip()):
        sentence = raw.strip()
        if not sentence or "?" in sentence:
            continue
        match = _FRAME.match(sentence.strip().rstrip("."))
        if not match:
            continue
        body = match.group("body").strip().rstrip(".")
        if re.match(r"(?i)^not\b", body):
            continue
        explicit = sentence.lower().startswith(("i commit to", "i promise to"))
        if not explicit and not _TIME.search(sentence):
            continue
        kind, cadence, due_on = _classify(sentence, today)
        cleaned = _clean_text(body)
        key = _norm(cleaned)
        if not key or key in seen:
            continue
        seen.add(key)
        found.append(
            {"text": cleaned, "kind": kind, "cadence": cadence, "due_on": due_on}
        )
    return found


def add_commitment(state, *, text, kind, cadence, due_on, source, today, max_open):
    state = _copy(state)
    text = _clean_text(text)
    if not text or message_has_secret(text):
        return state, None, False
    norm = _norm(text)
    for item in state["commitments"]:
        if item["status"] == "open" and _norm(item["text"]) == norm:
            return state, item, False
    open_count = sum(1 for item in state["commitments"] if item["status"] == "open")
    if open_count >= max_open:
        return state, None, False
    if kind not in ("task", "habit"):
        kind = "task"
    if kind == "habit":
        cadence = cadence if cadence in ("daily", "weekly") else (infer_cadence(text) or "daily")
        due_on = None
    else:
        cadence = None
    item = {
        "id": _new_id(state),
        "text": text,
        "kind": kind,
        "cadence": cadence,
        "status": "open",
        "due_on": due_on,
        "source": source,
        "created_on": today.isoformat(),
        "last_completed_on": None,
        "streak": 0,
        "best_streak": 0,
    }
    state["commitments"].append(item)
    return state, item, True


def complete(state, *, ref, today):
    state = _copy(state)
    item, err = _resolve(state, ref)
    if err:
        return state, {"ok": False, "error": err}
    if item["kind"] == "habit":
        last = _parse(item.get("last_completed_on"))
        stored = int(item.get("streak") or 0)
        base = visible_streak(item, today)
        if item.get("cadence") == "weekly":
            if last and _iso_week(last) == _iso_week(today):
                new_streak = stored
            elif last and _iso_week(last) == _previous_week(today):
                new_streak = base + 1
            else:
                new_streak = 1
        else:
            if last == today:
                new_streak = stored
            elif last == today - timedelta(days=1):
                new_streak = base + 1
            else:
                new_streak = 1
        item["streak"] = new_streak
        item["best_streak"] = max(int(item.get("best_streak") or 0), new_streak)
        item["last_completed_on"] = today.isoformat()
    else:
        item["status"] = "done"
        item["last_completed_on"] = today.isoformat()
    return state, {"ok": True, "commitment": public(item, today)}


def drop(state, *, ref, today):
    state = _copy(state)
    item, err = _resolve(state, ref)
    if err:
        return state, {"ok": False, "error": err}
    item["status"] = "dropped"
    return state, {"ok": True, "commitment": public(item, today)}


def defer(state, *, ref, due_on, today):
    state = _copy(state)
    item, err = _resolve(state, ref)
    if err:
        return state, {"ok": False, "error": err}
    if item["kind"] != "task":
        return state, {"ok": False, "error": "habits stay on their cadence; complete or drop them"}
    parsed = _parse(due_on)
    if parsed is None:
        return state, {"ok": False, "error": "due_on must be YYYY-MM-DD"}
    item["due_on"] = parsed.isoformat()
    return state, {"ok": True, "commitment": public(item, today)}


def board(state, today):
    overdue = []
    due_today = []
    open_items = []
    habits = []
    for item in state["commitments"]:
        if item["status"] != "open":
            continue
        view = public(item, today)
        open_items.append(view)
        if item["kind"] == "habit":
            habits.append(view)
        if view["overdue"]:
            overdue.append(view)
        elif view["due_today"]:
            due_today.append(view)
    return {
        "open": open_items,
        "overdue": overdue,
        "due_today": due_today,
        "habits": habits,
    }


def visible_streak(item, today):
    if item.get("kind") != "habit":
        return int(item.get("streak") or 0)
    last = _parse(item.get("last_completed_on"))
    stored = int(item.get("streak") or 0)
    if last is None:
        return 0
    if item.get("cadence") == "weekly":
        if _iso_week(last) in (_iso_week(today), _previous_week(today)):
            return stored
        return 0
    if last == today or last == today - timedelta(days=1):
        return stored
    return 0


def public(item, today):
    view = {
        "id": item["id"],
        "text": item["text"],
        "kind": item["kind"],
        "cadence": item.get("cadence"),
        "status": item["status"],
        "due_on": item.get("due_on"),
        "source": item.get("source"),
        "created_on": item.get("created_on"),
        "last_completed_on": item.get("last_completed_on"),
        "streak": visible_streak(item, today) if item["status"] == "open" else int(item.get("streak") or 0),
        "best_streak": int(item.get("best_streak") or 0),
        "overdue": False,
        "due_today": False,
    }
    if item["status"] != "open":
        return view
    if item["kind"] == "habit":
        created = _parse(item.get("created_on")) or today
        last = _parse(item.get("last_completed_on"))
        if item.get("cadence") == "weekly":
            view["due_today"] = last is None or _iso_week(last) != _iso_week(today)
            view["overdue"] = created < _week_start(today) and (
                last is None or _iso_week(last) < _previous_week(today)
            )
        else:
            view["due_today"] = last != today
            view["overdue"] = created < today and (last is None or last < today - timedelta(days=1))
    else:
        due = _parse(item.get("due_on"))
        if due == today:
            view["due_today"] = True
        elif due is not None and due < today:
            view["overdue"] = True
    return view


def render_context(snapshot, captured, session_id, nudged):
    if not snapshot["open"] and not captured:
        return None, list(nudged)
    lines = ["Life Manager board (stored only in this Hermes profile):"]
    if snapshot["overdue"]:
        lines.append("Overdue: " + _fmt(snapshot["overdue"]))
    if snapshot["due_today"]:
        lines.append("Due today: " + _fmt(snapshot["due_today"]))
    if snapshot["habits"]:
        bits = [
            f"{habit['text']} streak {habit['streak']} best {habit['best_streak']}"
            for habit in snapshot["habits"]
        ]
        lines.append("Habits: " + "; ".join(bits))
    later = [
        item for item in snapshot["open"]
        if not item["overdue"] and not item["due_today"] and item["kind"] != "habit"
    ]
    if later:
        lines.append("Open: " + _fmt(later))
    nudged = list(nudged)
    if snapshot["overdue"] and session_id and session_id not in nudged:
        lines.append(
            "Name the overdue item once and ask whether to do it, defer it, or drop it. "
            "Do not mark it complete unless the user says it is done."
        )
        nudged.append(session_id)
        nudged = nudged[-32:]
    if captured:
        names = ", ".join(item["text"] for item in captured)
        lines.append(
            f"Just recorded from the user's words: {names}. Confirm the wording in one sentence."
        )
    return "\n".join(lines), nudged


def _classify(sentence, today):
    blob = sentence.lower()
    cadence = infer_cadence(blob)
    if cadence:
        return "habit", cadence, None
    due_on = None
    if re.search(r"\btomorrow\b", blob):
        due_on = (today + timedelta(days=1)).isoformat()
    elif re.search(r"\b(?:today|tonight)\b", blob):
        due_on = today.isoformat()
    else:
        match = re.search(
            r"\bby\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
            blob,
        )
        if match:
            target = _WEEKDAYS[match.group(1)]
            delta = (target - today.weekday()) % 7
            due_on = (today + timedelta(days=delta)).isoformat()
        elif re.search(r"\bthis\s+week\b", blob):
            delta = (6 - today.weekday()) % 7
            due_on = (today + timedelta(days=delta)).isoformat()
    return "task", None, due_on


def _fmt(items):
    return "; ".join(f"{item['text']} ({item['id']})" for item in items)


def _clean_text(text):
    return " ".join((text or "").split())[:240].strip()


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _new_id(state):
    return f"lm-{len(state['commitments']) + 1:04d}"


def _copy(state):
    return copy.deepcopy(state)


def _parse(value):
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _iso_week(day):
    return day.isocalendar()[:2]


def _week_start(day):
    return day - timedelta(days=day.weekday())


def _previous_week(day):
    return _iso_week(_week_start(day) - timedelta(days=1))


def _resolve(state, ref, statuses=("open",)):
    ref = (ref or "").strip()
    if not ref:
        return None, "missing ref"
    items = [item for item in state["commitments"] if item["status"] in statuses]
    exact = [item for item in items if item["id"] == ref]
    if len(exact) == 1:
        return exact[0], None
    by_text = [item for item in items if _norm(item["text"]) == _norm(ref)]
    if len(by_text) == 1:
        return by_text[0], None
    prefix = [item for item in items if item["id"].startswith(ref)]
    if len(prefix) == 1:
        return prefix[0], None
    if len(prefix) > 1 or len(by_text) > 1:
        return None, "ambiguous ref"
    return None, "not found"
