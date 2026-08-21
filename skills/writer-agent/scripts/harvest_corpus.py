#!/usr/bin/env python3
"""Harvest real, high-performing writing with its real engagement numbers.

Why this exists: spec 47 section 19.5 needs a corpus of writing we did NOT
produce, each row carrying the engagement it actually got, so a later gate can
blind-compare our drafts against real writing instead of against our own
judge's opinion of itself (section 19.1 -- a closed loop that only rewards
"pleases my own judge" degrades, arxiv 2310.01798). This script is the
harvester half; the compare/gate half is a separate TODO (19-3/19-4).

Sources (HTTP only -- the daily-driver browser is reserved for publishing,
section 20 CLAUDE.md, and must not be touched by this script):
  * Hacker News, `hn.algolia.com/api/v1/search` (top slice, popularity
    ranked) and `.../search_by_date` (baseline slice, recency ranked) --
    points/comments are ground truth, no auth. Scoped to a fixed AI/dev
    niche query list and to the last 180 days (round-2 fix: an unscoped,
    undated search surfaces news-event virality like "Stephen Hawking has
    died", which teaches nothing about writing craft and poisons the top of
    the distribution).
  * dev.to, `dev.to/api/articles` -- public_reactions_count and
    comments_count, no auth.
  * Zenn, `zenn.dev/api/articles` -- liked_count, no auth. This is the ja
    revenue-facing source (note publishing is ja); without it the corpus was
    100% English and the ja title slice had nothing to train on.
  * Hatena Bookmark, `b.hatena.ne.jp/hotentry/{it,all}.rss` (top slice,
    popularity ranked -- these are the "人気エントリー" feeds) and
    `b.hatena.ne.jp/entrylist/{it,all}.rss` (baseline slice, "新着エントリー",
    recency ranked, genuinely lower/mixed bookmark counts) -- 4 requests/run.
    XML (RDF/RSS 1.0), not JSON; `hatena:bookmarkcount` per `<item>` is
    ground truth, no auth. No native numeric id is exposed in the feed, so
    the entry's own URL (via the item's `rdf:about` attribute) is the
    native id -- it is unique and stable, which is all dedup needs.
  * Qiita, `qiita.com/api/v2/items` -- `likes_count` is ground truth, no
    auth (60 req/hr per IP, well inside the 2 req/run budget here). Top
    slice: `query=stocks:>=15 created:>{30d ago}` (a real popularity floor,
    not just a recency window -- Qiita's default listing is date-descending
    with no relevance/popularity weighting at all, so an unfiltered request
    already IS a fair recency-ranked baseline with no separate query needed
    for that half). Baseline slice: the same unfiltered `/api/v2/items`
    listing, no stocks floor.

  round-4 (T15) considered and REJECTED: note.com. Systematically probed
  (2026-07-27) beyond the coordinator's own single 404 finding:
  `/api/v3/searchnote` and `/api/v2/searchnote` both 404;
  `/api/v3/searches` 403 (WAF-blocked); `/api/v1/notes/trend` 405 (allows
  only OPTIONS/PATCH -- an admin-only route, not a public listing);
  `/api/v2/notes/trend`, `/api/v2/category_pv_notes`,
  `/api/v2/hashtags/<tag>/notes` all 404. The `/hashtag/<tag>` HTML page
  returns 200 but its embedded Nuxt state (`window.__NUXT__`) has an empty
  notes array -- the real list is lazy-loaded through some other,
  undiscovered request. `/hashtag/<tag>/rss` DOES return 200 with real
  content, but its items carry no engagement metric at all (no like
  count in the feed) and are recency-, not popularity-, ordered, so even
  reachable it fails "the metric is ground truth" -- getting a real like
  count would mean one HTTP request per article to scrape it off the note
  page, a fundamentally heavier shape than every other source here, and
  `robots.txt` disallows `/api/*` for `User-agent: *` outright, which is
  where the like count actually lives. Per the task's own instruction
  ("if none answers without auth, say so and skip note rather than
  inventing a path"): note.com is SKIPPED. Two sources were added, not
  three -- a smaller honest corpus over a padded one.

Round-3 fix: hn's baseline slice used to be one /search query with the points
floor dropped to 1. That collapsed into the top slice, because /search ranks
by relevance (which weights points) even at floor=1, so its one fetched page
was still the popular set -- hn's "loser" was really just its least-popular
winner (50 points), not a real loser, and a contrastive miner trained on that
pair would learn noise. Fixed by moving the baseline slice to
`search_by_date` (recency-ranked, not popularity-ranked) with no points
floor at all, across the same 8 niche queries and the same date window --
that is what actually surfaces the unpopular tail (0-1 point stories). hn is
now 16 requests/run (8 top + 8 baseline), up from 9.

Request budget, this run: hn 16 + devto 2 + zenn 2 + hatena 4 + qiita 2 =
26 HTTP requests total, all unauthenticated, all read-only GETs.

Round-2 design choices made because the coordinator's spec left them open
(simplest option, noted here rather than asked about):
  * When the same native id would appear in both a source's top and baseline
    slice fetch, the row is tagged "top" -- the more informative label wins.
    Implemented by inserting top-slice rows into the dedupe dict before
    baseline-slice rows and skipping ids already present.
  * `text` is always "" -- fetching full article bodies would need one HTTP
    request per story, blowing the request budget. Only the title (and its
    metric) is harvested; that is also all the title-candidate slice
    (title_candidates.py) needs.
  * `topic_tags` is always [] -- left for a future pass (see round-1 notes).
  * `followers` is always 0 -- none of the three APIs expose author follower
    counts without an extra per-item request. `norm_score` (percentile
    within source+lang) is the cross-comparable signal instead.
  * HN stories with no external `url` (Ask HN / Show HN) fall back to the HN
    item page URL, so a row is never dropped just for being self-text.
  * Non-English, non-CJK Latin-script titles get `lang: "other"` via a small
    substring marker list (pt/es/fr). These markers are substrings, not
    whole-word matches, so a small false-positive rate against English words
    that happen to contain them (e.g. "comparable", "pour" the verb) is a
    known, accepted limitation of "cheap marker set", not a bug to design
    around here.

Row schema (one JSON object per line, per spec 47 section 19.5, extended with
`slice` for contrastive top-vs-baseline mining and `metric_primary` -- round
3 -- so a later gate can read "how did it actually do" without re-deriving
it from `metric` + `source`; `norm_score` alone only answers "where in its
group", which cannot distinguish a real loser from a merely-less-popular
winner; `bookmarks` added round-4/T15 for Hatena's bookmark count -- Qiita's
`likes_count` reuses the existing `likes` field, since it is the same
concept zenn's `liked_count` already occupies there):
  {"id": "<source>:<native id>", "source": "hn|devto|zenn|hatena|qiita", "format": "article",
   "lang": "ja|en|other", "title": "...", "text": "", "url": "...",
   "metric": {"points": 0, "comments": 0, "reactions": 0, "likes": 0, "bookmarks": 0},
   "metric_primary": 0.0, "followers": 0, "norm_score": 0.0, "topic_tags": [],
   "slice": "top|baseline", "harvested_at": "..."}

Output: skills/writer-agent/state/writing-corpus/<UTC date>-<source>.jsonl,
append-only, deduped on `id` against whatever is already in that day's file
so re-running the same day never duplicates rows.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

USER_AGENT = (
    "profitable-claude-writing-corpus-harvester/1.0 "
    "(+https://github.com/anicca-ai/profitable-claude; research corpus, low volume)"
)
REQUEST_TIMEOUT_S = 25
DEFAULT_MIN_POINTS = 50
DEFAULT_TOP_DAYS = 7

# HN scoping (round-2 defect 2): niche queries instead of the global
# firehose, and a 180-day recency window so old news-event stories cannot
# outrank writing craft in the top slice. Round 3: the same 8 queries are
# also used for the baseline slice (via search_by_date instead of search),
# so there is no separate "baseline query" constant any more.
HN_NICHE_QUERIES = (
    "AI agent", "LLM", "coding agent", "prompt engineering",
    "evals", "developer tools", "Claude", "open source AI",
)
HN_DATE_WINDOW_DAYS = 180

# Hatena Bookmark: fixed category feeds, no query/auth concept at all --
# "it" and "all" (総合) are the two categories the coordinator named.
HATENA_CATEGORIES = ("it", "all")
_HATENA_NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rss": "http://purl.org/rss/1.0/",
    "hatena": "http://www.hatena.ne.jp/info/xmlns#",
}
_RDF_ABOUT_ATTR = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"

# Qiita: a real popularity floor (stocks, not just a recency window --
# Qiita's default listing has no relevance/popularity weighting at all, so
# it is already a fair baseline on its own) over a 30-day window.
DEFAULT_QIITA_MIN_STOCKS = 15
DEFAULT_QIITA_WINDOW_DAYS = 30

REQUIRED_KEYS = {
    "id", "source", "format", "lang", "title", "text", "url",
    "metric", "metric_primary", "followers", "norm_score", "topic_tags",
    "slice", "harvested_at",
}
REQUIRED_METRIC_KEYS = {"points", "comments", "reactions", "likes", "bookmarks"}
VALID_SOURCES = {"hn", "devto", "zenn", "hatena", "qiita"}
VALID_LANGS = {"ja", "en", "other"}
VALID_SLICES = {"top", "baseline"}

# Hiragana, katakana, and CJK unified ideographs. "Nothing smarter" per spec:
# no library, no per-word segmentation, just "does this title contain a
# Japanese/CJK character at all".
_CJK_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿]")

# Cheap non-English Latin-script markers (Portuguese/Spanish/French), per the
# coordinator's "at minimum" list. Substring match on a casefolded title.
_NON_EN_LATIN_MARKERS = (
    "ção", "não", "você", "cómo", "según", "más", "très", "pour", "avec", "sobre", "para",
)

FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(hn|devto|zenn|hatena|qiita)\.jsonl$")


class HarvestContractError(ValueError):
    """A row about to be written violates the writing-corpus schema contract."""


# ---------------------------------------------------------------------------
# Small pure functions -- these are what the contract test drives directly,
# with no network involved.
# ---------------------------------------------------------------------------

def detect_lang(title: str) -> str:
    """"ja" if the title has any hiragana/katakana/CJK; "other" if it is
    Latin-script but matches a non-English marker; else "en"."""
    if _CJK_RE.search(title or ""):
        return "ja"
    lowered = (title or "").casefold()
    if any(marker in lowered for marker in _NON_EN_LATIN_MARKERS):
        return "other"
    return "en"


def _primary_metric_value(source: str, metric: dict) -> float:
    """The single raw number norm_score is a percentile of: points for hn,
    reactions for devto, likes for zenn, likes for qiita (qiita's
    `likes_count` is the same concept zenn's `liked_count` already
    occupies in this field, so it is reused rather than given a second
    field), bookmarks for hatena. Shared by build_row (which stamps it onto
    the row as `metric_primary`) and primary_metric (which reads it back
    off an already-built row for ranking)."""
    if source == "hn":
        return float(metric.get("points", 0) or 0)
    if source == "devto":
        return float(metric.get("reactions", 0) or 0)
    if source in ("zenn", "qiita"):
        return float(metric.get("likes", 0) or 0)
    if source == "hatena":
        return float(metric.get("bookmarks", 0) or 0)
    return 0.0


def build_row(
    *,
    source: str,
    native_id,
    lang: str,
    title: str | None,
    text: str,
    url: str | None,
    metric: dict,
    slice_name: str,
    followers: int = 0,
    topic_tags: list | None = None,
    harvested_at: str,
) -> dict | None:
    """Build one corpus row, or return None if title/url is missing.

    A row without a title or a url is useless to every downstream consumer
    (the title slice trains on `title`, everything else needs `url` to be
    traceable back to the source), so it is dropped here rather than written.
    """
    title = (title or "").strip()
    url = (url or "").strip()
    if not title or not url:
        return None
    metric_out = {
        "points": int(metric.get("points", 0) or 0),
        "comments": int(metric.get("comments", 0) or 0),
        "reactions": int(metric.get("reactions", 0) or 0),
        "likes": int(metric.get("likes", 0) or 0),
        "bookmarks": int(metric.get("bookmarks", 0) or 0),
    }
    return {
        "id": f"{source}:{native_id}",
        "source": source,
        "format": "article",
        "lang": lang,
        "title": title,
        "text": text or "",
        "url": url,
        "metric": metric_out,
        "metric_primary": _primary_metric_value(source, metric_out),
        "followers": int(followers or 0),
        "norm_score": 0.0,
        "topic_tags": list(topic_tags or []),
        "slice": slice_name,
        "harvested_at": harvested_at,
    }


def primary_metric(row: dict) -> float:
    """The metric percentile ranking is computed on: points for hn, reactions
    for devto, likes for zenn. Same number as the row's `metric_primary`
    field; this reads it fresh from `metric` so it stays correct even for
    rows built before `metric_primary` existed."""
    return _primary_metric_value(row.get("source"), row.get("metric", {}))


def apply_norm_scores(rows: list[dict]) -> list[dict]:
    """Percentile rank in [0,1] of each row's primary metric within its own
    (source, lang) group -- never across groups, because raw counts are not
    comparable across sources (spec 47 section 19.5).

    Rank is dense (ties share a rank) and scaled so the group's highest
    metric always lands exactly on 1.0 and the lowest on 0.0. A singleton
    group gets 1.0 (nothing to rank it against).

    Returns a new list; does not mutate the input rows.
    """
    groups: dict[tuple, list[int]] = {}
    for i, row in enumerate(rows):
        groups.setdefault((row["source"], row["lang"]), []).append(i)

    out = [dict(row) for row in rows]
    for idxs in groups.values():
        if len(idxs) == 1:
            out[idxs[0]]["norm_score"] = 1.0
            continue
        sorted_idxs = sorted(idxs, key=lambda i: primary_metric(rows[i]))
        rank_of: dict[int, int] = {}
        current_rank = 0
        prev_val = None
        for pos, i in enumerate(sorted_idxs):
            val = primary_metric(rows[i])
            if prev_val is None or val != prev_val:
                current_rank = pos
            rank_of[i] = current_rank
            prev_val = val
        max_rank = max(rank_of.values())
        for i in idxs:
            out[i]["norm_score"] = (rank_of[i] / max_rank) if max_rank > 0 else 1.0
    return out


def validate_row_schema(row: dict) -> None:
    """Raise HarvestContractError if a row about to be written breaks the schema."""
    missing = REQUIRED_KEYS - row.keys()
    if missing:
        raise HarvestContractError(f"row {row.get('id')!r} missing keys: {sorted(missing)}")
    if row["source"] not in VALID_SOURCES:
        raise HarvestContractError(f"row {row['id']!r} source must be hn|devto|zenn, got {row['source']!r}")
    if row["lang"] not in VALID_LANGS:
        raise HarvestContractError(f"row {row['id']!r} lang must be ja|en|other, got {row['lang']!r}")
    if row["slice"] not in VALID_SLICES:
        raise HarvestContractError(f"row {row['id']!r} slice must be top|baseline, got {row['slice']!r}")
    if row["format"] != "article":
        raise HarvestContractError(f"row {row['id']!r} format must be 'article', got {row['format']!r}")
    if not (0.0 <= row["norm_score"] <= 1.0):
        raise HarvestContractError(f"row {row['id']!r} norm_score out of [0,1]: {row['norm_score']}")
    if not row["title"] or not row["url"]:
        raise HarvestContractError(f"row {row['id']!r} has empty title or url")
    missing_metric = REQUIRED_METRIC_KEYS - row.get("metric", {}).keys()
    if missing_metric:
        raise HarvestContractError(f"row {row['id']!r} metric missing keys: {sorted(missing_metric)}")
    expected_primary = _primary_metric_value(row["source"], row.get("metric", {}))
    if row["metric_primary"] != expected_primary:
        raise HarvestContractError(
            f"row {row['id']!r} metric_primary {row['metric_primary']!r} does not match "
            f"metric ({expected_primary!r}) -- norm_score would be computed on stale data"
        )


def load_existing_ids(path: Path) -> set:
    """The ids already on disk for this day's file -- the idempotency key."""
    if not path.exists():
        return set()
    ids = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ids.add(json.loads(line).get("id"))
        except json.JSONDecodeError:
            continue
    return ids


def append_rows(path: Path, rows: list[dict]) -> tuple[int, int]:
    """Append rows whose id is not already in the file. Returns (written, duplicate)."""
    for row in rows:
        validate_row_schema(row)
    existing = load_existing_ids(path)
    written = 0
    duplicate = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            rid = row["id"]
            if rid in existing:
                duplicate += 1
                continue
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            existing.add(rid)
            written += 1
    return written, duplicate


def collect_stats(out_dir: Path) -> dict:
    """Counts per source/lang and the date range present, from filenames + rows on disk."""
    by_source: dict[str, dict[str, int]] = {}
    dates: list[str] = []
    total = 0
    if out_dir.exists():
        for path in sorted(out_dir.glob("*.jsonl")):
            match = FILENAME_RE.match(path.name)
            if not match:
                continue
            date_str, source = match.group(1), match.group(2)
            dates.append(date_str)
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                lang = row.get("lang", "?")
                by_source.setdefault(source, {}).setdefault(lang, 0)
                by_source[source][lang] += 1
                total += 1
    return {
        "out_dir": str(out_dir),
        "total_rows": total,
        "by_source": by_source,
        "date_range": {
            "min": min(dates) if dates else None,
            "max": max(dates) if dates else None,
        },
    }


def top_titles_by_group(out_dir: Path, n: int = 3) -> dict:
    """Diagnostic (not part of the CLI contract): the n highest norm_score
    rows per (source, lang), read straight off disk -- for eyeballing the top
    of the distribution after a harvest."""
    groups: dict[tuple, list[dict]] = {}
    if out_dir.exists():
        for path in sorted(out_dir.glob("*.jsonl")):
            if not FILENAME_RE.match(path.name):
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = (row.get("source"), row.get("lang"))
                groups.setdefault(key, []).append(row)
    out = {}
    for key, rows in groups.items():
        rows_sorted = sorted(rows, key=lambda r: r.get("norm_score", 0.0), reverse=True)
        out["/".join(key)] = [
            {
                "title": r["title"],
                "norm_score": r["norm_score"],
                "metric_primary": r.get("metric_primary"),
                "metric": r["metric"],
                "slice": r["slice"],
            }
            for r in rows_sorted[:n]
        ]
    return out


def norm_score_extremes_by_group(out_dir: Path) -> dict:
    """Diagnostic (not part of the CLI contract): per (source, lang), the
    metric_primary of the lowest-norm_score and highest-norm_score row, read
    straight off disk. This is what actually shows whether a slice contains
    real losers (metric_primary near 0) or only less-popular winners --
    norm_score alone cannot distinguish the two."""
    groups: dict[tuple, list[dict]] = {}
    if out_dir.exists():
        for path in sorted(out_dir.glob("*.jsonl")):
            if not FILENAME_RE.match(path.name):
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = (row.get("source"), row.get("lang"))
                groups.setdefault(key, []).append(row)
    out = {}
    for key, rows in groups.items():
        lo = min(rows, key=lambda r: r.get("norm_score", 0.0))
        hi = max(rows, key=lambda r: r.get("norm_score", 0.0))
        out["/".join(key)] = {
            "lowest": {"title": lo["title"], "norm_score": lo["norm_score"],
                       "metric_primary": lo.get("metric_primary"), "slice": lo["slice"]},
            "highest": {"title": hi["title"], "norm_score": hi["norm_score"],
                        "metric_primary": hi.get("metric_primary"), "slice": hi["slice"]},
        }
    return out


# ---------------------------------------------------------------------------
# Network (impure) -- everything above this line is what the contract test
# drives without a socket.
# ---------------------------------------------------------------------------

def _http_get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
        return resp.read().decode("utf-8")


def _parse_hatena_rss_items(xml_text: str) -> list[dict]:
    """Hatena Bookmark's category feeds are RDF/RSS 1.0 XML, not JSON --
    every other source here is JSON, so this is the one XML parser in the
    file. stdlib ElementTree only, no lxml/feedparser dependency. Returns
    [{"url", "title", "bookmarks"}, ...]; a malformed feed (unparseable
    XML) yields an empty list rather than raising, since one source's
    fetch failure must not crash the whole harvest (mirrors fetch()'s own
    per-source try/except one level up)."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    out = []
    for item in root.findall("rss:item", _HATENA_NS):
        url = item.get(_RDF_ABOUT_ATTR)
        title_el = item.find("rss:title", _HATENA_NS)
        count_el = item.find("hatena:bookmarkcount", _HATENA_NS)
        title = title_el.text if title_el is not None else None
        count_text = count_el.text if count_el is not None else None
        count = int(count_text) if count_text and count_text.isdigit() else 0
        if url:
            out.append({"url": url, "title": title, "bookmarks": count})
    return out


def fetch_hn(min_points: int, harvested_at: str) -> list[dict]:
    """16 requests: one per niche query x 2 endpoints. Top slice = `/search`
    (popularity/relevance ranked) with the points floor, one request per
    query (8). Baseline slice = `/search_by_date` (recency ranked, NOT
    popularity ranked) with no points floor at all, same 8 queries (8 more).

    Round-3 fix: the baseline used to be one `/search` query with the floor
    dropped to 1, but `/search` ranks by relevance even at floor=1, so that
    page was still dominated by popular stories -- hn's "loser" was really
    just its least-popular winner, not a real loser. `/search_by_date`
    ignores popularity entirely, so it actually returns the stories nobody
    upvoted (0-1 points), which is what a baseline/loser slice needs to be.

    Every request (both endpoints) is date-scoped to the last
    HN_DATE_WINDOW_DAYS days so an old news-event story cannot sit at the
    top of the distribution."""
    rows: dict[str, dict] = {}
    since_i = int(datetime.now(timezone.utc).timestamp()) - HN_DATE_WINDOW_DAYS * 86400

    def _run(endpoint: str, query: str, points_floor: int | None, slice_name: str) -> None:
        numeric_filters = f"created_at_i>{since_i}"
        if points_floor is not None:
            numeric_filters = f"points>={points_floor},{numeric_filters}"
        params = {
            "tags": "story",
            "query": query,
            "numericFilters": numeric_filters,
            "hitsPerPage": 100,
        }
        url = f"https://hn.algolia.com/api/v1/{endpoint}?{urllib.parse.urlencode(params)}"
        data = _http_get_json(url)
        for hit in data.get("hits", []):
            native_id = hit.get("objectID")
            title = hit.get("title")
            fallback_url = f"https://news.ycombinator.com/item?id={native_id}" if native_id else None
            row = build_row(
                source="hn",
                native_id=native_id,
                lang=detect_lang(title or ""),
                title=title,
                text="",
                url=hit.get("url") or fallback_url,
                metric={"points": hit.get("points", 0), "comments": hit.get("num_comments", 0), "reactions": 0, "likes": 0},
                slice_name=slice_name,
                followers=0,
                topic_tags=[],
                harvested_at=harvested_at,
            )
            if row and row["id"] not in rows:
                rows[row["id"]] = row

    for query in HN_NICHE_QUERIES:
        _run("search", query, min_points, "top")
    for query in HN_NICHE_QUERIES:
        _run("search_by_date", query, None, "baseline")
    return list(rows.values())


def fetch_devto(top_days: int, harvested_at: str) -> list[dict]:
    """2 requests: the top-N-days listing (top slice) + the default
    unfiltered listing (baseline slice, includes low/zero-reaction rows)."""
    rows: dict[str, dict] = {}

    def _run(url: str, slice_name: str) -> None:
        data = _http_get_json(url)
        for item in data:
            native_id = item.get("id")
            title = item.get("title")
            row = build_row(
                source="devto",
                native_id=native_id,
                lang=detect_lang(title or ""),
                title=title,
                text="",
                url=item.get("url"),
                metric={
                    "points": 0,
                    "comments": item.get("comments_count", 0),
                    "reactions": item.get("public_reactions_count", 0),
                    "likes": 0,
                },
                slice_name=slice_name,
                followers=0,
                topic_tags=[],
                harvested_at=harvested_at,
            )
            if row and row["id"] not in rows:
                rows[row["id"]] = row

    top_url = f"https://dev.to/api/articles?{urllib.parse.urlencode({'top': top_days, 'per_page': 100})}"
    _run(top_url, "top")
    baseline_url = f"https://dev.to/api/articles?{urllib.parse.urlencode({'per_page': 100})}"
    _run(baseline_url, "baseline")
    return list(rows.values())


def fetch_zenn(harvested_at: str) -> list[dict]:
    """2 requests: order=liked_count (top slice) + order=latest (baseline slice)."""
    rows: dict[str, dict] = {}

    def _run(order: str, slice_name: str) -> None:
        url = f"https://zenn.dev/api/articles?{urllib.parse.urlencode({'order': order})}"
        data = _http_get_json(url)
        for item in data.get("articles", []):
            title = item.get("title")
            slug = item.get("slug")
            path = item.get("path")
            if path:
                article_url = f"https://zenn.dev{path}"
            elif slug:
                article_url = f"https://zenn.dev/articles/{slug}"
            else:
                article_url = None
            native_id = slug or item.get("id")
            row = build_row(
                source="zenn",
                native_id=native_id,
                lang=detect_lang(title or ""),
                title=title,
                text="",
                url=article_url,
                metric={"points": 0, "comments": 0, "reactions": 0, "likes": item.get("liked_count", 0)},
                slice_name=slice_name,
                followers=0,
                topic_tags=[],
                harvested_at=harvested_at,
            )
            if row and row["id"] not in rows:
                rows[row["id"]] = row

    _run("liked_count", "top")
    _run("latest", "baseline")
    return list(rows.values())


def fetch_hatena(harvested_at: str) -> list[dict]:
    """4 requests: hotentry/{it,all}.rss (top slice, popularity-ranked
    "人気エントリー") + entrylist/{it,all}.rss (baseline slice,
    recency-ranked "新着エントリー" -- genuinely lower and more mixed
    bookmark counts, verified live 2026-07-27: 3-262 range vs hotentry's
    curated-popular set). No native id in the feed, so the entry's own URL
    (the item's `rdf:about`) is the native id -- unique and stable, which
    is all dedup needs."""
    rows: dict[str, dict] = {}

    def _run(path: str, category: str, slice_name: str) -> None:
        url = f"https://b.hatena.ne.jp/{path}/{category}.rss"
        items = _parse_hatena_rss_items(_http_get_text(url))
        for entry in items:
            title = entry.get("title")
            article_url = entry.get("url")
            row = build_row(
                source="hatena",
                native_id=article_url,
                lang=detect_lang(title or ""),
                title=title,
                text="",
                url=article_url,
                metric={"points": 0, "comments": 0, "reactions": 0, "likes": 0,
                        "bookmarks": entry.get("bookmarks", 0)},
                slice_name=slice_name,
                followers=0,
                topic_tags=[],
                harvested_at=harvested_at,
            )
            if row and row["id"] not in rows:
                rows[row["id"]] = row

    for category in HATENA_CATEGORIES:
        _run("hotentry", category, "top")
    for category in HATENA_CATEGORIES:
        _run("entrylist", category, "baseline")
    return list(rows.values())


def fetch_qiita(min_stocks: int, window_days: int, harvested_at: str) -> list[dict]:
    """2 requests: a stocks-floored, date-scoped query (top slice -- a real
    popularity floor, not just a recency window) + the plain unfiltered
    listing (baseline slice; Qiita's default order is date-descending with
    no popularity weighting at all, so this is already a fair baseline on
    its own, same reasoning as HN round-3's fix but true from the start
    here since Qiita never ranks by relevance/points the way HN's /search
    does)."""
    rows: dict[str, dict] = {}

    def _run(url: str, slice_name: str) -> None:
        data = _http_get_json(url)
        for item in data:
            native_id = item.get("id")
            title = item.get("title")
            row = build_row(
                source="qiita",
                native_id=native_id,
                lang=detect_lang(title or ""),
                title=title,
                text="",
                url=item.get("url"),
                metric={"points": 0, "comments": item.get("comments_count", 0),
                        "reactions": 0, "likes": item.get("likes_count", 0)},
                slice_name=slice_name,
                followers=0,
                topic_tags=[],
                harvested_at=harvested_at,
            )
            if row and row["id"] not in rows:
                rows[row["id"]] = row

    since = (datetime.now(timezone.utc) - timedelta(days=window_days)).strftime("%Y-%m-%d")
    query = f"stocks:>={min_stocks} created:>{since}"
    top_url = f"https://qiita.com/api/v2/items?{urllib.parse.urlencode({'page': 1, 'per_page': 100, 'query': query})}"
    _run(top_url, "top")
    baseline_url = f"https://qiita.com/api/v2/items?{urllib.parse.urlencode({'page': 1, 'per_page': 100})}"
    _run(baseline_url, "baseline")
    return list(rows.values())


SOURCE_FETCHERS = {
    "hn": lambda min_points, top_days, harvested_at: fetch_hn(min_points, harvested_at),
    "devto": lambda min_points, top_days, harvested_at: fetch_devto(top_days, harvested_at),
    "zenn": lambda min_points, top_days, harvested_at: fetch_zenn(harvested_at),
    "hatena": lambda min_points, top_days, harvested_at: fetch_hatena(harvested_at),
    "qiita": lambda min_points, top_days, harvested_at: fetch_qiita(
        DEFAULT_QIITA_MIN_STOCKS, DEFAULT_QIITA_WINDOW_DAYS, harvested_at),
}


def harvest(out_dir: Path, min_points: int, top_days: int) -> dict:
    """Fetch all sources independently; one source's network failure must
    not fail the others (each is wrapped in its own try/except)."""
    now = datetime.now(timezone.utc)
    harvested_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = now.strftime("%Y-%m-%d")
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {"date": date_str, "sources": {}}
    any_rows = False
    for source, fetch in SOURCE_FETCHERS.items():
        entry = {"fetched": 0, "written": 0, "duplicate": 0, "error": None}
        try:
            rows = fetch(min_points, top_days, harvested_at)
            rows = apply_norm_scores(rows)
            entry["fetched"] = len(rows)
            path = out_dir / f"{date_str}-{source}.jsonl"
            written, duplicate = append_rows(path, rows)
            entry["written"] = written
            entry["duplicate"] = duplicate
            if rows:
                any_rows = True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}"
        report["sources"][source] = entry
    report["ok"] = any_rows
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_out_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "state" / "writing-corpus"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_harvest = sub.add_parser("harvest", help="fetch HN + dev.to + Zenn + Hatena Bookmark + Qiita and append new rows")
    p_harvest.add_argument("--out-dir", default=None, help="writing-corpus dir (default: sibling state/)")
    p_harvest.add_argument("--min-points", type=int, default=DEFAULT_MIN_POINTS)
    p_harvest.add_argument("--top-days", type=int, default=DEFAULT_TOP_DAYS)

    p_stats = sub.add_parser("stats", help="print counts per source/lang and date range")
    p_stats.add_argument("--out-dir", default=None)

    args = parser.parse_args(argv)
    out_dir = Path(args.out_dir) if args.out_dir else _default_out_dir()

    if args.command == "harvest":
        try:
            report = harvest(out_dir, args.min_points, args.top_days)
        except HarvestContractError as exc:
            print(f"FATAL: {exc}", file=sys.stderr)
            return 3
        print(json.dumps(report))
        return 0 if report["ok"] else 1

    if args.command == "stats":
        print(json.dumps(collect_stats(out_dir)))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
