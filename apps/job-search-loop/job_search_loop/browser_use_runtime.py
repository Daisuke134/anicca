"""Build and verify the content-locked Browser Use Python runtime."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Callable, Sequence


PINNED_BROWSER_USE_VERSION = "0.13.7"
RUNTIME_DIRECTORY = "browser-use-0.13.7-py312"


def browser_use_runtime_python(runtime_root: Path) -> Path:
    return runtime_root / RUNTIME_DIRECTORY / "bin" / "python"


def _run(arguments: Sequence[str | Path]) -> str:
    completed = subprocess.run(
        [str(item) for item in arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _version(python: Path, command_runner: Callable[[Sequence[str | Path]], str]) -> str:
    return command_runner(
        [
            python,
            "-c",
            "from importlib.metadata import version; print(version('browser-use'))",
        ]
    ).strip()


def bootstrap_browser_use_runtime(
    *,
    runtime_root: Path,
    lock_path: Path,
    uv_path: Path,
    command_runner: Callable[[Sequence[str | Path]], str] = _run,
) -> Path:
    runtime_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = runtime_root / RUNTIME_DIRECTORY
    python = browser_use_runtime_python(runtime_root)
    if python.is_file() and os.access(python, os.X_OK):
        if _version(python, command_runner) == PINNED_BROWSER_USE_VERSION:
            return python
        raise RuntimeError("installed Browser Use runtime does not match the pinned version")
    if target.exists():
        raise RuntimeError("incomplete Browser Use runtime already exists")
    if not lock_path.is_file():
        raise RuntimeError("Browser Use dependency lock is missing")
    temporary = runtime_root / f".{RUNTIME_DIRECTORY}.tmp-{os.getpid()}"
    if temporary.exists():
        raise RuntimeError("Browser Use runtime temporary path already exists")
    command_runner([uv_path, "venv", "--python", "3.12", temporary])
    temporary_python = temporary / "bin" / "python"
    command_runner(
        [
            uv_path,
            "pip",
            "sync",
            "--python",
            temporary_python,
            "--require-hashes",
            lock_path,
        ]
    )
    if _version(temporary_python, command_runner) != PINNED_BROWSER_USE_VERSION:
        raise RuntimeError("new Browser Use runtime does not match the pinned version")
    temporary.replace(target)
    if _version(python, command_runner) != PINNED_BROWSER_USE_VERSION:
        raise RuntimeError("activated Browser Use runtime failed verification")
    return python


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--uv", required=True, type=Path)
    arguments = parser.parse_args()
    python = bootstrap_browser_use_runtime(
        runtime_root=arguments.runtime_root,
        lock_path=arguments.lock,
        uv_path=arguments.uv,
    )
    print(json.dumps({"status": "ready", "python": str(python)}, sort_keys=True))


if __name__ == "__main__":
    main()
