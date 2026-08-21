#!/usr/bin/env python3
"""Local Ollama draft writer; immutable ledger remains the acceptance gate."""
from __future__ import annotations

import json
import urllib.request


def draft(*, language: str, hook: str, pain_angle: str, teaching: str, action: str, cta: str,
          model: str = "qwen2.5:1.5b") -> dict:
    prompt = ("Return JSON only in this exact shape: {\"body\":\"...\"}. Preserve these exact components in this order: "
              f"hook={hook!r}; pain={pain_angle!r}; teaching={teaching!r}; action={action!r}; cta={cta!r}. "
              "Write an original short-video script. No medical, therapeutic, guaranteed, sleep, or anxiety claims. "
              f"Language={language}.")
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate",
        data=json.dumps({"model": model, "prompt": prompt, "format": "json", "stream": False}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.load(response)
    output = json.loads(payload["response"])
    body = output.get("body")
    if not isinstance(body, str) or not body.strip():
        raise ValueError("Ollama writer did not return body")
    return {"model": model, "body": body.strip(), "external_effects": []}
