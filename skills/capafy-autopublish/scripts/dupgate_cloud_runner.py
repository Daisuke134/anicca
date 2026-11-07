#!/usr/bin/env python3
"""dupgate_cloud_runner.py — claude-CLI-shaped model runner for tenant computers.

duplicate_gate.default_runner invokes CAPAFY_DUPGATE_CLAUDE_BIN with the
`claude` print-mode argv (`-p <prompt> --setting-sources "" --system-prompt
<s> --model haiku`), prints the model's reply on stdout, and treats a nonzero
exit as a runner error (the gate then fails closed as "unknown"). On a
founder host that binary is the real claude CLI. Inside a Maritime tenant
computer there is deliberately no Anthropic login — the tenant's only model
access is the platform-injected cloud route — so cloud_cycle.py points the
same env var at this script instead. It reads the route (base_url + model)
from the tenant's own AGENT_RUNNER_CONFIG (written by
apps/life-manager/maritime/runtime-env.js from the platform-injected
OPENAI_BASE_URL) and the key from LM_CLOUD_MODEL_API_KEY, then calls the
Responses API. The judgment itself is unchanged: same prompt in, same
one-line JSON out; only the transport differs.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

_VALUE_FLAGS = {"-p", "--system-prompt", "--model", "--setting-sources"}


def _parse_argv(argv: list[str]) -> dict:
    parsed: dict[str, str] = {}
    index = 0
    while index < len(argv):
        flag = argv[index]
        if flag in _VALUE_FLAGS and index + 1 < len(argv):
            parsed[flag] = argv[index + 1]
            index += 2
        else:
            index += 1
    return parsed


def _route(env: dict) -> tuple[str, str, str]:
    config = json.loads(Path(env["AGENT_RUNNER_CONFIG"]).read_text(encoding="utf-8"))
    provider = config["providers"]["codex"]
    providers = provider["model_providers"]
    route = providers[provider.get("model_provider") or next(iter(providers))]
    base = str(route["base_url"]).rstrip("/")
    key = env.get(route.get("env_key") or "LM_CLOUD_MODEL_API_KEY") or ""
    model = config["task_classes"]["application-lane-agent"]["candidates"][0]["model"]
    return base, key, str(model)


def _extract_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"]:
        return payload["output_text"]
    parts: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                parts.append(content["text"])
    return "".join(parts)


def run(argv: list[str], env: dict | None = None, opener=urllib.request.urlopen) -> tuple[int, str]:
    """Returns (exit_code, stdout_text). Any failure is a nonzero exit with
    empty stdout, mirroring a failed claude CLI invocation."""
    env = dict(os.environ if env is None else env)
    parsed = _parse_argv(list(argv))
    prompt = parsed.get("-p") or ""
    if not prompt:
        return 2, ""
    try:
        base, key, model = _route(env)
        if not key:
            return 1, ""
        body: dict = {"model": model, "input": prompt}
        if parsed.get("--system-prompt"):
            body["instructions"] = parsed["--system-prompt"]
        request = urllib.request.Request(
            base + "/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with opener(request, timeout=100) as response:
            payload = json.load(response)
    except Exception:  # noqa: BLE001 — every transport/config failure is a runner error
        return 1, ""
    text = _extract_text(payload)
    return (0, text) if text else (1, "")


def main() -> int:
    code, out = run(sys.argv[1:])
    if out:
        sys.stdout.write(out)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
