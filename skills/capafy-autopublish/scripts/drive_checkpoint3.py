#!/usr/bin/env python3
"""Drive Capafy CP3 (Submit for Review) through a strict raw page-CDP flow."""

from __future__ import annotations

import re
import sys
import time
import urllib.request
from urllib.parse import parse_qsl, urlsplit

from drive_checkpoint2 import (
    _RawPage,
    _bounded_page_call,
    _bounded_page_evaluate,
    _detect_cdp,
    _is_capafy_target_url,
    _validate_cdp_base,
    _open_responsive_page,
    _single_redirect_location,
    _target_url_key,
    _validate_ws_url,
)


CP3_HOST = "capafy.ai"
CP3_PATH = "/developer/createAgent"
CP3_NAV_TIMEOUT_S = 10.0
CP3_HYDRATE_TIMEOUT_S = 10.0
CP3_POLL_S = 0.25


def _is_review_url(url: str) -> bool:
    parts = urlsplit(str(url or ""))
    query = parse_qsl(parts.query, keep_blank_values=True)
    token_values = [value for key, value in query if key == "token"]
    return (
        parts.scheme == "https"
        and parts.netloc.lower() == CP3_HOST
        and parts.path == CP3_PATH
        and not parts.fragment
        and len(query) == 3
        and sorted(query) == sorted([("page", "review"), ("source", "temp-link"), ("token", token_values[0] if len(token_values) == 1 else "")])
        and len(token_values) == 1
        and re.fullmatch(r"[0-9]+", token_values[0]) is not None
    )


def _validate_review_url(url: str) -> str:
    if not _is_review_url(url):
        raise RuntimeError("CP3 URL must be exact HTTPS Capafy createAgent page=review")
    return str(url)


def _resolve_review_url(raw_url: str) -> str:
    raw_url = str(raw_url or "").strip()
    if _is_review_url(raw_url):
        return raw_url
    parts = urlsplit(raw_url)
    if (
        parts.scheme != "https"
        or parts.netloc.lower() != "api.capafy.ai"
        or not re.fullmatch(r"/R[0-9]+", parts.path)
        or parts.query
        or parts.fragment
    ):
        raise RuntimeError("CP3 short URL must be exactly https://api.capafy.ai/R<digits>")
    locations = _single_redirect_location(raw_url, "HEAD")
    if not locations:
        locations = _single_redirect_location(raw_url, "GET")
    if len(locations) != 1:
        raise RuntimeError("CP3 short URL must return exactly one redirect Location")
    return _validate_review_url(locations[0])


def _candidate_page_targets(cdp_base: str):
    cdp_base = _validate_cdp_base(cdp_base)
    import json

    with urllib.request.urlopen(f"{cdp_base}/json/list", timeout=8) as response:
        targets = json.loads(response.read())
    candidates = []
    for target in reversed(targets if isinstance(targets, list) else []):
        if not isinstance(target, dict) or target.get("type") != "page":
            continue
        if not _is_capafy_target_url(target.get("url")):
            continue
        try:
            _validate_ws_url(target.get("webSocketDebuggerUrl"))
        except RuntimeError:
            continue
        candidates.append(target)
    if not candidates:
        raise RuntimeError("no existing Capafy createAgent page target")
    return candidates


def _navigate(page: _RawPage, url: str) -> None:
    _validate_review_url(url)
    expected = _target_url_key(url)
    deadline = time.monotonic() + CP3_NAV_TIMEOUT_S
    result = _bounded_page_call(page, "Page.navigate", {"url": url}, deadline)
    error_text = str(result.get("errorText") or "").strip()
    if error_text:
        raise RuntimeError(f"CP3 Page.navigate failed: {error_text}")
    while time.monotonic() < deadline:
        state = _bounded_page_evaluate(page, "({ready:document.readyState,href:location.href})", deadline)
        if isinstance(state, dict) and state.get("ready") in {"interactive", "complete"}:
            if _target_url_key(str(state.get("href") or "")) != expected:
                raise RuntimeError("CP3 navigation reached the wrong exact target")
            return
        time.sleep(CP3_POLL_S)
    raise RuntimeError("CP3 navigation did not become ready before deadline")


SUBMIT_STATE_JS = """(() => {
  const visible = b => !!(b.offsetWidth || b.offsetHeight || b.getClientRects().length);
  const all = [...document.querySelectorAll('button')].filter(b => visible(b) && b.classList.contains('finalReviewSubmitButton') && ['審査に提出','Submit for Review'].includes((b.textContent || '').trim()));
  const enabled = all.filter(b => !b.disabled);
  const confirms = [...document.querySelectorAll('button')].filter(b => visible(b) && ['提出を確認','Confirm Submit'].includes((b.textContent || '').trim()));
  return {count: all.length, enabled: enabled.length, disabled: all.filter(b => b.disabled).length, confirms: confirms.length};
})()"""


SUBMIT_CLICK_JS = """(() => {
  const visible = b => !!(b.offsetWidth || b.offsetHeight || b.getClientRects().length);
  const xs = [...document.querySelectorAll('button')].filter(b => visible(b) && b.classList.contains('finalReviewSubmitButton') && ['審査に提出','Submit for Review'].includes((b.textContent || '').trim()));
  if (xs.length !== 1 || xs[0].disabled) return {ok:false, reason:'submit-not-unique-or-disabled', count:xs.length};
  xs[0].click();
  return {ok:true};
})()"""


CONFIRM_CLICK_JS = """(() => {
  const visible = b => !!(b.offsetWidth || b.offsetHeight || b.getClientRects().length);
  const xs = [...document.querySelectorAll('button')].filter(b => visible(b) && ['提出を確認','Confirm Submit'].includes((b.textContent || '').trim()));
  if (xs.length !== 1 || xs[0].disabled) return {ok:false, reason:'confirm-not-unique-or-disabled', count:xs.length};
  xs[0].click();
  return {ok:true};
})()"""


def _wait_and_submit(page: _RawPage) -> None:
    deadline = time.monotonic() + CP3_HYDRATE_TIMEOUT_S
    while time.monotonic() < deadline:
        state = _bounded_page_evaluate(page, SUBMIT_STATE_JS, deadline)
        if not isinstance(state, dict):
            raise RuntimeError("CP3 submit state unavailable")
        if state.get("count", 0) > 1 or state.get("enabled", 0) > 1:
            raise RuntimeError(f"CP3 submit button is ambiguous: {state}")
        if state.get("count") == 1:
            if state.get("disabled"):
                raise RuntimeError("CP3 submit button is disabled")
            break
        time.sleep(CP3_POLL_S)
    else:
        raise RuntimeError("CP3 submit button did not hydrate before deadline")

    clicked = _bounded_page_evaluate(page, SUBMIT_CLICK_JS, deadline)
    if not isinstance(clicked, dict) or not clicked.get("ok"):
        raise RuntimeError(f"CP3 submit click rejected: {clicked}")

    deadline = time.monotonic() + CP3_HYDRATE_TIMEOUT_S
    confirmed_clicked = False
    while time.monotonic() < deadline:
        state = _bounded_page_evaluate(page, SUBMIT_STATE_JS, deadline)
        if not isinstance(state, dict):
            raise RuntimeError("CP3 post-submit state unavailable")
        if state.get("confirms", 0) > 1:
            raise RuntimeError(f"CP3 confirmation is ambiguous: {state}")
        if state.get("confirms") == 1 and not confirmed_clicked:
            confirmed = _bounded_page_evaluate(page, CONFIRM_CLICK_JS, deadline)
            if not isinstance(confirmed, dict) or not confirmed.get("ok"):
                raise RuntimeError(f"CP3 confirmation click rejected: {confirmed}")
            confirmed_clicked = True
        elif state.get("count") == 1 and state.get("disabled") == 1:
            return
        time.sleep(CP3_POLL_S)
    raise RuntimeError("CP3 submit did not become disabled or show a unique confirmation")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("ERR: need CP3 url")
        return 1
    resolved = _resolve_review_url(argv[1])
    cdp = _detect_cdp()
    targets = _candidate_page_targets(cdp)
    page = _open_responsive_page(targets)
    try:
        page.call("Page.enable")
        page.call("Page.bringToFront")
        _navigate(page, resolved)
        _wait_and_submit(page)
        print("RESULT: submitted")
        return 0
    finally:
        page.close()


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception as exc:
        print(f"ERR: CP3 failed ({type(exc).__name__}: {str(exc)[:160]})")
        sys.exit(1)
