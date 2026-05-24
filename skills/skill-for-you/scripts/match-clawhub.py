#!/usr/bin/env python3
"""
match-clawhub.py — rank ClawHub catalog vs today's profile vector.

Steps:
  1. Load today's profile-YYYY-MM-DD.json (must exist; produced by profile-day.py).
  2. Fetch the ClawHub catalog (URL from skill_for_you.catalog_url).
     - Falls back to scripts/clawhub-fallback.json if the URL is unreachable
       or returns non-200. The audit notes the formal catalog API does not
       exist yet.
  3. Embed each catalog skill (title + summary + tags) using the same backend
     that wrote the profile (or hash-TF if sentence-transformers unavailable).
  4. Cosine-rank, exclude already-installed (`~/.openclaw/skills/<slug>/SKILL.md`
     exists) and currently-muted (per installed.json), deweight recent skips.
  5. Generate a 3-sentence pitch per top-N pick.
  6. Write recommendations-YYYY-MM-DD.json.
  7. Post Slack card with [✅ Install] [❌ Skip] [😴 Mute 7d] buttons,
     unless SKILL_FOR_YOU_DRY_RUN is set.

Outputs:
  ~/.openclaw/workspace/skill-for-you/recommendations-YYYY-MM-DD.json
"""

from __future__ import annotations

import json
import os
import sys
import math
import time
import datetime as dt
import urllib.request
from pathlib import Path
from typing import Iterable, List, Tuple

HOME = Path(os.path.expanduser("~"))
SKILL_DIR = HOME / ".openclaw" / "skills" / "skill-for-you"
WORKSPACE = HOME / ".openclaw" / "workspace" / "skill-for-you"
INSTALLED_PATH = WORKSPACE / "installed.json"
SKILLS_DIR = HOME / ".openclaw" / "skills"
OPENCLAW_JSON = HOME / ".openclaw" / "openclaw.json"
FALLBACK_CATALOG = SKILL_DIR / "scripts" / "clawhub-fallback.json"

DRY_RUN = os.environ.get("SKILL_FOR_YOU_DRY_RUN", "").strip() not in ("", "0", "false", "False")
TODAY_ISO = dt.date.today().isoformat()
NOW = dt.datetime.now(dt.timezone.utc)
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "{{profile.channels.reportChannel}}")
SLACK_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

sys.path.insert(0, str(SKILL_DIR / "scripts"))


# ──────────────────────────────────────────────────────────────────────────────
# Config

def load_wizard_config() -> dict:
    cfg = {
        "catalog_url": "https://clawhub.dev/catalog.json",
        "embed_model": "sentence-transformers/all-MiniLM-L6-v2",
        "daily_n": 1,
    }
    try:
        data = json.loads(OPENCLAW_JSON.read_text())
    except Exception:
        return cfg
    s = (((data.get("skills") or {}).get("skill_for_you")) or {})
    for k in cfg.keys():
        if k in s:
            cfg[k] = s[k]
    return cfg


# ──────────────────────────────────────────────────────────────────────────────
# Catalog fetch + embed

def fetch_catalog(url: str) -> Tuple[List[dict], str]:
    """Returns (list of skill dicts, source_label)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "skill-for-you/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status != 200:
                raise RuntimeError(f"http {resp.status}")
            blob = json.loads(resp.read().decode("utf-8"))
            # Tolerate either {skills:[...]} or [...]
            if isinstance(blob, dict) and "skills" in blob:
                return list(blob["skills"]), f"live:{url}"
            if isinstance(blob, list):
                return blob, f"live:{url}"
            raise RuntimeError("unrecognized catalog shape")
    except Exception as e:
        sys.stderr.write(f"[match-clawhub] catalog fetch failed ({e}); using fallback\n")
        try:
            blob = json.loads(FALLBACK_CATALOG.read_text())
            return list(blob.get("skills") or []), f"fallback:{FALLBACK_CATALOG.name}"
        except Exception as e2:
            sys.stderr.write(f"[match-clawhub] fallback load failed: {e2}\n")
            return [], "none"


def embed_text(text: str, backend: str, model_name: str, dim: int) -> List[float]:
    """Embed using whichever backend the profile used so vectors live in the
    same space."""
    if backend.startswith("sentence-transformers/"):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            name = backend.split("/", 1)[1]
            model = SentenceTransformer(name)
            v = model.encode([text])[0]
            return [float(x) for x in v.tolist()]
        except Exception as e:
            sys.stderr.write(f"[match-clawhub] embed fallback (model load failed: {e})\n")
    return _hash_tf(text, dim)


def _hash_tf(text: str, dim: int) -> List[float]:
    import hashlib, re

    vec = [0.0] * dim
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9_+\-]{2,}", text.lower()):
        h = int(hashlib.blake2b(tok.encode("utf-8"), digest_size=4).hexdigest(), 16)
        vec[h % dim] += 1.0 if (h >> 31) & 1 else -1.0
    n = sum(x * x for x in vec) ** 0.5
    return [x / n for x in vec] if n > 0 else vec


def cosine(a: List[float], b: List[float]) -> float:
    n = min(len(a), len(b))
    num = sum(a[i] * b[i] for i in range(n))
    da = math.sqrt(sum(a[i] * a[i] for i in range(n)))
    db = math.sqrt(sum(b[i] * b[i] for i in range(n)))
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)


# ──────────────────────────────────────────────────────────────────────────────
# Exclude / deweight

def slug_to_local_path(slug: str) -> Path:
    """Map e.g. `karpathy/nanochat@read-arxiv-paper` to a local skill dir name."""
    name = slug.replace("/", "__").replace("@", "__")
    return SKILLS_DIR / name


def already_installed(slug: str) -> bool:
    # Either local skill dir matches OR its trailing leaf matches an existing
    # skill name (loose check).
    if (slug_to_local_path(slug) / "SKILL.md").exists():
        return True
    leaf = slug.split("@", 1)[-1].split("/")[-1]
    return (SKILLS_DIR / leaf / "SKILL.md").exists()


def load_installed_state() -> dict:
    if not INSTALLED_PATH.exists():
        return {}
    try:
        return json.loads(INSTALLED_PATH.read_text())
    except Exception:
        return {}


def state_modifier(slug: str, state: dict) -> Tuple[bool, float]:
    """Return (should_exclude, score_multiplier). 1.0 = neutral."""
    s = state.get(slug)
    if not s:
        return False, 1.0
    action = s.get("action")
    if action == "install":
        return True, 0.0
    if action == "mute":
        until = s.get("mute_until", "")
        try:
            t = dt.datetime.fromisoformat(until)
            if t > NOW:
                return True, 0.0
        except Exception:
            pass
        return False, 0.7
    if action == "skip":
        try:
            t = dt.datetime.fromisoformat(s.get("ts", ""))
            age_h = (NOW - t).total_seconds() / 3600.0
            if age_h < 24:
                return False, 0.5  # downweight 24h after a skip
        except Exception:
            pass
    return False, 1.0


# ──────────────────────────────────────────────────────────────────────────────
# Pitch

def three_sentence_pitch(skill: dict, matched_tokens: List[str]) -> str:
    summary = skill.get("summary") or skill.get("title") or skill.get("slug", "")
    title = skill.get("title") or skill.get("slug", "").split("@")[-1]
    matched = ", ".join(matched_tokens[:3]) if matched_tokens else "your recent activity"
    return (
        f"`{title}` {summary.rstrip('.')}.  "
        f"Today's profile lit up on {matched}, which this skill targets directly.  "
        f"If installed, it'd run in the same pipeline you already use — no new tooling."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Slack

def slack_post(blocks: list, text: str) -> Tuple[bool, str]:
    if not SLACK_TOKEN:
        return False, "no SLACK_BOT_TOKEN set; not posted"
    if DRY_RUN:
        return False, "DRY_RUN; not posted"
    body = json.dumps({"channel": SLACK_CHANNEL, "text": text, "blocks": blocks}).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=body,
        headers={
            "Authorization": f"Bearer {SLACK_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if not data.get("ok"):
                return False, f"slack err: {data}"
            return True, data.get("ts", "")
    except Exception as e:
        return False, f"slack post failed: {e}"


def card_blocks(picks: List[dict]) -> Tuple[list, str]:
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "📦 Today's recommended skill (skill-for-you)"}},
    ]
    fallback_text = "Today's recommended skill"
    for i, p in enumerate(picks, 1):
        slug = p["slug"]
        score = p["score"]
        pitch = p["pitch"]
        section_text = (
            f"*[{i}] `{slug}`*\n"
            f"💡 {pitch}\n"
            f"score: {score:.3f}  •  matched: {', '.join(p.get('matched_tokens', [])[:3])}"
        )
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": section_text}})
        blocks.append({
            "type": "actions",
            "block_id": f"sky_{slug}",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "✅ Install"},
                 "action_id": f"install:{slug}", "value": slug, "style": "primary"},
                {"type": "button", "text": {"type": "plain_text", "text": "❌ Skip"},
                 "action_id": f"skip:{slug}", "value": slug},
                {"type": "button", "text": {"type": "plain_text", "text": "😴 Mute 7d"},
                 "action_id": f"mute:{slug}", "value": slug},
            ],
        })
        fallback_text = f"Today's recommended skill: {slug}"
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": "_skill-for-you · daily 09:30 JST_"}]})
    return blocks, fallback_text


# ──────────────────────────────────────────────────────────────────────────────
# Main

def main() -> int:
    cfg = load_wizard_config()
    profile_path = WORKSPACE / f"profile-{TODAY_ISO}.json"
    if not profile_path.exists():
        sys.stderr.write(
            f"[match-clawhub] no profile for {TODAY_ISO} at {profile_path}; "
            f"run profile-day.py first\n"
        )
        return 2

    profile = json.loads(profile_path.read_text())
    profile_vec = profile["vector"]
    profile_dim = int(profile.get("vector_dim", len(profile_vec)))
    backend = profile.get("embed_backend", "hash-tf-fallback")
    profile_top_tokens = [t for t, _ in profile.get("tokens_top_50") or []]

    catalog, source_label = fetch_catalog(cfg["catalog_url"])
    if not catalog:
        sys.stderr.write("[match-clawhub] empty catalog; aborting\n")
        return 3

    state = load_installed_state()

    ranked: List[dict] = []
    for skill in catalog:
        slug = skill.get("slug")
        if not slug:
            continue
        if already_installed(slug):
            continue
        excl, mult = state_modifier(slug, state)
        if excl:
            continue
        text = " ".join([
            skill.get("title", ""),
            skill.get("summary", ""),
            " ".join(skill.get("tags") or []),
        ])
        v = embed_text(text, backend, cfg["embed_model"], profile_dim)
        score = cosine(profile_vec, v) * mult
        matched = [t for t in profile_top_tokens if any(t in (skill.get("summary", "") + " " + " ".join(skill.get("tags") or [])).lower() for _ in [0])][:5]
        ranked.append({
            "slug": slug,
            "score": score,
            "url": skill.get("url"),
            "summary": skill.get("summary"),
            "matched_tokens": matched,
            "pitch": three_sentence_pitch(skill, matched),
        })

    ranked.sort(key=lambda r: r["score"], reverse=True)
    daily_n = max(1, int(cfg["daily_n"]))
    picks = ranked[:daily_n]

    out = {
        "date": TODAY_ISO,
        "dry_run": DRY_RUN,
        "catalog_source": source_label,
        "embed_backend": backend,
        "candidate_count": len(ranked),
        "picks": picks,
        "all_ranked": ranked,
    }
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    out_path = WORKSPACE / f"recommendations-{TODAY_ISO}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))

    blocks, fallback_text = card_blocks(picks)
    posted, status = slack_post(blocks, fallback_text)

    sys.stderr.write(
        f"[match-clawhub] wrote {out_path}  "
        f"catalog={source_label}  candidates={len(ranked)}  "
        f"top1={picks[0]['slug'] if picks else '-'}  "
        f"slack_posted={posted}  status={status}  dry_run={DRY_RUN}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
