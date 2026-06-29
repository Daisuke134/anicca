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

S2 is RE-EVALUABLE, not a trap: run.sh refreshes `affiliate_available` from env EVERY wake (true iff a link
URL is configured). So at day>=7: if a link IS available and not yet set → S2 installs it; if NO link yet →
S2 is skipped and the machine keeps POSTING (S3) daily; the moment a link is configured, S2 fires on the next
wake and installs it. Never stalls, never needs a human, and the monetization link is never permanently unreachable.
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
    # ── warmup COMPLETE (warmup_day >= 7) — posting + monetization are gated on the DAY count, not the
    #    status string, so a finished account always posts even if status was never flipped to "warmed". ──
    # day-7 affiliate link — fires whenever a link is AVAILABLE (env-derived, refreshed each wake) and not set.
    # No link available ⇒ skip to posting; appears later ⇒ S2 fires next wake (re-evaluable, no permanent trap).
    if warmup_day >= 7 and not s.get("affiliate_set") and s.get("affiliate_available"):
        return "S2_affiliate"
    if warmup_day >= 7 and s.get("last_post_date") != today:
        return "S3_post"          # post daily (builds audience even while the affiliate link is still pending)
    return "S4_record"
