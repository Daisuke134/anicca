import hashlib

import pytest

from horse_racing_agent.ingest import ingest_raw_boundary


RAW = "synthetic-raw-row-v1"
BASE = dict(
    source_url="https://www.jra.go.jp/", source_authority="official", jurisdiction="JRA",
    host_os="macos", storage_scope="mac_local_private", raw_payload=RAW,
    export_destination="local_raw_snapshot", robots_snapshot_url="https://www.jra.go.jp/robots.txt",
    robots_status="observed", terms_url="https://www.jra.go.jp/use/", terms_status="observed",
    permission_basis="JRA_PRIVATE_USE_POLICY", permission_document_verified=False,
)


def accepted(**overrides):
    return ingest_raw_boundary(**(BASE | overrides))


def test_accepts_nar_official_dynamic_path_and_permission_metadata():
    metadata = ingest_raw_boundary(
        "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily",
        "official", "NAR", "macos", "mac_local_private", b"synthetic", "local_raw_snapshot",
        "https://www.keiba.go.jp/robots.txt",
        "Crawl-delay: 10; TodayRaceInfo/DataRoom/DataDownload disallowed",
        "https://www.keiba.go.jp/terms.html", "USER_ATTESTED_PERMISSION_DOCUMENT_UNVERIFIED",
        "USER_ATTESTED_PERMISSION", False,
    )
    assert metadata["allowed_scope"] == "private_shadow"
    assert metadata["permission_document_verified"] is False
    assert metadata["cash_authorized"] is False
    assert metadata["raw_payload_exported"] is False
    assert "raw_payload" not in metadata and "synthetic" not in metadata.values()


@pytest.mark.parametrize(
    ("source_url", "authority", "jurisdiction"),
    [("https://www.jra.go.jp/", "official", "JRA"),
     ("https://race.netkeiba.com/", "secondary", "JRA"),
     ("https://nar.netkeiba.com/", "secondary", "NAR")],
)
def test_authority_matrix_and_shadow_scope(source_url, authority, jurisdiction):
    metadata = accepted(source_url=source_url, source_authority=authority, jurisdiction=jurisdiction)
    expected = "private_shadow" if authority == "official" else "shadow_only"
    assert metadata["allowed_scope"] == expected
    assert metadata["cash_authorized"] is False


@pytest.mark.parametrize("source_url", ["https://evil-jra.go.jp/race", "https://race.netkeiba.com.evil.example/race"])
def test_rejects_hostname_spoof(source_url):
    with pytest.raises(ValueError, match="source URL/authority mismatch"):
        accepted(source_url=source_url)


@pytest.mark.parametrize(
    ("source_url", "source_authority", "jurisdiction"),
    [("http://www.jra.go.jp/", "official", "JRA"),
     ("https://www.jra.go.jp/", "secondary", "JRA"),
     ("https://www.jra.go.jp/", "official", "NAR"),
     ("https://www.keiba.go.jp/KeibaWeb/DataDownloadEvil", "official", "NAR")],
)
def test_rejects_invalid_source_contract(source_url, source_authority, jurisdiction):
    with pytest.raises(ValueError, match="source URL/authority mismatch"):
        accepted(source_url=source_url, source_authority=source_authority, jurisdiction=jurisdiction)


def test_rejects_nar_path_traversal():
    with pytest.raises(ValueError, match="source URL/authority mismatch"):
        accepted(
            source_url="https://www.keiba.go.jp/KeibaWeb/DataDownload/../../outside",
            source_authority="official", jurisdiction="NAR",
        )


@pytest.mark.parametrize("field", ["host_os", "storage_scope", "export_destination"])
def test_rejects_non_mac_local_environment(field):
    with pytest.raises(ValueError, match="Mac-local storage contract"):
        accepted(**{field: {"host_os": "linux", "storage_scope": "cloud", "export_destination": "telegram"}[field]})


@pytest.mark.parametrize("raw_payload", [None, bytearray(b"synthetic"), 123])
def test_rejects_non_string_or_bytes_payload(raw_payload):
    with pytest.raises(ValueError, match="raw payload must be str or bytes"):
        accepted(raw_payload=raw_payload)


@pytest.mark.parametrize(
    "overrides",
    [{field: ""} for field in ("robots_snapshot_url", "robots_status", "terms_url", "terms_status", "permission_basis")]
    + [{"permission_document_verified": "false"}],
)
def test_rejects_invalid_permission_metadata(overrides):
    with pytest.raises(ValueError, match="permission metadata"):
        accepted(**overrides)


def test_returns_redacted_utf8_hash_and_byte_size():
    payload = "日本語"
    metadata = accepted(raw_payload=payload)
    assert metadata["content_sha256"] == hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert metadata["payload_size"] == len(payload.encode("utf-8"))
    assert payload not in metadata.values() and "raw_payload" not in metadata
