from __future__ import annotations

import os
from pathlib import Path


GIG_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = GIG_DIR.parents[2]
MR_BOT_HOME = Path(
    os.environ.get(
        "MR_BOT_HOME",
        os.environ.get(
            "ANICCA_HOME",
            Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
            / "mr-bot",
        ),
    )
)
# Provider/profile selection is repository-global. Gig business code keeps its
# schemas and adapters here but never owns a second runner or auth boundary.
RUNNER_DIR = REPO_ROOT / "runtime/agent-runner"
BROWSER_DIR = Path(os.environ.get("GIG_BROWSER_DIR", REPO_ROOT / "skills/browser"))
STATE_DIR = Path(os.environ.get("GIG_STATE_DIR", Path.home() / "gig"))
HOST_STATE_DIR = Path(os.environ.get("GIG_HOST_STATE_DIR", MR_BOT_HOME / "state"))
LOG_DIR = Path(os.environ.get("GIG_LOG_DIR", MR_BOT_HOME / "logs"))
ENV_FILE = Path(os.environ.get("GIG_ENV_FILE", MR_BOT_HOME / ".env"))
