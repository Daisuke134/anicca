#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s 2>/dev/null || true)" != "Darwin" ]]; then
  printf '%s\n' 'affiliate bootstrap: unsupported operating system' >&2
  exit 64
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec python3 - "$SCRIPT_DIR/manifest.lock" "$@" <<'PY'
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
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
    manifest_path = Path(os.environ.get("LIFE_MANAGER_BOOTSTRAP_MANIFEST", default_manifest))
    entries = read_manifest(manifest_path)
    manifest_hash = digest(manifest_path)
    home = Path(os.environ.get("HOME", str(Path.home())))
    data_home = Path(os.environ.get("LIFE_MANAGER_DATA_HOME", home / ".local/share/life-manager"))
    state_home = Path(os.environ.get("LIFE_MANAGER_STATE_HOME", home / ".local/state/life-manager"))
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
    receipt.parent.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for entry in entries:
        destination = install_artifact(entry, artifact_dir)
        artifacts.append(
            {"name": entry["name"], "version": entry["version"], "sha256": entry["sha256"], "path": str(destination)}
        )

    payload = {
        "status": "READY",
        "platform": "Darwin",
        "manifest_sha256": manifest_hash,
        "completed_steps": ["directories", "artifacts", "receipt"],
        "artifacts": sorted(artifacts, key=lambda item: (item["name"], item["version"], item["sha256"])),
    }
    write_receipt(receipt, payload)


if __name__ == "__main__":
    try:
        main(sys.argv[1])
    except (BootstrapError, OSError, ValueError):
        print("affiliate bootstrap: failed closed", file=sys.stderr)
        sys.exit(1)
PY
