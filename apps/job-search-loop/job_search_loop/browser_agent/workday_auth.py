from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .actions import ActionExecutor
from .contracts import ActionTargetV1, SessionHandleV1, VisibleActionV1
from .workday_account import MachineWorkdayCredentialStore


@dataclass(frozen=True, slots=True)
class WorkdayAuthReceiptV1:
    mode: str
    tenant: str
    email_sha256: str
    action_receipt_hashes: tuple[str, ...]
    readiness_wait_ms: int


class WorkdayAuthTool:
    """Fill Workday auth secrets without returning them to the model caller."""

    def __init__(
        self,
        *,
        store: MachineWorkdayCredentialStore,
        executor: ActionExecutor,
        profile_path: Path,
    ) -> None:
        self._store = store
        self._executor = executor
        self._profile_path = profile_path

    async def prepare(
        self,
        *,
        handle: SessionHandleV1,
        job_url: str,
        mode: str,
        email_target: ActionTargetV1,
        password_target: ActionTargetV1,
        verify_password_target: ActionTargetV1 | None = None,
    ) -> WorkdayAuthReceiptV1:
        if mode not in {"sign_in", "create_account"}:
            raise ValueError("Workday auth mode must be sign_in or create_account")
        if mode == "create_account" and verify_password_target is None:
            raise ValueError("create_account requires visible verify-password target")
        if mode == "sign_in" and verify_password_target is not None:
            raise ValueError("sign_in must not receive verify-password target")
        safe = self._store.ensure(job_url=job_url, profile_path=self._profile_path)
        secrets = self._store.load(job_url)
        receipts = []
        for target, value in (
            (email_target, secrets["application_email"]),
            (password_target, secrets["password"]),
            (verify_password_target, secrets["password"] if verify_password_target else None),
        ):
            if target is not None and value is not None:
                receipt = await self._executor.execute(
                    handle, VisibleActionV1("type", target=target, text=value)
                )
                receipts.append(receipt.receipt_sha256)
        wait_receipt = await self._executor.execute(
            handle, VisibleActionV1("wait", wait_ms=6_000)
        )
        receipts.append(wait_receipt.receipt_sha256)
        return WorkdayAuthReceiptV1(
            mode,
            safe["tenant"],
            safe["email_sha256"],
            tuple(receipts),
            6_000,
        )
