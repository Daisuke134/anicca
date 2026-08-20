import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts" / "publication_resume.py"
SPEC = importlib.util.spec_from_file_location("publication_resume", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_substack_identities_are_resolved_separately() -> None:
    identities = MODULE.configured_destination_identities(
        {
            "SUBSTACK_PUBLICATION_JA": "aniccabuddha.substack.com",
            "SUBSTACK_PUBLICATION_EN": "anicca-global.substack.com",
        }
    )

    assert identities["substack/ja"] == "aniccabuddha.substack.com"
    assert identities["substack/en"] == "anicca-global.substack.com"
    MODULE.validate_destination_identities(identities)


def test_substack_identity_conflation_fails_closed() -> None:
    with pytest.raises(MODULE.InvariantError, match="distinct"):
        MODULE.configured_destination_identities(
            {
                "SUBSTACK_PUBLICATION_JA": "aniccabuddha.substack.com",
                "SUBSTACK_PUBLICATION_EN": "aniccabuddha.substack.com",
            }
        )

    with pytest.raises(MODULE.InvariantError, match="required"):
        MODULE.configured_destination_identities(
            {"SUBSTACK_PUBLICATION_JA": "aniccabuddha.substack.com"}
        )
