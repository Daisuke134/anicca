"""Project-scoped LangGraph persistence.

The shadow runtime owns no marketplace effect capability.  It only persists
agent checkpoints and project files under the existing ``~/gig`` state root.
"""

from __future__ import annotations

import sqlite3
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def fulfillment_thread_id(marketplace: str, contract_id: str) -> str:
    """Return the stable one-project/one-thread identity required by the SSOT."""
    clean_marketplace = marketplace.strip().lower()
    clean_contract = contract_id.strip()
    if not clean_marketplace or not clean_contract:
        raise ValueError("marketplace and contract_id are required")
    if ":" in clean_marketplace or "/" in clean_contract:
        raise ValueError("invalid fulfillment thread identity")
    return f"{clean_marketplace}:{clean_contract}"


@dataclass
class DurableRuntime:
    """Resources whose lifetime must cover graph construction and invocation."""

    checkpointer: Any
    store: Any
    backend: Any
    stack: ExitStack

    def close(self) -> None:
        self.stack.close()


def open_durable_runtime(*, state_root: Path, thread_id: str) -> DurableRuntime:
    """Open SQLite checkpoint/store plus a project-scoped persistent filesystem."""
    from deepagents.backends import CompositeBackend, FilesystemBackend, StoreBackend
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.store.sqlite import SqliteStore

    if not thread_id:
        raise ValueError("thread_id is required")
    runtime_root = state_root.expanduser().resolve() / "deep-agent"
    project_root = runtime_root / "projects" / thread_id
    runtime_root.mkdir(parents=True, exist_ok=True)
    project_root.mkdir(parents=True, exist_ok=True)

    stack = ExitStack()
    checkpoint_connection = sqlite3.connect(
        runtime_root / "checkpoints.sqlite3", check_same_thread=False
    )
    store_connection = sqlite3.connect(
        runtime_root / "store.sqlite3",
        check_same_thread=False,
        isolation_level=None,
    )
    stack.callback(checkpoint_connection.close)
    stack.callback(store_connection.close)
    checkpointer = SqliteSaver(checkpoint_connection)
    store = SqliteStore(store_connection)
    checkpointer.setup()
    store.setup()

    persistent_files = StoreBackend(
        store=store,
        namespace=lambda _runtime: ("coconala-fulfillment", thread_id, "files"),
    )
    project_files = FilesystemBackend(root_dir=project_root, virtual_mode=True)
    backend = CompositeBackend(
        default=persistent_files,
        routes={"/project/": project_files},
    )
    return DurableRuntime(checkpointer, store, backend, stack)
