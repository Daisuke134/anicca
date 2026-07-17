# Login-Once Hardening (#12) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the already-implemented v24 golden-session machinery so the instagrapi session stays alive between posts and bloks poisoning is never masked — completing #12 without rewriting what already works.

**Architecture:** `instagrapi_post.py` already implements v24 points 1/3/4 (tier1 session reuse, relogin refusal, bloks→mark_poisoned, tier3 cooldown) and defines `keepalive()`/`gentle_ping()` — but nothing ever calls them. We add: (a) ChallengeRequired must propagate out of the two probe functions (today `except Exception: return True` swallows the poison signal), (b) a `--keepalive` CLI mode that probes the golden session read-only and persists refreshed cookies, (c) tier1 success persists refreshed settings, (d) `session_vault_tick.sh` (launchd `ai.anicca.session-vault`, every 1800s) runs the keepalive for `session_owner=instagrapi` accounts it currently skips entirely.

**Tech Stack:** Python 3 (instagrapi), bash, pytest, jq. Repo: `~/anicca`, worktree `/Users/anicca/anicca/.worktrees/login-once-hardening`, branch `feature/login-once-hardening`.

**Copy source (spec v24, `docs/earn/ig-4account-reels-carousel-loop-plan.md` in anicca-project):** alsk1992/instagram-ai-agent `plugins/ig.py` L1142-1250 (two-stage keepalive), L556-708 (gold-standard set_settings persistence).

**Working directory for ALL tasks:** `/Users/anicca/anicca/.worktrees/login-once-hardening`

**Test command (run from worktree root):** `python3 -m pytest skills/earn/clip/tests/ -q`

**Style constraint:** Before writing any test, read `skills/earn/clip/tests/test_login_resilient.py` and mirror its existing fixture/mock style (it already fakes the instagrapi Client). The code blocks below are the required behavior and assertions; adapt mock construction to the existing style, keep function/flag names exactly as written.

**Never** print/log secret values (pw, sessionid, cookies). Never call the real Instagram API from tests.

---

### Task 1: ChallengeRequired must propagate out of keepalive() and gentle_ping()

**Files:**
- Modify: `skills/earn/clip/scripts/instagrapi_post.py` (functions `keepalive` ~L121, `gentle_ping` ~L135)
- Test: `skills/earn/clip/tests/test_login_resilient.py` (append)

**Why:** bloks ChallengeRequired = account poisoned. Today both probes catch bare `Exception` and return `True`, so a poison signal during a probe reads as "alive". The caller (Task 2's `keepalive_main`) must see it to `mark_poisoned`.

- [ ] **Step 1: Write the failing tests** (append to `test_login_resilient.py`, reusing its existing fake-client style):

```python
def test_keepalive_reraises_challenge_required():
    from instagrapi.exceptions import ChallengeRequired
    cl = mock.Mock()
    cl.get_timeline_feed.side_effect = ChallengeRequired()
    with pytest.raises(ChallengeRequired):
        ip.keepalive(cl)

def test_gentle_ping_reraises_challenge_required():
    from instagrapi.exceptions import ChallengeRequired
    cl = mock.Mock()
    cl.sync_launcher.side_effect = ChallengeRequired()
    with pytest.raises(ChallengeRequired):
        ip.gentle_ping(cl)

def test_keepalive_transient_error_still_true():
    cl = mock.Mock()
    cl.get_timeline_feed.side_effect = RuntimeError("transient network blip")
    assert ip.keepalive(cl) is True
```

(`ip` = however the existing tests import the module under test; reuse their import. If they don't import `mock`/`pytest`, add the imports the way the file already does.)

- [ ] **Step 2: Run tests, verify the two new ChallengeRequired tests FAIL**

Run: `python3 -m pytest skills/earn/clip/tests/test_login_resilient.py -q`
Expected: 2 new failures (ChallengeRequired swallowed → no raise), transient test passes.

- [ ] **Step 3: Implement — reorder except clauses in both functions:**

```python
def keepalive(cl):
    # Read-only session-alive probe (v24 point 2). Never writes, never relogins. Returns False
    # ONLY on a confirmed LoginRequired (the session is actually dead); a bloks ChallengeRequired
    # is a poison signal and must PROPAGATE to the caller (which marks the account poisoned);
    # any other exception is an inconclusive/transient blip, not proof of death.
    try:
        cl.get_timeline_feed()
        return True
    except LoginRequired:
        return False
    except ChallengeRequired:
        raise
    except Exception:
        return True


def gentle_ping(cl):
    # (keep existing docstring comment block unchanged)
    try:
        cl.sync_launcher(login=False)
        return True
    except LoginRequired:
        return False
    except ChallengeRequired:
        raise
    except AttributeError:
        return keepalive(cl)
    except Exception:
        return True
```

(`ChallengeRequired` is already imported at module top — verify with grep before assuming; if not, add it to the existing exceptions import line.)

- [ ] **Step 4: Run full clip suite, verify green**

Run: `python3 -m pytest skills/earn/clip/tests/ -q`
Expected: 0 failed.

- [ ] **Step 5: Commit**

```bash
git add skills/earn/clip/scripts/instagrapi_post.py skills/earn/clip/tests/test_login_resilient.py
git commit -m "fix(clip): keepalive probes must not swallow bloks ChallengeRequired (v24 #12)"
```

---

### Task 2: `--keepalive` CLI mode (golden-session probe, read-only, never logs in)

**Files:**
- Modify: `skills/earn/clip/scripts/instagrapi_post.py` (new function `keepalive_main` after `login_resilient`; `main()` argparse ~L253-260)
- Test: `skills/earn/clip/tests/test_keepalive_mode.py` (create)

- [ ] **Step 1: Write the failing tests** (`test_keepalive_mode.py`, mirroring `test_login_resilient.py`'s import/mock style):

```python
def test_keepalive_main_no_settings_file(tmp_path):
    res = ip.keepalive_main("nosuch", settings_path=str(tmp_path / "absent.json"))
    assert res["alive"] is False
    assert "no saved session" in res["error"]

def test_keepalive_main_alive_dumps_settings(tmp_path, fake_client):
    # fake_client: get_timeline_feed ok, sync_launcher ok
    settings = tmp_path / "s.json"; settings.write_text("{}")
    res = ip.keepalive_main("h", settings_path=str(settings), client_factory=lambda: fake_client)
    assert res["alive"] is True and res["feed_ok"] is True and res["ping_ok"] is True
    fake_client.dump_settings.assert_called_once_with(str(settings))

def test_keepalive_main_login_required_never_relogins(tmp_path, fake_client):
    from instagrapi.exceptions import LoginRequired
    fake_client.get_timeline_feed.side_effect = LoginRequired()
    settings = tmp_path / "s.json"; settings.write_text("{}")
    res = ip.keepalive_main("h", settings_path=str(settings), client_factory=lambda: fake_client)
    assert res["alive"] is False
    fake_client.login.assert_not_called()
    fake_client.login_by_sessionid.assert_not_called()
    assert res.get("poisoned") is not True

def test_keepalive_main_challenge_marks_poisoned(tmp_path, fake_client):
    from instagrapi.exceptions import ChallengeRequired
    fake_client.get_timeline_feed.side_effect = ChallengeRequired()
    settings = tmp_path / "s.json"; settings.write_text("{}")
    accounts = tmp_path / "accounts.json"
    accounts.write_text('[{"handle": "h", "status": "ready"}]')
    res = ip.keepalive_main("h", settings_path=str(settings), accounts_path=str(accounts), client_factory=lambda: fake_client)
    assert res["alive"] is False and res["poisoned"] is True
    import json as j
    assert j.load(open(accounts))[0]["status"] == "poisoned_manual_backup"
    fake_client.login.assert_not_called()
```

Provide `fake_client` as a local pytest fixture (a `mock.Mock()` whose `load_settings`/`dump_settings`/`get_timeline_feed`/`sync_launcher` succeed by default).

- [ ] **Step 2: Run, verify FAIL** (`keepalive_main` not defined)

Run: `python3 -m pytest skills/earn/clip/tests/test_keepalive_mode.py -q`
Expected: FAIL/error on missing attribute `keepalive_main`.

- [ ] **Step 3: Implement `keepalive_main`** (insert after `login_resilient`, before `get_sessionid`):

```python
def keepalive_main(handle, settings_path=None, accounts_path=None, client_factory=None):
    # v24 point 2, wired: two-stage read-only probe on the golden session, fired by
    # session_vault_tick.sh every 30 min so the session never rots between posts.
    # NEVER logs in — a dead session is self-heal's job (replace the account), not ours.
    # On success, persist refreshed cookies back to disk (gold standard: alsk1992 ig.py L556-708).
    res = {"handle": handle, "mode": "keepalive", "alive": False}
    settings = settings_path or C(f"~/.cloak/instagrapi-{handle}.json")
    if not os.path.exists(settings):
        res["error"] = "no saved session — keepalive only applies to accounts with a golden session"
        return res
    if client_factory is None:
        from instagrapi import Client
        client_factory = Client
    cl = client_factory()
    cl.delay_range = [2, 5]
    try:
        cl.load_settings(settings)
    except Exception as e:
        res["error"] = f"load_settings failed: {type(e).__name__}"
        return res
    try:
        res["feed_ok"] = keepalive(cl)
        res["ping_ok"] = gentle_ping(cl) if res["feed_ok"] else False
        res["alive"] = bool(res["feed_ok"] and res["ping_ok"])
        if res["alive"]:
            cl.dump_settings(settings)
    except ChallengeRequired:
        mark_poisoned(handle, "keepalive ChallengeRequired (bloks) — replace, never relogin", accounts_path)
        res["poisoned"] = True
        res["error"] = "account poisoned (bloks ChallengeRequired) during keepalive"
    return res
```

**And in `main()`:** add `--keepalive` flag; `--video`/`--caption-file` become optional but are enforced when not in keepalive mode:

```python
    ap.add_argument("--video")
    ap.add_argument("--caption-file")
    ap.add_argument("--handle", required=True)
    ap.add_argument("--port", default=os.environ.get("CDP_PORT", "9222"))
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--keepalive", action="store_true", help="read-only golden-session probe; no post, never logs in")
    a = ap.parse_args()
    if a.keepalive:
        print(json.dumps(keepalive_main(a.handle), ensure_ascii=False)); return
    if not a.video or not a.caption_file:
        ap.error("--video and --caption-file are required unless --keepalive")
```

(The rest of `main()` stays untouched.)

- [ ] **Step 4: Run full suite, verify green**

Run: `python3 -m pytest skills/earn/clip/tests/ -q`
Expected: 0 failed.

- [ ] **Step 5: Smoke-test the CLI parses (no network):**

Run: `python3 skills/earn/clip/scripts/instagrapi_post.py --keepalive --handle __smoke_no_such_account__`
Expected: one-line JSON with `"alive": false` and `"no saved session"` error. Must NOT traceback.

- [ ] **Step 6: Commit**

```bash
git add skills/earn/clip/scripts/instagrapi_post.py skills/earn/clip/tests/test_keepalive_mode.py
git commit -m "feat(clip): --keepalive golden-session probe mode (v24 #12, alsk1992 two-stage pattern)"
```

---

### Task 3: tier1 success persists refreshed settings (gold standard)

**Files:**
- Modify: `skills/earn/clip/scripts/instagrapi_post.py` (`login_resilient` tier1 block ~L165-169)
- Test: `skills/earn/clip/tests/test_login_resilient.py` (append)

- [ ] **Step 1: Write the failing test** (reuse the file's existing tier1-success fixture style):

```python
def test_tier1_success_dumps_refreshed_settings(...existing fixture args...):
    # arrange exactly like the existing tier1 happy-path test, then additionally:
    assert fake_client.dump_settings.called  # cookies refreshed on disk after successful reuse
```

(Concretely: copy the file's existing tier1 happy-path test, rename, and add the `dump_settings` assertion.)

- [ ] **Step 2: Run, verify FAIL**

Run: `python3 -m pytest skills/earn/clip/tests/test_login_resilient.py -q`
Expected: new test fails (`dump_settings` not called on tier1 path).

- [ ] **Step 3: Implement — tier1 block becomes:**

```python
    if settings_existed:
        try:
            cl.load_settings(settings)
            cl.get_timeline_feed()  # validates the session; identity guaranteed by filename
            cl.dump_settings(settings)  # persist server-rotated cookies (gold standard, alsk1992 ig.py L556-708)
            return True
```

- [ ] **Step 4: Run full suite, verify green**

Run: `python3 -m pytest skills/earn/clip/tests/ -q`
Expected: 0 failed.

- [ ] **Step 5: Commit**

```bash
git add skills/earn/clip/scripts/instagrapi_post.py skills/earn/clip/tests/test_login_resilient.py
git commit -m "feat(clip): persist refreshed cookies after tier1 session reuse (gold standard)"
```

---

### Task 4: wire keepalive into session_vault_tick.sh for instagrapi-owned accounts

**Files:**
- Modify: `skills/browser/scripts/session_vault_tick.sh` (after the existing per-account browser loop, inside the same `if/elif/else` — i.e. also guarded by the `clip_pass.sh` running check)
- Test: `skills/earn/clip/tests/test_vault_tick_instagrapi_keepalive.sh` (create)

**Why:** the tick (launchd `ai.anicca.session-vault`, StartInterval 1800) currently *excludes* `session_owner=instagrapi` accounts from browser warming (correct — churn guard) but gives them nothing instead, so the golden session gets zero traffic between posts.

- [ ] **Step 1: Write the failing shell test** (`test_vault_tick_instagrapi_keepalive.sh`, follow the style of `test_prop008_isolation.sh` — pure grep/static assertions on the script text):

```bash
#!/bin/bash
# The tick must run an instagrapi --keepalive probe for session_owner=instagrapi accounts
# (they are excluded from browser warming, so this is their ONLY between-post traffic),
# and that probe must live inside the clip_pass.sh concurrency guard.
set -u
T="$HOME/anicca/skills/browser/scripts/session_vault_tick.sh"
fail(){ echo "FAIL: $*"; exit 1; }
grep -q 'session_owner // ""' "$T" || fail "roster filter missing"
grep -q -- '--keepalive' "$T" || fail "no instagrapi --keepalive probe wired"
grep -q 'instagrapi_post.py' "$T" || fail "keepalive must go through instagrapi_post.py (single owner of session logic)"
# the keepalive block must appear AFTER the clip_pass.sh guard line (same guard applies)
guard_line=$(grep -n 'pgrep -f "clip_pass' "$T" | head -1 | cut -d: -f1)
ka_line=$(grep -n -- '--keepalive' "$T" | head -1 | cut -d: -f1)
[ -n "$guard_line" ] && [ -n "$ka_line" ] && [ "$ka_line" -gt "$guard_line" ] || fail "keepalive not under clip_pass guard"
echo "PASS"
```

- [ ] **Step 2: Run, verify FAIL**

Run: `bash skills/earn/clip/tests/test_vault_tick_instagrapi_keepalive.sh`
Expected: `FAIL: no instagrapi --keepalive probe wired`

- [ ] **Step 3: Implement — append inside the `else` branch of the existing account block in `session_vault_tick.sh`, after the browser-warm `while` loop (line ~84), still before the closing `fi`:**

```bash
  # ── instagrapi-owned accounts (session_owner=instagrapi) ──
  # These are EXCLUDED from browser warming above (a parallel web session is the churn vector,
  # v22) — instead their golden instagrapi session gets a read-only two-stage keepalive probe
  # (v24 #12: get_timeline_feed + launcher/sync ping, never logs in, poisons on bloks).
  IG_POST="$HOME/anicca/skills/earn/clip/scripts/instagrapi_post.py"
  jq -r '.[] | select((.session_owner // "") == "instagrapi" and (.status=="ready" or .status=="warming" or .status=="provisioned_pending_live_post")) | .handle' "$ACCOUNTS" |
  while IFS= read -r handle; do
    [ -z "$handle" ] && continue
    log "clip/$handle (instagrapi): golden-session keepalive"
    python3 "$IG_POST" --keepalive --handle "$handle" >&2 || true
  done
```

- [ ] **Step 4: Run the new shell test + bash syntax check, verify green**

Run: `bash skills/earn/clip/tests/test_vault_tick_instagrapi_keepalive.sh && bash -n skills/browser/scripts/session_vault_tick.sh && echo SYNTAX-OK`
Expected: `PASS` then `SYNTAX-OK`.

- [ ] **Step 5: Run the ENTIRE clip test suite + all clip shell tests**

Run: `python3 -m pytest skills/earn/clip/tests/ -q && for t in skills/earn/clip/tests/test_*.sh; do bash "$t" >/dev/null 2>&1 || echo "SHELL-FAIL: $t"; done; echo DONE`
Expected: 0 failed, no `SHELL-FAIL` lines, `DONE`.

- [ ] **Step 6: Commit**

```bash
git add skills/browser/scripts/session_vault_tick.sh skills/earn/clip/tests/test_vault_tick_instagrapi_keepalive.sh
git commit -m "feat(clip): session_vault_tick runs instagrapi golden-session keepalive for instagrapi-owned accounts (v24 #12)"
```

---

## Out of scope (explicitly)

- Client TCP rotation (alsk1992 human_mimic.py L192-206): each clip pass is a fresh short-lived process; there is no long-lived connection to rotate. YAGNI.
- New account creation / posting (Task #2 on the TaskList) — happens after this merges.
- `@aiclips_world_hq2` recovery — semi-poisoned, do not touch.
- launchd plist changes — `ai.anicca.session-vault` already ticks every 1800s.
