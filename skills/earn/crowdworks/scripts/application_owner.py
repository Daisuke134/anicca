#!/usr/bin/env python3
"""Continuously eligible CrowdWorks application owner; one bounded tick per launch."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[4]
STATE = Path("~/.local/state/anicca/crowdworks").expanduser()
PRODUCT = Path("~/gig/private/storefront-bundle/contracts/market-products/ui-translation.json").expanduser()
TRANSACTION = STATE / "application-transaction.json"
LEDGER = STATE / "application-receipts.jsonl"
SEARCH = "イタリア語 UI Web アプリ 翻訳"

def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module
    spec.loader.exec_module(module); return module

account = _module("crowdworks_account", Path(__file__).with_name("account.py"))
profile = _module("crowdworks_profile", Path(__file__).with_name("profile.py"))
application = _module("crowdworks_application", Path(__file__).with_name("application_tick.py"))

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.current=None; self.jobs=[]
    def handle_starttag(self, tag, attrs):
        href=dict(attrs).get("href","")
        match=re.fullmatch(r"/public/jobs/([0-9]+)",href)
        if tag=="a" and match: self.current=[match.group(1),""]
    def handle_data(self,data):
        if self.current is not None:self.current[1]+=data
    def handle_endtag(self,tag):
        if tag=="a" and self.current is not None:
            self.jobs.append(tuple(self.current));self.current=None

def _get(url: str) -> str:
    request=Request(url,headers={"User-Agent":"Mozilla/5.0"})
    with urlopen(request,timeout=20) as response:return response.read(2_000_000).decode("utf-8","replace")

def _candidate():
    parser=Links();parser.feed(_get("https://crowdworks.jp/public/jobs?search%5Bkeywords%5D="+quote(SEARCH)))
    seen=set()
    for job_id,title in parser.jobs:
        if job_id in seen:continue
        seen.add(job_id); detail=_get(f"https://crowdworks.jp/public/jobs/{job_id}")
        text=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",detail))
        required=("イタリア語" in text and "翻訳" in text and any(word in text for word in ("UI","Webサイト","アプリ","画面文言")))
        forbidden=any(word in text for word in ("このお仕事の募集は終了しています","ネイティブ限定","AI翻訳は禁止","出身地がイタリア語"))
        if required and not forbidden:return {"external_id":job_id,"title":re.sub(r"\s+"," ",title).strip()}
    return None

def _proposal(product):
    return "\n".join((
        "はじめまして。募集内容を拝見し、以下の範囲で対応できます。",
        product["buyer_job"],
        "対応内容: "+"、".join(product["inclusions"]),
        "納品物: "+product["delivery_kind"],
        "必要資料: "+"、".join(product["required_inputs"]),
        product["recurring_support_boundary"],
    ))

def _append(receipt):
    LEDGER.parent.mkdir(parents=True,exist_ok=True)
    with LEDGER.open("a",encoding="utf-8") as handle:
        handle.write(json.dumps(receipt,ensure_ascii=False,separators=(",",":"))+"\n");handle.flush();os.fsync(handle.fileno())

def _write_status(payload):
    path=STATE/"application-owner.json";path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=".application-owner.")
    with os.fdopen(fd,"w",encoding="utf-8") as handle:json.dump(payload,handle,ensure_ascii=False,separators=(",",":"));handle.write("\n");handle.flush();os.fsync(handle.fileno())
    os.chmod(tmp,0o600);os.replace(tmp,path)

def main():
    now=datetime.now(timezone.utc)
    if not account._owner():result={"ok":False,"status":"browser_unavailable","effect_delta":0}
    else:
        browser=account._browser(account.CDP_URL);page=browser.contexts[0].new_page();page.goto(account.DASHBOARD_URL);account._wait(page);authenticated,_=account._auth(page)
        if not authenticated:result={"ok":False,"status":"auth_required","effect_delta":0}
        else:
            configured=profile.run_apply(page=page,receipt_path=STATE/"profile-receipt.json")
            if not configured.get("ok"):
                result={"ok":False,"status":configured.get("error","profile_incomplete"),"effect_delta":0}
            elif (candidate:=_candidate()) is None:
                result={"ok":True,"status":"profile_complete_no_eligible_open_job","effect_delta":0}
            else:
                product=json.loads(PRODUCT.read_text(encoding="utf-8"));due=(date.today()+timedelta(days=7)).isoformat()
                tick=application.execute_application(page=page,opportunity=candidate,proposal_text=_proposal(product),proposed_amount_minor=product["base_price"]["amount"],delivery_due_on=due,expire_period_days=7,state_path=TRANSACTION,ledger_writer=_append,now=lambda:datetime.now(timezone.utc).isoformat(),account_ready=lambda:True)
                result={**tick.to_dict(),"status":"verified" if tick.application_verified else tick.error or tick.reason,"effect_delta":1 if tick.submitted else 0}
        page.close()
    result["observed_at"]=now.isoformat();_write_status(result);print(json.dumps(result,ensure_ascii=False,separators=(",",":")));return 0 if result.get("ok") else 1

if __name__=="__main__":raise SystemExit(main())
