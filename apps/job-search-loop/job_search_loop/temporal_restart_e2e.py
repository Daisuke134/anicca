"""Real Temporal worker-restart proof for the local Job Hunter runtime."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from job_search_loop.temporal_restart_fixture import effect_counts, record_activity_effect

MODULE_NAME = "job_search_loop.temporal_restart_e2e"


@activity.defn
async def durable_effect_activity(arguments: dict[str, str]) -> list[int]:
    inserted = record_activity_effect(arguments["database_path"], arguments["effect_key"])
    if arguments["worker_mode"] == "stall_after_effect":
        Path(arguments["effect_marker"]).write_text("effect-recorded\n", encoding="utf-8")
        while True:
            activity.heartbeat("effect-recorded")
            await asyncio.sleep(0.2)
    return [int(inserted), activity.info().attempt]


@workflow.defn
class RestartProofWorkflow:
    @workflow.run
    async def run(self, arguments: dict[str, str]) -> list[int]:
        return await workflow.execute_activity(
            durable_effect_activity,
            arguments,
            start_to_close_timeout=timedelta(seconds=15),
            heartbeat_timeout=timedelta(seconds=1),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=1),
                maximum_attempts=3,
            ),
        )


async def run_worker(address: str, task_queue: str) -> None:
    client = await Client.connect(address)
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[RestartProofWorkflow],
        activities=[durable_effect_activity],
        workflow_runner=UnsandboxedWorkflowRunner(),
    )
    async with worker:
        await asyncio.Event().wait()


async def wait_for_marker(marker: Path, timeout_seconds: float = 10) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while loop.time() < deadline:
        if marker.exists():
            return
        await asyncio.sleep(0.05)
    raise TimeoutError(f"activity marker not created: {marker}")


def worker_process(address: str, task_queue: str, mode: str) -> subprocess.Popen[bytes]:
    environment = os.environ.copy()
    environment["JOB_HUNTER_TEMPORAL_WORKER_MODE"] = mode
    return subprocess.Popen(
        [sys.executable, "-m", MODULE_NAME, "worker", "--address", address, "--task-queue", task_queue],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=None,
    )


async def run_restart_proof(address: str, state_directory: Path) -> dict[str, object]:
    state_directory.mkdir(parents=True, exist_ok=True)
    database_path = state_directory / "effects.sqlite3"
    marker = state_directory / "effect-recorded.marker"
    workflow_id = f"job-hunter-restart-proof-{os.getpid()}"
    task_queue = workflow_id
    effect_key = "application:temporal-restart-proof"
    arguments = {
        "database_path": str(database_path),
        "effect_key": effect_key,
        "effect_marker": str(marker),
        "worker_mode": "stall_after_effect",
    }
    first_worker = worker_process(address, task_queue, "stall_after_effect")
    second_worker: subprocess.Popen[bytes] | None = None
    try:
        client = await Client.connect(address)
        handle = await client.start_workflow(
            RestartProofWorkflow.run,
            arguments,
            id=workflow_id,
            task_queue=task_queue,
        )
        await wait_for_marker(marker)
        first_worker.kill()
        first_worker.wait(timeout=5)
        arguments["worker_mode"] = "complete"
        # Workflow input is immutable; the replacement worker selects its local mode.
        second_worker = worker_process(address, task_queue, "complete")
        result = await asyncio.wait_for(handle.result(), timeout=20)
        effects, attempts = effect_counts(database_path, effect_key)
        proof = {
            "workflow_id": workflow_id,
            "first_worker_pid": first_worker.pid,
            "second_worker_pid": second_worker.pid,
            "first_worker_exit": first_worker.returncode,
            "activity_result": result,
            "effect_count": effects,
            "attempt_count": attempts,
        }
        if effects != 1 or attempts < 2:
            raise RuntimeError(f"restart proof failed: {proof}")
        return proof
    finally:
        if first_worker.poll() is None:
            first_worker.kill()
            first_worker.wait(timeout=5)
        if second_worker is not None and second_worker.poll() is None:
            second_worker.terminate()
            second_worker.wait(timeout=5)


async def async_main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    worker_parser = subparsers.add_parser("worker")
    worker_parser.add_argument("--address", required=True)
    worker_parser.add_argument("--task-queue", required=True)
    proof_parser = subparsers.add_parser("proof")
    proof_parser.add_argument("--address", default="127.0.0.1:7233")
    proof_parser.add_argument("--state-directory", type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.command == "worker":
        mode = os.environ["JOB_HUNTER_TEMPORAL_WORKER_MODE"]
        original = durable_effect_activity

        @activity.defn(name="durable_effect_activity")
        async def configured_activity(payload: dict[str, str]) -> list[int]:
            payload = {**payload, "worker_mode": mode}
            return await original(payload)

        client = await Client.connect(arguments.address)
        worker = Worker(
            client,
            task_queue=arguments.task_queue,
            workflows=[RestartProofWorkflow],
            activities=[configured_activity],
            workflow_runner=UnsandboxedWorkflowRunner(),
        )
        async with worker:
            await asyncio.Event().wait()
    else:
        proof = await run_restart_proof(arguments.address, arguments.state_directory)
        print(json.dumps(proof, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(async_main())
