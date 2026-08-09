from hashlib import sha256
from urllib.parse import urlsplit


_SOURCE_SCOPES = {
    ("www.jra.go.jp", "official", "JRA"): "private_shadow",
    ("www.keiba.go.jp", "official", "NAR"): "private_shadow",
    ("race.netkeiba.com", "secondary", "JRA"): "shadow_only",
    ("nar.netkeiba.com", "secondary", "NAR"): "shadow_only",
}
_NAR_OFFICIAL_PATHS = (
    "/KeibaWeb/TodayRaceInfo",
    "/KeibaWeb/DataRoom",
    "/KeibaWeb/DataDownload",
    "/KeibaWeb/MonthlyConveneInfo",
)


def _source_scope(source_url: str, source_authority: str, jurisdiction: str) -> str:
    if not all(isinstance(value, str) for value in (source_url, source_authority, jurisdiction)):
        raise ValueError("source URL/authority mismatch")
    try:
        parsed = urlsplit(source_url)
        hostname = parsed.hostname
    except (TypeError, ValueError):
        raise ValueError("source URL/authority mismatch") from None

    scope = _SOURCE_SCOPES.get((hostname, source_authority, jurisdiction))
    if parsed.scheme != "https" or scope is None:
        raise ValueError("source URL/authority mismatch")
    if hostname == "www.keiba.go.jp":
        path = parsed.path
        if any(segment in {".", ".."} for segment in path.split("/")):
            raise ValueError("source URL/authority mismatch")
        if not any(path == prefix or path.startswith(prefix + "/") for prefix in _NAR_OFFICIAL_PATHS) and not path.lower().endswith(".pdf"):
            raise ValueError("source URL/authority mismatch")
    return scope


def ingest_raw_boundary(
    source_url: str,
    source_authority: str,
    jurisdiction: str,
    host_os: str,
    storage_scope: str,
    raw_payload: str | bytes,
    export_destination: str,
    robots_snapshot_url: str,
    robots_status: str,
    terms_url: str,
    terms_status: str,
    permission_basis: str,
    permission_document_verified: bool,
) -> dict[str, str | int | bool]:
    allowed_scope = _source_scope(source_url, source_authority, jurisdiction)

    if (host_os, storage_scope, export_destination) != (
        "macos", "mac_local_private", "local_raw_snapshot"
    ):
        raise ValueError("Mac-local storage contract")
    if not isinstance(raw_payload, (str, bytes)):
        raise ValueError("raw payload must be str or bytes")
    permission_values = (robots_snapshot_url, robots_status, terms_url, terms_status, permission_basis)
    if (
        any(not isinstance(value, str) or not value.strip() for value in permission_values)
        or type(permission_document_verified) is not bool
    ):
        raise ValueError("permission metadata")

    payload = raw_payload.encode("utf-8") if isinstance(raw_payload, str) else raw_payload
    return {
        "source_url": source_url,
        "source_authority": source_authority,
        "jurisdiction": jurisdiction,
        "host_os": host_os,
        "storage_scope": storage_scope,
        "export_destination": export_destination,
        "content_sha256": sha256(payload).hexdigest(),
        "payload_size": len(payload),
        "robots_snapshot_url": robots_snapshot_url,
        "robots_status": robots_status,
        "terms_url": terms_url,
        "terms_status": terms_status,
        "permission_basis": permission_basis,
        "permission_document_verified": permission_document_verified,
        "raw_payload_exported": False,
        "allowed_scope": allowed_scope,
        "cash_authorized": False,
    }
