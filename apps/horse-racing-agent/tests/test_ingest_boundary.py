import hashlib

import pytest

from horse_racing_agent.ingest import IngestBoundaryRejected, ingest_raw_boundary


RAW = "synthetic-raw-row-v1"
BASE = dict(source="JRA-VAN JV-Link", jurisdiction="JRA", worker_os="windows", storage_scope="owned_windows_local", raw_payload=RAW, export_destination="local_raw_db")


def accepted(**overrides):
    return ingest_raw_boundary(**(BASE | overrides))


def test_allowlist_keeps_jurisdictions_separate():
    assert accepted()["jurisdiction"] == "JRA"
    assert accepted(source="UmaConn/NV-Link", jurisdiction="NAR")["jurisdiction"] == "NAR"
    for bad in ({"source": "unregistered-source"}, {"jurisdiction": "NAR"}):
        with pytest.raises(IngestBoundaryRejected):
            accepted(**bad)


def test_windows_local_boundary_rejects_nonlocal_exports():
    for overrides in ({"worker_os": "linux"}, {"storage_scope": "cloud"}, {"export_destination": "telegram"}, {"export_destination": "cloud"}, {"export_destination": "Git"}, {"export_destination": "log"}):
        with pytest.raises(IngestBoundaryRejected):
            accepted(**overrides)


def test_receipt_omits_raw_and_hash_is_deterministic():
    first = accepted()
    second = accepted(raw_payload=RAW.encode())

    assert first == second
    assert first["content_hash"] == hashlib.sha256(RAW.encode()).hexdigest()
    assert first["raw_payload_exported"] is False
    assert "raw_payload" not in first
    assert RAW not in first.values()
