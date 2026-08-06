from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .ledger import FenceError, Ledger
from .route_executor import execute_next_message_route


def _private_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_bytes(data)
    os.chmod(path, 0o600)


def run_no_send_fixture(
    *,
    request_path: Path,
    evidence_dir: Path,
    authority: dict[str, Any],
) -> dict[str, Any]:
    if authority.get("actor") != "resident_worker":
        raise RuntimeError("route fixture requires resident worker authority")
    if authority.get("worker_pid") != os.getpid():
        raise RuntimeError("route fixture resident worker PID does not match")
    for key in ("run_id", "lease_id", "fence"):
        if authority.get(key) in (None, ""):
            raise RuntimeError("route fixture resident worker authority is incomplete")
    request = json.loads(Path(request_path).read_text(encoding="utf-8"))
    if request.get("version") != 1 or not isinstance(request.get("request_id"), str):
        raise ValueError("route fixture request is invalid")
    application = request.get("application")
    routes = request.get("routes")
    if not isinstance(application, dict) or not isinstance(routes, list) or not routes:
        raise ValueError("route fixture application routes are missing")
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(evidence_dir, 0o700)
    message = evidence_dir / "fixture-message.txt"
    resume = evidence_dir / "fixture-resume.pdf"
    _private_file(message, b"NO-SEND ROUTE FIXTURE\n")
    _private_file(resume, b"%PDF-1.4\nNO-SEND ROUTE FIXTURE\n")
    database = evidence_dir / "route-fixture-ledger.sqlite3"
    source_text = f"no-send fixture {request['request_id']}"
    source_sha256 = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    ledger = Ledger(database)
    simulated_transport_count = 0
    try:
        application_id = ledger.add_application(
            str(application.get("company") or ""),
            str(application.get("title") or ""),
            str(application.get("url") or ""),
        )
        route_ids: list[str] = []
        for ordinal, route in enumerate(routes, start=1):
            if not isinstance(route, dict):
                raise ValueError("route fixture route is invalid")
            route_ids.append(
                ledger.register_application_route(
                    application_id,
                    route_kind=str(route.get("kind") or ""),
                    endpoint=str(route.get("endpoint") or ""),
                    ordinal=ordinal,
                    source_url="https://careers.fixture.test/jobs",
                    source_sha256=source_sha256,
                    recipient_acceptance=str(route.get("acceptance") or ""),
                )
            )
        next_fence = int(authority["fence"]) * 100
        while True:
            current = [
                route
                for route in ledger.application_routes(application_id)
                if route["delivery_state"] == "eligible"
            ]
            if not current:
                break
            route = current[0]
            next_fence += 1
            if route["route_kind"] in {"canonical_ats", "alternate_official"}:
                ledger.claim_application_route(
                    str(route["route_id"]),
                    actor="resident_worker",
                    fence=next_fence,
                    message_path=str(message),
                    message_sha256=hashlib.sha256(message.read_bytes()).hexdigest(),
                    resume_path=str(resume),
                    resume_sha256=hashlib.sha256(resume.read_bytes()).hexdigest(),
                )
                ledger.complete_application_route(
                    str(route["route_id"]),
                    fence=next_fence,
                    state="failed",
                    provider_id="fixture:no-send-browser-failure",
                    evidence_sha256=hashlib.sha256(
                        f"{route['route_id']}:failed".encode("utf-8")
                    ).hexdigest(),
                )
                continue

            def no_send_transport(**payload: Any) -> dict[str, str]:
                nonlocal simulated_transport_count
                simulated_transport_count += 1
                return {
                    "status": "failed",
                    "provider_id": "fixture:no-send-message-failure",
                    "evidence_sha256": hashlib.sha256(
                        str(payload["idempotency_key"]).encode("utf-8")
                    ).hexdigest(),
                }

            execute_next_message_route(
                ledger=ledger,
                application_id=application_id,
                actor="resident_worker",
                fence=next_fence,
                message_path=message,
                resume_path=resume,
                transport=no_send_transport,
            )
        replay = execute_next_message_route(
            ledger=ledger,
            application_id=application_id,
            actor="resident_worker",
            fence=next_fence + 1,
            message_path=message,
            resume_path=resume,
            transport=lambda **payload: (_ for _ in ()).throw(
                AssertionError("no-send replay invoked transport")
            ),
        )
        ordered_attempts = [
            {
                "route_kind": route["route_kind"],
                "state": route["delivery_state"],
                "provider_id": route["provider_id"],
            }
            for route in ledger.application_routes(application_id)
        ]

        crash_id = ledger.add_application(
            "Crash Fixture Corp",
            "AI Engineer",
            "https://jobs.fixture.test/crash-role",
        )
        crash_routes = [
            ledger.register_application_route(
                crash_id,
                route_kind=kind,
                endpoint=endpoint,
                ordinal=index,
                source_url="https://careers.fixture.test/jobs",
                source_sha256=source_sha256,
                recipient_acceptance=acceptance,
            )
            for index, (kind, endpoint, acceptance) in enumerate(
                [
                    ("canonical_ats", "https://jobs.fixture.test/crash-role", "not_applicable"),
                    ("recruiting_email", "jobs@fixture.test", "accepts_applications"),
                ],
                start=1,
            )
        ]
        crash_fence = next_fence + 100
        ledger.claim_application_route(
            crash_routes[0],
            actor="resident_worker",
            fence=crash_fence,
            message_path=str(message),
            message_sha256=hashlib.sha256(message.read_bytes()).hexdigest(),
            resume_path=str(resume),
            resume_sha256=hashlib.sha256(resume.read_bytes()).hexdigest(),
        )
        ledger.close()
        ledger = Ledger(database)
        try:
            ledger.claim_application_route(
                crash_routes[1],
                actor="resident_worker",
                fence=crash_fence + 1,
                message_path=str(message),
                message_sha256=hashlib.sha256(message.read_bytes()).hexdigest(),
                resume_path=str(resume),
                resume_sha256=hashlib.sha256(resume.read_bytes()).hexdigest(),
            )
        except FenceError:
            crash_replay_status = "cross_route_fenced"
        else:
            crash_replay_status = "unsafe_claim_succeeded"
        result = {
            "version": 1,
            "status": "fixture_verified",
            "request_id": request["request_id"],
            "send_count": 0,
            "simulated_transport_count": simulated_transport_count,
            "ordered_attempts": ordered_attempts,
            "replay_status": replay["status"],
            "crash_replay_status": crash_replay_status,
            "actor_provenance": {
                "actor": authority["actor"],
                "worker_pid": authority["worker_pid"],
                "run_id": authority["run_id"],
                "lease_id": authority["lease_id"],
                "fence": authority["fence"],
            },
        }
        if crash_replay_status != "cross_route_fenced":
            raise RuntimeError("route fixture crash replay fence failed")
        return result
    finally:
        ledger.close()
        os.chmod(database, 0o600)
