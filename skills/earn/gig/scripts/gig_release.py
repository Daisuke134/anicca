#!/usr/bin/env python3
"""Cut a release of this checkout and point the coconala launchd jobs at it.

A lane never runs from a working tree: a git checkout changes under a job that
is mid-pass, so every lane runs from an immutable copy under
``~/gig/releases/life-manager/<sha>``. This builds that copy and rewrites the
launchd jobs to use it.

The jobs themselves are data -- ``config/launchd-jobs.json`` -- rendered against
per-machine values from ``~/.config/anicca/gig/install.json``. That is what lets
a Mac that has never run this loop install the same four jobs, and lets this one
keep the exact paths its lanes already use.

launchd runs the definition it loaded, not the file on disk, so activation is
always bootout + bootstrap, then a ``launchctl print`` readback that proves the
loaded job really is the new release.

    gig_release.py build                 # release the current HEAD
    gig_release.py activate              # build if needed, then switch the four lanes
    gig_release.py activate --jobs ai.anicca.hf-gig-browser
    gig_release.py status
"""

from __future__ import annotations

import argparse
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
GIG_DIR = HERE.parent
REPO_ROOT = GIG_DIR.parents[2]
MANIFEST = GIG_DIR / "config" / "launchd-jobs.json"
OVERRIDES = Path(
    os.environ.get("GIG_INSTALL_OVERRIDES", Path.home() / ".config/anicca/gig/install.json")
)
LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
# The browser owns the one authenticated session the lanes share. Reloading it
# throws that session away, so it is never in the default set.
DEFAULT_EXCLUDED = {"ai.anicca.hf-gig-browser", "ai.anicca.hf-gig-release-watch"}
PLACEHOLDER = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


def git(*args: str, cwd: Path = REPO_ROOT) -> str:
    return subprocess.run(("git", *args), cwd=cwd, check=True,
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
    return Path.home() / "gig" / "releases" / "life-manager" / sha


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


def is_running(label: str) -> bool:
    printed = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{label}"],
                             capture_output=True, text=True)
    return "state = running" in printed.stdout


def activate(job: dict, table: dict[str, str], release: Path, dry_run: bool,
             skip_busy: bool = False) -> bool:
    label = job["label"]
    path = LAUNCH_AGENTS / f"{label}.plist"
    body = plist_for(job, table)
    if dry_run:
        print(json.dumps(body, indent=1))
        return True
    if skip_busy:
        # Booting out mid-pass kills the browser lease and leaves locks behind, so
        # wait for the gap between passes. A lane whose pass is long and whose
        # interval is short is idle only briefly, and a watcher that only sampled
        # once would keep missing that window forever.
        for _ in range(60):
            if not is_running(label):
                break
            time.sleep(5)
        else:
            print(f"  {label}: still mid-pass, leaving it for the next tick")
            return True

    Path(table["GIG_LOG_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(table["GIG_BRAKE_DIR"]).mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        plistlib.dump(body, handle)

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
        # Fast-forward only: a lane must never run a merge nobody wrote down.
        git("fetch", "--quiet", "origin", "main")
        if git("rev-parse", "HEAD") != git("rev-parse", "origin/main"):
            git("merge", "--ff-only", "--quiet", "origin/main")
        sha = git("rev-parse", "HEAD")
        wanted = {job["label"] for job in manifest["jobs"]} - DEFAULT_EXCLUDED
        behind = [job for job in manifest["jobs"] if job["label"] in wanted
                  and not next((a for a in loaded_program(job["label"])
                                if a.endswith((".py", ".sh"))), "").startswith(
                                    str(release_dir(sha)))]
        if not behind:
            return 0
        release = build(sha)
        print(f"release {sha[:12]} -> {release}")
        for job in behind:
            activate(job, settings(release)[1], release, False, skip_busy=True)
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

    wanted = ({label.strip() for label in args.jobs.split(",")} if args.jobs
              else {job["label"] for job in manifest["jobs"]} - DEFAULT_EXCLUDED)
    _, table = settings(release)
    failed = [job["label"] for job in manifest["jobs"] if job["label"] in wanted
              and not activate(job, table, release, args.dry_run)]
    if failed:
        print(f"not activated: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
