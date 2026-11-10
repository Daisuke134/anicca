"""Behavior of the Life Manager Hermes plugin, without a Hermes install."""

from __future__ import annotations

import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import engine  # noqa: E402
import runtime  # noqa: E402


TODAY = date(2026, 11, 10)  # Tuesday


class MemoryStore:
    def __init__(self):
        self.data = engine.blank_state()

    def load(self):
        return self.data

    def save(self, data):
        self.data = data


class ExtractTests(unittest.TestCase):
    def test_explicit_commit_tomorrow_is_a_task(self):
        found = engine.extract_statements("I commit to ship the essay tomorrow.", TODAY)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["kind"], "task")
        self.assertEqual(found[0]["due_on"], "2026-11-11")
        self.assertIn("ship the essay", found[0]["text"])

    def test_daily_habit_from_ill_with_time_cue(self):
        found = engine.extract_statements("I'll meditate every morning.", TODAY)
        self.assertEqual(found[0]["kind"], "habit")
        self.assertEqual(found[0]["cadence"], "daily")

    def test_will_without_time_cue_is_ignored(self):
        self.assertEqual(engine.extract_statements("I will think about it.", TODAY), [])

    def test_question_and_negation_are_ignored(self):
        self.assertEqual(engine.extract_statements("Will I meditate tomorrow?", TODAY), [])
        self.assertEqual(engine.extract_statements("I will not skip the walk today.", TODAY), [])

    def test_secretish_message_is_not_stored(self):
        store = MemoryStore()
        context = runtime.ingest_user_message(
            store,
            "I commit to paste the api key tomorrow.",
            today=TODAY,
            session_id="s1",
        )
        self.assertEqual(store.load()["commitments"], [])
        self.assertIsNone(context)


class StateTests(unittest.TestCase):
    def test_duplicate_open_commitment_is_not_duplicated(self):
        store = MemoryStore()
        runtime.ingest_user_message(
            store, "I commit to ship the essay tomorrow.", today=TODAY, session_id="s"
        )
        runtime.ingest_user_message(
            store, "I commit to ship the essay tomorrow.", today=TODAY, session_id="s"
        )
        self.assertEqual(len(store.load()["commitments"]), 1)

    def test_daily_streak_grows_then_breaks(self):
        state = engine.blank_state()
        state, item, created = engine.add_commitment(
            state,
            text="meditate",
            kind="habit",
            cadence="daily",
            due_on=None,
            source="tool",
            today=TODAY,
            max_open=30,
        )
        self.assertTrue(created)
        state, done = engine.complete(state, ref=item["id"], today=TODAY)
        self.assertTrue(done["ok"])
        self.assertEqual(done["commitment"]["streak"], 1)
        next_day = date(2026, 11, 11)
        state, done = engine.complete(state, ref=item["id"], today=next_day)
        self.assertEqual(done["commitment"]["streak"], 2)
        self.assertEqual(done["commitment"]["best_streak"], 2)
        later = date(2026, 11, 13)
        board = engine.board(state, later)
        habit = board["habits"][0]
        self.assertEqual(habit["streak"], 0)
        self.assertEqual(habit["best_streak"], 2)
        self.assertTrue(habit["overdue"])

    def test_weekly_streak_same_week_does_not_increment(self):
        state = engine.blank_state()
        state, item, _ = engine.add_commitment(
            state,
            text="review finances",
            kind="habit",
            cadence="weekly",
            due_on=None,
            source="tool",
            today=TODAY,
            max_open=30,
        )
        state, first = engine.complete(state, ref=item["id"], today=TODAY)
        state, second = engine.complete(state, ref=item["id"], today=date(2026, 11, 12))
        self.assertEqual(first["commitment"]["streak"], 1)
        self.assertEqual(second["commitment"]["streak"], 1)
        state, third = engine.complete(state, ref=item["id"], today=date(2026, 11, 17))
        self.assertEqual(third["commitment"]["streak"], 2)

    def test_task_due_today_and_overdue(self):
        state = engine.blank_state()
        state, _, _ = engine.add_commitment(
            state,
            text="call the clinic",
            kind="task",
            cadence=None,
            due_on="2026-11-10",
            source="tool",
            today=TODAY,
            max_open=30,
        )
        state, _, _ = engine.add_commitment(
            state,
            text="file the receipt",
            kind="task",
            cadence=None,
            due_on="2026-11-09",
            source="tool",
            today=TODAY,
            max_open=30,
        )
        board = engine.board(state, TODAY)
        self.assertEqual([item["text"] for item in board["due_today"]], ["call the clinic"])
        self.assertEqual([item["text"] for item in board["overdue"]], ["file the receipt"])

    def test_new_habit_today_is_due_not_overdue(self):
        state = engine.blank_state()
        state, _, _ = engine.add_commitment(
            state,
            text="meditate",
            kind="habit",
            cadence="daily",
            due_on=None,
            source="stated",
            today=TODAY,
            max_open=30,
        )
        board = engine.board(state, TODAY)
        self.assertEqual(board["habits"][0]["due_today"], True)
        self.assertEqual(board["habits"][0]["overdue"], False)
        self.assertEqual(board["overdue"], [])

    def test_drop_and_ambiguous_prefix(self):
        state = engine.blank_state()
        state, a, _ = engine.add_commitment(
            state, text="alpha walk", kind="task", cadence=None, due_on=None,
            source="tool", today=TODAY, max_open=30,
        )
        state, b, _ = engine.add_commitment(
            state, text="alpha stretch", kind="task", cadence=None, due_on=None,
            source="tool", today=TODAY, max_open=30,
        )
        self.assertTrue(a["id"] != b["id"])
        shared = a["id"][:2]
        _, ambiguous = engine.drop(state, ref=shared, today=TODAY)
        self.assertFalse(ambiguous["ok"])
        state, result = engine.drop(state, ref=a["id"], today=TODAY)
        self.assertTrue(result["ok"])
        self.assertEqual(result["commitment"]["status"], "dropped")
        open_items = [item for item in state["commitments"] if item["status"] == "open"]
        self.assertEqual(len(open_items), 1)


class InterventionTests(unittest.TestCase):
    def test_context_names_overdue_once_per_session(self):
        store = MemoryStore()
        runtime.tool_commit(
            store,
            {"text": "file the receipt", "kind": "task", "due_on": "2026-11-09"},
            today=TODAY,
        )
        first = runtime.ingest_user_message(store, "what is next?", today=TODAY, session_id="sess")
        second = runtime.ingest_user_message(store, "still here", today=TODAY, session_id="sess")
        self.assertIn("file the receipt", first)
        self.assertIn("Name the overdue item once", first)
        self.assertIn("file the receipt", second)
        self.assertNotIn("Name the overdue item once", second)

    def test_empty_board_injects_nothing(self):
        store = MemoryStore()
        self.assertIsNone(
            runtime.ingest_user_message(store, "hello", today=TODAY, session_id="s")
        )

    def test_checkin_unattended_records_and_does_not_ask(self):
        store = MemoryStore()
        runtime.tool_commit(
            store, {"text": "meditate every morning", "kind": "habit", "cadence": "daily"}, today=TODAY
        )
        report = runtime.tool_checkin(
            store, today=TODAY, unattended=True, execution_id="exec-1"
        )
        self.assertTrue(report["ok"])
        self.assertTrue(report["unattended"])
        self.assertNotIn("prompt", report)
        self.assertEqual(store.load()["last_checkin"]["execution_id"], "exec-1")
        self.assertEqual(report["due_today"][0]["text"], "meditate every morning")

    def test_middleware_normalizes_cadence_and_whitespace(self):
        rewritten = runtime.normalize_tool_request(
            "life_manager_commit",
            {"text": "  stretch   ", "cadence": "everyday"},
        )
        self.assertEqual(rewritten["args"]["text"], "stretch")
        self.assertEqual(rewritten["args"]["cadence"], "daily")
        self.assertIsNone(runtime.normalize_tool_request("life_manager_status", {}))

    def test_handlers_return_json_and_reject_bad_input(self):
        store = MemoryStore()
        bad = json.loads(runtime.handle_tool(store, "life_manager_commit", {}, today=TODAY))
        self.assertFalse(bad["ok"])
        good = json.loads(
            runtime.handle_tool(
                store,
                "life_manager_commit",
                {"text": "walk today", "kind": "task"},
                today=TODAY,
            )
        )
        self.assertTrue(good["ok"])
        status = json.loads(runtime.handle_tool(store, "life_manager_status", {}, today=TODAY))
        self.assertEqual(status["due_today"][0]["text"], "walk today")
        missing = json.loads(
            runtime.handle_tool(store, "life_manager_complete", {"ref": "nope"}, today=TODAY)
        )
        self.assertFalse(missing["ok"])

    def test_slash_and_cli_do_not_prompt(self):
        store = MemoryStore()
        created = runtime.slash(store, "add ship the essay tomorrow", today=TODAY)
        self.assertIn("ship the essay", created)
        usage = runtime.slash(store, "nope", today=TODAY)
        self.assertIn("Usage", usage)
        lines = []
        code = runtime.cli_dispatch(
            store, ["status"], today=TODAY, write=lines.append
        )
        self.assertEqual(code, 0)
        self.assertTrue(any("ship the essay" in line for line in lines))
        missing = runtime.cli_dispatch(store, [], today=TODAY, write=lines.append)
        self.assertEqual(missing, 0)
        self.assertTrue(any("Usage" in line for line in lines))


class WiringTests(unittest.TestCase):
    def test_registered_hook_records_a_statement(self):
        recorded = {"hooks": {}}

        class State:
            def __init__(self):
                self.data = {}

            def get(self, key, default=None):
                return self.data.get(key, default)

            def set(self, key, value):
                self.data[key] = value

        class Ctx:
            state = State()

            def register_tool(self, name, *args, **kwargs):
                return None

            def register_hook(self, hook_name, callback, *args, **kwargs):
                recorded["hooks"][hook_name] = callback

            def register_middleware(self, kind, callback):
                return None

            def register_command(self, *args, **kwargs):
                return None

            def register_cli_command(self, *args, **kwargs):
                return None

            def register_skill(self, *args, **kwargs):
                return None

            def register_automation_blueprint(self, *args, **kwargs):
                return None

            def get_config(self, key, default=None):
                return default

            def current_cron_execution(self):
                return None

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "life_manager_plugin_wire",
            ROOT / "__init__.py",
            submodule_search_locations=[str(ROOT)],
        )
        module = importlib.util.module_from_spec(spec)
        module.__path__ = [str(ROOT)]
        sys.modules["life_manager_plugin_wire"] = module
        spec.loader.exec_module(module)
        module.register(Ctx())
        result = recorded["hooks"]["pre_llm_call"](
            user_message="I commit to ship the essay tomorrow.",
            session_id="wire",
        )
        self.assertIn("context", result)
        self.assertIn("ship the essay", result["context"])


class ManifestTests(unittest.TestCase):
    def test_register_matches_manifest(self):
        text = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
        recorded = {"tools": [], "hooks": [], "middleware": []}

        class Ctx:
            def register_tool(self, name, *args, **kwargs):
                recorded["tools"].append(name)

            def register_hook(self, hook_name, callback, *args, **kwargs):
                recorded["hooks"].append(hook_name)

            def register_middleware(self, kind, callback):
                recorded["middleware"].append(kind)

            def register_command(self, *args, **kwargs):
                return None

            def register_cli_command(self, *args, **kwargs):
                return None

            def register_skill(self, *args, **kwargs):
                return None

            def register_automation_blueprint(self, *args, **kwargs):
                return None

            def get_config(self, key, default=None):
                return default

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "life_manager_plugin",
            ROOT / "__init__.py",
            submodule_search_locations=[str(ROOT)],
        )
        module = importlib.util.module_from_spec(spec)
        module.__path__ = [str(ROOT)]
        sys.modules["life_manager_plugin"] = module
        spec.loader.exec_module(module)
        module.register(Ctx())
        for key, label in (
            ("tools", "provides_tools"),
            ("hooks", "provides_hooks"),
            ("middleware", "provides_middleware"),
        ):
            declared = _yaml_list(text, label)
            self.assertEqual(sorted(recorded[key]), sorted(declared))


def _yaml_list(text, key):
    lines = text.splitlines()
    values = []
    capturing = False
    for line in lines:
        if line.startswith(f"{key}:"):
            capturing = True
            continue
        if capturing:
            if line.startswith(" ") or line.startswith("-"):
                stripped = line.strip()
                if stripped.startswith("- "):
                    values.append(stripped[2:].strip().strip("'\""))
                elif stripped and not stripped.startswith("#"):
                    break
            elif line.strip():
                break
    return values


if __name__ == "__main__":
    unittest.main()
