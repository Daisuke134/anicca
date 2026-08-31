#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s 2>/dev/null || true)" != "Darwin" ]]; then
  printf '%s\n' 'affiliate bootstrap: unsupported operating system' >&2
  exit 64
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec python3 -I -B - "$SCRIPT_DIR/manifest.lock" "$@" <<'PY'
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname, urlopen


class BootstrapError(Exception):
    pass


SHA256 = re.compile(r"^[0-9a-f]{64}$")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_manifest(path):
    if not path.is_file():
        raise BootstrapError("manifest is missing")
    entries = []
    seen = set()
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) != 4:
            raise BootstrapError("invalid manifest entry")
        name, version, url, expected = fields
        if not NAME.fullmatch(name) or not NAME.fullmatch(version):
            raise BootstrapError("invalid manifest identity")
        if not (url.startswith("file://") or url.startswith("https://")):
            raise BootstrapError("invalid manifest URL")
        if not SHA256.fullmatch(expected):
            raise BootstrapError("invalid manifest checksum")
        if name in seen:
            raise BootstrapError("duplicate manifest entry")
        seen.add(name)
        entries.append({"name": name, "version": version, "url": url, "sha256": expected})
    if not entries:
        raise BootstrapError("manifest has no entries")
    return entries


def source_stream(url):
    parsed = urlparse(url)
    if parsed.scheme == "file":
        if parsed.netloc not in ("", "localhost"):
            raise BootstrapError("file URL host is not allowed")
        return Path(url2pathname(unquote(parsed.path))).open("rb")
    return urlopen(url, timeout=30)


def install_artifact(entry, artifact_dir):
    destination = artifact_dir / (entry["name"] + "-" + entry["version"] + "-" + entry["sha256"])
    if destination.exists():
        if not destination.is_file() or digest(destination) != entry["sha256"]:
            raise BootstrapError("existing artifact checksum mismatch")
        return destination

    fd, temporary = tempfile.mkstemp(prefix="." + destination.name + ".", dir=str(artifact_dir))
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as output, source_stream(entry["url"]) as source:
            shutil.copyfileobj(source, output)
        if digest(temporary_path) != entry["sha256"]:
            raise BootstrapError("download checksum mismatch")
        os.replace(str(temporary_path), str(destination))
        return destination
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def signature(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_mode)


def digest_fd(fd):
    value = hashlib.sha256()
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            return value.hexdigest()
        value.update(chunk)


def tree_digest(root):
    if root.is_symlink() or not root.is_dir():
        raise BootstrapError("runtime tree root is invalid")
    root = root.resolve(strict=True)
    records = []
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        for name in sorted(directories + files):
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            info = os.lstat(path)
            mode = stat.S_IMODE(info.st_mode)
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(path)
                try:
                    path.resolve(strict=True).relative_to(root)
                except (OSError, RuntimeError, ValueError):
                    raise BootstrapError("runtime symlink escapes tree")
                records.append((relative, "l", mode, path, target))
            elif stat.S_ISDIR(info.st_mode):
                records.append((relative, "d", mode, path, ""))
            elif stat.S_ISREG(info.st_mode):
                records.append((relative, "f", mode, path, ""))
            else:
                raise BootstrapError("runtime tree contains unsupported file")
    value = hashlib.sha256()
    for relative, kind, mode, path, target in sorted(records):
        value.update((kind + "\0" + relative + "\0" + str(mode) + "\0").encode())
        if kind == "l":
            value.update(target.encode())
        elif kind == "f":
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    value.update(chunk)
    return value.hexdigest()


def validate_runtime(root):
    if root.is_symlink() or not root.is_dir():
        raise BootstrapError("runtime root is invalid")
    binary = root / "bin" / "python3.14"
    if binary.is_symlink() or not binary.is_file() or not binary.stat().st_mode & 0o111:
        raise BootstrapError("runtime binary is invalid")
    resolved_root = root.resolve(strict=True)
    for alias in (root / "bin" / "python", root / "bin" / "python3"):
        try:
            alias.resolve(strict=True).relative_to(resolved_root)
        except (OSError, RuntimeError, ValueError):
            raise BootstrapError("runtime alias is outside staged tree")
    try:
        result = subprocess.run(
            [str(binary), "-I", "-B", "-c", "import sys,ssl,sqlite3; assert sys.version_info[:3] == (3,14,7); print('.'.join(map(str, sys.version_info[:3])))"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
            env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C", "LC_ALL": "C"},
            cwd=str(root.resolve(strict=True)),
        )
    except (OSError, subprocess.SubprocessError):
        raise BootstrapError("runtime verification failed")
    if result.stdout != "3.14.7\n" or result.stderr:
        raise BootstrapError("runtime version output is invalid")
    return {
        "binary_path": str(binary),
        "binary_sha256": digest(binary),
        "reported_version": result.stdout.rstrip("\n"),
        "tree_sha256": tree_digest(root),
    }


def install_runtime(entry, artifact, runtime_root):
    expected = {
        "name": "cpython-runtime",
        "version": "3.14.7.20260814",
        "url": "https://github.com/astral-sh/python-build-standalone/releases/download/20260814/cpython-3.14.7%2B20260814-aarch64-apple-darwin-install_only_stripped.tar.gz",
        "sha256": "423717c485b9ee7822590b9d973c1b5fb2cda0fe43448ab82a3d44f823bd329c",
    }
    if entry != expected:
        raise BootstrapError("runtime pin mismatch")
    runtime_root.mkdir(parents=True, exist_ok=True)
    if runtime_root.is_symlink() or not runtime_root.is_dir():
        raise BootstrapError("runtime directory is invalid")
    destination = runtime_root / ("cpython-3.14.7.20260814-" + entry["sha256"][:16])
    staging = Path(tempfile.mkdtemp(prefix=".cpython-runtime-", dir=str(runtime_root)))
    artifact_fd = -1
    try:
        artifact_fd = os.open(str(artifact), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        artifact_before = os.fstat(artifact_fd)
        if not stat.S_ISREG(artifact_before.st_mode):
            raise BootstrapError("runtime artifact is not regular")
        actual = digest_fd(artifact_fd)
        if actual != entry["sha256"]:
            raise BootstrapError("runtime artifact checksum mismatch")
        os.lseek(artifact_fd, 0, os.SEEK_SET)
        with tarfile.open(fileobj=os.fdopen(os.dup(artifact_fd), "rb"), mode="r:*") as archive:
            members = archive.getmembers()
            if not members:
                raise BootstrapError("runtime archive is empty")
            for member in members:
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "python":
                    raise BootstrapError("runtime archive path is unsafe")
            archive.extractall(staging, filter="data")
        artifact_after = os.fstat(artifact_fd)
        artifact_path = os.lstat(str(artifact))
        if (signature(artifact_before) != signature(artifact_after) or stat.S_ISLNK(artifact_path.st_mode) or
                signature(artifact_path) != signature(artifact_after)):
            raise BootstrapError("runtime artifact changed during extraction")
        staged_python = staging / "python"
        details = validate_runtime(staged_python)
        if destination.exists() or destination.is_symlink():
            if destination.is_symlink() or not destination.is_dir():
                raise BootstrapError("runtime destination is invalid")
            if tree_digest(destination) != details["tree_sha256"]:
                raise BootstrapError("runtime destination conflicts")
        else:
            os.replace(str(staged_python), str(destination))
        details["binary_path"] = str(destination / "bin" / "python3.14")
        ensure_current(runtime_root, destination)
        return {"name": entry["name"], "version": entry["version"], "path": str(destination), "build": "20260814", **details}
    finally:
        if artifact_fd >= 0:
            os.close(artifact_fd)
        if staging.exists():
            shutil.rmtree(staging)


def ensure_current(runtime_root, destination):
    current = runtime_root / "current"
    if current.is_symlink():
        try:
            if current.resolve(strict=True) == destination.resolve(strict=True):
                return
        except (OSError, RuntimeError):
            pass
        fd, temporary_name = tempfile.mkstemp(prefix=".current-", dir=str(runtime_root))
        os.close(fd)
        temporary = Path(temporary_name)
        temporary.unlink()
        try:
            os.symlink(str(destination), str(temporary))
            os.replace(str(temporary), str(current))
        finally:
            if temporary.is_symlink() or temporary.exists():
                temporary.unlink()
        return
    if current.exists():
        raise BootstrapError("runtime current path conflicts")
    fd, temporary_name = tempfile.mkstemp(prefix=".current-", dir=str(runtime_root))
    os.close(fd)
    temporary = Path(temporary_name)
    temporary.unlink()
    try:
        os.symlink(str(destination), str(temporary))
        os.replace(str(temporary), str(current))
    finally:
        if temporary.is_symlink() or temporary.exists():
            temporary.unlink()


def write_receipt(path, payload):
    fd, temporary = tempfile.mkstemp(prefix=".machine-capability.", dir=str(path.parent))
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        os.replace(str(temporary_path), str(path))
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def main(default_manifest):
    manifest_path = Path(os.environ.get("MR_BOT_BOOTSTRAP_MANIFEST", default_manifest))
    entries = read_manifest(manifest_path)
    if len([entry for entry in entries if entry["name"] == "cpython-runtime"]) != 1:
        raise BootstrapError("exactly one cpython-runtime is required")
    manifest_hash = digest(manifest_path)
    home = Path(os.environ.get("HOME", str(Path.home())))
    data_home = Path(os.environ.get("MR_BOT_DATA_HOME", home / ".local/share/mr-bot"))
    state_home = Path(os.environ.get("MR_BOT_STATE_HOME", home / ".local/state/mr-bot"))
    receipt = state_home / "affiliate" / "bootstrap" / "machine-capability.json"

    if receipt.exists():
        try:
            previous = json.loads(receipt.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise BootstrapError("invalid existing receipt")
        if previous.get("manifest_sha256") != manifest_hash:
            raise BootstrapError("receipt belongs to a different manifest")
        if previous.get("status") not in ("READY", "IN_PROGRESS"):
            raise BootstrapError("invalid receipt status")

    artifact_dir = data_home / "affiliate" / "bootstrap" / "artifacts"
    runtime_root = data_home / "affiliate" / "bootstrap" / "runtimes"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifacts = []
    runtime = None
    for entry in entries:
        destination = install_artifact(entry, artifact_dir)
        artifacts.append(
            {"name": entry["name"], "version": entry["version"], "sha256": entry["sha256"], "path": str(destination)}
        )
        if entry["name"] == "cpython-runtime":
            runtime = install_runtime(entry, destination, runtime_root)
    if runtime is None:
        raise BootstrapError("runtime installation did not complete")

    payload = {
        "status": "READY",
        "platform": "Darwin",
        "manifest_sha256": manifest_hash,
        "completed_steps": ["directories", "artifacts", "receipt"],
        "artifacts": sorted(artifacts, key=lambda item: (item["name"], item["version"], item["sha256"])),
    }
    payload["runtime"] = runtime
    write_receipt(receipt, payload)


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except (BootstrapError, OSError, ValueError) as error:
        message = str(error) if isinstance(error, BootstrapError) else "unexpected bootstrap failure"
        print(f"affiliate bootstrap: failed closed: {message}", file=sys.stderr)
        sys.exit(1)
PY
