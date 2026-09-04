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
# Provider/profile selection is repository-global. Gig business code keeps its
# schemas and adapters here but never owns a second runner or auth boundary.
RUNNER_DIR = REPO_ROOT / "runtime/agent-runner"
BROWSER_DIR = Path(os.environ.get("GIG_BROWSER_DIR", REPO_ROOT / "skills/browser"))
STATE_DIR = Path(os.environ.get("GIG_STATE_DIR", Path.home() / "gig"))
HOST_STATE_DIR = Path(os.environ.get("GIG_HOST_STATE_DIR", LIFE_MANAGER_HOME / "state"))
LOG_DIR = Path(os.environ.get("GIG_LOG_DIR", LIFE_MANAGER_HOME / "logs"))
ENV_FILE = Path(os.environ.get("GIG_ENV_FILE", LIFE_MANAGER_HOME / ".env"))
# Platform-agnostic listing specs the owner curated from competitor evidence and real buyer
# budgets. The storefront CREATE path grounds generated proposals in this catalog instead of
# inventing content, keyed by the same capability_family names as families.json.
LISTING_CATALOG = Path(
    os.environ.get("GIG_LISTING_CATALOG", REPO_ROOT / "skills/gig-work/profile/listings/catalog.json")
)
