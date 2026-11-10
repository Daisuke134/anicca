"""Life Manager — commitments, habit streaks, and a check-in before each turn."""

from __future__ import annotations

from pathlib import Path

try:
    from . import engine, runtime, schemas
except ImportError:  # unit tests load the modules by path
    import engine
    import runtime
    import schemas

_SKILL = Path(__file__).resolve().parent / "skills" / "intervene" / "SKILL.md"


def register(ctx):
    """Register tools, the turn hook, middleware, commands, and the check-in blueprint."""
    store = runtime.CtxStore(ctx)

    def _bool(key, default):
        try:
            value = ctx.get_config(key, default)
        except Exception:
            return default
        return value if isinstance(value, bool) else default

    def _int(key, default):
        try:
            value = ctx.get_config(key, default)
        except Exception:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def pre_llm_call(user_message="", session_id="", **kwargs):
        try:
            return runtime.hook_context(
                store,
                user_message or "",
                session_id=session_id or "",
                today=engine.clock(),
                capture=_bool("capture_statements", True),
                max_open=_int("max_open", 30),
            )
        except Exception:
            return None

    def on_tool_request(tool_name, args=None, **kwargs):
        try:
            return runtime.normalize_tool_request(tool_name, args)
        except Exception:
            return None

    def make_handler(name):
        def handler(args, **kwargs):
            unattended = False
            execution_id = None
            try:
                cron = ctx.current_cron_execution()
            except Exception:
                cron = None
            if cron is not None:
                unattended = True
                execution_id = getattr(cron, "execution_id", None)
            return runtime.handle_tool(
                store,
                name,
                args or {},
                today=engine.clock(),
                unattended=unattended,
                execution_id=execution_id,
                max_open=_int("max_open", 30),
            )

        return handler

    for schema in schemas.ALL:
        ctx.register_tool(
            name=schema["name"],
            toolset="life-manager",
            schema=schema,
            handler=make_handler(schema["name"]),
        )
    ctx.register_hook("pre_llm_call", pre_llm_call)
    ctx.register_middleware("tool_request", on_tool_request)

    def slash_command(raw_args="", **kwargs):
        try:
            return runtime.slash(
                store, raw_args, today=engine.clock(), max_open=_int("max_open", 30)
            )
        except Exception:
            return "Life Manager could not read its board."

    ctx.register_command(
        "commitments",
        handler=slash_command,
        description="Show or update Life Manager commitments",
        args_hint="[status|add|done|drop|defer]",
    )

    def setup_cli(subparser):
        commands = subparser.add_subparsers(dest="lm_command")
        commands.add_parser("status", help="Show the board")
        add = commands.add_parser("add", help="Record a commitment")
        add.add_argument("text", nargs="+")
        done = commands.add_parser("done", help="Mark a commitment done")
        done.add_argument("ref")
        drop = commands.add_parser("drop", help="Stop tracking a commitment")
        drop.add_argument("ref")
        defer = commands.add_parser("defer", help="Move a task's due date")
        defer.add_argument("ref")
        defer.add_argument("due_on")
        commands.add_parser("checkin", help="Record an unattended check-in and print the board")

    def cli_command(args):
        argv = []
        command = getattr(args, "lm_command", None)
        if command:
            argv.append(command)
            if command == "add":
                argv.extend(getattr(args, "text", []) or [])
            elif command in ("done", "drop"):
                argv.append(getattr(args, "ref", ""))
            elif command == "defer":
                argv.extend([getattr(args, "ref", ""), getattr(args, "due_on", "")])
        runtime.cli_dispatch(
            store,
            argv,
            today=engine.clock(),
            write=print,
            max_open=_int("max_open", 30),
        )

    ctx.register_cli_command(
        name="life-manager",
        help="Life Manager commitments and habit streaks",
        setup_fn=setup_cli,
        handler_fn=cli_command,
    )

    if _SKILL.is_file():
        try:
            ctx.register_skill(
                "intervene",
                _SKILL,
                "Intervene on stated commitments using the Life Manager board.",
            )
        except Exception:
            pass

    try:
        ctx.register_automation_blueprint(
            "check-in",
            title="Life Manager check-in",
            description="Review open commitments and habit streaks, then say the one next action.",
            category="general",
            schedule_template="{minute} {hour} * * *",
            prompt_template=(
                "Call life_manager_checkin. In under 120 words, name anything overdue, "
                "any habit streak at risk, and one next action. "
                "Do not mark an item complete unless the user already said it is done. "
                "If nothing is open, say the board is clear."
            ),
            slots=[
                {"name": "time", "type": "time", "label": "What time?", "default": "08:30"},
            ],
            tags=["habits", "check-in"],
        )
    except Exception:
        pass
