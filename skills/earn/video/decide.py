"""decide.py — PURE state-machine decision for the earn/video slot. No I/O, no browser: given the
account state + today's date, return the ONE transition the loop should run this wake. Testable in isolation
(tests/test_decide.py). The faceless-video lifecycle (warmup→affiliate-link@day7→post→record) is expressed
here so the ONE loop drives it with ZERO human per wake — EVERY recurring step, including the day-7 affiliate
link, is a transition, never a manual後工程. (S0_create = a ONE-TIME bootstrap performed by the ig-account-create
skill, itself proven 0-human; the slot then runs the recurring S1–S4 lifecycle on the existing account.)

Transitions:
  S0_create   no account yet                              → create account + profile (icon+bio, NO link)
  S1_warmup   warming, day<7, not yet warmed today        → one day's humanized warmup
  noop        warming but already warmed today            → nothing (bounded/idempotent)
  S2_affiliate day>=7 AND affiliate not set AND not pending→ set affiliate/ebook link (the deferred step, in-loop)
  S3_post     warmed (warmup done) AND not posted today    → generate + post one faceless short (link optional;
                                                             posting builds audience even while the link is pending)
  S4_record   already posted today (or steady state)      → record only real external USDC inflows

NOTE on the S2 dead-end (fixed): if no affiliate link is available yet, run.sh sets `affiliate_pending=true`
and advances status to `warmed` — so the machine does NOT loop on S2 forever; it proceeds to post daily, and
S2 fires later (clearing `affiliate_pending`) once a link exists. The loop NEVER stalls and NEVER needs a human.
"""

def decide(state, today):
    s = state or {}
    status = s.get("status") or "none"
    if status == "none":
        return "S0_create"
    warmup_day = int(s.get("warmup_day", 0) or 0)
    if status == "warming" and warmup_day < 7:
        if s.get("last_warmup_date") == today:
            return "noop"          # already did today's warmup — idempotent, do nothing this wake
        return "S1_warmup"
    # day-7 affiliate link — only when a link is available-and-not-yet-set (pending ⇒ skip, keep posting)
    if warmup_day >= 7 and not s.get("affiliate_set") and not s.get("affiliate_pending"):
        return "S2_affiliate"
    if status in ("warmed", "monetized") and s.get("last_post_date") != today:
        return "S3_post"
    return "S4_record"
