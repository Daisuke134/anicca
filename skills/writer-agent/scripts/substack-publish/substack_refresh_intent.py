#!/usr/bin/env python3
"""Restore the paid contract on one persisted, unpublished Substack ID."""
import argparse, importlib.util, json
from pathlib import Path
from urllib.parse import urlparse

P=Path(__file__).with_name("substack_inplace_repair.py")
S=importlib.util.spec_from_file_location("substack_repair",P); m=importlib.util.module_from_spec(S); S.loader.exec_module(m)

def _publication_host(value):
    if isinstance(value, dict):
        for key in ("subdomain", "host", "domain", "url"):
            host = _publication_host(value.get(key))
            if host:
                return host
        return ""
    if not isinstance(value, str):
        return ""
    value=value.strip().lower()
    if not value:
        return ""
    if "://" in value:
        value=urlparse(value).hostname or ""
    value=value.rstrip("/")
    if value and "." not in value:
        value=f"{value}.substack.com"
    return value if value.endswith(".substack.com") else ""

def _draft_publication_host(draft):
    for key in ("publication", "draft_publication", "publication_host", "publication_subdomain", "subdomain"):
        host=_publication_host(draft.get(key))
        if host:
            return host
    return ""

def _authenticated_draft_publication_host(draft):
    direct = _draft_publication_host(draft)
    if direct:
        return direct
    publication_id = draft.get("publication_id")
    if not str(publication_id).isdigit():
        return ""
    try:
        profile = m._request("GET", "/api/v1/publication")
    except (OSError, ValueError, m.SubstackRepairRefused):
        return ""
    if not isinstance(profile, dict) or str(profile.get("id")) != str(publication_id):
        return ""
    return _publication_host(profile)

def refresh(pair):
    state=m._state(); entry=state["pairs"][pair]; target=str(entry.get("target",""))
    if entry.get("status")!="intent" or not target.isdigit(): raise m.SubstackRepairRefused("persisted intent missing")
    old=m._request("GET",f"/api/v1/drafts/{target}")
    if not isinstance(old, dict) or str(old.get("id", "")) != target:
        raise m.SubstackRepairRefused("draft identity readback missing")
    draft_publication=_authenticated_draft_publication_host(old)
    if not draft_publication:
        raise m.SubstackRepairRefused("draft publication identity readback missing")
    if draft_publication != m._publication():
        raise m.SubstackRepairRefused("draft publication identity does not match configured publication")
    title=str(old.get("draft_title") or old.get("title") or "").strip()
    bylines=old.get("draft_bylines")
    if not isinstance(bylines, list) or not bylines:
        raise m.SubstackRepairRefused("draft byline identity readback missing")
    byline_ids={int(x["id"]) for x in bylines if isinstance(x,dict) and str(x.get("id","")).isdigit()}
    if not title or byline_ids!={m._identity()}: raise m.SubstackRepairRefused("owned title/byline missing")
    media=state["media"]; headline=media["headline_image"]; bodies=media["body_assets"]
    for x in [headline,*bodies]:
        p=Path(x["path"])
        if not p.is_file() or m.sha256(p)!=x["sha256"]: raise m.SubstackRepairRefused("immutable media changed")
    pub=m._publication(); cookie=m._cookie()
    hu=m.upload_image(headline["path"],pub,cookie); bu=[m.upload_image(x["path"],pub,cookie) for x in bodies]
    payload=m._paid_payload_builder()(title=title,subtitle=str(old.get("draft_subtitle") or old.get("subtitle") or ""),markdown=m.adapt_body(state,pair.split("/")[1],hu,bu),byline_id=m._identity())
    updated=m._request("PUT",f"/api/v1/drafts/{target}",payload=payload)
    if str(updated.get("id",""))!=target: raise m.SubstackRepairRefused("same-ID refresh failed")
    return {"pair":pair,"target":target,"refreshed":True}
def main():
    p=argparse.ArgumentParser();p.add_argument("--pair",required=True,choices=("substack/ja","substack/en"));a=p.parse_args()
    print(json.dumps(refresh(a.pair),separators=(",",":")));return 0
if __name__=="__main__": raise SystemExit(main())
