"""PURE helpers for install-proactive-plist (sprint-3 #30).

Single source of truth (FIND-007 fix). The shell front-end calls into this
module via `python3 -m lib.plist_render <subcmd>` and never re-implements
validate/render/parse logic in bash.
"""
from __future__ import annotations
import hashlib
import re
import sys
from pathlib import Path
from typing import Optional

# REQ-A2: resolve the checked-out OSS framework repo, independent of username or install path.
CANONICAL_ANICCA_HOME = str(Path(__file__).resolve().parents[3])

_SLOT_RE = re.compile(r"^[a-z0-9_-]{1,32}$")


class SlotValidationError(ValueError):
    """REQ-A4: slot argument fails [a-z0-9_-]{1,32}."""


def validate_slot(slot: str) -> None:
    """Raise SlotValidationError if slot is empty / oversize / contains shell metas.

    Must be called BEFORE any filesystem or launchctl side-effect (REQ-A4
    ordering invariant). The shell wrapper invokes this first; render_plist
    also re-validates for defense in depth.
    """
    if not isinstance(slot, str) or not _SLOT_RE.match(slot):
        raise SlotValidationError(
            f"invalid slot: {slot!r} (must match [a-z0-9_-]{{1,32}})"
        )


def render_plist(*, slot: str, anicca_home: str, log_dir: str,
                 plist_path: str) -> str:
    """Render the launchd plist XML for a slot.

    All path inputs MUST be absolute and pre-expanded by the caller — launchd
    does NOT expand $HOME / ~ tokens (FIND-002). plist_path is included in the
    signature so the caller is reminded that the file lives at an absolute
    path that must already be resolved.
    """
    validate_slot(slot)
    if not anicca_home.startswith("/") or not log_dir.startswith("/") or not plist_path.startswith("/"):
        raise ValueError("anicca_home, log_dir, plist_path must be absolute paths")

    label = f"ai.anicca.{slot}-proactive"
    program = f"{anicca_home}/skills/_shared/proactive-loop.sh"
    out_path = f"{log_dir}/{slot}-proactive.out"
    err_path = f"{log_dir}/{slot}-proactive.err"

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        '<dict>\n'
        f'  <key>Label</key><string>{label}</string>\n'
        '  <key>ProgramArguments</key>\n'
        '  <array>\n'
        '    <string>/bin/bash</string>\n'
        f'    <string>{program}</string>\n'
        f'    <string>{slot}</string>\n'
        '  </array>\n'
        '  <key>StartInterval</key><integer>300</integer>\n'
        '  <key>RunAtLoad</key><false/>\n'
        f'  <key>StandardOutPath</key><string>{out_path}</string>\n'
        f'  <key>StandardErrorPath</key><string>{err_path}</string>\n'
        '</dict>\n'
        '</plist>\n'
    )


def plist_digest(content: str) -> str:
    """Stable hex digest for idempotent install (PROP-B1)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


_PATH_RE = re.compile(r"^\s*path\s*=\s*(.+?)\s*$", re.MULTILINE)


def parse_loaded_plist_path(launchctl_print_output: str) -> Optional[str]:
    """REQ-E2: extract the `path = ...` line from `launchctl print` output.

    Returns the absolute path string or None if no path line present.
    """
    m = _PATH_RE.search(launchctl_print_output)
    return m.group(1).strip() if m else None


# ─── CLI entrypoint so the shell can call us without import ─────────
def _cli(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: plist_render.py <validate|render|digest|parse-path>", file=sys.stderr)
        return 2
    cmd = argv[1]
    try:
        if cmd == "validate":
            validate_slot(argv[2])
            return 0
        if cmd == "render":
            # render <slot> <anicca_home> <log_dir> <plist_path>
            print(render_plist(
                slot=argv[2], anicca_home=argv[3],
                log_dir=argv[4], plist_path=argv[5],
            ), end="")
            return 0
        if cmd == "digest":
            print(plist_digest(sys.stdin.read()))
            return 0
        if cmd == "parse-path":
            r = parse_loaded_plist_path(sys.stdin.read())
            if r is None:
                return 1
            print(r)
            return 0
    except SlotValidationError as e:
        print(str(e), file=sys.stderr)
        return 3
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        return 4
    print(f"unknown subcommand: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
