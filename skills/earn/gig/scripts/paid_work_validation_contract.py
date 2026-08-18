#!/usr/bin/env python3
"""Run a pre-existing, project-owned paid-work validation contract.

The contract is snapshotted before the paid agent starts.  Agent-authored
``PASS`` fields are never a trust boundary: this module re-runs the immutable
argv commands and built-in artifact checks after the agent exits.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


CONTRACT_RELATIVE_PATH = Path("delivery/validation-contract.json")
ALLOWED_EXECUTABLES = frozenset(
    ("python", "python3", "pytest", "node", "npm", "npx", "go", "cargo", "make", "unzip")
)
PLACEHOLDERS = frozenset(
    ("project_root", "artifact_path", "artifact_version", "acceptance_path", "requirements_path")
)
COMMAND_KINDS = frozenset(("build", "test", "domain"))
ARTIFACT_TYPES = frozenset(("file", "zip"))
# The paid agent and its project files never choose the validator image.  This
# harness-owned local image is allowlisted here and Docker is forbidden from
# pulling a replacement during validation.
VALIDATOR_IMAGE = "openclaw-sandbox:bookworm-slim"
CONTAINER_PROJECT_ROOT = PurePosixPath("/workspace")


class ContractError(ValueError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _owned_relative(root: Path, value: Any, label: str) -> Path:
    raw = str(value or "")
    path = Path(raw)
    if not raw or path.is_absolute():
        raise ContractError(f"{label}_must_be_project_relative")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ContractError(f"{label}_outside_project_root") from exc
    return resolved


def parse_contract(content: bytes) -> dict[str, Any]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("acceptance_contract_missing_or_invalid") from exc
    if not isinstance(value, dict) or value.get("version") != 1:
        raise ContractError("acceptance_contract_missing_or_invalid")

    artifact = value.get("artifact")
    if not isinstance(artifact, dict):
        raise ContractError("acceptance_contract_artifact_invalid")
    minimum = artifact.get("min_size_bytes")
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ContractError("acceptance_contract_artifact_min_size_invalid")
    artifact_type = artifact.get("type")
    if artifact_type not in ARTIFACT_TYPES:
        raise ContractError("acceptance_contract_artifact_type_invalid")
    suffixes = artifact.get("allowed_suffixes")
    if (
        not isinstance(suffixes, list)
        or not suffixes
        or not all(isinstance(item, str) and item.startswith(".") and len(item) > 1 for item in suffixes)
    ):
        raise ContractError("acceptance_contract_artifact_suffixes_invalid")
    if artifact_type == "zip" and artifact.get("safe_archive_paths") is not True:
        raise ContractError("acceptance_contract_zip_safety_required")

    trusted_files = value.get("trusted_files")
    if (
        not isinstance(trusted_files, list)
        or not trusted_files
        or not all(isinstance(item, str) and item.strip() for item in trusted_files)
        or len(set(trusted_files)) != len(trusted_files)
    ):
        raise ContractError("acceptance_contract_trusted_files_invalid")

    trusted_set = set(trusted_files)
    commands = value.get("commands")
    if not isinstance(commands, list) or not commands:
        raise ContractError("acceptance_contract_commands_invalid")
    identifiers: set[str] = set()
    kinds: set[str] = set()
    placeholder_pattern = re.compile(r"\{([^{}]+)\}")
    for command in commands:
        if not isinstance(command, dict):
            raise ContractError("acceptance_contract_command_invalid")
        identifier = command.get("id")
        kind = command.get("kind")
        argv = command.get("argv")
        timeout = command.get("timeout_seconds")
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            raise ContractError("acceptance_contract_command_id_invalid")
        identifiers.add(identifier)
        if kind not in COMMAND_KINDS:
            raise ContractError("acceptance_contract_command_kind_invalid")
        kinds.add(kind)
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
            raise ContractError("acceptance_contract_command_argv_invalid")
        executable = Path(argv[0]).name
        if argv[0] != executable or executable not in ALLOWED_EXECUTABLES:
            raise ContractError("acceptance_contract_command_executable_forbidden")
        if executable in ("python", "python3") and len(argv) > 1 and argv[1] in ("-c", "-"):
            raise ContractError("acceptance_contract_inline_code_forbidden")
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 900:
            raise ContractError("acceptance_contract_command_timeout_invalid")
        used = {name for token in argv for name in placeholder_pattern.findall(token)}
        if not used.issubset(PLACEHOLDERS):
            raise ContractError("acceptance_contract_placeholder_invalid")
        # A pre-run contract is not a trust boundary if its argv loads a test
        # or validator that the paid agent can rewrite before execution.  Pin
        # mechanically identifiable project files as immutable trusted_files.
        referenced = {
            token
            for token in argv[1:]
            if "{" not in token
            and not token.startswith("-")
            and Path(token).suffix.casefold() in {".py", ".js", ".json", ".toml", ".yaml", ".yml"}
        }
        if any(Path(token).is_absolute() or ".." in Path(token).parts for token in referenced):
            raise ContractError("acceptance_contract_argv_file_outside_project")
        if not referenced.issubset(trusted_set):
            raise ContractError("acceptance_contract_argv_file_untrusted")
        if executable in ("npm", "npx") and "package.json" not in trusted_set:
            raise ContractError("acceptance_contract_package_manifest_untrusted")
        if executable == "make" and not ({"Makefile", "makefile"} & trusted_set):
            raise ContractError("acceptance_contract_makefile_untrusted")
        if executable == "go" and "go.mod" not in trusted_set:
            raise ContractError("acceptance_contract_go_mod_untrusted")
        if executable == "cargo" and "Cargo.toml" not in trusted_set:
            raise ContractError("acceptance_contract_cargo_manifest_untrusted")
        expected_json = command.get("expect_stdout_json", {})
        if not isinstance(expected_json, dict):
            raise ContractError("acceptance_contract_stdout_expectation_invalid")
    if not {"test", "domain"}.issubset(kinds):
        raise ContractError("acceptance_contract_test_and_domain_commands_required")
    return value


def trusted_paths(contract: dict[str, Any], root: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for relative in contract["trusted_files"]:
        resolved = _owned_relative(root, relative, "acceptance_contract_trusted_file")
        if not resolved.is_file() or resolved.stat().st_size == 0:
            raise ContractError("acceptance_contract_trusted_file_missing_or_empty")
        paths[relative] = resolved
    return paths


def _expanded_argv(argv: list[str], context: dict[str, str]) -> list[str]:
    class Strict(dict[str, str]):
        def __missing__(self, key: str) -> str:
            raise ContractError(f"acceptance_contract_placeholder_unknown:{key}")

    return [token.format_map(Strict(context)) for token in argv]


def _container_owned_path(root: Path, path: Path, label: str) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except (OSError, ValueError) as exc:
        raise ContractError(f"acceptance_contract_{label}_outside_project") from exc
    return str(CONTAINER_PROJECT_ROOT.joinpath(*relative.parts))


def _validator_docker_executable() -> str:
    configured = os.environ.get("GIG_PAID_VALIDATOR_DOCKER")
    if configured:
        candidate = Path(configured).expanduser().resolve()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        raise ContractError("acceptance_contract_sandbox_unavailable")
    discovered = shutil.which("docker")
    if not discovered:
        raise ContractError("acceptance_contract_sandbox_unavailable")
    return str(Path(discovered).resolve())


# Observed live on 2026-07-25: colima down => rc=1 "dial unix /var/run/docker.sock",
# VM recreated => rc=125 "No such image: openclaw-sandbox:bookworm-slim".
_INFRA_STDERR_SIGNATURES = (
    b"docker.sock",
    b"cannot connect to the docker daemon",
    b"error during connect",
    b"no such image",
    b"unable to find image",
    b"docker daemon",
)


def _sandbox_infra_failure(rc: int, stderr: bytes) -> bool:
    if rc == 127:
        return True
    lowered = stderr.lower()
    return any(signature in lowered for signature in _INFRA_STDERR_SIGNATURES)


def _docker_argv(docker: str, root: Path, command_argv: list[str]) -> list[str]:
    mount = f"type=bind,src={root.resolve()},dst={CONTAINER_PROJECT_ROOT},readonly"
    return [
        docker,
        "run", "--rm",
        "--network", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--mount", mount,
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
        "-w", str(CONTAINER_PROJECT_ROOT),
        "--pull", "never",
        VALIDATOR_IMAGE,
        *command_argv,
    ]


def _artifact_errors(contract: dict[str, Any], artifact: Path) -> list[str]:
    spec = contract["artifact"]
    errors: list[str] = []
    if not artifact.is_file():
        return ["artifact_contract_file_missing"]
    if artifact.stat().st_size < int(spec["min_size_bytes"]):
        errors.append("artifact_contract_too_small")
    if artifact.suffix.casefold() not in {str(item).casefold() for item in spec["allowed_suffixes"]}:
        errors.append("artifact_contract_suffix_forbidden")
    if spec["type"] == "zip":
        try:
            with zipfile.ZipFile(artifact) as archive:
                members = archive.infolist()
                if not members or archive.testzip() is not None:
                    errors.append("artifact_contract_zip_integrity_failed")
                for member in members:
                    path = PurePosixPath(member.filename)
                    if path.is_absolute() or ".." in path.parts:
                        errors.append("artifact_contract_zip_unsafe_path")
                        break
        except (OSError, zipfile.BadZipFile):
            errors.append("artifact_contract_zip_integrity_failed")
    return errors


def run_contract(
    contract: dict[str, Any],
    root: Path,
    *,
    artifact: Path,
    artifact_version: str,
    acceptance: Path,
    requirements: Path,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Execute snapshotted argv without a shell and return durable evidence.

    This deterministic validator runs on the host only after the provider has
    exited.  It is deliberately separate from the OpenClaw agent sandbox: the
    sandbox limits agent mutation, while this immutable contract decides truth.
    """
    errors = _artifact_errors(contract, artifact)
    context = {
        "project_root": str(CONTAINER_PROJECT_ROOT),
        "artifact_path": _container_owned_path(root, artifact, "artifact"),
        "artifact_version": artifact_version,
        "acceptance_path": _container_owned_path(root, acceptance, "acceptance"),
        "requirements_path": _container_owned_path(root, requirements, "requirements"),
    }
    rows: list[dict[str, Any]] = []
    # Do not inherit credentials, HOME, Docker config, proxy variables, or any
    # other host environment into the Docker CLI or validation container.
    docker_env = {"PATH": os.defpath, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}
    docker: str | None = None
    if not errors:
        try:
            docker = _validator_docker_executable()
        except ContractError as exc:
            errors.append(str(exc))
    if not errors:
        assert docker is not None
        for command in contract["commands"]:
            argv = _expanded_argv(command["argv"], context)
            sandbox_argv = _docker_argv(docker, root, argv)
            started = time.monotonic()
            rc = 124
            timed_out = False
            stdout = b""
            stderr = b""
            try:
                result = subprocess.run(
                    sandbox_argv,
                    cwd=Path("/"),
                    env=docker_env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=int(command["timeout_seconds"]),
                    check=False,
                )
                rc = result.returncode
                stdout = result.stdout
                stderr = result.stderr
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                stdout = exc.stdout or b""
                stderr = exc.stderr or b""
            except OSError as exc:
                rc = 127
                stderr = str(exc).encode("utf-8", errors="replace")
            row = {
                "id": command["id"],
                "kind": command["kind"],
                "argv": argv,
                "sandbox_argv": sandbox_argv,
                "sandbox_image": VALIDATOR_IMAGE,
                "timeout_seconds": command["timeout_seconds"],
                "duration_ms": round((time.monotonic() - started) * 1000),
                "rc": rc,
                "timed_out": timed_out,
                "stdout_sha256": _sha256_bytes(stdout),
                "stderr_sha256": _sha256_bytes(stderr),
                "stdout_tail": stdout.decode("utf-8", errors="replace")[-2000:],
                "stderr_tail": stderr.decode("utf-8", errors="replace")[-2000:],
            }
            rows.append(row)
            if rc != 0 or timed_out:
                if _sandbox_infra_failure(rc, stderr):
                    # Docker itself is unusable (daemon down, image missing,
                    # binary gone). The artifact was never judged, so report an
                    # infra failure instead of rejecting the agent's work.
                    errors.append(f"sandbox_infra_unavailable:{command['id']}")
                else:
                    errors.append(f"acceptance_contract_command_failed:{command['id']}")
                break
            expected_json = command.get("expect_stdout_json", {})
            if expected_json:
                try:
                    actual = json.loads(stdout.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    errors.append(f"acceptance_contract_stdout_json_invalid:{command['id']}")
                    break
                if not isinstance(actual, dict) or any(actual.get(key) != value for key, value in expected_json.items()):
                    errors.append(f"acceptance_contract_stdout_json_mismatch:{command['id']}")
                    break
    after_errors = _artifact_errors(contract, artifact)
    errors.extend(error for error in after_errors if error not in errors)
    evidence = {
        "contract_version": contract["version"],
        "artifact": {
            "path": str(artifact),
            "size_bytes": artifact.stat().st_size if artifact.is_file() else 0,
            "sha256": _sha256_bytes(artifact.read_bytes()) if artifact.is_file() else None,
            "constraints": contract["artifact"],
        },
        "commands": rows,
    }
    return not errors, errors, evidence
