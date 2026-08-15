"""A gig LaunchAgent may never execute out of a git worktree.

WHY THIS EXISTS (2026-08-08, E6a -- spec 37 §2.2/§2.3, spec 34 §3.1):

  ``ai.anicca.hf-gig-pass`` was installed pointing at
  ``$LIFE_MANAGER_REPO/.worktrees/gig-p0-promissory-stop/skills/earn/gig`` while the
  other seven ``hf-gig-*`` jobs ran from ``$LIFE_MANAGER_REPO``. The two checkouts
  had drifted 199/271 commits apart, and both wrote
  ``~/gig/projects/<id>/requirements/live-buyer-reply.json``. Measured on real data
  the same day: for the two live orders with revision traffic the two copies of
  ``coconala_queue_snapshot.py`` computed DIFFERENT ``feedback_sha256`` for identical
  input, so each rewrote the other's sidecar every few minutes and stripped A6's
  accumulated-requirements fields on the way through. That held a finished delivery
  for nine hours (A14).

  The rule, from spec 37 §2.2: a worktree is a short-lived place for a human or an
  agent to work. Production runs from ONE checkout. If production has two, that is
  two productions.

WHY IT IS NOT ENOUGH TO TRUST plist-selfheal.sh:

  ``plist-selfheal.sh`` restores an installed plist from the repo copy only when the
  installed file FAILS ``plutil -lint``. The pass plist was valid -- someone had
  hand-edited a well-formed path into it -- so the reconcile loop saw nothing wrong
  and the drift survived indefinitely. The repo copies were correct the whole time.
  Validity is not correctness, so this test checks the installed files too.

WHY IT DOES NOT JUST GREP ProgramArguments:

  ``gig_gates.sh`` reads ProgramArguments only. A worktree path can also arrive via
  WorkingDirectory or an EnvironmentVariables entry, so this walks every string in
  the parsed plist.
"""

from __future__ import annotations

import os
import plistlib
from pathlib import Path

import pytest

# The single production checkout. Same default plist-selfheal.sh uses for its repo
# dir, which is what makes that script's notion of "canonical" and this test's agree.
PRODUCTION_CHECKOUT = Path(
    os.environ.get("GIG_PRODUCTION_CHECKOUT", str(Path.home() / "life-manager"))
)
REPO_LAUNCHD_DIR = Path(
    os.environ.get("GIG_LAUNCHD_REPO_DIR", str(PRODUCTION_CHECKOUT / "skills/earn/gig/launchd"))
)
INSTALLED_DIR = Path(
    os.environ.get("GIG_LAUNCH_AGENTS_DIR", str(Path.home() / "Library/LaunchAgents"))
)

WORKTREE_MARKER = "/.worktrees/"


def _strings(value: object) -> list[str]:
    """Every string anywhere in a parsed plist, whatever nests it."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in _strings(item)]
    if isinstance(value, (list, tuple)):
        return [s for item in value for s in _strings(item)]
    return []


def _worktree_paths(plist_path: Path) -> list[str]:
    with plist_path.open("rb") as handle:
        parsed = plistlib.load(handle)
    return [s for s in _strings(parsed) if WORKTREE_MARKER in s]


def _gig_plists(directory: Path) -> list[Path]:
    return sorted(directory.glob("ai.anicca.hf-gig-*.plist"))


def test_repo_launchagents_never_reference_a_worktree() -> None:
    """The versioned copies are what plist-selfheal.sh restores from."""
    plists = _gig_plists(REPO_LAUNCHD_DIR)
    assert plists, f"no gig plists found under {REPO_LAUNCHD_DIR}"
    offenders = {
        plist.name: found for plist in plists if (found := _worktree_paths(plist))
    }
    assert not offenders, (
        "gig LaunchAgents in the repo point into a git worktree; production runs from "
        f"one checkout ({PRODUCTION_CHECKOUT}), never a worktree: {offenders}"
    )


def test_installed_launchagents_never_reference_a_worktree() -> None:
    """The files launchd actually loads -- where the 2026-08-08 drift lived."""
    if not INSTALLED_DIR.is_dir():
        pytest.skip(f"no LaunchAgents directory at {INSTALLED_DIR}")
    plists = _gig_plists(INSTALLED_DIR)
    if not plists:
        pytest.skip(f"no gig LaunchAgents installed under {INSTALLED_DIR}")
    offenders = {
        plist.name: found for plist in plists if (found := _worktree_paths(plist))
    }
    assert not offenders, (
        "installed gig LaunchAgents point into a git worktree. Two checkouts in "
        "production is two productions, and on 2026-08-08 it cost a paying customer "
        f"nine hours. Restore from {REPO_LAUNCHD_DIR} and re-bootstrap: {offenders}"
    )


def test_installed_gig_work_paths_are_the_production_checkout() -> None:
    """Not-a-worktree is necessary but not sufficient: it must be THE checkout.

    A plist pointing at a second full clone would pass the two tests above and
    reproduce the same split brain.
    """
    if not INSTALLED_DIR.is_dir():
        pytest.skip(f"no LaunchAgents directory at {INSTALLED_DIR}")
    plists = _gig_plists(INSTALLED_DIR)
    if not plists:
        pytest.skip(f"no gig LaunchAgents installed under {INSTALLED_DIR}")
    expected = str(PRODUCTION_CHECKOUT / "skills/earn/gig")
    offenders: dict[str, list[str]] = {}
    for plist in plists:
        with plist.open("rb") as handle:
            parsed = plistlib.load(handle)
        wrong = [
            s
            for s in _strings(parsed)
            if "/skills/earn/gig" in s and not s.startswith(expected)
        ]
        if wrong:
            offenders[plist.name] = wrong
    assert not offenders, (
        f"installed gig LaunchAgents run skills/earn/gig from outside {expected}: {offenders}"
    )


def test_the_guard_actually_fires_on_a_worktree_plist(tmp_path: Path) -> None:
    """Prove the assertion is reachable, so a green run means something.

    Builds the exact shape of the plist this incident installed and checks the
    detector finds it -- in ProgramArguments, and again when the worktree path
    only appears in WorkingDirectory.
    """
    worktree_program = tmp_path / "ai.anicca.hf-gig-pass.plist"
    worktree_program.write_bytes(
        plistlib.dumps(
            {
                "Label": "ai.anicca.hf-gig-pass",
                "ProgramArguments": [
                    "/bin/bash",
                    str(
                        PRODUCTION_CHECKOUT
                        / ".worktrees/gig-p0-promissory-stop/skills/earn/gig/gig_pass.sh"
                    ),
                ],
            }
        )
    )
    assert _worktree_paths(worktree_program), "detector missed a worktree ProgramArguments path"

    worktree_cwd = tmp_path / "ai.anicca.hf-gig-other.plist"
    worktree_cwd.write_bytes(
        plistlib.dumps(
            {
                "Label": "ai.anicca.hf-gig-other",
                "ProgramArguments": ["/bin/bash", "/usr/local/bin/ok.sh"],
                "WorkingDirectory": str(PRODUCTION_CHECKOUT / ".worktrees/somewhere"),
                "EnvironmentVariables": {"PATH": "/usr/bin"},
            }
        )
    )
    assert _worktree_paths(worktree_cwd), (
        "detector only looks at ProgramArguments; a worktree in WorkingDirectory "
        "would reproduce the incident undetected"
    )

    clean = tmp_path / "ai.anicca.hf-gig-clean.plist"
    clean.write_bytes(
        plistlib.dumps(
            {
                "Label": "ai.anicca.hf-gig-clean",
                "ProgramArguments": [
                    "/bin/bash",
                    str(PRODUCTION_CHECKOUT / "skills/earn/gig/gig_pass.sh"),
                ],
            }
        )
    )
    assert not _worktree_paths(clean), "detector false-positives on the correct checkout"
