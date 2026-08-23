# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright>=1.40"]
# ///
"""Publish one standalone post, quote, or reply through the leased CDP browser.

A quote tweet is a normal post whose body ends with the quoted post's URL -- X renders the
embedded card itself. That is deliberately the least selector-dependent path available: no
retweet dropdown, no menu item, no locale-specific label.

Exit 0 ONLY after the published post has been read back from the account timeline and its
permalink captured. A compose box that accepted text is not evidence that anything shipped,
so every other outcome exits non-zero and the caller must not record a post.
"""
import argparse
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright


def ensure_logged_in(page) -> str:
    for attempt in (1, 2):
        page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(6000)
        link = page.query_selector('[data-testid="AppTabBar_Profile_Link"]')
        if link:
            return (link.get_attribute("href") or "").strip("/")
        if attempt == 2:
            break
        token = os.environ.get("TWITTER_AUTH_TOKEN", "")
        if not token:
            raise SystemExit("x_post: not logged in and TWITTER_AUTH_TOKEN is unset")
        page.context.add_cookies([
            {"name": "auth_token", "value": token, "domain": ".x.com", "path": "/",
             "httpOnly": True, "secure": True, "sameSite": "None"},
        ])
    raise SystemExit("x_post: X session could not be restored from TWITTER_AUTH_TOKEN")


def get_page(browser):
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    for p in ctx.pages:
        if "x.com" in p.url and "doubleclick" not in p.url:
            return p
    return ctx.pages[0] if ctx.pages else ctx.new_page()


def scan_timeline(page, handle: str, needle: str):
    for art in page.query_selector_all('article[data-testid="tweet"]'):
        text_el = art.query_selector('div[data-testid="tweetText"]')
        body = text_el.inner_text() if text_el else ""
        if needle and needle in body.replace("\n", ""):
            link = art.query_selector(f'a[href*="/{handle}/status/"]')
            href = link.get_attribute("href") if link else ""
            if href:
                return "https://x.com" + href.split("/photo/")[0]
    return None


def find_reply_permalink(pw, cdp: str, source_url: str, handle: str, needle: str, attempts: int = 5):
    """A reply lives in the conversation, not on the profile timeline, so read it back there.

    Scanning the profile would report every reply as unverified: X files replies under a separate
    tab, and treating that absence as failure would consume sources for posts that did ship.
    """
    for attempt in range(attempts):
        try:
            browser = pw.chromium.connect_over_cdp(cdp)
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.new_page()
            try:
                page.goto(source_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(6000)
                found = scan_timeline(page, handle, needle)
                if found:
                    return found
            finally:
                page.close()
        except Exception as exc:
            print(f"x_post: reply read-back attempt {attempt + 1} failed: {exc}", file=sys.stderr)
        time.sleep(6)
    return None


def find_permalink(pw, cdp: str, handle: str, needle: str, attempts: int = 6):
    """Read the account timeline back and return the permalink of the post we just made.

    Reconnects on every attempt instead of holding one page handle. The browser can die
    underneath this step -- it did on 2026-08-17, when navigating away from a dirty composer
    fired a beforeunload dialog and killed the Playwright driver process -- and a read-back that
    cannot survive that turns a published post into an unrecorded one.
    """
    for attempt in range(attempts):
        try:
            browser = pw.chromium.connect_over_cdp(cdp)
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.new_page()   # own tab: never navigate one that might hold composer text
            try:
                page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(5000)
                found = scan_timeline(page, handle, needle)
                if found:
                    return found
            finally:
                page.close()
        except Exception as exc:
            print(f"x_post: read-back attempt {attempt + 1} failed: {exc}", file=sys.stderr)
        time.sleep(6)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--cdp",
        default=os.environ.get("CDP"),
        help="leased CDP base URL (or CDP from with-browser.sh)",
    )
    ap.add_argument("--source-url", help="the post being quoted or replied to")
    ap.add_argument("--text-file", required=True, help="file holding the comment body")
    # A quote is a new post from an account with no followers, which asks the ranker to distribute
    # out-of-network content to nobody. A reply is rendered to the people already reading the
    # original, and "the author engaged your reply" is the single highest-weighted signal X
    # publishes (+75, against 0.5 for a like).
    ap.add_argument("--mode", choices=["post", "quote", "reply"], default="quote")
    args = ap.parse_args()
    if not args.cdp:
        ap.error("--cdp or the CDP environment variable is required")

    if args.mode in {"quote", "reply"} and not args.source_url:
        ap.error("--source-url is required for quote and reply modes")

    text = open(args.text_file, encoding="utf-8").read().strip()
    if not text:
        raise SystemExit("x_post: refusing to publish an empty comment")

    needle = "".join(text.split("\n")[0])[:24]
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(args.cdp)
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        handle = ensure_logged_in(get_page(browser))

        # NEVER navigate or close a tab that still holds composer text. X guards it with
        # beforeunload, and the dialog is handled by the driver that OWNS the persistent context,
        # not by this connection -- its auto-accept raced the dialog closing itself, threw
        # "No dialog is showing" as an uncaught Node rejection, and killed the whole browser twice
        # (2026-08-17 10:28 and 10:35). So the composer gets its own tab, and that tab is only ever
        # closed after it is provably clean.
        compose = ctx.new_page()
        published = False
        try:
            if args.mode == "reply":
                # Reply inline on the post's own page: no URL is appended, because the reply is
                # already attached to the conversation and a link would only spend characters and
                # trip the link penalty.
                compose.goto(args.source_url, wait_until="domcontentloaded", timeout=60000)
                compose.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=45000)
                compose.click('[data-testid="tweetTextarea_0"]')
                compose.keyboard.type(text, delay=18)
                compose.wait_for_timeout(2000)
            else:
                compose.goto("https://x.com/compose/post", wait_until="domcontentloaded", timeout=60000)
                compose.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=45000)
                compose.click('[data-testid="tweetTextarea_0"]')
                compose.keyboard.type(text, delay=18)
                if args.mode == "quote":
                    compose.keyboard.press("Enter")
                    compose.keyboard.type(args.source_url, delay=12)
                    compose.wait_for_timeout(6000)  # let X resolve the quoted-post card
                else:
                    compose.wait_for_timeout(2000)

            # Scope the button to the composer itself: x.com/home keeps an inline composer mounted
            # whose button carries a confusingly similar testid, and clicking the wrong one silently
            # does nothing (measured 10:35 -- "composer did not close within 30s", zero posts).
            button = (compose.query_selector('[data-testid="tweetButtonInline"]')
                      or compose.query_selector('[data-testid="tweetButton"]'))
            if button and button.is_enabled():
                button.click()
            else:
                compose.keyboard.press("Meta+Enter")

            # The composer emptying is X's own acknowledgement that it took the post.
            try:
                compose.wait_for_selector('[data-testid="tweetTextarea_0"]',
                                          state="detached", timeout=30000)
                published = True
            except Exception:
                body = compose.query_selector('[data-testid="tweetTextarea_0"]')
                published = bool(body) and not (body.inner_text() or "").strip()
                if not published:
                    print("x_post: composer still holds text -- publish did not go through",
                          file=sys.stderr)
        finally:
            # Discard through X's own UI rather than navigating away: Escape opens an in-page
            # confirmation sheet, not a JavaScript dialog, so nothing can crash the owner driver.
            if not published:
                try:
                    compose.keyboard.press("Escape")
                    compose.wait_for_timeout(1500)
                    confirm = compose.query_selector('[data-testid="confirmationSheetConfirm"]')
                    if confirm:
                        confirm.click()
                        compose.wait_for_timeout(1500)
                except Exception as exc:
                    print(f"x_post: could not discard the draft: {exc}", file=sys.stderr)
            try:
                compose.close()
            except Exception as exc:
                print(f"x_post: leaving the compose tab open: {exc}", file=sys.stderr)

        if not published:
            permalink = None
        elif args.mode == "reply":
            permalink = find_reply_permalink(pw, args.cdp, args.source_url, handle, needle)
        else:
            permalink = find_permalink(pw, args.cdp, handle, needle)

    if not published:
        # The composer never emptied and the draft was discarded: nothing reached X. The caller
        # must NOT consume the source, or a post nobody ever saw would be crossed off the list.
        json.dump({"posted": False, "mode": args.mode, "handle": handle, "source_url": args.source_url,
                   "reason": "composer never emptied -- the post was not submitted"},
                  sys.stdout, ensure_ascii=False)
        print()
        sys.exit(1)

    if not permalink:
        # "Composer accepted it, timeline could not confirm it" is NOT "did not publish". Say
        # unverified so the caller consumes the source anyway rather than quoting it twice.
        json.dump({"posted": "unverified", "mode": args.mode, "handle": handle, "needle": needle,
                   "source_url": args.source_url,
                   "reason": "publish was accepted but no matching post was found on the timeline"},
                  sys.stdout, ensure_ascii=False)
        print()
        sys.exit(2)

    json.dump({"posted": True, "mode": args.mode, "handle": handle, "post_url": permalink,
               "source_url": args.source_url}, sys.stdout, ensure_ascii=False)
    print()


if __name__ == "__main__":
    main()
