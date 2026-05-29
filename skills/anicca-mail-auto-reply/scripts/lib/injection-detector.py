"""FR-015 - Prompt-injection fail-CLOSED detector.

Source: agentic-inbox/workers/lib/ai.ts:52-58 - `isPromptInjection` catches any
exception and returns `true`. We mirror that posture: any internal error returns
True (= treat as injection, hard-block upstream).

Public API:
    is_injection(text: str | None) -> bool

CLI usage:
    echo "<input>" | python3 injection-detector.py
    # prints 'INJECTION' or 'OK' to stdout
"""
from __future__ import annotations
import re
import sys

PATTERNS = [
    re.compile(r"ignore (?:all |the )?previous instructions?", re.IGNORECASE),
    re.compile(r"forget (?:all |the )?(?:earlier|previous) (?:instructions?|messages?)", re.IGNORECASE),
    re.compile(r"as the (?:system|root|admin(?:istrator)?)\b", re.IGNORECASE),
    re.compile(r"disclose (?:your |the )?(?:private key|api[- ]?key|password|secret)", re.IGNORECASE),
    re.compile(r"forward (?:all|copies?|every)\b.*to\s+\S+@\S+", re.IGNORECASE),
    re.compile(r"</?(?:system|sysprompt|instruction)>", re.IGNORECASE),
]


def is_injection(text) -> bool:
    """Fail-CLOSED: any internal failure returns True (= treat as injection)."""
    try:
        if text is None:
            return True
        if not isinstance(text, str):
            return True
        if text == "":
            return False
        for p in PATTERNS:
            if p.search(text):
                return True
        return False
    except Exception:
        return True


def _main() -> int:
    try:
        body = sys.stdin.read()
    except Exception:
        # I/O error -> fail-CLOSED
        print("INJECTION")
        return 0
    print("INJECTION" if is_injection(body) else "OK")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
