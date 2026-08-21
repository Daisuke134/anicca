import importlib.util
import sys
from pathlib import Path

from PIL import Image


MODULE = Path(__file__).parents[1] / "scripts" / "x-publish" / "x_inplace_repair.py"
sys.path.insert(0, str(MODULE.parent))
SPEC = importlib.util.spec_from_file_location("x_inplace_repair", MODULE)
assert SPEC and SPEC.loader
x_repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(x_repair)


def _png(path: Path, height: int) -> None:
    Image.new("RGB", (1300, height), "white").save(path, format="PNG")


def test_source_media_readability_rejects_flat_and_tall_images(tmp_path):
    flat = tmp_path / "flat.png"
    tall = tmp_path / "tall.png"
    _png(flat, 70)
    _png(tall, 651)
    receipt = x_repair._body_media_readability([flat, tall])
    assert receipt["status"] == "FAIL"
    assert any("too-flat" in item for item in receipt["violations"])
    assert any("too-tall" in item for item in receipt["violations"])


def test_source_media_readability_accepts_x_range(tmp_path):
    body = tmp_path / "body.png"
    _png(body, 110)
    receipt = x_repair._body_media_readability([body])
    assert receipt["status"] == "PASS"
    assert receipt["images"][0]["height"] == 110


def test_publish_path_persists_receipt_and_quarantines_readability_failure():
    source = MODULE.read_text(encoding="utf-8")
    assert '"media-readability.json"' in source
    assert '_guard("mark-unavailable", pair, reason=reason)' in source
    assert '"action": "quarantined-unreadable-media"' in source
