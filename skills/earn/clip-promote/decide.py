"""decide.py — PURE state-machine decision for the earn/clip-promote slot (promote.fun USDC-Solana
per-view clipping). No I/O, no browser: given the pipeline state + now (epoch seconds), return the ONE
transition this wake should run. Testable in isolation (tests/test_decide.py). Mirrors earn/video/decide.py.

The clip-promote lifecycle (one campaign-clip item at a time, then free the slot for the next):
  SELECT    no active item            → pick an ACTIVE campaign that allows IG, not already clipped
  CLIP      campaign chosen           → produce a 15-45s 1080x1920 clip (earn-clip-rewards)
  POST      clip ready                → post --live to a WARMED account, capture the post URL
  SUBMIT    posted                    → submit the post URL to the campaign on promote.fun
  MEASURE   submitted+accepted        → read views; loop here until the campaign ENDS or it STALLS
  WITHDRAW  campaign ended + balance>0 → claim USDC on Solana, capture the signature
  RECORD    sig captured             → verify the Solana sig + append the ONLY earned_usdc>0 line (DONE)
  STALLED   0 views past DEAD_ZERO_HOURS, or submission rejected/dead → free the slot, narrate

DONE = a RECORD wake only. Every other wake prints earned_usdc:0 and keeps the slot `declared`.
DEAD_ZERO_HOURS (default 48) is the honest dead-vs-early-zero discriminator: a shadowban can't be
detected directly (a throttled reel still resolves + stays accepted), so 0 views past the bound = dead.
"""

DEAD_ZERO_HOURS_DEFAULT = 48


def decide(state, now):
    """Return the ONE transition string for this wake. Pure. `now` = epoch seconds.
    Defensive: an unknown/empty phase resolves to SELECT (free the slot) — never a dead-end."""
    s = state or {}
    phase = s.get("phase") or "SELECT"

    # terminal / free-slot phases → pick the next campaign
    if phase in ("idle", "dead", "stalled", "STALLED", "RECORD", "DONE"):
        return "SELECT"
    if phase == "SELECT":
        return "SELECT"
    if phase == "CLIP":
        return "CLIP"
    if phase == "POST":
        return "POST"
    if phase == "SUBMIT":
        return "SUBMIT"
    if phase == "MEASURE":
        status = s.get("submit_status")
        if status not in (None, "accepted", "active"):
            return "STALLED"  # rejected/disallowed/removed — free the slot (REQ-5a/REQ-6 dead)
        if s.get("campaign_ended") and float(s.get("withdrawable_usdc", 0) or 0) > 0:
            return "WITHDRAW"
        views = float(s.get("views", 0) or 0)
        posted_at = float(s.get("posted_at", 0) or 0)
        dead_hours = float(s.get("dead_zero_hours", DEAD_ZERO_HOURS_DEFAULT) or DEAD_ZERO_HOURS_DEFAULT)
        if views == 0 and posted_at > 0 and (now - posted_at) >= dead_hours * 3600:
            return "STALLED"  # 0 views past the bound = not earning; free the slot (honest, no shadowban overclaim)
        return "MEASURE"
    if phase == "WITHDRAW":
        if s.get("sig"):
            return "RECORD"
        return "WITHDRAW"
    return "SELECT"  # unknown phase → safe default, never a dead-end
