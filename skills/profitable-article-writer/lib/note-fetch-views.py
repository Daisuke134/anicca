#!/usr/bin/env python3
"""lib/note-fetch-views.py -- REQ-28 (Sprint 5): "view -> yen" funnel, views half. Fetches REAL per-article
view counts for every note.com key this skill has verified live (state/live-publishes.jsonl, PASS==true)
and appends one honest metrics line per key to state/article-metrics.jsonl.

WHY a logged-IN fetch (unlike lib/note-verify-live.py's deliberately logged-out check): note.com's own
per-article read/like counters are ONLY exposed to the account owner, via the SAME session cookie the
Mode-A/Mode-B publish pipeline already uses (NOTE_COOKIES_FILE). There is no public per-article view-count
endpoint on note.com (confirmed by probing this account's own live articles: the public note page + the
public GET /api/v3/notes/<key> response both omit any view/read field; only the authenticated
GET /api/v1/stats/pv endpoint returns it, as `read_count`/`like_count` per note in its `note_stats` array).

REVENUE HONESTY (task requirement, non-negotiable): this tool has NO verified path to note.com's actual JPY
sales/payout numbers (no sales-stats endpoint was found reachable from this account's session; note.com's
creator payout dashboard is not confirmed scriptable). It therefore ALWAYS records revenue_jpy: 0 with
revenue_source: "not_verified_no_sales_api" -- never a guessed or fabricated non-zero figure. A future
sprint that finds/proves a real sales-read path should replace this constant, not this tool's honesty
contract.

INTERFACE:
  argv: none
  env in:
    NOTE_COOKIES_FILE           default: $HOME/.cloak/note-work/note-cookies.json (same convention as the
                                other lib/note-*.py scripts). A JSON object of {cookie_name: value}.
    NOTE_USERNAME               default "anicca123"
    NOTE_LIVE_STATE_FILE        default: <this skill>/state/live-publishes.jsonl -- the SOURCE list of keys
                                to fetch views for (only entries with "PASS": true are considered; the
                                latest entry per key wins if a key appears more than once).
    ARTICLE_METRICS_STATE_FILE  default: <this skill>/state/article-metrics.jsonl -- the ledger this tool
                                appends to (never overwrites; append-only, same as live-publishes.jsonl).
    NOTE_STATS_FILTER           default "all" -- the note.com stats API's own time-window filter
                                (day|week|month|all); "all" is the only one guaranteed to cover every
                                key regardless of publish date.
  stdout: one JSON line per key processed, PLUS a final summary line
          {"summary": true, "processed": N, "views_recorded": N, "views_none": N}
  exit: 0 always for a normal run (this is a best-effort periodic job -- a single key's failure or even a
        total stats-API failure must never crash the caller; every failure mode is recorded to the ledger
        as an honest "views": "none" row with a "views_reason", never silently dropped and never a fake
        number). Exit 2 only for a genuine argv/usage error.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_LIVE_STATE_FILE = os.path.join(_SKILL_DIR, "state", "live-publishes.jsonl")
_DEFAULT_METRICS_STATE_FILE = os.path.join(_SKILL_DIR, "state", "article-metrics.jsonl")
_DEFAULT_COOKIES_FILE = os.path.join(os.path.expanduser("~"), ".cloak", "note-work", "note-cookies.json")

REVENUE_SOURCE_NOT_VERIFIED = "not_verified_no_sales_api"


def _load_published_keys(live_state_file: str) -> list:
    """Read live-publishes.jsonl -> ordered list of DISTINCT keys with the latest PASS==true entry per key.
    A key that only ever appears with PASS: false (e.g. a deliberately-nonexistent test placeholder key) is
    excluded -- never fetched, never recorded as a false "views: none" row for a key that was never really
    live. Missing/unreadable file -> empty list (never raises)."""
    latest_by_key: dict = {}
    try:
        with open(live_state_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                key = row.get("key")
                if not key:
                    continue
                latest_by_key[key] = row
    except FileNotFoundError:
        return []
    except Exception:
        return []

    return [key for key, row in latest_by_key.items() if row.get("PASS") is True]


def _load_cookie_header(cookies_file: str):
    """Returns (cookie_header_str, error_reason). error_reason is None on success."""
    try:
        with open(cookies_file, "r") as f:
            cookies = json.load(f)
    except FileNotFoundError:
        return None, "no_session_cookie"
    except Exception as e:
        return None, f"cookie_file_unreadable:{e}"

    if not isinstance(cookies, dict) or not cookies:
        return None, "cookie_file_empty_or_malformed"

    return "; ".join(f"{k}={v}" for k, v in cookies.items()), None


def _fetch_note_stats(cookie_header: str, filt: str):
    """Returns (stats_by_key: dict|None, error_reason: str|None). Never raises."""
    url = f"https://note.com/api/v1/stats/pv?filter={filt}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*", "Cookie": cookie_header})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return None, f"stats_api_http_error:{e.code}"
    except Exception as e:
        return None, f"stats_api_fetch_error:{e}"

    if status != 200:
        return None, f"stats_api_http_error:{status}"

    try:
        data = json.loads(body).get("data", {})
    except Exception as e:
        return None, f"stats_api_bad_json:{e}"

    stats_by_key = {}
    for row in data.get("note_stats", []) or []:
        k = row.get("key")
        if k:
            stats_by_key[k] = row
    return stats_by_key, None


def _record(result: dict, state_file: str) -> None:
    """Best-effort append, one JSON line -- never raises (mirrors lib/note-verify-live.py's convention)."""
    try:
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, "a") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"note-fetch-views: state recording to {state_file!r} failed (non-fatal): {e}", file=sys.stderr)


def main() -> int:
    live_state_file = os.environ.get("NOTE_LIVE_STATE_FILE", _DEFAULT_LIVE_STATE_FILE)
    metrics_state_file = os.environ.get("ARTICLE_METRICS_STATE_FILE", _DEFAULT_METRICS_STATE_FILE)
    cookies_file = os.environ.get("NOTE_COOKIES_FILE", _DEFAULT_COOKIES_FILE)
    username = os.environ.get("NOTE_USERNAME", "anicca123")
    filt = os.environ.get("NOTE_STATS_FILTER", "all")

    keys = _load_published_keys(live_state_file)

    cookie_header, cookie_err = _load_cookie_header(cookies_file)
    stats_by_key, stats_err = (None, cookie_err) if cookie_err else _fetch_note_stats(cookie_header, filt)
    top_level_err = cookie_err or stats_err

    processed = 0
    views_recorded = 0
    views_none = 0
    ts = int(time.time())

    for key in keys:
        url = f"https://note.com/{username}/n/{key}"
        row = (stats_by_key or {}).get(key)
        if top_level_err is not None:
            result = {
                "ts": ts, "key": key, "url": url,
                "views": "none", "views_reason": top_level_err,
                "likes": None,
                "revenue_jpy": 0, "revenue_source": REVENUE_SOURCE_NOT_VERIFIED,
            }
            views_none += 1
        elif row is None:
            result = {
                "ts": ts, "key": key, "url": url,
                "views": "none", "views_reason": "key_not_in_stats_response",
                "likes": None,
                "revenue_jpy": 0, "revenue_source": REVENUE_SOURCE_NOT_VERIFIED,
            }
            views_none += 1
        else:
            result = {
                "ts": ts, "key": key, "url": url,
                "views": row.get("read_count", 0) or 0, "views_reason": None,
                "likes": row.get("like_count", 0) or 0,
                "revenue_jpy": 0, "revenue_source": REVENUE_SOURCE_NOT_VERIFIED,
            }
            views_recorded += 1

        print(json.dumps(result, ensure_ascii=False))
        _record(result, metrics_state_file)
        processed += 1

    print(json.dumps({"summary": True, "processed": processed, "views_recorded": views_recorded, "views_none": views_none}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
