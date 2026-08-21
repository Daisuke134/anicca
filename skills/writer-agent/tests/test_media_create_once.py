import importlib.util
from pathlib import Path

import pytest
from PIL import Image


MODULE = Path(__file__).parents[1] / "scripts" / "media_create_once.py"
SPEC = importlib.util.spec_from_file_location("media_create_once", MODULE)
assert SPEC and SPEC.loader
media = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(media)


def _png(path: Path, height: int) -> None:
    Image.new("RGB", (1300, height), "white").save(path, format="PNG")


def test_body_candidate_below_x_readability_floor_is_refused(tmp_path):
    candidate = tmp_path / "candidate.png"
    _png(candidate, 70)
    with pytest.raises(media.MediaCreateRefused, match="too-flat-for-x"):
        media.commit(
            candidate,
            tmp_path / "body-diagram.png",
            tmp_path / "body-receipt.json",
            "body",
        )


def test_body_candidate_at_x_readability_floor_commits(tmp_path):
    candidate = tmp_path / "candidate.png"
    _png(candidate, 110)
    receipt = media.commit(
        candidate,
        tmp_path / "body-diagram.png",
        tmp_path / "body-receipt.json",
        "body",
    )
    assert receipt["height"] == 110
