#!/usr/bin/env python3
"""Stop deterministic publication retry storms until executable context changes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def context(state: Path, code_files: list[Path]) -> dict[str, str]:
    code_digest = hashlib.sha256()
    for path in code_files:
        code_digest.update(str(path).encode())
        code_digest.update(b"\0")
        code_digest.update(path.read_bytes())
        code_digest.update(b"\0")
    return {
        "state_sha256": sha256(state),
        "code_sha256": code_digest.hexdigest(),
    }


def read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "pairs": {}}
    if not isinstance(value, dict) or not isinstance(value.get("pairs"), dict):
        return {"version": 1, "pairs": {}}
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def error_signature(path: Path) -> str:
    return signature_from_text(path.read_text(encoding="utf-8", errors="replace"))


def signature_from_text(text: str) -> str:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]
    return (lines[-1] if lines else "empty-error-output")[-500:]


def emit(value: dict[str, Any]) -> int:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
    return 0


def run_bounded(argv: list[str], timeout_seconds: float) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        signature = f"publisher-timeout-seconds={timeout_seconds:g}"
        stderr = f"{stderr}{'' if not stderr or stderr.endswith(chr(10)) else chr(10)}{signature}\n"
        return subprocess.CompletedProcess(argv, 124, stdout, stderr)


def main() -> int:
    raw_args = sys.argv[1:]
    command_argv: list[str] = []
    if "--" in raw_args:
        separator = raw_args.index("--")
        command_argv = raw_args[separator + 1 :]
        raw_args = raw_args[:separator]
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("check", "failure", "success", "run"))
    parser.add_argument("--circuit", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument(
        "--code-file", required=True, type=Path, action="append"
    )
    parser.add_argument("--pair", required=True)
    parser.add_argument("--error-file", type=Path)
    parser.add_argument("--threshold", type=int, default=2)
    parser.add_argument("--timeout-seconds", type=float, default=300)
    parser.add_argument("--log", type=Path)
    parser.add_argument(
        "--notify-command",
        type=Path,
        default=Path(__file__).resolve().parent / "_shared" / "notifier.sh",
    )
    args = parser.parse_args(raw_args)

    value = read(args.circuit)
    pairs = value["pairs"]
    current_context = context(args.state, args.code_file)
    row = pairs.get(args.pair)

    if args.command == "run":
        if (
            args.threshold < 1
            or args.timeout_seconds <= 0
            or not command_argv
            or args.log is None
        ):
            parser.error(
                "run requires --log, positive --threshold/--timeout-seconds, and a command"
            )
        if isinstance(row, dict) and all(
            row.get(key) == digest for key, digest in current_context.items()
        ) and row.get("open") is True:
            decision = {
                "action": "block",
                "count": int(row["count"]),
                "notify": False,
                "pair": args.pair,
                "reason": "same-failure-circuit-open",
                "signature": str(row["signature"]),
            }
            args.log.parent.mkdir(parents=True, exist_ok=True)
            with args.log.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(decision, ensure_ascii=False) + "\n")
            return emit(decision)
        if isinstance(row, dict) and any(
            row.get(key) != digest for key, digest in current_context.items()
        ):
            pairs.pop(args.pair, None)
            row = None
            write(args.circuit, value)
        completed = run_bounded(command_argv, args.timeout_seconds)
        args.log.parent.mkdir(parents=True, exist_ok=True)
        with args.log.open("a", encoding="utf-8") as stream:
            stream.write(completed.stdout)
            stream.write(completed.stderr)
        if completed.returncode == 0:
            pairs.pop(args.pair, None)
            write(args.circuit, value)
            return emit({"action": "closed", "pair": args.pair})
        signature = signature_from_text(completed.stderr or completed.stdout)
        same_failure = (
            isinstance(row, dict)
            and row.get("signature") == signature
            and all(
                row.get(key) == digest
                for key, digest in current_context.items()
            )
        )
        count = int(row.get("count", 0)) + 1 if same_failure else 1
        opened = count >= args.threshold
        already_notified = bool(row.get("notified")) if same_failure else False
        notify = opened and not already_notified
        pairs[args.pair] = {
            **current_context,
            "code_files": [str(path) for path in args.code_file],
            "count": count,
            "notified": already_notified or notify,
            "open": opened,
            "signature": signature,
        }
        write(args.circuit, value)
        decision = {
            "action": "open" if opened else "retry",
            "count": count,
            "notify": notify,
            "pair": args.pair,
            "signature": signature,
        }
        with args.log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(decision, ensure_ascii=False) + "\n")
        if notify:
            message = (
                "Writer publication circuit opened "
                f"pair={args.pair} count={count} error={signature}"
            )
            subprocess.run(
                [str(args.notify_command), message],
                text=True,
                capture_output=True,
                check=False,
            )
        print(json.dumps(decision, ensure_ascii=False, separators=(",", ":")))
        return 0 if opened else completed.returncode

    if args.command == "check":
        if not isinstance(row, dict):
            return emit(
                {"action": "run", "pair": args.pair, "reason": "no-failure"}
            )
        if any(row.get(key) != digest for key, digest in current_context.items()):
            pairs.pop(args.pair, None)
            write(args.circuit, value)
            return emit(
                {
                    "action": "run",
                    "pair": args.pair,
                    "reason": "execution-context-changed",
                }
            )
        if row.get("open") is True:
            return emit(
                {
                    "action": "block",
                    "count": int(row["count"]),
                    "notify": False,
                    "pair": args.pair,
                    "reason": "same-failure-circuit-open",
                    "signature": str(row["signature"]),
                }
            )
        return emit({"action": "run", "pair": args.pair, "reason": "retry"})

    if args.command == "success":
        pairs.pop(args.pair, None)
        write(args.circuit, value)
        return emit({"action": "closed", "pair": args.pair})

    if args.error_file is None or args.threshold < 1:
        parser.error("failure requires --error-file and positive --threshold")
    signature = error_signature(args.error_file)
    same_failure = (
        isinstance(row, dict)
        and row.get("signature") == signature
        and all(row.get(key) == digest for key, digest in current_context.items())
    )
    count = int(row.get("count", 0)) + 1 if same_failure else 1
    opened = count >= args.threshold
    already_notified = bool(row.get("notified")) if same_failure else False
    notify = opened and not already_notified
    pairs[args.pair] = {
        **current_context,
        "code_files": [str(path) for path in args.code_file],
        "count": count,
        "notified": already_notified or notify,
        "open": opened,
        "signature": signature,
    }
    write(args.circuit, value)
    return emit(
        {
            "action": "open" if opened else "retry",
            "count": count,
            "notify": notify,
            "pair": args.pair,
            "signature": signature,
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
