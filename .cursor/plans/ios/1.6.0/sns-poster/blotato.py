"""
DEPRECATED — Blotato → Postiz migration (2026-05-07, Daisuke direction).

This file used to wrap Blotato's API. Blotato is no longer used; all calls now
go through Postiz. This shim re-exports the new PostizClient under the old
BlotatoClient name (and re-exports the module-level helpers) so existing imports
keep working without code changes.

New code should `from postiz import PostizClient, post, upload_media` directly.

Bug fix: the old default `account="x_xg2grb"` resolved to a non-existent ACCOUNTS
key, masking typos as KeyErrors. PostizClient now raises a clear ValueError on
unknown account keys, and the X default is `x_aniccaxxx`.

Original implementation backed up at:
  blotato.py.bak.20260507-2030-pre-postiz
"""
import warnings as _warnings

from postiz import (
    PostizClient,
    get_client,
    post,
    upload_media,
    resolve_integration_id,
)

_warnings.warn(
    "blotato.py is deprecated; use `from postiz import PostizClient, post, upload_media`. "
    "This module will be removed after the Postiz migration grace period.",
    DeprecationWarning,
    stacklevel=2,
)

# Back-compat alias.
BlotatoClient = PostizClient

__all__ = [
    "BlotatoClient",
    "PostizClient",
    "get_client",
    "post",
    "upload_media",
    "resolve_integration_id",
]


if __name__ == "__main__":
    client = PostizClient()
    print("=== Postiz Integrations (via deprecated blotato shim) ===")
    print(client.list_accounts())
