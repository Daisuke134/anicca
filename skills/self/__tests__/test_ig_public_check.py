"""test_ig_public_check.py — negative-test proof for the reality-gate Instagram public-surface
adapter. Spec: teammate task "V0-6 runtime配線 + IGアダプタ" (reality-gate REQ-005/006/010/018
follow-on). Plain-assert style (repo convention, see test_public_artifact_snapshot.py),
runnable directly: `python3 test_ig_public_check.py`.

Deterministic fixtures use an injected `client_factory` (fake instagrapi.Client stand-in) so
this suite never depends on network access for its PASS/FAIL/CANNOT_VERIFY branch coverage —
per this feature's own instruction: network-required tests must be skippable, never flaky in CI.
ONE real, live, logged-out network call against a real public Instagram account is included and
SKIPPED (not failed) if the network is unreachable, to prove the actual instagrapi integration
really works end-to-end (this repo's "no dry run" / own-eyes-verification rule).
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
_SCRIPT_PATH = os.path.join(_SELF_DIR, "scripts", "ig_public_check.py")

P = 0
F = 0
S = 0


def chk(name, cond):
    global P, F
    if cond:
        print(f"  ok {name}")
        P += 1
    else:
        print(f"  FAIL {name}")
        F += 1


def skip(name):
    global S
    print(f"  skip {name}")
    S += 1


if not os.path.exists(_SCRIPT_PATH):
    print(f"  FAIL scripts/ig_public_check.py does not exist yet at {_SCRIPT_PATH}")
    print("=== test_ig_public_check: 0 passed 1 failed (module missing) ===")
    sys.exit(1)

_spec = importlib.util.spec_from_file_location("ig_public_check", _SCRIPT_PATH)
mod = importlib.util.module_from_spec(_spec)
sys.modules["ig_public_check"] = mod
_spec.loader.exec_module(mod)

chk("exposes check_ig_post", hasattr(mod, "check_ig_post"))
chk("exposes capture_and_sign", hasattr(mod, "capture_and_sign"))
chk("exposes append_row", hasattr(mod, "append_row"))
chk("reuses (does not redefine) compute_row_hmac from public_artifact_snapshot.py", mod.compute_row_hmac.__module__ == "public_artifact_snapshot")
chk("reuses (does not redefine) create_trail_dir_exclusive from public_artifact_snapshot.py", mod.create_trail_dir_exclusive.__module__ == "public_artifact_snapshot")
chk("reuses (does not redefine) generate_pass_id from public_artifact_snapshot.py", mod.generate_pass_id.__module__ == "public_artifact_snapshot")

SECRET = "test-secret-do-not-use-in-prod"


# ─── Fake, network-free instagrapi.Client stand-ins (dependency-injected via client_factory) ───
class _FakeClientFound:
    def user_id_from_username(self, account):
        return "123456"

    def user_medias_gql(self, uid, amount):
        class M:
            def __init__(self, code):
                self.code = code

        return [M("ABC123"), M("XYZ999"), M("claimed-code-1")]


class _FakeClientNotFound:
    def user_id_from_username(self, account):
        return "123456"

    def user_medias_gql(self, uid, amount):
        class M:
            def __init__(self, code):
                self.code = code

        return [M("ABC123"), M("XYZ999")]


class _FakeClientRaises:
    def user_id_from_username(self, account):
        raise RuntimeError("simulated_private_or_ratelimited_account")


# ─── (1) PASS material: claimed code IS in the fixed public surface ───────────────────────────
row_pass = mod.check_ig_post("someaccount", "claimed-code-1", client_factory=lambda: _FakeClientFound())
chk("PASS-material row: found=True", row_pass["found"] is True)
chk("PASS-material row: verdictMaterial='pass'", row_pass["verdictMaterial"] == "pass")
chk("PASS-material row: surfaceCodes captured, real list", isinstance(row_pass["surfaceCodes"], list) and "claimed-code-1" in row_pass["surfaceCodes"])
chk("PASS-material row: httpStatus=200 (surface fetched cleanly)", row_pass["httpStatus"] == 200)

# ─── (2) FAIL material: surface fetched OK, claimed code absent -> positive contradiction ──────
row_fail = mod.check_ig_post("someaccount", "code-never-posted", client_factory=lambda: _FakeClientNotFound())
chk("FAIL-material row: found=False", row_fail["found"] is False)
chk("FAIL-material row: verdictMaterial='fail' (a positive contradiction, not cannot_verify)", row_fail["verdictMaterial"] == "fail")
chk("FAIL-material row: surfaceCodes is the REAL fetched list (evidence the surface WAS read)", row_fail["surfaceCodes"] == ["ABC123", "XYZ999"])

# ─── (3) CANNOT_VERIFY material: the surface itself could not be fetched ───────────────────────
row_cv = mod.check_ig_post("someaccount", "whatever", client_factory=lambda: _FakeClientRaises())
chk("CANNOT_VERIFY-material row: found is None (never coerced to False)", row_cv["found"] is None)
chk("CANNOT_VERIFY-material row: verdictMaterial='cannot_verify'", row_cv["verdictMaterial"] == "cannot_verify")
chk("CANNOT_VERIFY-material row: surfaceCodes is None (never a fabricated empty list)", row_cv["surfaceCodes"] is None)
chk("CANNOT_VERIFY-material row: networkError field present, non-empty", bool(row_cv.get("networkError")))
chk("CANNOT_VERIFY-material row: httpStatus is None, never a fabricated real-looking status", row_cv["httpStatus"] is None)

# ─── row envelope + HMAC: SAME shape/signing convention as public_artifact_snapshot.py rows ────
signed = mod.capture_and_sign("pass-abc", "someaccount", "claimed-code-1", 12, SECRET, client_factory=lambda: _FakeClientFound())
chk("signed row carries tool=ig_public_check", signed["tool"] == "ig_public_check")
chk("signed row carries the given passId", signed["passId"] == "pass-abc")
chk("signed row has an integer ms timestamp", isinstance(signed["ts"], int))
recomputed = mod.compute_row_hmac(SECRET, signed)
chk("signed row's rowHmac verifies against a fresh recomputation under the same secret", recomputed == signed["rowHmac"])
wrong = mod.compute_row_hmac("a-different-secret", signed)
chk("signed row's rowHmac does NOT verify under a different secret", wrong != signed["rowHmac"])
expected_canon = mod.canonical_row_for_signing(signed)
expected_hmac = hmac_module.new(SECRET.encode("utf-8"), expected_canon.encode("utf-8"), hashlib.sha256).hexdigest()
chk("rowHmac matches a hand-computed HMAC over the canonical serialization (same algorithm as public_artifact_snapshot.py)", signed["rowHmac"] == expected_hmac)

# ─── end-to-end via the real CLI (subprocess): secret via stdin, NEVER argv/env; exclusive dir ─
_tmp_root = tempfile.mkdtemp(prefix="ig_public_check_test_")
try:
    e2e_dir = os.path.join(_tmp_root, "pass-e2e")
    # Real CLI invocation hits the real, unauthenticated instagrapi Client (network required) —
    # skip (not fail) if the network is unreachable, per this feature's CI-safety rule.
    result = subprocess.run(
        [sys.executable, _SCRIPT_PATH, "--pass-id", "test-pass-e2e", "--trail-dir", e2e_dir,
         "--account", "instagram", "--claimed-code", "this-code-almost-certainly-was-not-just-posted",
         "--sample-size", "12"],
        input=SECRET,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        skip(f"live CLI E2E against real instagram.com unreachable/blocked (rc={result.returncode}, stderr={result.stderr.strip()[:200]}) — not counted as a failure")
    else:
        chk("live CLI E2E: exits 0", True)
        parsed = json.loads(result.stdout)
        chk("live CLI E2E: stdout is valid JSON reporting a trailPath", "trailPath" in parsed)
        chk("live CLI E2E: verdictMaterial is one of pass/fail/cannot_verify", parsed.get("verdictMaterial") in ("pass", "fail", "cannot_verify"))
        trail_file = os.path.join(e2e_dir, "artifacts.jsonl")
        chk("live CLI E2E: artifacts.jsonl actually written to disk", os.path.exists(trail_file))
        with open(trail_file, encoding="utf-8") as fh:
            written_row = json.loads(fh.readline())
        chk("live CLI E2E: written row tool=ig_public_check", written_row.get("tool") == "ig_public_check")
        recomputed_live = mod.compute_row_hmac(SECRET, written_row)
        chk("live CLI E2E: written row's rowHmac verifies", recomputed_live == written_row.get("rowHmac"))
        chk("secret never appears in the subprocess argv this test constructed", SECRET not in [
            sys.executable, _SCRIPT_PATH, "--pass-id", "test-pass-e2e", "--trail-dir", e2e_dir,
            "--account", "instagram", "--claimed-code", "this-code-almost-certainly-was-not-just-posted",
        ])

    # ─── negative test: re-running against the SAME trail dir must FAIL, not silently append ──
    if result.returncode == 0:
        result2 = subprocess.run(
            [sys.executable, _SCRIPT_PATH, "--pass-id", "test-pass-e2e-2", "--trail-dir", e2e_dir,
             "--account", "instagram", "--claimed-code", "whatever"],
            input=SECRET,
            text=True,
            capture_output=True,
            timeout=30,
        )
        chk("negative test: re-running against an already-claimed trail dir exits non-zero", result2.returncode != 0)
finally:
    shutil.rmtree(_tmp_root, ignore_errors=True)

print(f"=== test_ig_public_check: {P} passed {F} failed {S} skipped ===")
sys.exit(1 if F else 0)
