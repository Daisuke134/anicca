#!/usr/bin/env python3
"""Cut a release of this checkout and publish it for the coconala launchd jobs.

A lane never runs from a working tree: a git checkout changes under a job that
is mid-pass, so every lane runs from an immutable copy under
``~/gig/releases/life-manager/<sha>``.  The launchd definitions use the stable
``~/gig/releases/life-manager/current`` path; publishing atomically moves that
symlink after the immutable release has been built.

The jobs themselves are data -- ``config/launchd-jobs.json`` -- rendered against
per-machine values from ``~/.config/anicca/gig/install.json``. That is what lets
a Mac that has never run this loop install the same four jobs, and lets this one
keep the exact paths its lanes already use.

launchd runs the definition it loaded, not the file on disk.  Activation loads
the stable definition once.  Later watcher deploys only move ``current``; the
next natural process start resolves the new release without a plist reload.

    gig_release.py build                 # release the current HEAD
    gig_release.py activate              # build if needed, then switch the four lanes
    gig_release.py activate --jobs ai.anicca.hf-gig-browser
    gig_release.py status
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.parse import urlparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
GIG_DIR = HERE.parent
REPO_ROOT = GIG_DIR.parents[2]
MANIFEST = GIG_DIR / "config" / "launchd-jobs.json"
OVERRIDES = Path(
    os.environ.get("GIG_INSTALL_OVERRIDES", Path.home() / ".config/anicca/gig/install.json")
)
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
RELEASE_ROOT = Path.home() / "gig" / "releases" / "life-manager"
CURRENT_RELEASE = RELEASE_ROOT / "current"
PUBLISH_LOCK = RELEASE_ROOT / ".publish.lock"
# The browser owns the one authenticated session the lanes share. Reloading it
# throws that session away, so it is never in the default set.
DEFAULT_EXCLUDED = {"ai.anicca.hf-gig-browser", "ai.anicca.hf-gig-release-watch"}
# Negotiate is a durable supervisor rather than a periodic one-shot pass.  Waiting for
# ``is_running`` would therefore postpone every source release forever; its outbox is the
# restart boundary, so the watcher may reload it while periodic lanes wait for a gap.
CONTINUOUS_RELOADABLE = {"ai.anicca.hf-gig-reply-detector"}
PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
JOB_PROCESS_MARKERS = {
    "ai.anicca.hf-gig-apply-direct": "application_direct.py",
    "ai.anicca.hf-gig-storefront-direct": "storefront_direct.py",
    "ai.anicca.hf-gig-paid-direct": "paid_direct.py",
    "ai.anicca.hf-gig-reply-detector": "reply_detector.py",
}


def git(*args: str, cwd: Path = REPO_ROOT) -> str:
    command = ("git", *args)
    try:
        return subprocess.run(command, cwd=cwd, check=True,
                              capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError:
        # The release watcher is itself a launchd job. On this Mac the system resolver can
        # answer GitHub while libcurl's resolver intermittently cannot, which otherwise leaves
        # the watcher on an old immutable release forever. Retry fetches through the resolved
        # IPv4 address while retaining the TLS host name via curl's resolve option.
        if not args or args[0] != "fetch":
            raise
        remote = subprocess.run(
            ("git", "config", "--get", "remote.origin.url"), cwd=cwd,
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        host = urlparse(remote).hostname or ""
        if not host:
            raise
        resolved = subprocess.run(
            ("nslookup", "-type=A", host), capture_output=True, text=True, check=False,
        )
        addresses = re.findall(r"^Address:\s+(\d{1,3}(?:\.\d{1,3}){3})$",
                               resolved.stdout, flags=re.MULTILINE)
        if not addresses:
            raise
        fallback = ("git", "-c", f"http.curloptResolve={host}:443:{addresses[-1]}", *args)
        return subprocess.run(fallback, cwd=cwd, check=True,
                              capture_output=True, text=True).stdout.strip()


def resolve(values: dict[str, str]) -> dict[str, str]:
    """Expand {{NAME}} against the same table until it stops changing."""
    out = dict(values)
    for _ in range(10):
        changed = False
        for key, value in out.items():
            if not isinstance(value, str):
                continue
            new = PLACEHOLDER.sub(lambda m: out.get(m.group(1), m.group(0)), value)
            if new != value:
                out[key], changed = new, True
        if not changed:
            return out
    raise SystemExit("launchd-jobs.json: placeholders do not settle -- check for a cycle")


def render(value, table: dict[str, str]):
    if isinstance(value, str):
        return PLACEHOLDER.sub(lambda m: table.get(m.group(1), m.group(0)), value)
    if isinstance(value, list):
        return [render(item, table) for item in value]
    if isinstance(value, dict):
        return {key: render(item, table) for key, item in value.items()}
    return value


def settings(release: Path) -> tuple[dict, dict[str, str]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    table = dict(manifest["defaults"])
    table["HOME"] = str(Path.home())
    if OVERRIDES.is_file():
        machine = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        if not isinstance(machine, dict):
            raise SystemExit(f"{OVERRIDES}: expected a flat object of overrides")
        table.update({k: str(v) for k, v in machine.items()})
    table["RELEASE"] = str(release)
    # The watcher is the one job that runs from the checkout: it has to fetch.
    table["CHECKOUT"] = str(REPO_ROOT)
    return manifest, resolve(table)


def release_dir(sha: str) -> Path:
    return RELEASE_ROOT / sha


def current_sha() -> str:
    """Return the published immutable SHA, or empty when no valid pointer exists."""
    try:
        resolved = CURRENT_RELEASE.resolve(strict=True)
    except (FileNotFoundError, OSError):
        return ""
    if resolved.parent != RELEASE_ROOT.resolve() or not re.fullmatch(r"[0-9a-f]{40}", resolved.name):
        return ""
    return resolved.name


def publish(release: Path) -> None:
    """Atomically make a validated immutable release current, with one writer."""
    release = release.resolve(strict=True)
    if release.parent != RELEASE_ROOT.resolve() or not re.fullmatch(r"[0-9a-f]{40}", release.name):
        raise SystemExit(f"refusing release outside {RELEASE_ROOT}: {release}")
    marker = release / "skills" / "earn" / "gig" / "scripts" / "gig_paths.py"
    if not marker.is_file():
        raise SystemExit(f"incomplete release: {release}")
    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)
    with PUBLISH_LOCK.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        temporary = RELEASE_ROOT / f".current.{os.getpid()}"
        try:
            temporary.unlink(missing_ok=True)
            temporary.symlink_to(release.name)
            os.replace(temporary, CURRENT_RELEASE)
        finally:
            temporary.unlink(missing_ok=True)


def build(sha: str) -> Path:
    """Extract the tracked tree at `sha` and freeze it read-only."""
    target = release_dir(sha)
    if (target / "skills" / "earn" / "gig" / "scripts" / "gig_paths.py").is_file():
        return target
    if target.exists():                       # a half-written tree from an aborted run
        subprocess.run(["chmod", "-R", "u+w", str(target)], check=False)
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=target.parent, prefix=f".{sha[:12]}-"))
    try:
        archive = staging / "tree.tar"
        with archive.open("wb") as handle:
            subprocess.run(["git", "archive", "--format=tar", sha], cwd=REPO_ROOT,
                           check=True, stdout=handle)
        tree = staging / "tree"
        tree.mkdir()
        with tarfile.open(archive) as tar:
            tar.extractall(tree)              # noqa: S202 - our own git archive
        archive.unlink()
        tree.rename(target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    # Read-only so a lane, or an agent a lane spawns, cannot edit the code it runs.
    subprocess.run(["chmod", "-R", "a-w", str(target)], check=True)
    return target


def plist_for(job: dict, table: dict[str, str]) -> dict:
    manifest_env = json.loads(MANIFEST.read_text(encoding="utf-8"))["shared_env"]
    env = render(dict(manifest_env), table) | render(dict(job.get("env", {})), table)
    log_dir = table["GIG_LOG_DIR"]
    out = {
        "Label": job["label"],
        "ProgramArguments": render(job["program"], table),
        "EnvironmentVariables": {k: v for k, v in env.items() if v != ""},
        "WorkingDirectory": str(Path.home()),
        "StandardOutPath": f"{log_dir}/{job['log_basename']}.out.log",
        "StandardErrorPath": f"{log_dir}/{job['log_basename']}.err.log",
    }
    for key in ("StartInterval", "ThrottleInterval", "RunAtLoad", "KeepAlive", "ProcessType"):
        if key in job:
            out[key] = job[key]
    return out


def loaded_program(label: str) -> list[str]:
    """The argv launchd is actually holding, not the argv on disk."""
    printed = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
        capture_output=True, text=True,
    )
    if printed.returncode != 0:
        return []
    argv, inside = [], False
    for line in printed.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("arguments = {"):
            inside = True
            continue
        if inside:
            if stripped == "}":
                break
            argv.append(stripped)
    return argv


def control_plane_available() -> bool:
    """Whether this context can read the user's launchd domain."""
    return subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}"],
        capture_output=True,
    ).returncode == 0


def is_running(label: str) -> bool:
    printed = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{label}"],
                             capture_output=True, text=True)
    if printed.returncode == 0:
        return "state = running" in printed.stdout
    # ``launchctl print`` can fail transiently with macOS' Reentrancy avoided
    # response while the process itself is healthy. Treating that as idle lets
    # the watcher bootout a live browser pass. The process table is read-only
    # and is used only as a conservative busy fence; a missing or unreadable
    # table still fails closed (busy) rather than reloading.
    marker = JOB_PROCESS_MARKERS.get(label)
    if not marker:
        return True
    try:
        processes = subprocess.run(
            ["ps", "-axo", "command="], capture_output=True, text=True,
            timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return True
    if processes.returncode != 0:
        return True
    return any(marker in line for line in processes.stdout.splitlines())


def is_brake_only_process(label: str, table: dict[str, str]) -> bool:
    """True only when the current Apply PID has durably refused work on the brake."""
    if label != "ai.anicca.hf-gig-apply-direct":
        return False
    processes = subprocess.run(
        ["ps", "-axo", "pid=,command="], capture_output=True, text=True, check=False,
    )
    if processes.returncode != 0:
        return False
    pids = []
    for line in processes.stdout.splitlines():
        if JOB_PROCESS_MARKERS[label] not in line:
            continue
        fields = line.strip().split(None, 1)
        if fields and fields[0].isdigit():
            pids.append(fields[0])
    if len(pids) != 1:
        return False
    wakes = Path(table["GIG_STATE_DIR"]) / "apply-direct" / "wakes.jsonl"
    try:
        with wakes.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            end = handle.tell()
            start = max(0, end - 2_000_000)
            handle.seek(start)
            lines = handle.read().splitlines()
        receipt = json.loads(lines[-1])
    except (OSError, IndexError, json.JSONDecodeError):
        return False
    return (
        receipt.get("status") == "operator_brake"
        and receipt.get("effect") == 0
        and str(receipt.get("pass_id") or "").endswith(f"-{pids[0]}")
    )


def activate(job: dict, table: dict[str, str], release: Path, dry_run: bool,
             skip_busy: bool = False) -> bool:
    label = job["label"]
    path = LAUNCH_AGENTS / f"{label}.plist"
    body = plist_for(job, table)
    if dry_run:
        print(json.dumps(body, indent=1))
        return True
    # Persist the desired immutable release before the busy fence. The loaded
    # launchd definition is unchanged while a pass is live, but the next natural
    # gap must already have the new plist waiting on disk.
    Path(table["GIG_LOG_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(table["GIG_BRAKE_DIR"]).mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        plistlib.dump(body, handle)
    if skip_busy:
        # Booting out mid-pass kills the browser lease and leaves locks behind.  A
        # The next watcher tick can activate the new immutable release after a
        # natural gap, while this tick never creates a second owner. Continuous
        # lanes are deliberately reloadable because their durable outbox is the
        # restart boundary and they otherwise have no natural idle gap.
        running = is_running(label)
        brake_only = is_brake_only_process(label, table) if running else False
        if running and not brake_only:
            print(f"  {label}: still mid-pass, leaving it for the next tick")
            return True
        if brake_only:
            print(f"  {label}: brake-only receipt confirmed; migrating stable definition")

    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", f"{domain}/{label}"], capture_output=True)
    # bootout returns before launchd has finished unloading; bootstrapping into
    # the gap fails with "Input/output error" and leaves the lane down.
    for _ in range(50):
        if subprocess.run(["launchctl", "print", f"{domain}/{label}"],
                          capture_output=True).returncode != 0:
            break
        time.sleep(0.2)
    else:
        print(f"  {label}: still loaded after bootout, not bootstrapping")
        return False
    loaded = subprocess.run(["launchctl", "bootstrap", domain, str(path)],
                            capture_output=True, text=True)
    if loaded.returncode != 0:
        print(f"  {label}: bootstrap failed: {loaded.stderr.strip()}")
        return False

    # launchd runs the definition it loaded, so the file we just wrote proves
    # nothing. Compare what launchd hands back with what we meant to install.
    argv = loaded_program(label)
    if argv != body["ProgramArguments"]:
        print(f"  {label}: readback disagrees -> {argv or '(no program)'}")
        return False
    script = next((a for a in argv if a.endswith((".py", ".sh"))), "")
    print(f"  {label}: running {script}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("build", "activate", "status", "watch"))
    parser.add_argument("--sha", help="release this commit instead of HEAD")
    parser.add_argument("--jobs", help="comma-separated labels; default is the four lanes")
    parser.add_argument("--dry-run", action="store_true", help="print the plists, load nothing")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    if args.command == "watch":
        # The watcher only needs the immutable commit object.  Do not merge the
        # operator's checkout: a concurrent local commit or a temporary branch
        # divergence must not stop release publication after fetch succeeds.
        git("fetch", "--quiet", "origin", "main")
        sha = git("rev-parse", "origin/main")
        wanted = {job["label"] for job in manifest["jobs"]} - DEFAULT_EXCLUDED
        behind = [
            job for job in manifest["jobs"] if job["label"] in wanted
            and not any(str(CURRENT_RELEASE) in arg for arg in loaded_program(job["label"]))
        ]
        if current_sha() == sha and not behind:
            return 0
        release = build(sha)
        if current_sha() != sha:
            publish(release)
        print(f"release {sha[:12]} -> {release}")
        # SHA-specific definitions are migrated once. Stable definitions need no
        # deploy-time reload: their next process start follows CURRENT_RELEASE.
        if behind and not control_plane_available():
            print("launchd readback unavailable; current published, legacy jobs left running")
            return 0
        _, stable_table = settings(CURRENT_RELEASE)
        for job in behind:
            activate(job, stable_table, release, False,
                     skip_busy=job["label"] not in CONTINUOUS_RELOADABLE)
        return 0

    sha = git("rev-parse", args.sha or "HEAD")

    if args.command == "status":
        for job in manifest["jobs"]:
            argv = loaded_program(job["label"])
            script = next((a for a in argv if a.endswith((".py", ".sh"))), "(not loaded)")
            print(f"{job['lane']:11s} {job['label']:36s} {script}")
        return 0

    release = build(sha)
    print(f"release {sha[:12]} -> {release}")
    if args.command == "build":
        return 0

    if not args.dry_run:
        publish(release)
    wanted = ({label.strip() for label in args.jobs.split(",")} if args.jobs
              else {job["label"] for job in manifest["jobs"]} - DEFAULT_EXCLUDED)
    _, table = settings(CURRENT_RELEASE)
    failed = [job["label"] for job in manifest["jobs"] if job["label"] in wanted
              and not activate(job, table, release, args.dry_run)]
    if failed:
        print(f"not activated: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
