"""An expired session must be named, not disguised as a hydration failure.

Run: python3 -m pytest skills/earn/gig/tests/test_storefront_session.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import storefront_direct as sd  # noqa: E402


def test_the_seller_area_is_the_signal_not_the_word_login():
    # The public page always carries a login link, so wording proves nothing. Being sent out
    # of /mypage/ while reading an authenticated page is what proves the session is gone.
    assert sd._looks_signed_out("https://coconala.com/mypage/services/91000004") is False
    assert sd._looks_signed_out("https://coconala.com/login") is True
    assert sd._looks_signed_out("https://coconala.com/users/login?return_to=%2Fmypage") is True


def test_a_redirect_off_the_platform_counts_as_signed_out():
    assert sd._looks_signed_out("https://accounts.google.com/signin") is True


def test_no_observation_is_not_a_signed_out_claim():
    # Missing evidence must never be reported as an expired session.
    assert sd._looks_signed_out(None) is False
    assert sd._looks_signed_out("") is False


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
