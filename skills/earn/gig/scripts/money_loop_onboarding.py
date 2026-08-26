#!/usr/bin/env python3
"""Create one private, read-only capability receipt for the local Gig loop."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from provider_authorization import load_receipts


GIG_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO_ROOT = GIG_ROOT.parents[2]
PUBLIC_CAPABILITIES = GIG_ROOT / "config" / "provider-capabilities.public.json"


def _text(name: str, value: Any, maximum: int = 200) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid_{name}")
    text = value.strip()
    if not text or len(text) > maximum or "\x00" in text:
        raise ValueError(f"invalid_{name}")
    return text


def _bound(name: str, value: Any, *, maximum: int | None = None) -> int:
    if isinstance(value, bool):
        raise ValueError(f"invalid_{name}")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid_{name}") from exc
    if str(value).strip() != str(number) or number < 0 or (maximum is not None and number > maximum):
        raise ValueError(f"invalid_{name}")
    return number


def _timestamp(value: Any) -> str:
    text = _text("observed_at", value, 40)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_observed_at") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("invalid_observed_at")
    return text


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _write_private(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(_canonical(value) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _skill_inventory(repo_root: Path) -> list[dict[str, str]]:
    skills_root = repo_root / "skills"
    rows = []
    for path in sorted(skills_root.glob("**/SKILL.md")):
        body = path.read_bytes()
        rows.append({
            "skill": path.parent.relative_to(skills_root).as_posix(),
            "source_sha256": hashlib.sha256(body).hexdigest(),
        })
    if not rows:
        raise ValueError("skill_inventory_empty")
    return rows


def onboard(
    *,
    owner_id: str,
    providers: list[str],
    minimum_margin_bps: Any,
    spend_cap_minor: Any,
    concurrent_job_cap: Any,
    human_minute_value_minor: Any,
    home: Path | None = None,
    repo_root: Path = DEFAULT_REPO_ROOT,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Write private local facts after one filesystem-only capability probe."""
    owner_id = _text("owner_id", owner_id)
    home = Path(home or Path.home())
    repo_root = Path(repo_root).resolve(strict=True)
    observed_at = _timestamp(observed_at or datetime.now(timezone.utc).isoformat())
    bounds = {
        "minimum_margin_bps": _bound("minimum_margin_bps", minimum_margin_bps, maximum=10_000),
        "spend_cap_minor": _bound("spend_cap_minor", spend_cap_minor),
        "concurrent_job_cap": _bound("concurrent_job_cap", concurrent_job_cap),
        "human_minute_value_minor": _bound("human_minute_value_minor", human_minute_value_minor),
    }
    public_path = repo_root / PUBLIC_CAPABILITIES.relative_to(DEFAULT_REPO_ROOT)
    public = json.loads(public_path.read_text(encoding="utf-8"))
    available = public.get("providers")
    if not isinstance(providers, list) or not providers or not isinstance(available, dict):
        raise ValueError("invalid_providers")
    selected = [_text("provider", provider, 80) for provider in providers]
    if len(set(selected)) != len(selected) or any(provider not in available for provider in selected):
        raise ValueError("invalid_providers")

    config_dir = home / ".config" / "anicca" / "gig"
    receipt_store = config_dir / "authorizations.json"
    if receipt_store.exists():
        load_receipts(receipt_store)
    config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    config_dir.chmod(0o700)
    browser_root = home / ".cloak" / "profiles"
    browser_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    browser_root.chmod(0o700)
    browser_profiles = {}
    for provider in selected:
        profile_name = f"gig-{provider}"
        profile = browser_root / profile_name
        profile.mkdir(mode=0o700, exist_ok=True)
        profile.chmod(0o700)
        browser_profiles[provider] = profile_name

    owner_profile = {
        "version": 1,
        "owner_id": owner_id,
        "selected_providers": selected,
        "bounds": bounds,
        "portfolio_assets": [],
        "observed_at": observed_at,
    }
    matrix = {
        "version": 1,
        "providers": {
            provider: {
                "default_state": "unknown",
                "actions": {action: "unknown" for action in available[provider]["actions"]},
            }
            for provider in selected
        },
    }
    inventory = {
        "version": 1,
        "probe_mode": "read_only",
        "marketplace_mutations": 0,
        "skills": _skill_inventory(repo_root),
        "browser_profiles": browser_profiles,
        "selected_providers": selected,
        "observed_at": observed_at,
    }
    files = {
        "owner-profile.json": owner_profile,
        "authorization-matrix.json": matrix,
        "capability-inventory.json": inventory,
    }
    for name, value in files.items():
        _write_private(config_dir / name, value)
    if not receipt_store.exists():
        _write_private(receipt_store, {"version": 1, "receipts": []})

    receipt = {
        "version": 1,
        "owner_profile_sha256": hashlib.sha256(_canonical(owner_profile)).hexdigest(),
        "authorization_matrix_sha256": hashlib.sha256(_canonical(matrix)).hexdigest(),
        "capability_inventory_sha256": hashlib.sha256(_canonical(inventory)).hexdigest(),
        "selected_providers": selected,
        "probe_mode": "read_only",
        "marketplace_mutations": 0,
        "observed_at": observed_at,
    }
    receipt["onboarding_sha256"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    _write_private(config_dir / "onboarding-receipt.json", receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-id", required=True)
    parser.add_argument("--providers", required=True)
    parser.add_argument("--minimum-margin-bps", required=True)
    parser.add_argument("--spend-cap-minor", required=True)
    parser.add_argument("--concurrent-job-cap", required=True)
    parser.add_argument("--human-minute-value-minor", required=True)
    args = parser.parse_args(argv)
    receipt = onboard(
        owner_id=args.owner_id,
        providers=[provider.strip() for provider in args.providers.split(",") if provider.strip()],
        minimum_margin_bps=args.minimum_margin_bps,
        spend_cap_minor=args.spend_cap_minor,
        concurrent_job_cap=args.concurrent_job_cap,
        human_minute_value_minor=args.human_minute_value_minor,
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
