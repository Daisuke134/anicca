"""Effect-free P1-1 shadow fulfillment composition."""

from __future__ import annotations

from typing import Any


SHADOW_SYSTEM_PROMPT = """You are the shadow Coconala fulfillment agent.
Read the complete project context before deciding what work remains. Keep every
unfinished buyer requirement on the todo list. A todo cannot be completed
without an artifact hash and acceptance evidence. This shadow has no customer
effect tools: never claim that a reply, upload, or formal delivery occurred.
Return the intended next work state and evidence needed for comparison with the
live fulfillment loop.
"""


def build_shadow_fulfillment_agent(
    *, model: Any, runtime: Any, todo_middleware: Any
) -> Any:
    """Assemble Deep Agents without exposing browser or marketplace effects."""
    from deepagents import create_deep_agent

    return create_deep_agent(
        model=model,
        tools=[],
        system_prompt=SHADOW_SYSTEM_PROMPT,
        middleware=[todo_middleware],
        backend=runtime.backend,
        checkpointer=runtime.checkpointer,
        store=runtime.store,
        name="coconala-fulfillment-shadow",
    )
