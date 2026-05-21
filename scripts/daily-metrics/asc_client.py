"""App Store Connect API client for fetching download and conversion metrics."""

import gzip
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
import jwt

from models import AppStoreMetrics
from window import ReportingWindow, asc_reporting_window

ASC_BASE_URL = "https://api.appstoreconnect.apple.com/v1"
TOKEN_EXPIRY_SECONDS = 1200  # 20 minutes

# Token cache (W-1 fix)
_cached_token: str | None = None
_token_expires_at: int = 0


def _generate_token() -> str:
    """Generate JWT token for App Store Connect API. Cached for 20 min."""
    global _cached_token, _token_expires_at
    now = int(time.time())
    if _cached_token and now < _token_expires_at - 60:
        return _cached_token

    key_id = os.environ["ASC_KEY_ID"]
    issuer_id = os.environ["ASC_ISSUER_ID"]
    private_key = os.environ.get("ASC_PRIVATE_KEY", "")
    if not private_key:
        key_path = Path(os.environ.get("ASC_PRIVATE_KEY_PATH", f"/home/anicca/.keys/AuthKey_{key_id}.p8"))
        if key_path.exists():
            private_key = key_path.read_text()
        else:
            raise KeyError("ASC_PRIVATE_KEY")

    payload = {
        "iss": issuer_id,
        "iat": now,
        "exp": now + TOKEN_EXPIRY_SECONDS,
        "aud": "appstoreconnect-v1",
    }
    headers = {"kid": key_id, "typ": "JWT"}
    token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
    _cached_token = token
    _token_expires_at = now + TOKEN_EXPIRY_SECONDS
    return token


def _get_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_generate_token()}",
        "Content-Type": "application/json",
    }


async def fetch_app_store_metrics(window: ReportingWindow | None = None) -> AppStoreMetrics:
    """Fetch downloads, impressions, page views, and CVR from App Store Connect."""
    if window is None:
        window = asc_reporting_window()
    start_date = window.start_date
    end_date = window.end_date

    headers = _get_headers()
    total_downloads = 0
    downloads_by_country: dict[str, int] = {}
    impressions = 0
    page_views = 0

    # C-2: Vendor number is required for sales reports
    vendor_number = os.environ.get("ASC_VENDOR_NUMBER", "")
    if not vendor_number:
        print("WARNING: ASC_VENDOR_NUMBER not set. Sales reports may return empty.", file=sys.stderr)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch sales reports (daily, summary)
        for day_offset in range(7):
            report_date = start_date + timedelta(days=day_offset)
            params = {
                "filter[frequency]": "DAILY",
                "filter[reportDate]": report_date.isoformat(),
                "filter[reportSubType]": "SUMMARY",
                "filter[reportType]": "SALES",
                "filter[vendorNumber]": vendor_number,
            }

            try:
                resp = await client.get(
                    f"{ASC_BASE_URL}/salesReports",
                    headers=headers,
                    params=params,
                )
                if resp.status_code == 200:
                    # Sales reports are gzip compressed
                    try:
                        content = gzip.decompress(resp.content).decode("utf-8")
                    except gzip.BadGzipFile:
                        content = resp.text  # Fallback if not compressed
                    lines = content.strip().split("\n")
                    if len(lines) > 1:
                        # S-2: Parse header row for column indices
                        header_cols = lines[0].split("\t")
                        units_idx = _find_col(header_cols, "Units", fallback=7)
                        country_idx = _find_col(header_cols, "Country Code", fallback=12)
                        pti_idx = _find_col(header_cols, "Product Type Identifier", fallback=6)
                        for line in lines[1:]:
                            cols = line.split("\t")
                            if len(cols) > max(units_idx, country_idx, pti_idx):
                                # Only count new downloads (type 1), not updates (7) or IAP (3)
                                product_type = cols[pti_idx].strip()
                                if not product_type.startswith("1"):
                                    continue
                                units = int(cols[units_idx]) if cols[units_idx].isdigit() else 0
                                country = cols[country_idx] if len(cols) > country_idx else "Unknown"
                                total_downloads += units
                                downloads_by_country[country] = (
                                    downloads_by_country.get(country, 0) + units
                                )
                else:
                    print(f"WARNING: ASC sales report {report_date}: HTTP {resp.status_code}", file=sys.stderr)
            except httpx.HTTPError as e:
                # W-2: Log instead of silently swallowing
                print(f"WARNING: ASC sales report {report_date} failed: {e}", file=sys.stderr)
                continue

        # Fetch app analytics for impressions and page views
        # Uses the Analytics Reports API (async multi-step flow)
        try:
            impressions, page_views = await _fetch_analytics(
                client, headers, start_date, end_date
            )
        except Exception as e:
            print(f"WARNING: ASC analytics fetch failed: {e}", file=sys.stderr)

    cvr = (total_downloads / page_views * 100) if page_views > 0 else 0.0

    # Sort countries by downloads descending, convert to immutable tuple
    sorted_countries = tuple(
        sorted(downloads_by_country.items(), key=lambda x: x[1], reverse=True)
    )

    return AppStoreMetrics(
        total_downloads_7d=total_downloads,
        downloads_by_country=sorted_countries,
        impressions=impressions,
        page_views=page_views,
        cvr_page_to_download=round(cvr, 1),
    )


async def _fetch_analytics(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    start_date: date,
    end_date: date,
) -> tuple[int, int]:
    """Fetch impressions and page views via Analytics Reports API.

    Flow: get app_id → find/create ONGOING report request
          → list reports (APP_STORE_ENGAGEMENT) → get instances
          → download segment TSV → sum impressions & page views.

    Returns (impressions, page_views).
    """
    # Step 1: Get app ID
    apps_resp = await client.get(
        f"{ASC_BASE_URL}/apps",
        headers=headers,
        params={"filter[bundleId]": "ai.anicca.app.ios"},
    )
    if apps_resp.status_code != 200:
        print(f"WARNING: ASC apps endpoint: HTTP {apps_resp.status_code}", file=sys.stderr)
        return 0, 0

    apps_data = apps_resp.json()
    if not apps_data.get("data"):
        print("WARNING: No app found for bundle ID ai.anicca.app.ios", file=sys.stderr)
        return 0, 0

    app_id = apps_data["data"][0]["id"]

    # Step 2: Find existing ONGOING report request or create one
    req_resp = await client.get(
        f"{ASC_BASE_URL}/apps/{app_id}/analyticsReportRequests",
        headers=headers,
        params={"filter[accessType]": "ONGOING"},
    )
    request_id = None
    if req_resp.status_code == 200:
        for req in req_resp.json().get("data", []):
            if req.get("attributes", {}).get("accessType") == "ONGOING":
                request_id = req["id"]
                break

    if not request_id:
        # Create an ONGOING report request (first-time setup)
        create_resp = await client.post(
            f"{ASC_BASE_URL}/analyticsReportRequests",
            headers=headers,
            json={
                "data": {
                    "type": "analyticsReportRequests",
                    "attributes": {"accessType": "ONGOING"},
                    "relationships": {
                        "app": {"data": {"type": "apps", "id": app_id}}
                    },
                }
            },
        )
        if create_resp.status_code in (200, 201):
            request_id = create_resp.json()["data"]["id"]
            print("INFO: Created ONGOING analytics report request. Data available in 1-2 days.", file=sys.stderr)
            return 0, 0
        else:
            print(f"WARNING: Failed to create analytics report request: {create_resp.status_code} {create_resp.text}", file=sys.stderr)
            return 0, 0

    # Step 3: List reports filtered by APP_STORE_ENGAGEMENT
    reports_resp = await client.get(
        f"{ASC_BASE_URL}/analyticsReportRequests/{request_id}/reports",
        headers=headers,
        params={"filter[category]": "APP_STORE_ENGAGEMENT"},
    )
    if reports_resp.status_code != 200:
        print(f"WARNING: ASC analytics reports: HTTP {reports_resp.status_code}", file=sys.stderr)
        return 0, 0

    reports_data = reports_resp.json().get("data", [])
    if not reports_data:
        print("WARNING: No APP_STORE_ENGAGEMENT reports available yet.", file=sys.stderr)
        return 0, 0

    # Find the report with name containing "App Store Engagement" or similar
    report_id = reports_data[0]["id"]

    # Step 4: Get report instances (daily granularity)
    instances_resp = await client.get(
        f"{ASC_BASE_URL}/analyticsReports/{report_id}/instances",
        headers=headers,
        params={"filter[granularity]": "DAILY", "limit": 30},
    )
    if instances_resp.status_code != 200:
        print(f"WARNING: ASC analytics instances: HTTP {instances_resp.status_code}", file=sys.stderr)
        return 0, 0

    instances = instances_resp.json().get("data", [])
    if not instances:
        print("WARNING: No analytics report instances available.", file=sys.stderr)
        return 0, 0

    # Filter instances within our date range
    total_impressions = 0
    total_page_views = 0

    for instance in instances:
        proc_date_str = instance.get("attributes", {}).get("processingDate", "")
        if not proc_date_str:
            continue
        try:
            proc_date = date.fromisoformat(proc_date_str[:10])
        except ValueError:
            continue
        if proc_date < start_date or proc_date > end_date:
            continue

        instance_id = instance["id"]

        # Step 5: Get segments (download URLs)
        segments_resp = await client.get(
            f"{ASC_BASE_URL}/analyticsReportInstances/{instance_id}/segments",
            headers=headers,
        )
        if segments_resp.status_code != 200:
            continue

        for segment in segments_resp.json().get("data", []):
            url = segment.get("attributes", {}).get("url", "")
            if not url:
                continue

            # Download and parse the TSV segment
            dl_resp = await client.get(url)
            if dl_resp.status_code != 200:
                continue

            try:
                tsv_content = gzip.decompress(dl_resp.content).decode("utf-8")
            except gzip.BadGzipFile:
                tsv_content = dl_resp.text

            lines = tsv_content.strip().split("\n")
            if len(lines) < 2:
                continue

            tsv_headers = lines[0].split("\t")
            imp_idx = _find_col(tsv_headers, "Impressions Total Unique", fallback=-1)
            pv_idx = _find_col(tsv_headers, "Product Page Views Total Unique", fallback=-1)

            # Fallback column names
            if imp_idx == -1:
                imp_idx = _find_col(tsv_headers, "Impressions", fallback=-1)
            if pv_idx == -1:
                pv_idx = _find_col(tsv_headers, "Page Views", fallback=-1)

            for line in lines[1:]:
                cols = line.split("\t")
                if imp_idx >= 0 and imp_idx < len(cols):
                    val = cols[imp_idx].strip()
                    total_impressions += int(val) if val.isdigit() else 0
                if pv_idx >= 0 and pv_idx < len(cols):
                    val = cols[pv_idx].strip()
                    total_page_views += int(val) if val.isdigit() else 0

    return total_impressions, total_page_views


def _find_col(headers: list[str], name: str, fallback: int) -> int:
    """Find column index by name, with fallback for backwards compatibility."""
    try:
        return headers.index(name)
    except ValueError:
        return fallback
