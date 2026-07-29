#!/usr/bin/env python3
"""
inventory_status.py — deterministic answer to "does the drain-only loop have ANY real
work to do right now?", so the daily loop (and the health signal) can tell three states
apart that the old "did published.jsonl grow?" proxy could NOT:

  PUBLISHABLE  — there is a ready inventory item (LISTING + icon + skill dir) whose title
                 is not yet on the server, and the 5-slot cap is open. The loop SHOULD run
                 the publish flow. (Also covers a REVIEW_REJECTED item that needs a retry.)
  DRAINED      — every ready inventory title is already online. Nothing to publish. This is
                 HEALTHY IDLE, not a failure — do not alarm, do not burn a self-fix.
  CAP_FULL     — >=5 unlisted (draft/under_review) agents already occupy the publish cap.
                 Wait for review to clear. Healthy idle.
  SERVER_UNREADABLE — publish-list could not be read (auth/network). Report, do not guess.

WHY THIS EXISTS (self-fix-capafy-loop, 2026-07-08):
  The capafy healthcheck escalated an Opus self-fix whenever state/published.jsonl went 30h
  without growing, on the theory "loop alive but produces no skill => CP1 broken". But this
  loop is DRAIN-ONLY over a FINITE, hand-built inventory (c1-c5, o1-o10). Once every built
  listing is online (the real state on 2026-07-08: 20 online, 0 publishable), published.jsonl
  CANNOT grow, so the 30h alarm fires forever and spawns an expensive Opus fixer for a NON-bug.
  The pipeline (agentic cp1_agent.py -> CP2 -> CP3) was never broken; the loop just correctly
  stops at "inventory empty". The health proxy was wrong. This tool gives the loop a truthful
  verdict so the marker it writes distinguishes "healthy idle" from "genuinely stuck".

Server truth only (never the local ledger). Exit 0 always; verdict is on stdout as JSON and
as a VERDICT=<state> line for cheap bash grepping.
"""
import json, os, re, subprocess, sys
from pathlib import Path

REPO_ROOT = Path(os.environ.get("LIFE_MANAGER_REPO", Path(__file__).resolve().parents[3]))
STATE_HOME = Path(os.environ.get(
    "LIFE_MANAGER_STATE_HOME",
    Path.home() / ".local/state/life-manager",
)).expanduser()
AUTO = os.environ.get("CAPAFY_AUTO") or str(REPO_ROOT / "skills/capafy-autopublish")
PUB = os.path.join(AUTO, "vendor", "capafy-publisher")
ICONS = os.environ.get("CAPAFY_ICONS_DIR") or str(STATE_HOME / "assets/capafy/icons")
FEATURES = os.environ.get("CAPAFY_FEATURES_DIR") or str(STATE_HOME / "features")
SKILLS = os.environ.get("CAPAFY_SKILLS_ROOT") or str(REPO_ROOT / "skills")

ONLINE = {"online", "approved"}
UNLISTED = {"draft", "under_review"}   # occupy the 5-slot publish cap
REJECTED = {"review_rejected", "banned"}
CAP = 5


def server_agents():
    """Return list of server agents, or None on read failure."""
    try:
        out = subprocess.run(
            [sys.executable, "packager.py", "publish-list"],
            cwd=PUB, capture_output=True, text=True, timeout=90,
        ).stdout
        return json.loads(out, strict=False)["agents"]["list"]
    except Exception as e:
        print(f"[inventory_status] server read FAILED: {e}", file=sys.stderr)
        return None


def listing_title(path):
    """Extract the '## Title' value from a LISTING.md (same rule publish_prepare.sh uses)."""
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except Exception:
        return None
    for i, ln in enumerate(lines):
        if ln.strip() == "## Title" and i + 1 < len(lines):
            return lines[i + 1].strip()
    return None


def ready_inventory():
    """Ready items = feature dirs with LISTING.md (## Title) + matching icon + a real skill dir."""
    items = []
    if not os.path.isdir(FEATURES):
        return items
    for name in sorted(os.listdir(FEATURES)):
        if not name.startswith("capafy-"):
            continue
        d = os.path.join(FEATURES, name)
        listing = os.path.join(d, "LISTING.md")
        if not os.path.isfile(listing):
            continue
        title = listing_title(listing)
        if not title:
            continue
        m = re.match(r"^capafy-([a-z][0-9]+)-", name)
        if not m:
            continue
        icon = os.path.join(ICONS, m.group(1) + ".png")
        if not os.path.isfile(icon):
            continue
        items.append({"feature": name, "title": title, "icon": icon, "listing": listing})
    return items


def main():
    agents = server_agents()
    if agents is None:
        verdict = {"verdict": "SERVER_UNREADABLE"}
        print("VERDICT=SERVER_UNREADABLE")
        print(json.dumps(verdict, ensure_ascii=False))
        return 0

    online_titles = {(a.get("name") or "").strip() for a in agents if a.get("agentStatus") in ONLINE}
    unlisted = [a for a in agents if a.get("agentStatus") in UNLISTED]
    rejected = [a for a in agents if a.get("agentStatus") in REJECTED]

    # In-flight titles = agents already submitted and awaiting review, or a half-saved draft
    # (draft/under_review). An inventory item whose title is already in-flight must NOT count as
    # publishable — it is done from the loop's side (the resume-guard would just re-open an already
    # status=1 agent, the loop would forever log "PUBLISHABLE" and never reach DRAINED, and the
    # healthcheck's healthy-pass marker would go stale → a FALSE self-fix escalation). Publishable =
    # ready inventory that is NOT online AND NOT already in-flight on the server. (self-fix, 2026-07-08)
    inflight_titles = {(a.get("name") or "").strip() for a in unlisted}

    items = ready_inventory()
    publishable = [it for it in items
                   if it["title"] not in online_titles and it["title"] not in inflight_titles]

    # A rejected agent is only retryable if its title still matches a CURRENT
    # ready_inventory LISTING.md. If the LISTING.md title has since drifted (edited,
    # or the skill was successfully republished under a new agent_id/title), the
    # rejected agent is an ORPHAN: no local content matches it, retrying is a no-op
    # that just creates a duplicate draft (publish_prepare.sh's exact-title RESUME
    # GUARD can never find it). An orphan must NOT block DRAINED forever.
    # (self-fix-capafy-loop, 2026-07-17: found agent 2485008254 stuck exactly this
    # way — review_rejected under an old title "...Built for Retention" while
    # o9's LISTING.md now reads "...Keep Viewers Watching", already online as a
    # different agent_id 7686597754.)
    ready_titles = {it["title"] for it in items}
    retryable_rejected = [a for a in rejected if (a.get("name") or "").strip() in ready_titles]

    if retryable_rejected:
        v = {"verdict": "PUBLISHABLE", "reason": "review_rejected retry",
             "item": {"agent_id": str(retryable_rejected[0].get("agentId")), "title": (retryable_rejected[0].get("name") or "").strip()}}
    elif len(unlisted) >= CAP:
        v = {"verdict": "CAP_FULL", "unlisted": len(unlisted)}
    elif publishable:
        v = {"verdict": "PUBLISHABLE", "item": {k: publishable[0][k] for k in ("feature", "title", "icon", "listing")}}
    else:
        v = {"verdict": "DRAINED"}

    v.update({
        "online_count": len(online_titles),
        "unlisted_count": len(unlisted),
        "rejected_count": len(rejected),
        "ready_inventory": len(items),
        "publishable_count": len(publishable),
    })
    print("VERDICT=" + v["verdict"])
    print(json.dumps(v, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
