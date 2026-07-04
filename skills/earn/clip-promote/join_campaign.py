"""join_campaign.py — JOIN (REQ-1b): actually attempt to join the SELECTed campaign on
promote.fun. A campaign's minimum-follower requirement is INVISIBLE until join is
attempted (its Rules tab stays locked with "Join the Campaign to unlock full details"
pre-join — verified live 2026-07-04 on thomas-rhett-content/susannah-joffe). This module
does the live attempt and classifies the outcome so the caller (run.sh) knows whether to
proceed to CLIP or mark the campaign permanently skipped.

Discovered live 2026-07-04 (fresh evidence, not assumed): of 17 IG-eligible campaigns,
15 were already Ended/budget-exhausted (some showed "Live" in the UI while their budget
bar read "$0.00 left" — Ended/budget state must be read from page text, not the badge
alone). The 2 genuinely open ones (thomas-rhett-content, susannah-joffe) both gated on a
minimum follower count (2000, 200) our fresh 0-follower account could not clear. See spec
docs/superpowers/specs/2026-07-04-openclaw-claude-p-merge-design.md §18 for the full
investigation. The takeaway (Dais 2026-07-04 verbatim): "in order to do good money-making
affiliate work, you have to earn trust and followers first" — this module's job is only
to detect the gate honestly, never to fabricate a join that didn't happen.
"""
import json
import re
import time


def _click_join_submit(cdp, tid):
    """The submit button's text is dynamic ("Join with N Account(s)"), so exact-match
    click_by_text can't target it — find-by-prefix via a one-off JS eval instead."""
    js = (
        "(()=>{const btns=Array.from(document.querySelectorAll('button'));"
        "const btn=btns.find(b=>b.textContent&&b.textContent.trim().startsWith('Join with'));"
        "if(!btn)return{found:false};btn.click();return{found:true};})()"
    )
    return cdp.evaluate(tid, js)


def fetch_live(tid, cdp, campaign_slug):
    """Live attempt to join campaign_slug. Returns:
    {"joined": bool, "reason": str, "min_followers": int|None}
    reason values: "ok" | "campaign-ended" | "follower-requirement" | "join-button-not-found"
    """
    cdp.navigate(tid, f"https://www.promote.fun/campaigns/{campaign_slug}")
    time.sleep(3)

    r = cdp.click_by_text(tid, "Join Campaign")
    if not r.get("found"):
        text = cdp.evaluate(tid, "document.body.innerText") or ""
        if "Ended" in text[:2000]:
            return {"joined": False, "reason": "campaign-ended", "min_followers": None}
        return {"joined": False, "reason": "join-button-not-found", "min_followers": None}

    time.sleep(2)
    cdp.click_by_text(tid, "Select All")
    time.sleep(1)

    text = cdp.evaluate(tid, "document.body.innerText") or ""
    m = re.search(r"requires at least ([\d,]+) followers", text)
    if m:
        min_followers = int(m.group(1).replace(",", ""))
        cdp.click_by_text(tid, "Cancel")
        return {"joined": False, "reason": "follower-requirement", "min_followers": min_followers}

    submit = _click_join_submit(cdp, tid)
    if not submit.get("found"):
        return {"joined": False, "reason": "join-button-not-found", "min_followers": None}
    time.sleep(2)
    return {"joined": True, "reason": "ok", "min_followers": None}


if __name__ == "__main__":  # CLI: prints the JOIN outcome as JSON, needs a live CDP tab
    import os
    import sys
    cdp_dir = os.environ.get("CDP_DIR", os.path.expanduser("~/.claude/skills/ig-account-create/scripts"))
    sys.path.insert(0, cdp_dir)
    import cdp  # noqa: E402
    tid = os.environ.get("PF_TID", "")
    slug = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CAMPAIGN_SLUG", "")
    result = fetch_live(tid, cdp, slug)
    print(json.dumps(result, ensure_ascii=False))
