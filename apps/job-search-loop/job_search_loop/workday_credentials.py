from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import string
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from .config import ConfigError, validate_profile


class WorkdayCredentialError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def tenant_key(job_url: str) -> str:
    try:
        parsed = urlsplit(job_url.strip())
    except (AttributeError, ValueError) as error:
        raise WorkdayCredentialError("Workday job URL is invalid") from error
    host = (parsed.hostname or "").casefold().rstrip(".")
    if (
        parsed.scheme.casefold() != "https"
        or not host.endswith(".myworkdayjobs.com")
        or host == "myworkdayjobs.com"
    ):
        raise WorkdayCredentialError(
            "Workday job URL must use an official tenant host"
        )
    return host


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(28))
        if (
            any(character.islower() for character in password)
            and any(character.isupper() for character in password)
            and any(character.isdigit() for character in password)
            and any(not character.isalnum() for character in password)
        ):
            return password


def _validate_password(password: Any) -> str:
    if (
        not isinstance(password, str)
        or len(password) < 20
        or any(character.isspace() for character in password)
        or not any(character.islower() for character in password)
        or not any(character.isupper() for character in password)
        or not any(character.isdigit() for character in password)
        or not any(not character.isalnum() for character in password)
    ):
        raise WorkdayCredentialError(
            "generated Workday password does not meet the strong local policy"
        )
    return password


def _application_email(profile_path: Path) -> str:
    try:
        profile: Any = json.loads(profile_path.read_text(encoding="utf-8"))
        validate_profile(profile)
    except (OSError, json.JSONDecodeError, ConfigError) as error:
        raise WorkdayCredentialError(f"private profile is invalid: {error}") from error
    candidate = profile["candidate"]
    email = candidate.get("application_email")
    if (
        not isinstance(email, str)
        or "@" not in email
        or any(character.isspace() for character in email)
    ):
        raise WorkdayCredentialError(
            "private profile has no valid candidate.application_email"
        )
    return email.strip()


def _empty_store() -> dict[str, Any]:
    return {"version": 1, "accounts": {}}


def _read_store(store_path: Path) -> dict[str, Any]:
    if not store_path.exists():
        return _empty_store()
    if not store_path.is_file():
        raise WorkdayCredentialError("Workday credential store is not a file")
    os.chmod(store_path, 0o600)
    try:
        value: Any = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise WorkdayCredentialError(
            f"Workday credential store is invalid: {error}"
        ) from error
    if (
        not isinstance(value, dict)
        or value.get("version") != 1
        or not isinstance(value.get("accounts"), dict)
    ):
        raise WorkdayCredentialError("Workday credential store schema is invalid")
    return value


def _account(value: Any, tenant: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise WorkdayCredentialError(f"Workday credential for {tenant} is invalid")
    required = ("application_email", "password", "created_at")
    if any(not isinstance(value.get(key), str) or not value[key] for key in required):
        raise WorkdayCredentialError(f"Workday credential for {tenant} is invalid")
    _validate_password(value["password"])
    return {
        "application_email": value["application_email"],
        "password": value["password"],
        "created_at": value["created_at"],
    }


def _write_store(store_path: Path, value: dict[str, Any]) -> None:
    store_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(store_path.parent, 0o700)
    temporary = store_path.with_name(f".{store_path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        temporary.replace(store_path)
        os.chmod(store_path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _receipt(
    *, tenant: str, store_path: Path, created: bool, email: str
) -> dict[str, Any]:
    return {
        "version": 1,
        "tenant": tenant,
        "credential_path": str(store_path.expanduser().resolve()),
        "created": created,
        "email_sha256": hashlib.sha256(email.encode("utf-8")).hexdigest(),
    }


def ensure_credentials(
    *,
    job_url: str,
    profile_path: Path,
    store_path: Path,
    password_factory: Callable[[], str] = _generate_password,
) -> dict[str, Any]:
    tenant = tenant_key(job_url)
    profile_path = Path(profile_path).expanduser().resolve()
    store_path = Path(store_path).expanduser().resolve()
    email = _application_email(profile_path)
    store = _read_store(store_path)
    existing = store["accounts"].get(tenant)
    if existing is not None:
        account = _account(existing, tenant)
        if account["application_email"].casefold() != email.casefold():
            raise WorkdayCredentialError(
                "existing Workday application email does not match the profile"
            )
        return _receipt(
            tenant=tenant, store_path=store_path, created=False, email=email
        )

    password = _validate_password(password_factory())
    store["accounts"][tenant] = {
        "application_email": email,
        "password": password,
        "created_at": _now(),
    }
    _write_store(store_path, store)
    return _receipt(tenant=tenant, store_path=store_path, created=True, email=email)


def load_credentials(store_path: Path, job_url: str) -> dict[str, str]:
    tenant = tenant_key(job_url)
    store_path = Path(store_path).expanduser().resolve()
    store = _read_store(store_path)
    value = store["accounts"].get(tenant)
    if value is None:
        raise WorkdayCredentialError(
            f"no private Workday credential exists for {tenant}"
        )
    return _account(value, tenant)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-url", required=True)
    parser.add_argument("--profile-path", required=True, type=Path)
    parser.add_argument("--store-path", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = ensure_credentials(
            job_url=args.job_url,
            profile_path=args.profile_path,
            store_path=args.store_path,
        )
    except WorkdayCredentialError as error:
        print(f"job-search Workday credentials: {error}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
