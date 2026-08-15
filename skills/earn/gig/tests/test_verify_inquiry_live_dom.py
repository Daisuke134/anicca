import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_inquiry_live_dom.py"
SPEC = importlib.util.spec_from_file_location("verify_inquiry_live_dom", SCRIPT)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def test_reply_fingerprint_requires_new_seller_message():
    before = [{"side": "buyer", "text": "質問", "attachments": []}]
    after = before + [{"side": "seller", "text": "回答", "attachments": []}]
    assert verifier.fingerprint(before) != verifier.fingerprint(after)
    assert verifier.last_side(after) == "seller"
    assert verifier.last_side(before) == "buyer"
    assert verifier.seller_count(before) == 0
    assert verifier.seller_count(after) == 1
