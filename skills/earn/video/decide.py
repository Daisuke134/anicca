"""decide.py — PURE state-machine decision for the earn/video slot. No I/O, no browser: given the
account state + today's date, return the ONE transition the loop should run this wake. Testable in isolation
(tests/test_decide.py). The whole faceless-video lifecycle (create→warmup→affiliate-link→post→record) is
expressed here so the ONE loop drives it with zero human — EVERY step, including the day-7 affiliate link,
is a transition, never a manual後工程.

Transitions:
  S0_create   no account yet                              → create account + profile (icon+bio, NO link)
  S1_warmup   warming, day<7, not yet warmed today        → one day's humanized warmup
  noop        warming but already warmed today            → nothing (bounded/idempotent)
  S2_affiliate day>=7 AND affiliate link not set          → set affiliate/ebook link (the deferred step, in-loop)
  S3_post     warmed AND affiliate set AND not posted today→ generate + post one faceless short
  S4_record   already posted today (or steady state)      → record only real external USDC inflows
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
    if warmup_day >= 7 and not s.get("affiliate_set"):
        return "S2_affiliate"      # day-7 deferred affiliate link, applied automatically IN the loop
    if status in ("warmed", "monetized") and s.get("last_post_date") != today:
        return "S3_post"
    return "S4_record"
