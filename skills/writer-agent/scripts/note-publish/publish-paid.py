"""Publish a note.com article as either FREE or PLAIN PAID (買い切り). Generalized CLI,
two-stage guard: without --arm the script configures the selected article type and tags, plus price
and paywall for paid articles, then STOPS before the one irreversible click; with --arm it clicks and
self-verifies.

The Writer money contract uses the plain-paid path at a fixed price supplied by its executable policy.
The generic CLI retains --free for callers outside that Writer contract. The other publisher in this
directory (publish.py) configures a different 無料+メンバーシップ+試し読み shape and is not used by this flow.

Every selector below was read off the live editor, not guessed:
  記事タイプ = input[name="is_paid"] value=free|paid   (click the label, not the input)
  price      = input[type=text][placeholder="300"]     (PRE-FILLED WITH 500 — must be overwritten)
  paywall    = "有料エリア設定" replaces 投稿する until a line is placed; inside it every paragraph
               gets its own 「ラインをこの場所に変更」 button and the current line shows
               「このラインより先を有料にする」

WHY --arm is safe to gate on (measured 2026-07-16, SKILL.md #74): 有料/price/paywall-line/tags are
TRANSIENT draft form state. note only commits them on 投稿する — reload the editor and they are gone
(price reads back NONE, paid radio unchecked). So stopping before the click leaves ZERO trace on
note; there is no "configure now, publish later" because there is nothing left to publish later.
--arm is therefore the only meaningful gate: everything before it is inspectable and reversible by
just not clicking; the moment 投稿する/更新する is clicked (inside the --arm branch, and ONLY there
in this file) the change is real and gets a mandatory self-verify against note's own API.

usage:
  publish-paid.py --key <draft key> --free [--tags "t1,t2,t3"] [--arm]
  publish-paid.py --key <draft key> --price <yen> [--after-chars 2500] [--tags "t1,t2,t3"] [--arm]

  --key          note draft key, e.g. nd963b86eeaa7                              (required)
  --free         publish the complete article for free; --price is not required
  --price        integer yen price                                              (required unless --free)
  --after-chars  free-part length before the paid paywall line, default 2500 — this is note.com's own
                 market shape (punimaru_dev ¥3,480 -> 2,529 chars free; shiro_life0 ¥100,000 -> 2,467).
                 RE-MEASURE per paid article, do not trust the default.
  --tags         comma-separated hashtags, no leading #, up to 5. Pick them by measuring, not vibes:
                 scripts/_shared/tag-counts.py <candidates...> returns real counts; avoid the giants
                 (#AI is 794k, you drown) and take what your buyers actually search.
  --arm          actually click 投稿する/更新する and self-verify via GET /api/v3/notes/{key}. Without
                 this flag the run stops right after printing FREE_ENDS_WITH/PAID_STARTS_WITH — the
                 last chance to eyeball the paywall boundary before anything becomes real.

stdout: machine-readable token lines only (TAGS_ENTERED=, PRICE_READBACK=, PAYWALL_PLACED=,
FREE_ENDS_WITH:, PAID_STARTS_WITH:, GUARD_STOPPED=, POSTED_CLICKED=, API_VERIFY,
FREE_PUBLISHED or PAID_PUBLISHED).
Diagnostics and FATAL errors go to stderr (FATAL: via SystemExit, same as every other script here).
exit 0 = either a clean guard-stop (no --arm) or an armed publish that verified against the API.
exit non-zero = something is wrong; with --arm this can mean the article WAS published but did not
verify — that fact is always printed before the non-zero exit, never hidden.
"""
import argparse
import json
import os
import subprocess
import sys
# --- fail-closed PII gate wiring ---------------------------------------------------
# gate_run_dir raises SystemExit (non-zero) on a finding, a missing blocklist, an unreadable
# artifact, or ANY scanner error. No code path here turns a failure into a publish.
import sys as _pii_sys  # noqa: E402
from pathlib import Path as _PiiPath  # noqa: E402
_pii_sys.path.insert(0, str(next(
    _p / "_shared"
    for _p in _PiiPath(__file__).resolve().parents
    if (_p / "_shared" / "pii_gate.py").is_file()
)))
from pii_gate import gate_run_dir  # noqa: E402

import time
import urllib.request

from publish_guard import assert_publish_allowed
from cloakbrowser import launch_context

WORK = os.path.expanduser("~/.cloak/note-work")
PUBLICATION_GUARD = os.path.join(os.path.dirname(os.path.dirname(__file__)), "publication-guard.py")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--key", help="note draft key, e.g. nd963b86eeaa7")
    p.add_argument("--free", action="store_true", help="publish the complete article for free")
    p.add_argument("--price", type=int, help="integer yen price (required unless --free)")
    p.add_argument("--after-chars", type=int, default=2500,
                    help="free-part length before the paid paywall line (default 2500; re-measure per article)")
    p.add_argument("--tags", default="", help="comma-separated hashtags, no leading #, up to 5")
    p.add_argument("--arm", action="store_true",
                    help="click 投稿する/更新する and self-verify. Without this flag the script stops "
                         "before the click (no trace left on note — see module docstring).")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    # Fail-closed PII gate: this repairs/republishes a LIVE article, so re-scan the frozen
    # artifacts before touching it. An unset ARTICLE_RUN_DIR is itself a refusal.
    gate_run_dir("note-publish-paid", os.environ.get("ARTICLE_RUN_DIR", ""), pair="note/ja")
    if not args.key:
        raise SystemExit("FATAL: --key is required, e.g. --key nd963b86eeaa7")
    if args.free and args.price is not None:
        raise SystemExit("FATAL: --free and --price are mutually exclusive")
    if not args.free and (not args.price or args.price <= 0):
        raise SystemExit("FATAL: --price is required and must be a positive integer yen amount unless --free is set")
    tags = [t.strip().lstrip("#") for t in args.tags.split(",") if t.strip()][:5]
    managed_publication = False

    # The two-factor click guard protects authorization; this run-scoped guard protects
    # idempotency.  Ask note's API about the stable draft key before opening the editor.  If a
    # previous process died after the click but before ledger append, it repairs the receipt and
    # returns without another 更新する click.
    if args.arm:
        checked = subprocess.run(
            [sys.executable, PUBLICATION_GUARD, "preflight", "--pair", "note/ja",
             "--target-kind", "note-key", "--target", args.key],
            check=False, text=True, capture_output=True,
        )
        if checked.returncode != 0:
            raise SystemExit(checked.stderr.strip() or "FATAL: publication resume guard refused note")
        decision = json.loads(checked.stdout)
        managed_publication = decision.get("action") != "manual-unmanaged"
        if decision.get("action") == "skip-live":
            print(f"ALREADY_LIVE_SKIP url={decision['live_url']}")
            return 0

    ck = json.load(open(WORK + "/note-cookies.json"))
    cookies = [{"name": k, "value": v, "domain": ".note.com", "path": "/"} for k, v in ck.items()]
    ctx = launch_context(headless=True, humanize=False)
    try:
        ctx.add_cookies(cookies)
        pg = ctx.new_page()
        pg.set_viewport_size({"width": 1280, "height": 1100})
        pg.goto(f"https://editor.note.com/notes/{args.key}/edit/", wait_until="domcontentloaded", timeout=45000)
        for _ in range(25):
            if "公開に進む" in pg.evaluate("()=>document.body.innerText"):
                break
            time.sleep(1)
        time.sleep(2)
        for b in pg.query_selector_all("button,a"):
            if (b.text_content() or "").strip() == "公開に進む":
                b.click()
                time.sleep(4)
                break

        # 1) 記事タイプ = 無料 or 有料. note requires clicking the label, not the input itself.
        article_type = "free" if args.free else "paid"
        if pg.evaluate("""(value)=>{const r=document.querySelector(`input[name="is_paid"][value="${value}"]`);
            if(!r) return false; (r.closest('label')||r).click(); return true;}""", article_type) is not True:
            raise SystemExit(f"FATAL: {article_type} radio not found")
        time.sleep(2)

        # 1b) hashtags — MEASURED 2026-07-16: tags set through the API (stage2's update_article) are
        # WIPED the moment this form is submitted, because at publish time the browser form is
        # authoritative and its tag field is empty if not filled here. Type them into THIS form, in
        # THIS run. Pick them by measuring (scripts/_shared/tag-counts.py), not vibes.
        if tags:
            inp = pg.query_selector('input[placeholder="ハッシュタグを追加する"]')
            if not inp:
                raise SystemExit("FATAL: hashtag input not found")
            for tg in tags:
                inp.click()
                inp.fill(tg)
                time.sleep(1.0)
                pg.keyboard.press("Enter")
                time.sleep(1.4)
            print("TAGS_ENTERED=" + ",".join(tags))

        if not args.free:
            # 2) price — React ignores a plain .value assignment, so go through the native setter and
            #    fire input/change; then READ IT BACK. "I set it" and "it is set" are different facts.
            pg.evaluate("""(p)=>{const i=[...document.querySelectorAll('input[type=text]')].find(x=>x.placeholder==='300');
                const set=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
                set.call(i,''); i.dispatchEvent(new Event('input',{bubbles:true}));
                set.call(i,p);  i.dispatchEvent(new Event('input',{bubbles:true}));
                i.dispatchEvent(new Event('change',{bubbles:true}));}""", str(args.price))
            time.sleep(2)
            back = pg.evaluate("""()=>{const i=[...document.querySelectorAll('input[type=text]')].find(x=>x.placeholder==='300');return i?i.value:'';}""")
            print(f"PRICE_READBACK={back}")
            if back != str(args.price):
                raise SystemExit(f"FATAL: price did not stick (wanted {args.price}, editor shows {back})")

            # 3) 有料エリア設定 → place the line after the first paragraph past --after-chars
            if not pg.evaluate("""()=>{const b=[...document.querySelectorAll('button,a')].find(x=>(x.textContent||'').trim()==='有料エリア設定'&&x.offsetParent!==null);
                if(b){b.click();return true;} return false;}"""):
                raise SystemExit("FATAL: 有料エリア設定 button not found")
            time.sleep(4)

            placed = pg.evaluate("""(after)=>{
                // Walk the overlay in document order, accumulating the text a reader would see for free,
                // and click the first 「ラインをこの場所に変更」 that appears once we are past `after`.
                const btns=[...document.querySelectorAll('button')].filter(b=>(b.textContent||'').trim()==='ラインをこの場所に変更');
                if(!btns.length) return {ok:false, reason:'no line buttons'};
                let chars=0, chosen=null, idx=-1;
                const walker=document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
                let n;
                while(n=walker.nextNode()){
                  if(n.tagName==='BUTTON' && (n.textContent||'').trim()==='ラインをこの場所に変更'){
                    if(chars>=after){ chosen=n; idx=btns.indexOf(n); break; }
                  } else if(n.children.length===0 && n.textContent){
                    const t=n.textContent.trim();
                    if(t && t!=='ラインをこの場所に変更' && t!=='このラインより先を有料にする') chars+=t.length;
                  }
                }
                if(!chosen){ chosen=btns[btns.length-1]; idx=btns.length-1; }
                chosen.scrollIntoView({block:'center'}); chosen.click();
                return {ok:true, free_chars_before_line:chars, button_index:idx, total_buttons:btns.length};
            }""", args.after_chars)
            print("PAYWALL_PLACED=" + json.dumps(placed, ensure_ascii=False))
            if not placed.get("ok"):
                raise SystemExit(f"FATAL: could not place the paywall line: {placed}")
            time.sleep(3)

            # Show where the line actually landed, in the article's own words, BEFORE anything is
            # published. This is the only chance to see the boundary — see module docstring for why
            # there is no "set it now, inspect it later" for this transient form state.
            around = pg.evaluate("""()=>{
                const marker=[...document.querySelectorAll('*')].find(e=>(e.textContent||'').trim()==='このラインより先を有料にする'&&e.children.length===0);
                if(!marker) return null;
                const txt=[]; const walk=document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
                let n, hit=false, before=[], after=[];
                while(n=walk.nextNode()){
                  if(n===marker){hit=true; continue;}
                  if(n.children.length===0 && n.textContent){
                    const t=n.textContent.trim();
                    if(!t||t==='ラインをこの場所に変更'||t==='このラインより先を有料にする') continue;
                    (hit?after:before).push(t);
                  }
                }
                return {free_tail: before.slice(-3).join(' / ').slice(-260), paid_head: after.slice(0,3).join(' / ').slice(0,260)};
            }""")
            if around:
                print("FREE_ENDS_WITH: " + around["free_tail"])
                print("PAID_STARTS_WITH: " + around["paid_head"])

        if not args.arm:
            print("GUARD_STOPPED=true (no --arm; 投稿する was never clicked, nothing changed on note)")
            return 0

        # 4) publish — the only irreversible step, and the only place this file clicks
        # 投稿する/更新する. Guarded exactly like publish.py for both free and paid articles.
        # 投稿する appears on a draft and 更新する once the article is already public.
        assert_publish_allowed()
        posted = pg.evaluate("""()=>{const el=[...document.querySelectorAll('button,a,div[role=button],span')]
            .find(b=>['投稿する','更新する'].includes((b.textContent||'').trim())&&b.offsetParent!==null);
            if(el){el.scrollIntoView({block:'center'}); el.click(); return (el.textContent||'').trim();} return '';}""")
        print(f"POSTED_CLICKED={posted or False}")
        if not posted:
            raise SystemExit("FATAL: neither 投稿する nor 更新する found in the publish settings")
        time.sleep(9)
        pg.screenshot(path=WORK + f"/{article_type}-published-{args.key}.png", full_page=False)
    finally:
        try:
            ctx.close()
        except Exception:
            pass

    # 5) Ask note, not the editor. Only the API proves which article type is actually live.
    req = urllib.request.Request(f"https://note.com/api/v3/notes/{args.key}", headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=25))["data"]
    got_price, got_limited, got_trial = d.get("price"), d.get("is_limited"), d.get("is_trial")
    status = d.get("status")
    print(f"API_VERIFY key={args.key} price={got_price} is_limited={got_limited} is_trial={got_trial} status={status}")
    if args.free:
        ok = (got_price in (None, 0)) and (got_limited is False) and (got_trial is False) and status == "published"
        print(f"FREE_PUBLISHED verified={str(ok).lower()} key={args.key} price={got_price}")
        if not ok:
            raise SystemExit(
                f"FATAL: article WAS published (see POSTED_CLICKED above) but the API verify does not match "
                f"the free intent (wanted price=0 is_limited=false is_trial=false status=published; "
                f"got price={got_price} is_limited={got_limited} is_trial={got_trial} status={status}) — "
                f"the publish is real, only the verification failed"
            )
    else:
        ok = (got_price == args.price) and (got_limited is False) and (got_trial is False)
        print(f"PAID_PUBLISHED key={args.key} price={got_price} verified={str(ok).lower()}")
        if not ok:
            raise SystemExit(
                f"FATAL: article WAS published (see POSTED_CLICKED above) but the API verify does not match "
                f"the intent (wanted price={args.price} is_limited=false is_trial=false; got price={got_price} "
                f"is_limited={got_limited} is_trial={got_trial}) — the publish is real, only the verification failed"
            )
    if managed_publication:
        reconciled = subprocess.run(
            [sys.executable, PUBLICATION_GUARD, "reconcile", "--pair", "note/ja"],
            check=False, text=True, capture_output=True,
        )
        if reconciled.returncode != 0:
            raise SystemExit(reconciled.stderr.strip() or "FATAL: note live but receipt reconciliation failed")
        print(f"PUBLICATION_RECEIPT={reconciled.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
