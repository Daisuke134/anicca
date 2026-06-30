"""PURE observer for proactive-loop per-slot state — used by gig run.sh shim.

REQ-S2..S5 + EDGE-E2/E5 from gig-run-shim spec. Read-only; ZERO writes.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, TypedDict


class ObserveResult(TypedDict):
    installed: bool
    last_pass_ts: Optional[int]
    last_pass_step: Optional[str]
    build_log_passes: int


def summarize_loops_dir(
    loops_dir: Path | str,
    plist_path: Path | str,
    *,
    launchctl_print_rc: int,
) -> ObserveResult:
    """Read-only summary of `~/loops/<slot>/` + plist load state.

    Args:
        loops_dir: e.g. ~/loops/gig
        plist_path: e.g. ~/Library/LaunchAgents/ai.anicca.gig-proactive.plist
        launchctl_print_rc: caller-provided result of `launchctl print gui/<uid>/<label>`

    Returns:
        4-key dict with installed bool, last_pass_ts int|None,
        last_pass_step str|None, build_log_passes int.
    """
    loops = Path(loops_dir)
    plist = Path(plist_path)

    # REQ-S3: BOTH disk AND launchctl rc=0
    installed = plist.exists() and launchctl_print_rc == 0

    last_pass_ts: Optional[int] = None
    last_pass_step: Optional[str] = None
    cs = loops / "state" / "core-status.json"
    if cs.exists():
        try:
            d = json.loads(cs.read_text())
            v = d.get("ts")
            last_pass_ts = int(v) if isinstance(v, (int, float)) else None
            s = d.get("step")
            last_pass_step = str(s) if s is not None else None
        except (json.JSONDecodeError, ValueError, OSError):
            # EDGE-E2: malformed JSON → fields null; do NOT crash
            pass

    # REQ-S5: count `## ` headers in build_log.md
    build_log_passes = 0
    bl = loops / "build_log.md"
    if bl.exists():
        try:
            build_log_passes = sum(
                1 for line in bl.read_text().splitlines()
                if line.startswith("## ")
            )
        except OSError:
            pass

    return {
        "installed": installed,
        "last_pass_ts": last_pass_ts,
        "last_pass_step": last_pass_step,
        "build_log_passes": build_log_passes,
    }


# ─── CLI entrypoint for shell ──────────────────────────────────────
def _cli(argv: list[str]) -> int:
    import sys
    import os
    import subprocess
    if len(argv) < 3:
        print("usage: proactive_observe.py <slot> <loops_dir>", file=sys.stderr)
        return 2
    slot, loops_dir = argv[1], argv[2]
    uid = os.getuid()
    label = f"ai.anicca.{slot}-proactive"
    plist = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    rc = subprocess.run(
        ["launchctl", "print", f"gui/{uid}/{label}"],
        capture_output=True, text=True,
    ).returncode
    print(json.dumps(summarize_loops_dir(loops_dir, plist, launchctl_print_rc=rc)))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli(sys.argv))
