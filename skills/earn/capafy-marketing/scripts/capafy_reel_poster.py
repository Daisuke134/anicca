#!/usr/bin/env python3
"""Browser-direct Capafy Reel adapter with public-URL readback verification."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse


class BrowserChallenge(RuntimeError):
    pass


@dataclass(frozen=True)
class PostRequest:
    video: Path
    caption: str
    handle: str
    port: int
    tid: str
    capability: str
    live: bool


@dataclass(frozen=True)
class PostResult:
    status: str
    reached: str
    published: bool
    reel_url: str | None
    owner_session_verified: bool
    pre_urls: tuple[str, ...]
    post_urls: tuple[str, ...]
    screenshots: tuple[str, ...]


class BrowserAci(Protocol):
    screenshots: list[str]
    def active_handle(self) -> str: ...
    def reel_urls(self) -> set[str]: ...
    def open_composer(self) -> None: ...
    def upload_video(self, path: Path) -> None: ...
    def advance_to_caption(self) -> None: ...
    def enter_caption(self, caption: str) -> None: ...
    def share(self) -> None: ...
    def discard(self) -> None: ...


def _reel_url(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {"instagram.com", "www.instagram.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "reel" or not parts[1]:
        return None
    return f"https://www.instagram.com/reel/{parts[1]}/"


def _result(status: str, reached: str, browser: BrowserAci, pre=(), post=(), url=None, published=False, owner_session_verified=False):
    return asdict(PostResult(status, reached, published, url, owner_session_verified, tuple(sorted(pre)), tuple(sorted(post)), tuple(getattr(browser, "screenshots", ()))))


def _valid_mp4(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() != ".mp4":
        return False
    try:
        return b"ftyp" in path.read_bytes()[:64]
    except OSError:
        return False


def post_reel(request: PostRequest, browser: BrowserAci) -> dict:
    if not _valid_mp4(request.video):
        return _result("invalid_media", "preflight", browser)
    if request.live and request.capability != "publish_probe":
        return _result("capability_refused", "preflight", browser)
    try:
        if browser.active_handle().lstrip("@").lower() != request.handle.lstrip("@").lower():
            return _result("session_handle_mismatch", "session", browser)
        pre = {_reel_url(url) for url in browser.reel_urls()}
        pre.discard(None)
        browser.open_composer()
        browser.upload_video(request.video)
        browser.advance_to_caption()
        browser.enter_caption(request.caption)
        if not request.live:
            browser.discard()
            return _result("dry_verified", "share", browser, pre=pre)
        browser.share()
        post = set(pre)
        polls = max(1, int(os.environ.get("CAPAFY_REEL_READBACK_POLLS", "5")))
        for attempt in range(polls):
            post = {_reel_url(url) for url in browser.reel_urls()}
            post.discard(None)
            if post - pre:
                break
            if attempt + 1 < polls:
                time.sleep(float(getattr(browser, "poll_interval_seconds", 0)))
    except BrowserChallenge:
        return _result("challenge", "session", browser)
    except Exception as exc:
        return _result(f"browser_failure:{type(exc).__name__}", "browser", browser)
    new = post - pre
    if len(new) == 1:
        url = next(iter(new))
        try:
            owner_verified = (
                browser.active_handle().lstrip("@").lower()
                == request.handle.lstrip("@").lower()
            )
        except BrowserChallenge:
            return _result("challenge", "post_write_session", browser, pre, post, url)
        except Exception:
            return _result("post_write_session_unverified", "post_write_session", browser, pre, post, url)
        if not owner_verified:
            return _result("post_write_session_mismatch", "post_write_session", browser, pre, post, url)
        return _result("published_verified", "post_write_session", browser, pre, post, url, True, True)
    if len(new) > 1:
        return _result("share_ambiguous", "public_readback", browser, pre, post)
    return _result("share_unconfirmed", "public_readback", browser, pre, post)


class RawCdpBrowser:
    def __init__(self, request: PostRequest):
        os.environ["CDP_PORT"] = str(request.port)
        helper = Path.home() / ".agents/skills/ig-account-create/scripts"
        sys.path.insert(0, str(helper))
        import cdp  # type: ignore
        self.cdp = cdp
        self.request = request
        self.poll_interval_seconds = 4
        self.screenshots: list[str] = []
        self.shot_dir = Path(os.environ.get("CAPAFY_REEL_SCREENSHOT_DIR", str(Path.home() / ".openclaw/state/capafy-reel-screenshots")))
        self.shot_dir.mkdir(parents=True, exist_ok=True)

    def _eval(self, expression: str):
        value = self.cdp.evaluate(self.request.tid, expression)
        if isinstance(value, dict) and "__error__" in value:
            raise RuntimeError(value["__error__"])
        return value

    def _guard(self):
        path = self._eval("location.pathname") or ""
        if str(path).startswith(("/challenge", "/accounts/login")):
            raise BrowserChallenge(str(path))

    def _shot(self, name: str):
        path = self.shot_dir / f"{int(time.time())}-{name}.png"
        self.cdp.screenshot(self.request.tid, str(path)); self.screenshots.append(str(path))

    def active_handle(self) -> str:
        self.cdp.navigate(self.request.tid, "https://www.instagram.com/accounts/edit/"); time.sleep(4); self._guard()
        value = self._eval("(()=>{const e=document.querySelector('input[name=username]');return e&&e.value})()")
        if not value: raise RuntimeError("username field unavailable")
        return str(value)

    def reel_urls(self) -> set[str]:
        self.cdp.navigate(self.request.tid, f"https://www.instagram.com/{self.request.handle}/reels/"); time.sleep(5); self._guard()
        values = self._eval("(()=>[...document.querySelectorAll('a[href]')].map(a=>a.href).filter(x=>x.includes('/reel/')))()") or []
        self._shot("profile-readback")
        return {str(value) for value in values}

    def open_composer(self) -> None:
        self.cdp.navigate(self.request.tid, "https://www.instagram.com/"); time.sleep(4); self._guard()
        clicked = self._eval("(()=>{const s=[...document.querySelectorAll('svg[aria-label]')].find(x=>['New post','新規投稿'].includes(x.getAttribute('aria-label')));const b=s&&(s.closest('[role=button]')||s.parentElement);if(!b)return false;b.click();return true})()")
        if not clicked: raise RuntimeError("new post control unavailable")
        time.sleep(2); self._shot("composer")

    def upload_video(self, path: Path) -> None:
        ws = self.cdp._connect_page(self.request.tid)
        try:
            root = self.cdp._rpc(ws, 1, "DOM.getDocument", {"depth": -1})["root"]["nodeId"]
            node = self.cdp._rpc(ws, 2, "DOM.querySelector", {"nodeId": root, "selector": "input[type=file]"})["nodeId"]
            if not node: raise RuntimeError("file input unavailable")
            self.cdp._rpc(ws, 3, "DOM.setFileInputFiles", {"nodeId": node, "files": [str(path.resolve())]})
        finally:
            ws.close()
        time.sleep(5); self._guard()

    def advance_to_caption(self) -> None:
        for _ in range(3):
            if self._eval("!!document.querySelector('textarea')"): self._shot("caption"); return
            clicked = self._eval("(()=>{const b=[...document.querySelectorAll('button,[role=button]')].find(x=>['Next','次へ'].includes((x.textContent||'').trim()));if(!b)return false;b.click();return true})()")
            if not clicked: raise RuntimeError("next control unavailable")
            time.sleep(3); self._guard()
        raise RuntimeError("caption step unavailable")

    def enter_caption(self, caption: str) -> None:
        changed = self._eval(f"(()=>{{const e=document.querySelector('textarea');if(!e)return false;const s=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set;s.call(e,{json.dumps(caption)});e.dispatchEvent(new Event('input',{{bubbles:true}}));return true}})()")
        if not changed: raise RuntimeError("caption field unavailable")
        self._shot("share-ready")

    def share(self) -> None:
        clicked = self._eval("(()=>{const b=[...document.querySelectorAll('button,[role=button]')].find(x=>['Share','シェア'].includes((x.textContent||'').trim()));if(!b)return false;b.click();return true})()")
        if not clicked: raise RuntimeError("share control unavailable")
        time.sleep(8); self._guard(); self._shot("shared")

    def discard(self) -> None:
        self._eval("(()=>{const b=[...document.querySelectorAll('button,[role=button]')].find(x=>['Close','閉じる'].includes(x.getAttribute('aria-label')||(x.textContent||'').trim()));if(b)b.click();return true})()")
        time.sleep(1)
        self._eval("(()=>{const b=[...document.querySelectorAll('button')].find(x=>['Discard','破棄'].includes((x.textContent||'').trim()));if(b)b.click();return true})()")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True); parser.add_argument("--caption-file", type=Path, required=True)
    parser.add_argument("--handle", required=True); parser.add_argument("--port", type=int, required=True); parser.add_argument("--tid", required=True)
    parser.add_argument("--expected-capability", required=True)
    mode = parser.add_mutually_exclusive_group(required=True); mode.add_argument("--dry", action="store_true"); mode.add_argument("--live", action="store_true")
    args = parser.parse_args()
    try: caption = args.caption_file.read_text(encoding="utf-8").strip()
    except OSError as exc: print(json.dumps({"status":"invalid_caption","error":str(exc)})); return 2
    request = PostRequest(args.video, caption, args.handle, args.port, args.tid, args.expected_capability, args.live)
    result = post_reel(request, RawCdpBrowser(request)); print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] in {"dry_verified", "published_verified"} else 2


if __name__ == "__main__": raise SystemExit(main())
