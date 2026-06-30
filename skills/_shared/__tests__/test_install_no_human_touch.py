"""PROP-D1 / PROP-NFR1 — static grep over install-proactive-plist sources.

Forbidden patterns covers:
- human-touch surfaces (osascript, terminal-notifier, telegram, slack, twilio,
  sudo, SecKeychain, find-generic-password, security add-generic-password)
- outbound URLs other than localhost
- duplicate PURE logic in the shell (= FIND-007 single-source enforcement)
"""
from __future__ import annotations
import re
from pathlib import Path
import pytest

SHARED_DIR = Path(__file__).resolve().parent.parent
INSTALL_SH = SHARED_DIR / "install-proactive-plist.sh"
PLIST_RENDER_PY = SHARED_DIR / "lib" / "plist_render.py"


HUMAN_TOUCH_PATTERNS = [
    r"\bosascript\b",
    r"\bterminal-notifier\b",
    r"telegram\.org",
    r"hooks\.slack\.com",
    r"\btwilio\b",
    r"\bsudo\b",
    r"\bSecKeychain\b",
    r"find-generic-password",
    r"security add-generic-password",
]

# Allow localhost; allow Apple plist DOCTYPE namespace marker
# (= http://www.apple.com/DTDs/PropertyList-1.0.dtd, a documented constant
# baked into EVERY macOS plist DOCTYPE — not an outbound fetch); flag everything else.
OUTBOUND_URL_RE = re.compile(
    r"https?://(?!"
    r"localhost|127\.0\.0\.1|0\.0\.0\.0"
    r"|www\.apple\.com/DTDs/"
    r")[\w.-]+"
)

# Keywords from lib.plist_render that the .sh MUST NOT re-implement (FIND-007).
DUPLICATE_KEYWORDS = [
    "validate_slot",
    "render_plist",
    "parse_loaded_plist_path",
    "plist_digest",
]


def _read(p: Path) -> str:
    if not p.exists():
        pytest.fail(f"required source missing: {p}")
    return p.read_text()


# ─── PROP-D1 — comprehensive human-touch ban ───────────────────────
@pytest.mark.parametrize("source_path", [INSTALL_SH, PLIST_RENDER_PY])
def test_no_human_touch_patterns(source_path):
    txt = _read(source_path)
    for pat in HUMAN_TOUCH_PATTERNS:
        m = re.search(pat, txt, flags=re.IGNORECASE)
        assert not m, f"forbidden human-touch pattern '{pat}' found in {source_path}: {m.group(0) if m else ''}"


@pytest.mark.parametrize("source_path", [INSTALL_SH, PLIST_RENDER_PY])
def test_no_outbound_urls(source_path):
    txt = _read(source_path)
    hits = OUTBOUND_URL_RE.findall(txt)
    assert hits == [], f"outbound URL(s) in {source_path}: {hits}"


# ─── PROP-NFR1 — single-source PURE (FIND-007 fix) ─────────────────
def test_shell_does_not_reimplement_pure_logic():
    txt = _read(INSTALL_SH)
    # The .sh may CALL `python3 -m lib.plist_render <kw>` (= acceptable usage)
    # but MUST NOT define a function with the same name.
    for kw in DUPLICATE_KEYWORDS:
        # Bash function definition signatures: `kw()` or `function kw`
        assert not re.search(rf"\b{kw}\s*\(\s*\)", txt), \
            f"shell defines duplicate PURE function: {kw}()"
        assert not re.search(rf"\bfunction\s+{kw}\b", txt), \
            f"shell defines duplicate PURE function: function {kw}"


# ─── REQ-D2 — no sudo / elevated privilege requests ───────────────
def test_no_elevated_privilege():
    # FIND-006 fix: word-boundary regex avoids matching 'pseudo' / 'sudo-less'
    # in comments; strip line comments first so a banning-comment doesn't trip
    # the assertion.
    sudo_re = re.compile(r"\bsudo\b")
    for src in (INSTALL_SH, PLIST_RENDER_PY):
        raw = _read(src)
        stripped = "\n".join(
            (line.split("#", 1)[0] if not line.lstrip().startswith("#!") else line)
            for line in raw.splitlines()
        )
        m = sudo_re.search(stripped)
        assert not m, f"sudo invocation in {src}: {m.group(0) if m else ''}"
