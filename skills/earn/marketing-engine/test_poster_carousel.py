import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).parent


def load_poster(monkeypatch):
    cdp = types.ModuleType("cdp")
    cdp.page_ws = lambda _tid: "ws://unused"
    monkeypatch.setitem(sys.modules, "cdp", cdp)

    websocket = types.ModuleType("websocket")
    websocket.create_connection = lambda *_args, **_kwargs: None
    monkeypatch.setitem(sys.modules, "websocket", websocket)

    exceptions = types.ModuleType("instagrapi.exceptions")
    exceptions.ChallengeRequired = type("ChallengeRequired", (Exception,), {})
    exceptions.LoginRequired = type("LoginRequired", (Exception,), {})
    instagrapi = types.ModuleType("instagrapi")
    instagrapi.exceptions = exceptions
    monkeypatch.setitem(sys.modules, "instagrapi", instagrapi)
    monkeypatch.setitem(sys.modules, "instagrapi.exceptions", exceptions)

    spec = importlib.util.spec_from_file_location("poster_under_test", ROOT / "poster.py")
    poster = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(poster)
    return poster, instagrapi


def write_account_state(tmp_path, *, started_warming="2026-07-17"):
    path = tmp_path / "accounts.json"
    path.write_text(json.dumps([{"handle": "carousel", "started_warming": started_warming}]))
    return path


def run_main(monkeypatch, poster, argv):
    monkeypatch.setattr(sys, "argv", ["poster.py", *argv])
    poster.main()


def test_live_images_calls_album_upload_and_returns_post_url(monkeypatch, tmp_path, capsys):
    poster, instagrapi = load_poster(monkeypatch)
    caption = tmp_path / "caption.txt"
    caption.write_text("carousel caption")
    images = [tmp_path / "1.jpg", tmp_path / "2.jpg"]
    for image in images:
        image.write_bytes(b"fake-image")
    accounts = write_account_state(tmp_path)

    class Media:
        def model_dump(self):
            return {"code": "ALBUM123"}

    class Client:
        def __init__(self):
            self.delay_range = None
            self.album_calls = []

        def album_upload(self, paths, caption_text):
            self.album_calls.append((paths, caption_text))
            return Media()

    client = Client()
    instagrapi.Client = lambda: client
    monkeypatch.setattr(poster, "login_resilient", lambda *_args, **_kwargs: True)

    run_main(monkeypatch, poster, [
        "--images", ",".join(map(str, images)),
        "--caption-file", str(caption),
        "--handle", "carousel",
        "--accounts-path", str(accounts),
        "--live",
    ])

    result = json.loads(capsys.readouterr().out)
    assert client.delay_range == [1, 3]
    assert client.album_calls == [([str(path) for path in images], "carousel caption")]
    assert result["outcome"] == "published"
    assert result["post_url"] == "https://www.instagram.com/p/ALBUM123/"


@pytest.mark.parametrize("media_args", [[], ["--video", "v.mp4", "--images", "1.jpg,2.jpg"]])
def test_video_and_images_are_exactly_one_required(monkeypatch, tmp_path, media_args):
    poster, _ = load_poster(monkeypatch)
    caption = tmp_path / "caption.txt"
    caption.write_text("caption")
    with pytest.raises(SystemExit) as error:
        run_main(monkeypatch, poster, [
            *media_args,
            "--caption-file", str(caption),
            "--handle", "carousel",
        ])
    assert error.value.code == 2


def test_day_under_three_refuses_album_before_client_creation(monkeypatch, tmp_path, capsys):
    poster, instagrapi = load_poster(monkeypatch)
    caption = tmp_path / "caption.txt"
    caption.write_text("caption")
    images = [tmp_path / "1.jpg", tmp_path / "2.jpg"]
    accounts = write_account_state(tmp_path, started_warming="2026-07-19")

    class Client:
        def __init__(self):
            self.delay_range = None
            self.album_called = False

        def album_upload(self, *_args):
            self.album_called = True
            raise AssertionError("album_upload must not run before the day<3 refusal")

    client = Client()
    instagrapi.Client = lambda: client

    class FixedDate(poster.datetime.date):
        @classmethod
        def today(cls):
            return cls(2026, 7, 19)

    monkeypatch.setattr(poster.datetime, "date", FixedDate)

    run_main(monkeypatch, poster, [
        "--images", ",".join(map(str, images)),
        "--caption-file", str(caption),
        "--handle", "carousel",
        "--accounts-path", str(accounts),
        "--live",
    ])

    result = json.loads(capsys.readouterr().out)
    assert result["outcome"] == "failed"
    assert result["refused"] == "warming_day<3"
    assert "warming_day=1 < 3" in result["error"]
    assert client.album_called is False
