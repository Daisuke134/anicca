from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit

from .browser_agent.workday_account import MachineWorkdayCredentialStore
from .browser_agent.session import BrowserSession
from .workday_verification import (
    VerificationError,
    VerificationStore,
    extract_verification_target_from_gmail,
)


async def complete_account_mail(
    *,
    account: str,
    message_id: str,
    credential_store: Path,
    database: Path,
    endpoint: str,
    gog: str,
) -> dict[str, str]:
    target = extract_verification_target_from_gmail(
        account=account,
        message_id=message_id,
        credential_store=credential_store,
        gog=gog,
    )
    store = VerificationStore(database)
    fence = store.claim(target)
    if fence is None:
        store.close()
        return target.receipt("duplicate")
    session = BrowserSession()
    handle = None
    navigation_started = False
    try:
        handle = await session.attach(endpoint, f"account-mail-{target.message_id}")
        page = session.page(handle)
        store.mark_navigation_started(target.event_key, fence)
        navigation_started = True
        await page.goto(target.verification_url)
        await page.wait_for_timeout(3_000)
        host = (urlsplit(page.url).hostname or "").casefold().rstrip(".")
        if host != target.tenant:
            raise VerificationError("Workday account mail escaped the known tenant")
        if target.kind == "password_reset":
            password = MachineWorkdayCredentialStore(credential_store).load(
                target.verification_url
            )["password"]
            await page.type_target(
                {"label": "", "role": "textbox", "stable_id": "automation:password"},
                password,
            )
            await page.type_target(
                {"label": "", "role": "textbox", "stable_id": "automation:verifyPassword"},
                password,
            )
            await page.click_target(
                {"label": "", "role": "button", "stable_id": "automation:resetPasswordButton"}
            )
            await page.wait_for_timeout(5_000)
            current = page.url.casefold()
            visible = str(await page.evaluate("() => document.body.innerText")).casefold()
            if "passwordreset" in current or not (
                "sign in" in visible
                or "password has been reset" in visible
                or "password was reset" in visible
            ):
                raise VerificationError("Workday did not visibly confirm password reset")
        store.mark_opened(target.event_key, fence)
        return target.receipt("opened")
    except Exception:
        try:
            if navigation_started:
                store.mark_unknown(target.event_key, fence)
            else:
                store.release_claim(target.event_key, fence)
        except VerificationError:
            pass
        raise
    finally:
        if handle is not None:
            await session.close_owned(handle)
        store.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True)
    parser.add_argument("--message-id", required=True)
    parser.add_argument("--credential-store", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--endpoint", default="http://127.0.0.1:9222")
    parser.add_argument("--gog", default="/opt/homebrew/bin/gog")
    args = parser.parse_args(argv)
    receipt = asyncio.run(
        complete_account_mail(
            account=args.account,
            message_id=args.message_id,
            credential_store=args.credential_store,
            database=args.database,
            endpoint=args.endpoint,
            gog=args.gog,
        )
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
