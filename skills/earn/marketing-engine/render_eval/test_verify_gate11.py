import json
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from verify_gate11 import verify_gate11


def test_gate11_verifier_requires_ten_outputs(tmp_path):
    with pytest.raises(ValueError, match="missing successful safety receipt"):
        verify_gate11(engine=HERE.parent, evidence_root=tmp_path)


def test_gate11_source_has_no_publisher_or_openclaw_dependency():
    source = (HERE / "renderer_eval.py").read_text(encoding="utf-8")
    assert ".openclaw" not in source
    assert "postiz" not in source.lower()
    assert "publish" not in source.lower().replace("publication_effects", "")
