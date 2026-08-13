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

from .browser_pages import registered_created_target
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


def known_tenants(store_path: Path) -> list[str]:
    store_path = Path(store_path).expanduser().resolve()
    store = _read_store(store_path)
    tenants: list[str] = []
    for tenant, value in store["accounts"].items():
        if not isinstance(tenant, str):
            raise WorkdayCredentialError("Workday credential tenant is invalid")
        canonical = tenant_key(f"https://{tenant}/")
        _account(value, canonical)
        tenants.append(canonical)
    return sorted(tenants)


def _wait_visible(page: Any, selector: str, stage: str) -> None:
    waiter = getattr(page, "wait_for_selector", None)
    if not callable(waiter):
        page.wait_for_timeout(1_000)
        return
    try:
        waiter(selector, state="visible", timeout=20_000)
    except Exception as error:
        if error.__class__.__name__ == "TimeoutError":
            raise WorkdayCredentialError(
                f"Workday account surface did not load:{stage}"
            ) from error
        raise


def _single_visible(control: Any) -> Any | None:
    count = control.count()
    if count == 1:
        return control if control.is_visible() else None
    if not hasattr(control, "nth"):
        return None
    visible = [control.nth(index) for index in range(count) if control.nth(index).is_visible()]
    return visible[0] if len(visible) == 1 else None


def _advance_application_entry(page: Any) -> int:
    actions = 0
    for selector, next_selector in (
        (
            '[data-automation-id="jobPostingApplyButton"]',
            '[data-automation-id="applyManually"], [data-automation-id="adventureButton"]',
        ),
        (
            '[data-automation-id="applyManually"], [data-automation-id="adventureButton"]',
            '[data-automation-id="createAccountLink"], [data-automation-id="SignInWithEmailButton"], [data-automation-id="signInLink"], [data-automation-id="email"]',
        ),
    ):
        control = page.locator(selector)
        control = _single_visible(control)
        if control is None:
            continue
        try:
            control.click(timeout=5_000)
        except Exception as error:
            if error.__class__.__name__ != "TimeoutError":
                raise
            control.click(timeout=15_000, force=True)
        actions += 1
        _wait_visible(
            page,
            next_selector,
            "manual_choice" if actions == 1 else "native_chooser",
        )
    return actions


def _advance_native_auth(page: Any) -> int:
    for selector in (
        '[data-automation-id="createAccountLink"]',
        '[data-automation-id="SignInWithEmailButton"]',
        '[data-automation-id="signInLink"]',
    ):
        control = page.locator(selector)
        control = _single_visible(control)
        if control is None:
            continue
        control.click(timeout=5_000)
        _wait_visible(page, '[data-automation-id="email"]', "email_form")
        _wait_visible(page, '[data-automation-id="password"]', "password_form")
        return 1
    return 0


def fill_account_creation(
    *,
    job_url: str,
    profile_path: Path,
    store_path: Path,
    owner_receipt: dict[str, Any],
    ownership_receipt: dict[str, Any],
    owned_page: dict[str, Any],
    playwright: Any,
) -> dict[str, Any]:
    if owner_receipt.get("status") != "ready":
        raise WorkdayCredentialError("browser owner is not ready")
    receipt = ensure_credentials(
        job_url=job_url,
        profile_path=profile_path,
        store_path=store_path,
    )
    target = registered_created_target(
        owner_receipt, ownership_receipt, owned_page
    )
    endpoint = str(owner_receipt.get("endpoint") or "")
    if endpoint != "http://127.0.0.1:9222":
        raise WorkdayCredentialError("browser owner endpoint is invalid")
    browser = playwright.chromium.connect_over_cdp(endpoint)
    pages = []
    for context in browser.contexts:
        for page in context.pages:
            session = context.new_cdp_session(page)
            page_target = session.send("Target.getTargetInfo")["targetInfo"][
                "targetId"
            ]
            if page_target == target:
                pages.append(page)
    if len(pages) != 1:
        raise WorkdayCredentialError("owned Workday page is unavailable")
    page = pages[0]
    if tenant_key(page.url) != receipt["tenant"]:
        raise WorkdayCredentialError("owned page does not match the Workday tenant")
    account = load_credentials(store_path, job_url)

    def locator(automation_id: str) -> Any:
        value = page.locator(f'[data-automation-id="{automation_id}"]')
        if value.count() != 1:
            raise WorkdayCredentialError(
                f"Workday account control is unavailable: {automation_id}"
            )
        return value

    verify_password = page.locator('[data-automation-id="verifyPassword"]')
    if verify_password.count() == 0 and "/login" not in urlsplit(page.url).path:
        _wait_visible(
            page,
            '[data-automation-id="jobPostingApplyButton"], [data-automation-id="applyManually"], [data-automation-id="adventureButton"], [data-automation-id="createAccountLink"], [data-automation-id="SignInWithEmailButton"], [data-automation-id="signInLink"], [data-automation-id="email"]',
            "job_surface",
        )
        entry_actions = _advance_application_entry(page)
        entry_actions += _advance_native_auth(page)
        verify_password = page.locator('[data-automation-id="verifyPassword"]')
    else:
        entry_actions = 0
    if verify_password.count() == 1:
        mode = "create"
    elif (
        verify_password.count() == 0
        and page.locator('[data-automation-id="email"]').count() == 1
        and page.locator('[data-automation-id="password"]').count() == 1
    ):
        mode = "sign_in"
    else:
        raise WorkdayCredentialError("Workday account form is unavailable")

    email = locator("email")
    password = locator("password")
    email.fill(account["application_email"])
    password.fill(account["password"])
    if (
        email.input_value() != account["application_email"]
        or password.input_value() != account["password"]
    ):
        raise WorkdayCredentialError("Workday credential fill verification failed")

    if mode == "create":
        verify_password.fill(account["password"])
        if verify_password.input_value() != account["password"]:
            raise WorkdayCredentialError("Workday credential fill verification failed")
        checkbox = page.locator('[data-automation-id="createAccountCheckbox"]')
        if checkbox.count() == 1 and not checkbox.is_checked():
            checkbox.check(force=True)
        submit = locator("createAccountSubmitButton")
        status = "account_creation_clicked"
        action_count = entry_actions + (5 if checkbox.count() == 1 else 4)
    else:
        submit = page.locator(
            '[data-automation-id="signInSubmitButton"], button[type="submit"]'
        )
        if submit.count() != 1:
            raise WorkdayCredentialError("Workday sign-in control is unavailable")
        status = "sign_in_clicked"
        action_count = entry_actions + 3
    try:
        submit.click(timeout=5_000)
    except Exception as error:
        if error.__class__.__name__ != "TimeoutError":
            raise
        submit.click(timeout=15_000, force=True)
    page.wait_for_timeout(2_000)
    return {
        **receipt,
        "status": status,
        "browser_action_count": action_count,
        "owned_target_sha256": hashlib.sha256(target.encode()).hexdigest(),
        "secret_values_returned": False,
    }


def _write_receipt(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-url", required=True)
    parser.add_argument("--profile-path", required=True, type=Path)
    parser.add_argument("--store-path", required=True, type=Path)
    parser.add_argument("--fill-account", action="store_true")
    parser.add_argument("--owner-receipt", type=Path)
    parser.add_argument("--ownership-receipt", type=Path)
    parser.add_argument("--owned-page", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.fill_account:
            if not all(
                (args.owner_receipt, args.ownership_receipt, args.owned_page, args.output)
            ):
                parser.error(
                    "--fill-account requires owner, ownership, owned-page, and output"
                )
            owner = json.loads(args.owner_receipt.read_text(encoding="utf-8"))
            ownership = json.loads(
                args.ownership_receipt.read_text(encoding="utf-8")
            )
            owned_page = json.loads(args.owned_page.read_text(encoding="utf-8"))
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                receipt = fill_account_creation(
                    job_url=args.job_url,
                    profile_path=args.profile_path,
                    store_path=args.store_path,
                    owner_receipt=owner,
                    ownership_receipt=ownership,
                    owned_page=owned_page,
                    playwright=playwright,
                )
            _write_receipt(args.output, receipt)
        else:
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
