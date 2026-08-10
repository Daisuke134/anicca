from dataclasses import dataclass
from datetime import datetime, timedelta
from html.parser import HTMLParser
import re
from typing import Literal
from urllib.parse import parse_qs, unquote, urljoin, urlsplit


ArtifactKind = Literal[
    "navigation", "daily_race", "daily_odds", "monthly_race", "monthly_odds"
]
Transport = Literal["crwl", "curl"]


@dataclass(frozen=True)
class FetchRequest:
    url: str
    transport: Transport
    artifact_kind: ArtifactKind
    not_before: datetime


_ORIGIN = "https://www.keiba.go.jp/"
_PATH_PREFIXES = (
    "/KeibaWeb/TodayRaceInfo",
    "/KeibaWeb/DataRoom",
    "/KeibaWeb/DataDownload",
    "/KeibaWeb/MonthlyConveneInfo",
)
_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")
_BINARY_TYPES = {"application/zip", "application/x-zip-compressed", "application/octet-stream"}


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        hrefs = [values[name] for name in ("href", "data-href", "data-url") if values.get(name)]
        disabled = (
            "disabled" in values
            or values.get("aria-disabled", "").casefold() == "true"
            or "disabled" in values.get("class", "").casefold().split()
        )
        self.links.extend((href, disabled) for href in hrefs if href is not None)


def _normalise_url(href: str) -> str:
    try:
        raw_path = urlsplit(href).path
        parsed = urlsplit(urljoin(_ORIGIN, href))
        port = parsed.port
        decoded_path = _decode_path(parsed.path)
    except (TypeError, ValueError):
        raise ValueError("official NAR URL is invalid") from None
    _reject_dot_segments(raw_path)
    _reject_dot_segments(decoded_path)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "www.keiba.go.jp"
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("official NAR URL is invalid")
    if not any(decoded_path == prefix or decoded_path.startswith(prefix + "/") for prefix in _PATH_PREFIXES):
        raise ValueError("official NAR URL is invalid")
    return parsed._replace(netloc="www.keiba.go.jp", path=decoded_path, fragment="").geturl()


def _decode_path(path: str) -> str:
    decoded = path
    for _ in range(3):
        unquoted = unquote(decoded)
        if unquoted == decoded:
            break
        decoded = unquoted
    return decoded


def _reject_dot_segments(path: str) -> None:
    if any(segment in {".", ".."} for segment in re.split(r"[/\\]", path)):
        raise ValueError("official NAR URL is invalid")


def _link_kind(url: str, default_period: Literal["daily", "monthly"]) -> ArtifactKind | None:
    parsed = urlsplit(url)
    path = parsed.path.casefold()
    if any(marker in path for marker in ("/todayraceinfo", "/dataroom", "/monthlyconveneinfo")):
        return "navigation"
    query = parse_qs(parsed.query)
    period = query.get("type", [default_period])[0].casefold()
    if "oddsdatadownload" in path:
        return "monthly_odds" if period == "monthly" else "daily_odds" if period == "daily" else None
    if "racedatadownload" in path:
        return "monthly_race" if period == "monthly" else "daily_race" if period == "daily" else None
    return None


def _discover(html: str, default_period: Literal["daily", "monthly"]) -> list[tuple[str, ArtifactKind]]:
    parser = _LinkParser()
    parser.feed(html)
    discovered: list[tuple[str, ArtifactKind]] = []
    for href, disabled in parser.links:
        raw_path = urlsplit(href).path.casefold()
        candidate_path = urlsplit(urljoin(_ORIGIN, href)).path.casefold()
        if "keibaweb" not in raw_path and "keibaweb" not in candidate_path:
            continue
        url = _normalise_url(href)
        kind = _link_kind(url, default_period)
        if kind is None or (disabled and kind == "daily_odds"):
            continue
        discovered.append((url, kind))
    return discovered


def _not_before(now: datetime, period: Literal["daily", "monthly"]) -> datetime:
    if period == "daily":
        return now + timedelta(minutes=2)
    update_gate = now.replace(hour=2, minute=0, second=0, microsecond=0)
    return max(now, update_gate)


def plan_nar_fetch(now: datetime, today_html: str, monthly_html: str) -> tuple[FetchRequest, ...]:
    if not isinstance(now, datetime) or not isinstance(today_html, str) or not isinstance(monthly_html, str):
        raise TypeError("now and HTML inputs have invalid types")
    requests: list[FetchRequest] = []
    seen: set[str] = set()
    for html, period in ((today_html, "daily"), (monthly_html, "monthly")):
        for url, kind in _discover(html, period):
            if url in seen:
                continue
            requests.append(
                FetchRequest(url, "crwl" if kind == "navigation" else "curl", kind, _not_before(now, period))
            )
            seen.add(url)
    return tuple(requests)


def classify_download(
    *, http_status: int, content_type: str, body_sha256: str, previous_sha256: str | None
) -> Literal["NEW", "UNCHANGED", "NOT_PUBLISHED", "INVALID"]:
    if type(http_status) is not int or not isinstance(content_type, str) or not isinstance(body_sha256, str):
        return "INVALID"
    media_type = content_type.partition(";")[0].strip().casefold()
    if http_status in {200, 204, 404, 410} and not body_sha256:
        return "NOT_PUBLISHED"
    if http_status in {204, 404, 410} and media_type not in _BINARY_TYPES:
        return "NOT_PUBLISHED"
    if http_status == 200 and media_type in {"text/html", "text/plain"}:
        return "NOT_PUBLISHED"
    if http_status != 200 or media_type not in _BINARY_TYPES or not _SHA256.fullmatch(body_sha256):
        return "INVALID"
    if previous_sha256 is not None and not isinstance(previous_sha256, str):
        return "INVALID"
    if previous_sha256 is not None and not _SHA256.fullmatch(previous_sha256):
        return "INVALID"
    return "UNCHANGED" if previous_sha256 is not None and previous_sha256.casefold() == body_sha256.casefold() else "NEW"
