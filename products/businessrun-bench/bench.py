#!/usr/bin/env python3
"""BusinessRun Bench: run pinned upstream environments; keep their scores separate."""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
STATE = Path(os.environ.get("BUSINESSRUN_STATE", Path.home() / ".local/state/businessrun-bench"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def new_run(root, name):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,100}", name):
        raise ValueError("run ID must be a single safe directory name")
    path = root / name
    path.mkdir(parents=True, exist_ok=False, mode=0o700)
    return path


def summarize_process(rows, expected, model_cost_basis="recorded"):
    if not isinstance(expected, int) or expected < 1 or len(rows) > expected:
        raise ValueError("invalid campaign denominator")
    ids = [r["run_id"] for r in rows if "run_id" in r]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate upstream attempt")
    valid = []
    for row in rows:
        turns = row.get("turns")
        execution_ok = (not row.get("error") and row.get("grader_errors") == []
                        and isinstance(turns, list) and bool(turns)
                        and all(t.get("exit_code") == 0 and t.get("timed_out") is False for t in turns))
        valid.append(execution_ok)
    passed = sum(ok and row.get("passed") is True for ok, row in zip(valid, rows))
    costs = [r.get("cost_usd") for r in rows]
    known = (model_cost_basis != "unknown" and len(rows) == expected
             and all(type(c) in (int, float) and math.isfinite(c) and c >= 0 for c in costs))
    cost = sum(costs) if known else None
    return {"attempts": len(rows), "expected_attempts": expected, "missing": expected - len(rows),
            "passed": passed, "invalid": len(rows) - sum(valid),
            "campaign_complete": len(rows) == expected and all(valid),
            "model_cost_usd": cost, "cost_per_success_usd": cost / passed if cost is not None and passed else None}


def catalog():
    return json.loads((HERE / "catalog.json").read_text())


def source_info(suite, source_root):
    spec = catalog()["runnable"][suite]
    source = source_root / spec["directory"]
    actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if actual != spec["commit"]:
        raise ValueError(f"source pin mismatch for {suite}: {actual}")
    dirty = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True)
    if any(line[3:] != "harnesses/businessrun-native.sh" for line in dirty.splitlines()):
        raise ValueError("upstream source contains unrecorded changes")
    return source, {"repository": spec["repository"], "commit": actual, "dirty": bool(dirty)}


def setup(args):
    if sys.version_info[:2] != (3, 12):
        raise ValueError("Use Python 3.12 for pinned upstream dependencies")
    spec = catalog()["runnable"][args.suite]
    args.sources.mkdir(parents=True, exist_ok=True)
    path = args.sources / spec["directory"]
    if not path.exists():
        subprocess.run(["git", "clone", "--no-checkout", "--filter=blob:none", spec["repository"], str(path)], check=True)
        subprocess.run(["git", "-C", str(path), "checkout", "--detach", spec["commit"]], check=True)
    source_info(args.suite, args.sources)
    venv = args.state / "venvs" / args.suite
    if not (venv / "bin/python").exists():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    packages = spec["baseline_requirements"]
    if packages:
        subprocess.run([str(venv / "bin/python"), "-m", "pip", "install", *packages], check=True)
    if args.suite == "business-process":
        subprocess.run([str(venv / "bin/python"), "-m", "pip", "install", "-r", str(path / "requirements.txt")], check=True)
    print(json.dumps({"suite": args.suite, "ready": True, "scope": "baseline dependencies; model access is separate"}))


def process_workspace(source, run):
    """Reuse immutable code while keeping upstream's ROOT-relative cache/results per run."""
    root = run / "upstream"
    root.mkdir()
    for name in ["bench", "tasks", "erp"]:
        (root / name).symlink_to(source / name, target_is_directory=True)
    (root / "harnesses").mkdir()
    (root / "harnesses/businessrun-native.sh").symlink_to(HERE / "native_adapter.sh")
    return root


def command_for(args, source, run):
    python = str(args.python or args.state / "venvs" / args.suite / "bin/python")
    if args.suite == "coffee":
        if args.policy not in ("passive", "heuristic"):
            raise ValueError("coffee supports passive or heuristic with five passive background actors")
        cmd = [python, "-m", "coffeebench.main", "--model", "passive", "--max_days", "90",
               "--seed", str(args.seed), "--main_agent", "roaster_A", "--output", str(run / "trajectory.json")]
        if args.policy == "heuristic":
            cmd += ["--models", "roaster_A:heuristic_roaster"]
        return cmd, run, "environment_baseline_passive_background"
    if args.suite == "yc":
        if args.policy not in ("greedy", "random", "throughput", "prestige"):
            raise ValueError("yc baseline policy must be greedy, random, throughput, or prestige")
        return [python, str(HERE / "bench.py"), "_yc", str(source), str(args.seed), args.policy], run, "script_baseline_default_year"
    if args.policy not in ("oracle", "null", "native-codex"):
        raise ValueError("business-process policy must be oracle, null, or native-codex")
    label = "businessrun-" + run.name
    harness = args.policy
    if harness == "native-codex":
        harness = "businessrun-native"  # not 'codex': upstream guesses a model when trace omits it
    runtime = process_workspace(source, run)
    cmd = [python, str(runtime / "bench/process_run.py"), "--task", args.task, "--harness", harness,
           "--seed", str(args.seed), "--runs", "1", "--parallel", "1", "--label", label,
           "--timeout", str(args.timeout)]
    if args.faults:
        cmd += ["--faults", args.faults]
    return cmd, runtime, "local_development_not_answer_isolated"


def stop_tree(process):
    """Freeze the owned tree, including new sessions, before terminating it (POSIX)."""
    owned = {process.pid}
    identities = {}
    def identity(pid):
        return subprocess.run(["ps", "-p", str(pid), "-o", "lstart="], capture_output=True, text=True, check=False).stdout.strip()
    def send(pid, sig):
        initial = identities.setdefault(pid, identity(pid))
        if not initial or identity(pid) != initial:
            return
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass
    send(process.pid, signal.SIGSTOP)
    while True:
        rows = subprocess.check_output(["ps", "-axo", "pid=,ppid="], text=True)
        pairs = [tuple(map(int, line.split())) for line in rows.splitlines()]
        expanded = set(owned)
        while True:
            children = {pid for pid, parent in pairs if parent in expanded}
            if children <= expanded:
                break
            expanded |= children
        new = expanded - owned
        for pid in new:
            send(pid, signal.SIGSTOP)
        owned = expanded
        if not new:
            break
    # SIGCONT delivers pending SIGTERM to stopped processes. A surviving child gets SIGKILL.
    for pid in owned:
        send(pid, signal.SIGTERM)
        send(pid, signal.SIGCONT)
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    for pid in owned:
        send(pid, signal.SIGKILL)
    process.wait()


def failure_diagnostics(run):
    """Publish types and missing import names, never exception messages or log text."""
    allowed_types = {"ModuleNotFoundError", "ImportError", "RuntimeError", "ValueError", "TypeError",
                     "FileNotFoundError", "PermissionError", "OSError", "OperationalError", "AssertionError",
                     "AttributeError", "KeyError", "CalledProcessError", "TimeoutExpired", "ZeroDivisionError"}
    allowed_modules = {"requests", "httpx", "yaml", "fastapi", "uvicorn", "pandas", "numpy", "openpyxl",
                       "bberp", "procgen", "PIL", "sqlalchemy", "pydantic", "typer", "rich", "dotenv",
                       "litellm", "psutil", "xlsxwriter", "pypdf", "aiohttp", "tabulate"}
    found = []
    for path in sorted(run.rglob("*.log")):
        if path.stat().st_size > 2_000_000:
            continue
        for line in path.read_text(errors="replace").splitlines():
            match = re.match(r"^([A-Za-z][A-Za-z0-9_]*(?:Error|Exception)):", line)
            if match:
                item = {"log_role": "upstream", "exception": match[1] if match[1] in allowed_types else "other"}
                missing = re.match(r"^ModuleNotFoundError: No module named '([A-Za-z0-9_.]+)'$", line)
                if missing:
                    item["missing_module"] = missing[1] if missing[1] in allowed_modules else "other"
                if item not in found:
                    found.append(item)
    return found[:20]


def execute(args):
    source, info = source_info(args.suite, args.sources)
    name = args.run_id or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    run = new_run(args.state / "runs", name)
    cmd, cwd, protocol = command_for(args, source, run)
    _, info = source_info(args.suite, args.sources)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(source / "src"), str(source), os.environ.get("PYTHONPATH", "")]))
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    begin = time.monotonic()
    error_class = None
    with (run / "stdout.log").open("w") as out, (run / "stderr.log").open("w") as err:
        try:
            process = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=out, stderr=err, start_new_session=True)
            code = process.wait(timeout=args.wall_seconds)
        except OSError as exc:
            code = 127 if isinstance(exc, FileNotFoundError) else 126
            error_class = "executable_not_found" if code == 127 else "process_start_failed"
        except subprocess.TimeoutExpired:
            stop_tree(process)
            code = 124
            error_class = "wall_timeout"
    summary = None
    evidence = []
    if args.suite == "coffee":
        path = run / "trajectory.json"
        if path.exists():
            data = json.loads(path.read_text())
            focal = data["result"]["agents"]["roaster_A"]
            summary = {"completed": focal["completed"], "bankrupt_day": focal["bankrupt_day"],
                       "net_income_simulated_usd": focal["net_income"],
                       "days_recorded": data["max_days"], "background_policy": "passive",
                       "model_cost_usd": 0.0, "llm_calls": 0}
            evidence.append(path)
    elif args.suite == "yc":
        path = run / "baseline.json"
        if path.exists():
            data = json.loads(path.read_text())
            summary = {k: data[k] for k in ["bankrupt", "tasks_completed", "tasks_failed", "turns", "final_balance_cents"]}
            summary["model_cost_usd"] = 0.0
            evidence.extend([path, *sorted((run / "results").glob("*.json"))])
    else:
        root = run / "upstream/results" / ("businessrun-" + name)
        path = root / "summary.json"
        expected = len(list((source / "tasks/process").glob("*/task.yaml"))) if args.task == "all" else len(args.task.split(","))
        rows = json.loads(path.read_text()) if path.exists() else []
        if args.policy in ("oracle", "null"):
            rows = [dict(r, cost_usd=0.0) for r in rows]
        else:
            # Native subscription: retain unknown cost; do not inherit upstream's fallback model/rate card.
            rows = [dict(r, cost_usd=None) for r in rows]
        summary = summarize_process(rows, expected, "unknown" if args.policy == "native-codex" else "script_llm_zero")
        evidence = sorted(root.glob("*/result.json"))
    public_command = [str(c).replace(str(source), "$SOURCE").replace(str(run), "$RUN").replace(str(HERE), "$RUNNER") for c in cmd]
    try:
        python_version = subprocess.check_output([cmd[0], "-c", "import platform; print(platform.python_version())"], text=True, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        python_version = None
    public_command[0] = "$PYTHON"
    receipt = {"schema_version": 1, "run_id": name, "suite": args.suite, "policy": args.policy,
               "command": public_command, "python_version": python_version,
               "seed": args.seed, "task": args.task if args.suite == "business-process" else None,
               "faults": args.faults, "protocol": protocol, "source": info,
               "runner_sha256": digest(__file__), "adapter_sha256": digest(HERE / "native_adapter.sh"),
               "started_at": started, "wall_seconds": round(time.monotonic() - begin, 3),
               "exit_code": code, "artifact_present": bool(evidence), "error_class": error_class,
               "summary": summary, "host_cost_usd": None,
               "failure_diagnostics": failure_diagnostics(run) if code or not evidence else [],
               "artifact_hashes": [{"name": p.name, "sha256": digest(p)} for p in evidence]}
    (run / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    if code:
        return code
    if args.suite == "business-process" and not summary["campaign_complete"]:
        return 1
    return 0 if summary is not None else 1


def yc_child(source, seed, policy):
    sys.path[:0] = [str(source / "src"), str(source / "scripts")]
    from bot_runner import run_bot, STRATEGIES
    slug, strategy = STRATEGIES[policy]
    result = run_bot("default", seed, slug, strategy)
    Path("baseline.json").write_text(json.dumps(result, indent=2))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "_yc":
        yc_child(Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    for name in ["setup", "run"]:
        p = sub.add_parser(name)
        p.add_argument("--suite", choices=list(catalog()["runnable"]), required=True)
        p.add_argument("--state", type=Path, default=STATE)
        p.add_argument("--sources", type=Path, default=STATE / "sources")
        if name == "run":
            p.add_argument("--python", type=Path)
            p.add_argument("--policy", required=True)
            p.add_argument("--seed", type=int, default=0)
            p.add_argument("--task", default="procure-to-pay-week")
            p.add_argument("--faults")
            p.add_argument("--timeout", type=int, default=300)
            p.add_argument("--wall-seconds", type=int, default=2400)
            p.add_argument("--run-id")
    args = parser.parse_args()
    if args.command == "catalog":
        print(json.dumps(catalog(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "setup":
        setup(args)
        return 0
    if args.timeout <= 0 or args.wall_seconds <= 0:
        parser.error("timeouts must be positive")
    return execute(args)


if __name__ == "__main__":
    raise SystemExit(main())
