from __future__ import annotations

import importlib.util
import socket
import urllib.error
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "substack-publish" / "substack_http.py"
SPEC = importlib.util.spec_from_file_location("substack_http_test_module", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_asset_host_is_allowlisted_but_unrelated_host_is_not() -> None:
    assert MODULE._host(
        "https://substack-post-media.s3.amazonaws.com/public/images/a.png"
    ) == "substack-post-media.s3.amazonaws.com"
    assert MODULE._host("https://substackcdn.com/image/fetch/a.png") == "substackcdn.com"
    try:
        MODULE._host("https://example.com/a.png")
    except OSError as error:
        assert "non-Substack" in str(error)
    else:
        raise AssertionError("unrelated asset host was accepted")


def test_bytes_request_retries_dns_failure_with_resolver_transport(
    monkeypatch,
) -> None:
    def fail_open(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise urllib.error.URLError(socket.gaierror("nodename nor servname provided"))

    calls: list[tuple[str, bool]] = []

    def fallback(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append((args[1], kwargs["content_type"]))
        return b"\x89PNG\r\n", "image/png"

    monkeypatch.setattr(MODULE, "_open", fail_open)
    monkeypatch.setattr(MODULE, "_curl", fallback)
    data, content_type = MODULE.bytes_request(
        "https://substack-post-media.s3.amazonaws.com/public/images/a.png"
    )
    assert data.startswith(b"\x89PNG")
    assert content_type == "image/png"
    assert calls == [
        ("https://substack-post-media.s3.amazonaws.com/public/images/a.png", True)
    ]


def test_publication_readback_routes_substack_cdn_through_transport(
    monkeypatch,
) -> None:
    remote_path = Path(__file__).parents[1] / "scripts" / "publication_remote.py"
    remote_spec = importlib.util.spec_from_file_location("publication_remote_test_module", remote_path)
    remote = importlib.util.module_from_spec(remote_spec)
    assert remote_spec.loader is not None
    remote_spec.loader.exec_module(remote)
    monkeypatch.setattr(
        remote,
        "substack_bytes_request",
        lambda *args, **kwargs: (b"asset", "image/png"),
    )
    assert remote.get_bytes("https://substackcdn.com/image/fetch/a.png") == b"asset"


def test_publication_receipt_reread_routes_substack_cdn_through_transport(
    monkeypatch,
) -> None:
    resume_path = Path(__file__).parents[1] / "scripts" / "publication_resume.py"
    resume_spec = importlib.util.spec_from_file_location(
        "publication_resume_test_module", resume_path
    )
    resume = importlib.util.module_from_spec(resume_spec)
    assert resume_spec.loader is not None
    resume_spec.loader.exec_module(resume)
    monkeypatch.setattr(
        resume,
        "substack_bytes_request",
        lambda *args, **kwargs: (b"asset", "image/png"),
    )
    assert resume.fetch_remote_asset(
        "https://substackcdn.com/image/fetch/a.png", {}
    ) == b"asset"
