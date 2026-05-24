"""
_lib.py — shared helpers for the donation skill.

Loads env from ~/.openclaw/.env (and ~/anicca-monk-factory/.env if present),
reads wizard config from ~/.openclaw/openclaw.json, exposes period helpers
and recipients-file loader.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Tuple

HOME = Path(os.path.expanduser("~"))
SKILL_DIR = HOME / ".openclaw" / "skills" / "donation"
WORKSPACE = HOME / ".openclaw" / "workspace" / "donation"
RECEIPTS_DIR = WORKSPACE / "receipts"
ROLLUP_DIR = WORKSPACE / "1099"
OPENCLAW_JSON = HOME / ".openclaw" / "openclaw.json"
ENV_FILES = [HOME / ".openclaw" / ".env", HOME / "anicca-monk-factory" / ".env"]


def load_env_files():
    """Best-effort dotenv-style loading. Doesn't overwrite existing env."""
    for envp in ENV_FILES:
        if not envp.exists():
            continue
        try:
            for raw in envp.read_text().splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
        except Exception:
            pass


def load_wizard_config() -> dict:
    cfg = {
        "percent": 1,
        "recipients_path": str(SKILL_DIR / "recipients.json"),
        "receipt_host": "https://aniccaai.com/donation",
        "tweet_account": "@aniccaxxx",
        "tax_entity": "Anicca, LLC",
        "anonymize_amount": False,
        "tweet_via_buildinpublic": True,
    }
    try:
        data = json.loads(OPENCLAW_JSON.read_text())
        s = (((data.get("skills") or {}).get("donation")) or {})
        for k in cfg.keys():
            if k in s:
                cfg[k] = s[k]
    except Exception:
        pass
    cfg["recipients_path"] = os.path.expanduser(cfg["recipients_path"])
    return cfg


def is_dry_run() -> bool:
    v = os.environ.get("DONATION_DRY_RUN", "true").strip().lower()
    return v not in ("false", "0", "no", "off")


def prior_month_period() -> Tuple[str, dt.datetime, dt.datetime]:
    """Return (label 'YYYY-MM', UTC start, UTC end-exclusive) for the prior
    calendar month relative to today."""
    today = dt.date.today()
    first_of_this_month = today.replace(day=1)
    last_of_prior = first_of_this_month - dt.timedelta(days=1)
    period_start = last_of_prior.replace(day=1)
    label = period_start.strftime("%Y-%m")
    start_dt = dt.datetime(period_start.year, period_start.month, 1, tzinfo=dt.timezone.utc)
    end_dt = dt.datetime(first_of_this_month.year, first_of_this_month.month, 1, tzinfo=dt.timezone.utc)
    return label, start_dt, end_dt


def load_recipients(path: str) -> list:
    p = Path(os.path.expanduser(path))
    if not p.exists():
        return []
    blob = json.loads(p.read_text())
    if isinstance(blob, dict):
        return list(blob.get("recipients") or [])
    return list(blob or [])


def write_run_state(period_label: str, payload: dict) -> Path:
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    out = WORKSPACE / f"run-{period_label}.json"
    existing = {}
    if out.exists():
        try:
            existing = json.loads(out.read_text())
        except Exception:
            existing = {}
    existing.update(payload)
    out.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    return out


def read_run_state(period_label: str) -> dict:
    p = WORKSPACE / f"run-{period_label}.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def is_period_skipped(period_label: str) -> bool:
    return (WORKSPACE / f"skipped-{period_label}.json").exists()
