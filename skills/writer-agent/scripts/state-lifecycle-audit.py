#!/usr/bin/env python3
"""State lifecycle audit — WRITER-AGENT-SSOT §9.3 R1.

Resolves every path under the Writer state root and the Writer log root to
exactly one lifecycle class using the committed registry
`config/state-lifecycle.json`:

    immutable-receipt   publication receipt, money row, claim, opportunity
                        evidence, learning receipt, state migration record,
                        or credential. MUST NOT be deleted, moved, or
                        rewritten by any prune path.
    derived-artifact    regenerable output (model stdout logs, generated
                        images, candidate media, judge broker scratch,
                        interrupted generation attempts).
    transient-log       launchd stdout/stderr and the wrapper-redirected run
                        streams that sit beside them.

Fail-safe: a path that no registry entry and no registry rule covers resolves
to `immutable-receipt`. The default lives in the registry
(`default_class`) and is applied here in code, never as a comment.

THIS TOOL IS READ-ONLY. It never deletes, moves, truncates, or rewrites any
path under the state root or the log root. Its only write is the optional
`--manifest-out` file, which it refuses to place inside either root.

Resolution order for a path (relative to its root):
    1. the first matching rule in `path_rules` (ordered, most specific first);
    2. otherwise the registry entry for its first path segment (inherited);
    3. otherwise `default_class` (the fail-safe), recorded as a fall-through.

Exit codes:
    0  every existing top-level path is covered by the registry
    1  at least one existing top-level path is missing from the registry
    2  usage or registry error
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Iterable

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = SKILL_ROOT / "config" / "state-lifecycle.json"
CLASSES = ("immutable-receipt", "derived-artifact", "transient-log")
READ_CHUNK = 1024 * 1024


# --------------------------------------------------------------------------
# glob matching: `*` and `?` inside one segment, `**` across segments
# --------------------------------------------------------------------------

def _match_segments(pattern: list[str], parts: list[str]) -> bool:
    if not pattern:
        return not parts
    head, rest = pattern[0], pattern[1:]
    if head == "**":
        if not rest:
            return True
        for i in range(len(parts) + 1):
            if _match_segments(rest, parts[i:]):
                return True
        return False
    if not parts:
        return False
    if not fnmatch.fnmatchcase(parts[0], head):
        return False
    return _match_segments(rest, parts[1:])


def glob_match(pattern: str, relpath: str) -> bool:
    return _match_segments(pattern.split("/"), relpath.split("/"))


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------

class Registry:
    def __init__(self, data: dict, source: Path):
        self.source = source
        self.data = data
        self.policy_version = data["policy_version"]
        self.default_class = data["default_class"]
        self.default_reason = data.get("default_reason", "fail-safe default")
        if self.default_class != "immutable-receipt":
            raise ValueError(
                "default_class MUST be immutable-receipt (§9.3 fail-safe rule); "
                f"registry says {self.default_class!r}"
            )
        self.roots: dict[str, dict] = {}
        for name, spec in data["roots"].items():
            entries = {e["path"]: e for e in spec.get("entries", [])}
            rules = list(spec.get("path_rules", []))
            for holder in (entries.values(), rules):
                for item in holder:
                    if item["class"] not in CLASSES:
                        raise ValueError(f"unknown class {item['class']!r} in {name}")
            self.roots[name] = {
                "spec": spec,
                "entries": entries,
                "rules": rules,
                # A root may declare which top-level names belong to the Writer.
                # Anything else in that directory is owned by another loop and is
                # explicitly out of scope for §9.3 (see its Boundaries section).
                "include": list(spec.get("include_top_level", [])),
            }

    @classmethod
    def load(cls, path: Path) -> "Registry":
        return cls(json.loads(path.read_text(encoding="utf-8")), path)

    def default_root_path(self, root: str) -> Path:
        spec = self.roots[root]["spec"]
        raw = spec["default_path"]
        if spec.get("relative_to") == "skill_root":
            return (SKILL_ROOT / raw).resolve()
        return Path(os.path.expanduser(os.path.expandvars(raw)))

    def classify(self, root: str, relpath: str) -> dict:
        cfg = self.roots[root]
        exact = cfg["entries"].get(relpath)
        if exact is not None:
            return {
                "class": exact["class"],
                "reason": exact["reason"],
                "basis": exact.get("basis", "spec-rule"),
                "matched": relpath,
                "matched_kind": "entry",
            }
        for rule in cfg["rules"]:
            if glob_match(rule["pattern"], relpath):
                return {
                    "class": rule["class"],
                    "reason": rule["reason"],
                    "basis": rule.get("basis", "spec-rule"),
                    "matched": rule["pattern"],
                    "matched_kind": "rule",
                }
        top = relpath.split("/", 1)[0]
        entry = cfg["entries"].get(top)
        if entry is not None:
            return {
                "class": entry["class"],
                "reason": entry["reason"],
                "basis": entry.get("basis", "spec-rule"),
                "matched": top,
                "matched_kind": "entry",
            }
        return {
            "class": self.default_class,
            "reason": self.default_reason,
            "basis": "fail-safe-default",
            "matched": None,
            "matched_kind": "fail-safe",
        }

    def in_scope(self, root: str, top_level_name: str) -> bool:
        include = self.roots[root]["include"]
        if not include:
            return True
        return any(fnmatch.fnmatchcase(top_level_name, g) for g in include)

    def covered_top_level(self, root: str, name: str) -> bool:
        cfg = self.roots[root]
        if name in cfg["entries"]:
            return True
        probe = f"{name}/__coverage_probe__"
        for rule in cfg["rules"]:
            if glob_match(rule["pattern"], name) or glob_match(rule["pattern"], probe):
                return True
        return False


# --------------------------------------------------------------------------
# walking
# --------------------------------------------------------------------------

def iter_files(root: Path, keep=None) -> Iterable[tuple[str, Path, int]]:
    """Yield (relpath, abspath, size) for every regular file. Symlinks skipped."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        at_root = Path(dirpath) == root
        dirnames[:] = [
            d for d in sorted(dirnames)
            if not os.path.islink(os.path.join(dirpath, d))
            and (keep is None or not at_root or keep(d))
        ]
        if at_root and keep is not None:
            filenames = [f for f in filenames if keep(f)]
        for name in sorted(filenames):
            abspath = Path(dirpath) / name
            if abspath.is_symlink():
                continue
            try:
                size = abspath.stat().st_size
            except OSError:
                continue
            yield (abspath.relative_to(root).as_posix(), abspath, size)


def count_symlinks(root: Path, keep=None) -> int:
    total = 0
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        at_root = Path(dirpath) == root
        if at_root and keep is not None:
            dirnames[:] = [d for d in dirnames if keep(d)]
            filenames = [f for f in filenames if keep(f)]
        for name in list(dirnames):
            if os.path.islink(os.path.join(dirpath, name)):
                total += 1
                dirnames.remove(name)
        for name in filenames:
            if os.path.islink(os.path.join(dirpath, name)):
                total += 1
    return total


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(READ_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


# --------------------------------------------------------------------------
# audit
# --------------------------------------------------------------------------

def audit_root(registry: Registry, root_name: str, root: Path, want_manifest: bool):
    summary = {c: {"files": 0, "bytes": 0} for c in CLASSES}
    fail_safe_paths: list[str] = []
    manifest: list[dict] = []
    resolved: dict[str, dict] = {}

    keep = lambda name: registry.in_scope(root_name, name)  # noqa: E731

    for relpath, abspath, size in iter_files(root, keep):
        verdict = registry.classify(root_name, relpath)
        resolved[relpath] = verdict
        cls = verdict["class"]
        summary[cls]["files"] += 1
        summary[cls]["bytes"] += size
        if verdict["matched_kind"] == "fail-safe":
            fail_safe_paths.append(relpath)
        if want_manifest and cls == "immutable-receipt":
            manifest.append(
                {
                    "root": root_name,
                    "path": relpath,
                    "bytes": size,
                    "sha256": sha256_of(abspath),
                }
            )

    on_disk = sorted(p.name for p in root.iterdir() if keep(p.name))
    unregistered = [n for n in on_disk if not registry.covered_top_level(root_name, n)]
    listed = set(registry.roots[root_name]["entries"])
    rule_only = [
        n for n in on_disk
        if n not in listed and registry.covered_top_level(root_name, n)
    ]
    absent = sorted(listed - set(on_disk))

    return {
        "root": str(root),
        "summary": summary,
        "fail_safe_default_paths": sorted(fail_safe_paths),
        "unregistered_top_level": unregistered,
        "covered_by_rule_not_listed": rule_only,
        "listed_but_absent_on_disk": absent,
        "top_level_on_disk": len(on_disk),
        "symlinks_skipped": count_symlinks(root, keep),
        "manifest": manifest,
        "resolved": resolved,
    }


def entries_assigned_by_fail_safe(registry: Registry, root_name: str) -> list[dict]:
    return [
        {"path": e["path"], "class": e["class"], "reason": e["reason"]}
        for e in registry.roots[root_name]["entries"].values()
        if e.get("basis") == "fail-safe-default"
    ]


def human_bytes(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:,.1f} {unit}" if unit != "B" else f"{int(value):,} B"
        value /= 1024
    return f"{value:,.1f} GB"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify every Writer state and log path (read-only).",
    )
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--state-root")
    parser.add_argument("--log-root")
    parser.add_argument(
        "--manifest-out",
        help="write a deterministic SHA-256 manifest of every immutable-receipt file",
    )
    parser.add_argument("--explain", action="append", default=[],
                        help="report the resolved class of one state-relative path")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-listed", type=int, default=40,
                        help="cap for path lists in the text summary (0 = no cap)")
    args = parser.parse_args(argv)

    registry_path = Path(args.registry)
    if not registry_path.is_file():
        print(f"registry not found: {registry_path}", file=sys.stderr)
        return 2
    try:
        registry = Registry.load(registry_path)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"invalid registry {registry_path}: {exc}", file=sys.stderr)
        return 2

    roots: dict[str, Path] = {}
    for name, override in (("state", args.state_root), ("logs", args.log_root)):
        path = Path(override).expanduser() if override else registry.default_root_path(name)
        roots[name] = path

    manifest_out = Path(args.manifest_out).resolve() if args.manifest_out else None
    if manifest_out is not None:
        for name, path in roots.items():
            try:
                manifest_out.relative_to(path.resolve())
            except (ValueError, OSError):
                continue
            print(
                f"refusing to write the manifest inside the {name} root: {manifest_out}",
                file=sys.stderr,
            )
            return 2

    report: dict = {
        "policy_version": registry.policy_version,
        "registry": str(registry_path),
        "roots": {},
        "summary": {c: {"files": 0, "bytes": 0} for c in CLASSES},
        "unregistered_top_level": [],
        "fail_safe_default_paths": [],
        "fail_safe_default_entries": [],
        "explain": {},
    }

    results: dict[str, dict] = {}
    manifest_rows: list[dict] = []
    for name, path in roots.items():
        if not path.is_dir():
            report["roots"][name] = {"path": str(path), "present": False}
            continue
        result = audit_root(registry, name, path, want_manifest=manifest_out is not None)
        results[name] = result
        manifest_rows.extend(result["manifest"])
        for cls in CLASSES:
            report["summary"][cls]["files"] += result["summary"][cls]["files"]
            report["summary"][cls]["bytes"] += result["summary"][cls]["bytes"]
        report["unregistered_top_level"] += result["unregistered_top_level"]
        report["fail_safe_default_paths"] += [
            f"{p}" if name == "state" else f"logs:{p}"
            for p in result["fail_safe_default_paths"]
        ]
        report["fail_safe_default_entries"] += [
            {**e, "root": name} for e in entries_assigned_by_fail_safe(registry, name)
        ]
        report["roots"][name] = {
            "path": str(path),
            "present": True,
            "summary": result["summary"],
            "top_level_on_disk": result["top_level_on_disk"],
            "top_level_listed": len(registry.roots[name]["entries"]),
            "unregistered_top_level": result["unregistered_top_level"],
            "covered_by_rule_not_listed": result["covered_by_rule_not_listed"],
            "listed_but_absent_on_disk": result["listed_but_absent_on_disk"],
            "symlinks_skipped": result["symlinks_skipped"],
        }

    for target in args.explain:
        root_name = "logs" if target.startswith("logs:") else "state"
        rel = target[5:] if target.startswith("logs:") else target
        report["explain"][target] = registry.classify(root_name, rel)

    exit_code = 1 if report["unregistered_top_level"] else 0

    if manifest_out is not None:
        manifest_rows.sort(key=lambda row: (row["root"], row["path"]))
        payload = {
            "policy_version": registry.policy_version,
            "class": "immutable-receipt",
            "roots": {n: str(p) for n, p in roots.items()},
            "file_count": len(manifest_rows),
            "total_bytes": sum(r["bytes"] for r in manifest_rows),
            "files": manifest_rows,
        }
        manifest_out.parent.mkdir(parents=True, exist_ok=True)
        manifest_out.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        report["manifest_out"] = {
            "path": str(manifest_out),
            "file_count": payload["file_count"],
            "total_bytes": payload["total_bytes"],
        }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return exit_code

    cap = None if args.max_listed <= 0 else args.max_listed
    print(f"state-lifecycle-audit  policy {registry.policy_version}")
    print(f"registry: {registry_path}")
    for name in ("state", "logs"):
        info = report["roots"].get(name, {})
        mark = "" if info.get("present") else "  (ABSENT)"
        print(f"root[{name}]: {info.get('path', '-')}{mark}")
    print()
    print(f"{'class':<20}{'files':>10}{'bytes':>16}{'size':>14}")
    for cls in CLASSES:
        row = report["summary"][cls]
        print(f"{cls:<20}{row['files']:>10,}{row['bytes']:>16,}{human_bytes(row['bytes']):>14}")
    total_files = sum(report["summary"][c]["files"] for c in CLASSES)
    total_bytes = sum(report["summary"][c]["bytes"] for c in CLASSES)
    print(f"{'TOTAL':<20}{total_files:>10,}{total_bytes:>16,}{human_bytes(total_bytes):>14}")
    print()

    for name in ("state", "logs"):
        info = report["roots"].get(name)
        if not info or not info.get("present"):
            continue
        print(
            f"[{name}] top-level on disk {info['top_level_on_disk']}, "
            f"listed in registry {info['top_level_listed']}, "
            f"unregistered {len(info['unregistered_top_level'])}, "
            f"covered by rule but not listed {len(info['covered_by_rule_not_listed'])}, "
            f"listed but absent {len(info['listed_but_absent_on_disk'])}, "
            f"symlinks skipped {info['symlinks_skipped']}"
        )
        for label, key in (
            ("UNREGISTERED", "unregistered_top_level"),
            ("rule-covered drift", "covered_by_rule_not_listed"),
        ):
            values = info[key]
            if values:
                shown = values if cap is None else values[:cap]
                print(f"  {label}: {', '.join(shown)}"
                      + ("" if cap is None or len(values) <= cap
                         else f" ... (+{len(values) - cap} more)"))
    print()

    fs_entries = report["fail_safe_default_entries"]
    print(f"fail-safe default (unclassified -> {registry.default_class})")
    print(f"  registry entries assigned by the fail-safe default: {len(fs_entries)}")
    for entry in (fs_entries if cap is None else fs_entries[:cap]):
        print(f"    {entry['root']}:{entry['path']}")
    if cap is not None and len(fs_entries) > cap:
        print(f"    ... (+{len(fs_entries) - cap} more)")
    fs_paths = report["fail_safe_default_paths"]
    print(f"  paths that fell through to the fail-safe default: {len(fs_paths)}")
    for path in (fs_paths if cap is None else fs_paths[:cap]):
        print(f"    {path}")
    if cap is not None and len(fs_paths) > cap:
        print(f"    ... (+{len(fs_paths) - cap} more)")

    if "manifest_out" in report:
        info = report["manifest_out"]
        print()
        print(
            f"manifest: {info['path']}  files={info['file_count']:,}  "
            f"bytes={info['total_bytes']:,} ({human_bytes(info['total_bytes'])})"
        )

    if args.explain:
        print()
        print("explain:")
        for target, verdict in report["explain"].items():
            print(f"  {target}")
            print(f"    class={verdict['class']}  basis={verdict['basis']}  "
                  f"matched={verdict['matched']} ({verdict['matched_kind']})")
            print(f"    reason={verdict['reason']}")

    if exit_code:
        print()
        print(
            f"FAIL: {len(report['unregistered_top_level'])} existing top-level "
            f"path(s) are missing from the registry",
            file=sys.stderr,
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
