"""dump() and restore() must work whether or not the caller already has a loop running.

Both are entry points for plain scripts and for async callers alike: the CrowdWorks account
flow drives a page and then asks for a dump. `asyncio.run` refuses inside a running loop,
and that refusal reached the lane as the single word `vault_dump_failed` -- the session was
fine, the call shape was not.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("_sv_loop", SCRIPTS / "session_vault.py")
VAULT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VAULT)


async def _answer():
    return "ran"


def test_runs_with_no_loop_running():
    assert VAULT._run(_answer()) == "ran"


def test_runs_from_inside_a_running_loop():
    async def caller():
        return VAULT._run(_answer())
    assert asyncio.run(caller()) == "ran"


def test_an_exception_still_reaches_the_caller_from_inside_a_loop():
    async def boom():
        raise ValueError("real reason")

    async def caller():
        try:
            VAULT._run(boom())
        except ValueError as error:
            return str(error)
        return None
    assert asyncio.run(caller()) == "real reason"


def test_no_bare_asyncio_run_is_left_on_a_transport_call():
    source = (SCRIPTS / "session_vault.py").read_text(encoding="utf-8")
    for call in ("_call(", "_localstorage(", "_keepalive(", "_relogin_x("):
        assert f"asyncio.run({call}" not in source, call
