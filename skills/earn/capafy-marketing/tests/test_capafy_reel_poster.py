import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from capafy_reel_poster import (  # noqa: E402
    BrowserChallenge,
    CAPTION_EDITOR_SELECTOR,
    COMPOSER_LABELS,
    PostRequest,
    post_reel,
    resolve_active_handle,
    resolve_share_progress,
)


def test_composer_labels_cover_current_japanese_instagram_ui():
    assert "新しい投稿" in COMPOSER_LABELS


def test_caption_selector_covers_current_lexical_contenteditable_ui():
    assert "contenteditable='true'" in CAPTION_EDITOR_SELECTOR
    assert "role='textbox'" in CAPTION_EDITOR_SELECTOR


def test_share_progress_waits_while_instagram_is_still_uploading():
    assert resolve_share_progress(True, "シェア中") == "processing"


@pytest.mark.parametrize("text", ["リール動画がシェアされました", "Your reel has been shared"])
def test_share_progress_accepts_explicit_completion(text):
    assert resolve_share_progress(True, text) == "complete"


def test_share_progress_accepts_modal_close_after_share_started():
    assert resolve_share_progress(False, "") == "complete"


class FakeCdp:
    def __init__(self):
        self.handle = "capafy.skills25042"
        self.post_handle = None
        self.handle_reads = 0
        self.pre_urls = set()
        self.post_urls = set()
        self.actions = []
        self.destructive_actions = []
        self.challenge = False
        self.screenshots = ["before.png", "share.png"]

    def active_handle(self):
        if self.challenge:
            raise BrowserChallenge("challenge page")
        self.handle_reads += 1
        return self.post_handle if self.handle_reads > 1 and self.post_handle else self.handle

    def reel_urls(self):
        return self.post_urls if "share" in self.actions else self.pre_urls

    def open_composer(self): self.actions.append("open_composer")
    def upload_video(self, _path): self.actions.append("upload_video")
    def advance_to_caption(self): self.actions.append("advance_to_caption")
    def enter_caption(self, _caption): self.actions.append("enter_caption")
    def share(self): self.actions.append("share"); self.destructive_actions.append("share")
    def discard(self): self.actions.append("discard")


@pytest.fixture
def media(tmp_path):
    path = tmp_path / "reel.mp4"
    path.write_bytes(b"\x00\x00\x00\x18ftypmp42fixture")
    return path


def request(media, live=False, capability="publish_probe", handle="capafy.skills25042"):
    return PostRequest(media, "Exact caption", handle, 9555, "tab-1", capability, live)


def test_active_handle_falls_back_to_exact_profile_link_when_username_input_is_absent():
    assert resolve_active_handle(
        None,
        ["/explore/", "/capafy.skills25042/"],
        "capafy.skills25042",
    ) == "capafy.skills25042"


def test_active_handle_refuses_foreign_profile_link_fallback():
    with pytest.raises(RuntimeError, match="ownership evidence"):
        resolve_active_handle(None, ["/capafy.someone-else/"], "capafy.skills25042")


def test_dry_reaches_share_then_discards_without_clicking_share(media):
    browser = FakeCdp()
    result = post_reel(request(media, live=False), browser)
    assert result["status"] == "dry_verified"
    assert result["reached"] == "share"
    assert result["published"] is False
    assert "share" not in browser.destructive_actions
    assert browser.actions[-1] == "discard"


def test_live_requires_publish_probe_new_reel_and_post_write_owner_session(media):
    browser = FakeCdp()
    browser.pre_urls = {"https://www.instagram.com/reel/OLD123/"}
    browser.post_urls = browser.pre_urls | {"https://www.instagram.com/reel/NEW456/"}
    result = post_reel(request(media, live=True), browser)
    assert result["published"] is True
    assert result["reel_url"] == "https://www.instagram.com/reel/NEW456/"
    assert result["owner_session_verified"] is True
    assert browser.handle_reads == 2


def test_profile_scoped_reel_url_is_normalized_and_verified(media):
    browser = FakeCdp()
    browser.post_urls = {
        "https://www.instagram.com/capafy.skills25042/reel/NEW456/"
    }
    result = post_reel(request(media, live=True), browser)
    assert result["status"] == "published_verified"
    assert result["reel_url"] == "https://www.instagram.com/reel/NEW456/"


def test_post_write_owner_mismatch_refuses_publish_claim(media):
    browser = FakeCdp()
    browser.post_urls = {"https://www.instagram.com/reel/NEW456/"}
    browser.post_handle = "capafy.someone-else"
    result = post_reel(request(media, live=True), browser)
    assert result["status"] == "post_write_session_mismatch"
    assert result["published"] is False
    assert result["owner_session_verified"] is False


def test_share_click_without_new_url_is_unconfirmed_failure(media):
    browser = FakeCdp()
    browser.pre_urls = {"https://www.instagram.com/reel/OLD123/"}
    browser.post_urls = set(browser.pre_urls)
    assert post_reel(request(media, live=True), browser)["status"] == "share_unconfirmed"


def test_multiple_new_urls_are_ambiguous(media):
    browser = FakeCdp()
    browser.post_urls = {
        "https://www.instagram.com/reel/NEW1/",
        "https://www.instagram.com/reel/NEW2/",
    }
    result = post_reel(request(media, live=True), browser)
    assert result["status"] == "share_ambiguous"
    assert result["published"] is False


def test_post_urls_are_not_accepted_as_reels(media):
    browser = FakeCdp()
    browser.post_urls = {"https://www.instagram.com/p/NOTAREEL/"}
    assert post_reel(request(media, live=True), browser)["status"] == "share_unconfirmed"


@pytest.mark.parametrize("capability", ["none", "warmup_only", "noncommercial_post", "commercial_post"])
def test_live_refuses_capability_mismatch(media, capability):
    browser = FakeCdp()
    result = post_reel(request(media, live=True, capability=capability), browser)
    assert result["status"] == "capability_refused"
    assert browser.actions == []


def test_wrong_active_handle_is_refused(media):
    browser = FakeCdp(); browser.handle = "capafy.someone-else"
    result = post_reel(request(media), browser)
    assert result["status"] == "session_handle_mismatch"
    assert browser.actions == []


def test_challenge_page_is_typed_failure(media):
    browser = FakeCdp(); browser.challenge = True
    result = post_reel(request(media), browser)
    assert result["status"] == "challenge"


@pytest.mark.parametrize("kind", ["missing", "wrong_suffix", "invalid_header"])
def test_missing_or_invalid_mp4_is_refused(tmp_path, kind):
    path = tmp_path / ("video.mov" if kind == "wrong_suffix" else "video.mp4")
    if kind != "missing": path.write_bytes(b"not an mp4")
    result = post_reel(request(path), FakeCdp())
    assert result["status"] == "invalid_media"
