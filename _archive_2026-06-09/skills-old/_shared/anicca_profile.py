"""
Shared profile loader — keeps Anicca OSS-general (one canonical profile schema).

Personal data lives in a gitignored per-user file `$ANICCA_HOME/identity/profile.json`
(see identity/profile.example.json). This module is the single adapter the skills
use, so the wake / lateness / renraku engines never hardcode anyone's details and
there is exactly ONE profile schema across the whole repo.

Canonical schema (identity/contact/work/education/...) + these alarm/lateness
sections used by the wake & never-late engines:

  "identity":  { "{{profile.lateness.stakeholders.senderType}}Name","{{profile.lateness.stakeholders.senderType}}Name","preferredName","homeAddress","timezone" }
  "contact":   { "phone","personalEmail","workEmail" }
  "location":  { "homeLat", "homeLon" }
  "alarm":     { "wakeTime": "07:00" }
  "lateness":  {
     "defaultSenderType": "{{profile.lateness.stakeholders.senderType}}" | "{{profile.lateness.stakeholders.senderType}}",
     "stakeholders": [
        { "match": "<regex on event text>", "channel": "{{profile.lateness.stakeholders.channel}}"|"slack"|"{{profile.lateness.stakeholders.channel}}",
          "toField": "{{profile.lateness.stakeholders.toField}}",  # dotted path into THIS profile (no PII in code)
          "senderType": "{{profile.lateness.stakeholders.senderType}}"|"{{profile.lateness.stakeholders.senderType}}" }
     ]
  }

Source principle: 12factor.net/config — strict separation of config from code.
"""
import json
import os
import re
from pathlib import Path

_CACHE = None


def anicca_home():
    return Path(os.environ.get("ANICCA_HOME", str(Path.home() / ".openclaw")))


def load_profile():
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads((anicca_home() / "identity" / "profile.json").read_text(encoding="utf-8"))
    return _CACHE


def get(path, default=None):
    cur = load_profile()
    for k in path.split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


# ---- engine accessors (stable interface; map canonical schema -> engine needs) ----
def name():
    return (get("identity.preferredName")
            or (get("identity.{{profile.lateness.stakeholders.senderType}}Name", "").split() or [""])[0]
            or get("identity.{{profile.lateness.stakeholders.senderType}}Name", ""))


def phone():
    return get("contact.phone", "")


def google_account():
    return get("contact.personalEmail", "")


def home_address():
    return get("identity.homeAddress", "")


def home_latlon():
    return get("location.homeLat"), get("location.homeLon")


def wake_time():
    return get("alarm.wakeTime", "07:00")


def _sender(stype):
    return get("identity.{{profile.lateness.stakeholders.senderType}}Name", "") if stype == "{{profile.lateness.stakeholders.senderType}}" else get("identity.{{profile.lateness.stakeholders.senderType}}Name", "")


def identity_for(text):
    """Signing name for an event/context (comedy={{profile.lateness.stakeholders.senderType}} name, work/academic={{profile.lateness.stakeholders.senderType}})."""
    text = text or ""
    for s in (get("lateness.stakeholders") or []):
        if s.get("match") and re.search(s["match"], text, re.I):
            return _sender(s.get("senderType", get("lateness.defaultSenderType", "{{profile.lateness.stakeholders.senderType}}")))
    return _sender(get("lateness.defaultSenderType", "{{profile.lateness.stakeholders.senderType}}"))


def stakeholder_for(text):
    """Resolve {channel,to,sender} for this event from the profile, or None.
    `toField` is a dotted path into this profile so no recipient lives in code."""
    text = text or ""
    for s in (get("lateness.stakeholders") or []):
        if s.get("match") and re.search(s["match"], text, re.I):
            to = get(s["toField"]) if s.get("toField") else s.get("to")
            return {"channel": s.get("channel", "{{profile.lateness.stakeholders.channel}}"), "to": to or "",
                    "sender": _sender(s.get("senderType", "{{profile.lateness.stakeholders.senderType}}")), "note": s.get("note", "")}
    return None
