"""test_public_artifact_snapshot.py — negative-test proof for the reality-gate capture tool.
Spec: .vcsdd/features/reality-gate/specs/behavioral-spec.md REQ-004/REQ-012/REQ-016/REQ-017.

Plain-assert style (repo convention, see skills/earn/gig/__tests__/test_gig_reality_gate.py),
runnable directly: `python3 test_public_artifact_snapshot.py`.

Network-required fixtures use `http://127.0.0.1:<closed-port>` (loopback only, no external
network dependency) so this suite never depends on internet access and never flakes in CI —
per this feature's own instruction: "ネットワーク必須のテストはskip可能にする(CIで落ちない)".
"""
import hashlib
import hmac as hmac_module
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SELF_DIR = os.path.dirname(_TESTS_DIR)  # .../skills/self
_SCRIPT_PATH = os.path.join(_SELF_DIR, "scripts", "public_artifact_snapshot.py")

P = 0
F = 0


def chk(name, cond):
    global P, F
    if cond:
        print(f"  ok {name}")
        P += 1
    else:
        print(f"  FAIL {name}")
        F += 1


if not os.path.exists(_SCRIPT_PATH):
    print(f"  FAIL scripts/public_artifact_snapshot.py does not exist yet at {_SCRIPT_PATH}")
    print("=== test_public_artifact_snapshot: 0 passed 1 failed (module missing) ===")
    sys.exit(1)

_spec = importlib.util.spec_from_file_location("public_artifact_snapshot", _SCRIPT_PATH)
mod = importlib.util.module_from_spec(_spec)
sys.modules["public_artifact_snapshot"] = mod
_spec.loader.exec_module(mod)

chk("exposes canonical_row_for_signing", hasattr(mod, "canonical_row_for_signing"))
chk("exposes compute_row_hmac", hasattr(mod, "compute_row_hmac"))
chk("exposes generate_pass_id", hasattr(mod, "generate_pass_id"))
chk("exposes create_trail_dir_exclusive", hasattr(mod, "create_trail_dir_exclusive"))
chk("exposes capture_and_sign", hasattr(mod, "capture_and_sign"))
chk("exposes classify_network_error", hasattr(mod, "classify_network_error"))

SECRET = "test-secret-do-not-use-in-prod"

# ─── canonical_row_for_signing / compute_row_hmac: deterministic, sorted-key, no rowHmac ──────
row = {"b": 2, "a": 1, "rowHmac": "should-be-excluded"}
canonical = mod.canonical_row_for_signing(row)
chk("canonical_row_for_signing sorts keys ascending", canonical == '{"a":1,"b":2}')
chk("canonical_row_for_signing excludes rowHmac itself", "rowHmac" not in canonical)

expected_hmac = hmac_module.new(SECRET.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
chk("compute_row_hmac matches a hand-computed HMAC over the canonical serialization", mod.compute_row_hmac(SECRET, row) == expected_hmac)

h1 = mod.compute_row_hmac(SECRET, {"x": 1})
h2 = mod.compute_row_hmac(SECRET, {"x": 1})
chk("compute_row_hmac is deterministic for identical input", h1 == h2)
h3 = mod.compute_row_hmac("a-different-secret", {"x": 1})
chk("compute_row_hmac differs under a different secret", h1 != h3)

# ─── generate_pass_id: CSPRNG-shaped, not time+PID ─────────────────────────────────────────────
pid_a = mod.generate_pass_id()
pid_b = mod.generate_pass_id()
chk("generate_pass_id produces distinct values across calls", pid_a != pid_b)
chk("generate_pass_id has >=32 hex chars of entropy (>=128 bits)", len(pid_a.split("-")[-1]) >= 32)

# ─── classify_network_error: never fabricates a real-looking status ───────────────────────────
class _FakeTimeout(TimeoutError):
    pass


chk("classify_network_error never returns something that looks like an HTTP status", not str(mod.classify_network_error(_FakeTimeout())).isdigit())

# ─── create_trail_dir_exclusive: exclusive create, refuses to reuse an existing dir ────────────
_tmp_root = tempfile.mkdtemp(prefix="public_artifact_snapshot_test_")
try:
    trail_dir = os.path.join(_tmp_root, "pass-xyz")
    mod.create_trail_dir_exclusive(trail_dir)
    chk("create_trail_dir_exclusive creates the directory on first call", os.path.isdir(trail_dir))

    raised = False
    try:
        mod.create_trail_dir_exclusive(trail_dir)
    except FileExistsError:
        raised = True
    chk("create_trail_dir_exclusive REFUSES a pre-existing directory (raises, never silently reuses)", raised)

    # ─── end-to-end via the real CLI (subprocess): secret via stdin, NEVER argv/env ────────────
    e2e_dir = os.path.join(_tmp_root, "pass-e2e")
    result = subprocess.run(
        [sys.executable, _SCRIPT_PATH, "--pass-id", "test-pass-e2e", "--trail-dir", e2e_dir, "http://127.0.0.1:1/unreachable"],
        input=SECRET,
        text=True,
        capture_output=True,
        timeout=20,
    )
    chk("CLI end-to-end run exits 0 for a network-error capture", result.returncode == 0)
    chk("CLI stdout is valid JSON reporting rowsWritten", json.loads(result.stdout).get("rowsWritten") == 1)

    trail_file = os.path.join(e2e_dir, "artifacts.jsonl")
    chk("artifacts.jsonl was actually written to disk", os.path.exists(trail_file))
    with open(trail_file, encoding="utf-8") as fh:
        written_row = json.loads(fh.readline())

    chk("network-error row: httpStatus is null, never a fabricated real-looking status", written_row["httpStatus"] is None)
    chk("network-error row: networkError field is present and non-empty", bool(written_row.get("networkError")))
    chk("network-error row: tool field is exactly public_artifact_snapshot", written_row["tool"] == "public_artifact_snapshot")

    recomputed = mod.compute_row_hmac(SECRET, written_row)
    chk("written row's rowHmac verifies against a fresh recomputation under the same secret", recomputed == written_row["rowHmac"])
    wrong_recompute = mod.compute_row_hmac("wrong-secret", written_row)
    chk("written row's rowHmac does NOT verify under a different secret (forger can't launder without the secret)", wrong_recompute != written_row["rowHmac"])

    # ─── negative test: re-running against the SAME trail dir must FAIL, not silently append ──
    result2 = subprocess.run(
        [sys.executable, _SCRIPT_PATH, "--pass-id", "test-pass-e2e-2", "--trail-dir", e2e_dir, "http://127.0.0.1:1/unreachable"],
        input=SECRET,
        text=True,
        capture_output=True,
        timeout=20,
    )
    chk("CLI negative test: re-running against an already-claimed trail dir exits non-zero (refuses to reuse)", result2.returncode != 0)

    # ─── PROP-051-style mechanical check: the secret never appears in the argv this process saw ──
    chk("secret never appears in the subprocess argv this test constructed", SECRET not in [sys.executable, _SCRIPT_PATH, "--pass-id", "test-pass-e2e", "--trail-dir", e2e_dir])
finally:
    shutil.rmtree(_tmp_root, ignore_errors=True)

print(f"=== test_public_artifact_snapshot: {P} passed {F} failed ===")
sys.exit(1 if F else 0)
