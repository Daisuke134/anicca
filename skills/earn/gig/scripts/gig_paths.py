from __future__ import annotations

import os
from pathlib import Path


GIG_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = GIG_DIR.parents[2]
LIFE_MANAGER_HOME = Path(
    os.environ.get(
        "LIFE_MANAGER_HOME",
        os.environ.get(
            "ANICCA_HOME",
            Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
            / "life-manager",
        ),
    )
)
RUNNER_DIR = Path(os.environ.get("GIG_RUNNER_DIR", REPO_ROOT / "runtime/agent-runner"))
BROWSER_DIR = Path(os.environ.get("GIG_BROWSER_DIR", REPO_ROOT / "skills/browser"))
STATE_DIR = Path(os.environ.get("GIG_STATE_DIR", Path.home() / "gig"))
HOST_STATE_DIR = Path(os.environ.get("GIG_HOST_STATE_DIR", LIFE_MANAGER_HOME / "state"))
LOG_DIR = Path(os.environ.get("GIG_LOG_DIR", LIFE_MANAGER_HOME / "logs"))
ENV_FILE = Path(os.environ.get("GIG_ENV_FILE", LIFE_MANAGER_HOME / ".env"))
