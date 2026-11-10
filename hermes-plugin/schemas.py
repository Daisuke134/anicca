"""Tool schemas shown to the model."""

_OBJECT = "object"

STATUS = {
    "name": "life_manager_status",
    "description": (
        "Show Life Manager's open commitments, overdue items, and habit streaks. "
        "Use this before advising the user what to do next."
    ),
    "parameters": {"type": _OBJECT, "properties": {}, "additionalProperties": False},
}

COMMIT = {
    "name": "life_manager_commit",
    "description": (
        "Record a task or habit the user agreed to. Habits need cadence daily or weekly. "
        "Tasks may set due_on as YYYY-MM-DD. Do not store passwords, tokens, or keys."
    ),
    "parameters": {
        "type": _OBJECT,
        "properties": {
            "text": {"type": "string", "description": "What the user will do, in their words."},
            "kind": {"type": "string", "enum": ["task", "habit"], "description": "task or habit."},
            "cadence": {
                "type": "string",
                "enum": ["daily", "weekly", "none"],
                "description": "Required for habits.",
            },
            "due_on": {"type": "string", "description": "Task due date, YYYY-MM-DD."},
        },
        "required": ["text"],
    },
}

COMPLETE = {
    "name": "life_manager_complete",
    "description": (
        "Mark a task done, or record that a habit was done today. "
        "Only call this after the user says the thing is done. ref is an id or unique text."
    ),
    "parameters": {
        "type": _OBJECT,
        "properties": {"ref": {"type": "string", "description": "Commitment id or unique text."}},
        "required": ["ref"],
    },
}

DROP = {
    "name": "life_manager_drop",
    "description": "Stop tracking a commitment the user dropped. ref is an id or unique text.",
    "parameters": {
        "type": _OBJECT,
        "properties": {"ref": {"type": "string"}},
        "required": ["ref"],
    },
}

DEFER = {
    "name": "life_manager_defer",
    "description": "Move an open task to a new due date (YYYY-MM-DD). Does not change habits.",
    "parameters": {
        "type": _OBJECT,
        "properties": {
            "ref": {"type": "string"},
            "due_on": {"type": "string", "description": "New due date, YYYY-MM-DD."},
        },
        "required": ["ref", "due_on"],
    },
}

CHECKIN = {
    "name": "life_manager_checkin",
    "description": (
        "Return the commitment board for a check-in. During a scheduled run this records "
        "the check-in and returns immediately, with no question for the user to answer inside the tool."
    ),
    "parameters": {"type": _OBJECT, "properties": {}, "additionalProperties": False},
}

ALL = (STATUS, COMMIT, COMPLETE, DROP, DEFER, CHECKIN)
