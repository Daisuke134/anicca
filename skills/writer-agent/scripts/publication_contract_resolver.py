"""Resolve one persisted publication contract at its canonical run boundary."""

from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path
from typing import Any, Mapping

from publication_contract import DORMANT_PAIRS


ACTIVE_CONTRACT = "active-four"
ACTIVE_ALIAS = "active-six"
LEGACY_CONTRACT = "legacy-exact8"


class PublicationContractError(ValueError):
    """The persisted publication contract cannot be trusted."""


def infer_publication_contract(state: Mapping[str, Any]) -> str:
    """Resolve an explicit contract or a validated pre-migration state.

    Historical states predate ``publication_contract`` but retain both dormant
    pair entries as real work. Explicit active-six is a compatibility alias for
    the current active-four contract; legacy exact-eight remains separate.
    """
    marker = state.get("publication_contract")
    if marker == ACTIVE_ALIAS:
        return ACTIVE_CONTRACT
    if marker in {ACTIVE_CONTRACT, LEGACY_CONTRACT}:
        return str(marker)
    if "publication_contract" in state:
        raise PublicationContractError("publication state contract is unsupported")

    pairs = state.get("pairs")
    if not isinstance(pairs, Mapping):
        raise PublicationContractError(
            "publication state contract is missing and historical pairs are unavailable"
        )
    dormant = [pairs.get(pair) for pair in DORMANT_PAIRS]
    if all(
        isinstance(entry, Mapping)
        and entry.get("status") != "skipped"
        for entry in dormant
    ):
        return LEGACY_CONTRACT
    if all(
        isinstance(entry, Mapping)
        and entry.get("status") == "skipped"
        for entry in dormant
    ):
        return ACTIVE_CONTRACT
    raise PublicationContractError(
        "publication state contract is missing and historical pair set is ambiguous"
    )


def canonical_state_path(ledger_path: Path, run_id: str) -> Path:
    """Return the only state path allowed to govern one ledger/run pair."""
    if not run_id or Path(run_id).name != run_id or ".." in Path(run_id).parts:
        raise PublicationContractError("completion run ID is not a canonical path component")
    ledger = Path(ledger_path).resolve(strict=False)
    return ledger.parent / "runs" / run_id / "gates" / "publication-state.json"


def resolve_publication_contract(
    state_path: Path,
    ledger_path: Path,
    run_id: str,
    *,
    state: Mapping[str, Any] | None = None,
) -> str:
    """Validate the canonical state boundary and return its persisted contract."""
    expected = canonical_state_path(ledger_path, run_id).resolve(strict=False)
    actual_path = Path(state_path)
    if actual_path.is_symlink() or actual_path.resolve(strict=False) != expected:
        raise PublicationContractError(
            "publication state must be the canonical run gates/publication-state.json"
        )
    if not actual_path.is_file():
        raise PublicationContractError("publication state must be a regular file")

    if state is None:
        try:
            state = json.loads(actual_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise PublicationContractError("publication state is unreadable") from error
    if not isinstance(state, Mapping) or state.get("version") != 1:
        raise PublicationContractError("publication state is malformed")
    if state.get("run_id") != run_id:
        raise PublicationContractError("publication state run ID conflicts with completion run")

    stored_state_path = state.get("state_path")
    if stored_state_path is not None and Path(str(stored_state_path)).resolve(strict=False) != expected:
        raise PublicationContractError("persisted state path conflicts with canonical run boundary")
    stored_ledger_path = state.get("ledger_path")
    if (
        stored_ledger_path is not None
        and Path(str(stored_ledger_path)).resolve(strict=False)
        != Path(ledger_path).resolve(strict=False)
    ):
        raise PublicationContractError("persisted ledger path conflicts with completion ledger")
    return infer_publication_contract(state)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        print(resolve_publication_contract(args.state, args.ledger, args.run_id))
    except PublicationContractError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
