"""Composition root for the P1-1 Coconala fulfillment shadow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.fulfillment.agent import build_shadow_fulfillment_agent
from persistence.runtime import fulfillment_thread_id, open_durable_runtime
from provider.cli_chat_model import ExistingRunnerChatModel


def existing_runner_model(
    *, skill_root: Path, evidence_root: Path, workdir: Path
) -> ExistingRunnerChatModel:
    """Build the Deep Agents model adapter over the already-deployed runner."""
    skills_root = skill_root.resolve().parent
    return ExistingRunnerChatModel(
        runner_path=skills_root / "agent-runner" / "agent_runner.py",
        schema_path=skill_root / "schemas" / "deep_agent_turn.schema.json",
        evidence_root=evidence_root,
        workdir=workdir,
    )


def build_fulfillment_shadow(
    *, model: Any, contract_id: str, state_root: Path = Path.home() / "gig"
) -> tuple[Any, Any, dict[str, dict[str, str]]]:
    """Return the graph, owned runtime, and stable LangGraph invocation config."""
    from langchain.agents.middleware import TodoListMiddleware

    thread_id = fulfillment_thread_id("coconala", contract_id)
    runtime = open_durable_runtime(state_root=state_root, thread_id=thread_id)
    graph = build_shadow_fulfillment_agent(
        model=model,
        runtime=runtime,
        todo_middleware=TodoListMiddleware(),
    )
    config = {
        "configurable": {"thread_id": thread_id},
        "metadata": {
            "assistant_id": "coconala-fulfillment",
            "effect_mode": "shadow-read-only",
        },
    }
    return graph, runtime, config
