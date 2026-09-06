"""A partitioned cookie saved in the old shape must not make a session unrestorable.

`Storage.setCookies` is all-or-nothing: one cookie whose `partitionKey` is a site string
rather than an object fails the whole call with
`Failed to deserialize params.cookies.partitionKey`. Sixteen cookies out of a hundred and
twenty in a real vault were enough to leave that account unable to restore its session.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "_session_vault_under_test", Path(__file__).resolve().parents[1] / "scripts" / "session_vault.py")


def _module():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    module = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(module)
    return module


VAULT = _module()


def test_a_site_string_becomes_the_object_the_browser_wants():
    out = VAULT._restorable_cookie({"name": "a", "partitionKey": "https://crowdworks.jp"})
    assert out["partitionKey"] == {"topLevelSite": "https://crowdworks.jp",
                                   "hasCrossSiteAncestor": False}
    assert out["name"] == "a"


def test_an_object_partition_key_is_left_exactly_as_it_is():
    partition = {"topLevelSite": "https://coconala.com", "hasCrossSiteAncestor": True}
    cookie = {"name": "b", "partitionKey": partition}
    assert VAULT._restorable_cookie(cookie) == cookie


def test_a_cookie_without_a_partition_key_is_untouched():
    cookie = {"name": "c", "value": "v"}
    assert VAULT._restorable_cookie(cookie) is cookie


@pytest.mark.parametrize("partition", [0, [], "", {}.get("x")])
def test_a_key_the_browser_cannot_use_is_dropped_not_guessed(partition):
    out = VAULT._restorable_cookie({"name": "d", "partitionKey": partition})
    assert "partitionKey" not in out or isinstance(out["partitionKey"], dict)


def test_restore_normalises_before_sending():
    source = (Path(__file__).resolve().parents[1] / "scripts" / "session_vault.py").read_text(encoding="utf-8")
    body = source[source.index("def restore():"):]
    send = body.index('_call("Storage.setCookies"')
    assert body.index("_restorable_cookie") < send, (
        "cookies must be normalised before Storage.setCookies, not after")
