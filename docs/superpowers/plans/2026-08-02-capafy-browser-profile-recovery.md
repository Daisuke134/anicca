# Capafy Browser and Profile Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Capafy publishing recover autonomously from shared-browser Playwright attachment timeouts and prevent an isolated provider config from ever staging the main OpenClaw `.env`.

**Architecture:** Add a small target-scoped CDP CLI that connects only to the Capafy page whose temporary token was returned by the platform; it never enumerates or mutates unrelated tabs. Separately, make `OPENCLAW_CONFIG_PATH` imply its parent as the OpenClaw state root unless an explicit `OPENCLAW_STATE_DIR` is supplied, so config and `.env` cannot silently come from different profiles.

**Tech Stack:** Python 3.14, Chrome DevTools Protocol over `websockets`, pytest, existing Capafy publisher and browser-guard contracts.

## Global Constraints

- One Capafy publish chain at a time; never create a replacement Agent to recover a checkpoint.
- Never close, navigate, or inspect a browser target that does not contain the exact platform-issued temporary token.
- Never print credential values; secret entry accepts an environment-variable name and reads the value inside the process.
- `OPENCLAW_STATE_DIR` remains the explicit highest-priority state-root override.
- With only `OPENCLAW_CONFIG_PATH=/x/profile/openclaw.json`, optional state files must resolve under `/x/profile`, never `~/.openclaw`.
- Success remains a fresh platform readback, not a browser toast or code exit alone.

---

### Task 1: Fail-closed OpenClaw profile binding

**Files:**
- Modify: `/Users/anicca/.openclaw/skills/capafy-autopublish/vendor/capafy-publisher/packaging/runtimes/openclaw/workspace_common.py`
- Create: `/Users/anicca/.openclaw/skills/capafy-autopublish/tests/test_openclaw_profile_binding.py`
- Modify: `/Users/anicca/.openclaw/skills/capafy-autopublish/vendor/capafy-publisher/docs/openclaw-2026-6-publish-compatibility.md`

**Interfaces:**
- Consumes: `OPENCLAW_CONFIG_PATH`, optional `OPENCLAW_STATE_DIR`.
- Produces: `resolve_openclaw_state_root(openclaw_root: Path = OPENCLAW_ROOT) -> Path` with explicit-state, config-parent, default-root precedence.

- [x] **Step 1: Write the failing tests**

```python
def test_config_path_parent_is_implicit_state_root(monkeypatch, tmp_path):
    profile = tmp_path / "profile"
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(profile / "openclaw.json"))
    monkeypatch.delenv("OPENCLAW_STATE_DIR", raising=False)
    assert workspace_common.resolve_openclaw_state_root() == profile

def test_explicit_state_root_overrides_config_parent(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "profile" / "openclaw.json"))
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(tmp_path / "explicit"))
    assert workspace_common.resolve_openclaw_state_root() == tmp_path / "explicit"
```

- [x] **Step 2: Run RED**

Run: `uv run --with pytest pytest -q /Users/anicca/.openclaw/skills/capafy-autopublish/tests/test_openclaw_profile_binding.py`

Expected: the config-only case returns the main OpenClaw root instead of the profile parent.

- [x] **Step 3: Implement the minimal precedence rule**

```python
def resolve_openclaw_state_root(*, openclaw_root: Path = OPENCLAW_ROOT) -> Path:
    configured_state = str(os.environ.get(OPENCLAW_STATE_DIR_ENV, "") or "").strip()
    if configured_state:
        return safe_expanduser_path(configured_state)
    configured_config = str(os.environ.get(OPENCLAW_CONFIG_PATH_ENV, "") or "").strip()
    if configured_config:
        return safe_expanduser_path(configured_config).parent
    return safe_expanduser_path(openclaw_root)
```

- [x] **Step 4: Run GREEN and the publisher regression tests**

Run: `uv run --with pytest pytest -q /Users/anicca/.openclaw/skills/capafy-autopublish/tests`

Expected: all tests pass with no warnings.

- [x] **Step 5: Verify a Google-only dry configure boundary**

Run the packaging scan against a disposable local state using only `OPENCLAW_CONFIG_PATH`; assert the staged `.env` source is the config parent, the reviewed contract has exactly one Google `url_proxy`, and `generic=0`. Do not call a remote mutation command.

### Task 2: Exact-target CDP recovery CLI

**Files:**
- Create: `/Users/anicca/.openclaw/skills/capafy-autopublish/scripts/capafy_target_cdp.py`
- Create: `/Users/anicca/.openclaw/skills/capafy-autopublish/tests/test_capafy_target_cdp.py`
- Modify: `/Users/anicca/.openclaw/skills/capafy-autopublish/CP1_AGENTIC.md`
- Modify: `/Users/anicca/.openclaw/skills/capafy-autopublish/CP2_AGENTIC.md`

**Interfaces:**
- Consumes: `--cdp-url`, exact `--token`, and one command: `state`, `navigate`, `click-text`, or `fill`.
- Produces: bounded JSON containing only the matched target ID, current URL, non-secret field metadata, buttons, validation colors, and command outcome.
- `fill --env-name GEMINI_API_KEY` reads the secret internally and reports only its final length.

- [ ] **Step 1: Write failing pure-selection and redaction tests**

```python
def test_select_target_requires_exact_token():
    targets = [
        {"id": "wrong", "type": "page", "url": "https://capafy.ai/?token=111"},
        {"id": "right", "type": "page", "url": "https://capafy.ai/?token=222"},
    ]
    assert target_cdp.select_exact_target(targets, "222")["id"] == "right"

def test_select_target_refuses_ambiguous_or_missing_token():
    with pytest.raises(ValueError):
        target_cdp.select_exact_target([], "222")

def test_secret_result_reports_length_only():
    assert target_cdp.redact_field_value("password", "abc123") == "<set len=6>"
```

- [ ] **Step 2: Run RED**

Run: `uv run --with pytest pytest -q /Users/anicca/.openclaw/skills/capafy-autopublish/tests/test_capafy_target_cdp.py`

Expected: import or missing-function failure.

- [ ] **Step 3: Implement target selection, one-target websocket calls, state, trusted click, and trusted fill**

The implementation must fetch `/json/list`, require exactly one `type=page` URL containing `token=<exact token>`, connect to `/devtools/page/<target id>`, and use `Input.dispatchMouseEvent` / `Input.insertText`. It must never call whole-browser Playwright and never return a password value.

- [ ] **Step 4: Run GREEN and static checks**

Run: `uv run --with pytest pytest -q /Users/anicca/.openclaw/skills/capafy-autopublish/tests`

Run: `python3 -m py_compile /Users/anicca/.openclaw/skills/capafy-autopublish/scripts/capafy_target_cdp.py`

Expected: all tests and compilation pass without warnings.

- [ ] **Step 5: Run a read-only live integration against the current Performance Review review token**

Acquire `interactive:dais`, call `state` with the exact token, assert the returned URL contains only that token and the output contains no credential value, then release the lease. Do not navigate or click during this integration check.

### Task 3: Runtime handoff and living-spec checkpoint

**Files:**
- Modify: `/Users/anicca/anicca/skills/self/capafy-loop/capafy-loop-daily.sh`
- Modify: `/Users/anicca/anicca/docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`

**Interfaces:**
- Consumes: Playwright attachment timeout or profile-boundary error text.
- Produces: deterministic next action naming `capafy_target_cdp.py` and the paired-profile rule; no `self-fix` dispatch for these now-known recoverable cases.

- [ ] **Step 1: Add a failing prompt-contract test**

Extend the existing Capafy loop wiring test to require the exact-target fallback command, exact token requirement, and the paired `OPENCLAW_CONFIG_PATH` / `OPENCLAW_STATE_DIR` safety rule.

- [ ] **Step 2: Run RED, then update only the recovery paragraph**

Do not rewrite pricing, renewal, Telegram, or business-outcome instructions. Add the two deterministic recovery rules beside the existing browser lease rule.

- [ ] **Step 3: Run the focused wiring test and full Capafy suite**

Run: `uv run --with pytest pytest -q skills/earn/capafy-marketing/tests`

Expected: the complete suite passes.

- [ ] **Step 4: Poll Agent `4886968609` and update the living spec**

If `status=4`, generate and apply its provider-bound packaging decision. If it remains `status=1`, record automatic review as the external machine condition and no human action. Include command evidence, browser lease state, test counts, and commit identifiers.
