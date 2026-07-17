#!/usr/bin/env python3
"""
B5 — Capafy marketing X (Twitter) poster.

Posts a Capafy skill listing to X via Postiz as a 2-tweet self-thread:
  tweet 1 = native value post, NO link  (X down-ranks link-in-body)
  tweet 2 = self-reply carrying the Capafy listing URL (UTM-tagged for attribution)

This is a DETERMINISTIC TOOL. It does NOT call any LLM — the running agent (or the
B1 selector upstream) writes `--tweet` (and optionally `--reply`); this script only
does the mechanical Postiz posting + ledger bookkeeping. Copy = input, never invented here.

Default mode is DRAFT (Postiz type:"draft") — a real Postiz object is created but nothing
is published to the live @aniccaxxx feed, so the full pipeline is proven WITHOUT a live
brand post. `--live` switches to type:"now" (production cron only).

Emits a single clean JSON object on stdout (loop-child contract).

★ KNOWN BLOCKER (verified live 2026-07-18, 5 tests on @diceai0) ★
The Postiz public-API rail STRIPS ALL URLs from tweet content — verified across:
text+url reply, url-only reply, single-tweet-body url, and shortLink true AND false,
with both an un-previewable SPA url (capafy.ai) and a known-good url (github.com).
The root native tweet publishes fine, but the self-reply link NEVER reaches X.
=> This poster CANNOT deliver the required self-reply link via Postiz today.
   Do NOT wire it to a live cron until the rail is switched to browser-direct
   (drive X compose on CloakBrowser :9222, like ig-reels-poster) or the X API v2.
   The code below is correct; the Postiz rail is the blocker.
"""
import argparse, datetime, json, os, sys, time, urllib.request, urllib.error

POSTIZ_BASE = "https://api.postiz.com/public/v1"
LEDGER = os.path.expanduser("~/.openclaw/state/capafy-marketing-x-ledger.jsonl")
UTM = "utm_source=x&utm_medium=x_reply&utm_campaign=capafy_marketing"


def _tag_url(url: str) -> str:
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{UTM}"


def _post_postiz(api_key: str, integration_id: str, tweets: list, mode: str) -> dict:
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    body = {
        "type": mode,  # "draft" (test) | "now" (production publish)
        "date": now_iso,  # Postiz requires a valid ISO-8601 date even for now/draft
        "shortLink": False,  # keep the raw Capafy URL — do not let Postiz wrap it
        "tags": [],
        "posts": [{
            "integration": {"id": integration_id},
            # a multi-element value array is a native X self-thread:
            # value[0] is the root tweet, value[1..] are self-replies to it.
            # each element needs content + an image array (empty = text-only).
            "value": [{"content": t, "image": []} for t in tweets],
            "settings": {"who_can_reply_post": "everyone"},
        }],
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{POSTIZ_BASE}/posts", data=data, method="POST",
        headers={"Authorization": api_key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode())


def _append_ledger(row: dict) -> None:
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    tmp = LEDGER + ".tmp"
    with open(tmp, "w") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with open(LEDGER, "a") as f, open(tmp) as t:
        f.write(t.read())
    os.remove(tmp)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="Capafy listing URL (from B1 selector)")
    ap.add_argument("--tweet", required=True, help="native value tweet, NO link, <=270 chars (written by the agent)")
    ap.add_argument("--reply", default=None, help="optional self-reply CTA text; the URL is appended automatically")
    ap.add_argument("--live", action="store_true", help="publish for real (type:now). default = draft")
    args = ap.parse_args()

    api_key = os.environ.get("POSTIZ_API_KEY")
    integration_id = os.environ.get("POSTIZ_X_INTEGRATION_ID")
    if not api_key or not integration_id:
        print(json.dumps({"ok": False, "error": "POSTIZ_API_KEY / POSTIZ_X_INTEGRATION_ID not set in env"}))
        return 2

    native = args.tweet.strip()
    if len(native) > 280:
        print(json.dumps({"ok": False, "error": f"tweet too long ({len(native)} > 280)"}))
        return 2
    if "http://" in native or "https://" in native:
        print(json.dumps({"ok": False, "error": "native tweet must NOT contain a link (link goes in the self-reply)"}))
        return 2

    tagged = _tag_url(args.url)
    cta = (args.reply.strip() + " ") if args.reply else "Get it here: "
    reply = f"{cta}{tagged}"

    mode = "now" if args.live else "draft"
    try:
        resp = _post_postiz(api_key, integration_id, [native, reply], mode)
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:400]
        print(json.dumps({"ok": False, "error": f"postiz HTTP {e.code}", "detail": detail}))
        return 1
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"postiz call failed: {e}"}))
        return 1

    # Postiz returns a top-level array: [{ postId, releaseURL, ... }]
    if isinstance(resp, list):
        first = resp[0] if resp else {}
    else:
        posts = resp.get("posts") or []
        first = posts[0] if posts else resp
    row = {
        "ts": int(time.time()),
        "mode": mode,
        "listing_url": args.url,
        "tagged_url": tagged,
        "post_id": first.get("postId") or first.get("id"),
        "release_url": first.get("releaseURL"),
    }
    _append_ledger(row)
    print(json.dumps({"ok": True, **row}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
