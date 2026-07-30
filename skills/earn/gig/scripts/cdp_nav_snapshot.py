#!/usr/bin/env python3
"""cdp_nav_snapshot.py — deterministic hidden-target evidence helper for the gig reality-verifier
(feature gig-reality-verify, fresh-adversary FIND-001 fix: docs/loop-engineering/26-...md §8).

Unlike cdp_snapshot.py (which only screenshots whatever tab is ALREADY open), this helper actually
performs a real CDP `Page.navigate(url)` call, WAITS for the page to finish loading (Page.loadEventFired
event, with a document.readyState poll fallback), THEN captures rendered DOM text and appends a trajectory
row — so the fresh judge's navigation is a reproducible tool call, not freeform LLM-improvised Bash/CDP
that happened to work once.

get_tab()/navigate mechanics below are self-contained (copied IN, not imported from any path outside
this repo — behavioral-spec REQ-006 requires no dangling cross-repo reference).

Usage:
  python3 cdp_nav_snapshot.py <pass_id> <seq> <label> <url> [action_note]
    e.g. python3 cdp_nav_snapshot.py reality-1783800000 01 reality_check_01 https://coconala.com/mypage/services_lists

Writes:
  ~/gig/trajectory/<pass_id>/<seq>-<label>.json
  appends {ts,pass_id,seq,label,url,title,action,navigated_ok} to ~/gig/trajectory/<pass_id>/trajectory.jsonl
Prints the evidence path on success, or ERROR:<reason> on failure (never raises — capture must never abort
a verification run).
"""
import argparse, asyncio, base64, fcntl, hashlib, json, os, re, sys, subprocess, time, urllib.request
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from urllib.parse import urlparse

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from application_eligibility import evaluate_application

try:
    import websockets
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "websockets", "-q"], capture_output=True)
    import websockets

LOAD_TIMEOUT_SECS = 15  # bounded — never hang the judge indefinitely on a page that never settles
APPLICATION_CONFIRM_SELECTOR = (
    '#OfferAddForm button[type="submit"],'
    'form[action^="/offers/add/"] button[type="submit"]'
)
RETAINER_ULID_PATTERN = re.compile(r"[0-9A-HJKMNP-TV-Z]{26}")


def _cdp_base():
    # No silent default. The old fallback was http://127.0.0.1:9222, which on this host
    # is a proxy onto the SAME browser as gig production :9223 -- the 2026-07-26
    # collision. Whenever the env is set (gig_pass.sh exports :9223) nothing changes;
    # when it is missing we now fail loudly instead of quietly attaching to whatever
    # answers on the interactive port.
    base = os.environ.get("CLOAK_CDP_BASE_URL")
    if not base:
        raise RuntimeError(
            "CLOAK_CDP_BASE_URL is unset. Lease a browser first: "
            "~/.config/ai/bin/browser-guard.sh acquire <identity> "
            "(identities in ~/.config/ai/registry/browsers.toml). "
            "Refusing to guess a CDP port."
        )
    return base.rstrip("/")


def _target_operation_lock_path(
    ws_url: str,
    *,
    leases_path: Path | None = None,
) -> Path:
    target_id = urlparse(ws_url).path.rstrip("/").split("/")[-1]
    if not target_id:
        raise ValueError("target_operation_lock_missing_target")
    if leases_path is None:
        leases_path = Path(os.path.expanduser(
            os.environ.get(
                "CLOAK_CONTEXT_LEASES_FILE",
                "~/.cloak/vault/leases.json",
            )
        ))
    return Path(leases_path).parent / "operations" / f"{target_id}.lock"


def _leases_path() -> Path:
    return Path(os.path.expanduser(
        os.environ.get(
            "CLOAK_CONTEXT_LEASES_FILE",
            "~/.cloak/vault/leases.json",
        )
    ))


def _resolve_lease_ws(lease_name: str) -> str:
    """Resolve an opaque page websocket from a stable, code-owned lease name."""
    if not lease_name:
        raise RuntimeError("context_lease_name_missing")
    try:
        payload = json.loads(_leases_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("context_lease_ledger_unreadable") from error
    held = payload.get(lease_name) if isinstance(payload, dict) else None
    if not isinstance(held, dict):
        raise RuntimeError(f"context_lease_not_found:{lease_name}")
    target_id = str(held.get("target_id") or "")
    ws_url = str(held.get("ws") or "")
    parsed = urlparse(ws_url)
    if (
        not target_id
        or parsed.scheme not in {"ws", "wss"}
        or not parsed.netloc
        or parsed.path != f"/devtools/page/{target_id}"
    ):
        raise RuntimeError(f"context_lease_invalid:{lease_name}")
    return ws_url


def _add_connection_arguments(parser: argparse.ArgumentParser) -> None:
    connection = parser.add_mutually_exclusive_group(required=True)
    connection.add_argument("--ws")
    connection.add_argument("--lease")


def _connection_ws(args: argparse.Namespace) -> str:
    if args.lease:
        return _resolve_lease_ws(args.lease)
    return str(args.ws)


@contextmanager
def _target_operation_lock(ws_url: str):
    lock_path = _target_operation_lock_path(ws_url)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def get_tab():
    data = json.loads(
        urllib.request.urlopen(f"{_cdp_base()}/json/list", timeout=8).read()
    )
    pages = [t for t in data if t.get("type") == "page"]
    for t in pages:
        if "coconala.com" in (t.get("url") or ""):
            return t["id"]
    if pages:
        return pages[0]["id"]
    raise RuntimeError(f"no page tab on {_cdp_base()}")


def _browser_ws_url():
    data = json.loads(
        urllib.request.urlopen(f"{_cdp_base()}/json/version", timeout=8).read()
    )
    return data["webSocketDebuggerUrl"]


@asynccontextmanager
async def hidden_page_target(url):
    """Own one authenticated default-context target without adding a browser window tab."""
    async with websockets.connect(
        _browser_ws_url(),
        ping_interval=None,
        open_timeout=10,
        max_size=40 * 1024 * 1024,
    ) as browser:
        opened = await _call(
            browser,
            "Target.createTarget",
            {"url": url, "hidden": True, "background": True},
            1,
        )
        if opened.get("error"):
            raise RuntimeError(f"hidden_target_create_failed:{opened['error']}")
        target_id = opened.get("result", {}).get("targetId")
        if not target_id:
            raise RuntimeError("hidden_target_create_missing_id")
        try:
            yield (
                f"ws://{urlparse(_cdp_base()).netloc}"
                f"/devtools/page/{target_id}"
            )
        finally:
            try:
                await _call(
                    browser,
                    "Target.closeTarget",
                    {"targetId": target_id},
                    2,
                )
            except Exception:
                pass


async def _connect():
    tab = get_tab()
    return await websockets.connect(
        f"ws://{urlparse(_cdp_base()).netloc}/devtools/page/{tab}",
        ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024,
    )


async def _call(ws, method, params, cid):
    await ws.send(json.dumps({"id": cid, "method": method, "params": params}))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=25)
        d = json.loads(raw)
        if d.get("id") == cid:
            return d


async def _wait_for_load(ws, deadline, start_cid):
    """Wait for Page.loadEventFired, falling back to a document.readyState poll if the event never
    arrives within the deadline (bounded — REQ-006 edge case: never hang indefinitely)."""
    cid = start_cid
    loop = asyncio.get_event_loop()
    while loop.time() < deadline:
        remaining = deadline - loop.time()
        if remaining <= 0:
            break
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=min(1.0, remaining))
        except asyncio.TimeoutError:
            continue
        try:
            d = json.loads(raw)
        except Exception:
            continue
        if d.get("method") == "Page.loadEventFired":
            return True, cid
    # fallback: poll document.readyState directly
    while loop.time() < deadline:
        r = await _call(ws, "Runtime.evaluate",
                         {"expression": "document.readyState", "returnByValue": True}, cid)
        cid += 1
        val = r.get("result", {}).get("result", {}).get("value")
        if val == "complete":
            return True, cid
        await asyncio.sleep(0.5)
    return False, cid


async def navigate_and_snapshot(pass_id, seq, label, url, action):
    outdir = os.path.expanduser(f"~/gig/trajectory/{pass_id}")
    os.makedirs(outdir, exist_ok=True)
    evidence_path = os.path.join(outdir, f"{seq}-{label}.json")
    final_url, title, navigated_ok = "", "", False
    rendered_text = ""

    async with hidden_page_target(url) as ws_url:
        async with websockets.connect(
            ws_url,
            ping_interval=None,
            open_timeout=10,
            max_size=40 * 1024 * 1024,
        ) as ws:
            cid = 1
            await _call(ws, "Page.enable", {}, cid); cid += 1
            await ws.send(json.dumps({"id": cid, "method": "Page.navigate", "params": {"url": url}}))
            cid += 1

            deadline = asyncio.get_event_loop().time() + LOAD_TIMEOUT_SECS
            navigated_ok, cid = await _wait_for_load(ws, deadline, cid)

            # page state (url + title) — evidence beyond the pixels, and proof navigation actually landed
            try:
                r = await _call(ws, "Runtime.evaluate",
                                 {"expression": "document.location.href+'|||'+document.title",
                                  "returnByValue": True}, cid); cid += 1
                v = r.get("result", {}).get("result", {}).get("value", "") or ""
                if "|||" in v:
                    final_url, title = v.split("|||", 1)
            except Exception:
                pass

            # Hidden targets intentionally have no compositor window, so Chrome never
            # answers Page.captureScreenshot for them. Persist the rendered DOM text
            # instead: it is the exact server/JS result the judge must compare, without
            # opening or navigating a user-visible tab.
            r = await _call(
                ws,
                "Runtime.evaluate",
                {
                    "expression": (
                        "document.body ? "
                        "document.body.innerText.slice(0,120000) : ''"
                    ),
                    "returnByValue": True,
                },
                cid,
            )
            rendered_text = (
                r.get("result", {}).get("result", {}).get("value", "")
                or ""
            )

    evidence = {
        "url": final_url,
        "requested_url": url,
        "title": title,
        "rendered_text": rendered_text,
        "navigated_ok": navigated_ok,
    }
    with open(evidence_path, "w", encoding="utf-8") as handle:
        json.dump(evidence, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")
    os.chmod(evidence_path, 0o600)

    row = {"ts": int(time.time()), "pass_id": str(pass_id), "seq": str(seq), "label": label,
           "requested_url": url, "url": final_url, "title": title, "action": action,
           "navigated_ok": navigated_ok, "evidence_kind": "rendered_dom_text",
           "artifact": evidence_path}
    with open(os.path.join(outdir, "trajectory.jsonl"), "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return evidence_path


async def probe_session(url: str) -> dict[str, object]:
    """Check authenticated routing in a hidden target without changing a visible tab."""
    final_url = ""
    async with hidden_page_target(url) as ws_url:
        async with websockets.connect(
            ws_url,
            ping_interval=None,
            open_timeout=10,
            max_size=40 * 1024 * 1024,
        ) as ws:
            cid = 1
            await _call(ws, "Page.enable", {}, cid)
            cid += 1
            await ws.send(json.dumps({
                "id": cid,
                "method": "Page.navigate",
                "params": {"url": url},
            }))
            cid += 1
            _, cid = await _wait_for_load(
                ws,
                asyncio.get_event_loop().time() + LOAD_TIMEOUT_SECS,
                cid,
            )
            result = await _call(
                ws,
                "Runtime.evaluate",
                {
                    "expression": "document.location.href",
                    "returnByValue": True,
                },
                cid,
            )
            final_url = (
                result.get("result", {}).get("result", {}).get("value", "")
                or ""
            )
    lowered = final_url.lower()
    logged_out = any(
        marker in lowered
        for marker in ("/login", "/signin", "/sign_in")
    )
    return {
        "ok": not logged_out,
        "logged_out": logged_out,
        "url": url,
        "final_url": final_url,
        "hidden": True,
    }


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def _is_public_marketplace_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc != "coconala.com":
        return False
    path = parsed.path.rstrip("/") or "/"
    return bool(
        re.fullmatch(r"/requests(?:/categories/\d+|/\d+)?", path)
        or re.fullmatch(
            rf"/job_matching/outsources(?:/{RETAINER_ULID_PATTERN.pattern})?",
            path,
        )
    )


PUBLIC_MARKETPLACE_SNAPSHOT_EXPRESSION = r"""
(() => {
  // gig_public_marketplace_snapshot_v1
  const clean = (value) => String(value || "").replace(/\s+/g, " ").trim();
  const current = new URL(document.location.href);
  const rows = [];
  const seen = new Set();
  const classify = (path) => {
    const single = path.match(/^\/requests\/(\d+)\/?$/);
    if (single) return {request_id: single[1], bucket: "single"};
    const retainer = path.match(
      /^\/job_matching\/outsources\/([0-9A-HJKMNP-TV-Z]{26})\/?$/
    );
    if (retainer) return {request_id: retainer[1], bucket: "retainer"};
    return null;
  };
  for (const anchor of Array.from(document.querySelectorAll("a[href]"))) {
    let linked;
    try {
      linked = new URL(anchor.getAttribute("href"), current);
    } catch (_) {
      continue;
    }
    if (linked.origin !== current.origin) continue;
    const identity = classify(linked.pathname);
    if (!identity || seen.has(identity.request_id)) continue;
    seen.add(identity.request_id);
    let container = anchor.closest(
      "article,li,[class*='card'],[class*='Card'],[class*='item'],[class*='Item']"
    );
    if (!container || !clean(container.innerText)) {
      let candidate = anchor;
      for (let depth = 0; depth < 8 && candidate; depth += 1) {
        const text = clean(candidate.innerText);
        if (text && text.length <= 5000) {
          container = candidate;
          break;
        }
        candidate = candidate.parentElement;
      }
    }
    container = container || anchor;
    const rawText = String(container.innerText || anchor.innerText || "");
    const summary = clean(rawText).slice(0, 1500);
    const heading = container.querySelector("h1,h2,h3,h4,[class*='title'],[class*='Title']");
    const firstUsefulLine = rawText
      .split(/\n+/)
      .map(clean)
      .find((line) => line.length >= 4 && line.length <= 300);
    const title = clean(
      (heading && heading.innerText) || anchor.innerText || firstUsefulLine || summary
    ).slice(0, 300);
    rows.push({
      request_id: identity.request_id,
      bucket: identity.bucket,
      url: linked.href,
      title,
      summary,
    });
    if (rows.length >= 50) break;
  }
  const detail = classify(current.pathname);
  const bodyText = clean(document.body && document.body.innerText).slice(0, 30000);
  if (detail && !seen.has(detail.request_id)) {
    const heading = document.querySelector("h1,h2,[class*='title'],[class*='Title']");
    rows.unshift({
      request_id: detail.request_id,
      bucket: detail.bucket,
      url: current.href,
      title: clean((heading && heading.innerText) || document.title).slice(0, 300),
      summary: bodyText.slice(0, 1500),
    });
  }
  const currentPage = Number(current.searchParams.get("page") || "1");
  const hasNext = Array.from(document.querySelectorAll("a[href]")).some((anchor) => {
    const label = clean(
      anchor.getAttribute("aria-label") || anchor.getAttribute("rel") || anchor.innerText
    ).toLowerCase();
    const disabled = anchor.getAttribute("aria-disabled") === "true"
      || anchor.classList.contains("disabled")
      || anchor.classList.contains("is-disabled");
    let linkedPage = 0;
    try {
      const linked = new URL(anchor.getAttribute("href"), current);
      if (linked.pathname === current.pathname) {
        linkedPage = Number(linked.searchParams.get("page") || "0");
      }
    } catch (_) {
      linkedPage = 0;
    }
    return !disabled && (
      label === "next" || label.includes("次へ") || label === "次"
      || anchor.getAttribute("rel") === "next" || linkedPage > currentPage
    );
  });
  return JSON.stringify({
    url: current.href,
    title: document.title,
    public_marketplace: true,
    public_text: bodyText,
    opportunities: rows.slice(0, 50),
    has_next: hasNext,
  });
})()
"""


async def observe_target(
    ws_url: str,
    url: str,
    screenshot_path: Path,
    live_dom_path: Path,
) -> dict[str, object]:
    """Serialize navigation against irreversible work on this leased target."""
    with _target_operation_lock(ws_url):
        return await _observe_target_locked(
            ws_url,
            url,
            screenshot_path,
            live_dom_path,
        )


async def _observe_target_locked(
    ws_url: str,
    url: str,
    screenshot_path: Path,
    live_dom_path: Path,
) -> dict[str, object]:
    """Navigate one already-leased page target and emit bounded exact-route evidence."""
    async with websockets.connect(
        ws_url,
        ping_interval=None,
        open_timeout=10,
        max_size=40 * 1024 * 1024,
    ) as ws:
        cid = 1
        await _call(ws, "Page.enable", {}, cid)
        cid += 1
        await ws.send(json.dumps({"id": cid, "method": "Page.navigate", "params": {"url": url}}))
        cid += 1
        loaded, cid = await _wait_for_load(
            ws,
            asyncio.get_event_loop().time() + LOAD_TIMEOUT_SECS,
            cid,
        )
        if not loaded:
            raise RuntimeError("navigation_timeout")
        public_marketplace = _is_public_marketplace_url(url)
        expression = (
            PUBLIC_MARKETPLACE_SNAPSHOT_EXPRESSION
            if public_marketplace
            else "document.location.href+'|||'+document.title"
        )
        state = await _call(
            ws,
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
            cid,
        )
        cid += 1
        value = state.get("result", {}).get("result", {}).get("value", "") or ""
        public_snapshot: dict[str, object] | None = None
        if public_marketplace:
            try:
                decoded = json.loads(value)
            except (TypeError, json.JSONDecodeError) as exc:
                raise RuntimeError("public_marketplace_snapshot_invalid") from exc
            if not isinstance(decoded, dict):
                raise RuntimeError("public_marketplace_snapshot_invalid")
            public_snapshot = decoded
            final_url = str(decoded.get("url") or "")
            title = str(decoded.get("title") or "")
        else:
            final_url, separator, title = value.partition("|||")
            if not separator:
                raise RuntimeError(f"navigation_url_mismatch:{final_url}")
        if final_url != url:
            raise RuntimeError(f"navigation_url_mismatch:{final_url}")
        shot = await _call(ws, "Page.captureScreenshot", {"format": "png"}, cid)
        screenshot_data = shot.get("result", {}).get("data")
        if not screenshot_data:
            raise RuntimeError("no_screenshot_data")

    live_dom = {
        "url": final_url,
        "not_found": False,
        "observed": True,
        "title": title,
    }
    if public_snapshot is not None:
        opportunities = public_snapshot.get("opportunities")
        live_dom.update({
            "public_marketplace": True,
            "public_text": str(public_snapshot.get("public_text") or "")[:30000],
            "opportunities": (
                opportunities[:50] if isinstance(opportunities, list) else []
            ),
            "has_next": bool(public_snapshot.get("has_next")),
        })
    _atomic_write(screenshot_path, base64.b64decode(screenshot_data))
    _atomic_write(
        live_dom_path,
        (json.dumps(live_dom, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"),
    )
    return live_dom


async def open_application_form(
    ws_url: str,
    request_id: str,
    screenshot_path: Path,
    evidence_path: Path,
) -> dict[str, object]:
    """Open Coconala's canonical application route and verify the real form controls."""
    request_id = str(request_id).strip()
    if not request_id.isdigit():
        raise ValueError("request_id_must_be_digits")
    expected_url = f"https://coconala.com/offers/add/{request_id}"
    async with websockets.connect(
        ws_url,
        ping_interval=None,
        open_timeout=10,
        max_size=40 * 1024 * 1024,
    ) as ws:
        cid = 1
        await _call(ws, "Page.enable", {}, cid)
        cid += 1
        await ws.send(json.dumps({
            "id": cid,
            "method": "Page.navigate",
            "params": {"url": expected_url},
        }))
        cid += 1
        loaded, cid = await _wait_for_load(
            ws,
            asyncio.get_event_loop().time() + LOAD_TIMEOUT_SECS,
            cid,
        )
        if not loaded:
            raise RuntimeError("application_form_navigation_timeout")
        state = await _call(
            ws,
            "Runtime.evaluate",
            {
                "expression": (
                    "JSON.stringify({"
                    "url:document.location.href,"
                    "title:document.title,"
                    "has_content:!!document.querySelector("
                    "'textarea[name=\"data[Offer][content]\"]'),"
                    "has_price:!!document.querySelector("
                    "'input[name=\"data[Offer][price]\"]'),"
                    "has_expire_date:!!document.querySelector("
                    "'input[name=\"data[Offer][expire_date]\"]'),"
                    "has_confirm:[...document.querySelectorAll('button')].some("
                    "button=>button.innerText.trim()==='確認する')"
                    "})"
                ),
                "returnByValue": True,
            },
            cid,
        )
        cid += 1
        raw_state = (
            state.get("result", {}).get("result", {}).get("value", "")
            or ""
        )
        try:
            form_state = json.loads(raw_state)
        except (TypeError, json.JSONDecodeError) as error:
            raise RuntimeError("application_form_state_invalid") from error
        if form_state.get("url") != expected_url:
            raise RuntimeError(
                f"application_form_url_mismatch:{form_state.get('url', '')}"
            )
        field_state = {
            "content": form_state.get("has_content") is True,
            "price": form_state.get("has_price") is True,
            "expire_date": form_state.get("has_expire_date") is True,
            "confirm": form_state.get("has_confirm") is True,
        }
        form_verified = (
            str(form_state.get("title", "")).startswith("応募する")
            and all(field_state.values())
        )
        if not form_verified:
            raise RuntimeError("application_form_controls_missing")
        shot = await _call(ws, "Page.captureScreenshot", {"format": "png"}, cid)
        screenshot_data = shot.get("result", {}).get("data")
        if not screenshot_data:
            raise RuntimeError("application_form_screenshot_missing")

    evidence = {
        "request_id": request_id,
        "url": expected_url,
        "title": form_state["title"],
        "form_verified": True,
        "fields": field_state,
    }
    _atomic_write(screenshot_path, base64.b64decode(screenshot_data))
    _atomic_write(
        evidence_path,
        (
            json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
            + "\n"
        ).encode("utf-8"),
    )
    return evidence


async def open_retainer_application_form(
    ws_url: str,
    outsource_ulid: str,
    screenshot_path: Path,
    evidence_path: Path,
) -> dict[str, object]:
    """Open and verify the distinct Coconala retainer application form."""
    outsource_ulid = str(outsource_ulid).strip()
    if RETAINER_ULID_PATTERN.fullmatch(outsource_ulid) is None:
        raise ValueError("outsource_ulid_invalid")
    expected_url = (
        "https://coconala.com/job_matching/outsources/"
        f"{outsource_ulid}/apply"
    )
    async with websockets.connect(
        ws_url,
        ping_interval=None,
        open_timeout=10,
        max_size=40 * 1024 * 1024,
    ) as ws:
        cid = 1
        await _call(ws, "Page.enable", {}, cid)
        cid += 1
        await ws.send(json.dumps({
            "id": cid,
            "method": "Page.navigate",
            "params": {"url": expected_url},
        }))
        cid += 1
        loaded, cid = await _wait_for_load(
            ws,
            asyncio.get_event_loop().time() + LOAD_TIMEOUT_SECS,
            cid,
        )
        if not loaded:
            raise RuntimeError("retainer_application_form_navigation_timeout")
        state = await _call(
            ws,
            "Runtime.evaluate",
            {
                "expression": (
                    "JSON.stringify({"
                    "url:document.location.href,"
                    "title:document.title,"
                    "has_compensation:!!document.querySelector("
                    "'input[name=\"desiredCompensation\"]'),"
                    "has_working_days:!!document.querySelector('select'),"
                    "has_hours_start:!!document.querySelector("
                    "'input[name=\"weeklyWorkingHoursStart\"]'),"
                    "has_hours_end:!!document.querySelector("
                    "'input[name=\"weeklyWorkingHoursEnd\"]'),"
                    "has_message:!!document.querySelector('textarea'),"
                    "has_confirm:[...document.querySelectorAll('button')].some("
                    "button=>(button.innerText||'').trim()==='確認画面に進む')"
                    "})"
                ),
                "returnByValue": True,
            },
            cid,
        )
        cid += 1
        raw_state = (
            state.get("result", {}).get("result", {}).get("value", "")
            or ""
        )
        try:
            form_state = json.loads(raw_state)
        except (TypeError, json.JSONDecodeError) as error:
            raise RuntimeError("retainer_application_form_state_invalid") from error
        if form_state.get("url") != expected_url:
            raise RuntimeError(
                "retainer_application_form_url_mismatch:"
                f"{form_state.get('url', '')}"
            )
        field_state = {
            "compensation": form_state.get("has_compensation") is True,
            "working_days": form_state.get("has_working_days") is True,
            "hours_start": form_state.get("has_hours_start") is True,
            "hours_end": form_state.get("has_hours_end") is True,
            "message": form_state.get("has_message") is True,
            "confirm": form_state.get("has_confirm") is True,
        }
        if not all(field_state.values()):
            raise RuntimeError("retainer_application_form_controls_missing")
        shot = await _call(ws, "Page.captureScreenshot", {"format": "png"}, cid)
        screenshot_data = shot.get("result", {}).get("data")
        if not screenshot_data:
            raise RuntimeError("retainer_application_form_screenshot_missing")

    evidence = {
        "request_id": outsource_ulid,
        "bucket": "retainer",
        "url": expected_url,
        "title": form_state["title"],
        "form_verified": True,
        "fields": field_state,
    }
    _atomic_write(screenshot_path, base64.b64decode(screenshot_data))
    _atomic_write(
        evidence_path,
        (
            json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
            + "\n"
        ).encode("utf-8"),
    )
    return evidence


async def _mouse_click(ws, x: float, y: float, cid: int) -> int:
    for event_type, button, click_count in (
        ("mouseMoved", "none", 0),
        ("mousePressed", "left", 1),
        ("mouseReleased", "left", 1),
    ):
        await _call(
            ws,
            "Input.dispatchMouseEvent",
            {
                "type": event_type,
                "x": x,
                "y": y,
                "button": button,
                "clickCount": click_count,
            },
            cid,
        )
        cid += 1
    return cid


def _submit_intent_path(evidence_path: Path) -> Path:
    return evidence_path.with_suffix(".intent.json")


def _eligibility_evidence_path(evidence_path: Path) -> Path:
    return evidence_path.with_suffix(".eligibility.json")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_eligibility_evidence(
    evidence_path: Path,
    *,
    request_id: str,
    bucket: str,
    opportunity_url: str,
    brief_text: str,
    proposal_text: str,
    verdict: dict[str, object],
) -> None:
    payload = {
        **verdict,
        "request_id": request_id,
        "bucket": bucket,
        "opportunity_url": opportunity_url,
        "brief_sha256": _sha256_text(brief_text),
        "proposal_sha256": _sha256_text(proposal_text),
    }
    _atomic_write(
        _eligibility_evidence_path(evidence_path),
        (
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            + "\n"
        ).encode("utf-8"),
    )


async def _load_opportunity_brief(opportunity_url: str) -> str:
    """Read an authenticated brief in a separate owned target."""
    async with hidden_page_target(opportunity_url) as brief_ws_url:
        async with websockets.connect(
            brief_ws_url,
            ping_interval=None,
            open_timeout=10,
            max_size=40 * 1024 * 1024,
        ) as ws:
            cid = 1
            await _call(ws, "Page.enable", {}, cid)
            cid += 1
            loaded, cid = await _wait_for_load(
                ws,
                asyncio.get_event_loop().time() + LOAD_TIMEOUT_SECS,
                cid,
            )
            if not loaded:
                raise RuntimeError("opportunity_brief_navigation_timeout")
            state = await _call(
                ws,
                "Runtime.evaluate",
                {
                    "expression": (
                        "JSON.stringify({url:location.href,"
                        "text:document.body?.innerText||''})"
                    ),
                    "returnByValue": True,
                },
                cid,
            )
    raw = state.get("result", {}).get("result", {}).get("value", "") or ""
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("opportunity_brief_state_invalid") from error
    if (
        not isinstance(parsed, dict)
        or parsed.get("url") != opportunity_url
        or not str(parsed.get("text") or "").strip()
    ):
        raise RuntimeError("opportunity_brief_unavailable")
    return str(parsed["text"])


def _write_submit_intent(
    evidence_path: Path,
    *,
    request_id: str,
    bucket: str,
    url: str,
    title: str | None,
    state: str,
) -> None:
    """Persist the mutation identity before a click whose ACK may be lost."""
    payload = {
        "request_id": request_id,
        "bucket": bucket,
        "url": url,
        "title": str(title).strip() if title else None,
        "state": state,
    }
    _atomic_write(
        _submit_intent_path(evidence_path),
        (
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            + "\n"
        ).encode("utf-8"),
    )


async def _application_submit_state(ws, cid: int) -> tuple[dict[str, object], int]:
    state = await _call(
        ws,
        "Runtime.evaluate",
        {
            "expression": (
                "/* application_submit_state_v1 */"
                "JSON.stringify((()=>{"
                "const body=document.body?.innerText||'';"
                "const visible=e=>{if(!e||e.offsetParent===null)return false;"
                "const r=e.getBoundingClientRect();return r.width>0&&r.height>0;};"
                "const buttons=[...document.querySelectorAll('button')];"
                "const modalApply=buttons.find(b=>visible(b)&&!b.disabled&&"
                "(b.innerText||'').trim()==='応募する'&&"
                "b.classList.contains('js_ignite-submit'));"
                "const confirmCandidate=document.querySelector("
                + json.dumps(APPLICATION_CONFIRM_SELECTOR)
                + ");"
                "const confirm=visible(confirmCandidate)&&"
                "(confirmCandidate.innerText||'').trim()==='確認する'"
                "?confirmCandidate:null;"
                "const apply=buttons.find(b=>visible(b)&&!b.disabled&&"
                "(b.innerText||'').trim()==='応募する');"
                "let button=modalApply||confirm||apply||null;"
                "let buttonState=null;"
                "if(button){button.scrollIntoView({block:'center'});"
                "const r=button.getBoundingClientRect();"
                "buttonState={kind:button===modalApply?'modal_apply':"
                "button===confirm?'confirm':'apply',"
                "x:r.left+r.width/2,y:r.top+r.height/2};}"
                "const content=document.querySelector("
                "'textarea[name=\"data[Offer][content]\"]');"
                "const price=document.querySelector("
                "'input[name=\"data[Offer][price]\"]');"
                "const date=document.querySelector("
                "'input[name=\"data[Offer][expire_date]\"]');"
                "const success=location.pathname.startsWith("
                "'/mypage/job_matching/applied/offers')&&"
                "body.includes('応募しました');"
                "return {url:location.href,title:document.title,"
                "body:body.slice(-4000),"
                "proposal_text:content?.value||'',"
                "form_filled:!!(content?.value.trim()&&price?.value.trim()&&"
                "date?.value.trim()),"
                "validation_error:body.includes('入力情報を確認して下さい')||"
                "body.includes('入力内容をご確認'),"
                "success,button:buttonState};})())"
            ),
            "returnByValue": True,
        },
        cid,
    )
    cid += 1
    raw = state.get("result", {}).get("result", {}).get("value", "") or ""
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("application_submit_state_invalid") from error
    if not isinstance(parsed, dict):
        raise RuntimeError("application_submit_state_invalid")
    return parsed, cid


async def _retainer_application_submit_state(
    ws, cid: int
) -> tuple[dict[str, object], int]:
    state = await _call(
        ws,
        "Runtime.evaluate",
        {
            "expression": (
                "/* retainer_application_submit_state_v1 */"
                "JSON.stringify((()=>{"
                "const body=document.body?.innerText||'';"
                "const visible=e=>{if(!e||e.offsetParent===null)return false;"
                "const r=e.getBoundingClientRect();return r.width>0&&r.height>0;};"
                "const buttons=[...document.querySelectorAll('button')];"
                "const confirmCandidates=buttons.filter(b=>visible(b)&&"
                "(b.innerText||'').trim()==='確認画面に進む');"
                "const generated_message_confirmation="
                "body.includes('応募メッセージの確認')&&"
                "body.includes('確認画面に進んでもよろしいですか？');"
                "const confirm=generated_message_confirmation"
                "?confirmCandidates.at(-1):confirmCandidates[0];"
                "const apply=buttons.find(b=>visible(b)&&!b.disabled&&"
                "(b.innerText||'').trim()==='応募する');"
                "const checkbox=document.querySelector("
                "'input[type=\"checkbox\"]:not(:checked),"
                "[role=\"checkbox\"][aria-checked=\"false\"]');"
                "const consentCandidate=checkbox?.closest('label')||checkbox;"
                "const consent=visible(consentCandidate)?consentCandidate:null;"
                "const onConfirm=body.includes('応募内容を確認する')||"
                "body.includes('登録済みの氏名と非公開情報');"
                "let button=onConfirm?(consent||apply):confirm;"
                "let buttonState=null;"
                "if(button){button.scrollIntoView({block:'center'});"
                "const r=button.getBoundingClientRect();"
                "buttonState={kind:button===confirm?"
                "(generated_message_confirmation?"
                "'generated_message_confirm':'confirm'):"
                "button===consent?'consent':'apply',"
                "x:r.left+r.width/2,y:r.top+r.height/2};}"
                "const compensation=document.querySelector("
                "'input[name=\"desiredCompensation\"]');"
                "const workingDays=document.querySelector('select');"
                "const hoursStart=document.querySelector("
                "'input[name=\"weeklyWorkingHoursStart\"]');"
                "const hoursEnd=document.querySelector("
                "'input[name=\"weeklyWorkingHoursEnd\"]');"
                "const message=document.querySelector('textarea');"
                "const success=location.pathname.startsWith("
                "'/mypage/job_matching/applied/outsource_applications');"
                "const completion_modal="
                "body.includes('応募が完了しました！')&&"
                "body.includes('ご応募ありがとうございます。');"
                "return {url:location.href,title:document.title,"
                "body:body.slice(-8000),"
                "proposal_text:message?.value||'',"
                "form_filled:!!(compensation?.value.trim()&&"
                "workingDays?.value&&hoursStart?.value.trim()&&"
                "hoursEnd?.value.trim()&&message?.value.trim()),"
                "validation_error:body.includes('入力内容をご確認'),"
                "success,completion_modal,button:buttonState};})())"
            ),
            "returnByValue": True,
        },
        cid,
    )
    cid += 1
    raw = state.get("result", {}).get("result", {}).get("value", "") or ""
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("retainer_application_submit_state_invalid") from error
    if not isinstance(parsed, dict):
        raise RuntimeError("retainer_application_submit_state_invalid")
    return parsed, cid


async def _submit_application_locked(
    ws_url: str,
    request_id: str,
    screenshot_path: Path,
    evidence_path: Path,
    *,
    wait_seconds: float = 2.5,
    opportunity_brief: str | None = None,
) -> dict[str, object]:
    """Finish both confirmation stages and create proof only after applied-page success."""
    request_id = str(request_id).strip()
    if not request_id.isdigit():
        raise ValueError("request_id_must_be_digits")
    expected_form_url = f"https://coconala.com/offers/add/{request_id}"
    opportunity_url = f"https://coconala.com/requests/{request_id}"
    applied_url_prefix = "https://coconala.com/mypage/job_matching/applied/offers"
    final_state: dict[str, object] | None = None
    if opportunity_brief is None:
        opportunity_brief = await _load_opportunity_brief(opportunity_url)
    policy_checked = False

    for _ in range(7):
        async with websockets.connect(
            ws_url,
            ping_interval=None,
            open_timeout=10,
            max_size=40 * 1024 * 1024,
        ) as ws:
            cid = 1
            await _call(ws, "Page.enable", {}, cid)
            cid += 1
            state, cid = await _application_submit_state(ws, cid)
            current_url = str(state.get("url") or "")
            if current_url != expected_form_url and not current_url.startswith(
                applied_url_prefix
            ):
                raise RuntimeError(f"application_submit_url_mismatch:{current_url}")
            if state.get("success") is True:
                shot = await _call(
                    ws, "Page.captureScreenshot", {"format": "png"}, cid
                )
                screenshot_data = shot.get("result", {}).get("data")
                if not screenshot_data:
                    raise RuntimeError("application_submit_screenshot_missing")
                final_state = state
                break
            if not policy_checked:
                proposal_text = str(state.get("proposal_text") or "")
                verdict = evaluate_application(
                    opportunity_brief,
                    proposal_text,
                    form_text=str(state.get("body") or ""),
                )
                _write_eligibility_evidence(
                    evidence_path,
                    request_id=request_id,
                    bucket="single",
                    opportunity_url=opportunity_url,
                    brief_text=opportunity_brief,
                    proposal_text=proposal_text,
                    verdict=verdict,
                )
                policy_checked = True
                if verdict.get("allowed") is not True:
                    reasons = verdict.get("reason_codes")
                    reason = (
                        ",".join(str(item) for item in reasons)
                        if isinstance(reasons, list)
                        else "unknown"
                    )
                    raise RuntimeError(
                        f"application_eligibility_rejected:{reason}"
                    )
            if state.get("validation_error") is True:
                raise RuntimeError("application_form_validation_failed")
            button = state.get("button")
            if not isinstance(button, dict):
                break
            if button.get("kind") == "confirm" and state.get("form_filled") is not True:
                raise RuntimeError("application_form_incomplete")
            try:
                x = float(button["x"])
                y = float(button["y"])
            except (KeyError, TypeError, ValueError) as error:
                raise RuntimeError("application_submit_button_invalid") from error
            if button.get("kind") in {"apply", "modal_apply"}:
                _write_submit_intent(
                    evidence_path,
                    request_id=request_id,
                    bucket="single",
                    url=f"https://coconala.com/requests/{request_id}",
                    title=None,
                    state="prepared",
                )
            await _mouse_click(ws, x, y, cid)
        if wait_seconds:
            await asyncio.sleep(wait_seconds)

    if final_state is None:
        raise RuntimeError("submission_not_verified")
    evidence = {
        "request_id": request_id,
        "url": str(final_state["url"]),
        "title": str(final_state.get("title") or ""),
        "submit_verified": True,
        "applied_page_verified": True,
        "confirmation_text": "応募しました",
    }
    _atomic_write(screenshot_path, base64.b64decode(screenshot_data))
    _atomic_write(
        evidence_path,
        (
            json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
            + "\n"
        ).encode("utf-8"),
    )
    _write_submit_intent(
        evidence_path,
        request_id=request_id,
        bucket="single",
        url=f"https://coconala.com/requests/{request_id}",
        title=None,
        state="confirmed",
    )
    return evidence


async def submit_application(
    ws_url: str,
    request_id: str,
    screenshot_path: Path,
    evidence_path: Path,
    *,
    wait_seconds: float = 2.5,
    opportunity_brief: str | None = None,
) -> dict[str, object]:
    """Serialize a submit against context release for this leased target."""
    with _target_operation_lock(ws_url):
        return await _submit_application_locked(
            ws_url,
            request_id,
            screenshot_path,
            evidence_path,
            wait_seconds=wait_seconds,
            opportunity_brief=opportunity_brief,
        )


async def _submit_retainer_application_locked(
    ws_url: str,
    outsource_ulid: str,
    screenshot_path: Path,
    evidence_path: Path,
    *,
    listing_title: str | None = None,
    wait_seconds: float = 2.5,
    opportunity_brief: str | None = None,
) -> dict[str, object]:
    """Submit a retainer application and prove the canonical applied-list redirect."""
    outsource_ulid = str(outsource_ulid).strip()
    if RETAINER_ULID_PATTERN.fullmatch(outsource_ulid) is None:
        raise ValueError("outsource_ulid_invalid")
    expected_form_url = (
        "https://coconala.com/job_matching/outsources/"
        f"{outsource_ulid}/apply"
    )
    opportunity_url = (
        "https://coconala.com/job_matching/outsources/"
        f"{outsource_ulid}"
    )
    applied_url_prefix = (
        "https://coconala.com/mypage/job_matching/applied/"
        "outsource_applications"
    )
    final_state: dict[str, object] | None = None
    completion_modal_verified = False
    if opportunity_brief is None:
        opportunity_brief = await _load_opportunity_brief(opportunity_url)
    policy_checked = False

    for _ in range(7):
        async with websockets.connect(
            ws_url,
            ping_interval=None,
            open_timeout=10,
            max_size=40 * 1024 * 1024,
        ) as ws:
            cid = 1
            await _call(ws, "Page.enable", {}, cid)
            cid += 1
            state, cid = await _retainer_application_submit_state(ws, cid)
            current_url = str(state.get("url") or "")
            if current_url != expected_form_url and not current_url.startswith(
                applied_url_prefix
            ):
                raise RuntimeError(
                    f"retainer_application_submit_url_mismatch:{current_url}"
                )
            if state.get("success") is True:
                shot = await _call(
                    ws, "Page.captureScreenshot", {"format": "png"}, cid
                )
                screenshot_data = shot.get("result", {}).get("data")
                if not screenshot_data:
                    raise RuntimeError(
                        "retainer_application_submit_screenshot_missing"
                    )
                final_state = state
                break
            if not policy_checked:
                proposal_text = str(state.get("proposal_text") or "")
                verdict = evaluate_application(
                    opportunity_brief,
                    proposal_text,
                    form_text=str(state.get("body") or ""),
                )
                _write_eligibility_evidence(
                    evidence_path,
                    request_id=outsource_ulid,
                    bucket="retainer",
                    opportunity_url=opportunity_url,
                    brief_text=opportunity_brief,
                    proposal_text=proposal_text,
                    verdict=verdict,
                )
                policy_checked = True
                if verdict.get("allowed") is not True:
                    reasons = verdict.get("reason_codes")
                    reason = (
                        ",".join(str(item) for item in reasons)
                        if isinstance(reasons, list)
                        else "unknown"
                    )
                    raise RuntimeError(
                        f"application_eligibility_rejected:{reason}"
                    )
            if state.get("completion_modal") is True:
                completion_modal_verified = True
                await ws.send(json.dumps({
                    "id": cid,
                    "method": "Page.navigate",
                    "params": {"url": applied_url_prefix},
                }))
                cid += 1
                loaded, cid = await _wait_for_load(
                    ws,
                    asyncio.get_event_loop().time() + LOAD_TIMEOUT_SECS,
                    cid,
                )
                if not loaded:
                    raise RuntimeError(
                        "retainer_applied_page_navigation_timeout"
                    )
                continue
            if state.get("validation_error") is True:
                raise RuntimeError("retainer_application_form_validation_failed")
            button = state.get("button")
            if not isinstance(button, dict):
                break
            if (
                button.get("kind") in {"confirm", "generated_message_confirm"}
                and state.get("form_filled") is not True
            ):
                raise RuntimeError("retainer_application_form_incomplete")
            try:
                x = float(button["x"])
                y = float(button["y"])
            except (KeyError, TypeError, ValueError) as error:
                raise RuntimeError(
                    "retainer_application_submit_button_invalid"
                ) from error
            if button.get("kind") == "apply":
                _write_submit_intent(
                    evidence_path,
                    request_id=outsource_ulid,
                    bucket="retainer",
                    url=(
                        "https://coconala.com/job_matching/outsources/"
                        f"{outsource_ulid}"
                    ),
                    title=listing_title,
                    state="prepared",
                )
            await _mouse_click(ws, x, y, cid)
        if wait_seconds:
            await asyncio.sleep(wait_seconds)

    if final_state is None:
        raise RuntimeError("retainer_submission_not_verified")
    evidence = {
        "request_id": outsource_ulid,
        "bucket": "retainer",
        "url": str(final_state["url"]),
        "title": str(final_state.get("title") or ""),
        "submit_verified": True,
        "applied_page_verified": True,
        "confirmation_text": (
            "応募が完了しました！"
            if completion_modal_verified
            else "応募履歴へ遷移"
        ),
    }
    _atomic_write(screenshot_path, base64.b64decode(screenshot_data))
    _atomic_write(
        evidence_path,
        (
            json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
            + "\n"
        ).encode("utf-8"),
    )
    _write_submit_intent(
        evidence_path,
        request_id=outsource_ulid,
        bucket="retainer",
        url=(
            "https://coconala.com/job_matching/outsources/"
            f"{outsource_ulid}"
        ),
        title=listing_title,
        state="confirmed",
    )
    return evidence


async def submit_retainer_application(
    ws_url: str,
    outsource_ulid: str,
    screenshot_path: Path,
    evidence_path: Path,
    *,
    listing_title: str | None = None,
    wait_seconds: float = 2.5,
    opportunity_brief: str | None = None,
) -> dict[str, object]:
    """Serialize a retainer submit against context release for this target."""
    with _target_operation_lock(ws_url):
        return await _submit_retainer_application_locked(
            ws_url,
            outsource_ulid,
            screenshot_path,
            evidence_path,
            listing_title=listing_title,
            wait_seconds=wait_seconds,
            opportunity_brief=opportunity_brief,
        )


def _open_application_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    _add_connection_arguments(parser)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--screenshot", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        ws_url = _connection_ws(args)
        result = asyncio.run(open_application_form(
            ws_url,
            args.request_id,
            args.screenshot,
            args.evidence,
        ))
    except Exception as error:
        print(json.dumps({
            "ok": False,
            "error": f"{type(error).__name__}:{error}",
        }, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, separators=(",", ":")))
    return 0


def _submit_application_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    _add_connection_arguments(parser)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--screenshot", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        ws_url = _connection_ws(args)
        result = asyncio.run(submit_application(
            ws_url,
            args.request_id,
            args.screenshot,
            args.evidence,
        ))
    except Exception as error:
        print(json.dumps({
            "ok": False,
            "error": f"{type(error).__name__}:{error}",
        }, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, separators=(",", ":")))
    return 0


def _open_retainer_application_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    _add_connection_arguments(parser)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--screenshot", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        ws_url = _connection_ws(args)
        result = asyncio.run(open_retainer_application_form(
            ws_url,
            args.request_id,
            args.screenshot,
            args.evidence,
        ))
    except Exception as error:
        print(json.dumps({
            "ok": False,
            "error": f"{type(error).__name__}:{error}",
        }, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, separators=(",", ":")))
    return 0


def _submit_retainer_application_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    _add_connection_arguments(parser)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--screenshot", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--listing-title")
    args = parser.parse_args(argv)
    try:
        ws_url = _connection_ws(args)
        result = asyncio.run(submit_retainer_application(
            ws_url,
            args.request_id,
            args.screenshot,
            args.evidence,
            listing_title=args.listing_title,
        ))
    except Exception as error:
        print(json.dumps({
            "ok": False,
            "error": f"{type(error).__name__}:{error}",
        }, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, separators=(",", ":")))
    return 0


def _observe_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    _add_connection_arguments(parser)
    parser.add_argument("--url", required=True)
    parser.add_argument("--screenshot", required=True, type=Path)
    parser.add_argument("--dom", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        ws_url = _connection_ws(args)
        result = asyncio.run(observe_target(
            ws_url,
            args.url,
            args.screenshot,
            args.dom,
        ))
    except Exception as error:
        print(json.dumps({
            "ok": False,
            "error": f"{type(error).__name__}:{error}",
        }, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, separators=(",", ":")))
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "open-application":
        return _open_application_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "submit-application":
        return _submit_application_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "open-retainer-application":
        return _open_retainer_application_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "submit-retainer-application":
        return _submit_retainer_application_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "probe-session":
        parser = argparse.ArgumentParser()
        parser.add_argument("--url", required=True)
        args = parser.parse_args(sys.argv[2:])
        try:
            print(json.dumps(
                asyncio.run(probe_session(args.url)),
                ensure_ascii=False,
                separators=(",", ":"),
            ))
        except Exception as error:
            print(json.dumps({
                "ok": False,
                "logged_out": False,
                "error": f"{type(error).__name__}:{error}",
            }, ensure_ascii=False, separators=(",", ":")))
            return 1
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "observe":
        return _observe_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] in {"-h", "--help"}:
        print(
            "usage: cdp_nav_snapshot.py "
            "{open-application,submit-application,open-retainer-application,"
            "submit-retainer-application,observe,probe-session} [options]\n"
            "       cdp_nav_snapshot.py "
            "<pass_id> <seq> <label> <url> [action_note]\n\n"
            "commands:\n"
            "  open-application  open and verify the canonical Coconala form\n"
            "  submit-application finish both submit stages and verify applied history\n"
            "  open-retainer-application  open and verify the retainer form\n"
            "  submit-retainer-application submit and verify retainer applied history\n"
            "  observe           navigate one leased target and capture evidence\n"
            "  probe-session     verify an authenticated session in a hidden target"
        )
        return 0
    if len(sys.argv) < 5:
        print("ERROR:usage: cdp_nav_snapshot.py <pass_id> <seq> <label> <url> [action_note]")
        return 0
    pass_id, seq, label, url = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    action = sys.argv[5] if len(sys.argv) > 5 else ""
    try:
        print(asyncio.run(navigate_and_snapshot(pass_id, seq, label, url, action)))
    except Exception as e:
        # capture must never abort a verification run
        print(f"ERROR:{type(e).__name__}:{e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
