from datetime import datetime, timedelta, timezone

import pytest

from horse_racing_agent.nar_source import FetchRequest, classify_download, plan_nar_fetch


JST = timezone(timedelta(hours=9))

TODAY_HTML = """
<html>
  <a href="/KeibaWeb/TodayRaceInfo/TodayRaceInfoTop">today</a>
  <a href="/KeibaWeb/DataRoom/DataRoomTop">data room</a>
  <a href="/KeibaWeb/DataDownload/RaceDataDownload?type=daily&date=20270811">daily race</a>
  <a href="/KeibaWeb/DataDownload/OddsDataDownload?type=daily&date=20270811" aria-disabled="true">daily odds</a>
</html>
"""

MONTHLY_HTML = """
<html>
  <a href="/KeibaWeb/MonthlyConveneInfo/MonthlyConveneInfoTop">monthly</a>
  <a href="/KeibaWeb/DataDownload/RaceDataDownload?type=monthly&k_year=2027&k_month=11">monthly race</a>
  <a href="/KeibaWeb/DataDownload/OddsDataDownload?type=monthly&k_year=2027&k_month=11">monthly odds</a>
</html>
"""


def test_planner_discovers_current_official_links_and_transport_kinds():
    now = datetime(2027, 11, 15, 1, 30, tzinfo=JST)

    requests = plan_nar_fetch(now, TODAY_HTML, MONTHLY_HTML)

    assert all(isinstance(request, FetchRequest) for request in requests)
    assert [request.transport for request in requests] == [
        "crwl",
        "crwl",
        "curl",
        "crwl",
        "curl",
        "curl",
    ]
    assert [request.artifact_kind for request in requests] == [
        "navigation",
        "navigation",
        "daily_race",
        "navigation",
        "monthly_race",
        "monthly_odds",
    ]
    urls = {request.url for request in requests}
    assert "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=daily&date=20270811" in urls
    assert "https://www.keiba.go.jp/KeibaWeb/DataDownload/RaceDataDownload?type=monthly&k_year=2027&k_month=11" in urls
    assert "202608" not in " ".join(urls)
    assert all(request.url.startswith("https://www.keiba.go.jp/") for request in requests)


def test_planner_applies_daily_two_minute_and_monthly_two_am_gates():
    now = datetime(2027, 11, 15, 1, 30, tzinfo=JST)

    requests = plan_nar_fetch(now, TODAY_HTML, MONTHLY_HTML)

    daily = [request for request in requests if request.artifact_kind == "daily_race"]
    monthly = [request for request in requests if request.artifact_kind == "monthly_race"]
    monthly_navigation = [
        request
        for request in requests
        if request.artifact_kind == "navigation" and "MonthlyConveneInfo" in request.url
    ]
    assert daily and daily[0].not_before == now + timedelta(minutes=2)
    assert monthly and monthly[0].not_before == datetime(2027, 11, 15, 2, tzinfo=JST)
    assert monthly_navigation and monthly_navigation[0].not_before == datetime(2027, 11, 15, 2, tzinfo=JST)


def test_classifier_marks_duplicate_binary_as_unchanged():
    digest = "a" * 64

    assert classify_download(
        http_status=200,
        content_type="application/zip; charset=binary",
        body_sha256=digest,
        previous_sha256=digest,
    ) == "UNCHANGED"
    assert classify_download(
        http_status=200,
        content_type="application/zip",
        body_sha256=digest,
        previous_sha256=None,
    ) == "NEW"


def test_classifier_marks_disabled_odds_as_not_published():
    assert classify_download(
        http_status=200,
        content_type="text/html",
        body_sha256="",
        previous_sha256=None,
    ) == "NOT_PUBLISHED"
    assert classify_download(
        http_status=204,
        content_type="application/octet-stream",
        body_sha256="",
        previous_sha256=None,
    ) == "NOT_PUBLISHED"


@pytest.mark.parametrize(
    ("http_status", "content_type", "body_sha256"),
    [
        (500, "application/zip", "a" * 64),
        (200, "application/json", "a" * 64),
        (200, "application/zip", "not-a-sha256"),
    ],
)
def test_classifier_rejects_invalid_downloads(http_status, content_type, body_sha256):
    assert classify_download(
        http_status=http_status,
        content_type=content_type,
        body_sha256=body_sha256,
        previous_sha256=None,
    ) == "INVALID"


def test_planner_rejects_non_official_download_host():
    with pytest.raises(ValueError, match="official NAR URL"):
        plan_nar_fetch(
            datetime(2027, 11, 15, 2, tzinfo=JST),
            TODAY_HTML.replace(
                "/KeibaWeb/DataDownload/",
                "https://www.keiba.go.jp.evil.example/KeibaWeb/DataDownload/",
            ),
            MONTHLY_HTML,
        )
