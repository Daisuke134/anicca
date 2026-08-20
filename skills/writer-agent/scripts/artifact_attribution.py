#!/usr/bin/env python3
"""artifact_attribution.py — joins Writer money to ONE published artifact, or says it cannot.

THE ATTRIBUTION KEY
-------------------
Spec §22.14 fixes the join lineage as
`product_id + run_id + artifact_id + variant_id + destination + published_at`, and §28.6
item 4 requires a Stripe `client_reference_id = <artifact_id>` to carry it. So `artifact_id`
has to already exist in `state/articles.jsonl` — and it does not.

No new id is invented here. `artifact_id` is a deterministic, REVERSIBLE encoding of three
fields every published row in `state/articles.jsonl` already carries, and which
`scripts/_shared/measure-funnel.py` already joins on:

    artifact_id = "<run_id>__<platform>__<lang>"

  * `run_id`            — one Writer run; `measure-funnel.derive_manifest()` already selects by it.
  * `platform` + `lang` — measure-funnel's EXACT8 `pair`. One run publishes exactly one artifact
                          per pair, so (run_id, platform, lang) is unique per artifact.
  * `topic_id` is deliberately NOT in the key: it is a function of `run_id` (1 run = 1 topic).
    Folding it in would break every existing join the day a topic is renamed. It travels
    alongside as context instead.
  * `public_id` / `live_url` are NOT the key: they only exist after publication and their shape
    differs per platform. They are used in the REVERSE direction — `resolve_source_url()` maps a
    money receipt's URL back to an `artifact_id`.

`__` is the separator because `run_id` and `platform` both contain `-`, so `-` cannot be
unambiguous. The resulting charset is `[A-Za-z0-9_-]` and the length is ~35 chars, which is
exactly what Stripe accepts for `client_reference_id` on Payment Links (<= 200 chars) — that is
the whole point: the key can be pasted into Stripe unchanged when collector task #4 lands.

SCOPE
-----
Some platform numbers are genuinely per-article (a note paid-article purchase, a Stripe
checkout carrying the key). Others are only ever account-wide (Substack MRR, note's monthly
dashboard total). Every sales row therefore declares `scope`:

    scope = "artifact"  -> the row also carries `artifact_id`
    scope = "account"   -> the row carries NO artifact key, plus a `scope_reason`

An account-level number is NEVER spread, divided, or guessed onto an article. An account-scoped
row is a correct outcome, not a gap.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

# same tuple as scripts/_shared/measure-funnel.py; kept here so the key encoder can be
# validated against the real publication surface without importing a hyphenated module.
EXACT8 = (
    "note/ja",
    "zenn-article/ja",
    "devto/en",
    "substack/ja",
    "substack/en",
    "x-article/ja",
    "x-article/en",
    "x-post/ja",
)

SEPARATOR = "__"
SCOPE_ARTIFACT = "artifact"
SCOPE_ACCOUNT = "account"

# Stripe Payment Links accept alphanumerics, dashes and underscores, up to 200 chars.
STRIPE_CLIENT_REFERENCE_RE = re.compile(r"[A-Za-z0-9_-]{1,200}")
_FIELD_RE = re.compile(r"[A-Za-z0-9-]+")

# Numbers that are structurally account-wide. Listed as (platform, metric) so a future
# per-article metric on the SAME platform is unaffected.
ACCOUNT_ONLY_METRICS: dict[tuple[str, str], str] = {
    ("note", "sales_revenue"): (
        "note's 今月の売上 total is an account-wide monthly sum across every article"
    ),
    ("note", "sales_count"): (
        "note's 販売履歴 count is an account-wide monthly sum across every article"
    ),
    ("substack", "paid_subscribers"): (
        "a Substack paid subscriber belongs to the publication account, not to one post"
    ),
    ("substack", "mrr"): (
        "Substack MRR is publication-account recurring revenue, not one post's earnings"
    ),
    ("substack", "revenue"): (
        "Substack cumulative revenue is publication-account wide"
    ),
}

# Where an explicit artifact key may arrive from. `client_reference_id` is the Stripe field
# named by §28.6 item 4; listing it here is what lets that collector drop in without a
# schema migration.
ARTIFACT_KEY_FIELDS = ("artifact_id", "client_reference_id")


class AttributionKeyError(ValueError):
    """A value cannot be encoded into, or decoded from, one artifact identity."""


def artifact_id(*, run_id: str, platform: str, lang: str) -> str:
    """Encode the canonical article identity. Reversible via `parse_artifact_id`."""
    parts = {"run_id": run_id, "platform": platform, "lang": lang}
    for name, value in parts.items():
        if not isinstance(value, str) or not _FIELD_RE.fullmatch(value):
            raise AttributionKeyError(
                f"{name}={value!r} is not usable in an artifact_id "
                "(allowed: A-Z a-z 0-9 and '-')"
            )
    key = SEPARATOR.join((run_id, platform, lang))
    if not STRIPE_CLIENT_REFERENCE_RE.fullmatch(key):
        raise AttributionKeyError(f"artifact_id {key!r} is not Stripe-safe")
    return key


def parse_artifact_id(key: str) -> dict[str, str]:
    """Decode an artifact_id back into the ledger fields it was built from."""
    if not isinstance(key, str):
        raise AttributionKeyError("artifact_id must be a string")
    parts = key.split(SEPARATOR)
    if len(parts) != 3 or not all(_FIELD_RE.fullmatch(part) for part in parts):
        raise AttributionKeyError(f"artifact_id {key!r} is malformed")
    return {"run_id": parts[0], "platform": parts[1], "lang": parts[2]}


def artifact_id_for_row(row: Mapping[str, Any]) -> str | None:
    """Build the key from an articles.jsonl / funnel.jsonl row, or None if it cannot."""
    platform = row.get("platform")
    lang = row.get("lang") or row.get("language")
    if not lang and isinstance(row.get("pair"), str):
        platform, _, lang = row["pair"].rpartition("/")
    run_id = row.get("run_id")
    if not (run_id and platform and lang):
        return None
    try:
        return artifact_id(run_id=str(run_id), platform=str(platform), lang=str(lang))
    except AttributionKeyError:
        return None


def normalize_url(url: str) -> str:
    """Drop query/fragment/trailing slash so a receipt URL matches its live_url."""
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}".lower()


def build_artifact_index(article_rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Index published artifacts by key and by normalized live_url.

    A URL that maps to more than one artifact is recorded as ambiguous and never resolved —
    guessing between two articles would be fabrication.
    """
    artifacts: dict[str, dict[str, Any]] = {}
    by_url: dict[str, set[str]] = {}
    for row in article_rows:
        key = artifact_id_for_row(row)
        if key is None:
            continue
        live_url = row.get("live_url")
        if not live_url:
            continue
        fields = parse_artifact_id(key)
        existing = artifacts.get(key)
        # last write wins on ts, matching the append-only ledger's own semantics
        if existing and str(row.get("ts", "")) < str(existing.get("ts", "")):
            continue
        artifacts[key] = {
            "artifact_id": key,
            **fields,
            "topic_id": row.get("topic_id"),
            "live_url": live_url,
            "public_id": row.get("public_id"),
            "published_at": row.get("published_at"),
            "artifact_sha256": row.get("artifact_sha256"),
            "ts": row.get("ts"),
        }
        by_url.setdefault(normalize_url(str(live_url)), set()).add(key)
    return {"artifacts": artifacts, "by_url": by_url}


def resolve_source_url(url: str | None, index: Mapping[str, Any]) -> str | None:
    """Map a money receipt URL back to exactly one artifact_id, else None."""
    if not url:
        return None
    keys = index.get("by_url", {}).get(normalize_url(str(url)))
    if not keys or len(keys) != 1:
        return None
    return next(iter(keys))


def classify_sales_row(
    row: Mapping[str, Any], index: Mapping[str, Any]
) -> dict[str, Any]:
    """Return a copy of `row` with `scope` (+ `artifact_id` only when scope is artifact).

    Order matters. The account-only check runs FIRST so that an account-wide number can never
    be turned into per-article revenue, not even by a caller that attached a key to it.
    """
    scoped = dict(row)
    platform = str(row.get("platform", ""))
    metric = str(row.get("metric", ""))

    account_reason = ACCOUNT_ONLY_METRICS.get((platform, metric))
    if account_reason is not None:
        carried = next(
            (row[field] for field in ARTIFACT_KEY_FIELDS if row.get(field)), None
        )
        for field in ARTIFACT_KEY_FIELDS:
            scoped.pop(field, None)
        scoped["scope"] = SCOPE_ACCOUNT
        scoped["scope_reason"] = account_reason
        if carried:
            scoped["rejected_artifact_id"] = carried
            scoped["scope_reason"] = (
                f"{account_reason}; the carried artifact key was NOT used for attribution"
            )
        return scoped

    for field in ARTIFACT_KEY_FIELDS:
        carried = row.get(field)
        if not carried:
            continue
        try:
            parse_artifact_id(str(carried))
        except AttributionKeyError as exc:
            scoped["scope"] = SCOPE_ACCOUNT
            scoped["scope_reason"] = f"{field}={carried!r} is not a valid artifact_id: {exc}"
            return scoped
        scoped["scope"] = SCOPE_ARTIFACT
        scoped["artifact_id"] = str(carried)
        scoped["artifact_known"] = str(carried) in index.get("artifacts", {})
        return scoped

    resolved = resolve_source_url(row.get("source_url"), index)
    if resolved:
        scoped["scope"] = SCOPE_ARTIFACT
        scoped["artifact_id"] = resolved
        scoped["artifact_known"] = True
        return scoped

    scoped["scope"] = SCOPE_ACCOUNT
    scoped["scope_reason"] = (
        f"source_url={row.get('source_url')!r} does not identify exactly one published "
        "artifact and the row carries no artifact key; account-scoped is the honest outcome"
    )
    return scoped


def _add_amount(totals: dict[str, float], row: Mapping[str, Any]) -> bool:
    """Sum only scorable numeric values. Missing is never coerced to zero."""
    value = row.get("value")
    status = row.get("status", "scorable" if row.get("ok") else "unknown")
    if status != "scorable" or not isinstance(value, (int, float)):
        return False
    unit = str(row.get("unit") or "unknown")
    totals[unit] = totals.get(unit, 0) + value
    return True


def _engagement_for(
    key: str,
    funnel: Iterable[Mapping[str, Any]],
    own_metrics: Iterable[Mapping[str, Any]],
    live_url: str | None,
) -> dict[str, Any]:
    latest = None
    for row in funnel:
        if artifact_id_for_row(row) != key:
            continue
        if latest is None or str(row.get("measured_at", "")) >= str(
            latest.get("measured_at", "")
        ):
            latest = row
    own = None
    if live_url:
        target = normalize_url(str(live_url))
        for row in own_metrics:
            if row.get("url") and normalize_url(str(row["url"])) == target:
                if own is None or str(row.get("ts", "")) >= str(own.get("ts", "")):
                    own = row
    measured = (latest or {}).get("measured")
    if isinstance(measured, dict) and "error" not in measured:
        return {
            "status": "measured",
            "source": "funnel.jsonl",
            "measured_at": latest.get("measured_at"),
            "metrics": measured,
        }
    if own and isinstance(own.get("metric"), dict):
        return {
            "status": "measured",
            "source": "own-metrics.jsonl",
            "measured_at": own.get("ts"),
            "metrics": own["metric"],
        }
    reason = None
    if isinstance(measured, dict):
        reason = measured.get("error")
    return {
        "status": "unknown",
        "reason": reason or "no measured engagement row for this artifact",
    }


def join_revenue(
    *,
    articles: Iterable[Mapping[str, Any]],
    funnel: Iterable[Mapping[str, Any]],
    own_metrics: Iterable[Mapping[str, Any]],
    sales: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """publish identity -> engagement -> attributable revenue, + what stayed account-scoped."""
    articles = list(articles)
    funnel = list(funnel)
    own_metrics = list(own_metrics)
    index = build_artifact_index(articles)

    scoped_rows = [classify_sales_row(row, index) for row in sales]
    per_artifact: dict[str, list[dict[str, Any]]] = {}
    unjoinable: list[dict[str, Any]] = []
    account_rows: list[dict[str, Any]] = []
    for row in scoped_rows:
        if row["scope"] != SCOPE_ARTIFACT:
            account_rows.append(row)
        elif row.get("artifact_known"):
            per_artifact.setdefault(row["artifact_id"], []).append(row)
        else:
            unjoinable.append(row)

    out_artifacts = []
    with_revenue = 0
    engagement_only = 0
    for key, meta in sorted(index["artifacts"].items()):
        engagement = _engagement_for(key, funnel, own_metrics, meta.get("live_url"))
        rows = per_artifact.get(key, [])
        totals: dict[str, float] = {}
        measured = sum(1 for row in rows if _add_amount(totals, row))
        if measured:
            revenue = {
                "status": "attributed",
                "totals_by_unit": totals,
                "rows": len(rows),
                "unknown_rows": len(rows) - measured,
            }
            with_revenue += 1
        else:
            revenue = {
                "status": "unknown",
                "totals_by_unit": "unknown",
                "rows": len(rows),
                "reason": (
                    "no artifact-scoped sales row with a measured value references this "
                    "artifact; unknown is not zero"
                ),
            }
            if engagement["status"] == "measured":
                engagement_only += 1
        out_artifacts.append(
            {
                "artifact_id": key,
                "run_id": meta["run_id"],
                "topic_id": meta.get("topic_id"),
                "platform": meta["platform"],
                "lang": meta["lang"],
                "live_url": meta.get("live_url"),
                "public_id": meta.get("public_id"),
                "published_at": meta.get("published_at"),
                "artifact_sha256": meta.get("artifact_sha256"),
                "engagement": engagement,
                "revenue": revenue,
            }
        )

    account_totals: dict[str, float] = {}
    account_measured = sum(1 for row in account_rows if _add_amount(account_totals, row))
    unjoinable_totals: dict[str, float] = {}
    for row in unjoinable:
        _add_amount(unjoinable_totals, row)

    return {
        "attribution_key": "run_id__platform__lang",
        "artifacts": out_artifacts,
        "account_scoped_revenue": {
            "rows": len(account_rows),
            "measured_rows": account_measured,
            "unknown_rows": len(account_rows) - account_measured,
            "measured_totals_by_unit": account_totals,
            "note": (
                "publication/account-wide numbers. They are NOT divided across articles; "
                "no per-article attribution exists for them."
            ),
            "by_platform_metric": sorted(
                {f"{row.get('platform')}/{row.get('metric')}" for row in account_rows}
            ),
        },
        "artifact_scoped_but_unjoinable_revenue": {
            "rows": len(unjoinable),
            "measured_totals_by_unit": unjoinable_totals,
            "artifact_ids": sorted({row["artifact_id"] for row in unjoinable}),
            "note": (
                "money that carries an artifact key naming an artifact absent from "
                "articles.jsonl"
            ),
        },
        "summary": {
            "artifacts_total": len(out_artifacts),
            "artifacts_with_attributed_revenue": with_revenue,
            "artifacts_with_engagement_no_revenue": engagement_only,
            "artifacts_with_engagement": sum(
                1 for a in out_artifacts if a["engagement"]["status"] == "measured"
            ),
            "sales_rows_total": len(scoped_rows),
            "sales_rows_artifact_scoped": len(scoped_rows) - len(account_rows),
            "sales_rows_account_scoped": len(account_rows),
        },
    }
