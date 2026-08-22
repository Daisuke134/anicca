from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..workday_credentials import (
    WorkdayCredentialError,
    _application_email,
    _generate_password,
    _validate_password,
    tenant_key,
)


def _service(tenant: str) -> str:
    return f"workday:{tenant}"


class MachineWorkdayCredentialStore:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "credentials": []}
        os.chmod(self.path, 0o600)
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if value.get("version") != 1 or not isinstance(value.get("credentials"), list):
            raise WorkdayCredentialError("machine credential SSOT schema is invalid")
        return value

    def _write(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _find(self, value: dict[str, Any], tenant: str) -> dict[str, Any] | None:
        matches = [item for item in value["credentials"] if isinstance(item, dict) and item.get("service") == _service(tenant)]
        if len(matches) > 1:
            raise WorkdayCredentialError("duplicate Workday tenant in machine credential SSOT")
        return matches[0] if matches else None

    @staticmethod
    def _validate(entry: dict[str, Any], tenant: str) -> dict[str, str]:
        email = entry.get("email") or entry.get("username")
        password = entry.get("password")
        if not isinstance(email, str) or "@" not in email:
            raise WorkdayCredentialError(f"Workday email for {tenant} is invalid")
        return {"application_email": email, "password": _validate_password(password)}

    def ensure(self, *, job_url: str, profile_path: Path) -> dict[str, Any]:
        tenant = tenant_key(job_url)
        email = _application_email(profile_path)
        value = self._read()
        existing = self._find(value, tenant)
        created = existing is None
        if existing is None:
            existing = {
                "service": _service(tenant),
                "username": email,
                "email": email,
                "password": _generate_password(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "note": "Job Hunter Workday tenant credential",
            }
            value["credentials"].append(existing)
            self._write(value)
        account = self._validate(existing, tenant)
        if account["application_email"].casefold() != email.casefold():
            raise WorkdayCredentialError("Workday tenant email does not match private profile")
        return {
            "version": 1,
            "tenant": tenant,
            "credential_path": str(self.path),
            "created": created,
            "email_sha256": hashlib.sha256(email.encode()).hexdigest(),
        }

    def load(self, job_url: str) -> dict[str, str]:
        tenant = tenant_key(job_url)
        entry = self._find(self._read(), tenant)
        if entry is None:
            raise WorkdayCredentialError(f"no machine credential exists for {tenant}")
        return self._validate(entry, tenant)

    def account_status(self, job_url: str) -> str:
        tenant = tenant_key(job_url)
        entry = self._find(self._read(), tenant)
        if entry is None:
            return "missing"
        status = str(entry.get("account_status") or "credential_only")
        if status not in {"credential_only", "create_submitted", "signed_in"}:
            raise WorkdayCredentialError("Workday tenant account status is invalid")
        return status

    def mark_account_status(self, job_url: str, status: str) -> None:
        if status not in {"create_submitted", "signed_in"}:
            raise WorkdayCredentialError("Workday tenant account status is invalid")
        tenant = tenant_key(job_url)
        value = self._read()
        entry = self._find(value, tenant)
        if entry is None:
            raise WorkdayCredentialError(f"no machine credential exists for {tenant}")
        entry["account_status"] = status
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write(value)

    def known_tenants(self) -> list[str]:
        tenants = []
        for entry in self._read()["credentials"]:
            service = entry.get("service") if isinstance(entry, dict) else None
            if isinstance(service, str) and service.startswith("workday:"):
                tenant = tenant_key(f"https://{service.removeprefix('workday:')}/")
                self._validate(entry, tenant)
                tenants.append(tenant)
        return sorted(tenants)

    def import_legacy(self, legacy_path: Path) -> dict[str, int]:
        legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
        accounts = legacy.get("accounts") if isinstance(legacy, dict) else None
        if legacy.get("version") != 1 or not isinstance(accounts, dict):
            raise WorkdayCredentialError("legacy Workday credential store is invalid")
        value = self._read()
        imported = 0
        for tenant, account in accounts.items():
            canonical = tenant_key(f"https://{tenant}/")
            legacy_email = account.get("application_email")
            if not isinstance(legacy_email, str) or "@" not in legacy_email:
                raise WorkdayCredentialError("legacy Workday email is invalid")
            validated = {
                "application_email": legacy_email,
                "password": _validate_password(account.get("password")),
            }
            existing = self._find(value, canonical)
            if existing is not None:
                if self._validate(existing, canonical) != validated:
                    raise WorkdayCredentialError("machine and legacy Workday credentials differ")
                continue
            value["credentials"].append(
                {
                    "service": _service(canonical),
                    "username": validated["application_email"],
                    "email": validated["application_email"],
                    "password": validated["password"],
                    "updated_at": account.get("created_at") or datetime.now(timezone.utc).isoformat(),
                    "note": "Job Hunter Workday tenant credential (migrated)",
                }
            )
            imported += 1
        self._write(value)
        for tenant in accounts:
            self.load(f"https://{tenant}/")
        return {"legacy_count": len(accounts), "imported_count": imported}
