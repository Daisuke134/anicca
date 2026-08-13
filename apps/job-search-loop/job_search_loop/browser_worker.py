from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from .candidate_queue import CandidateQueue
from .telemetry import Telemetry


class BrowserWorkerBusy(RuntimeError):
    pass


def _write_private_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def exclusive_worker(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise BrowserWorkerBusy("browser worker is already running") from error
        yield
    finally:
        os.close(descriptor)


def run_worker(
    *,
    database: Path,
    owner_receipt: Path,
    holder_pid: int,
    run_id: str,
    lock_path: Path,
    worker_receipt: Path,
    output: Path,
    prefilter_result: Path | None = None,
    profile_path: Path | None = None,
    materials_root: Path | None = None,
    evidence_dir: Path | None = None,
    pre_submit_runner: Callable[..., dict[str, Any]] | None = None,
    route_fixture: Path | None = None,
    application_ledger: Path | None = None,
    telemetry: Any = None,
) -> dict[str, Any]:
    telemetry = telemetry or Telemetry()
    with exclusive_worker(lock_path), telemetry.span("hourly_pass") as pass_span:
        correlation = {
            "trace_id": pass_span.trace_id if re.fullmatch(r"[a-f0-9]{32}", str(pass_span.trace_id or "")) else None,
            "span_id": pass_span.span_id if re.fullmatch(r"[a-f0-9]{16}", str(pass_span.span_id or "")) else None,
        }
        owner = json.loads(owner_receipt.read_text(encoding="utf-8"))
        if owner.get("status") != "ready" or owner.get("holder_pid") != holder_pid:
            raise RuntimeError("browser owner receipt does not match daily owner")
        started_at = datetime.now(timezone.utc).isoformat()
        _write_private_json(
            worker_receipt,
            {
                "version": 1,
                "status": "running",
                "run_id": run_id,
                "worker_pid": os.getpid(),
                "holder_pid": holder_pid,
                "lease_id": owner.get("lease_id"),
                "fence": owner.get("fence"),
                "actor": "resident_worker",
                "started_at": started_at,
                **correlation,
            },
        )
        if route_fixture is not None:
            if evidence_dir is None:
                raise ValueError("route fixture evidence directory is missing")
            from .route_fixture import run_no_send_fixture

            result = run_no_send_fixture(
                request_path=route_fixture,
                evidence_dir=evidence_dir / "route-fixture",
                authority={
                    "actor": "resident_worker",
                    "worker_pid": os.getpid(),
                    "run_id": run_id,
                    "lease_id": owner.get("lease_id"),
                    "fence": owner.get("fence"),
                },
            )
            result = {**result, **correlation}
            _write_private_json(output, result)
            _write_private_json(
                worker_receipt,
                {
                    "version": 1,
                    "status": "completed",
                    "actor": "resident_worker",
                    "run_id": run_id,
                    "worker_pid": os.getpid(),
                    "holder_pid": holder_pid,
                    "lease_id": owner.get("lease_id"),
                    "fence": owner.get("fence"),
                    "started_at": started_at,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "route_fixture_status": result["status"],
                    "send_count": result["send_count"],
                    **correlation,
                },
            )
            return result
        queue = CandidateQueue(database)
        try:
            summary = queue.summary()
        finally:
            queue.close()
        remaining = summary["remaining_unverified_count"]
        pre_submit = {
            "status": "pending_verification",
            "blocked": [f"{remaining}_candidate_links_await_fill_adapter"],
        }
        if prefilter_result is not None:
            if profile_path is None or materials_root is None or evidence_dir is None:
                raise ValueError("pre-submit runner inputs are incomplete")
            if pre_submit_runner is None:
                from .playwright_ats import run_pre_submit

                pre_submit_runner = run_pre_submit
            route_materialization: list[dict[str, Any]] = []
            effective_prefilter_result = prefilter_result
            if application_ledger is not None:
                from .candidate_routes import (
                    filter_terminal_candidates,
                    materialize_canonical_routes,
                )

                filtered_payload = filter_terminal_candidates(
                    application_ledger,
                    json.loads(prefilter_result.read_text(encoding="utf-8")),
                )
                effective_prefilter_result = evidence_dir / "terminal-filtered-candidates.json"
                _write_private_json(effective_prefilter_result, filtered_payload)

                route_materialization = materialize_canonical_routes(
                    application_ledger, effective_prefilter_result
                )
            pre_submit = pre_submit_runner(
                owner_receipt=owner,
                prefilter_result=effective_prefilter_result,
                profile_path=profile_path,
                materials_root=materials_root,
                evidence_dir=evidence_dir,
                telemetry=telemetry,
            )
            dossier = pre_submit.get("claim_ready_dossier")
            if isinstance(dossier, dict):
                route = next(
                    (
                        item
                        for item in route_materialization
                        if item.get("url_sha256") == dossier.get("url_sha256")
                    ),
                    None,
                )
                if route is not None and route.get("application_id"):
                    dossier = {**dossier, "application_id": route["application_id"]}
        result = {
            "status": str(pre_submit.get("status") or "pending_verification"),
            "executor": str(pre_submit.get("executor") or "none"),
            "submitted": [],
            "submit_unknown": [],
            "blocked": list(pre_submit.get("blocked") or []),
            "attempted_count": int(pre_submit.get("attempted_count") or 0),
            "attempt_audit": list(pre_submit.get("attempt_audit") or []),
            "continued_after_failure": bool(
                pre_submit.get("continued_after_failure")
            ),
            "claim_ready_dossier": dossier if prefilter_result is not None else None,
            "route_materialization": route_materialization
            if prefilter_result is not None
            else [],
            "report_message_id": None,
            "discovered_link_count": summary["discovered_count"],
            "verified_link_count": summary["verified_count"],
            "remaining_unverified_count": remaining,
            **correlation,
        }
        _write_private_json(output, result)
        _write_private_json(
            worker_receipt,
            {
                "version": 1,
                "status": "completed",
                "actor": "resident_worker",
                "executor": result["executor"],
                "run_id": run_id,
                "worker_pid": os.getpid(),
                "holder_pid": holder_pid,
                "lease_id": owner.get("lease_id"),
                "fence": owner.get("fence"),
                "started_at": started_at,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "submitted_count": 0,
                "remaining_unverified_count": remaining,
                **correlation,
            },
        )
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run", "route-fixture"))
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--owner-receipt", type=Path, required=True)
    parser.add_argument("--holder-pid", type=int, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--worker-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prefilter-result", type=Path)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--materials-root", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--route-fixture", type=Path)
    parser.add_argument("--application-ledger", type=Path)
    args = parser.parse_args()
    if args.action == "route-fixture" and args.route_fixture is None:
        parser.error("route-fixture action requires --route-fixture")
    if args.action == "run" and args.route_fixture is not None:
        parser.error("run action cannot consume --route-fixture")
    run_worker(
        database=args.database,
        owner_receipt=args.owner_receipt,
        holder_pid=args.holder_pid,
        run_id=args.run_id,
        lock_path=args.lock,
        worker_receipt=args.worker_receipt,
        output=args.output,
        prefilter_result=args.prefilter_result,
        profile_path=args.profile,
        materials_root=args.materials_root,
        evidence_dir=args.evidence_dir,
        route_fixture=args.route_fixture,
        application_ledger=args.application_ledger,
    )
    print(json.dumps({"status": "ok", "result_path": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
