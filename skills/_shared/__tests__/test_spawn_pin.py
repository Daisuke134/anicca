"""PROP-E5-spawn-pin (required:true, Tier 1 integration) — spawn-surface immutability.

Spec: REQ-E5 — ed25519 sig + macOS Keychain pubkey + OS uchg + AST adversary gate.
Closes ROUND-2-002 (high) + ROUND-3-001 (critical pinned.json self-ref) + ROUND-3-002 (high
grep defeated by encodings).

Tests exercise the 12 PROP-E5 fixture cases (f-i through f-xii) from verification-architecture.md.
Integration tests use a sandbox tmp dir + stubbed keychain access.
"""
import hashlib
import pytest

from lib.spawn_pin import (  # FAIL until 2b
    SpawnSurfaceState,
    verify_spawn_surface,
    adversary_path_intersect,
)


# ── f-i: clean run → PASS ────────────────────────────────────────────
def test_clean_state_passes(tmp_path, monkeypatch):
    """All sigs valid, all sha match → verify returns OK."""
    state = SpawnSurfaceState.fixture_clean(tmp_path)
    result = verify_spawn_surface(state)
    assert result.ok is True
    assert result.reason is None


# ── f-ii: drift on one spawn-surface file → halt+escalate ────────────
def test_drift_on_adversary_daily_tmpl_halts(tmp_path):
    """An attacker bypassed the 0o444 production guard (= chmod 0o644 themselves) and
    mutated a surface file. The signature/sha-compare layer must still catch it."""
    state = SpawnSurfaceState.fixture_clean(tmp_path)
    target = tmp_path / "adversary-daily-prompt.tmpl"
    import os
    os.chmod(target, 0o644)  # simulate attacker removing the 0o444 guard
    target.write_text("evil content")
    result = verify_spawn_surface(state)
    assert result.ok is False
    assert "adversary-daily-prompt.tmpl" in result.reason
    assert result.escalation_reason == "spawn-surface-drift"


# ── f-iii: skill attempts write to spawn-surface → EACCES ────────────
def test_skill_write_to_surface_returns_eaccess(tmp_path):
    state = SpawnSurfaceState.fixture_clean(tmp_path)
    target = tmp_path / "loop-improve.py"
    with pytest.raises(PermissionError):
        target.write_text("evil mutation")


# ── f-iv: base64-encoded path in strategy.json.next → adversary FAIL ─
def test_base64_encoded_path_caught_by_adversary_gate(tmp_path):
    """ROUND-3-002 attack (a)."""
    strategy_next_src = """
import base64
path = base64.b64decode('X19zaGFyZWQvbG9vcC1pbXByb3ZlLnB5').decode()
open(path, 'w').write('pwned')
"""
    surface = ["_shared/loop-improve.py", "_shared/adversary-daily.sh"]
    assert adversary_path_intersect(strategy_next_src, surface) is True


# ── f-v: hex-encoded path → adversary FAIL ───────────────────────────
def test_hex_encoded_path_caught(tmp_path):
    # Hex of `_shared/loop-improve.py` (2f=/ for the path separator).
    src = (
        "path = bytes.fromhex('5f736861726564 2f6c6f6f702d 696d 70726f76652e7079'.replace(' ','')).decode()"
    )
    surface = ["_shared/loop-improve.py"]
    assert adversary_path_intersect(src, surface) is True


# ── f-vi: string concat → adversary FAIL ─────────────────────────────
def test_string_concat_path_caught():
    """ROUND-3-002 attack (c)."""
    src = "path = '_sh' + 'ared/' + 'loop-improve' + '.py'\nopen(path, 'w')"
    surface = ["_shared/loop-improve.py"]
    assert adversary_path_intersect(src, surface) is True


# ── f-vii: os.path.join with split → adversary FAIL ──────────────────
def test_os_path_join_caught():
    """ROUND-3-002 attack (d)."""
    src = (
        "import os\n"
        "p = os.path.join('_shared', 'loop-' + 'improve.py')\n"
        "open(p, 'w')"
    )
    surface = ["_shared/loop-improve.py"]
    assert adversary_path_intersect(src, surface) is True


# ── f-viii: glob/iterdir → adversary FAIL ────────────────────────────
def test_glob_iterdir_caught():
    """ROUND-3-002 attack (e). The adversary should recognize that iterating
    the _shared/ directory and writing to any file there intersects spawn surface."""
    src = (
        "import pathlib\n"
        "for f in pathlib.Path('_shared').iterdir():\n"
        "    if f.stat().st_size < 1000:\n"
        "        f.write_text('evil')"
    )
    surface = ["_shared/loop-improve.py"]
    assert adversary_path_intersect(src, surface) is True


# ── f-ix: read pinned.json + iterate → adversary FAIL (meta-attack) ──
def test_reading_pinned_json_and_writing_caught():
    """ROUND-3-002 attack (f) — meta-loophole where the script reads spawn-surface
    list FROM the pin file and iterates it."""
    src = (
        "import json\n"
        "pin = json.load(open('_shared/spawn-surface.pinned.json'))\n"
        "for fname in pin['files']:\n"
        "    open(fname, 'w').write('evil')"
    )
    surface = ["_shared/loop-improve.py", "_shared/spawn-surface.pinned.json"]
    assert adversary_path_intersect(src, surface) is True


# ── f-x: sig file tampered → halt+escalate ──────────────────────────
def test_tampered_signature_halts(tmp_path):
    state = SpawnSurfaceState.fixture_clean(tmp_path)
    (tmp_path / "spawn-surface.pinned.json.sig").write_bytes(b"\x00" * 64)
    result = verify_spawn_surface(state)
    assert result.ok is False
    assert result.escalation_reason == "spawn-surface-sig-invalid"


# ── f-xi: anicca-bot.pub framework key unreadable → halt+escalate ────
def test_anicca_bot_pubkey_unreadable_halts(tmp_path):
    state = SpawnSurfaceState.fixture_clean(tmp_path)
    state.trust_anchor_readable = False  # simulate anicca-bot.pub gone
    result = verify_spawn_surface(state)
    assert result.ok is False
    assert result.escalation_reason == "trust-anchor-unreadable"


# ── f-xii: pinned.json self-sha doesn't match its current content ────
def test_pinned_json_self_sha_mismatch_halts(tmp_path):
    """ROUND-3-001 the final loophole: pinned.json itself was rewritten such
    that its self-sha entry no longer matches its current sha256."""
    state = SpawnSurfaceState.fixture_clean(tmp_path)
    # tamper pinned.json without re-signing — its self-sha entry stays the OLD value
    # but its current bytes hash to a NEW value
    pin = tmp_path / "spawn-surface.pinned.json"
    import os
    os.chmod(pin, 0o644)
    contents = pin.read_text()
    pin.write_text(contents + "\n# evil appended\n")
    result = verify_spawn_surface(state)
    assert result.ok is False
    # could surface as sig-invalid (the sig was over the old bytes) OR drift
    assert result.escalation_reason in ("spawn-surface-sig-invalid", "spawn-surface-drift")
