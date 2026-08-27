#!/usr/bin/env python3
"""Bounded provider-agnostic agent runner with durable per-attempt evidence."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from token_budget import TokenBudgetLedger, budget_day_for


HERE = Path(__file__).resolve().parent
# These tools can perform the filesystem mutation required by a high-value
# invocation.  Artifact truth is still decided by the deterministic domain
# validator after the provider exits.
OPENCLAW_WRITE_TOOLS = frozenset(("write", "file_write", "edit", "apply_patch", "exec"))
OPENCLAW_THINKING_VALUES = frozenset(("off", "minimal", "low", "medium", "high", "xhigh", "adaptive", "max"))
OPENCLAW_JSON_FENCE = re.compile(r"\A```json\r?\n(?P<body>.*?)\r?\n```\Z", re.DOTALL)
HERMES_JSON_FENCE = re.compile(r"```json\r?\n(?P<body>.*?)\r?\n```", re.DOTALL)
BLOCKRUN_WALLET_NOTICE = "> **⚠️ Wallet empty** — using free model. Send USDC to `0x2f4816a5d3494A2F2fE217C191B360762B8A1B2e`.\n\n"
DEFAULT_USAGE_LEDGER = Path.home() / ".local" / "state" / "anicca" / "telemetry" / "agent-usage.jsonl"
CLAUDE_PROVIDERS = {"claude", "claude-direct"}
# Smallest prompt that could plausibly express a bounded task. Kept low on
# purpose: this is a floor against empty/degenerate transport, not a style
# rule. Callers that legitimately want a stricter floor set
# AGENT_RUNNER_MIN_PROMPT_CHARS (run_agent.sh does, for loop prompts).
MIN_PROMPT_CHARS = 16
DEFAULT_HISTORY_GENERATIONS = 3

# OpenAI Standard tier, short context, USD per 1M tokens: (input, cached_input, output).
# Source: https://developers.openai.com/api/docs/pricing (fetched 2026-07-25).
CODEX_MTOK_PRICING_USD = {
    "gpt-5.6-luna": (1.00, 0.10, 6.00),
    "gpt-5.6-terra": (2.50, 0.25, 15.00),
    "gpt-5.6-sol": (5.00, 0.50, 30.00),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(name, path)
    except BaseException:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(value)
        os.replace(name, path)
    except BaseException:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_bytes(path: Path) -> int:
    total = 0
    for current, directories, files in os.walk(path, followlinks=False):
        directories[:] = [
            name for name in directories
            if not (Path(current) / name).is_symlink()
        ]
        for name in files:
            try:
                total += (Path(current) / name).lstat().st_size
            except OSError:
                continue
    return total


def prune_history_generations(history: Path, *, keep: int = DEFAULT_HISTORY_GENERATIONS) -> dict[str, int]:
    """Bound rotated runner output without touching ledgers or the active run."""
    result = {"removed": 0, "bytes_reclaimed": 0, "errors": 0}
    try:
        generations = sorted(
            path for path in history.iterdir()
            if path.is_dir() and not path.is_symlink() and ".gc-trash." not in path.name
        )
    except OSError:
        result["errors"] += 1
        return result
    for generation in generations[:-max(0, keep)] if keep > 0 else generations:
        reclaimed = _tree_bytes(generation)
        trash = generation.with_name(f"{generation.name}.gc-trash.{os.getpid()}")
        try:
            os.replace(generation, trash)
            shutil.rmtree(trash)
        except OSError:
            result["errors"] += 1
            continue
        result["removed"] += 1
        result["bytes_reclaimed"] += reclaimed
    return result


def _token(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _empty_usage() -> dict[str, Any]:
    return {
        "measurement": "unavailable",
        "input_tokens": None,
        "cached_input_tokens": None,
        "cache_creation_input_tokens": None,
        "output_tokens": None,
        "reasoning_output_tokens": None,
        "total_tokens": None,
        "provider_cost_usd": None,
        "cost_basis": "unavailable",
        "upstream_provider": None,
        "upstream_model": None,
    }


def extract_provider_usage(provider: str, stdout_text: str, model: str | None = None) -> dict[str, Any]:
    """Normalize provider-reported usage; never invent missing token counts."""
    usage = _empty_usage()
    try:
        if provider == "codex":
            completed = None
            for line in stdout_text.splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict) and event.get("type") == "turn.completed":
                    completed = event.get("usage")
            if not isinstance(completed, dict):
                return usage
            input_tokens = _token(completed.get("input_tokens"))
            output_tokens = _token(completed.get("output_tokens"))
            if input_tokens is None or output_tokens is None:
                return usage
            if any(_token(completed[key]) is None for key in ("cached_input_tokens", "reasoning_output_tokens") if key in completed):
                return usage
            usage.update({
                "measurement": "provider_reported",
                "input_tokens": input_tokens,
                "cached_input_tokens": _token(completed.get("cached_input_tokens")) or 0,
                "cache_creation_input_tokens": 0,
                "output_tokens": output_tokens,
                "reasoning_output_tokens": _token(completed.get("reasoning_output_tokens")) or 0,
                "total_tokens": input_tokens + output_tokens,
            })
            pricing = CODEX_MTOK_PRICING_USD.get(str(model or ""))
            if pricing is not None:
                cached = usage["cached_input_tokens"]
                uncached = max(0, input_tokens - cached)
                input_rate, cached_rate, output_rate = pricing
                usage["provider_cost_usd"] = (
                    uncached * input_rate + cached * cached_rate + output_tokens * output_rate
                ) / 1_000_000
                # Codex runs on subscription; this is the API-price equivalent,
                # the same cost basis the Claude CLI branch reports below.
                usage["cost_basis"] = "api_equivalent_estimate"
            return usage
        wrapper = json.loads(stdout_text)
        if not isinstance(wrapper, dict):
            return usage
        if provider in CLAUDE_PROVIDERS:
            model_usage = wrapper.get("modelUsage")
            if isinstance(model_usage, dict) and len(model_usage) == 1:
                usage["upstream_model"] = next(iter(model_usage))
            raw = wrapper.get("usage")
            if not isinstance(raw, dict):
                return usage
            direct = _token(raw.get("input_tokens"))
            output_tokens = _token(raw.get("output_tokens"))
            if direct is None or output_tokens is None:
                return usage
            if any(_token(raw[key]) is None for key in ("cache_creation_input_tokens", "cache_read_input_tokens", "reasoning_output_tokens") if key in raw):
                return usage
            cache_create = _token(raw.get("cache_creation_input_tokens")) or 0
            cache_read = _token(raw.get("cache_read_input_tokens")) or 0
            cost = wrapper.get("total_cost_usd")
            usage.update({
                "measurement": "provider_reported",
                "input_tokens": direct + cache_create + cache_read,
                "cached_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_create,
                "output_tokens": output_tokens,
                "reasoning_output_tokens": _token(raw.get("reasoning_output_tokens")) or 0,
                "total_tokens": direct + cache_create + cache_read + output_tokens,
                "provider_cost_usd": float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) and 0 <= cost <= sys.float_info.max else None,
                # Claude CLI exposes an API-price equivalent even when OAuth/subscription is
                # paying the actual bill. It is useful telemetry, but not actual marginal cost.
                "cost_basis": "api_equivalent_estimate" if isinstance(cost, (int, float)) and not isinstance(cost, bool) and 0 <= cost <= sys.float_info.max else "unavailable",
            })
            return usage
        if provider == "openclaw":
            agent_meta = wrapper.get("result", {}).get("meta", {}).get("agentMeta", {})
            raw = agent_meta.get("lastCallUsage") if isinstance(agent_meta, dict) else None
            if not isinstance(raw, dict):
                return usage
            input_tokens = _token(raw.get("input"))
            output_tokens = _token(raw.get("output"))
            if input_tokens is None or output_tokens is None:
                return usage
            if any(_token(raw[key]) is None for key in ("cacheRead", "cacheWrite", "total") if key in raw):
                return usage
            usage.update({
                "measurement": "provider_reported",
                "input_tokens": input_tokens,
                "cached_input_tokens": _token(raw.get("cacheRead")) or 0,
                "cache_creation_input_tokens": _token(raw.get("cacheWrite")) or 0,
                "output_tokens": output_tokens,
                "reasoning_output_tokens": 0,
                "total_tokens": _token(raw.get("total")) if "total" in raw else input_tokens + output_tokens,
                "upstream_provider": agent_meta.get("provider"),
                "upstream_model": agent_meta.get("model"),
            })
            return usage
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return usage
    return usage


def budget_charge_tokens(
    provider: str,
    usage: dict[str, Any],
    reservation_tokens: int,
) -> int:
    if usage.get("measurement") != "provider_reported":
        return reservation_tokens
    total = _token(usage.get("total_tokens"))
    if total is None or total <= 0:
        return reservation_tokens
    if provider != "codex":
        return total
    cached = _token(usage.get("cached_input_tokens"))
    if cached is None or cached > total:
        return reservation_tokens
    return total - cached


def extract_claude_payload(stdout_path: Path, result_path: Path) -> str:
    """Unwrap Claude's JSON output envelope while tolerating legacy plain output."""
    text = stdout_path.read_text(encoding="utf-8", errors="replace")
    try:
        wrapper = json.loads(text)
    except json.JSONDecodeError:
        result_path.write_text(text, encoding="utf-8")
        return ""
    if isinstance(wrapper, dict) and wrapper.get("type") == "result" and "result" in wrapper:
        payload = wrapper["result"]
        result_path.write_text(
            payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
    else:
        result_path.write_text(text, encoding="utf-8")
    return ""


def extract_hermes_payload(stdout_path: Path, result_path: Path) -> str:
    """Extract one Hermes JSON object, rejecting ambiguous or unsafe output."""
    result_path.unlink(missing_ok=True)
    text = stdout_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return "hermes output is empty"
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = None
    if isinstance(value, dict):
        atomic_text(result_path, text)
        return ""
    fences = list(HERMES_JSON_FENCE.finditer(text))
    if text.count("```") != 2 or len(fences) != 1:
        return "hermes output must contain exactly one JSON object or fenced JSON object"
    match = fences[0]
    outside = text[:match.start()] + text[match.end():]
    if any(marker in outside for marker in ("{", "[")):
        return "hermes output has ambiguous JSON outside fenced object"
    body = match.group("body").strip()
    try:
        value = json.loads(body)
    except json.JSONDecodeError:
        return "hermes fenced payload is not valid JSON"
    if not isinstance(value, dict):
        return "hermes fenced payload must be a JSON object"
    atomic_text(result_path, body)
    return ""


def append_usage_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Terminate a timed-out provider and every child in its process group."""
    if os.name == "posix":
        # Codex Code Mode may start tool commands in their own sessions.  killpg(provider)
        # cannot reach those descendants and, once the provider exits, launchd reparents them
        # to PID 1.  Snapshot the live descendant tree before killing the provider so detached
        # browser/search commands cannot retain an account lease after their owner times out.
        descendants: list[int] = []
        try:
            rows = subprocess.run(
                ["/bin/ps", "-axo", "pid=,ppid="],
                check=True, capture_output=True, text=True, timeout=2,
            ).stdout.splitlines()
            children: dict[int, list[int]] = {}
            for row in rows:
                fields = row.split()
                if len(fields) != 2:
                    continue
                pid, parent = (int(value) for value in fields)
                children.setdefault(parent, []).append(pid)
            stack = list(children.get(process.pid, []))
            while stack:
                pid = stack.pop()
                descendants.append(pid)
                stack.extend(children.get(pid, []))
        except (OSError, ValueError, subprocess.SubprocessError):
            descendants = []
        for pid in reversed(descendants):
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        for pid in reversed(descendants):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    else:
        process.kill()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _strip_browser_routes_for_planner(child_env: dict[str, str]) -> dict[str, str]:
    """Remove every inherited browser/CDP or loopback route from a planner child.

    The application-intent planner is intentionally a data-only process.  A provider
    receiving an arbitrary local URL through a non-obvious variable is equivalent to
    giving it the leased websocket, so isolation applies to both variable names and
    values.  Provider credentials and PATH remain untouched.
    """
    forbidden_name_fragments = (
        "BROWSER", "CDP", "WEBSOCKET", "PLAYWRIGHT", "PUPPETEER",
    )
    loopback_markers = ("localhost", "127.0.0.1", "[::1]", "//::1")
    return {
        name: value
        for name, value in child_env.items()
        if not any(fragment in name.upper() for fragment in forbidden_name_fragments)
        and not any(marker in value.lower() for marker in loopback_markers)
    }


# Names a self-fix child process is allowed to see. Fail-closed by construction: a new
# credential-shaped variable added anywhere upstream (a wallet key, a marketplace session
# token, a .env export) is excluded by default because it is not on this list, not because
# something remembered to blocklist it.
SELF_FIX_ENV_ALLOWLIST = (
    "PATH", "LANG", "LC_ALL", "TERM", "TMPDIR", "TMP", "TEMP", "USER", "LOGNAME", "SHELL",
)


def self_fix_process_env(child_env: dict[str, str], evidence_dir: Path) -> dict[str, str]:
    """Confine a self-fix fixer: no credentials, no push access, writes cannot reach $HOME.

    Two of the four non-negotiable self-fix constraints
    (docs/loop-engineering/26-gig-loop-asis-tobe-plan.md v10.5 SS AB'/SC) are enforced here,
    not merely documented:

    - "NO CREDENTIALS in the fixer's environment": only SELF_FIX_ENV_ALLOWLIST survives.
      SSH_AUTH_SOCK and GIT_ASKPASS are dropped explicitly even though the allowlist above
      already excludes them, because losing push credentials is what makes the next
      constraint hold structurally rather than by instruction.
    - "PUSH ONLY TO A FEATURE BRANCH": with no SSH agent socket and no askpass helper, a
      `git push` attempted from inside this process has no credential to authenticate with.
      The dispatcher that spawned this fixer (skills/gig-work/scripts/gig_self_fix.py) does
      the actual `git push`, itself, after the fixer exits and tests are verified green --
      always to a fresh `self-fix/<id>` branch it created, never to the branch it started on.

    $HOME is redirected to a scratch directory under this run's own evidence_dir so a
    tilde-relative path can never resolve to the real browser profile, gig state, or host-agent
    state roots --
    the same pattern this module already uses for the codex provider's automation_home
    (see provider_process_env's codex branch above). Claude Code's own login lives in the
    macOS Keychain (service "Claude Code-credentials"), not under $HOME, so this redirection
    does not break the fixer's ability to authenticate as the provider.
    """
    scratch_home = evidence_dir / "self-fix-home"
    scratch_home.mkdir(parents=True, exist_ok=True, mode=0o700)
    scoped = {name: child_env[name] for name in SELF_FIX_ENV_ALLOWLIST if name in child_env}
    scoped["HOME"] = str(scratch_home)
    scoped.pop("SSH_AUTH_SOCK", None)
    scoped.pop("GIT_ASKPASS", None)
    return scoped


def provider_process_env(provider: str, provider_config: dict[str, Any],
                         environ: dict[str, str] | None = None,
                         *, task_class: str | None = None,
                         evidence_dir: Path | None = None) -> dict[str, str]:
    """Build a provider-scoped, non-interactive child environment."""
    child_env = dict(os.environ if environ is None else environ)
    if provider == "codex":
        automation_home_value = provider_config.get("automation_home")
        if automation_home_value:
            automation_home = Path(os.path.expandvars(os.path.expanduser(
                str(automation_home_value)
            )))
            automation_home.mkdir(parents=True, exist_ok=True, mode=0o700)
            automation_home.chmod(0o700)
            child_env["CODEX_HOME"] = str(automation_home)
            automation_user_home = automation_home / "user-home"
            automation_user_home.mkdir(parents=True, exist_ok=True, mode=0o700)
            automation_user_home.chmod(0o700)
            child_env["HOME"] = str(automation_user_home)

            ssl_cert_file_value = provider_config.get("ssl_cert_file")
            if ssl_cert_file_value:
                ssl_cert_file = Path(os.path.expandvars(os.path.expanduser(
                    str(ssl_cert_file_value)
                )))
                if not ssl_cert_file.is_file():
                    raise ValueError("codex TLS certificate bundle unavailable")
                child_env["SSL_CERT_FILE"] = str(ssl_cert_file)

            if not child_env.get("OPENAI_API_KEY"):
                auth_file = Path(os.path.expandvars(os.path.expanduser(str(
                    provider_config.get("auth_file", "~/.codex/auth.json")
                ))))
                if not auth_file.is_file():
                    raise ValueError("codex automation auth unavailable")
                auth_source = auth_file.resolve()
                auth_target = automation_home / "auth.json"
                try:
                    auth_target.symlink_to(auth_source)
                except FileExistsError:
                    try:
                        if auth_target.resolve(strict=True) != auth_source:
                            raise ValueError("codex automation auth target mismatch")
                    except OSError as error:
                        raise ValueError("codex automation auth target invalid") from error
    elif provider in CLAUDE_PROVIDERS and provider == "claude-direct":
        # ``claude-direct`` normally means the user's direct Claude login.  A
        # configured loopback proxy is an explicit, machine-local fallback:
        # it keeps the same tool-less JSON boundary while avoiding a DNS or
        # upstream OAuth outage.  Without the opt-in flag this remains the
        # original direct-login path and never inherits proxy credentials.
        if provider_config.get("loopback_proxy") is True:
            token_file = os.path.expandvars(os.path.expanduser(str(
                provider_config.get("auth_token_file", "~/.cli-proxy-api-key")
            )))
            try:
                auth_token = Path(token_file).read_text(encoding="utf-8").strip()
            except OSError as error:
                raise ValueError("claude loopback proxy auth unavailable") from error
            if not auth_token:
                raise ValueError("claude loopback proxy auth unavailable")
            child_env["ANTHROPIC_BASE_URL"] = str(
                provider_config.get("base_url", "http://127.0.0.1:8317")
            )
            child_env["ANTHROPIC_AUTH_TOKEN"] = auth_token
            for name in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"):
                child_env.pop(name, None)
        else:
            for name in (
                "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN",
                "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN",
            ):
                child_env.pop(name, None)
    elif provider in CLAUDE_PROVIDERS and not any(child_env.get(name) for name in (
        "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN",
    )):
        token_file = os.path.expandvars(os.path.expanduser(str(
            provider_config.get("auth_token_file", "~/.cli-proxy-api-key")
        )))
        try:
            auth_token = Path(token_file).read_text(encoding="utf-8").strip()
        except OSError as error:
            raise ValueError("claude headless auth unavailable") from error
        if not auth_token:
            raise ValueError("claude headless auth unavailable")
        child_env["ANTHROPIC_BASE_URL"] = str(
            provider_config.get("base_url", "http://127.0.0.1:8317")
        )
        child_env["ANTHROPIC_AUTH_TOKEN"] = auth_token
    if task_class == "application-intent-planner":
        return _strip_browser_routes_for_planner(child_env)
    if task_class == "self-fix":
        if evidence_dir is None:
            raise ValueError("self-fix task class requires evidence_dir for env confinement")
        return self_fix_process_env(child_env, evidence_dir)
    return child_env


def expand_codex_candidates(
    candidates: list[dict[str, Any]], providers: dict[str, Any]
) -> list[dict[str, Any]]:
    expanded: list[dict[str, Any]] = []
    for candidate in candidates:
        accounts = providers.get(candidate.get("provider"), {}).get("accounts", [])
        if candidate.get("provider") != "codex" or not accounts:
            expanded.append(dict(candidate))
            continue
        for account_index, account in enumerate(accounts):
            scoped = dict(candidate)
            scoped.update({
                "account": account["alias"],
                "account_index": account_index,
                "account_count": len(accounts),
                "automation_home": account["automation_home"],
                "auth_file": account["auth_file"],
            })
            expanded.append(scoped)
    return expanded


CODEX_EFFECT_ITEM_TYPES = frozenset({
    "command_execution", "file_change", "mcp_tool_call", "web_search",
})


def codex_effect_started(stdout: str) -> bool:
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if isinstance(item, dict) and item.get("type") in CODEX_EFFECT_ITEM_TYPES:
            return True
    return False


def should_retry_next_codex_account(error_class: str | None, effect_started: bool) -> bool:
    return not effect_started and error_class in {"transient_quota", "transient_auth"}


# The live provider Popen, if any. start_new_session detaches the provider into its
# own session, so a signal aimed at the RUNNER's process group never reaches it — when
# the runner is killed externally the provider survives as an orphan (2026-07-27: an
# orphaned codex child held the gig browser lock for 12 minutes after tier1-remediate
# SIGTERMed the worker; the next pass died with deferred_cdp_busy, exit 75). The
# forwarding handler below is that signal's only path into the detached session.
_ACTIVE_PROVIDER_PROCESS: subprocess.Popen[bytes] | None = None


def forward_termination_to_provider(signum: int, _frame: Any) -> None:
    """Take the detached provider's whole session down with us, then die honestly."""
    process = _ACTIVE_PROVIDER_PROCESS
    if process is not None and process.poll() is None:
        terminate_process_tree(process)
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


def install_termination_forwarding() -> None:
    if os.name != "posix":
        return
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, forward_termination_to_provider)


def run_provider_process(command: list[str], *, stdout: Any, stderr: Any,
                         timeout: int, cwd: str, input_bytes: bytes | None,
                         stdin: Any, env: dict[str, str]) -> int:
    """Run one provider in an isolated process group with a hard timeout."""
    global _ACTIVE_PROVIDER_PROCESS
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE if input_bytes is not None else stdin,
        stdout=stdout,
        stderr=stderr,
        cwd=cwd,
        env=env,
        start_new_session=os.name == "posix",
    )
    _ACTIVE_PROVIDER_PROCESS = process
    try:
        process.communicate(input=input_bytes, timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_process_tree(process)
        raise
    finally:
        _ACTIVE_PROVIDER_PROCESS = None
    return process.returncode


def resolve_executable(provider_config: dict[str, Any], default: str) -> str:
    """Resolve PATH first, then configured portable user-relative fallbacks."""
    primary = str(provider_config.get("executable", default))
    candidates = [primary, *provider_config.get("executable_fallbacks", [])]
    for candidate in candidates:
        expanded = os.path.expandvars(os.path.expanduser(str(candidate)))
        resolved = shutil.which(expanded)
        if resolved:
            return resolved
    return os.path.expandvars(os.path.expanduser(primary))


def parse_contract_result(text: str, *, salvage: bool = True) -> Any:
    """Read the contract object out of a provider reply that may carry prose.

    salvage=False keeps the openclaw wrapper path exactly as strict as it was.
    That path already has its own deliberate unwrapper (normalize_openclaw_payload)
    whose contract rejects prefix/suffix prose, a second fence, and a wallet warning
    sitting above the object -- there, the reply IS chat text, so guessing which
    object is "the result" can silently swallow a warning. Direct provider output
    written to -o is a different situation: the file is the answer, and the only
    question is whether the model fenced it.

    Providers under a schema contract sometimes answer conversationally: a sentence
    of preamble, then the object inside a ```json fence. Measured 2026-07-27 on
    gig-pass-1785123005 agent-LEARN -- the claude-direct fallback did the work
    correctly and wrote a valid object, but json.loads over the whole file failed at
    "line 1 column 1" and the step was recorded as a failure. Self-improvement had
    been stalled on this since 07-21, and capafy's listing lane fails identically.

    Strict parse first, so a clean reply is unaffected. Only then salvage, and only a
    real object: prose with no JSON at all still fails, because accepting an
    acknowledgement as a result is the defect this contract exists to prevent.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if not salvage:
            raise
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character not in "{[":
            continue
        try:
            value, _ = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            continue
        return value
    raise ValueError("no JSON object in provider result")


def validate_schema(value: Any, schema: dict[str, Any], at: str = "$") -> list[str]:
    errors: list[str] = []
    expected = schema.get("type")
    type_map = {
        "object": dict,
        "array": list,
        "string": str,
        "number": (int, float),
        "integer": int,
        "boolean": bool,
        "null": type(None),
    }
    expected_names = (
        [expected] if isinstance(expected, str)
        else expected if isinstance(expected, list)
        else []
    )
    known_names = [name for name in expected_names if name in type_map]
    if known_names:
        valid = False
        for name in known_names:
            matches = isinstance(value, type_map[name])
            if name in ("integer", "number") and isinstance(value, bool):
                matches = False
            valid = valid or matches
        if not valid:
            return [f"{at}: expected {' or '.join(known_names)}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{at}: expected const {schema['const']!r}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{at}: missing required property {key}")
        properties = schema.get("properties", {})
        for key, child in properties.items():
            if key in value:
                errors.extend(validate_schema(value[key], child, f"{at}.{key}"))
    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            errors.append(f"{at}: expected at least {schema['minItems']} items")
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                errors.extend(validate_schema(item, schema["items"], f"{at}[{index}]"))
    return errors


# Classes the runner deliberately starves of tools: they turn data into a decision
# and must not touch the world. Kept next to the contract so the two cannot drift —
# telling a tool-less turn to "use tools from that workdir" is an impossible order,
# and these classes are intentionally tool-less by contract.
TOOLLESS_TASK_CLASSES = (
    "composition-agent", "diagnostic-agent", "application-intent-planner",
    "reply-semantic-agent", "storefront-proposal-agent",
)
TOOLLESS_CODEX_DISABLED_FEATURES = (
    "shell_tool", "code_mode_host", "unified_exec",
)


def strict_output_contract(
    prompt: str,
    schema: dict[str, Any],
    workdir: Path | str,
    extra_rules: str = "",
    has_tools: bool = True,
) -> str:
    """Append the schema itself, and forbid prose, to a provider prompt.

    The task prompts end with "Return JSON matching <path to schema file>", which
    asks the model to go and read a file before it answers. Measured 2026-08-04
    from the runner's own attempts.jsonl: of eight claude-direct fallbacks on
    gig-PAID_WORK, seven were recorded schema_valid=False at $0.63 a turn
    ($4.41), and across every lane that day sixteen such failures cost $7.73.
    The one that passed still answered in prose around a ```json fence and was
    rescued by the salvage path, so the axis is not prose-versus-JSON but
    whether a contract object came back at all. Inlining the schema and stating
    the contract in the turn removes the indirection. openclaw already did this;
    codex and claude did not.
    """
    compact_schema = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    display_workdir = str(workdir.resolve()) if isinstance(workdir, Path) else str(workdir)
    return (
        prompt.rstrip()
        + "\n\nSTRICT OUTPUT CONTRACT (highest priority for this turn):\n"
        + f"- Workdir: {display_workdir}\n"
        + extra_rules
        + ("- Complete the requested work using tools from that workdir.\n"
           if has_tools else
           "- You have no tools this turn. Decide from the material already in the prompt.\n")
        + "- Return exactly one JSON object matching this full JSON Schema:\n"
        + compact_schema
        + "\n- JSON only: no Markdown fence, prose, preamble, or trailing text.\n"
        + "- If the work cannot be completed, still return the object with the "
        + "blocked/error status the schema defines. Prose is never a valid answer.\n"
    )


def openclaw_prompt(
    prompt: str,
    schema: dict[str, Any],
    workdir: Path | str,
    canonical_workdir: Path | None = None,
) -> str:
    compact_schema = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    display_workdir = str(workdir.resolve()) if isinstance(workdir, Path) else workdir
    sandbox_mapping = ""
    if canonical_workdir is not None:
        sandbox_mapping = (
            f"- Sandbox tool project root: {display_workdir}\n"
            f"- Host-canonical project root: {canonical_workdir.resolve()}\n"
            "- Use the sandbox tool project root for every filesystem tool read/write.\n"
            "- In delivery/paid-work-result.json, every path field MUST use the "
            "host-canonical project root, never /workspace.\n"
        )
    return (
        prompt.rstrip()
        + "\n\nSTRICT OUTPUT CONTRACT (highest priority for this turn):\n"
        + f"- Workdir: {display_workdir}\n"
        + sandbox_mapping
        + "- Complete the requested work using tools from that workdir.\n"
        + "- Return exactly one JSON object matching this full JSON Schema:\n"
        + compact_schema
        + "\n- JSON only: no Markdown fence, prose, preamble, or trailing text.\n"
        + "- Your entire final response becomes result.payloads[0].text; "
        + "the runner extracts that text to a fresh result_path and validates it.\n"
    )


def hermes_prompt(prompt: str, schema: dict[str, Any]) -> str:
    if not isinstance(schema, dict):
        raise ValueError("hermes provider requires an object schema")
    try:
        compact_schema = json.dumps(
            schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    except (TypeError, ValueError) as error:
        raise ValueError("hermes provider requires a JSON-serializable object schema") from error
    return (
        prompt
        + "\n\nSTRICT OUTPUT CONTRACT (highest priority for this turn):\n"
        + "- Final response MUST contain exactly one JSON object matching this schema; "
        + "summary prose or a single Markdown JSON fence is optional around it, but "
        + "schema-external structure is invalid.\n"
        + "- Schema: "
        + compact_schema
        + "\n- Return no additional JSON objects or schema-external fields.\n"
    )


def openclaw_runtime_capabilities(wrapper: Any, required: list[str]) -> tuple[dict[str, Any], str]:
    if "tool_write" not in required:
        return {}, ""
    runtime: dict[str, Any] = {"tool_write": False, "write_tools": []}
    try:
        summary = wrapper["result"]["meta"]["toolSummary"]
    except (KeyError, TypeError):
        return runtime, "missing result.meta.toolSummary"
    runtime["tool_summary"] = summary
    if not isinstance(summary, dict):
        return runtime, "result.meta.toolSummary must be an object"
    calls = summary.get("calls")
    failures = summary.get("failures")
    tools = summary.get("tools")
    if isinstance(calls, bool) or not isinstance(calls, int) or calls <= 0:
        return runtime, "result.meta.toolSummary.calls must be a positive integer"
    if isinstance(failures, bool) or not isinstance(failures, int) or failures != 0:
        return runtime, "result.meta.toolSummary.failures must equal zero"
    if not isinstance(tools, list) or not all(isinstance(name, str) and name for name in tools):
        return runtime, "result.meta.toolSummary.tools must be an array of non-empty strings"
    write_tools = [name for name in tools if name in OPENCLAW_WRITE_TOOLS]
    runtime["write_tools"] = write_tools
    if not write_tools:
        return runtime, "result.meta.toolSummary has no explicit write tool call"
    runtime["tool_write"] = True
    return runtime, ""


def normalize_openclaw_payload(text: str, runtime_capabilities: dict[str, Any]) -> str:
    """Remove the anchored BlockRun notice; unwrap one fence after proven mutation."""
    if text.startswith(BLOCKRUN_WALLET_NOTICE):
        candidate = text[len(BLOCKRUN_WALLET_NOTICE):]
        match = OPENCLAW_JSON_FENCE.fullmatch(candidate)
        probe = match.group("body") if match and runtime_capabilities.get("tool_write") is True else candidate
        try:
            json.loads(probe)
        except json.JSONDecodeError:
            pass
        else:
            text = candidate
    if runtime_capabilities.get("tool_write") is not True:
        return text
    match = OPENCLAW_JSON_FENCE.fullmatch(text)
    if not match:
        return text
    body = match.group("body")
    if "```" in body:
        return text
    return body


def extract_openclaw_payload(stdout_path: Path, result_path: Path,
                             required_capabilities: list[str]) -> tuple[str, dict[str, Any]]:
    """Extract OpenClaw's first textual payload after runtime capability checks."""
    runtime_capabilities: dict[str, Any] = {}
    try:
        wrapper = json.loads(stdout_path.read_text(encoding="utf-8"))
        runtime_capabilities, capability_error = openclaw_runtime_capabilities(
            wrapper, required_capabilities,
        )
        if capability_error:
            result_path.unlink(missing_ok=True)
            return f"openclaw runtime capability check failed: {capability_error}", runtime_capabilities
        payloads = wrapper["result"]["payloads"]
        if not isinstance(payloads, list) or not payloads:
            raise ValueError("result.payloads must be a non-empty array")
        payload = payloads[0]
        if not isinstance(payload, dict):
            raise ValueError("result.payloads[0] must be an object")
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("result.payloads[0].text must be a non-empty string")
        text = normalize_openclaw_payload(text, runtime_capabilities)
        result_path.write_text(text, encoding="utf-8")
        return "", runtime_capabilities
    except Exception as error:
        result_path.unlink(missing_ok=True)
        return f"openclaw wrapper extraction failed: {error}", runtime_capabilities


def candidate_capabilities(provider_config: dict[str, Any], candidate: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    required = candidate.get("required_capabilities", [])
    if not isinstance(required, list) or not all(isinstance(item, str) and item for item in required):
        raise ValueError("required_capabilities must be an array of non-empty strings")
    by_model = provider_config.get("model_capabilities", {})
    if not isinstance(by_model, dict):
        raise ValueError("provider model_capabilities must be an object")
    available = by_model.get(candidate.get("model"), {})
    if not isinstance(available, dict):
        raise ValueError("model capabilities must be an object")
    missing = [name for name in required if available.get(name) is not True]
    if missing:
        raise ValueError(f"missing required model capabilities: {', '.join(missing)}")
    return required, available


def openclaw_sandbox_preflight(
    executable: str,
    agent: str,
    required: dict[str, Any],
    workdir: Path,
) -> tuple[dict[str, Any], str]:
    """Verify the dedicated paid agent's effective sandbox before launch.

    OpenClaw's official docs say the workspace is only the default cwd, not a
    security boundary, and host execution remains possible while sandboxing is
    off. Paid OpenClaw work therefore requires a live-config proof first:
    https://docs.openclaw.ai/concepts/agent-workspace
    https://docs.openclaw.ai/tools/exec
    https://docs.openclaw.ai/gateway/sandboxing
    """
    evidence: dict[str, Any] = {"required": required, "agent": agent, "verified": False}
    safe_contract = {
        "mode": "all", "workspaceAccess": "rw", "containerWorkspace": "/workspace",
        "sessionIsSandboxed": True, "elevated": False, "execHost": "sandbox",
    }
    if any(required.get(key) != expected for key, expected in safe_contract.items()):
        return evidence, "paid sandbox contract is not fail-closed"
    try:
        completed = subprocess.run(
            [executable, "config", "get", "agents", "--json"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return evidence, f"sandbox config query failed: {error}"
    evidence["config_rc"] = completed.returncode
    evidence["config_stdout_sha256"] = hashlib.sha256(completed.stdout).hexdigest()
    evidence["config_stderr_sha256"] = hashlib.sha256(completed.stderr).hexdigest()
    if completed.returncode != 0:
        return evidence, "sandbox config query returned nonzero"
    try:
        config = json.loads(completed.stdout.decode("utf-8"))
        agents = config.get("list", []) if isinstance(config, dict) else []
        row = next(item for item in agents if isinstance(item, dict) and item.get("id") == agent)
    except (UnicodeDecodeError, json.JSONDecodeError, StopIteration):
        return evidence, f"dedicated agent not configured: {agent}"
    expected_workspace = Path(str(required.get("workspace") or "")).expanduser().resolve()
    actual_workspace = Path(str(row.get("workspace") or "")).expanduser().resolve()
    sandbox = row.get("sandbox")
    if actual_workspace != expected_workspace:
        return evidence, "dedicated agent workspace mismatch"
    try:
        workdir.resolve().relative_to(expected_workspace)
    except ValueError:
        return evidence, "paid workdir outside dedicated agent workspace"
    if not isinstance(sandbox, dict):
        return evidence, "dedicated agent sandbox missing"
    if sandbox.get("mode") != required.get("mode"):
        return evidence, "dedicated agent configured sandbox mode mismatch"
    if sandbox.get("workspaceAccess") != required.get("workspaceAccess"):
        return evidence, "dedicated agent configured workspaceAccess mismatch"
    tools = row.get("tools")
    if not isinstance(tools, dict):
        return evidence, "dedicated agent tool policy missing"
    elevated = tools.get("elevated")
    if not isinstance(elevated, dict) or elevated.get("enabled") is not required.get("elevated"):
        return evidence, "dedicated agent elevated policy mismatch"
    exec_policy = tools.get("exec")
    if not isinstance(exec_policy, dict) or exec_policy.get("host") != required.get("execHost"):
        return evidence, "dedicated agent exec host policy mismatch"

    try:
        explained = subprocess.run(
            [executable, "sandbox", "explain", "--agent", agent, "--json"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return evidence, f"sandbox explain query failed: {error}"
    evidence["explain_rc"] = explained.returncode
    evidence["explain_stdout_sha256"] = hashlib.sha256(explained.stdout).hexdigest()
    evidence["explain_stderr_sha256"] = hashlib.sha256(explained.stderr).hexdigest()
    if explained.returncode != 0:
        return evidence, "sandbox explain query returned nonzero"
    try:
        effective = json.loads(explained.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return evidence, "sandbox explain returned invalid JSON"
    effective_sandbox = effective.get("sandbox") if isinstance(effective, dict) else None
    effective_elevated = effective.get("elevated") if isinstance(effective, dict) else None
    if effective.get("agentId") != agent:
        return evidence, "sandbox explain agent mismatch"
    if not isinstance(effective_sandbox, dict):
        return evidence, "effective sandbox missing"
    if effective_sandbox.get("mode") != required.get("mode"):
        return evidence, "effective sandbox mode mismatch"
    if effective_sandbox.get("workspaceAccess") != required.get("workspaceAccess"):
        return evidence, "effective sandbox workspaceAccess mismatch"
    if effective_sandbox.get("sessionIsSandboxed") is not required.get("sessionIsSandboxed"):
        return evidence, "effective sandbox session state mismatch"
    if not isinstance(effective_elevated, dict):
        return evidence, "effective elevated state missing"
    # ``enabled`` may reflect the global feature switch.  Escape authority is
    # the effective per-agent allow decision below; the config row above must
    # still explicitly disable elevated tools for this dedicated agent.
    if effective_elevated.get("allowedByConfig") is not False:
        return evidence, "effective elevated allowedByConfig must be false"
    if effective_elevated.get("alwaysAllowedByConfig") is not False:
        return evidence, "effective elevated alwaysAllowedByConfig must be false"

    container_workspace_value = required.get("containerWorkspace")
    if not isinstance(container_workspace_value, str):
        return evidence, "sandbox container workspace missing"
    container_workspace = PurePosixPath(container_workspace_value)
    if not container_workspace.is_absolute() or ".." in container_workspace.parts:
        return evidence, "sandbox container workspace invalid"
    relative_project = workdir.resolve().relative_to(expected_workspace)
    sandbox_project_root = container_workspace.joinpath(*relative_project.parts)
    evidence.update({
        "verified": True,
        "workspace": str(actual_workspace),
        "mode": effective_sandbox.get("mode"),
        "workspaceAccess": effective_sandbox.get("workspaceAccess"),
        "sessionIsSandboxed": effective_sandbox.get("sessionIsSandboxed"),
        "elevatedGlobalEnabled": effective_elevated.get("enabled"),
        "elevatedAllowedByConfig": effective_elevated.get("allowedByConfig"),
        "execHost": exec_policy.get("host"),
        "sandbox_project_root": str(sandbox_project_root),
    })
    return evidence, ""


def command_for(provider: str, executable: str, provider_config: dict[str, Any],
                candidate: dict[str, Any], args: argparse.Namespace, prompt: str,
                schema: dict[str, Any], result_path: Path, timeout_seconds: int,
                session_id: str | None, openclaw_workdir: str | None = None,
                *, prompt_via_stdin: bool = False) -> list[str]:
    model = candidate["model"]
    effort = candidate.get("effort", "medium")
    if provider == "codex":
        command = [
            executable, "exec", "--ephemeral", "--model", model,
            "-c", f'model_reasoning_effort="{effort}"',
        ]
        if provider_config.get("automation_home"):
            project_doc_max_bytes = provider_config.get("project_doc_max_bytes", 0)
            if not isinstance(project_doc_max_bytes, int) or project_doc_max_bytes < 0:
                raise ValueError("codex project_doc_max_bytes must be a nonnegative integer")
            disabled_skills = provider_config.get("disabled_skills", [])
            if not isinstance(disabled_skills, list) or not all(
                isinstance(name, str) and name for name in disabled_skills
            ):
                raise ValueError("codex disabled_skills must be a list of nonempty names")
            skill_rows = ",".join(
                f'{{name={json.dumps(name)},enabled=false}}' for name in disabled_skills
            )
            command.extend([
                "-c", f"project_doc_max_bytes={project_doc_max_bytes}",
                "-c", f"shell_environment_policy.set.HOME={json.dumps(str(Path.home()))}",
                "-c", f"skills.config=[{skill_rows}]",
            ])
            disabled_features = provider_config.get("disabled_features", [])
            if not isinstance(disabled_features, list) or not all(
                isinstance(name, str) and name for name in disabled_features
            ):
                raise ValueError("codex disabled_features must be a list of nonempty names")
            for feature in disabled_features:
                command.extend(["--disable", feature])
        command.extend([
            "--ignore-user-config", "--json",
            "--output-schema", str(args.schema), "-o", str(result_path),
        ])
        for image in getattr(args, "image", []) or []:
            command.extend(["--image", str(image)])
        if args.task_class in TOOLLESS_TASK_CLASSES:
            command.extend(["--sandbox", "read-only"])
            for feature in TOOLLESS_CODEX_DISABLED_FEATURES:
                command.extend(["--disable", feature])
        elif getattr(args, "read_only", False):
            command.extend(["--sandbox", "read-only"])
        else:
            command.append("--dangerously-bypass-approvals-and-sandbox")
        command.extend([
            "--skip-git-repo-check", "-C", str(args.workdir),
            "-" if prompt_via_stdin else prompt,
        ])
        return command
    if provider in CLAUDE_PROVIDERS:
        if getattr(args, "image", None):
            raise ValueError("image inputs require the codex provider")
        command = [
            executable, "--model", model, "--no-session-persistence",
            "--output-format", "json",
        ]
        if args.task_class in TOOLLESS_TASK_CLASSES:
            command.extend(["--tools", ""])
        command.append("-p")
        if not prompt_via_stdin:
            command.append(prompt)
        return command
    if provider == "openclaw":
        if prompt_via_stdin:
            raise ValueError("openclaw does not support stdin-only prompt transport")
        agent = candidate.get("agent", provider_config.get("agent"))
        if not isinstance(agent, str) or not agent:
            raise ValueError("openclaw provider requires a non-empty agent config")
        if not session_id:
            raise ValueError("openclaw provider requires a unique session id")
        thinking = candidate.get("thinking", "off")
        if not isinstance(thinking, str) or thinking not in OPENCLAW_THINKING_VALUES:
            raise ValueError(
                "invalid openclaw thinking; expected one of: "
                + ", ".join(sorted(OPENCLAW_THINKING_VALUES))
            )
        return [
            executable, "agent",
            "--session-id", session_id,
            "--agent", agent,
            "--model", model,
            "--thinking", thinking,
            "--timeout", str(timeout_seconds),
            "--message", openclaw_prompt(
                prompt, schema, openclaw_workdir or args.workdir,
                args.workdir if openclaw_workdir else None,
            ),
            "--json",
        ]
    if provider == "hermes":
        profile = candidate.get("profile")
        if not isinstance(profile, str) or not profile.strip():
            raise ValueError("hermes provider requires a non-empty profile")
        inference_provider = candidate.get("inference_provider")
        if not isinstance(inference_provider, str) or not inference_provider.strip():
            raise ValueError("hermes provider requires a non-empty inference provider")
        toolsets = candidate.get("toolsets")
        if (
            not isinstance(toolsets, list)
            or not toolsets
            or not all(isinstance(toolset, str) and toolset.strip() for toolset in toolsets)
        ):
            raise ValueError("hermes provider requires non-empty toolsets")
        return [
            executable,
            "--profile",
            profile,
            "--provider",
            inference_provider,
            "--model",
            model,
            "--toolsets",
            ",".join(toolsets),
            "--in",
            str(args.workdir),
            "--ignore-rules",
            "-z",
            hermes_prompt(prompt, schema),
        ]
    raise ValueError(f"unsupported provider adapter: {provider}")


def classify_provider_error(rc: int, timed_out: bool, stdout: str, stderr: str, launch_error: str) -> str:
    """Classify failures for safe fallback. Only transient provider failures retry."""
    if timed_out or rc == 124:
        return "transient_timeout"
    # Claude prints quota/weekly-limit notices to stdout (with an empty
    # stderr), so both provider streams are part of the transient signal.
    text = f"{stdout}\n{stderr}\n{launch_error}".lower()
    if any(token in text for token in (
        "invalid credentials", "invalid api key", "invalid token",
        "permission denied", "insufficient permission", "forbidden", "unauthorized",
    )):
        return "validation_or_task_failure"
    if any(token in text for token in (
        "oauth session expired", "authentication session expired", "auth session expired",
        "oauth token expired", "authentication token expired", "access token expired",
        "access token has expired", "session token expired", "session token has expired",
        "oauth token refresh failed", "auth token refresh failed", "token refresh failed",
        "failed to refresh oauth", "failed to refresh auth", "failed to refresh token",
        "could not refresh oauth", "could not refresh auth", "could not refresh token",
    )):
        return "transient_auth"
    if any(token in text for token in (
        "quota", "429", "rate limit", "rate_limit", "usage limit", "usage_limit",
        "weekly limit", "weekly_limit", "resets jul",
        "temporarily unavailable", "overloaded",
    )):
        return "transient_quota"
    if rc == 127 or launch_error:
        return "transient_unavailable"
    return "validation_or_task_failure"


def run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-class", required=True,
                        choices=("deterministic", "composition-agent", "reply-semantic-agent", "storefront-proposal-agent", "application-intent-planner", "repeatable-agent", "tool-agent", "browser-lane-agent", "application-lane-agent", "diagnostic-agent", "marketing-agent", "high-value-agent", "escalation-agent", "self-fix"))
    prompt_source = parser.add_mutually_exclusive_group(required=True)
    prompt_source.add_argument("--prompt-file", type=Path)
    prompt_source.add_argument("--prompt-stdin", action="store_true")
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--task-label", required=True)
    parser.add_argument("--loop", default="unattributed")
    parser.add_argument("--workdir", type=Path, default=Path.home())
    parser.add_argument("--candidate-profile")
    parser.add_argument("--candidate-model")
    parser.add_argument("--escalation-reason")
    parser.add_argument("--timeout-seconds", type=int)
    parser.add_argument("--image", action="append", type=Path, default=[])
    parser.add_argument("--read-only", action="store_true")
    parsed = parser.parse_args()

    if parsed.task_class in ("composition-agent", "reply-semantic-agent", "storefront-proposal-agent", "application-intent-planner") and not parsed.prompt_stdin:
        parser.error(f"{parsed.task_class} requires --prompt-stdin")

    config_path = Path(os.environ.get("AGENT_RUNNER_CONFIG", HERE / "config.json"))
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        schema = json.loads(parsed.schema.read_text(encoding="utf-8"))
        if any(path.is_symlink() or not path.is_file() for path in parsed.image):
            raise ValueError("image input must be an existing regular file")
        prompt = sys.stdin.read() if parsed.prompt_stdin else parsed.prompt_file.read_text(encoding="utf-8")
        resolver = HERE.parents[3] / "skills" / "_shared" / "resource_resolver.py"
        if resolver.is_file():
            manifest = subprocess.run(
                [sys.executable, str(resolver), "manifest"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
            prompt = (
                "Life Manager shared capability manifest (non-secret; available to every loop owner): "
                f"{manifest}\n"
                "When this task needs an external skill, account, authenticated session, or credential, first run "
                f"python3 {resolver} resolve --service <service> --capability <action>. Reuse a returned resource "
                "before signup or reimplementation. Never print credential values; adapters read them by ref.\n\n"
                + prompt
            )
        # Fail closed before any provider process starts. Billing begins at
        # launch, not at a usable answer: capafy was charged $0.135 on both
        # 2026-07-26 and 2026-07-27 for a one-turn greeting. A prompt this
        # small cannot carry a bounded task, so paying to discover that is
        # pure waste and the guard must run before the launch, not after.
        min_prompt_chars = int(os.environ.get(
            "AGENT_RUNNER_MIN_PROMPT_CHARS", MIN_PROMPT_CHARS))
        stripped_prompt_chars = len(prompt.strip())
        if stripped_prompt_chars < min_prompt_chars:
            raise ValueError(
                f"prompt is empty or too small to carry a task "
                f"({stripped_prompt_chars} chars < {min_prompt_chars}); "
                "refusing to launch a paid provider"
            )
        task_config = config["task_classes"][parsed.task_class]
        candidates = expand_codex_candidates(
            task_config["candidates"], config.get("providers", {})
        )
        for candidate in candidates:
            if not isinstance(candidate, dict) or "timeout_seconds" not in candidate:
                continue
            candidate_timeout = candidate["timeout_seconds"]
            if (
                not isinstance(candidate_timeout, int)
                or isinstance(candidate_timeout, bool)
                or candidate_timeout <= 0
            ):
                raise ValueError("candidate timeout_seconds must be a positive integer")
        for value, reason in ((parsed.loop, "loop"), (parsed.task_label, "task label")):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"{reason} must be a nonempty trimmed string")
        selected_provider = os.environ.get("AGENT_RUNNER_PROVIDER", "").strip()
        if selected_provider:
            if selected_provider not in config.get("providers", {}):
                raise ValueError("selected provider is not configured")
            candidates = [
                candidate for candidate in candidates
                if candidate.get("provider") == selected_provider
            ]
            if not candidates:
                raise ValueError("selected provider is not a candidate for task class")
        preferred_provider = os.environ.get("AGENT_RUNNER_PROVIDER_PREFERENCE", "").strip()
        if preferred_provider and not selected_provider:
            preferred = [
                candidate for candidate in candidates
                if candidate.get("provider") == preferred_provider
            ]
            if preferred:
                candidates = preferred + [
                    candidate for candidate in candidates
                    if candidate.get("provider") != preferred_provider
                ]
        selected_model = str(parsed.candidate_model or "").strip()
        if selected_model:
            candidates = [
                candidate for candidate in candidates
                if candidate.get("model") == selected_model
            ]
            if not candidates:
                raise ValueError("selected model is not a candidate for task class")
        if any(
            not isinstance(candidate, dict)
            or not isinstance(candidate.get("provider"), str)
            or not candidate["provider"].strip()
            or candidate["provider"] != candidate["provider"].strip()
            or not isinstance(candidate.get("model"), str)
            or not candidate["model"].strip()
            or candidate["model"] != candidate["model"].strip()
            for candidate in candidates
        ):
            raise ValueError("candidate provider/model must be nonempty trimmed strings")
        configured_timeout_seconds = int(
            task_config.get("timeout_seconds", config["timeout_seconds"])
        )
        if configured_timeout_seconds < 1:
            raise ValueError("configured timeout must be positive")
        if parsed.timeout_seconds is not None and parsed.timeout_seconds < 1:
            raise ValueError("explicit timeout must be positive")
        timeout_seconds = min(
            configured_timeout_seconds,
            parsed.timeout_seconds
            if parsed.timeout_seconds is not None
            else configured_timeout_seconds,
        )
        route = str(task_config.get("route") or f"{parsed.task_class}:configured")
        escalation_reason = (
            parsed.escalation_reason.strip()
            if isinstance(parsed.escalation_reason, str) and parsed.escalation_reason.strip()
            else None
        )
        restricted_candidates = [
            candidate for candidate in candidates
            if candidate.get("effort") == "high"
            or "sol" in str(candidate.get("model") or "").lower()
        ]
        requires_explicit_escalation = bool(
            task_config.get("requires_explicit_escalation")
        )
        if restricted_candidates and not requires_explicit_escalation:
            raise ValueError("high-effort/Sol candidates require an explicit escalation route")
        if requires_explicit_escalation and escalation_reason is None:
            raise ValueError("explicit escalation reason is required")
        if not requires_explicit_escalation and escalation_reason is not None:
            raise ValueError("escalation reason is only valid for an explicit escalation route")
        budget_scope_id = os.environ.get("ANICCA_BUDGET_SCOPE_ID", "").strip()
        pass_budget_raw = os.environ.get("ANICCA_PASS_TOKEN_BUDGET", "").strip()
        daily_budget_raw = os.environ.get("ANICCA_LOOP_DAILY_TOKEN_BUDGET", "").strip()
        budget_values_present = tuple(bool(value) for value in (
            budget_scope_id, pass_budget_raw, daily_budget_raw,
        ))
        if any(budget_values_present) and not all(budget_values_present):
            raise ValueError("token budget scope/pass/daily settings must be provided together")
        budget_enabled = all(budget_values_present)
        # Fail closed. An unconfigured budget used to degrade silently to no
        # breaker at all, which is how the reply detector ran 47 uncharged model
        # calls. Owners that are meant to be budgeted set this and refuse to run
        # rather than run unbounded.
        if os.environ.get("ANICCA_BUDGET_REQUIRED", "").strip() == "1" and not budget_enabled:
            raise ValueError(
                "token budget is required but scope/pass/daily settings are missing"
            )
        # The daily pool belongs to one caller (one LaunchAgent), not to the
        # whole loop. Defaults to the loop, so callers that do not name an owner
        # keep their previous behaviour.
        budget_daily_scope = (
            os.environ.get("ANICCA_BUDGET_DAILY_SCOPE", "").strip() or parsed.loop
        )
        token_reservation = int(task_config.get("token_reservation", 0))
        pass_token_budget = int(pass_budget_raw or 0)
        daily_token_budget = int(daily_budget_raw or 0)
        if budget_enabled and (
            token_reservation <= 0 or pass_token_budget <= 0 or daily_token_budget <= 0
        ):
            raise ValueError("enabled token budgets and task reservation must be positive")
        usage_value = os.environ.get("ANICCA_USAGE_LEDGER", "").strip() or str(DEFAULT_USAGE_LEDGER)
        usage_path = Path(usage_value).expanduser().resolve()
        attempt_value = os.environ.get("ANICCA_USAGE_ATTEMPT_LEDGER", "").strip() or str(usage_path.with_name("agent-usage-attempts.jsonl"))
        attempt_ledger_path = Path(attempt_value).expanduser().resolve()
        if usage_path == attempt_ledger_path:
            raise ValueError("usage and attempt ledgers must differ")
        budget_ledger = TokenBudgetLedger(Path(os.environ.get(
            "ANICCA_TOKEN_BUDGET_LEDGER",
            Path.home() / ".local" / "state" / "anicca" / "telemetry" / "token-budget.jsonl",
        )))
        budget_day = budget_day_for(
            datetime.now(timezone.utc),
            os.environ.get("ANICCA_BUDGET_DAY_TZ", "").strip() or "Asia/Tokyo",
        )
        candidate_profile: dict[str, Any] = {}
        if parsed.candidate_profile:
            candidate_profile = config.get("candidate_profiles", {}).get(parsed.candidate_profile)
            if not isinstance(candidate_profile, dict):
                raise ValueError(f"candidate profile not configured: {parsed.candidate_profile}")
            if candidate_profile.get("task_class") != parsed.task_class:
                raise ValueError("candidate profile task_class mismatch")
    except Exception as error:
        print(f"agent-runner: invalid input/config: {error}", file=sys.stderr)
        return 2
    if parsed.task_class == "deterministic" or not candidates:
        print("agent-runner: deterministic tasks have no model candidate", file=sys.stderr)
        return 2

    evidence_dir = parsed.evidence_dir.resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    attempts_path = evidence_dir / "attempts.jsonl"
    summary_path = evidence_dir / "summary.json"
    # Keep the stable latest paths expected by existing consumers, but never erase a
    # previous wake: later owners need its official-effect trail for durable resume.
    previous = [path for path in evidence_dir.glob("attempt-*.*") if path.is_file()]
    previous += [path for path in (attempts_path, summary_path) if path.is_file()]
    if previous:
        history = evidence_dir / "history" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                                                + "-" + uuid.uuid4().hex[:8])
        history.mkdir(parents=True, exist_ok=False)
        for path in previous:
            os.replace(path, history / path.name)
        try:
            keep_history = int(os.environ.get("AGENT_RUNNER_HISTORY_GENERATIONS", DEFAULT_HISTORY_GENERATIONS))
        except ValueError:
            keep_history = DEFAULT_HISTORY_GENERATIONS
        prune_history_generations(history.parent, keep=max(1, keep_history))
    # A prior result still cannot satisfy the current run because its stable latest
    # paths have moved out of the active directory before provider launch.
    attempts_path.unlink(missing_ok=True)
    summary_path.unlink(missing_ok=True)
    started_at = utc_now()
    attempts: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    budget_blocked: dict[str, Any] | None = None
    attempt_capture_failed = False
    last_budget: dict[str, Any] = {
        "status": "disabled",
        "reason": "budget_not_configured",
        "scope_id": budget_scope_id or None,
    }
    total_deadline = time.monotonic() + timeout_seconds
    skip_remaining_codex_accounts = False

    for index, candidate in enumerate(candidates, 1):
        remaining_timeout = total_deadline - time.monotonic()
        remaining_timeout_seconds = math.floor(remaining_timeout)
        if remaining_timeout_seconds < 1:
            break
        effective_candidate = dict(candidate)
        provider = effective_candidate["provider"]
        if (
            skip_remaining_codex_accounts
            and provider == "codex"
            and effective_candidate.get("account")
        ):
            continue
        if provider != "codex":
            skip_remaining_codex_accounts = False
        proxy_timeout = os.environ.get("AGENT_RUNNER_PROXY_TIMEOUT_SECONDS", "").strip()
        if (
            provider == "claude-direct"
            and effective_candidate.get("model") == "gpt-5.3-codex-spark"
            and proxy_timeout
        ):
            try:
                proxy_timeout_seconds = int(proxy_timeout)
            except ValueError:
                proxy_timeout_seconds = 0
            if proxy_timeout_seconds > 0:
                effective_candidate["timeout_seconds"] = proxy_timeout_seconds
        candidate_timeout_seconds = effective_candidate.get(
            "timeout_seconds", remaining_timeout_seconds,
        )
        attempt_timeout_seconds = min(
            remaining_timeout_seconds, candidate_timeout_seconds,
        )
        budget_event_id = f"agent-budget-{uuid.uuid4().hex}"
        if budget_enabled:
            last_budget = budget_ledger.reserve(
                event_id=budget_event_id,
                loop=parsed.loop,
                scope_id=budget_scope_id,
                daily_scope=budget_daily_scope,
                day=budget_day,
                reservation_tokens=token_reservation,
                pass_limit=pass_token_budget,
                daily_limit=daily_token_budget,
            )
            if last_budget["status"] == "blocked":
                # Exhaustion stops everything for this owner, including the
                # revenue lane. Deliberate: the daily limit is set ~3x above
                # measured peak spend, so tripping it means a runaway, and the
                # revenue lane is the highest-token lane -- exempting it would
                # exempt the exact thing that runs away. A tripped breaker is a
                # page for a human, not a lane to route around. Per-pass limits
                # stay in place so one bad pass dies without burning the day.
                budget_blocked = last_budget
                break
        attempt_event_id = uuid.uuid4().hex[:24]
        attempt_started = utc_now()
        try:
            append_usage_event(attempt_ledger_path, {"version": 1, "event_id": attempt_event_id, "timestamp": attempt_started, "loop": parsed.loop, "task_label": parsed.task_label, "attempt": index, "provider": provider, "model": effective_candidate.get("model")})
        except OSError:
            if budget_enabled:
                settlement = budget_ledger.settle(event_id=budget_event_id, actual_tokens=0, measurement="unavailable")
                last_budget.update(charged_tokens=0, measurement="unavailable", pass_consumed_after_tokens=settlement["pass_consumed_after_tokens"], daily_consumed_after_tokens=settlement["daily_consumed_after_tokens"])
            attempt_capture_failed = True
            break
        provider_config = dict(config.get("providers", {}).get(provider, {}))
        for key in ("account", "automation_home", "auth_file"):
            if key in effective_candidate:
                provider_config[key] = effective_candidate[key]
        profile_openclaw: dict[str, Any] = {}
        if provider == "openclaw" and candidate_profile:
            value = candidate_profile.get("openclaw", {})
            profile_openclaw = value if isinstance(value, dict) else {}
            if profile_openclaw.get("agent"):
                effective_candidate["agent"] = profile_openclaw["agent"]
        executable = resolve_executable(provider_config, provider)
        stdout_path = evidence_dir / f"attempt-{index:02d}.stdout.log"
        stderr_path = evidence_dir / f"attempt-{index:02d}.stderr.log"
        result_path = evidence_dir / f"attempt-{index:02d}.result.json"
        for stale_path in (stdout_path, stderr_path, result_path):
            stale_path.unlink(missing_ok=True)
        attempt_started_ns = time.time_ns()
        monotonic_start = time.monotonic()
        session_id = f"agent-runner-{uuid.uuid4().hex}" if provider == "openclaw" else None
        rc = 127
        timed_out = False
        launch_error = ""
        adapter_error = ""
        required_capabilities: list[str] = []
        model_capabilities: dict[str, Any] = {}
        runtime_capabilities: dict[str, Any] = {}
        sandbox_preflight: dict[str, Any] = {}
        candidate_prompt = prompt
        openclaw_workdir: str | None = None
        try:
            required_capabilities, model_capabilities = candidate_capabilities(provider_config, effective_candidate)
            if provider in CLAUDE_PROVIDERS:
                candidate_prompt = strict_output_contract(
                    prompt, schema, parsed.workdir,
                    has_tools=parsed.task_class not in TOOLLESS_TASK_CLASSES,
                )
            if provider == "openclaw" and profile_openclaw:
                required_sandbox = profile_openclaw.get("sandbox")
                agent = effective_candidate.get("agent", provider_config.get("agent"))
                if not isinstance(agent, str) or not agent:
                    raise ValueError("openclaw candidate profile requires agent")
                if not isinstance(required_sandbox, dict):
                    raise ValueError("openclaw candidate profile requires sandbox contract")
                sandbox_preflight, sandbox_error = openclaw_sandbox_preflight(
                    executable, agent, required_sandbox, parsed.workdir,
                )
                if sandbox_error:
                    raise ValueError(f"openclaw paid sandbox preflight failed: {sandbox_error}")
                openclaw_workdir = sandbox_preflight["sandbox_project_root"]
            command = command_for(
                provider, executable, provider_config, effective_candidate, parsed, candidate_prompt,
                schema, result_path, attempt_timeout_seconds, session_id, openclaw_workdir,
                prompt_via_stdin=parsed.prompt_stdin,
            )
            with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                try:
                    rc = run_provider_process(
                        command,
                        stdout=stdout,
                        stderr=stderr,
                        timeout=attempt_timeout_seconds,
                        cwd=parsed.workdir,
                        # candidate_prompt, not prompt: the stdin path bypassed
                        # every per-candidate adjustment, so a contract added for
                        # one provider silently did nothing whenever the prompt
                        # travelled over stdin.
                        input_bytes=candidate_prompt.encode("utf-8") if parsed.prompt_stdin else None,
                        stdin=None if parsed.prompt_stdin else subprocess.DEVNULL,
                        env=provider_process_env(
                            provider,
                            provider_config,
                            task_class=parsed.task_class,
                            evidence_dir=evidence_dir,
                        ),
                    )
                except subprocess.TimeoutExpired:
                    timed_out = True
                    rc = 124
                except OSError as error:
                    launch_error = str(error)
                    stderr.write((launch_error + "\n").encode())
                    rc = 127
        except Exception as error:
            adapter_error = str(error)
            rc = 2
            stdout_path.touch()
            stderr_path.write_text(adapter_error + "\n", encoding="utf-8")

        if rc == 0 and not timed_out and provider in CLAUDE_PROVIDERS and not result_path.exists():
            adapter_error = extract_claude_payload(stdout_path, result_path)
        if rc == 0 and not timed_out and provider == "hermes":
            adapter_error = extract_hermes_payload(stdout_path, result_path)
        if rc == 0 and not timed_out and provider == "openclaw":
            adapter_error, runtime_capabilities = extract_openclaw_payload(
                stdout_path, result_path, required_capabilities,
            )
        result_fresh = result_path.is_file() and result_path.stat().st_mtime_ns >= attempt_started_ns
        schema_valid = False
        schema_errors: list[str] = []
        # The result artifact is the completion contract, not the provider CLI's
        # willingness to exit.  Production LEARN pass 1785304094-88563 had already
        # appended three durable lessons and written a complete schema-valid result,
        # then Codex remained alive until the outer 90-second timeout.  Rejecting that
        # artifact retried the same append-only work on Claude.  A fresh file that
        # independently parses and validates is safe to accept; a partial/stale file
        # still fails this gate exactly as before.
        if result_fresh:
            try:
                result = parse_contract_result(
                    result_path.read_text(encoding="utf-8"),
                    salvage=provider not in {"openclaw", "hermes"},
                )
                schema_errors = validate_schema(result, schema)
                schema_valid = not schema_errors
            except Exception as error:
                schema_errors = [f"result parse failed: {error}"]
        elif not result_fresh:
            schema_errors = ["provider did not produce a fresh result for this attempt"]

        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        usage = extract_provider_usage(provider, stdout_text, model=effective_candidate.get("model"))
        if budget_enabled:
            charged_tokens = budget_charge_tokens(
                provider,
                usage,
                token_reservation,
            )
            settlement = budget_ledger.settle(
                event_id=budget_event_id,
                actual_tokens=charged_tokens,
                measurement=str(usage["measurement"]),
            )
            last_budget = {
                **last_budget,
                "charged_tokens": charged_tokens,
                "measurement": usage["measurement"],
                "pass_consumed_after_tokens": settlement["pass_consumed_after_tokens"],
                "daily_consumed_after_tokens": settlement["daily_consumed_after_tokens"],
            }
        contract_complete = result_fresh and schema_valid
        error_class = None if contract_complete else classify_provider_error(
            rc, timed_out, stdout_text, stderr_text, launch_error,
        )

        row = {
            "event_id": attempt_event_id,
            "attempt": index,
            "started_at": attempt_started,
            "finished_at": utc_now(),
            "duration_ms": round((time.monotonic() - monotonic_start) * 1000),
            "task_label": parsed.task_label,
            "task_class": parsed.task_class,
            "route": route,
            "escalated": requires_explicit_escalation,
            "escalation_reason": escalation_reason,
            "budget": last_budget,
            "provider": provider,
            "account": provider_config.get("account"),
            "model": effective_candidate.get("model"),
            "effort": effective_candidate.get("effort"),
            "thinking": effective_candidate.get("thinking", "off") if provider == "openclaw" else None,
            "required_capabilities": required_capabilities,
            "model_capabilities": model_capabilities,
            "runtime_capabilities": runtime_capabilities,
            "sandbox_preflight": sandbox_preflight,
            "executable": executable,
            "session_id": session_id,
            "rc": rc,
            "timed_out": timed_out,
            "stdout_path": str(stdout_path),
            "stdout_sha256": sha256_file(stdout_path),
            "stderr_path": str(stderr_path),
            "stderr_sha256": sha256_file(stderr_path),
            "result_path": str(result_path),
            "result_present": result_fresh,
            "schema_path": str(parsed.schema.resolve()),
            "schema_valid": schema_valid,
            "schema_errors": schema_errors,
            "launch_error": launch_error or None,
            "adapter_error": adapter_error or None,
            "error_class": error_class,
            "capabilities": provider_config.get("capabilities", {}),
            "cost_tier": provider_config.get("cost_tier"),
            "quota": provider_config.get("quota"),
            "usage": usage,
        }
        provider_name = usage.get("upstream_provider") or provider_config.get("provider_name") or {
            "codex": "openai", "claude": "anthropic",
            "claude-direct": "anthropic",
        }.get(provider, provider)
        usage_event = {
            "version": 1,
            "event_id": attempt_event_id,
            "timestamp": row["finished_at"],
            "loop": parsed.loop,
            "task_label": parsed.task_label,
            "task_class": parsed.task_class,
            "route": route,
            "escalated": requires_explicit_escalation,
            "escalation_reason": escalation_reason,
            "budget": last_budget,
            "attempt": index,
            "provider": provider,
            "account": provider_config.get("account"),
            "provider_name": provider_name,
            "model": effective_candidate.get("model"),
            "upstream_model": usage.get("upstream_model"),
            "effort": effective_candidate.get("effort"),
            "status": "success" if contract_complete else "failed",
            "error_class": error_class,
            "duration_ms": row["duration_ms"],
            "measurement": usage["measurement"],
            "tokens": {
                "input": usage["input_tokens"],
                "cached_input": usage["cached_input_tokens"],
                "cache_creation_input": usage["cache_creation_input_tokens"],
                "output": usage["output_tokens"],
                "reasoning_output": usage["reasoning_output_tokens"],
                "total": usage["total_tokens"],
            },
            "provider_cost_usd": usage["provider_cost_usd"],
            "cost_basis": usage["cost_basis"],
            "gen_ai": {
                "operation_name": "invoke_agent",
                "provider_name": provider_name,
                "request_model": effective_candidate.get("model"),
            },
        }
        try:
            append_usage_event(usage_path, usage_event)
        except OSError as error:
            row["telemetry_error"] = str(error)
        with attempts_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        attempts.append(row)
        if contract_complete:
            selected = row
            break
        # A valid response with a schema/contract error is deterministic and
        # must not silently switch providers. Fallback is only for transient
        # timeout, expired provider auth, provider availability, or quota failures.
        if rc == 0 and result_fresh and not schema_valid:
            break
        if provider == "codex" and effective_candidate.get("account"):
            effect_started = codex_effect_started(stdout_text)
            if should_retry_next_codex_account(error_class, effect_started):
                if effective_candidate["account_index"] + 1 >= effective_candidate["account_count"]:
                    skip_remaining_codex_accounts = True
                continue
            if error_class in ("transient_timeout", "transient_unavailable"):
                skip_remaining_codex_accounts = True
                continue
            break
        if error_class not in (
            "transient_timeout", "transient_quota", "transient_unavailable", "transient_auth",
        ):
            break

    summary = {
        "version": 1,
        "started_at": started_at,
        "finished_at": utc_now(),
        "task_label": parsed.task_label,
        "loop": parsed.loop,
        "task_class": parsed.task_class,
        "route": route,
        "escalated": requires_explicit_escalation,
        "escalation_reason": escalation_reason,
        "status": "success" if selected else ("budget_blocked" if budget_blocked else "failed"),
        "budget": budget_blocked or last_budget,
        "selected_provider": selected["provider"] if selected else None,
        "selected_model": selected["model"] if selected else None,
        "selected_effort": selected["effort"] if selected else None,
        "attempt_count": len(attempts),
        "attempts_path": str(attempts_path),
        "result_path": selected["result_path"] if selected else None,
    }
    atomic_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    if selected:
        return 0
    if attempt_capture_failed:
        print("agent-runner: usage attempt capture failed", file=sys.stderr)
    return 75 if budget_blocked else 1


if __name__ == "__main__":
    install_termination_forwarding()
    raise SystemExit(run())
