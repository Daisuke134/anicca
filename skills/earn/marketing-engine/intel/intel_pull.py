#!/usr/bin/env python3
"""Collect bounded marketing intel evidence and accept only grounded judgments."""

from __future__ import annotations

import dataclasses
import datetime as dt
import fcntl
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import uuid
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import intel_store


USER_AGENT = "AniccaMarketingIntel/1.0 (+https://aniccaai.com)"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
HERE = pathlib.Path(__file__).resolve().parent
ENGINE_ROOT = HERE.parent
REPO_ROOT = ENGINE_ROOT.parents[2]


class JudgmentError(ValueError):
    pass


@dataclasses.dataclass
class HTTPResponse:
    status: int
    payload: bytes
    headers: dict[str, str]


class URLHTTP:
    def get(self, url: str, *, headers=None, params=None) -> HTTPResponse:
        if params:
            url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
        request = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read(MAX_RESPONSE_BYTES + 1)
                if len(payload) > MAX_RESPONSE_BYTES:
                    raise ValueError("response_exceeds_byte_limit")
                return HTTPResponse(response.status, payload, dict(response.headers.items()))
        except urllib.error.HTTPError as exc:
            payload = exc.read(MAX_RESPONSE_BYTES + 1)
            return HTTPResponse(exc.code, payload, dict(exc.headers.items()))


@dataclasses.dataclass
class CollectionResult:
    source_id: str
    status: str
    canonical_url: str | None
    http_status: int | None
    api_status: int | None
    item_ids: list[str]
    payload: dict | list | None
    reason: str | None = None
    error_class: str | None = None
    cache: dict = dataclasses.field(default_factory=dict)


def _headers(cache=None, extra=None):
    result = {"User-Agent": USER_AGENT, "Accept": "application/json, application/atom+xml, application/rss+xml, application/xml, text/xml"}
    cache = cache or {}
    if cache.get("etag"):
        result["If-None-Match"] = cache["etag"]
    if cache.get("last_modified"):
        result["If-Modified-Since"] = cache["last_modified"]
    result.update(extra or {})
    return result


def _response_cache(response):
    lowered = {str(key).lower(): value for key, value in response.headers.items()}
    return {
        key: value for key, value in {
            "etag": lowered.get("etag"),
            "last_modified": lowered.get("last-modified"),
        }.items() if value
    }


def _json(response, source_id):
    try:
        return json.loads(response.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid_json:{source_id}") from exc


def _failure(source, response, reason):
    return CollectionResult(source["id"], "error", source.get("url"), response.status, None, [], None, reason=reason)


def _collect_x_articles(source, http):
    handle = source["handle"].lstrip("@")
    canonical = f"https://x.com/{handle}"
    profile_url = f"https://api.fxtwitter.com/2/profile/{urllib.parse.quote(handle)}/articles"
    response = http.get(profile_url, headers=_headers())
    if response.status != 200:
        return CollectionResult(source["id"], "error", canonical, response.status, None, [], None, reason="x_profile_articles_http_error")
    profile = _json(response, source["id"])
    if profile.get("code") != 200 or not isinstance(profile.get("results"), list):
        return CollectionResult(source["id"], "error", canonical, response.status, profile.get("code"), [], None, reason="x_profile_articles_api_error")
    articles = []
    item_ids = []
    for summary in profile["results"][: int(source.get("limit", 5))]:
        item_id = str(summary.get("id") or "")
        if not item_id:
            continue
        detail_response = http.get(f"https://api.fxtwitter.com/2/status/{urllib.parse.quote(item_id)}", headers=_headers())
        if detail_response.status != 200:
            continue
        detail = _json(detail_response, source["id"])
        status = detail.get("status")
        if detail.get("code") != 200 or not isinstance(status, dict) or not isinstance(status.get("article"), dict):
            continue
        articles.append(status)
        item_ids.append(f"x:{item_id}")
    if not articles:
        return CollectionResult(source["id"], "error", canonical, response.status, profile.get("code"), [], {"profile": profile}, reason="no_complete_x_articles")
    return CollectionResult(source["id"], "success", canonical, response.status, profile.get("code"), item_ids, {"profile": profile, "articles": articles})


def _local_name(tag):
    return tag.rsplit("}", 1)[-1]


def _child_text(node, name):
    for child in node:
        if _local_name(child.tag) == name:
            return (child.text or "").strip() or None
    return None


def _parse_feed(payload, limit):
    root = ET.fromstring(payload)
    kind = _local_name(root.tag)
    entries = []
    if kind == "feed":
        candidates = [child for child in root if _local_name(child.tag) == "entry"]
        for entry in candidates[:limit]:
            link = None
            for child in entry:
                if _local_name(child.tag) == "link" and child.attrib.get("href"):
                    link = child.attrib["href"]
                    if child.attrib.get("rel", "alternate") == "alternate":
                        break
            native_id = _child_text(entry, "id") or link
            if native_id:
                entries.append({
                    "id": native_id,
                    "title": _child_text(entry, "title"),
                    "link": link,
                    "published_at": _child_text(entry, "published") or _child_text(entry, "updated"),
                    "summary": _child_text(entry, "summary") or _child_text(entry, "content"),
                })
    elif kind == "rss":
        channel = next((child for child in root if _local_name(child.tag) == "channel"), None)
        candidates = [] if channel is None else [child for child in channel if _local_name(child.tag) == "item"]
        for entry in candidates[:limit]:
            link = _child_text(entry, "link")
            native_id = _child_text(entry, "guid") or link
            if native_id:
                entries.append({
                    "id": native_id,
                    "title": _child_text(entry, "title"),
                    "link": link,
                    "published_at": _child_text(entry, "pubDate"),
                    "summary": _child_text(entry, "description"),
                })
    else:
        raise ValueError("unsupported_feed_format")
    return {"format": kind, "entries": entries}


def _collect_rss(source, http, cache):
    response = http.get(source["url"], headers=_headers(cache))
    current_cache = {**(cache or {}), **_response_cache(response)}
    if response.status == 304:
        return CollectionResult(source["id"], "unchanged", source["url"], 304, None, [], None, reason="not_modified", cache=current_cache)
    if response.status != 200:
        return CollectionResult(source["id"], "error", source["url"], response.status, None, [], None, reason="feed_http_error", cache=current_cache)
    parsed = _parse_feed(response.payload, int(source.get("limit", 20)))
    item_ids = [f"rss:{entry['id']}" for entry in parsed["entries"]]
    if not item_ids:
        return CollectionResult(source["id"], "error", source["url"], 200, None, [], parsed, reason="feed_has_no_identifiable_entries", cache=current_cache)
    return CollectionResult(source["id"], "success", source["url"], 200, None, item_ids, parsed, cache=current_cache)


def _collect_github_repo(source, http, env):
    repo = source["repo"]
    headers = _headers(extra={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    if env.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {env['GITHUB_TOKEN']}"
    response = http.get(f"https://api.github.com/repos/{repo}", headers=headers)
    if response.status != 200:
        return CollectionResult(source["id"], "error", f"https://github.com/{repo}", response.status, None, [], None, reason="github_repo_http_error")
    repo_data = _json(response, source["id"])
    commit_response = http.get(f"https://api.github.com/repos/{repo}/commits", headers=headers, params={"per_page": 1})
    if commit_response.status != 200:
        return CollectionResult(source["id"], "error", f"https://github.com/{repo}", commit_response.status, None, [], {"repository": repo_data}, reason="github_commit_http_error")
    commits = _json(commit_response, source["id"])
    if not isinstance(commits, list) or not commits or not commits[0].get("sha"):
        return CollectionResult(source["id"], "error", f"https://github.com/{repo}", 200, None, [], {"repository": repo_data, "commits": commits}, reason="github_commit_missing")
    sha = commits[0]["sha"]
    return CollectionResult(source["id"], "success", f"https://github.com/{repo}", 200, None, [f"github:{repo}@{sha}"], {"repository": repo_data, "latest_commit": commits[0]})


def _collect_github_search(source, http, env):
    headers = _headers(extra={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    if env.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {env['GITHUB_TOKEN']}"
    params = {
        "q": source["query"],
        "sort": source.get("sort", "updated"),
        "order": source.get("order", "desc"),
        "per_page": min(int(source.get("limit", 10)), 30),
    }
    response = http.get("https://api.github.com/search/repositories", headers=headers, params=params)
    if response.status != 200:
        return CollectionResult(source["id"], "error", "https://github.com/search", response.status, None, [], None, reason="github_search_http_error")
    payload = _json(response, source["id"])
    items = payload.get("items")
    if not isinstance(items, list):
        return CollectionResult(source["id"], "error", "https://github.com/search", 200, None, [], payload, reason="github_search_invalid_results")
    item_ids = [
        f"github-search:{row['full_name']}@{row.get('pushed_at') or row.get('updated_at') or 'unknown'}"
        for row in items if row.get("full_name")
    ]
    if not item_ids:
        return CollectionResult(source["id"], "error", "https://github.com/search", 200, None, [], payload, reason="github_search_no_matches")
    return CollectionResult(source["id"], "success", "https://github.com/search", 200, None, item_ids, payload)


def _apple_item_id(row):
    track_id = row.get("trackId")
    version = row.get("version") or "unknown"
    ratings = row.get("userRatingCount", "unknown")
    return f"apple:{track_id}@{version}:r{ratings}"


def _collect_apple(source, http):
    ids = [str(value) for value in source["ids"]]
    response = http.get("https://itunes.apple.com/lookup", headers=_headers(), params={"id": ",".join(ids), "country": source.get("country", "us")})
    if response.status != 200:
        return CollectionResult(source["id"], "error", "https://itunes.apple.com/lookup", response.status, None, [], None, reason="apple_lookup_http_error")
    payload = _json(response, source["id"])
    results = payload.get("results")
    if not isinstance(results, list):
        return CollectionResult(source["id"], "error", "https://itunes.apple.com/lookup", 200, None, [], payload, reason="apple_lookup_invalid_results")
    item_ids = [_apple_item_id(row) for row in results if row.get("trackId") is not None]
    if not item_ids:
        return CollectionResult(source["id"], "error", "https://itunes.apple.com/lookup", 200, None, [], payload, reason="apple_lookup_no_matches")
    return CollectionResult(source["id"], "success", "https://itunes.apple.com/lookup", 200, None, item_ids, payload)


def _collect_apple_search(source, http):
    params = {
        "term": source["term"],
        "country": source.get("country", "us"),
        "media": source.get("media", "software"),
        "entity": source.get("entity", "software"),
        "limit": min(int(source.get("limit", 10)), 50),
        "lang": source.get("lang", "en_us"),
    }
    response = http.get("https://itunes.apple.com/search", headers=_headers(), params=params)
    if response.status != 200:
        return CollectionResult(source["id"], "error", "https://itunes.apple.com/search", response.status, None, [], None, reason="apple_search_http_error")
    payload = _json(response, source["id"])
    results = payload.get("results")
    if not isinstance(results, list):
        return CollectionResult(source["id"], "error", "https://itunes.apple.com/search", 200, None, [], payload, reason="apple_search_invalid_results")
    item_ids = [_apple_item_id(row) for row in results if row.get("trackId") is not None]
    if not item_ids:
        return CollectionResult(source["id"], "error", "https://itunes.apple.com/search", 200, None, [], payload, reason="apple_search_no_matches")
    return CollectionResult(source["id"], "success", "https://itunes.apple.com/search", 200, None, item_ids, payload)


def _collect_meta(source, http, env):
    token = env.get("META_AD_LIBRARY_ACCESS_TOKEN")
    if not token:
        return CollectionResult(source["id"], "unavailable", "https://www.facebook.com/ads/library/", None, None, [], None, reason="meta_ad_library_access_token_not_configured")
    endpoint = source.get("endpoint")
    if not endpoint:
        return CollectionResult(source["id"], "unavailable", "https://www.facebook.com/ads/library/", None, None, [], None, reason="meta_ad_library_api_endpoint_not_declared")
    response = http.get(endpoint, headers=_headers(), params={
        "access_token": token,
        "search_terms": source["query"],
        "ad_reached_countries": json.dumps([source.get("country", "US")]),
    })
    if response.status != 200:
        return CollectionResult(source["id"], "error", "https://www.facebook.com/ads/library/", response.status, None, [], None, reason="meta_ad_library_http_error")
    payload = _json(response, source["id"])
    data = payload.get("data")
    if not isinstance(data, list):
        return CollectionResult(source["id"], "error", "https://www.facebook.com/ads/library/", 200, None, [], payload, reason="meta_ad_library_invalid_results")
    ids = [f"meta:{row['id']}" for row in data if row.get("id")]
    return CollectionResult(source["id"], "success", "https://www.facebook.com/ads/library/", 200, None, ids, payload)


def _resolved_runtime_env(env):
    if env is None:
        env = dict(os.environ)
        if not env.get("GITHUB_TOKEN"):
            try:
                token_result = subprocess.run(
                    ["gh", "auth", "token"], capture_output=True, text=True, timeout=5
                )
                if token_result.returncode == 0 and token_result.stdout.strip():
                    env["GITHUB_TOKEN"] = token_result.stdout.strip()
            except (OSError, subprocess.SubprocessError):
                pass
    return env


def collect_source(source, *, http=None, env=None, cache=None):
    http = http or URLHTTP()
    env = _resolved_runtime_env(env)
    try:
        adapter = source.get("adapter")
        if adapter == "x_articles":
            return _collect_x_articles(source, http)
        if adapter == "rss":
            return _collect_rss(source, http, cache or {})
        if adapter == "github_repo":
            return _collect_github_repo(source, http, env)
        if adapter == "github_search":
            return _collect_github_search(source, http, env)
        if adapter == "apple_lookup":
            return _collect_apple(source, http)
        if adapter == "apple_search":
            return _collect_apple_search(source, http)
        if adapter == "meta_ad_library":
            return _collect_meta(source, http, env)
        return CollectionResult(source.get("id", "unknown"), "error", source.get("url"), None, None, [], None, reason="unknown_adapter")
    except Exception as exc:
        if isinstance(exc, TimeoutError):
            reason = "transport_timeout"
        elif isinstance(exc, ET.ParseError):
            reason = "invalid_xml"
        elif isinstance(exc, ValueError):
            reason = str(exc).split(":", 1)[0]
        else:
            reason = "transport_or_parse_error"
        return CollectionResult(source.get("id", "unknown"), "error", source.get("url"), None, None, [], None, reason=reason, error_class=type(exc).__name__)


def _all_urls(value):
    urls = set()
    if isinstance(value, dict):
        for child in value.values():
            urls.update(_all_urls(child))
    elif isinstance(value, list):
        for child in value:
            urls.update(_all_urls(child))
    elif isinstance(value, str) and value.startswith("https://"):
        urls.add(value)
    return urls


def _validate_record(store_name, row):
    try:
        intel_store.VALIDATORS[store_name](row)
    except (KeyError, intel_store.StoreError) as exc:
        raise JudgmentError(str(exc)) from exc


def _validate_specific_source(store_name, row):
    source_url = row.get("source_url")
    if source_url is None:
        return
    generic = {
        "https://itunes.apple.com/search",
        "https://itunes.apple.com/lookup",
        "https://github.com/search",
        "https://www.facebook.com/ads/library/",
    }
    if source_url in generic:
        raise JudgmentError(f"source_url is a collection endpoint, not an item: {source_url}")
    if store_name == "playbook" and row.get("source_type") == "x_article":
        parsed = urllib.parse.urlparse(source_url)
        parts = [part for part in parsed.path.split("/") if part]
        if parsed.netloc not in {"x.com", "twitter.com"} or "status" not in parts:
            raise JudgmentError("x_article source_url must be an exact native status URL")
    if store_name == "ad-swipe" and row.get("platform") == "app_store":
        if urllib.parse.urlparse(source_url).netloc != "apps.apple.com":
            raise JudgmentError("app_store source_url must be an exact apps.apple.com item URL")


def accept_judgment(judgment, *, root, allowed_urls):
    """Atomically append grounded rows; identical replay is a no-op."""
    root = pathlib.Path(root)
    if not isinstance(judgment, dict) or set(judgment) != {"playbook", "creators", "ad_swipe"}:
        raise JudgmentError("judgment fields must be playbook, creators, ad_swipe")
    mapping = {"playbook": "playbook", "creators": "creators", "ad_swipe": "ad-swipe"}
    incoming = {}
    for output_key, store_name in mapping.items():
        rows = judgment[output_key]
        if not isinstance(rows, list):
            raise JudgmentError(f"{output_key} must be an array")
        limit = {"playbook": 5, "creators": 8, "ad-swipe": 8}[store_name]
        if len(rows) > limit:
            raise JudgmentError(f"{output_key} exceeds bounded item limit {limit}")
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                raise JudgmentError(f"{output_key} row must be object")
            _validate_record(store_name, row)
            _validate_specific_source(store_name, row)
            if row["id"] in seen:
                raise JudgmentError(f"duplicate incoming id {row['id']}")
            seen.add(row["id"])
            for field in ("source_url", "evidence_url"):
                url = row.get(field)
                if url is not None and url not in allowed_urls:
                    raise JudgmentError(f"{field} is not present in captured evidence: {url}")
        incoming[store_name] = rows

    lock_path = root / ".intel.lock"
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        new_rows = {}
        result = {}
        for store_name, rows in incoming.items():
            path = root / intel_store.STORES[store_name]
            existing = intel_store.read_jsonl(path)
            by_id = {row["id"]: row for row in existing}
            additions = []
            for row in rows:
                previous = by_id.get(row["id"])
                if previous is None:
                    additions.append(row)
                elif previous != row:
                    raise JudgmentError(f"conflicting replay for {row['id']}")
            new_rows[store_name] = existing + additions
            result[store_name] = len(additions)

        staged = []
        try:
            for store_name, rows in new_rows.items():
                path = root / intel_store.STORES[store_name]
                handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=root, delete=False)
                with handle:
                    for row in rows:
                        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                staged.append((pathlib.Path(handle.name), path, store_name))
            for temp_path, _, store_name in staged:
                intel_store.validate_store(temp_path, store_name)
            for temp_path, destination, _ in staged:
                os.replace(temp_path, destination)
        finally:
            for temp_path, _, _ in staged:
                temp_path.unlink(missing_ok=True)
        return result


def evidence_urls(results):
    urls = set()
    for result in results:
        if result.canonical_url:
            urls.add(result.canonical_url)
        urls.update(_all_urls(result.payload))
    return urls


def captured_urls(paths):
    urls = set()
    for path in paths:
        try:
            document = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        urls.update(_all_urls(document))
    return urls


def load_registry(path):
    path = pathlib.Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "marketing.intel-sources.v1":
        raise ValueError("unsupported_source_registry")
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("source_registry_requires_sources")
    seen = set()
    for source in sources:
        if not isinstance(source, dict) or not isinstance(source.get("id"), str):
            raise ValueError("source_id_required")
        if source["id"] in seen:
            raise ValueError(f"duplicate_source_id:{source['id']}")
        seen.add(source["id"])
        if source.get("cadence") not in {"daily", "weekly"}:
            raise ValueError(f"invalid_source_cadence:{source['id']}")
        if not isinstance(source.get("enabled"), bool):
            raise ValueError(f"source_enabled_boolean_required:{source['id']}")
        if not isinstance(source.get("product_ids"), list) or not isinstance(source.get("languages"), list):
            raise ValueError(f"source_scope_arrays_required:{source['id']}")
    return sources


def _compact_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _result_document(source, result):
    return {
        "schema_version": "marketing.source-capture.v1",
        "source": {key: value for key, value in source.items() if key not in {"access_token", "token", "authorization"}},
        "result": dataclasses.asdict(result),
    }


def _append_jsonl_locked(path, rows, lock_path):
    path = pathlib.Path(path)
    lock_path = pathlib.Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.touch(exist_ok=True)
    with lock_path.open("r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with path.open("ab") as output:
            for row in rows:
                output.write(_compact_json(row))


def _append_enrichments(path, rows, lock_path):
    existing = _item_rows(path)
    existing_ids = {row["id"] for row in existing}
    additions = []
    for row in rows:
        required = {"schema_version", "id", "tactic_id", "source_id", "item_id", "source_url", "captured_at", "evidence_path", "evidence_sha256"}
        if set(row) != required or row["schema_version"] != "marketing.source-enrichment.v1":
            raise ValueError("invalid_source_enrichment")
        if not row["source_url"].startswith("https://x.com/") or "/status/" not in row["source_url"]:
            raise ValueError("source_enrichment_requires_exact_x_status")
        if row["id"] not in existing_ids:
            additions.append(row)
            existing_ids.add(row["id"])
    if additions:
        _append_jsonl_locked(path, additions, lock_path)
    return len(additions)


def declared_enrichments(sources, results, receipts, observed_at):
    by_source = {result.source_id: result for result in results}
    receipt_by_source = {row["source_id"]: row for row in receipts}
    rows = []
    for source in sources:
        declarations = source.get("enrichments", [])
        if not declarations:
            continue
        result = by_source.get(source["id"])
        receipt = receipt_by_source.get(source["id"])
        if result is None or result.status != "success" or receipt is None:
            continue
        articles = result.payload.get("articles", []) if isinstance(result.payload, dict) else []
        article_by_id = {str(article.get("id")): article for article in articles if article.get("id")}
        for declaration in declarations:
            status_id = str(declaration["status_id"])
            article = article_by_id.get(status_id)
            if article is None:
                continue
            url = article.get("url")
            if not isinstance(url, str):
                continue
            tactic_slug = declaration["tactic_id"].replace(".", "-")
            rows.append({
                "schema_version": "marketing.source-enrichment.v1",
                "id": f"enrichment.{tactic_slug}.x-{status_id}.v1",
                "tactic_id": declaration["tactic_id"],
                "source_id": source["id"],
                "item_id": f"x:{status_id}",
                "source_url": url,
                "captured_at": observed_at,
                "evidence_path": receipt["evidence_path"],
                "evidence_sha256": receipt["sha256"],
            })
    return rows


def _seen_item_ids(path):
    if not pathlib.Path(path).exists():
        return set()
    return {row["item_id"] for row in intel_store.read_jsonl(path) if row.get("item_id")}


def _item_rows(path):
    if not pathlib.Path(path).exists():
        return []
    return intel_store.read_jsonl(path)


def run_pull(
    *, registry_path, intel_root, evidence_root, http=None, env=None, judge=None,
    run_id=None, observed_at=None,
):
    """Run one bounded collection pass and optionally judge only never-seen items."""
    intel_root = pathlib.Path(intel_root)
    evidence_root = pathlib.Path(evidence_root)
    intel_root.mkdir(parents=True, exist_ok=True)
    evidence_root.mkdir(parents=True, exist_ok=True)
    env = _resolved_runtime_env(env)
    run_id = run_id or uuid.uuid4().hex
    if not isinstance(run_id, str) or len(run_id) != 32 or set(run_id) == {"0"}:
        raise ValueError("run_id_must_be_nonzero_32_hex")
    try:
        int(run_id, 16)
    except ValueError as exc:
        raise ValueError("run_id_must_be_nonzero_32_hex") from exc
    observed_at = observed_at or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    run_dir = evidence_root / run_id
    run_dir.mkdir(parents=False, exist_ok=False)
    sources = load_registry(registry_path)
    cache_path = intel_root / "source-cache.json"
    cache_state = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    results = []
    source_receipts = []
    for source in sources:
        if not source["enabled"] or source["cadence"] != "daily":
            continue
        result = collect_source(source, http=http, env=env, cache=cache_state.get(source["id"], {}))
        results.append(result)
        if result.cache:
            cache_state[source["id"]] = result.cache
        document = _result_document(source, result)
        payload = _compact_json(document)
        capture_path = run_dir / f"{source['id']}.json"
        capture_path.write_bytes(payload)
        source_receipts.append({
            "source_id": source["id"],
            "adapter": source["adapter"],
            "status": result.status,
            "reason": result.reason,
            "error_class": result.error_class,
            "canonical_url": result.canonical_url,
            "http_status": result.http_status,
            "api_status": result.api_status,
            "item_ids": result.item_ids,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "evidence_path": str(capture_path),
        })
    cache_path.write_text(json.dumps(cache_state, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    enrichment_rows = declared_enrichments(sources, results, source_receipts, observed_at)
    enrichments_added = _append_enrichments(
        intel_root / "source-enrichments.jsonl", enrichment_rows,
        intel_root / ".source-enrichments.lock",
    )

    item_ledger = intel_root / "source-items.jsonl"
    previous_ids = _seen_item_ids(item_ledger)
    new_items = []
    source_by_id = {source["id"]: source for source in sources}
    for receipt in source_receipts:
        for item_id in receipt["item_ids"]:
            if item_id not in previous_ids:
                new_items.append({
                    "schema_version": "marketing.source-item.v1",
                    "item_id": item_id,
                    "source_id": receipt["source_id"],
                    "first_seen_at": observed_at,
                    "first_seen_run_id": run_id,
                    "evidence_path": receipt["evidence_path"],
                    "product_ids": source_by_id[receipt["source_id"]]["product_ids"],
                    "languages": source_by_id[receipt["source_id"]]["languages"],
                })
                previous_ids.add(item_id)
    if new_items:
        _append_jsonl_locked(item_ledger, new_items, intel_root / ".source-items.lock")

    accepted = {"playbook": 0, "creators": 0, "ad-swipe": 0}
    judged_ledger = intel_root / "judged-items.jsonl"
    judged_ids = _seen_item_ids(judged_ledger)
    pending_items = [row for row in _item_rows(item_ledger) if row["item_id"] not in judged_ids]
    judge_receipt = {"status": "skipped", "reason": "no_pending_source_items" if not pending_items else "judge_disabled"}
    if pending_items and judge is not None:
        manifest = {
            "schema_version": "marketing.intel-judge-input.v1",
            "run_id": run_id,
            "observed_at": observed_at,
            "judge_evidence_dir": str(run_dir / "judge"),
            "new_items": pending_items,
            "evidence_paths": sorted({row["evidence_path"] for row in pending_items}),
            "existing_ids": {
                name: [row["id"] for row in intel_store.read_jsonl(intel_root / filename)]
                for name, filename in intel_store.STORES.items()
            },
            "existing_playbook": [
                {key: row.get(key) for key in ("id", "claim", "mechanism", "status", "source_url")}
                for row in intel_store.read_jsonl(intel_root / intel_store.STORES["playbook"])
            ],
        }
        try:
            judgment = judge(manifest)
            (run_dir / "judgment.json").write_bytes(_compact_json(judgment))
            allowed = evidence_urls(results) | captured_urls(row["evidence_path"] for row in pending_items)
            accepted = accept_judgment(judgment, root=intel_root, allowed_urls=allowed)
            judge_receipt = {"status": "success", "reason": None, "accepted": accepted}
            judged_rows = [{
                "schema_version": "marketing.judged-item.v1",
                "item_id": row["item_id"],
                "source_id": row["source_id"],
                "judged_at": observed_at,
                "judge_run_id": run_id,
            } for row in pending_items]
            _append_jsonl_locked(judged_ledger, judged_rows, intel_root / ".judged-items.lock")
        except Exception as exc:
            judge_receipt = {"status": "error", "reason": type(exc).__name__, "detail": str(exc)[:500]}

    statuses = {row["status"] for row in source_receipts}
    overall = "success" if statuses and statuses <= {"success", "unchanged"} and judge_receipt["status"] != "error" else "partial"
    receipt = {
        "schema_version": "marketing.intel-pull.v1",
        "run_id": run_id,
        "observed_at": observed_at,
        "status": overall,
        "sources": source_receipts,
        "new_source_items": len(new_items),
        "enrichments_added": enrichments_added,
        "pending_judgment": len(pending_items) if judge_receipt["status"] != "success" else 0,
        "judge": judge_receipt,
        "accepted": accepted,
    }
    (run_dir / "run.json").write_bytes(_compact_json(receipt))
    _append_jsonl_locked(intel_root / "pull-runs.jsonl", [receipt], intel_root / ".pull-runs.lock")
    return receipt


def agent_judge(manifest):
    """Use the shared provider-neutral runner for bounded creative judgment."""
    run_id = manifest["run_id"]
    evidence_dir = pathlib.Path(manifest["judge_evidence_dir"])
    schema = HERE / "schemas" / "intel-judgment.schema.json"
    prompt = f"""You are the read-only Marketing Intel judge for one bounded pull.

Read each absolute JSON evidence file in this manifest:
{json.dumps(manifest, ensure_ascii=False, indent=2)}

Return only the JSON object required by the supplied schema.

Rules:
- Do not modify any file and do not perform external actions.
- Propose only novel, testable mechanisms, observed creators, or observed ad/storefront treatments directly supported by those evidence files.
- Compare concepts against existing_playbook, not only IDs. Omit a proposal when its claim or mechanism substantially duplicates an existing tactic.
- Every non-null source_url and evidence_url must be an exact HTTPS string present in the evidence. Never invent, normalize, shorten, or substitute a URL.
- source_url must identify the exact evidence item, never a collection endpoint or profile: use the native /status/<id> URL for X Articles and the exact apps.apple.com item URL for an App Store treatment.
- Copy source_url and evidence_url byte-for-byte from a captured JSON string. If you cannot copy the exact URL, omit that record; never reconstruct percent-encoding from memory.
- Use captured_at={manifest['observed_at']}. New hypotheses use status=new, our_result=null, and result_evidence=null. Never claim won, done, revenue lift, impressions, or conversion from source popularity.
- Apple Search/Lookup provides storefront metadata, ratings, and rating counts; it does not provide impressions, installs, or revenue. Keep impressions null with an exact reason.
- A single article does not prove a creator green/red. Preserve observed numeric metrics as individually labeled metric objects and use verdict=unknown unless the evidence contains the declared multi-post threshold.
- Extract reusable mechanisms and write an original replication plan. Do not copy protected wording, footage, character identity, screenshots, or unverified claims.
- If the captured items contain nothing novel beyond existing_ids, return empty arrays. Quality beats count.
"""
    command = [
        str(ENGINE_ROOT / "run_agent.sh"),
        "--task-class", "marketing-agent",
        "--schema", str(schema),
        "--evidence-dir", str(evidence_dir),
        "--task-label", f"marketing-intel-{run_id}",
        "--loop", "marketing-intel",
        "--workdir", str(REPO_ROOT),
        "--print-result",
    ]
    completed = subprocess.run(command, input=prompt, text=True, capture_output=True, timeout=920)
    if completed.returncode != 0:
        raise JudgmentError("agent_judge_failed")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise JudgmentError("agent_judge_non_json") from exc


def run_pending_judge(*, intel_root, evidence_root, judge=None, run_id=None, observed_at=None):
    """Retry only unjudged captured items without re-fetching external sources."""
    intel_root = pathlib.Path(intel_root)
    evidence_root = pathlib.Path(evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True)
    run_id = run_id or uuid.uuid4().hex
    observed_at = observed_at or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    run_dir = evidence_root / run_id
    run_dir.mkdir(parents=False, exist_ok=False)
    item_ledger = intel_root / "source-items.jsonl"
    judged_ledger = intel_root / "judged-items.jsonl"
    judged_ids = _seen_item_ids(judged_ledger)
    pending_items = [row for row in _item_rows(item_ledger) if row["item_id"] not in judged_ids]
    accepted = {"playbook": 0, "creators": 0, "ad-swipe": 0}
    status = "skipped"
    reason = "no_pending_source_items"
    detail = None
    if pending_items:
        manifest = {
            "schema_version": "marketing.intel-judge-input.v1",
            "run_id": run_id,
            "observed_at": observed_at,
            "judge_evidence_dir": str(run_dir / "judge"),
            "new_items": pending_items,
            "evidence_paths": sorted({row["evidence_path"] for row in pending_items}),
            "existing_ids": {
                name: [row["id"] for row in intel_store.read_jsonl(intel_root / filename)]
                for name, filename in intel_store.STORES.items()
            },
            "existing_playbook": [
                {key: row.get(key) for key in ("id", "claim", "mechanism", "status", "source_url")}
                for row in intel_store.read_jsonl(intel_root / intel_store.STORES["playbook"])
            ],
        }
        try:
            judgment = (judge or agent_judge)(manifest)
            (run_dir / "judgment.json").write_bytes(_compact_json(judgment))
            allowed = captured_urls(row["evidence_path"] for row in pending_items)
            accepted = accept_judgment(judgment, root=intel_root, allowed_urls=allowed)
            judged_rows = [{
                "schema_version": "marketing.judged-item.v1",
                "item_id": row["item_id"], "source_id": row["source_id"],
                "judged_at": observed_at, "judge_run_id": run_id,
            } for row in pending_items]
            _append_jsonl_locked(judged_ledger, judged_rows, intel_root / ".judged-items.lock")
            status, reason = "success", None
        except Exception as exc:
            status, reason, detail = "error", type(exc).__name__, str(exc)[:500]
    result = {
        "schema_version": "marketing.intel-judge-retry.v1",
        "run_id": run_id,
        "observed_at": observed_at,
        "status": status,
        "reason": reason,
        "detail": detail,
        "pending_before": len(pending_items),
        "pending_after": 0 if status == "success" else len(pending_items),
        "accepted": accepted,
    }
    (run_dir / "judge-retry.json").write_bytes(_compact_json(result))
    return result
