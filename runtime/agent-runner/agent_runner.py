#!/usr/bin/env python3
"""Bounded provider-agnostic agent runner with durable per-attempt evidence."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
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
DEFAULT_USAGE_LEDGER = Path.home() / ".local" / "state" / "life-manager" / "telemetry" / "agent-usage.jsonl"
CLAUDE_PROVIDERS = {"claude", "claude-direct"}
# Smallest prompt that could plausibly express a bounded task. Kept low on
# purpose: this is a floor against empty/degenerate transport, not a style
# rule. Callers that legitimately want a stricter floor set
# AGENT_RUNNER_MIN_PROMPT_CHARS (run_agent.sh does, for loop prompts).
MIN_PROMPT_CHARS = 16

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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
                "provider_cost_usd": float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None,
                # Claude CLI exposes an API-price equivalent even when OAuth/subscription is
                # paying the actual bill. It is useful telemetry, but not actual marginal cost.
                "cost_basis": "api_equivalent_estimate" if isinstance(cost, (int, float)) and not isinstance(cost, bool) else "unavailable",
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
            usage.update({
                "measurement": "provider_reported",
                "input_tokens": input_tokens,
                "cached_input_tokens": _token(raw.get("cacheRead")) or 0,
                "cache_creation_input_tokens": _token(raw.get("cacheWrite")) or 0,
                "output_tokens": output_tokens,
                "reasoning_output_tokens": 0,
                "total_tokens": _token(raw.get("total")) or input_tokens + output_tokens,
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


def append_usage_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    """Terminate a timed-out provider and every child in its process group."""
    if os.name == "posix":
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
    else:
        process.kill()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def provider_process_env(provider: str, provider_config: dict[str, Any],
                         environ: dict[str, str] | None = None) -> dict[str, str]:
    """Build a provider-scoped, non-interactive child environment."""
    child_env = dict(os.environ if environ is None else environ)
    if provider == "codex":
        automation_home_value = provider_config.get("automation_home")
        if not automation_home_value:
            return child_env
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

        if child_env.get("OPENAI_API_KEY"):
            return child_env
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
        return child_env
    if provider not in CLAUDE_PROVIDERS:
        return child_env
    if provider == "claude-direct":
        for name in (
            "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN",
        ):
            child_env.pop(name, None)
        return child_env
    if any(child_env.get(name) for name in (
        "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN",
    )):
        return child_env

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
    return child_env


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
    """Unwrap only one whole-string json fence after proven runtime mutation."""
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
        if args.task_class in ("composition-agent", "diagnostic-agent"):
            command.extend(["--sandbox", "read-only"])
        else:
            command.append("--dangerously-bypass-approvals-and-sandbox")
        command.extend([
            "--skip-git-repo-check", "-C", str(args.workdir),
            "-" if prompt_via_stdin else prompt,
        ])
        return command
    if provider in CLAUDE_PROVIDERS:
        command = [
            executable, "--model", model, "--no-session-persistence",
            "--output-format", "json",
        ]
        if args.task_class in ("composition-agent", "diagnostic-agent"):
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
                        choices=("deterministic", "composition-agent", "repeatable-agent", "tool-agent", "browser-lane-agent", "application-lane-agent", "diagnostic-agent", "marketing-agent", "high-value-agent", "escalation-agent"))
    prompt_source = parser.add_mutually_exclusive_group(required=True)
    prompt_source.add_argument("--prompt-file", type=Path)
    prompt_source.add_argument("--prompt-stdin", action="store_true")
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--task-label", required=True)
    parser.add_argument("--loop", default="unattributed")
    parser.add_argument("--workdir", type=Path, default=Path.home())
    parser.add_argument("--candidate-profile")
    parser.add_argument("--escalation-reason")
    parsed = parser.parse_args()

    if parsed.task_class == "composition-agent" and not parsed.prompt_stdin:
        parser.error("composition-agent requires --prompt-stdin")

    config_path = Path(os.environ.get("AGENT_RUNNER_CONFIG", HERE / "config.json"))
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        schema = json.loads(parsed.schema.read_text(encoding="utf-8"))
        prompt = sys.stdin.read() if parsed.prompt_stdin else parsed.prompt_file.read_text(encoding="utf-8")
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
        candidates = task_config["candidates"]
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
        timeout_seconds = int(task_config.get("timeout_seconds", config["timeout_seconds"]))
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
        task_token_reservation = int(task_config.get("token_reservation", 0))
        pass_token_budget = int(pass_budget_raw or 0)
        daily_token_budget = int(daily_budget_raw or 0)
        if budget_enabled and (
            task_token_reservation <= 0
            or pass_token_budget <= 0
            or daily_token_budget <= 0
        ):
            raise ValueError("enabled token budgets and task reservation must be positive")
        # Admission must reserve an upper bound, not the task class's planning
        # estimate. Settlement replaces this hold with provider-reported usage,
        # but a provider may already have spent far more than the estimate by
        # then. Reserving the whole pass allowance prevents that observed
        # estimate-to-settlement gap from crossing the daily cap.
        token_reservation = (
            pass_token_budget if budget_enabled else task_token_reservation
        )
        budget_ledger = TokenBudgetLedger(Path(os.environ.get(
            "ANICCA_TOKEN_BUDGET_LEDGER",
            Path.home() / ".local" / "state" / "life-manager" / "telemetry" / "token-budget.jsonl",
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
    # An evidence directory is one logical run. Reusing it must never let a
    # prior result/attempt/summary satisfy the current run.
    attempts_path.unlink(missing_ok=True)
    summary_path.unlink(missing_ok=True)
    started_at = utc_now()
    attempts: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    budget_blocked: dict[str, Any] | None = None
    last_budget: dict[str, Any] = {
        "status": "disabled",
        "reason": "budget_not_configured",
        "scope_id": budget_scope_id or None,
    }

    for index, candidate in enumerate(candidates, 1):
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
        effective_candidate = dict(candidate)
        provider = effective_candidate["provider"]
        provider_config = config.get("providers", {}).get(provider, {})
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
        attempt_started = utc_now()
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
                schema, result_path, timeout_seconds, session_id, openclaw_workdir,
                prompt_via_stdin=parsed.prompt_stdin,
            )
            with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                try:
                    rc = run_provider_process(
                        command,
                        stdout=stdout,
                        stderr=stderr,
                        timeout=timeout_seconds,
                        cwd=parsed.workdir,
                        input_bytes=prompt.encode("utf-8") if parsed.prompt_stdin else None,
                        stdin=None if parsed.prompt_stdin else subprocess.DEVNULL,
                        env=provider_process_env(provider, provider_config),
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
        if rc == 0 and not timed_out and provider == "openclaw":
            adapter_error, runtime_capabilities = extract_openclaw_payload(
                stdout_path, result_path, required_capabilities,
            )
        result_fresh = result_path.is_file() and result_path.stat().st_mtime_ns >= attempt_started_ns
        schema_valid = False
        schema_errors: list[str] = []
        if rc == 0 and not timed_out and result_fresh:
            try:
                result = parse_contract_result(
                    result_path.read_text(encoding="utf-8"),
                    salvage=provider != "openclaw",
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
        error_class = None if (rc == 0 and schema_valid) else classify_provider_error(
            rc, timed_out, stdout_text, stderr_text, launch_error,
        )

        row = {
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
        usage_path = Path(os.environ.get("ANICCA_USAGE_LEDGER", DEFAULT_USAGE_LEDGER))
        provider_name = usage.get("upstream_provider") or {
            "codex": "openai", "claude": "anthropic",
            "claude-direct": "anthropic",
        }.get(provider, provider)
        usage_event = {
            "version": 1,
            "event_id": hashlib.sha256(
                f"{evidence_dir}:{index}".encode("utf-8")
            ).hexdigest()[:24],
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
            "status": "success" if rc == 0 and schema_valid else "failed",
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
        if rc == 0 and schema_valid:
            selected = row
            break
        # A valid response with a schema/contract error is deterministic and
        # must not silently switch providers. Fallback is only for transient
        # timeout, expired provider auth, provider availability, or quota failures.
        if rc == 0 and result_fresh and not schema_valid:
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
    return 75 if budget_blocked else 1


if __name__ == "__main__":
    install_termination_forwarding()
    raise SystemExit(run())
