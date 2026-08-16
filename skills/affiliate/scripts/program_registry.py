#!/usr/bin/env python3
"""Validate and query the versioned Affiliate program research registry."""

import argparse
import hashlib
import hmac
import json
import os
import pwd
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from job_journal import JobStateError, start_effect, unresolved_effect, verify_effect


REQUIRED = {
    "id", "priority", "network", "decision", "program_url", "terms_url",
    "commission", "next_action", "evidence",
    "credential_ref",
}

GETRESPONSE_URL = "https://dash.partnerstack.com/application?company=getresponse&group=default"
ELEVENLABS_HOME = "https://elevenlabs.io/app/affiliates"
GETRESPONSE_PROMOTION = (
    "We publish evidence-led English software buying guides on aniccaai.com and disclose "
    "affiliate relationships before calls to action. We distribute each guide through "
    "@selawmqt on X, measure provider-side clicks and approved commissions, and update "
    "articles from official product documentation. For GetResponse, we will create "
    "email-marketing and automation comparison and how-to content for creators and small "
    "businesses, then link readers directly to GetResponse from the relevant article."
)


def load_registry(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("market") != "en":
        raise ValueError("unsupported program registry")
    programs = data.get("programs")
    if not isinstance(programs, list) or not programs:
        raise ValueError("empty program registry")
    ids = set()
    for program in programs:
        if set(program) != REQUIRED or program["id"] in ids:
            raise ValueError("invalid or duplicate program record")
        if not program["program_url"].startswith("https://"):
            raise ValueError("program URL must use HTTPS")
        ids.add(program["id"])
    return sorted(programs, key=lambda item: item["priority"])


def credential_state(program):
    secret_ref = program["credential_ref"]
    if secret_ref is None:
        return {"id": program["id"], "credential_state": "NOT_CONFIGURED"}
    parsed = urlparse(secret_ref)
    if parsed.scheme != "keychain" or not parsed.netloc or not parsed.path[1:]:
        raise ValueError("invalid credential reference")
    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "HOME": pwd.getpwuid(os.getuid()).pw_dir,
    }
    result = subprocess.run(
        [
            "/usr/bin/security", "find-generic-password", "-s", parsed.netloc,
            "-a", parsed.path[1:], "-w",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=False,
        env=environment,
    )
    state = "VERIFIED_NONEMPTY" if result.returncode == 0 and result.stdout.strip() else "MISSING_OR_EMPTY"
    return {"id": program["id"], "credential_ref": secret_ref, "credential_state": state}


def ensure_credential_section(text, label, source_label, credential_ref):
    section = re.search(rf"(?ms)^## {re.escape(label)}\n.*?(?=^## |\Z)", text)
    if section is not None:
        return text
    if not source_label:
        raise ValueError("private credential section is missing")
    source = re.search(rf"(?ms)^## {re.escape(source_label)}\n.*?(?=^## |\Z)", text)
    login = re.search(r"(?m)^- Login:\s*(.+)$", source.group() if source else "")
    if login is None:
        raise ValueError("source credential login is missing")
    return text.rstrip() + (
        f"\n\n## {label}\n"
        f"- Login: {login.group(1).strip()}\n"
        "- Password: \n"
        f"- Keychain: `{credential_ref}`\n"
        "- Verification: `UNVERIFIED`\n"
    )


def store_credential(program, label, markdown_path, verification, source_label=None):
    secret_ref = program["credential_ref"]
    if secret_ref is None:
        raise ValueError("credential reference is not configured")
    parsed = urlparse(secret_ref)
    if parsed.scheme != "keychain" or not parsed.netloc or not parsed.path[1:]:
        raise ValueError("invalid credential reference")
    secret = sys.stdin.buffer.readline().rstrip(b"\r\n")
    if len(secret) < 12 or b"\x00" in secret:
        raise ValueError("credential must contain at least 12 non-NUL bytes")
    markdown_path = markdown_path.expanduser()
    text = markdown_path.read_text(encoding="utf-8")
    text = ensure_credential_section(text, label, source_label, secret_ref)
    section = re.search(
        rf"(?ms)^## {re.escape(label)}\n.*?(?=^## |\Z)", text,
    )
    if section is None or not re.search(r"(?m)^- Password: .*$", section.group()):
        raise ValueError("private credential section is missing")
    updated_section = re.sub(
        r"(?m)^- Password: .*$",
        "- Password: " + secret.decode("utf-8"),
        section.group(),
        count=1,
    )
    updated_section = re.sub(
        r"(?m)^- Verification: .*$",
        f"- Verification: `{verification}`",
        updated_section,
        count=1,
    )
    updated = text[:section.start()] + updated_section + text[section.end():]
    markdown_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{markdown_path.name}.", dir=markdown_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(updated)
        os.chmod(temporary, 0o600)
        os.replace(temporary, markdown_path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    if secret.decode("utf-8") not in markdown_path.read_text(encoding="utf-8"):
        raise ValueError("private Markdown readback mismatch")

    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "HOME": pwd.getpwuid(os.getuid()).pw_dir,
    }
    subprocess.run(
        [
            "/usr/bin/security", "add-generic-password", "-U", "-s", parsed.netloc,
            "-a", parsed.path[1:], "-w", secret.decode("utf-8"),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=True,
        env=environment,
    )
    readback = subprocess.run(
        [
            "/usr/bin/security", "find-generic-password", "-s", parsed.netloc,
            "-a", parsed.path[1:], "-w",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=True,
        env=environment,
    ).stdout.rstrip(b"\r\n")
    if not hmac.compare_digest(secret, readback):
        raise ValueError("Keychain readback mismatch")
    return {
        "id": program["id"],
        "credential_ref": secret_ref,
        "keychain_state": "VERIFIED_NONEMPTY",
        "private_markdown_state": "VERIFIED_NONEMPTY",
    }


def store_login(label, markdown_path, login):
    if not login or len(login) > 320 or any(character.isspace() for character in login):
        raise ValueError("login must be one non-empty token")
    markdown_path = markdown_path.expanduser()
    text = markdown_path.read_text(encoding="utf-8")
    section = re.search(rf"(?ms)^## {re.escape(label)}\n.*?(?=^## |\Z)", text)
    if section is None or not re.search(r"(?m)^- Login: .*$", section.group()):
        raise ValueError("private credential section is missing")
    updated_section = re.sub(
        r"(?m)^- Login: .*$", "- Login: " + login, section.group(), count=1,
    )
    updated = text[:section.start()] + updated_section + text[section.end():]
    fd, temporary = tempfile.mkstemp(prefix=".affiliate-credentials.", dir=markdown_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(updated)
        os.chmod(temporary, 0o600)
        os.replace(temporary, markdown_path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    if login not in markdown_path.read_text(encoding="utf-8"):
        raise ValueError("private Markdown login readback mismatch")
    return {"label": label, "private_markdown_login_state": "VERIFIED_NONEMPTY"}


def store_link(label, field, markdown_path, link):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 -]{1,63} affiliate link", field):
        raise ValueError("invalid affiliate-link field")
    parsed = urlparse(link)
    if parsed.scheme != "https" or not parsed.netloc or any(character.isspace() for character in link):
        raise ValueError("affiliate link must be one HTTPS URL")
    markdown_path = markdown_path.expanduser()
    text = markdown_path.read_text(encoding="utf-8")
    section = re.search(rf"(?ms)^## {re.escape(label)}\n.*?(?=^## |\Z)", text)
    if section is None:
        raise ValueError("private credential section is missing")
    field_pattern = rf"(?m)^- {re.escape(field)}: .*$"
    if re.search(field_pattern, section.group()):
        updated_section = re.sub(field_pattern, f"- {field}: {link}", section.group(), count=1)
    else:
        updated_section = section.group().rstrip() + f"\n- {field}: {link}\n"
    updated = text[:section.start()] + updated_section + text[section.end():]
    fd, temporary = tempfile.mkstemp(prefix=".affiliate-links.", dir=markdown_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(updated)
        os.chmod(temporary, 0o600)
        os.replace(temporary, markdown_path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    if link not in markdown_path.read_text(encoding="utf-8"):
        raise ValueError("private Markdown link readback mismatch")
    return {"label": label, "field": field, "private_markdown_link_state": "VERIFIED_NONEMPTY"}


def atomic_receipt(path, payload):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def apply_getresponse(state, cdp_port, profile_path):
    """Submit the one admitted GetResponse application under a durable effect fence."""
    receipt_path = state / "program-applications" / "getresponse.json"
    if receipt_path.is_file():
        prior = json.loads(receipt_path.read_text(encoding="utf-8"))
        if prior.get("state") in {"APPLICATION_PENDING", "APPROVED", "REJECTED"}:
            return {**prior, "deduplicated": True}
    if unresolved_effect(state, "PROVIDER_APPLICATION", "getresponse"):
        return {
            "schema_version": 1, "receipt_type": "PROGRAM_APPLICATION",
            "program": "getresponse", "state": "RECONCILE_REQUIRED",
            "deduplicated": True,
        }
    profile = json.loads(profile_path.expanduser().read_text(encoding="utf-8"))
    linkedin = str(profile.get("candidate", {}).get("linkedin_url", ""))
    if not linkedin.startswith(("https://linkedin.com/", "https://www.linkedin.com/")):
        raise ValueError("verified LinkedIn profile is unavailable")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError("Playwright is unavailable") from error
    job = None
    result = None
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
        pages = [page for context in browser.contexts for page in context.pages]
        if len(pages) != 1:
            raise ValueError("expected one PartnerStack browser page")
        page = pages[0]
        try:
            page.goto(GETRESPONSE_URL, wait_until="domcontentloaded", timeout=20_000)
            page.get_by_text("GetResponse Affiliate Application", exact=True).wait_for(timeout=15_000)
            required_locked = page.locator("input[required][disabled]")
            if required_locked.count() != 3 or not all(
                required_locked.nth(index).input_value().strip() for index in range(3)
            ):
                raise ValueError("PartnerStack identity prefill is incomplete")
            turnstile = page.locator("input[name='cf-turnstile-response']")
            if turnstile.count() != 1 or not turnstile.input_value().strip():
                raise ValueError("PartnerStack Turnstile token is unavailable")
            page.locator("input[name='field_qlNDAL0eQOe6Pk']").fill("Anicca")
            page.locator("input[name='field_PeKF0gSPmi9TIk']").fill("https://aniccaai.com")
            page.locator("input[name='field_7xRPJ4InAwZY8I']").fill("ElevenLabs")
            page.locator("textarea[required]").fill(GETRESPONSE_PROMOTION)
            page.locator("input[name='field_sETYP00rsB0hyP']").fill(
                f"https://x.com/selawmqt {linkedin}"
            )
            country = page.get_by_role("button", name=re.compile(r"^(国を選択|Select country)$", re.I))
            country.click()
            page.get_by_role("option", name="Japan", exact=True).click()
            agency_no = page.get_by_text("No", exact=True)
            agency_no.click()
            if not page.locator("input[type='checkbox']").nth(1).is_checked():
                raise ValueError("agency answer was not selected")
            submit = page.get_by_role(
                "button", name=re.compile(r"^(申し込みを提出|Submit application)$", re.I),
            )
            if not submit.is_enabled():
                raise ValueError("GetResponse application is not submittable")
            job = start_effect(
                state, "PROVIDER_APPLICATION", "getresponse",
                {
                    "operation": "submit_application", "program": "getresponse",
                    "application_url": GETRESPONSE_URL,
                    "website": "https://aniccaai.com",
                    "promotion_sha256": hashlib.sha256(GETRESPONSE_PROMOTION.encode()).hexdigest(),
                },
                {"state": "FORM_READY", "url": page.url}, 86400,
            )
            before = page.locator("body").inner_text()
            submit.click(timeout=5_000)
            page.wait_for_function(
                "before => document.body.innerText !== before", arg=before, timeout=20_000,
            )
            rendered = page.locator("body").inner_text()
            lowered = rendered.casefold()
            accepted = (
                "application" in lowered
                and any(marker in lowered for marker in (
                    "submitted", "under review", "in review", "thank you for applying",
                ))
                and not page.get_by_role(
                    "button", name=re.compile(r"^(申し込みを提出|Submit application)$", re.I),
                ).count()
            )
            state_name = "APPLICATION_PENDING" if accepted else "SUBMISSION_AMBIGUOUS"
            result = {
                "schema_version": 1, "receipt_type": "PROGRAM_APPLICATION",
                "program": "getresponse", "state": state_name,
                "application_url": GETRESPONSE_URL,
                "observed_url": page.url,
                "rendered_text_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
                "job_id": job["job_id"], "deduplicated": False,
            }
            if accepted:
                verify_effect(state, job["job_id"], {
                    "state": state_name, "url": page.url,
                    "rendered_text_sha256": result["rendered_text_sha256"],
                })
            atomic_receipt(receipt_path, result)
        finally:
            page.goto(ELEVENLABS_HOME, wait_until="domcontentloaded", timeout=20_000)
    return result


def main():
    parser = argparse.ArgumentParser(prog="affiliate programs")
    parser.add_argument("command", choices=("list", "next", "credential", "store-credential", "store-login", "store-link", "apply"))
    parser.add_argument("--decision", action="append", default=[])
    parser.add_argument("--id")
    parser.add_argument("--label")
    parser.add_argument("--source-label")
    parser.add_argument("--field")
    parser.add_argument("--credential-ref")
    parser.add_argument("--state", type=Path, default=Path("~/.local/state/life-manager/affiliate"))
    parser.add_argument("--cdp-port", type=int, default=9324)
    parser.add_argument("--profile", type=Path, default=Path("~/.config/anicca/job-search/profile.json"))
    parser.add_argument(
        "--verification",
        choices=("SAVED_BEFORE_SUBMIT", "VERIFIED_LOGIN"),
        default="SAVED_BEFORE_SUBMIT",
    )
    parser.add_argument(
        "--private-markdown",
        type=Path,
        default=Path("~/.config/anicca/affiliate-credentials.md"),
    )
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / "config" / "programs" / "en-candidates.json"
    programs = load_registry(path)
    if args.decision:
        programs = [item for item in programs if item["decision"] in args.decision]
    if args.id:
        programs = [item for item in programs if item["id"] == args.id]
    if args.command in ("credential", "store-credential", "store-login", "store-link", "apply"):
        if len(programs) != 1:
            return 3
        if args.credential_ref:
            programs[0] = {**programs[0], "credential_ref": args.credential_ref}
        if args.command == "apply":
            if programs[0]["id"] != "getresponse":
                raise ValueError("application adapter is unavailable")
            result = apply_getresponse(args.state.expanduser(), args.cdp_port, args.profile)
        elif args.command == "credential":
            result = credential_state(programs[0])
        elif args.command == "store-login":
            if not args.label:
                raise ValueError("--label is required")
            result = store_login(args.label, args.private_markdown, sys.stdin.readline().strip())
        elif args.command == "store-link":
            if not args.label or not args.field:
                raise ValueError("--label and --field are required")
            result = store_link(
                args.label, args.field, args.private_markdown, sys.stdin.readline().strip(),
            )
        else:
            if not args.label:
                raise ValueError("--label is required")
            result = store_credential(
                programs[0], args.label, args.private_markdown, args.verification,
                args.source_label,
            )
    else:
        result = programs[:1] if args.command == "next" else programs
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result else 3


if __name__ == "__main__":
    raise SystemExit(main())
