#!/usr/bin/env python3
"""passprep.py — deterministic pass-prep helper for the gig earn-core.
Called at the START of every cron pass. Reads/repairs strategy.json,
enforces skip-floor, increments pass_count, and prints ONE JSON line
to stdout. No external dependencies (stdlib only).

Exit 0 always: on any unexpected error, falls back to safe defaults
and still prints valid JSON (with an _error field on stderr).
"""
import json
import os
import sys
import shutil
import tempfile

HOME = os.path.expanduser("~")
GIG_DIR = os.path.join(HOME, "gig")
STRATEGY_FILE = os.path.join(GIG_DIR, "strategy.json")
# strategy.default.json lives next to this script in the skill directory
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STRATEGY = os.path.join(SKILL_DIR, "strategy.default.json")

FALLBACK = {
    "version": 1,
    "max_apply_per_pass": 5,
    "improve_cadence_passes": 4,
    "priority_categories": [
        "PPT/スライド",
        "資料作成",
        "記事/blog",
        "データ入力/Excel",
        "文字起こし",
        "コード",
        "LP/ランディングページ",
    ],
    "skip_categories": [],
    "price_defaults": {
        "PPT/スライド": 8000,
        "資料作成": 10000,
        "記事/blog": 5000,
        "データ入力/Excel": 4000,
        "文字起こし": 4000,
        "コード": 15000,
        "LP/ランディングページ": 20000,
    },
    "proposal_templates": {},
    "profile_blurb": "AIエージェントによる高品質・迅速な作業対応。PPT・資料・記事・データ入力・コード対応。",
    "pass_count": 0,
    "notes": "Fallback defaults — strategy.default.json was not found.",
}


def atomic_write(path, data):
    """Write JSON atomically via temp file + os.replace."""
    dir_ = os.path.dirname(path)
    os.makedirs(dir_, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_strategy():
    """Load strategy.json; on missing/corrupt, restore from default (or fallback) and load that."""
    os.makedirs(GIG_DIR, exist_ok=True)

    # Try to load existing strategy.json
    if os.path.exists(STRATEGY_FILE):
        try:
            with open(STRATEGY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data, False  # (strategy, was_repaired)
        except (json.JSONDecodeError, OSError, ValueError):
            # Corrupt — fall through to repair
            pass

    # Restore from strategy.default.json if available
    if os.path.exists(DEFAULT_STRATEGY):
        try:
            shutil.copy2(DEFAULT_STRATEGY, STRATEGY_FILE)
            with open(STRATEGY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data, True
        except Exception:
            pass

    # Last resort: hardcoded fallback (strategy.default.json missing in this HOME)
    strategy = dict(FALLBACK)
    atomic_write(STRATEGY_FILE, strategy)
    return strategy, True


def main():
    try:
        strategy, was_repaired = load_strategy()

        # Enforce skip-floor (FIND-005):
        # If every priority_category is in skip_categories, reset skip_categories to []
        # so there are still categories available to apply to.
        priority = list(strategy.get("priority_categories") or [])
        skip = list(strategy.get("skip_categories") or [])
        if priority and all(c in skip for c in priority):
            strategy["skip_categories"] = []
            skip = []

        # Increment pass_count deterministically (FIND-001)
        pass_count = int(strategy.get("pass_count") or 0) + 1
        strategy["pass_count"] = pass_count

        # Write back atomically
        atomic_write(STRATEGY_FILE, strategy)

        # Compute do_improve: true when pass_count is a multiple of improve_cadence_passes
        cadence = max(1, int(strategy.get("improve_cadence_passes") or 4))
        do_improve = (pass_count % cadence == 0)

        result = {
            "pass_count": pass_count,
            "do_improve": do_improve,
            "max_apply_per_pass": int(strategy.get("max_apply_per_pass") or 5),
            "priority_categories": list(strategy.get("priority_categories") or []),
            "skip_categories": list(strategy.get("skip_categories") or []),
        }
        if was_repaired:
            result["_repaired"] = True
        print(json.dumps(result, ensure_ascii=False))

    except Exception as exc:
        # Crash-safe fallback: emit valid JSON with safe defaults; do_improve=false
        fallback_result = {
            "pass_count": 0,
            "do_improve": False,
            "max_apply_per_pass": 5,
            "priority_categories": FALLBACK["priority_categories"],
            "skip_categories": [],
            "_error": str(exc),
        }
        print(f"passprep.py ERROR: {exc}", file=sys.stderr)
        print(json.dumps(fallback_result, ensure_ascii=False))


if __name__ == "__main__":
    main()
