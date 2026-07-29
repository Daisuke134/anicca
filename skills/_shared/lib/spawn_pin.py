"""spawn_pin — spawn-surface immutability (REQ-E5 v7, NO HUMAN).

PROP-E5-spawn-pin (required:true, Tier 1 integration). v7 trust anchor =
anicca-bot ed25519 pubkey shipped at __REPO_ROOT__/skills/_shared/anicca-bot.pub
(NOT macOS Keychain Touch ID — ROUND-5-001 fix).

Closes ROUND-2-002 + ROUND-3-001 + ROUND-3-002 + ROUND-5-001.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# ────────────────────────────────────────────────────────────────────────
# Spawn-surface file set (v7: 6 files; anicca-bot.pub replaces Keychain entry)
# ────────────────────────────────────────────────────────────────────────
SPAWN_SURFACE_FILES = (
    "adversary-daily.sh",
    "adversary-daily-prompt.tmpl",
    "loop-improve.py",
    "payout-endpoint-allowlist.json",
    "hook-modules-allowlist.txt",
    "anicca-bot.pub",
    "spawn-surface.pinned.json",
)


@dataclass
class VerifyResult:
    ok: bool
    reason: str | None = None
    escalation_reason: str | None = None  # "spawn-surface-drift" | "spawn-surface-sig-invalid" | "trust-anchor-unreadable" | "spawn-surface-flag-missing"


@dataclass
class SpawnSurfaceState:
    """Fixture-side state container. In production, the equivalent is read
    from disk + the `__REPO_ROOT__/skills/_shared/` filesystem itself.
    """
    root_dir: Path
    trust_anchor_readable: bool = True

    @classmethod
    def fixture_clean(cls, tmp_path: Path) -> "SpawnSurfaceState":
        """Construct a clean fixture: write each surface file with placeholder
        content, generate pinned.json with sha256 of each + self-sha, generate
        a fixture-protocol sig, set files to 0o444 (= test f-iii EACCES path).
        """
        root = Path(tmp_path)
        # Sprint-3 #29 FIND-015 fix: generate ephemeral ed25519 keypair FIRST so
        # anicca-bot.pub already carries the real pubkey when we compute sha256s.
        from lib.ed25519_util import generate_test_keypair, sign_bytes_ed25519
        priv_path, pub_b64 = generate_test_keypair(root / ".fixture-keys")
        # 1. Write the 5 surface files (not pinned.json yet — needs to know own bytes)
        contents = {
            "adversary-daily.sh": "#!/usr/bin/env bash\necho 'fixture adversary-daily'\n",
            "adversary-daily-prompt.tmpl": "Fixture adversary prompt\n",
            "loop-improve.py": "# fixture loop-improve\nprint('improved')\n",
            "payout-endpoint-allowlist.json": '{"schema_version":1,"platforms":[]}\n',
            "hook-modules-allowlist.txt": "dotenv\nzx\n",
            "anicca-bot.pub": pub_b64 + "\n",  # real ed25519 pubkey from ephemeral keypair
        }
        for name, body in contents.items():
            (root / name).write_text(body)

        # 2. Compute sha256 of each + write pinned.json that includes its OWN sha (self-ref).
        # Because pinned.json must contain its own sha but its own sha depends on its content
        # (= chicken/egg), we use a two-pass: first write with placeholder, then rewrite with
        # the real self-sha. The final self-sha in the file matches sha256(final-file-bytes).
        files_section = {name: _sha256_file(root / name) for name in contents}
        pinned_dict = {"schema_version": 1, "files": files_section, "self_sha256": ""}
        import json
        first_bytes = (json.dumps(pinned_dict, indent=2, sort_keys=True) + "\n").encode()
        # Self-sha is the sha of the FINAL bytes. We iterate to a fixed point.
        # Trick: compute sha of canonical-form-with-self-sha-cleared, then put that into the file.
        canonical_bytes = first_bytes
        pinned_dict["self_sha256"] = hashlib.sha256(canonical_bytes).hexdigest()
        final_bytes = (json.dumps(pinned_dict, indent=2, sort_keys=True) + "\n").encode()
        (root / "spawn-surface.pinned.json").write_bytes(final_bytes)

        # 3. Sprint-3 #29 FIND-015 fix: sign final pinned bytes with the ephemeral
        # private key generated at the top of this method (see step 0).
        sig_64 = sign_bytes_ed25519(final_bytes, priv_path)
        assert len(sig_64) == 64  # real ed25519 sigs are exactly 64 bytes
        (root / "spawn-surface.pinned.json.sig").write_bytes(sig_64)

        # 4. Set surface files to 0o444 (= test f-iii EACCES; chflags uchg simulated here as 0o444).
        for name in list(contents.keys()) + ["spawn-surface.pinned.json"]:
            os.chmod(root / name, 0o444)

        return cls(root_dir=root, trust_anchor_readable=True)


# ────────────────────────────────────────────────────────────────────────
# Verification
# ────────────────────────────────────────────────────────────────────────
from lib._common import sha256_file as _sha256_file  # extracted in 2c refactor


def verify_spawn_surface(state: SpawnSurfaceState) -> VerifyResult:
    """Ordered check per REQ-E5 v7:
    (a) read anicca-bot.pub from framework path; halt if unreadable
    (b) verify pinned.json.sig against pinned.json with that pubkey
    (c) sha compare each of the 7 spawn-surface entries including pinned.json's self-sha
    """
    root = state.root_dir
    pubkey_path = root / "anicca-bot.pub"
    pinned_path = root / "spawn-surface.pinned.json"
    sig_path = root / "spawn-surface.pinned.json.sig"

    # (a) trust anchor readable check
    if not state.trust_anchor_readable or not pubkey_path.exists():
        return VerifyResult(
            ok=False,
            reason="anicca-bot.pub unreadable",
            escalation_reason="trust-anchor-unreadable",
        )

    pubkey_raw = pubkey_path.read_text().strip()

    # (b) sig verify — sprint-3 #29 FIND-015 fix: REAL ed25519 via openssl.
    # NO fallback to fixture sha256 protocol (REQ-P3, fail-closed).
    from lib.ed25519_util import is_valid_ed25519_pubkey, verify_bytes_ed25519
    if not is_valid_ed25519_pubkey(pubkey_raw):
        return VerifyResult(
            ok=False,
            reason="trust anchor not valid ed25519 pubkey",
            escalation_reason="trust-anchor-invalid-ed25519",
        )
    if not pinned_path.exists() or not sig_path.exists():
        return VerifyResult(
            ok=False,
            reason="pinned.json or sig missing",
            escalation_reason="spawn-surface-sig-invalid",
        )

    pinned_bytes = pinned_path.read_bytes()
    actual_sig = sig_path.read_bytes()
    if not verify_bytes_ed25519(pinned_bytes, actual_sig, pubkey_raw):
        return VerifyResult(
            ok=False,
            reason="signature mismatch",
            escalation_reason="spawn-surface-sig-invalid",
        )

    # (c) sha compare each surface file + pinned.json self-sha
    import json
    try:
        pinned = json.loads(pinned_bytes)
    except json.JSONDecodeError:
        return VerifyResult(
            ok=False,
            reason="pinned.json unparseable",
            escalation_reason="spawn-surface-sig-invalid",
        )

    # First check pinned.json's self-sha vs current bytes (with self_sha256 field cleared)
    self_sha_claimed = pinned.get("self_sha256", "")
    pinned_for_self_sha = dict(pinned)
    pinned_for_self_sha["self_sha256"] = ""
    canonical = (json.dumps(pinned_for_self_sha, indent=2, sort_keys=True) + "\n").encode()
    self_sha_actual = hashlib.sha256(canonical).hexdigest()
    if self_sha_claimed != self_sha_actual:
        return VerifyResult(
            ok=False,
            reason=f"pinned.json self-sha mismatch (claimed={self_sha_claimed[:8]} actual={self_sha_actual[:8]})",
            escalation_reason="spawn-surface-drift",
        )

    # Then compare each surface file
    for name, expected_sha in pinned.get("files", {}).items():
        fpath = root / name
        if not fpath.exists():
            return VerifyResult(
                ok=False,
                reason=f"{name} missing",
                escalation_reason="spawn-surface-drift",
            )
        actual_sha = _sha256_file(fpath)
        if actual_sha != expected_sha:
            return VerifyResult(
                ok=False,
                reason=f"{name} drift",
                escalation_reason="spawn-surface-drift",
            )

    return VerifyResult(ok=True)


# ────────────────────────────────────────────────────────────────────────
# Adversary path intersect — structured analysis (replaces v3 grep)
# Closes ROUND-3-002: detects base64/hex/concat/glob/pinned-read bypasses.
# ────────────────────────────────────────────────────────────────────────


def adversary_path_intersect(source: str, surface: Iterable[str]) -> bool:
    """Return True if `source` references any path in `surface` (= the spawn-surface
    set), through any of these encodings:
      (a) literal string
      (b) base64.b64decode of a literal
      (c) bytes.fromhex of a literal
      (d) string concatenation (BinOp Add) of constants
      (e) os.path.join with constant args
      (f) glob/iterdir on a directory that contains a surface entry
      (g) reading the spawn-surface.pinned.json file
    """
    surface_set = set(surface)
    # Also add the directory prefixes (e.g. "_shared" if "_shared/foo.py" is in surface).
    dir_prefixes: set[str] = set()
    for s in surface_set:
        parts = s.split("/")
        for i in range(1, len(parts)):
            dir_prefixes.add("/".join(parts[:i]))

    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Fall back to substring grep as a sanity check.
        return any(s in source for s in surface_set)

    finder = _PathFinder(surface_set=surface_set, dir_prefixes=dir_prefixes)
    finder.visit(tree)
    return finder.intersects


class _PathFinder(ast.NodeVisitor):
    def __init__(self, *, surface_set: set[str], dir_prefixes: set[str]) -> None:
        self.surface_set = surface_set
        self.dir_prefixes = dir_prefixes
        self.intersects = False
        # Track simple Name → folded-string assignments
        self.var_strings: dict[str, str] = {}

    def _check(self, s: str | None) -> None:
        if not s or self.intersects:
            return
        if s in self.surface_set:
            self.intersects = True
            return
        # Match by trailing path: source value ends with a surface name (= absolute or
        # nested path leading to a surface file).
        for sp in self.surface_set:
            if s.endswith(sp) or s.endswith("/" + sp.split("/")[-1]):
                # Trailing basename match — flag if the surface entry's basename is unique
                base = sp.split("/")[-1]
                if s.endswith(base) and base != s.split("/")[-1]:
                    # safer: only flag if full ending matches the surface relative
                    if s.endswith(sp):
                        self.intersects = True
                        return
                elif s.endswith(sp):
                    self.intersects = True
                    return

    def _fold(self, node: ast.AST) -> str | None:
        """Constant-fold a string expression with encoding decoders."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            l = self._fold(node.left)
            r = self._fold(node.right)
            if l is not None and r is not None:
                return l + r
        if isinstance(node, ast.Name) and node.id in self.var_strings:
            return self.var_strings[node.id]
        if isinstance(node, ast.JoinedStr):
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(v.value)
                else:
                    return None
            return "".join(parts)
        if isinstance(node, ast.Call):
            # base64.b64decode('xxx').decode() / .decode('utf-8')
            if (
                isinstance(node.func, ast.Attribute) and node.func.attr == "decode"
                and isinstance(node.func.value, ast.Call)
            ):
                inner = node.func.value
                if (
                    isinstance(inner.func, ast.Attribute)
                    and inner.func.attr == "b64decode"
                    and inner.args
                    and isinstance(inner.args[0], ast.Constant)
                    and isinstance(inner.args[0].value, str)
                ):
                    try:
                        return base64.b64decode(inner.args[0].value).decode()
                    except Exception:
                        return None
                if (
                    isinstance(inner.func, ast.Attribute)
                    and inner.func.attr == "fromhex"
                    and inner.args
                ):
                    # Handle both forms:
                    #   bytes.fromhex('5f7368...')
                    #   bytes.fromhex('5f 73 68 ...'.replace(' ', ''))
                    hex_arg = self._extract_hex_arg(inner.args[0])
                    if hex_arg is not None:
                        try:
                            return bytes.fromhex(hex_arg).decode()
                        except Exception:
                            return None
            # base64.b64decode('xxx') alone (bytes — caller may .decode later)
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "b64decode"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                try:
                    return base64.b64decode(node.args[0].value).decode()
                except Exception:
                    return None
            # bytes.fromhex('xxx').replace(' ','').decode() style — too complex, skip
            # os.path.join(...)
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Attribute)
                and getattr(node.func.value.value, "id", None) == "os"
                and node.func.value.attr == "path"
                and node.func.attr == "join"
            ):
                parts = [self._fold(a) for a in node.args]
                if all(p is not None for p in parts):
                    return "/".join(p for p in parts if p is not None)
        return None

    def _extract_hex_arg(self, node: ast.AST) -> str | None:
        """Extract the hex string from either a literal or a `'hex'.replace(' ','')` chain."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value.replace(" ", "").replace("\n", "")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "replace"
            and isinstance(node.func.value, ast.Constant)
            and isinstance(node.func.value.value, str)
        ):
            base = node.func.value.value
            # Look at the replace's args: ('old', 'new')
            if (
                len(node.args) == 2
                and all(isinstance(a, ast.Constant) and isinstance(a.value, str) for a in node.args)
            ):
                return base.replace(node.args[0].value, node.args[1].value).replace(" ", "").replace("\n", "")
            return base.replace(" ", "").replace("\n", "")
        return None

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            folded = self._fold(node.value)
            if folded is not None:
                self.var_strings[node.targets[0].id] = folded
                self._check(folded)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:  # noqa: N802
        if isinstance(node.value, str):
            self._check(node.value)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        # Check folded-string args of any call
        for arg in node.args:
            folded = self._fold(arg)
            if folded is not None:
                self._check(folded)

        # (f) glob/iterdir on a directory in dir_prefixes
        if isinstance(node.func, ast.Attribute) and node.func.attr in ("iterdir", "glob", "rglob"):
            # node.func.value = pathlib.Path('<dir>')
            inner = node.func.value
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "Path"
                and inner.args
                and isinstance(inner.args[0], ast.Constant)
                and isinstance(inner.args[0].value, str)
                and inner.args[0].value in self.dir_prefixes
            ):
                self.intersects = True

        # (g) open() / json.load() reading spawn-surface.pinned.json
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "open"
            and node.args
        ):
            folded = self._fold(node.args[0])
            if folded is not None:
                for sp in self.surface_set:
                    if folded.endswith(sp):
                        self.intersects = True
                        break
        self.generic_visit(node)
