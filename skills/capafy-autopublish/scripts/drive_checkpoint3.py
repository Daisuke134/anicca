#!/usr/bin/env python3
"""Drive Capafy Web Checkpoint 3 (Submit for Review) via camofox REST.

Submit-for-Review modal is React-controlled and only mounts when the button
is .click()'d from inside a JS context, not via Playwright's ref-click.
So this driver opens the tab and runs a single evaluate that clicks the
submit button, waits for the modal to mount, then clicks the "Confirm
Submit" button by exact text match.

usage: drive_checkpoint3.py <review_url>
"""

import json
import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright


def _detect_cdp():
    """Use the live CloakBrowser transport; the old CamoFox daemon is retired."""
    override = os.environ.get("CP1_CDP_URL")
    candidates = [override] if override else ["http://localhost:9222", "http://localhost:9223"]
    for url in candidates:
        if not url:
            continue
        try:
            with urllib.request.urlopen(f"{url}/json/version", timeout=2):
                return url
        except OSError:
            pass
    raise RuntimeError("CloakBrowser CDP unavailable on 9222/9223")


SUBMIT_JS = """(async ()=>{
  let submit=null;
  for(let i=0;i<24;i++){
    submit=Array.from(document.querySelectorAll('button'))
      .find(b=>b.classList && b.classList.contains('finalReviewSubmitButton'));
    if(submit) break;
    await new Promise(r=>setTimeout(r,500));
  }
  if(!submit) return {stage:'submit', error:'NO_SUBMIT_BTN'};
  submit.click();
  await new Promise(r=>setTimeout(r,1800));
  const all=Array.from(document.querySelectorAll('button'));
  const confirm=all.find(b=>b.textContent && b.textContent.trim()==='Confirm Submit');
  if(!confirm) return {stage:'modal', error:'NO_CONFIRM_BTN'};
  confirm.click();
  await new Promise(r=>setTimeout(r,3500));
  return {submitted:true, url:location.href, dialogs:document.querySelectorAll('[role=dialog]').length};
})()"""


def main(argv):
    url = argv[1]
    cdp = _detect_cdp()
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(cdp)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=120000)
        data = page.evaluate(SUBMIT_JS)
        print(f"[cp3] {json.dumps(data, ensure_ascii=False)}", file=sys.stderr)
        if data.get("error"):
            raise RuntimeError(f"checkpoint3 stage={data.get('stage')} error={data['error']}")
        if not data.get("submitted"):
            raise RuntimeError(f"checkpoint3 did not submit: {data}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
