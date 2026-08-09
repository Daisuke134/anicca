from hashlib import sha256


_SOURCE_JURISDICTION = {"JRA-VAN JV-Link": "JRA", "UmaConn/NV-Link": "NAR"}


class IngestBoundaryRejected(ValueError):
    pass


def ingest_raw_boundary(
    *, source: str, jurisdiction: str, worker_os: str, storage_scope: str,
    raw_payload: str | bytes, export_destination: str,
) -> dict[str, object]:
    if _SOURCE_JURISDICTION.get(source) != jurisdiction:
        raise IngestBoundaryRejected("source or jurisdiction is not allowlisted")
    if worker_os.casefold() != "windows" or storage_scope != "owned_windows_local":
        raise IngestBoundaryRejected("ingest must remain on owned Windows local storage")
    if export_destination != "local_raw_db":
        raise IngestBoundaryRejected("raw export destination is not allowed")
    if not isinstance(raw_payload, (str, bytes)):
        raise IngestBoundaryRejected("raw payload type is not allowed")
    payload = raw_payload.encode("utf-8") if isinstance(raw_payload, str) else raw_payload

    return {
        "source": source,
        "jurisdiction": jurisdiction,
        "worker_os": "windows",
        "storage_scope": "owned_windows_local",
        "export_destination": "local_raw_db",
        "content_hash": sha256(payload).hexdigest(),
        "payload_size": len(payload),
        "raw_payload_exported": False,
    }
