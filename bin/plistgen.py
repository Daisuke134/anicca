#!/usr/bin/env python3
"""Generate launchd jobs from each loop's own declaration.

241 launchd plists on this machine are hand-written with /Users/operator baked into them, which is
why none of them run on anyone else's Mac and why adding loop number 300 currently means writing
XML by hand. A loop should declare its cadence and its entrypoint; the paths belong to the machine
the job is installed on, so they are produced at generation time rather than committed.

  python3 bin/plistgen.py --loops-dir loops --out-dir ~/Library/LaunchAgents
  python3 bin/plistgen.py --loops-dir loops --out-dir /tmp/x --diff   # show, install nothing

Each loops/<name>/loop.toml:

    name      = "x-repost"
    state_dir = "~/loops/x-repost"

    [env]
    X_REPOST_BROWSER_IDENTITY = "x:anicca"

    [jobs.pass]
    program          = "skills/x-repost/x-repost-cli.sh"
    interval_seconds = 3600

    [jobs.digest]
    program  = "skills/x-repost/x-repost-digest.sh"
    calendar = { hour = 9, minute = 12 }
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import stat
import sys
import tomllib
from pathlib import Path

LABEL_PREFIX = "ai.anicca"
# launchd hands a job a minimal PATH. Homebrew covers python/tmux/openclaw, but npm-global
# binaries -- the model CLI among them -- live under ~/.local/bin, and leaving it out makes a loop
# depend on its own fallback guesswork instead of on its environment.
DEFAULT_PATH_PARTS = ("/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin",
                      "/usr/sbin", "/sbin", "{home}/.local/bin")


def expand(value: str, home: Path) -> str:
    return str(Path(os.path.expandvars(value.replace("~", str(home)))))


def normalized(path: Path) -> Path:
    """Resolve lexical and existing symlink components without requiring a target."""
    return Path(os.path.realpath(path))


def _is_descendant(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _has_worktree(path: Path) -> bool:
    return ".worktrees" in path.parts


def _source_checkout(loops_dir: Path) -> Path | None:
    loops = normalized(loops_dir)
    if loops.name == "loops" and (loops.parent / ".git").exists():
        return loops.parent
    if (loops / ".git").exists():
        return loops
    return None


def _reject_unsafe_path(path: Path, source_checkout: Path, description: str) -> None:
    lexical = Path(os.path.abspath(path))
    actual = normalized(path)
    if _has_worktree(lexical) or _has_worktree(actual):
        raise SystemExit(f"{description} resolves through a .worktrees path: {path}")
    source = normalized(source_checkout) if source_checkout is not None else None
    if source is not None and _is_descendant(actual, source):
        raise SystemExit(f"{description} resolves into the source checkout: {path}")


def _assert_sealed(release: Path) -> None:
    for path in [release, *release.rglob("*")]:
        if path.is_symlink():
            continue
        try:
            mode = path.stat().st_mode
        except OSError as error:
            raise SystemExit(f"agent-economy release cannot be inspected: {path}") from error
        if mode & 0o222:
            raise SystemExit(f"agent-economy release is writable: {path}")


def _source_manifest_payload(release: Path) -> dict:
    entries = []
    release_real = normalized(release)
    for path in sorted(release.rglob("*")):
        relative = path.relative_to(release).as_posix()
        if relative in {"RELEASE.json", "SOURCE-MANIFEST.json", "DEPENDENCY-MANIFEST.tsv"} or relative.startswith("node_modules/"):
            continue
        item = path.lstat()
        if stat.S_ISREG(item.st_mode):
            entries.append({
                "path": relative,
                "mode": format(stat.S_IMODE(item.st_mode) & 0o555, "04o"),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
        elif stat.S_ISLNK(item.st_mode):
            target = os.readlink(path)
            target_real = normalized(path)
            if not _is_descendant(target_real, release_real):
                raise SystemExit(f"agent-economy source symlink escapes release: {relative}")
            entries.append({
                "path": relative,
                "mode": "0000",
                "sha256": hashlib.sha256(target.encode()).hexdigest(),
                "target": target,
            })
    return {"version": 1, "entries": entries}


def _assert_source_manifest(release: Path, metadata: dict) -> None:
    manifest_path = release / "SOURCE-MANIFEST.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise SystemExit(f"agent-economy source manifest is missing: {manifest_path}")
    try:
        raw = manifest_path.read_bytes()
        manifest = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise SystemExit("agent-economy source manifest is invalid") from error
    encoded = (json.dumps(_source_manifest_payload(release), sort_keys=True, separators=(",", ":")) + "\n").encode()
    if raw != encoded or hashlib.sha256(raw).hexdigest() != str(metadata.get("source_manifest_sha256", "")):
        raise SystemExit("agent-economy source manifest does not match the sealed release")
    if manifest != json.loads(encoded.decode("utf-8")):
        raise SystemExit("agent-economy source manifest entries are invalid")


def _dependency_manifest_bytes(release: Path) -> bytes:
    node_modules = release / "node_modules"
    if not node_modules.is_dir() or node_modules.is_symlink():
        raise SystemExit("agent-economy release node_modules is missing")
    node_modules_real = normalized(node_modules)
    lines = []
    for path in sorted(node_modules.rglob("*"), key=lambda item: item.relative_to(release).as_posix()):
        relative = path.relative_to(release).as_posix()
        item = path.lstat()
        if stat.S_ISLNK(item.st_mode):
            target_real = normalized(path)
            if not _is_descendant(target_real, node_modules_real):
                raise SystemExit("agent-economy dependency symlink escapes node_modules")
            lines.append(f"symlink\t{relative}\t{format(stat.S_IMODE(path.stat().st_mode) & 0o555, 'o')}\t-\t{os.readlink(path)}")
        elif stat.S_ISREG(item.st_mode):
            lines.append(f"file\t{relative}\t{format(stat.S_IMODE(item.st_mode) & 0o555, 'o')}\t{hashlib.sha256(path.read_bytes()).hexdigest()}\t-")
    return ("\n".join(lines) + ("\n" if lines else "")).encode()


def _assert_dependency_manifest(release: Path, metadata: dict) -> None:
    manifest_path = release / "DEPENDENCY-MANIFEST.tsv"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise SystemExit(f"agent-economy dependency manifest is missing: {manifest_path}")
    try:
        raw = manifest_path.read_bytes()
    except OSError as error:
        raise SystemExit("agent-economy dependency manifest cannot be read") from error
    expected = _dependency_manifest_bytes(release)
    digest = str(metadata.get("dependency_tree_manifest_sha256", ""))
    if raw != expected or hashlib.sha256(raw).hexdigest() != digest:
        raise SystemExit("agent-economy dependency manifest does not match the sealed release")


def _release_metadata(current: Path, release_root: Path) -> tuple[Path, dict]:
    if not current.is_symlink():
        raise SystemExit(f"agent-economy current must be a symlink: {current}")
    try:
        release = current.resolve(strict=True)
    except OSError as error:
        raise SystemExit(f"agent-economy current target is unavailable: {current}") from error
    root = normalized(release_root)
    releases = normalized(root / "releases")
    if release.parent != releases:
        raise SystemExit(f"agent-economy current escapes the namespaced releases root: {current}")
    metadata_path = release / "RELEASE.json"
    if not metadata_path.is_file() or metadata_path.is_symlink():
        raise SystemExit(f"agent-economy release metadata is missing: {metadata_path}")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"agent-economy release metadata is invalid: {metadata_path}") from error
    if not isinstance(metadata, dict):
        raise SystemExit(f"agent-economy release metadata must be an object: {metadata_path}")
    try:
        metadata_root = normalized(Path(str(metadata["release_root"])))
        release_id = str(metadata["release_id"])
        sha = str(metadata["sha"])
        namespace = str(metadata["namespace"])
    except (KeyError, TypeError, ValueError) as error:
        raise SystemExit("agent-economy RELEASE.json is missing identity metadata") from error
    if metadata_root != root:
        raise SystemExit("agent-economy RELEASE.json release_root does not match the selected namespace")
    if metadata.get("current") and normalized(Path(str(metadata["current"]))) != normalized(current):
        raise SystemExit("agent-economy RELEASE.json current pointer does not match the selected current")
    if release_id != release.name or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise SystemExit("agent-economy RELEASE.json identity does not match its release directory")
    if metadata.get("git_commit") != sha:
        raise SystemExit("agent-economy RELEASE.json git_commit does not match its sha")
    if not (release.name == sha or release.name.endswith(f"-{sha[:8]}")):
        raise SystemExit("agent-economy RELEASE.json sha does not match its release directory")
    if namespace != "life-manager":
        raise SystemExit("agent-economy RELEASE.json namespace is not life-manager")
    if not re.fullmatch(r"[0-9a-f]{64}", str(metadata.get("source_manifest_sha256", ""))):
        raise SystemExit("agent-economy RELEASE.json source manifest digest is missing")
    if not re.fullmatch(r"[0-9a-f]{64}", str(metadata.get("dependency_tree_manifest_sha256", ""))):
        raise SystemExit("agent-economy RELEASE.json dependency manifest digest is missing")
    _assert_source_manifest(release, metadata)
    _assert_dependency_manifest(release, metadata)
    _assert_sealed(release)
    return release, metadata


def _current_for_loop(loop: dict, home: Path, explicit: Path | None) -> tuple[Path, Path | None]:
    release_root_value = loop.get("release_root")
    if explicit is not None:
        current = explicit
    elif release_root_value:
        current = Path(expand(str(release_root_value), home)) / "current"
    else:
        current = home / "loops" / "current"
    release_root = Path(expand(str(release_root_value), home)) if release_root_value else None
    if release_root is None and current.parent.name == "life-manager":
        release_root = current.parent
    return current, release_root


def build(loop: dict, job_name: str, job: dict, home: Path, current: Path, logs: Path,
          code_root: Path | None = None, metadata: dict | None = None) -> dict:
    name = loop["name"]
    # A migration must not rename. Labels on this machine follow no single convention
    # (ai.anicca.hf-gig-apply-direct, ai.anicca.bounty-core-healthcheck, ai.anicca.hf-bounty-daily),
    # and they are referenced by healthchecks, self-heal scripts, tests and docs. Renaming while
    # moving a loop would break those quietly, at the same moment its code moved -- two changes to
    # untangle instead of one. An existing loop declares the label it already answers to; only new
    # loops take the generated convention.
    label = job.get("label") or f"{LABEL_PREFIX}.{name}-{job_name}"

    default_path = ":".join(p.format(home=home) for p in DEFAULT_PATH_PARTS)
    env = {"HOME": str(home), "PATH": job.get("path", default_path)}
    if loop.get("state_dir"):
        # Every loop needs to be told where its own state lives, because the code it runs from is a
        # read-only release and must not be the place a ledger accumulates.
        env[loop.get("state_env", f"{name.upper().replace('-', '_')}_STATE_DIR")] = \
            expand(loop["state_dir"], home)
    env.update({k: expand(str(v), home) for k, v in (loop.get("env") or {}).items()})
    env.update({k: expand(str(v), home) for k, v in (job.get("env") or {}).items()})
    if metadata is not None:
        env["ANICCA_REPO"] = str(code_root or current)
        env["ANICCA_CODE_ROOT"] = str(code_root or current)
        env["ANICCA_RELEASE_ROOT"] = str(current.parent)
        env["ANICCA_RELEASE_ID"] = str(metadata["release_id"])
        env["ANICCA_RELEASE_SHA"] = str(metadata["sha"])

    plist = {
        "Label": label,
        "ProgramArguments": ["/bin/bash", str((code_root or current) / job["program"])],
        "ProcessType": job.get("process_type", "Background"),
        "ThrottleInterval": int(job.get("throttle_seconds", 60)),
        "WorkingDirectory": str(home),
        "EnvironmentVariables": env,
        "StandardOutPath": str(logs / f"{name}-{job_name}.out.log"),
        "StandardErrorPath": str(logs / f"{name}-{job_name}.err.log"),
    }

    continuous = bool(job.get("keep_alive", False))
    has_cadence = "interval_seconds" in job or "calendar" in job
    if continuous and has_cadence:
        raise SystemExit(f"{label}: continuous jobs cannot also define interval_seconds or calendar")
    if continuous:
        plist["KeepAlive"] = True
        if job.get("run_at_load", True):
            plist["RunAtLoad"] = True
    elif "interval_seconds" in job:
        plist["StartInterval"] = int(job["interval_seconds"])
    elif "calendar" in job:
        cal = job["calendar"]
        plist["StartCalendarInterval"] = {k.capitalize(): int(v) for k, v in cal.items()}
    else:
        raise SystemExit(f"{label}: needs interval_seconds or calendar")

    return plist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loops-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--home", default=str(Path.home()))
    ap.add_argument("--current", default=None,
                    help="current release symlink (default from loop declaration, or ~/loops/current)")
    ap.add_argument("--logs", default=None)
    ap.add_argument("--only", help="generate a single loop by name")
    ap.add_argument("--diff", action="store_true", help="print what would change, write nothing")
    args = ap.parse_args()

    home = Path(args.home)
    explicit_current = Path(expand(args.current, home)) if args.current else None
    logs = Path(args.logs) if args.logs else home / ".openclaw" / "logs"
    out_dir = Path(expand(args.out_dir, home))
    source_checkout = _source_checkout(Path(args.loops_dir))

    # Build and validate every plist before writing any one of them. A malformed release target in
    # a later loop must not leave a partially regenerated LaunchAgents directory behind.
    plans = []
    for toml_path in sorted(Path(args.loops_dir).glob("*/loop.toml")):
        loop = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        if args.only and loop.get("name") != args.only:
            continue
        current, release_root = _current_for_loop(loop, home, explicit_current)
        for job_name, job in (loop.get("jobs") or {}).items():
            program = Path(expand(str(job["program"]), home))
            if not program.is_absolute():
                program = current / program
            _reject_unsafe_path(current, source_checkout, f"{loop.get('name', 'loop')} current")
            _reject_unsafe_path(program, source_checkout, f"{loop.get('name', 'loop')} program")
            metadata = None
            if loop.get("name") == "agent-economy":
                if release_root is None:
                    release_root = current.parent
                code_root, metadata = _release_metadata(current, release_root)
            else:
                code_root = current
            plist = build(loop, job_name, job, home, current, logs, code_root, metadata)
            target = out_dir / f"{plist['Label']}.plist"
            body = plistlib.dumps(plist, sort_keys=True)
            plans.append((target, body, plist["Label"]))

    written = []
    for target, body, label in plans:
        existing = target.read_bytes() if target.exists() else None
        if args.diff:
            state = "unchanged" if existing == body else ("new" if existing is None else "CHANGED")
            print(f"{state:>9}  {target}")
            continue
        if existing == body:
            written.append((label, "unchanged"))
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        try:
            temporary.write_bytes(body)
            os.replace(temporary, target)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        written.append((label, "written"))

    for label, state in written:
        print(f"{state:>9}  {label}")
    if not written and not args.diff:
        print("no loop.toml found", file=sys.stderr)


if __name__ == "__main__":
    main()
