from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,1024}$")
ASSESSMENT_TYPES = {"take_home", "coding_test", "business_case", "live_interview"}
AI_POLICIES = {"explicitly_allowed", "explicitly_prohibited", "unspecified"}
ALLOWED_TRANSITIONS = {
    "detected": {"prepared", "policy_blocked"},
    "prepared": {"executing"},
    "executing": {"verified", "execution_failed"},
    "execution_failed": {"executing"},
    "verified": {"submit_claimed"},
    "submit_claimed": {"submit_started"},
    "submit_started": {"submitted", "submit_unknown"},
}


class AssessmentError(ValueError):
    pass


class SubmissionUncertain(RuntimeError):
    pass


def _clean(value: Any, *, name: str, maximum: int) -> str:
    cleaned = re.sub(r"\s+", " ", str(value or "")).strip()
    if not cleaned:
        raise AssessmentError(f"{name} is required")
    if len(cleaned) > maximum:
        raise AssessmentError(f"{name} exceeds {maximum} characters")
    return cleaned


def _identifier(value: Any, *, name: str) -> str:
    cleaned = str(value or "")
    if not IDENTIFIER_PATTERN.fullmatch(cleaned):
        raise AssessmentError(f"{name} is invalid")
    return cleaned


def classify_ai_policy(rules_text: str) -> str:
    rules = _clean(rules_text, name="assessment rules", maximum=10_000).casefold()
    prohibited = (
        "do not use ai",
        "ai tools are not allowed",
        "ai assistants are not allowed",
        "no ai tools",
        "no chatgpt",
        "outside help is prohibited",
        "without external assistance",
    )
    allowed = (
        "may use ai",
        "ai tools are allowed",
        "ai assistants are allowed",
        "use of ai is allowed",
        "ai tools are permitted",
        "external resources are allowed",
    )
    if any(phrase in rules for phrase in prohibited):
        return "explicitly_prohibited"
    if any(phrase in rules for phrase in allowed):
        return "explicitly_allowed"
    return "unspecified"


def route_assessment(
    *,
    assessment_type: str,
    ai_policy: str,
    proctored: bool,
) -> str:
    if assessment_type not in ASSESSMENT_TYPES:
        raise AssessmentError(f"unsupported assessment type: {assessment_type}")
    if ai_policy not in AI_POLICIES:
        raise AssessmentError(f"unsupported AI policy: {ai_policy}")
    if (
        assessment_type in {"take_home", "business_case"}
        and ai_policy == "explicitly_allowed"
        and not proctored
    ):
        return "autonomous_allowed"
    return "manual_integrity_gate"


def build_manifest(
    *,
    thread_id: str,
    message_id: str,
    company: str,
    role: str,
    assessment_type: str,
    source_url: str,
    deadline: str,
    deadline_source_span: str,
    rules_text: str,
    rules_source_span: str,
    proctored: bool,
) -> dict[str, Any]:
    thread_id = _identifier(thread_id, name="Gmail thread ID")
    message_id = _identifier(message_id, name="Gmail message ID")
    company = _clean(company, name="company", maximum=160)
    role = _clean(role, name="role", maximum=200)
    if assessment_type not in ASSESSMENT_TYPES:
        raise AssessmentError(f"unsupported assessment type: {assessment_type}")
    source_url = _clean(source_url, name="source URL", maximum=2_000)
    parts = urlsplit(source_url)
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
        raise AssessmentError("source URL must be credential-free HTTPS")
    try:
        parsed_deadline = datetime.fromisoformat(deadline)
    except (TypeError, ValueError) as error:
        raise AssessmentError("deadline must be RFC3339") from error
    if parsed_deadline.tzinfo is None or parsed_deadline.utcoffset() is None:
        raise AssessmentError("deadline requires an explicit timezone")
    deadline_source_span = _clean(
        deadline_source_span,
        name="deadline source span",
        maximum=500,
    )
    rules_text = _clean(rules_text, name="assessment rules", maximum=10_000)
    rules_source_span = _clean(
        rules_source_span,
        name="rules source span",
        maximum=1_000,
    )
    ai_policy = classify_ai_policy(rules_text)
    route = route_assessment(
        assessment_type=assessment_type,
        ai_policy=ai_policy,
        proctored=bool(proctored),
    )
    assessment_id = hashlib.sha256(
        f"{thread_id}\n{message_id}\n{source_url}".encode("utf-8")
    ).hexdigest()[:24]
    return {
        "version": 1,
        "assessment_id": assessment_id,
        "thread_id": thread_id,
        "message_id": message_id,
        "company": company,
        "role": role,
        "assessment_type": assessment_type,
        "source_url": source_url,
        "deadline": parsed_deadline.isoformat(),
        "deadline_source_span": deadline_source_span,
        "rules_text": rules_text,
        "rules_source_span": rules_source_span,
        "ai_policy": ai_policy,
        "proctored": bool(proctored),
        "route": route,
    }


class AssessmentStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(path.parent, 0o700)
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS assessments (
              assessment_id TEXT PRIMARY KEY,
              manifest_json TEXT NOT NULL,
              state TEXT NOT NULL,
              fence TEXT,
              receipt_id TEXT,
              outcome_note TEXT
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS assessment_events (
              event_id INTEGER PRIMARY KEY AUTOINCREMENT,
              assessment_id TEXT NOT NULL,
              from_state TEXT,
              to_state TEXT NOT NULL,
              created_at TEXT NOT NULL
            )
            """
        )
        os.chmod(path, 0o600)

    def close(self) -> None:
        self.connection.close()

    def register(self, manifest: dict[str, Any]) -> str:
        assessment_id = _identifier(
            manifest.get("assessment_id"),
            name="assessment ID",
        )
        route = manifest.get("route")
        if route not in {"autonomous_allowed", "manual_integrity_gate"}:
            raise AssessmentError("assessment route is invalid")
        initial_state = (
            "policy_blocked" if route == "manual_integrity_gate" else "detected"
        )
        manifest_json = json.dumps(manifest, ensure_ascii=False, sort_keys=True)
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            existing = self.connection.execute(
                "SELECT manifest_json FROM assessments WHERE assessment_id=?",
                (assessment_id,),
            ).fetchone()
            if existing and existing[0] != manifest_json:
                raise AssessmentError("assessment manifest changed for an existing ID")
            if existing is None:
                self.connection.execute(
                    """
                    INSERT INTO assessments(assessment_id,manifest_json,state)
                    VALUES(?,?,?)
                    """,
                    (assessment_id, manifest_json, initial_state),
                )
                created_at = datetime.now().astimezone().isoformat()
                self.connection.execute(
                    """
                    INSERT INTO assessment_events(
                      assessment_id,from_state,to_state,created_at
                    ) VALUES(?,NULL,'detected',?)
                    """,
                    (assessment_id, created_at),
                )
                if initial_state == "policy_blocked":
                    self.connection.execute(
                        """
                        INSERT INTO assessment_events(
                          assessment_id,from_state,to_state,created_at
                        ) VALUES(?,'detected','policy_blocked',?)
                        """,
                        (assessment_id, created_at),
                    )
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise
        return assessment_id

    def state(self, assessment_id: str) -> str:
        row = self.connection.execute(
            "SELECT state FROM assessments WHERE assessment_id=?",
            (_identifier(assessment_id, name="assessment ID"),),
        ).fetchone()
        if row is None:
            raise KeyError(assessment_id)
        return str(row[0])

    def transition(self, assessment_id: str, target: str) -> None:
        assessment_id = _identifier(assessment_id, name="assessment ID")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            current = self.state(assessment_id)
            if target not in ALLOWED_TRANSITIONS.get(current, set()):
                raise AssessmentError(f"forbidden assessment transition: {current} -> {target}")
            changed = self.connection.execute(
                """
                UPDATE assessments SET state=?
                WHERE assessment_id=? AND state=?
                """,
                (target, assessment_id, current),
            ).rowcount
            if changed != 1:
                raise AssessmentError("assessment state changed concurrently")
            self.connection.execute(
                """
                INSERT INTO assessment_events(
                  assessment_id,from_state,to_state,created_at
                ) VALUES(?,?,?,?)
                """,
                (
                    assessment_id,
                    current,
                    target,
                    datetime.now().astimezone().isoformat(),
                ),
            )
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def claim_submission(self, assessment_id: str) -> str:
        assessment_id = _identifier(assessment_id, name="assessment ID")
        current = self.state(assessment_id)
        if current in {"submit_started", "submit_unknown"}:
            raise SubmissionUncertain("submission outcome is unknown; retry forbidden")
        if current != "verified":
            raise AssessmentError(f"assessment is not submit-ready: {current}")
        fence = uuid.uuid4().hex
        self.transition(assessment_id, "submit_claimed")
        self.connection.execute(
            "UPDATE assessments SET fence=? WHERE assessment_id=? AND state='submit_claimed'",
            (fence, assessment_id),
        )
        return fence

    def _fenced_transition(
        self,
        assessment_id: str,
        fence: str,
        source: str,
        target: str,
        *,
        receipt_id: str | None = None,
        outcome_note: str | None = None,
    ) -> None:
        assessment_id = _identifier(assessment_id, name="assessment ID")
        row = self.connection.execute(
            "SELECT state,fence FROM assessments WHERE assessment_id=?",
            (assessment_id,),
        ).fetchone()
        if row is None or row[0] != source or row[1] != fence:
            raise SubmissionUncertain("assessment submission fence mismatch")
        self.transition(assessment_id, target)
        self.connection.execute(
            """
            UPDATE assessments SET receipt_id=?,outcome_note=?
            WHERE assessment_id=? AND state=?
            """,
            (receipt_id, outcome_note, assessment_id, target),
        )

    def mark_submit_started(self, assessment_id: str, fence: str) -> None:
        self._fenced_transition(
            assessment_id,
            fence,
            "submit_claimed",
            "submit_started",
        )

    def mark_submitted(
        self,
        assessment_id: str,
        fence: str,
        receipt_id: str,
    ) -> None:
        receipt_id = _clean(receipt_id, name="submission receipt", maximum=1_000)
        self._fenced_transition(
            assessment_id,
            fence,
            "submit_started",
            "submitted",
            receipt_id=receipt_id,
        )

    def mark_submit_unknown(
        self,
        assessment_id: str,
        fence: str,
        note: str,
    ) -> None:
        note = _clean(note, name="submission outcome note", maximum=1_000)
        self._fenced_transition(
            assessment_id,
            fence,
            "submit_started",
            "submit_unknown",
            outcome_note=note,
        )


def prepare_workspace(root: Path, manifest: dict[str, Any]) -> Path:
    if manifest.get("route") != "autonomous_allowed":
        raise AssessmentError("assessment requires the manual integrity gate")
    assessment_id = _identifier(
        manifest.get("assessment_id"),
        name="assessment ID",
    )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    workspace = root / assessment_id
    workspace.mkdir(exist_ok=True, mode=0o700)
    os.chmod(workspace, 0o700)
    manifest_path = workspace / "manifest.json"
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if manifest_path.exists() and manifest_path.read_text(encoding="utf-8") != serialized:
        raise AssessmentError("workspace manifest changed")
    manifest_path.write_text(serialized, encoding="utf-8")
    os.chmod(manifest_path, 0o600)
    return workspace


def _sandbox_string(path: Path) -> str:
    value = str(path)
    if "\n" in value or "\r" in value:
        raise AssessmentError("sandbox path is invalid")
    return value.replace("\\", "\\\\").replace('"', '\\"')


def run_isolated(
    *,
    store: AssessmentStore,
    assessment_id: str,
    workspace: Path,
    argv: list[str],
    evidence_dir: Path,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    assessment_id = _identifier(assessment_id, name="assessment ID")
    if store.state(assessment_id) not in {"prepared", "execution_failed"}:
        raise AssessmentError("assessment is not ready for isolated execution")
    if not argv or len(argv) > 100 or not all(isinstance(item, str) for item in argv):
        raise AssessmentError("execution argv is invalid")
    executable = Path(argv[0])
    if not executable.is_absolute() or not executable.is_file():
        raise AssessmentError("execution requires an absolute executable path")
    if not 1 <= timeout_seconds <= 1_800:
        raise AssessmentError("execution timeout must be between 1 and 1800 seconds")

    workspace = workspace.resolve(strict=True)
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(evidence_dir, 0o700)
    run_id = uuid.uuid4().hex
    profile_path = evidence_dir / f"sandbox-{run_id}.sb"
    home = workspace / ".home"
    temporary = workspace / ".tmp"
    home.mkdir(exist_ok=True, mode=0o700)
    temporary.mkdir(exist_ok=True, mode=0o700)
    real_home = Path.home().resolve()
    profile = (
        "(version 1)\n"
        "(allow default)\n"
        "(deny network*)\n"
        f'(deny file-read* (subpath "{_sandbox_string(real_home)}"))\n'
        f'(allow file-read* (subpath "{_sandbox_string(workspace)}"))\n'
        "(deny file-write*)\n"
        f'(allow file-write* (subpath "{_sandbox_string(workspace)}"))\n'
    )
    profile_path.write_text(profile, encoding="utf-8")
    os.chmod(profile_path, 0o600)
    stdout_path = evidence_dir / f"stdout-{run_id}.log"
    stderr_path = evidence_dir / f"stderr-{run_id}.log"
    store.transition(assessment_id, "executing")
    environment = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin",
        "HOME": str(home),
        "TMPDIR": str(temporary),
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    try:
        completed = subprocess.run(
            ["/usr/bin/sandbox-exec", "-f", str(profile_path), *argv],
            cwd=workspace,
            env=environment,
            check=False,
            capture_output=True,
            timeout=timeout_seconds,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        returncode = completed.returncode
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or b""
        stderr = (error.stderr or b"") + b"\nexecution timed out\n"
        returncode = 124
    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(stderr)
    os.chmod(stdout_path, 0o600)
    os.chmod(stderr_path, 0o600)
    target = "verified" if returncode == 0 else "execution_failed"
    store.transition(assessment_id, target)
    return {
        "status": target,
        "returncode": returncode,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "sandbox_profile_path": str(profile_path),
    }
