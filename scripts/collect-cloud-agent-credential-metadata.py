#!/usr/bin/env python3
"""Collect safe credential-reference metadata without emitting credential values.

Only official OpenClaw metadata commands are called. Their raw JSON is parsed in
memory and immediately reduced to an allowlisted projection; it is never logged
or persisted.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


REPO = Path(__file__).resolve().parents[1]
PRODUCTION_REPO = REPO
KERNEL_TRUST_ANCHOR = Path(os.path.sep)
DEFAULT_PARENT = REPO / "docs" / "reference" / "cloud-agent-loop-inventory.tsv"
SAFE_AGENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,127}$")
SAFE_PROVIDER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
SAFE_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SECRETS_AUDIT_CODES = frozenset(
    {"PLAINTEXT_FOUND", "REF_UNRESOLVED", "REF_SHADOWED", "LEGACY_RESIDUE"}
)
REFERENCE_HINT = re.compile(
    r"(?:KEY|TOKEN|SECRET|PASSWORD|PRIVATE|WEBHOOK|CREDENTIAL|AUTH|ACCOUNT_SID|DATABASE_URL|REDIS_URL|MONGODB_URI)"
)
TYPESCRIPT_VERSION = "5.5.4"
TYPESCRIPT_RESOLVED = "https://registry.npmjs.org/typescript/-/typescript-5.5.4.tgz"
TYPESCRIPT_NPM_INTEGRITY = "sha512-Mtq29sKDAEYP7aljRgtPOpTvOfbwRWlS6dPRzwjdE+C0R4brX/GUyhHSecbHMFLNBLcJIPt9nl9yG5TZ1weH+Q=="
TYPESCRIPT_ARTIFACT_SHA256 = "f7ff3e27aafe5dcc82d0307575e9a7dc5b053b141da123bec81c858537765b56"
TYPESCRIPT_TOOL = Path("tools/credential-ast-parser")
TYPESCRIPT_TOOL_NAME = "@anicca/credential-ast-parser"
TYPESCRIPT_TOOL_VERSION = "1.0.0"
SUPPORTED_SOURCE_EXTENSIONS = (".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx")
NODE_VERIFIED_FD_BOOTSTRAP = r'''
const fs = require("node:fs");
const path = require("node:path");
const Module = require("node:module");
const [projectorPath, typescriptPath, sourcePath, projectorFd, typescriptFd, sourceFd] = process.argv.slice(1);
function compileFromFd(fd, filename) {
  const loaded = new Module(filename, module);
  loaded.filename = filename;
  loaded.paths = Module._nodeModulePaths(path.dirname(filename));
  loaded._compile(fs.readFileSync(Number(fd), "utf8"), filename);
  return loaded;
}
const typescriptModule = compileFromFd(typescriptFd, typescriptPath);
Module._cache[typescriptPath] = typescriptModule;
global.__credentialInventoryTypeScript = typescriptModule.exports;
process.argv = [process.execPath, projectorPath, typescriptPath, sourcePath, sourceFd];
compileFromFd(projectorFd, projectorPath);
'''
CRON_LIST_ARGVS = tuple(
    (
        "openclaw", "gateway", "call", "cron.list",
        "--params", f'{{"includeDisabled":true,"limit":200,"offset":{offset}}}',
        "--json", "--timeout", "30000",
    )
    for offset in (0, 200)
)
CRON_LIST_ARGV = CRON_LIST_ARGVS[0]
CRON_SAFE_JQ_DEFS = r'''def safe_agent: if type == "string" and test("^[a-z0-9][a-z0-9-]{0,127}$") then . else "unverified" end;
def safe_provider: if type == "string" and test("^[a-z0-9][a-z0-9_-]{0,63}$") then . else "unverified" end;
def safe_model: if type == "string" and test("^[a-z0-9][a-z0-9_-]{0,63}/[A-Za-z0-9._:-]+$") then . else "unverified" end;
def safe_tool: select(type == "string" and test("^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"));
def safe_kind: . as $kind | if type == "string" and (["agentTurn", "systemEvent", "command", "script"] | index($kind)) then $kind else "unverified" end;
def safe_job: select(.id | type == "string" and test("^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"))
  | {
      job_id: .id,
      enabled: (.enabled == true),
      agent_id: ((.agentId // .owner.agentId // "unverified") | safe_agent),
      payload_kind: (.payload.kind | safe_kind),
      model_ref: ((.payload.model // "inherited") | if . == "inherited" then . else safe_model end),
      fallback_refs: [(.payload.fallbacks // [])[] | safe_model | select(. != "unverified")],
      fallbacks_inherited: ((.payload.fallbacks | type) != "array"),
      tools_allow: [(.payload.toolsAllow // [])[] | safe_tool],
      tools_inherited: ((.payload.toolsAllow | type) != "array"),
      delivery_provider: ((.delivery.channel // "none") | safe_provider)
    };
'''
CRON_SAFE_JQ_ARGV = (
    "jq",
    "-c",
    CRON_SAFE_JQ_DEFS + r'''{schema_version: 1,
  total: (if (.total | type) == "number" then .total else -1 end),
  offset: (if (.offset | type) == "number" then .offset else -1 end),
  limit: (if (.limit | type) == "number" then .limit else -1 end),
  has_more: (.hasMore == true),
  jobs: [(.jobs // [])[]
  | select(.id | type == "string" and test("^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"))
  | safe_job]}
''',
)
CRON_GET_SAFE_JQ_ARGV = (
    "jq",
    "-c",
    CRON_SAFE_JQ_DEFS + r'''if ((.error.code // .code // "") == "NOT_FOUND")
      then {schema_version: 1, jobs: [], result: "not_found", error_code: "NOT_FOUND"}
      else {schema_version: 1, jobs: [(.job // .) | safe_job], result: "found", error_code: "none"}
      end''',
)
CRON_ERROR_CLASSIFIER_ARGV = (
    "awk",
    r'''BEGIN { class="gateway_error"; seen=0 }
{
  seen=1; line=tolower($0)
  if (line ~ /(unauthorized|forbidden|authentication|permission denied|(^|[^0-9])(401|403)([^0-9]|$))/) class="auth_error"
  else if (line ~ /(timed out|timeout|deadline)/ && class != "auth_error") class="timeout"
  else if (line ~ /(not found|not_found)/ && class !~ /^(auth_error|timeout)$/) class="unstructured_not_found"
  else if (line ~ /(invalid json|parse error|syntax error)/ && class == "gateway_error") class="parse_error"
}
END { print (seen ? class : "gateway_error") }''',
)
LAUNCHD_SAFE_JQ_ARGV = (
    "jq",
    "-c",
    r'''def candidates:
      . as $value
      | if (test("^(?:/|~/|\\./|[A-Za-z0-9._@+:-]+/)") and (test("[;&|<>]") | not)) then $value
        else ([scan("(?:~/|/)[A-Za-z0-9._@+:-]+(?:/[A-Za-z0-9._@+:-]+)*")] as $absolute
              | if ($absolute | length) > 0 then $absolute[]
                else scan("(?:\\./|[A-Za-z0-9._@+:-]+/)[A-Za-z0-9._@+:/-]+")
                end)
        end;
    {schema_version: 2,
     program:
       ((.Program // "unverified")
        | if (type == "string" and test("^(?:/|~/)")
              and (test("(?i)(?:^|/)(?:[^/]*\\.env(?:\\.[^/]*)?|\\.env(?:\\.[^/]*)?)(?:$|/)|prompt|payload") | not))
          then . else "unverified" end),
     working_directory:
       ((.WorkingDirectory // "unverified")
        | if (type == "string" and test("^(?:/|~/)")
              and (test("(?i)(?:^|/)(?:[^/]*\\.env(?:\\.[^/]*)?|\\.env(?:\\.[^/]*)?)(?:$|/)|prompt|payload") | not))
          then . else "unverified" end),
     argument_count: (if (.ProgramArguments | type) == "array" then (.ProgramArguments | length) else 0 end),
     paths:
       [([.Program] + (.ProgramArguments // []))[]
        | select(type == "string")
        | candidates
        | select(startswith("/dev/") | not)
        | select(test("(?i)(?:^|/)(?:[^/]*\\.env(?:\\.[^/]*)?|\\.env(?:\\.[^/]*)?)(?:$|/)|prompt|payload") | not)]
       | unique}''',
)


def format_sha256_digest(hex_digest: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", hex_digest) is None:
        raise ValueError("sha256 digest must contain 64 lowercase hex characters")
    return "sha256:" + ":".join(
        hex_digest[index : index + 8] for index in range(0, 64, 8)
    )


class CronProjectionError(RuntimeError):
    def __init__(self, error_class: str):
        super().__init__("cron metadata command failed: " + error_class)
        self.error_class = error_class


def canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return format_sha256_digest(hashlib.sha256(encoded).hexdigest())


def parent_metadata_digest(row: dict[str, str]) -> str:
    return canonical_digest({key: row[key] for key in sorted(row)})


def safe_profile_alias(agent_id: str, profile_id: str) -> str:
    digest = hashlib.sha256(f"{agent_id}\0{profile_id}".encode()).hexdigest()[:16]
    return f"sha256:{digest}"


def project_agents_list(raw: object) -> dict[str, dict[str, str]]:
    if not isinstance(raw, list):
        raise ValueError("agents list projection requires an array")
    result: dict[str, dict[str, str]] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        agent_id = item.get("id")
        model = item.get("model")
        if not isinstance(agent_id, str) or not SAFE_AGENT_ID.fullmatch(agent_id):
            continue
        if not isinstance(model, str) or "/" not in model:
            continue
        result[agent_id] = {"model": model}
    return result


def project_auth_list(raw: object, agent_id: str = "default") -> list[dict[str, str]]:
    if not isinstance(raw, dict) or not isinstance(raw.get("profiles"), list):
        raise ValueError("auth list projection requires profiles")
    result: list[dict[str, str]] = []
    for profile in raw["profiles"]:
        if not isinstance(profile, dict):
            continue
        profile_id = profile.get("id")
        provider = profile.get("provider")
        profile_type = profile.get("type")
        if not all(isinstance(value, str) for value in (profile_id, provider, profile_type)):
            continue
        if not SAFE_PROVIDER.fullmatch(provider):
            continue
        if profile_type not in {"api_key", "token", "oauth"}:
            continue
        result.append(
            {
                "alias": safe_profile_alias(agent_id, profile_id),
                "provider": provider,
                "type": profile_type,
            }
        )
    return sorted(result, key=lambda item: (item["provider"], item["type"], item["alias"]))


def _provider_from_model(model: object) -> str | None:
    if not isinstance(model, str) or "/" not in model:
        return None
    provider = model.split("/", 1)[0].strip().lower()
    return provider if SAFE_PROVIDER.fullmatch(provider) else None


def project_models_status(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ValueError("models status projection requires an object")
    default_model = raw.get("defaultModel")
    fallbacks = raw.get("fallbacks") if isinstance(raw.get("fallbacks"), list) else []
    provider_chain = [
        provider
        for provider in (_provider_from_model(value) for value in [default_model, *fallbacks])
        if provider
    ]
    auth = raw.get("auth") if isinstance(raw.get("auth"), dict) else {}
    providers: list[dict[str, object]] = []
    for entry in auth.get("providers", []) if isinstance(auth.get("providers"), list) else []:
        if not isinstance(entry, dict) or not isinstance(entry.get("provider"), str):
            continue
        provider = entry["provider"].lower()
        counts = entry.get("profiles") if isinstance(entry.get("profiles"), dict) else {}
        if not SAFE_PROVIDER.fullmatch(provider):
            continue
        providers.append(
            {
                "provider": provider,
                "profile_counts": {
                    key: int(counts.get(key, 0))
                    for key in ("count", "oauth", "token", "apiKey")
                    if isinstance(counts.get(key, 0), int)
                },
            }
        )
    missing = [
        value
        for value in auth.get("missingProvidersInUse", [])
        if isinstance(value, str) and SAFE_PROVIDER.fullmatch(value)
    ] if isinstance(auth.get("missingProvidersInUse"), list) else []
    return {
        "provider_chain": list(dict.fromkeys(provider_chain)),
        "auth_providers": sorted(providers, key=lambda item: str(item["provider"])),
        "missing_providers": sorted(set(missing)),
    }


def project_secrets_audit(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ValueError("secrets audit projection requires an object")
    summary = raw.get("summary") if isinstance(raw.get("summary"), dict) else {}
    resolution = raw.get("resolution") if isinstance(raw.get("resolution"), dict) else {}
    counts: dict[str, int] = {}
    for finding in raw.get("findings", []) if isinstance(raw.get("findings"), list) else []:
        if not isinstance(finding, dict) or not isinstance(finding.get("code"), str):
            continue
        if finding["code"] not in SECRETS_AUDIT_CODES:
            raise ValueError("unknown secrets audit finding code")
        provider = finding.get("provider")
        safe_provider = provider if isinstance(provider, str) and SAFE_PROVIDER.fullmatch(provider) else "unattributed"
        key = f"{finding['code']}:{safe_provider}"
        counts[key] = counts.get(key, 0) + 1
    return {
        "status": raw.get("status") if raw.get("status") in {"clean", "findings", "unresolved"} else "unverified",
        "summary": {
            key: int(summary.get(key, 0))
            for key in ("plaintextCount", "unresolvedRefCount", "shadowedRefCount", "legacyResidueCount")
            if isinstance(summary.get(key, 0), int)
        },
        "resolution": {
            "refsChecked": int(resolution.get("refsChecked", 0)),
            "skippedExecRefs": int(resolution.get("skippedExecRefs", 0)),
            "resolvabilityComplete": resolution.get("resolvabilityComplete") is True,
        },
        "finding_counts": dict(sorted(counts.items())),
    }


def _run(argv: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=60)


def run_json(argv: tuple[str, ...], runner: Callable = _run) -> object:
    allowed = {
        ("openclaw", "config", "schema"),
        ("openclaw", "config", "validate", "--json"),
        ("openclaw", "agents", "list", "--json"),
        ("openclaw", "secrets", "audit", "--json"),
    }
    agent_dynamic = (
        len(argv) == 6
        and argv[:4] == ("openclaw", "models", "status", "--agent")
        and SAFE_AGENT_ID.fullmatch(argv[4]) is not None
        and argv[5] == "--json"
    )
    auth_dynamic = (
        len(argv) == 7
        and argv[:5] == ("openclaw", "models", "auth", "list", "--agent")
        and SAFE_AGENT_ID.fullmatch(argv[5]) is not None
        and argv[6] == "--json"
    )
    if argv not in allowed and not agent_dynamic and not auth_dynamic:
        raise ValueError("command is outside safe metadata allowlist")
    completed = runner(argv)
    return json.loads(completed.stdout)


def _fixed_cron_projection(
    producer_argv: tuple[str, ...], projector_argv: tuple[str, ...]
) -> dict[str, object]:
    valid_get = False
    if (
        len(producer_argv) == 9
        and producer_argv[:5] == ("openclaw", "gateway", "call", "cron.get", "--params")
        and producer_argv[6:] == ("--json", "--timeout", "30000")
        and projector_argv == CRON_GET_SAFE_JQ_ARGV
    ):
        try:
            params = json.loads(producer_argv[5])
        except json.JSONDecodeError:
            params = None
        valid_get = (
            isinstance(params, dict)
            and set(params) == {"id"}
            and isinstance(params["id"], str)
            and SAFE_JOB_ID.fullmatch(params["id"]) is not None
            and producer_argv[5] == json.dumps(params, separators=(",", ":"))
        )
    if not (producer_argv in CRON_LIST_ARGVS and projector_argv == CRON_SAFE_JQ_ARGV) and not valid_get:
        raise ValueError("cron command is outside fixed projection allowlist")
    producer = subprocess.Popen(
        producer_argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if producer.stdout is None or producer.stderr is None:
        producer.kill()
        raise RuntimeError("cron metadata pipe unavailable")
    classifier = subprocess.Popen(
        CRON_ERROR_CLASSIFIER_ARGV,
        stdin=producer.stderr,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    producer.stderr.close()
    try:
        projected = subprocess.run(
            projector_argv,
            stdin=producer.stdout,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        producer.stdout.close()
        producer_returncode = producer.wait(timeout=60)
        classified_stderr, _ = classifier.communicate(timeout=60)
    error_class = classified_stderr.strip()
    if error_class not in {
        "auth_error", "timeout", "unstructured_not_found", "parse_error", "gateway_error",
    }:
        error_class = "gateway_error"
    try:
        value = json.loads(projected.stdout)
    except (json.JSONDecodeError, TypeError):
        if producer_returncode != 0:
            raise CronProjectionError(error_class)
        raise RuntimeError("cron metadata projection invalid")
    if not isinstance(value, dict) or not isinstance(value.get("jobs"), list):
        raise RuntimeError("cron metadata projection invalid")
    if valid_get:
        if set(value) != {"schema_version", "jobs", "result", "error_code"}:
            raise RuntimeError("cron get projection invalid")
        explicit_not_found = (
            value.get("schema_version") == 1
            and value.get("jobs") == []
            and value.get("result") == "not_found"
            and value.get("error_code") == "NOT_FOUND"
        )
        if producer_returncode != 0 and not explicit_not_found:
            raise CronProjectionError(error_class)
    elif producer_returncode != 0:
        raise CronProjectionError(error_class)
    return value


def run_cron_metadata_projection(
    expected_job_ids: tuple[str, ...] = (),
) -> dict[str, object]:
    """Return only fixed allowlisted cron metadata; raw job JSON never reaches this process."""
    jobs: dict[str, dict[str, object]] = {}
    pages: list[dict[str, object]] = []
    for argv in CRON_LIST_ARGVS:
        value = _fixed_cron_projection(argv, CRON_SAFE_JQ_ARGV)
        pages.append(value)
        jobs.update(
            {
                job["job_id"]: job
                for job in value["jobs"]
                if isinstance(job, dict) and isinstance(job.get("job_id"), str)
            }
        )
    totals = {page.get("total") for page in pages}
    list_complete = (
        len(totals) == 1
        and next(iter(totals), -1) == len(jobs)
        and all(isinstance(value, int) and value >= 0 for value in totals)
        and pages[-1].get("has_more") is False
    )
    missing_jobs: list[dict[str, object]] = []
    for job_id in expected_job_ids:
        if job_id in jobs:
            continue
        if SAFE_JOB_ID.fullmatch(job_id) is None:
            raise ValueError("cron job id is outside safe allowlist")
        try:
            projected = _fixed_cron_projection(
                (
                    "openclaw", "gateway", "call", "cron.get",
                    "--params", json.dumps({"id": job_id}, separators=(",", ":")),
                    "--json", "--timeout", "30000",
                ),
                CRON_GET_SAFE_JQ_ARGV,
            )
        except CronProjectionError as error:
            missing_jobs.append(
                {
                    "job_id": job_id,
                    "result": "unverified",
                    "list_complete": list_complete,
                    "individual_get": error.error_class,
                }
            )
            continue
        except Exception:
            missing_jobs.append(
                {
                    "job_id": job_id,
                    "result": "unverified",
                    "list_complete": list_complete,
                    "individual_get": "gateway_error",
                }
            )
            continue
        if projected.get("result") == "not_found":
            missing_jobs.append(
                {
                    "job_id": job_id,
                    "result": "not_found" if list_complete else "unverified",
                    "list_complete": list_complete,
                    "individual_get": "not_found",
                }
            )
            continue
        for job in projected["jobs"]:
            if isinstance(job, dict) and job.get("job_id") == job_id:
                jobs[job_id] = job
        if job_id not in jobs:
            missing_jobs.append(
                {
                    "job_id": job_id,
                    "result": "unverified",
                    "list_complete": list_complete,
                    "individual_get": "invalid",
                }
            )
    return {
        "schema_version": 2,
        "jobs": [jobs[key] for key in sorted(jobs)],
        "missing_jobs": sorted(missing_jobs, key=lambda record: str(record["job_id"])),
    }


def read_parent(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _agent_id(parent: dict[str, str]) -> str | None:
    match = re.fullmatch(
        r"openclaw_gateway:agentTurn:agent=([a-z0-9][a-z0-9-]{0,127})",
        parent.get("entrypoint", ""),
    )
    return match.group(1) if match else None


def _safe_path_revision(path: Path, runner: Callable = _run) -> str:
    lowered_parts = {part.lower() for part in path.parts}
    if ".env" in lowered_parts or any(
        marker in part for part in lowered_parts for marker in ("prompt", "payload")
    ):
        return "unverified"
    try:
        completed = runner(("git", "hash-object", "--", str(path)))
    except Exception:
        return "unverified"
    object_id = completed.stdout.strip()
    return (
        canonical_digest({"git_blob": object_id})
        if re.fullmatch(r"[0-9a-f]{40,64}", object_id)
        else "unverified"
    )


def _portable_path(path: Path) -> str:
    path_text = path.as_posix()
    if path_text.startswith((
        "/bin/", "/usr/", "/opt/homebrew/", "/Library/", "/Applications/",
    )):
        return "system:" + path_text
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except (OSError, ValueError):
        pass
    try:
        return "~/" + path.resolve().relative_to(Path.home().resolve()).as_posix()
    except (OSError, ValueError):
        return "external:" + path.name


def _secret_bearing_path(path: Path | str) -> bool:
    parts = Path(path).parts
    for part in parts:
        lowered = part.lower()
        if re.search(r"(?:^|.)\.env(?:\..*)?$", lowered) or any(
            marker in lowered for marker in ("prompt", "payload")
        ):
            return True
    return False


def _blob_oid(path: Path, runner: Callable = _run) -> str | None:
    if _secret_bearing_path(path):
        return None
    try:
        value = runner(("git", "hash-object", "--", str(path))).stdout.strip()
    except Exception:
        return None
    return value if re.fullmatch(r"[0-9a-f]{40,64}", value) else None


def project_launchd_argv_paths(raw_argv: object) -> list[str]:
    if not isinstance(raw_argv, list):
        raise ValueError("launchd argv projection requires an array")
    paths: list[str] = []
    for raw in raw_argv:
        if not isinstance(raw, str):
            continue
        direct_path = raw.startswith(("/", "~/")) and re.search(r"[;&|<>]", raw) is None
        candidates = [raw] if direct_path else re.findall(
            r"(?:~/|/)[A-Za-z0-9._@+:-]+(?:/[A-Za-z0-9._@+:-]+)*"
            r"|(?:\./|[A-Za-z0-9._@+:-]+/)[A-Za-z0-9._@+:/-]+",
            raw,
        )
        if not candidates:
            continue
        for candidate in candidates:
            if candidate.startswith("/dev/"):
                continue
            if _secret_bearing_path(candidate):
                continue
            if candidate not in paths:
                paths.append(candidate)
    return paths


def run_launchd_argv_projection(plist_path: Path) -> list[str]:
    return run_launchd_metadata_projection(plist_path)["paths"]


def run_launchd_metadata_projection(plist_path: Path) -> dict[str, object]:
    if _secret_bearing_path(plist_path):
        raise ValueError("launchd plist path is outside safe projection allowlist")
    producer = subprocess.Popen(
        ("plutil", "-convert", "json", "-o", "-", str(plist_path)),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if producer.stdout is None:
        producer.kill()
        raise RuntimeError("launchd argv pipe unavailable")
    try:
        projected = subprocess.run(
            LAUNCHD_SAFE_JQ_ARGV,
            stdin=producer.stdout,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        producer.stdout.close()
        producer_returncode = producer.wait(timeout=30)
    if producer_returncode != 0:
        raise RuntimeError("launchd argv metadata command failed")
    value = json.loads(projected.stdout)
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != 2
        or not isinstance(value.get("program"), str)
        or not isinstance(value.get("working_directory"), str)
        or not isinstance(value.get("argument_count"), int)
        or value["argument_count"] < 0
        or not isinstance(value.get("paths"), list)
        or value["paths"] != project_launchd_argv_paths(value["paths"])
    ):
        raise RuntimeError("launchd argv projection invalid")
    return value


def _repository_start_path(parent: dict[str, str], repo_root: Path) -> Path | None:
    evidence = parent.get("evidence", "")
    if parent.get("source_type") == "railway_entrypoint":
        match = re.fullmatch(r"https://github\.com/[^/]+/[^/]+/blob/[^/]+/(.+package\.json)", evidence)
        if not match:
            return None
        manifest = match.group(1)
    else:
        manifest = evidence
    package_dir = (repo_root / manifest).parent
    try:
        tokens = shlex.split(parent.get("entrypoint", ""))
    except ValueError:
        return None
    for index, token in enumerate(tokens[:-1]):
        if Path(token).name in {"node", "tsx", "ts-node"}:
            candidate = tokens[index + 1]
            if candidate.startswith("-"):
                continue
            return package_dir / candidate
    return None


@dataclass(frozen=True)
class ResolvedImport:
    path: Path
    descriptor: int


@dataclass(frozen=True)
class TypeScriptModuleCandidate:
    path: Path
    device: int
    inode: int


@dataclass(frozen=True)
class VerifiedTypeScriptModule:
    path: Path
    descriptor: int
    device: int
    inode: int
    sha256: str


def _resolve_import(importer: Path, specifier: str, root: Path) -> ResolvedImport:
    base = importer.parent / specifier
    if base.suffix and base.suffix not in SUPPORTED_SOURCE_EXTENSIONS:
        raise RuntimeError("unsupported local import extension")
    candidates = [base]
    if not base.suffix:
        candidates.extend(base.with_suffix(suffix) for suffix in SUPPORTED_SOURCE_EXTENSIONS)
        candidates.extend(base / ("index" + suffix) for suffix in SUPPORTED_SOURCE_EXTENSIONS)
    for candidate in candidates:
        lexical = Path(os.path.abspath(candidate))
        try:
            lexical.relative_to(root)
        except ValueError as error:
            raise RuntimeError("unsafe local import path") from error
        try:
            metadata = lexical.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise RuntimeError("literal local import unresolved") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise RuntimeError("unsafe local import path")
        if stat.S_ISREG(metadata.st_mode):
            descriptor = _open_lstat_bound_fd(
                lexical, "literal local import", trusted_root=root
            )
            opened = os.fstat(descriptor)
            if (metadata.st_dev, metadata.st_ino) != (opened.st_dev, opened.st_ino):
                os.close(descriptor)
                raise RuntimeError("literal local import replacement detected")
            return ResolvedImport(path=lexical, descriptor=descriptor)
    raise RuntimeError("literal local import unresolved")


def _read_parser_metadata(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"TypeScript parser {label} unavailable") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"TypeScript parser {label} unavailable")
    return value


def _lstat_parser_component(path: Path, root: Path, *, directory: bool) -> None:
    try:
        metadata = path.lstat()
    except OSError as error:
        raise RuntimeError("pinned TypeScript parser unavailable; run documented npm ci bootstrap") from error
    expected_type = stat.S_ISDIR(metadata.st_mode) if directory else stat.S_ISREG(metadata.st_mode)
    if stat.S_ISLNK(metadata.st_mode) or not expected_type:
        raise RuntimeError(
            "TypeScript parser pre-read lstat requires non-symlink components "
            "inside current worktree"
        )
    try:
        path.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as error:
        raise RuntimeError("TypeScript parser pre-read lstat requires current worktree components") from error


def _typescript_module_path(*, repo_root: Path = REPO) -> TypeScriptModuleCandidate:
    root = repo_root.resolve()
    tool = root / TYPESCRIPT_TOOL
    package_root = tool / "node_modules" / "typescript"
    module = package_root / "lib" / "typescript.js"
    components = (
        (root / "tools", True),
        (tool, True),
        (tool / "package.json", False),
        (tool / "package-lock.json", False),
        (tool / "node_modules", True),
        (package_root, True),
        (package_root / "package.json", False),
        (package_root / "lib", True),
        (module, False),
    )
    for component, directory in components:
        _lstat_parser_component(component, root, directory=directory)
    package = _read_parser_metadata(tool / "package.json", "manifest")
    lock = _read_parser_metadata(tool / "package-lock.json", "lock")
    dependencies = package.get("dependencies")
    lock_packages = lock.get("packages")
    lock_root = lock_packages.get("") if isinstance(lock_packages, dict) else None
    lock_typescript = (
        lock_packages.get("node_modules/typescript")
        if isinstance(lock_packages, dict) else None
    )
    if (
        not isinstance(dependencies, dict)
        or dependencies.get("typescript") != TYPESCRIPT_VERSION
        or not isinstance(lock_typescript, dict)
        or lock_typescript.get("version") != TYPESCRIPT_VERSION
    ):
        raise RuntimeError("TypeScript parser exact version mismatch")
    expected_package = {
        "name": TYPESCRIPT_TOOL_NAME,
        "version": TYPESCRIPT_TOOL_VERSION,
        "private": True,
        "dependencies": {"typescript": TYPESCRIPT_VERSION},
    }
    expected_lock_root = {
        "name": TYPESCRIPT_TOOL_NAME,
        "version": TYPESCRIPT_TOOL_VERSION,
        "dependencies": {"typescript": TYPESCRIPT_VERSION},
    }
    if (
        package != expected_package
        or set(lock) != {"name", "version", "lockfileVersion", "requires", "packages"}
        or lock.get("name") != TYPESCRIPT_TOOL_NAME
        or lock.get("version") != TYPESCRIPT_TOOL_VERSION
        or lock.get("requires") is not True
        or not isinstance(lock_packages, dict)
        or set(lock_packages) != {"", "node_modules/typescript"}
        or lock_root != expected_lock_root
    ):
        raise RuntimeError("TypeScript parser manifest/lock mismatch")
    if (
        lock.get("lockfileVersion") != 3
        or lock_typescript.get("resolved") != TYPESCRIPT_RESOLVED
        or lock_typescript.get("integrity") != TYPESCRIPT_NPM_INTEGRITY
    ):
        raise RuntimeError("TypeScript parser lock integrity mismatch")
    installed = _read_parser_metadata(package_root / "package.json", "installation")
    if installed.get("name") != "typescript" or installed.get("version") != TYPESCRIPT_VERSION:
        raise RuntimeError("TypeScript parser exact version mismatch")
    try:
        metadata = module.lstat()
    except OSError as error:
        raise RuntimeError("pinned TypeScript parser unavailable") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError("TypeScript parser pre-read lstat requires non-symlink components")
    return TypeScriptModuleCandidate(
        path=module,
        device=metadata.st_dev,
        inode=metadata.st_ino,
    )


def _open_directory_from_kernel_root(root: Path, label: str) -> int:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory_flag is None:
        raise RuntimeError(f"{label} trust anchor requires directory descriptors")
    flags = os.O_RDONLY | directory_flag | nofollow | getattr(os, "O_CLOEXEC", 0)
    if not root.is_absolute() or root.anchor != os.path.sep:
        raise RuntimeError(f"{label} trust anchor unavailable")
    parts = root.parts[1:]
    if any(component in {"", ".", ".."} for component in parts):
        raise RuntimeError(f"{label} trust anchor unavailable")
    current: int | None = None
    try:
        current = os.open(KERNEL_TRUST_ANCHOR, flags)
        for component in parts:
            child = os.open(component, flags, dir_fd=current)
            if not stat.S_ISDIR(os.fstat(child).st_mode):
                os.close(child)
                raise RuntimeError(f"{label} trust anchor requires directory")
            os.close(current)
            current = child
        return current
    except OSError as error:
        if current is not None:
            os.close(current)
        raise RuntimeError(f"{label} trust anchor unavailable") from error


def _open_lstat_bound_fd(
    path: Path, label: str, *, trusted_root: Path | None = None
) -> int:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise RuntimeError(f"{label} verified fd requires O_NOFOLLOW")
    directory_flag = getattr(os, "O_DIRECTORY", None)
    if directory_flag is None:
        raise RuntimeError(f"{label} verified fd requires directory descriptors")
    root = Path(os.path.abspath(trusted_root if trusted_root is not None else REPO))
    lexical = Path(os.path.abspath(path))
    try:
        parts = lexical.relative_to(root).parts
    except ValueError as error:
        raise RuntimeError(f"{label} verified fd requires current worktree path") from error
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise RuntimeError(f"{label} verified fd requires current worktree path")
    close_on_exit: list[int] = []
    try:
        production_root = Path(os.path.abspath(PRODUCTION_REPO))
        try:
            root.relative_to(production_root)
            kernel_bound = True
        except ValueError:
            kernel_bound = False
        if kernel_bound:
            current = _open_directory_from_kernel_root(root, label)
        else:
            if trusted_root is None and Path(os.path.abspath(REPO)) == production_root:
                raise RuntimeError(
                    f"{label} production repository compatibility fallback denied"
                )
            current = os.open(
                root,
                os.O_RDONLY | directory_flag | nofollow | getattr(os, "O_CLOEXEC", 0),
            )
        close_on_exit.append(current)
        for component in parts[:-1]:
            try:
                child = os.open(
                    component,
                    os.O_RDONLY | directory_flag | nofollow | getattr(os, "O_CLOEXEC", 0),
                    dir_fd=current,
                )
            except OSError as error:
                raise RuntimeError(f"{label} verified fd ancestor unavailable") from error
            if not stat.S_ISDIR(os.fstat(child).st_mode):
                os.close(child)
                raise RuntimeError(f"{label} verified fd ancestor requires directory")
            close_on_exit.append(child)
            current = child
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY | nofollow | getattr(os, "O_CLOEXEC", 0),
            dir_fd=current,
        )
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise RuntimeError(f"{label} verified fd requires regular non-symlink file")
        return descriptor
    except OSError as error:
        raise RuntimeError(f"{label} verified fd unavailable") from error
    finally:
        for directory_descriptor in reversed(close_on_exit):
            os.close(directory_descriptor)


def _fd_sha256(descriptor: int) -> str:
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    while chunk := os.read(descriptor, 1024 * 1024):
        digest.update(chunk)
    os.lseek(descriptor, 0, os.SEEK_SET)
    return digest.hexdigest()


def _open_typescript_module(*, repo_root: Path = REPO) -> VerifiedTypeScriptModule:
    located = _typescript_module_path(repo_root=repo_root)
    if isinstance(located, TypeScriptModuleCandidate):
        candidate = located
    else:
        path = Path(located).resolve(strict=True)
        metadata = path.lstat()
        candidate = TypeScriptModuleCandidate(
            path=path,
            device=metadata.st_dev,
            inode=metadata.st_ino,
        )
    descriptor = _open_lstat_bound_fd(
        candidate.path,
        "TypeScript parser",
        trusted_root=Path(repo_root).resolve(strict=True),
    )
    try:
        opened = os.fstat(descriptor)
        if (candidate.device, candidate.inode) != (opened.st_dev, opened.st_ino):
            raise RuntimeError("TypeScript parser replacement detected")
        digest = _fd_sha256(descriptor)
        if digest != TYPESCRIPT_ARTIFACT_SHA256:
            raise RuntimeError("TypeScript parser artifact digest mismatch")
        return VerifiedTypeScriptModule(
            path=candidate.path,
            descriptor=descriptor,
            device=opened.st_dev,
            inode=opened.st_ino,
            sha256=digest,
        )
    except Exception:
        os.close(descriptor)
        raise


def _fd_git_blob_oid(descriptor: int) -> str:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while chunk := os.read(descriptor, 1024 * 1024):
        chunks.append(chunk)
    content = b"".join(chunks)
    os.lseek(descriptor, 0, os.SEEK_SET)
    return hashlib.sha1(
        b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    ).hexdigest()


def _project_js_ts_source_and_blob(
    path: Path,
    *,
    source_root: Path | None = None,
    verified_source_fd: int | None = None,
) -> tuple[dict[str, object], str]:
    projector = REPO / "scripts" / "project-js-env-references.js"
    descriptors: list[int] = []
    if verified_source_fd is not None:
        descriptors.append(verified_source_fd)
    try:
        verified_typescript = _open_typescript_module(repo_root=REPO)
        typescript_module = verified_typescript.path
        typescript_fd = verified_typescript.descriptor
        descriptors.append(typescript_fd)
        projector_fd = _open_lstat_bound_fd(projector, "JS/TS AST projector")
        descriptors.append(projector_fd)
        source_fd = verified_source_fd
        if source_fd is None:
            source_fd = _open_lstat_bound_fd(
                path,
                "JS/TS source",
                trusted_root=source_root if source_root is not None else REPO,
            )
            descriptors.append(source_fd)
        source_blob = _fd_git_blob_oid(source_fd)
        completed = subprocess.run(
            (
                "node", "-e", NODE_VERIFIED_FD_BOOTSTRAP,
                str(projector), str(typescript_module), str(path),
                str(projector_fd), str(typescript_fd), str(source_fd),
            ),
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
            pass_fds=tuple(descriptors),
        )
        projection = json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        raise RuntimeError("JS/TS AST projection failed") from error
    finally:
        for descriptor in descriptors:
            os.close(descriptor)
    if (
        not isinstance(projection, dict)
        or set(projection) != {
            "imports", "references", "unresolved_dynamic_env", "unresolved_import"
        }
        or not isinstance(projection["imports"], list)
        or not isinstance(projection["references"], list)
        or not isinstance(projection["unresolved_dynamic_env"], bool)
        or not isinstance(projection["unresolved_import"], bool)
    ):
        raise RuntimeError("JS/TS AST projection invalid")
    for specifier in projection["imports"]:
        if not isinstance(specifier, str) or not specifier.startswith("."):
            raise RuntimeError("JS/TS AST import projection invalid")
    for reference in projection["references"]:
        if (
            not isinstance(reference, dict)
            or set(reference) != {"reference_name", "line"}
            or not isinstance(reference["reference_name"], str)
            or re.fullmatch(r"[A-Z][A-Z0-9_]*", reference["reference_name"]) is None
            or REFERENCE_HINT.search(reference["reference_name"]) is None
            or not isinstance(reference["line"], int)
            or reference["line"] <= 0
        ):
            raise RuntimeError("JS/TS AST reference projection invalid")
    return projection, source_blob


def _project_js_ts_source(
    path: Path, *, source_root: Path | None = None
) -> dict[str, object]:
    return _project_js_ts_source_and_blob(path, source_root=source_root)[0]


def collect_repository_reference_evidence(
    parent: dict[str, str], *, repo_root: Path = REPO, runner: Callable = _run
) -> list[dict[str, object]]:
    start = _repository_start_path(parent, repo_root)
    if start is None or not start.is_file():
        raise RuntimeError("start entrypoint source unavailable")
    root = Path(os.path.abspath(repo_root))
    pending: list[Path | ResolvedImport] = [start]
    visited: set[Path] = set()
    records: list[dict[str, object]] = []
    try:
        while pending:
            item = pending.pop()
            source_fd = item.descriptor if isinstance(item, ResolvedImport) else None
            path = Path(os.path.abspath(item.path if isinstance(item, ResolvedImport) else item))
            try:
                if path in visited:
                    continue
                try:
                    relative_path = path.relative_to(root)
                except ValueError:
                    raise RuntimeError("unsafe repository source path")
                parts = relative_path.parts
                if any(parts[index:index + 3] == ("src", "generated", "prisma") for index in range(len(parts) - 2)):
                    continue
                if any(marker in part.lower() for part in path.parts for marker in (".env", "prompt", "payload")):
                    continue
                visited.add(path)
                transferred_source_fd = source_fd
                source_fd = None
                projection, blob = _project_js_ts_source_and_blob(
                    path,
                    source_root=root,
                    verified_source_fd=transferred_source_fd,
                )
                if projection["unresolved_dynamic_env"]:
                    raise RuntimeError("dynamic environment reference unresolved")
                if projection["unresolved_import"]:
                    raise RuntimeError("dynamic local import unresolved")
                relative = path.relative_to(root).as_posix()
                for reference in projection["references"]:
                    name = reference["reference_name"]
                    line_number = reference["line"]
                    records.append(
                        {
                            "reference_name": name,
                            "path": relative,
                            "blob_oid": blob,
                            "line": line_number,
                            "symbol_locator": f"path:{relative};blob:{blob};line:{line_number};symbol:env.{name}",
                        }
                    )
                for specifier in projection["imports"]:
                    pending.append(_resolve_import(path, specifier, root))
            finally:
                if source_fd is not None:
                    os.close(source_fd)
    finally:
        for item in pending:
            if isinstance(item, ResolvedImport):
                os.close(item.descriptor)
    unique = {
        (record["reference_name"], record["path"], record["line"]): record
        for record in records
    }
    return [unique[key] for key in sorted(unique)]


def source_revision_record(
    parent: dict[str, str], runner: Callable = _run
) -> dict[str, str]:
    source_type = parent.get("source_type")
    if source_type in {"repository_entrypoint", "railway_entrypoint"}:
        ref = "origin/main" if source_type == "railway_entrypoint" else "HEAD"
        evidence = parent.get("evidence", "")
        if source_type == "railway_entrypoint":
            match = re.fullmatch(r"https://github\.com/[^/]+/[^/]+/blob/([^/]+)/(.+)", evidence)
            if not match:
                return {"digest": "unverified", "evidence_locator": "unverified"}
            branch, path = match.groups()
            ref = f"origin/{branch}"
        else:
            path = evidence
        try:
            commit = runner(("git", "rev-parse", ref)).stdout.strip()
            tree = runner(("git", "rev-parse", f"{ref}^{{tree}}")).stdout.strip()
            blob = runner(("git", "rev-parse", f"{ref}:{path}")).stdout.strip()
        except Exception:
            return {"digest": "unverified", "evidence_locator": "unverified"}
        if not all(re.fullmatch(r"[0-9a-f]{40,64}", value) for value in (commit, tree, blob)):
            return {"digest": "unverified", "evidence_locator": "unverified"}
        locator = f"git:{ref};commit:{commit};tree:{tree};blob:{blob};path:{path}"
        return {"digest": format_sha256_digest(hashlib.sha256(locator.encode()).hexdigest()), "evidence_locator": locator}
    if source_type == "launchd":
        def launchd_unverified(reason: str) -> dict[str, str]:
            return {"digest": "unverified", "evidence_locator": "unverified", "reason": reason}

        evidence = parent.get("evidence", "")
        plist = Path.home() / evidence[2:] if evidence.startswith("~/") else Path(evidence)
        if not plist.is_absolute():
            return launchd_unverified("invalid_plist_locator")
        try:
            projected = run_launchd_metadata_projection(plist)
        except Exception:
            return launchd_unverified("projection_unavailable")
        components: list[str] = []
        working_value = projected["working_directory"]
        working_directory = (
            Path.home() / working_value[2:]
            if isinstance(working_value, str) and working_value.startswith("~/")
            else Path(working_value) if isinstance(working_value, str) and working_value != "unverified"
            else None
        )
        dynamic_base = working_directory
        for value in projected["paths"]:
            if not isinstance(value, str):
                return launchd_unverified("projection_invalid")
            path = Path.home() / value[2:] if value.startswith("~/") else Path(value)
            if not path.is_absolute():
                if dynamic_base is None:
                    return launchd_unverified("working_directory_unavailable")
                path = dynamic_base / path
            if path.is_dir():
                dynamic_base = path
                continue
            if path.suffix.lower() in {".log", ".jsonl", ".out"}:
                continue
            blob = _blob_oid(path, runner)
            if not blob:
                return launchd_unverified("component_unavailable")
            components.append(f"path:{_portable_path(path)};blob:{blob}")
        if not components:
            return launchd_unverified("no_retrievable_components")
        locator = "launchd-components:" + ",".join(sorted(set(components)))
        return {
            "digest": format_sha256_digest(hashlib.sha256(locator.encode()).hexdigest()),
            "evidence_locator": locator,
            "reason": "none",
        }
    return {"digest": "unverified", "evidence_locator": "unverified"}


def config_revision_record(
    parent: dict[str, str], runner: Callable = _run
) -> dict[str, str]:
    if parent.get("source_type") == "launchd":
        evidence = parent.get("evidence", "")
        path = Path.home() / evidence[2:] if evidence.startswith("~/") else Path(evidence)
        if not path.is_absolute() or _secret_bearing_path(path):
            return {"digest": "unverified", "evidence_locator": "unverified"}
        try:
            projection = run_launchd_metadata_projection(path)
        except Exception:
            return {"digest": "unverified", "evidence_locator": "unverified"}
        digest = canonical_digest(projection)
        locator = f"launchd-safe-config:path:{_portable_path(path)};digest:{digest}"
        return {"digest": digest, "evidence_locator": locator}
    if parent.get("source_type") in {"repository_entrypoint", "railway_entrypoint"}:
        return source_revision_record(parent, runner)
    return {"digest": "unverified", "evidence_locator": "unverified"}


def _safe_entrypoint_path(entrypoint: str) -> Path | None:
    if "<shell-command-redacted>" in entrypoint or entrypoint.startswith("unparsed_"):
        return None
    try:
        tokens = shlex.split(entrypoint)
    except ValueError:
        return None
    candidates = [
        token
        for token in tokens
        if token.startswith(("/", "~/")) and not token.startswith(("/bin/", "/usr/bin/"))
    ]
    if not candidates and len(tokens) == 1 and tokens[0].startswith(("/", "~/")):
        candidates = tokens
    if not candidates:
        return None
    value = candidates[-1]
    return Path.home() / value[2:] if value.startswith("~/") else Path(value)


def source_revision_digest(
    parent: dict[str, str], runner: Callable = _run
) -> str:
    record = source_revision_record(parent, runner)
    if record["digest"] != "unverified":
        return record["digest"]
    source_type = parent.get("source_type")
    if source_type in {"repository_entrypoint", "railway_entrypoint"}:
        ref = "origin/main^{tree}" if source_type == "railway_entrypoint" else "HEAD^{tree}"
        try:
            completed = runner(("git", "rev-parse", ref))
        except Exception:
            return "unverified"
        revision = completed.stdout.strip()
        return canonical_digest({"git_tree": revision}) if re.fullmatch(r"[0-9a-f]{40,64}", revision) else "unverified"
    if source_type == "launchd":
        path = _safe_entrypoint_path(parent.get("entrypoint", ""))
        return _safe_path_revision(path, runner) if path else "unverified"
    return "unverified"


def config_revision_digest(parent: dict[str, str], runner: Callable = _run) -> str:
    record = config_revision_record(parent, runner)
    if record["digest"] != "unverified":
        return record["digest"]
    source_type = parent.get("source_type")
    if source_type == "launchd":
        return "unverified"
    if source_type in {"repository_entrypoint", "railway_entrypoint"}:
        return canonical_digest(
            {"entrypoint": parent.get("entrypoint"), "state": parent.get("state")}
        )
    return "unverified"


def collect(
    parent_path: Path,
    runner: Callable = _run,
    cron_projection: dict[str, object] | None = None,
    reference_scanner: Callable[[dict[str, str]], list[dict[str, object]]] = collect_repository_reference_evidence,
) -> dict[str, object]:
    parents = read_parent(parent_path)
    parent_observations: dict[str, dict[str, object]] = {}
    agents: dict[str, dict[str, object]] = {}
    openclaw_parents = [row for row in parents if row.get("source_type") == "openclaw_cron"]
    try:
        schema_result = runner(("openclaw", "config", "schema"))
        schema_digest = format_sha256_digest(hashlib.sha256(schema_result.stdout.encode()).hexdigest())
        version_result = runner(("openclaw", "--version"))
        version_digest = canonical_digest(version_result.stdout.strip())
        configured = project_agents_list(run_json(("openclaw", "agents", "list", "--json"), runner))
        audit = project_secrets_audit(run_json(("openclaw", "secrets", "audit", "--json"), runner))
    except Exception:
        schema_digest = "unverified"
        version_digest = "unverified"
        configured = {}
        audit = {"status": "unverified", "resolution": {"resolvabilityComplete": False}}
    if cron_projection is None:
        try:
            cron_projection = run_cron_metadata_projection(
                tuple(
                    parent["inventory_id"].removeprefix("openclaw:")
                    for parent in openclaw_parents
                )
            )
        except Exception:
            cron_projection = {"schema_version": 1, "jobs": []}
    cron_jobs = {
        "openclaw:" + job["job_id"]: job
        for job in cron_projection.get("jobs", [])
        if isinstance(job, dict) and isinstance(job.get("job_id"), str)
    }
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    gateway_revision_digest = (
        canonical_digest({"version": version_digest, "schema": schema_digest})
        if version_digest != "unverified" and schema_digest != "unverified"
        else "unverified"
    )
    cron_absence_observations: dict[str, dict[str, object]] = {}
    cron_lookup_failures: dict[str, dict[str, object]] = {}
    for record in cron_projection.get("missing_jobs", []):
        if not isinstance(record, dict):
            continue
        job_id = record.get("job_id")
        exact_projection = set(record) == {
            "job_id", "result", "list_complete", "individual_get"
        }
        if (
            not isinstance(job_id, str)
            or not SAFE_JOB_ID.fullmatch(job_id)
            or not exact_projection
        ):
            continue
        if (
            record.get("result") == "unverified"
            and isinstance(record.get("list_complete"), bool)
            and record.get("individual_get") in {
                "auth_error", "timeout", "unstructured_not_found", "parse_error",
                "gateway_error", "invalid",
            }
        ):
            cron_lookup_failures["openclaw:" + job_id] = {
                "job_id": job_id,
                "result": "unverified",
                "list_complete": record["list_complete"],
                "individual_get": record["individual_get"],
                "gateway_revision_digest": gateway_revision_digest,
                "observed_at": observed_at,
            }
            continue
        if (
            record.get("result") != "not_found"
            or record.get("list_complete") is not True
            or record.get("individual_get") != "not_found"
            or gateway_revision_digest == "unverified"
        ):
            continue
        cron_absence_observations["openclaw:" + job_id] = {
            "job_id": job_id,
            "result": "not_found",
            "list_complete": True,
            "individual_get": "not_found",
            "gateway_revision_digest": gateway_revision_digest,
            "observed_at": observed_at,
        }
    default_agent_id = next(iter(configured)) if len(configured) == 1 else None

    for parent in parents:
        parent_id = parent["inventory_id"]
        source_revision = source_revision_record(parent, runner)
        config_revision = config_revision_record(parent, runner)
        base: dict[str, object] = {
            "parent_metadata_digest": parent_metadata_digest(parent),
            "source_revision_digest": source_revision["digest"],
            "config_revision_digest": config_revision["digest"],
            "source_evidence_locator": source_revision["evidence_locator"],
            "config_evidence_locator": config_revision["evidence_locator"],
            "source_revision_reason": source_revision.get(
                "reason", "none" if source_revision["digest"] != "unverified" else "revision_unavailable"
            ),
        }
        if parent.get("source_type") in {"repository_entrypoint", "railway_entrypoint"}:
            try:
                base["reference_evidence"] = reference_scanner(parent)
                base["reference_inspection_status"] = "verified"
            except Exception:
                base["reference_evidence"] = []
                base["reference_inspection_status"] = "unverified"
        if parent.get("state", "").startswith("parse_error") or parent.get("entrypoint", "").startswith("unparsed_"):
            base.update({"inspection_status": "unverified", "reason": "parse_error"})
        elif parent.get("source_type") == "openclaw_cron":
            agent_id = _agent_id(parent)
            cron_metadata = cron_jobs.get(parent_id)
            cron_absence_evidence = cron_absence_observations.get(parent_id)
            if cron_absence_evidence is not None:
                base["cron_absence_evidence"] = cron_absence_evidence
            cron_lookup_failure = cron_lookup_failures.get(parent_id)
            if cron_lookup_failure is not None:
                base["cron_lookup_failure"] = cron_lookup_failure
            if not agent_id:
                base.update({"inspection_status": "unverified", "reason": "opaque_input"})
            else:
                alias = "agent:" + agent_id
                if alias not in agents:
                    if agent_id not in configured:
                        agents[alias] = {
                            "inspection_status": "unverified",
                            "reason": "agent_not_configured",
                            "profiles": [],
                            "provider_chain": [],
                        }
                    else:
                        try:
                            status = project_models_status(
                                run_json(("openclaw", "models", "status", "--agent", agent_id, "--json"), runner)
                            )
                            profiles = project_auth_list(
                                run_json(("openclaw", "models", "auth", "list", "--agent", agent_id, "--json"), runner),
                                agent_id,
                            )
                            complete = audit.get("resolution", {}).get("resolvabilityComplete") is True
                            finding_counts = audit.get("finding_counts", {})
                            relevant_providers = {profile["provider"] for profile in profiles}
                            relevant_findings = {
                                key: value
                                for key, value in finding_counts.items()
                                if key.rsplit(":", 1)[-1] in relevant_providers
                            } if isinstance(finding_counts, dict) else {}
                            agents[alias] = {
                                "inspection_status": "verified" if complete else "unverified",
                                "reason": "none" if complete else "scan_incomplete",
                                "profiles": profiles,
                                "audit_finding_counts": relevant_findings,
                                **status,
                            }
                        except Exception:
                            agents[alias] = {
                                "inspection_status": "unverified",
                                "reason": "scan_incomplete",
                                "profiles": [],
                                "provider_chain": [],
                            }
                effective_cron_agent = (
                    default_agent_id
                    if isinstance(cron_metadata, dict)
                    and cron_metadata.get("agent_id") == "unverified"
                    else cron_metadata.get("agent_id") if isinstance(cron_metadata, dict) else None
                )
                cron_verified = (
                    isinstance(cron_metadata, dict)
                    and cron_metadata.get("payload_kind") == "agentTurn"
                    and effective_cron_agent == agent_id
                )
                agent_verified = agents[alias]["inspection_status"] == "verified"
                reason = (
                    "cron_metadata_unavailable"
                    if not isinstance(cron_metadata, dict)
                    else agents[alias]["reason"]
                    if not agent_verified
                    else "cron_metadata_mismatch"
                    if not cron_verified
                    else "parent_state_stale"
                    if cron_metadata.get("enabled") != (parent.get("state") == "enabled")
                    else "none"
                )
                gateway_verified = gateway_revision_digest != "unverified"
                version_identity = (
                    version_result.stdout.strip()
                    if gateway_verified and 'version_result' in locals()
                    else "unverified"
                )
                base.update(
                    {
                        "inspection_status": "verified" if agent_verified and cron_verified else "unverified",
                        "reason": reason,
                        "agent_alias": alias,
                        "cron_metadata": cron_metadata if isinstance(cron_metadata, dict) else {},
                        "source_revision_digest": gateway_revision_digest,
                        "config_revision_digest": canonical_digest(
                            {"agent": agents[alias], "cron": cron_metadata}
                        ) if isinstance(cron_metadata, dict) else "unverified",
                        "source_evidence_locator": (
                            f"openclaw:{version_identity};schema:{schema_digest}"
                            if gateway_verified else "unverified"
                        ),
                        "config_evidence_locator": (
                            f"openclaw-cli:cron-list-safe-projection;job:{parent_id.removeprefix('openclaw:')}"
                            if isinstance(cron_metadata, dict) else "unverified"
                        ),
                    }
                )
        else:
            base.update({"inspection_status": "review_required", "reason": "none"})
        parent_observations[parent_id] = base

    return {
        "schema_version": 1,
        "parent_inventory_digest": canonical_digest(
            [parent_metadata_digest(row) for row in parents]
        ),
        "openclaw_revision": {
            "version_digest": version_digest,
            "schema_digest": schema_digest,
        },
        "openclaw_audit": audit,
        "agents": dict(sorted(agents.items())),
        "cron_absence_observations": dict(sorted(cron_absence_observations.items())),
        "cron_lookup_failures": dict(sorted(cron_lookup_failures.items())),
        "parents": dict(sorted(parent_observations.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", type=Path, default=DEFAULT_PARENT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(collect(args.parent), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
