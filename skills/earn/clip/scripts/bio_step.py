#!/usr/bin/env python3
# bio_step.py — CLIP-BIO deterministic step for clip_pass.sh: IG only lets ONE link be
# clickable (the profile "website" / external_url field), so this is the sole money entry
# point for the clip loop. Sets it to offer.json's affiliate_link + ?sid1=<handle> (per-account
# attribution, per offer.json's own sub_id_scheme note).
#
# TIER-1 ONLY (deliberate, per Dais 2026-07-16): this script NEVER calls login_resilient() and
# NEVER touches ~/.cloak/.last-pwlogin-<handle> — it only loads the saved instagrapi session
# (~/.cloak/instagrapi-<handle>.json) and validates it with a read-only get_timeline_feed().
# If that session is missing/invalid it silently no-ops (outcome=skip) rather than triggering
# a password login — poster.py's login_resilient (tier1->tier2->tier3, with the 24h
# tier3 cooldown guard, commit b0a80b65) remains the ONLY path allowed to attempt tier2/tier3
# login, inside run.sh's POST step. Once that step refreshes the saved session, this step
# starts working again on the next pass with no code change needed.
#
# Idempotent: re-reads account_info() before AND after any edit, only writes when the composed
# URL actually differs, and re-verifies the write landed before claiming outcome=set.
#
# stdout: ONE compact JSON line (loop child-script contract). stderr: human-readable detail.
import argparse, json, os, sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

C = os.path.expanduser


def compose_url(affiliate_link, handle):
    # set (not append) sid1=<handle>, so a link that already carries a stale/foreign sid1
    # (e.g. from a manually-edited offer.json) is corrected rather than duplicated.
    parts = urlsplit(affiliate_link)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q["sid1"] = handle
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", required=True)
    a = ap.parse_args()
    handle = a.handle
    res = {"handle": handle, "outcome": "skip", "external_url": None}

    offer_path = C("~/clips/offer.json")
    try:
        offer = json.load(open(offer_path))
    except Exception as e:
        res["reason"] = f"offer.json unreadable: {type(e).__name__}"
        print(json.dumps(res, ensure_ascii=False)); return

    if not offer.get("joined") or not offer.get("affiliate_link"):
        res["reason"] = "offer not joined / no affiliate_link"
        print(json.dumps(res, ensure_ascii=False)); return

    desired = compose_url(offer["affiliate_link"], handle)

    settings = C(f"~/.cloak/instagrapi-{handle}.json")
    if not os.path.exists(settings):
        res["reason"] = "no valid session"
        print(json.dumps(res, ensure_ascii=False)); return

    try:
        from instagrapi import Client
        cl = Client()
        cl.load_settings(settings)
        cl.get_timeline_feed()  # read-only session validation; NEVER falls back to a login
    except Exception as e:
        res["reason"] = "no valid session"
        print(json.dumps(res, ensure_ascii=False), file=sys.stdout)
        print(f"bio_step: session invalid ({type(e).__name__}: {e})", file=sys.stderr)
        return

    try:
        current = cl.account_info()
        current_url = current.external_url or ""
        if current_url == desired:
            res["outcome"] = "noop"; res["external_url"] = desired
            print(json.dumps(res, ensure_ascii=False)); return

        # account_edit merges with the account's OWN current biography/full_name/etc (it reads
        # account_info() internally for any field not passed) so this write cannot blank them.
        cl.account_edit(external_url=desired)
        after = cl.account_info()
        if after.external_url == desired:
            res["outcome"] = "set"; res["external_url"] = desired
        else:
            res["outcome"] = "failed"
            res["reason"] = f"post-write mismatch: got {after.external_url!r}"
        print(json.dumps(res, ensure_ascii=False))
    except Exception as e:
        res["outcome"] = "failed"
        res["reason"] = f"{type(e).__name__}: {str(e)[:200]}"
        print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
