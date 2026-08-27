#!/usr/bin/env python3
"""One non-overlapping watch -> select -> queue-refill wake for Writer Agent."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from claim_supply import model_choose, refill_queue  # noqa: E402
from claim_store import SHA256_RE  # noqa: E402
from claim_watch import run_watch  # noqa: E402
from demand_observations import (  # noqa: E402
    DemandObservationError,
    claim_observations,
    configured_full_body_observations,
    mix_observations,
)
from x_article_identity import is_link_only_x_article_shell_title  # noqa: E402
from x_authenticated_cli import XArticleCaptureError, capture_x_article_body  # noqa: E402


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def _default_demand_reader(state: Path) -> list[dict[str, Any]]:
    observations = mix_observations(
        opportunity_database=(state / "opportunities.sqlite3")
        if (state / "opportunities.sqlite3").exists()
        else None,
        state_dir=state,
    )
    if (state / "claims.sqlite3").exists():
        observations.extend(claim_observations(state / "claims.sqlite3"))
    return observations


X_TARGET_LIMIT = 5
ARTICLE_DAILY_LOCK_STALE_SECONDS = 6 * 60 * 60
ARTICLE_DAILY_LOCK_OWNER_FILE = "owner.token"
ARTICLE_DAILY_RECOVERY_LOCK_DIR = "state/.article-daily.recovery.lockdir"


def _recent_x_claim_candidates(
    database: Path,
    *,
    limit: int = X_TARGET_LIMIT,
) -> list[dict[str, Any]]:
    """Read bounded X URLs as capture candidates without mutating ClaimStore.

    Claim-watch rows intentionally have no demand source family until the authenticated
    Article DOM verifier accepts them.  Keep these rows out of the demand digest and
    pass only their URL identity to the capture gate.
    """

    if not database.exists():
        return []
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        raise DemandObservationError("x_article_target_limit must be between 1 and 50")
    uri = f"file:{database.resolve()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT claim_id,canonical_url,first_observed_at,first_retrieved_sha256 "
                "FROM claims WHERE source_kind='x' "
                "ORDER BY first_observed_at DESC,claim_id ASC LIMIT ?",
                (limit,),
            ).fetchall()
    except sqlite3.Error as error:
        raise DemandObservationError("X claim candidate receipt is unreadable") from error
    candidates: list[dict[str, Any]] = []
    for row in rows:
        url = row["canonical_url"]
        if not isinstance(url, str) or not url.strip():
            continue
        candidates.append(
            {
                "observation_id": f"claim-candidate:{row['claim_id']}",
                "source_kind": "x",
                "source_url": url.strip(),
                "observed_at": row["first_observed_at"],
                "source_sha256": row["first_retrieved_sha256"],
            }
        )
    return candidates


def _x_observation_url(row: Mapping[str, Any]) -> str | None:
    if row.get("source_kind") not in (None, "x") and row.get("source_family") != "reader_demand":
        return None
    for field in ("source_url", "canonical_url", "url"):
        value = row.get(field)
        if not isinstance(value, str) or not value.strip():
            continue
        parsed = urlsplit(value.strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        parts = [part for part in parsed.path.split("/") if part]
        if host not in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
            continue
        if len(parts) < 3 or parts[-2] not in {"status", "article"}:
            continue
        if not parts[-1].isdigit() or len(parts[-1]) < 3:
            continue
        return value.strip()
    return None


def _recent_x_targets(
    observations: list[Mapping[str, Any]] | None,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if observations is None:
        return []
    candidates: list[tuple[str, str, Mapping[str, Any]]] = []
    for index, row in enumerate(observations):
        if not isinstance(row, Mapping):
            continue
        url = _x_observation_url(row)
        if url is None:
            continue
        timestamp = ""
        for field in ("observed_at", "captured_at", "published_at", "created_at"):
            value = row.get(field)
            if isinstance(value, str) and value.strip():
                timestamp = value.strip()
                break
        observation_id = str(row.get("observation_id") or f"x-observation-{index}")
        candidates.append((timestamp, observation_id, row | {"source_url": url}))
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _, observation_id, row in candidates:
        url = str(row["source_url"])
        if url in seen:
            continue
        seen.add(url)
        selected.append(
            {
                "url": url,
                "observation_id": observation_id,
                "observed_at": next(
                    (
                        str(row[field])
                        for field in ("observed_at", "captured_at", "published_at", "created_at")
                        if isinstance(row.get(field), str) and row[field].strip()
                    ),
                    None,
                ),
                "source_sha256": row.get("source_sha256"),
            }
        )
        if len(selected) >= limit:
            break
    return selected


def _target_set_sha256(targets: list[Mapping[str, Any]]) -> str:
    """Hash the normalized URL set, independent of discovery/receipt IDs."""

    canonical = json.dumps(
        sorted(
            {
                str(row.get("url")).strip()
                for row in targets
                if isinstance(row.get("url"), str) and row.get("url").strip()
            }
        ),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _validated_rendered_identity(
    receipt: Mapping[str, Any],
    *,
    url: str,
    body: str,
) -> dict[str, Any] | None:
    """Require the compound Article identity facts at the capture boundary."""

    value = receipt.get("rendered_identity")
    if not isinstance(value, Mapping):
        return None
    path_parts = [part for part in urlsplit(url).path.split("/") if part]
    expected_target_id = (
        path_parts[-1]
        if len(path_parts) >= 3
        and path_parts[-2] in {"status", "article"}
        and path_parts[-1].isdigit()
        else None
    )
    shell_title = value.get("shell_title")
    rendered_url = value.get("rendered_url")
    status_target_id = value.get("status_target_id")
    if (
        receipt.get("article_identity") is not True
        or expected_target_id is None
        or str(receipt.get("target_id")) != expected_target_id
        or value.get("exact_status_url") is not True
        or value.get("target_id_match") is not True
        or not isinstance(rendered_url, str)
        or rendered_url.rstrip("/") != url.rstrip("/")
        or str(status_target_id) != expected_target_id
        or value.get("shell_link_only") is not True
        or value.get("article_count") != 1
        or value.get("article_container_count") != 1
        or value.get("container_selector") != "article"
        or value.get("longform_chars") != len(body)
        or not isinstance(value.get("block_count"), int)
        or value.get("block_count", 0) < 3
    ):
        return None
    if not is_link_only_x_article_shell_title(shell_title):
        return None
    return dict(value)


def _state_path(skill_dir: Path, state_dir: Path | str | None, value: str) -> Path:
    if state_dir is None:
        return skill_dir / value
    relative = Path(value)
    if relative.parts and relative.parts[0] == "state":
        relative = Path(*relative.parts[1:])
    return Path(state_dir) / relative


def _target_urls(
    skill_dir: Path,
    config: dict[str, Any],
    *,
    state_dir: Path | str | None = None,
    recent_observations: list[Mapping[str, Any]] | None = None,
) -> list[str]:
    urls = config.get("x_article_urls", [])
    if urls in (None, ""):
        urls = []
    if not isinstance(urls, list) or any(not isinstance(url, str) for url in urls):
        raise DemandObservationError("x_article_urls must be a string list")
    target_source = config.get(
        "x_article_target_source", "state/x-article-targets.json"
    )
    if not isinstance(target_source, str) or Path(target_source).is_absolute():
        raise DemandObservationError("x_article_target_source must be a relative path")
    target_file = _state_path(skill_dir, state_dir, target_source)
    raw_limit = config.get("x_article_target_limit", X_TARGET_LIMIT)
    if not isinstance(raw_limit, int) or isinstance(raw_limit, bool) or not 1 <= raw_limit <= 50:
        raise DemandObservationError("x_article_target_limit must be between 1 and 50")
    recent_targets = _recent_x_targets(recent_observations, limit=raw_limit)
    if recent_targets:
        # These are discovery candidates only.  The target receipt is written after
        # capture, with ``targets`` containing only Article-identity successes.
        return [row["url"] for row in recent_targets]
    if target_file.exists():
        try:
            loaded = json.loads(target_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DemandObservationError("X Article target receipt is invalid") from error
        if isinstance(loaded, dict):
            targets = loaded.get("targets")
            if not isinstance(targets, list) or any(
                not isinstance(row, dict) or not isinstance(row.get("url"), str)
                for row in targets
            ):
                raise DemandObservationError("X Article target receipt targets are invalid")
            urls = [str(row["url"]) for row in targets]
        elif isinstance(loaded, list) and all(isinstance(url, str) for url in loaded):
            urls = loaded
        else:
            raise DemandObservationError("X Article target receipt must be a target list")
        if recent_observations is not None:
            recent_urls = {row["url"] for row in _recent_x_targets(recent_observations, limit=raw_limit)}
            dangling = [url for url in urls if url not in recent_urls]
            if dangling:
                raise DemandObservationError(
                    "dangling X Article target receipt: " + ",".join(dangling)
                )
    else:
        seed_urls = config.get("x_article_seed_urls", [])
        if seed_urls not in (None, ""):
            if not isinstance(seed_urls, list) or any(
                not isinstance(url, str) for url in seed_urls
            ):
                raise DemandObservationError("x_article_seed_urls must be a string list")
            urls = [*urls, *seed_urls]
    return list(dict.fromkeys(url.strip() for url in urls if url.strip()))


def _x_article_receipt_store(
    skill_dir: Path,
    config: dict[str, Any],
    state_dir: Path | str | None = None,
) -> Path:
    value = config.get("x_article_receipt_store", "state/x-article-bodies.json")
    if not isinstance(value, str) or Path(value).is_absolute():
        raise DemandObservationError("x_article_receipt_store must be a relative path")
    return _state_path(skill_dir, state_dir, value)


def _article_daily_lock_path(
    skill_dir: Path,
    config: Mapping[str, Any],
    state_dir: Path | str | None = None,
) -> Path:
    """Return the canonical publication/CDP lock used by article-daily.sh."""

    # The publication loop owns this exact path.  Never let a config value move
    # the capture process to an alternate lock that article-daily does not see.
    del config
    return _state_path(skill_dir, state_dir, "state/.article-daily.lockdir")


def _article_daily_recovery_lock_path(
    skill_dir: Path, state_dir: Path | str | None = None
) -> Path:
    return _state_path(skill_dir, state_dir, ARTICLE_DAILY_RECOVERY_LOCK_DIR)


def _lock_identity(path: Path) -> tuple[int, int, int]:
    try:
        stat_result = path.stat()
    except OSError as error:
        raise XArticleCaptureError(
            "article-daily publication lock held; lock identity unavailable; capture pending"
        ) from error
    return (
        int(stat_result.st_dev),
        int(stat_result.st_ino),
        int(stat_result.st_mtime_ns),
    )


def _process_start_token(pid: int) -> str:
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "lstart="],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _owner_alive(lock_path: Path) -> bool:
    try:
        pid = int((lock_path / "owner.pid").read_text(encoding="utf-8").strip())
    except (FileNotFoundError, OSError, ValueError):
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    try:
        expected = (lock_path / "owner.start").read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return False
    return bool(expected) and expected == _process_start_token(pid)


def _owner_metadata_present(lock_path: Path) -> bool:
    try:
        pid = (lock_path / "owner.pid").read_text(encoding="utf-8").strip()
        started = (lock_path / "owner.start").read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return False
    return bool(pid and started and pid.isdigit())


def _quarantine_stale_lock(
    lock_path: Path,
    snapshot: tuple[int, int, int],
) -> Path:
    """Atomically move exactly the snapshotted stale directory aside.

    The identity recheck prevents a replacement owner observed after the initial
    stale check from being touched.  All callers hold the short recovery mutex,
    so normal article-daily/claim-loop acquisitions cannot replace the path
    between this recheck and the atomic rename.
    """

    if _lock_identity(lock_path) != snapshot:
        raise XArticleCaptureError(
            "article-daily publication lock held; stale identity changed during recovery; capture pending"
        )
    quarantine = lock_path.with_name(
        f".{lock_path.name}.stale-{uuid.uuid4().hex}"
    )
    try:
        lock_path.rename(quarantine)
    except OSError as error:
        raise XArticleCaptureError(
            "article-daily publication lock held; stale quarantine failed; capture pending"
        ) from error
    try:
        if _lock_identity(quarantine) != snapshot:
            raise XArticleCaptureError(
                "article-daily publication lock held; stale quarantine identity changed; capture pending"
            )
    except XArticleCaptureError:
        try:
            if not lock_path.exists():
                quarantine.rename(lock_path)
        except OSError:
            pass
        raise
    return quarantine


def _cleanup_quarantined_lock(
    quarantine: Path,
    original: Path,
) -> None:
    """Remove only the quarantined, identity-checked stale lock directory."""

    owner_path = quarantine / ARTICLE_DAILY_LOCK_OWNER_FILE
    for name in ("owner.token", "owner.pid", "owner.start"):
        try:
            (quarantine / name).unlink()
        except FileNotFoundError:
            pass
    try:
        quarantine.rmdir()
    except OSError as error:
        try:
            if not original.exists():
                quarantine.rename(original)
        except OSError:
            pass
        raise XArticleCaptureError(
            "article-daily publication lock held; stale lock cleanup failed; capture pending"
        ) from error


def _release_owned_lock(lock_path: Path, owner_token: str) -> None:
    owner_path = lock_path / ARTICLE_DAILY_LOCK_OWNER_FILE
    try:
        current_owner = owner_path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return
    if current_owner != owner_token:
        return
    for name in ("owner.token", "owner.pid", "owner.start"):
        try:
            (lock_path / name).unlink()
        except (FileNotFoundError, OSError):
            pass
    try:
        lock_path.rmdir()
    except FileNotFoundError:
        pass


def _claim_owned_lock(lock_path: Path) -> str:
    owner_token = uuid.uuid4().hex
    lock_path.mkdir()
    owner_path = lock_path / ARTICLE_DAILY_LOCK_OWNER_FILE
    try:
        owner_path.write_text(owner_token, encoding="utf-8")
        (lock_path / "owner.pid").write_text(str(os.getpid()), encoding="utf-8")
        (lock_path / "owner.start").write_text(
            _process_start_token(os.getpid()), encoding="utf-8"
        )
    except OSError:
        try:
            for name in ("owner.token", "owner.pid", "owner.start"):
                (lock_path / name).unlink()
            lock_path.rmdir()
        except OSError:
            pass
        raise
    return owner_token


@contextmanager
def _article_daily_recovery_mutex(
    skill_dir: Path, state_dir: Path | str | None = None
):
    """Serialize short lock acquisition/recovery across both Writer loops."""

    mutex_path = _article_daily_recovery_lock_path(skill_dir, state_dir)
    mutex_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        owner_token = _claim_owned_lock(mutex_path)
    except FileExistsError as error:
        snapshot = _lock_identity(mutex_path)
        age = time.time() - (snapshot[2] / 1_000_000_000)
        if age <= ARTICLE_DAILY_LOCK_STALE_SECONDS:
            raise XArticleCaptureError(
                "article-daily publication lock held; recovery lock held; X Article capture pending"
            ) from error
        if _owner_alive(mutex_path):
            raise XArticleCaptureError(
                "article-daily publication lock held; live recovery owner; X Article capture pending"
            ) from error
        if not _owner_metadata_present(mutex_path):
            raise XArticleCaptureError(
                "article-daily publication lock held; owner identity unavailable; X Article capture pending"
            ) from error
        quarantine = _quarantine_stale_lock(mutex_path, snapshot)
        _cleanup_quarantined_lock(quarantine, mutex_path)
        try:
            owner_token = _claim_owned_lock(mutex_path)
        except OSError as claim_error:
            raise XArticleCaptureError(
                "article-daily publication lock held; recovery lock reacquire failed; capture pending"
            ) from claim_error
    try:
        yield
    finally:
        _release_owned_lock(mutex_path, owner_token)


def _capture_with_article_daily_lock(
    skill_dir: Path,
    config: Mapping[str, Any],
    url: str,
    capturer: Callable[[str], dict[str, Any]],
    state_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Capture only while holding article-daily.sh's non-blocking lockdir.

    The lockdir is the shared contract for every process that drives the live CDP
    browser.  A held lock is retryable state, not permission to open a second tab.
    """

    lock_path = _article_daily_lock_path(skill_dir, config, state_dir)
    owner_token: str | None = None
    with _article_daily_recovery_mutex(skill_dir, state_dir):
        try:
            owner_token = _claim_owned_lock(lock_path)
        except FileExistsError as error:
            snapshot = _lock_identity(lock_path)
            age = time.time() - (snapshot[2] / 1_000_000_000)
            if age <= ARTICLE_DAILY_LOCK_STALE_SECONDS:
                raise XArticleCaptureError(
                    "article-daily publication lock held; X Article capture pending"
                ) from error
            if _owner_alive(lock_path):
                raise XArticleCaptureError(
                    "article-daily publication lock held; live publication owner; X Article capture pending"
                ) from error
            if not _owner_metadata_present(lock_path):
                raise XArticleCaptureError(
                    "article-daily publication lock held; owner identity unavailable; X Article capture pending"
                ) from error
            quarantine = _quarantine_stale_lock(lock_path, snapshot)
            _cleanup_quarantined_lock(quarantine, lock_path)
            try:
                owner_token = _claim_owned_lock(lock_path)
            except OSError as claim_error:
                raise XArticleCaptureError(
                    "article-daily publication lock held; publication lock reacquire failed; capture pending"
                ) from claim_error
    try:
        return capturer(url)
    finally:
        if owner_token is not None:
            _release_owned_lock(lock_path, owner_token)


def _load_x_article_receipt(
    skill_dir: Path,
    config: dict[str, Any],
    state_dir: Path | str | None = None,
) -> dict[str, Any] | None:
    path = _x_article_receipt_store(skill_dir, config, state_dir)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DemandObservationError("durable X Article receipt is invalid") from error
    observations = payload.get("observations") if isinstance(payload, dict) else None
    if not isinstance(observations, list) or any(
        not isinstance(row, dict) for row in observations
    ):
        raise DemandObservationError("durable X Article receipt observations are invalid")
    return {
        **payload,
        "observations": [dict(row) for row in observations],
    }


def _load_x_article_observations(
    skill_dir: Path,
    config: dict[str, Any],
    state_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    payload = _load_x_article_receipt(skill_dir, config, state_dir)
    return list(payload["observations"]) if payload is not None else []


def _load_verified_bootstrap_observations(
    skill_dir: Path,
    config: dict[str, Any],
    state_dir: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Load capture-verified bootstrap bodies retained before supply commits.

    A valid capture can precede a failed demand-card supply.  Keep that bounded
    fallback receipt reusable on the next wake, while rechecking the same body
    hash and compound Article identity facts before treating it as evidence.
    """

    receipt_path = config.get(
        "x_article_capture_receipt", "state/x-article-capture-latest.json"
    )
    if not isinstance(receipt_path, str) or Path(receipt_path).is_absolute():
        raise DemandObservationError("x_article_capture_receipt must be relative")
    path = _state_path(skill_dir, state_dir, receipt_path)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DemandObservationError("X Article capture receipt is invalid") from error
    if not isinstance(payload, dict) or payload.get("fallback") not in {
        "bootstrap", "verified-bootstrap"
    }:
        return []
    rows = payload.get("captured_observations")
    if not isinstance(rows, list):
        return []
    verified: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        source_url = row.get("source_url")
        body = row.get("full_body")
        source_sha256 = row.get("source_sha256")
        if (
            row.get("source_family") != "reader_demand"
            or not isinstance(source_url, str)
            or not isinstance(body, str)
            or not body.strip()
            or not isinstance(source_sha256, str)
            or SHA256_RE.fullmatch(source_sha256.lower()) is None
            or hashlib.sha256(body.encode("utf-8")).hexdigest()
            != source_sha256.lower()
            or row.get("capture_method") != "rendered_cdp_dom"
            or _validated_rendered_identity(
                row,
                url=source_url,
                body=body,
            )
            is None
        ):
            continue
        verified.append(dict(row))
    return verified


def _target_set_hash_from_file(path: Path) -> str | None:
    """Read the durable target-set identity after ``_target_urls`` validates it."""

    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DemandObservationError("X Article target receipt is invalid") from error
    if not isinstance(payload, dict):
        return None
    value = payload.get("target_set_sha256")
    if isinstance(value, str) and SHA256_RE.fullmatch(value.lower()):
        return value.lower()
    targets = payload.get("targets")
    if isinstance(targets, list) and all(
        isinstance(row, dict)
        and isinstance(row.get("url"), str)
        and isinstance(row.get("observation_id"), str)
        for row in targets
    ):
        return _target_set_sha256(targets)
    return None


def _load_x_target_payload(path: Path | None) -> dict[str, Any] | None:
    """Load the candidate/verified target receipt without opening any store writable."""

    if path is None or not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DemandObservationError("X Article target receipt is invalid") from error
    if isinstance(payload, list) and all(isinstance(url, str) for url in payload):
        return {
            "version": 0,
            "targets": [{"url": url} for url in payload],
        }
    if not isinstance(payload, dict):
        raise DemandObservationError("X Article target receipt must be an object or list")
    targets = payload.get("targets", [])
    if not isinstance(targets, list) or any(
        not isinstance(row, dict) or not isinstance(row.get("url"), str)
        for row in targets
    ):
        raise DemandObservationError("X Article target receipt targets are invalid")
    return dict(payload)


def _commit_x_article_observations(
    skill_dir: Path,
    config: dict[str, Any],
    observations: list[dict[str, Any]],
    *,
    state_dir: Path | str | None = None,
    supply: dict[str, Any] | None = None,
) -> bool:
    """Commit captured X bodies only after a valid demand card is durable."""

    if supply is None or not (
        supply.get("status") in {"FILLED", "SUFFICIENT"}
        and supply.get("demand_card_sha256")
    ):
        return False
    if not observations:
        return False
    for row in observations:
        body = row.get("full_body")
        if (
            row.get("source_family") != "reader_demand"
            or row.get("capture_method") != "rendered_cdp_dom"
            or not isinstance(body, str)
            or not body.strip()
            or not isinstance(row.get("source_sha256"), str)
            or hashlib.sha256(body.strip().encode("utf-8")).hexdigest()
            != str(row["source_sha256"]).lower()
            or _validated_rendered_identity(
                row,
                url=str(row.get("source_url")),
                body=body,
            )
            is None
        ):
            raise DemandObservationError("X Article durable receipt is incomplete or hash-invalid")
    target_source = config.get(
        "x_article_target_source", "state/x-article-targets.json"
    )
    target_set_sha256 = None
    if isinstance(target_source, str) and not Path(target_source).is_absolute():
        target_path = _state_path(skill_dir, state_dir, target_source)
        if target_path.exists():
            try:
                target_payload = json.loads(target_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise DemandObservationError("X Article target receipt is invalid") from error
            if isinstance(target_payload, dict):
                value = target_payload.get("target_set_sha256")
                if isinstance(value, str) and SHA256_RE.fullmatch(value.lower()):
                    target_set_sha256 = value.lower()
    if target_set_sha256 is None:
        target_set_sha256 = _target_set_sha256(
            [
                {
                    "url": row.get("source_url"),
                    "observation_id": row.get("observation_id"),
                }
                for row in observations
            ]
        )
    canonical = json.dumps(
        observations,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    _atomic_json(
        _x_article_receipt_store(skill_dir, config, state_dir),
        {
            "version": 1,
            "committed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "observations": observations,
            "target_set_sha256": target_set_sha256,
            "observations_sha256": hashlib.sha256(canonical).hexdigest(),
        },
    )
    seed_receipt = config.get(
        "x_article_seed_receipt", "state/x-article-seeds-used.json"
    )
    if isinstance(seed_receipt, str) and not Path(seed_receipt).is_absolute():
        urls = [str(row.get("source_url")) for row in observations]
        _atomic_json(
            _state_path(skill_dir, state_dir, seed_receipt),
            {
                "version": 1,
                "consumed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "urls": urls,
                "url_sha256": [hashlib.sha256(url.encode("utf-8")).hexdigest() for url in urls],
                "observations_sha256": hashlib.sha256(canonical).hexdigest(),
            },
        )
    return True


def _x_article_observations(
    skill_dir: Path,
    config: dict[str, Any],
    *,
    state_dir: Path | str | None = None,
    recent_observations: list[Mapping[str, Any]] | None = None,
    capturer: Callable[[str], dict[str, Any]],
) -> list[dict[str, Any]]:
    target_source = config.get(
        "x_article_target_source", "state/x-article-targets.json"
    )
    target_file = (
        _state_path(skill_dir, state_dir, target_source)
        if isinstance(target_source, str)
        else None
    )
    recent_target_limit = config.get("x_article_target_limit", X_TARGET_LIMIT)
    if (
        not isinstance(recent_target_limit, int)
        or isinstance(recent_target_limit, bool)
        or not 1 <= recent_target_limit <= 50
    ):
        raise DemandObservationError("x_article_target_limit must be between 1 and 50")
    recent_targets = _recent_x_targets(
        recent_observations,
        limit=recent_target_limit,
    )
    if (
        target_file is not None
        and not target_file.exists()
        and not recent_targets
    ):
        durable = _load_x_article_observations(skill_dir, config, state_dir)
        if durable:
            return durable
    urls = _target_urls(
        skill_dir,
        config,
        state_dir=state_dir,
        recent_observations=recent_observations,
    )
    prior_payload = _load_x_article_receipt(skill_dir, config, state_dir)
    prior_observations = (
        list(prior_payload["observations"])
        if prior_payload is not None
        else []
    )
    target_payload = _load_x_target_payload(target_file)
    verified_target_hash = _target_set_hash_from_file(target_file)
    candidate_set_hash = _target_set_sha256(recent_targets) if recent_targets else None
    prior_candidate_hash = (
        target_payload.get("candidate_set_sha256")
        if isinstance(target_payload, dict)
        else None
    )
    prior_urls = {
        str(row.get("source_url"))
        for row in prior_observations
        if isinstance(row.get("source_url"), str)
    }
    candidate_verdicts = (
        target_payload.get("candidate_verdicts", {})
        if isinstance(target_payload, dict)
        else {}
    )
    if not isinstance(candidate_verdicts, dict):
        candidate_verdicts = {}
    prior_failed_urls = {
        str(url)
        for url, verdict in candidate_verdicts.items()
        if isinstance(verdict, dict)
        and verdict.get("status") in {"rejected", "failed", "skipped"}
    }

    # A dynamic candidate manifest is not a verified target set.  Once every URL in
    # the same manifest has a durable capture verdict, do not recapture it on each
    # launch.  Failed candidates remain receipted and are skipped until discovery
    # produces a different bounded manifest.
    if recent_targets and prior_candidate_hash == candidate_set_hash:
        if prior_observations and verified_target_hash == candidate_set_hash:
            urls = []
        else:
            failed_urls = {
                str(url)
                for url, verdict in candidate_verdicts.items()
                if isinstance(verdict, dict)
                and verdict.get("status") in {"rejected", "failed", "skipped"}
            }
            urls = [url for url in urls if url not in failed_urls and url not in prior_urls]
        if not urls and prior_observations:
            urls = []
        elif not urls:
            # No verified body exists yet; use configured bootstrap targets rather
            # than repeatedly retrying the same failed live candidates.
            bootstrap = [config.get("x_article_urls", []), config.get("x_article_seed_urls", [])]
            urls = [
                url.strip()
                for source in bootstrap
                if isinstance(source, list)
                for url in source
                if isinstance(url, str) and url.strip()
            ]
    elif (
        not recent_targets
        and verified_target_hash
        and prior_payload is not None
        and prior_payload.get("target_set_sha256") == verified_target_hash
        and prior_observations
    ):
        urls = []
    elif recent_targets and prior_failed_urls:
        urls = [url for url in urls if url not in prior_failed_urls]

    # Reuse a verified body set without invoking the browser.  The capture receipt
    # still records this wake so operators can distinguish reuse from a fresh capture.
    receipt_path = config.get(
        "x_article_capture_receipt", "state/x-article-capture-latest.json"
    )
    if not isinstance(receipt_path, str) or Path(receipt_path).is_absolute():
        raise DemandObservationError("x_article_capture_receipt must be relative")
    verified_bootstrap = _load_verified_bootstrap_observations(
        skill_dir, config, state_dir
    )
    candidate_urls = {target["url"] for target in recent_targets}
    if (
        verified_bootstrap
        and recent_targets
        and not prior_observations
        and candidate_urls <= prior_failed_urls
    ):
        # This exact candidate manifest already has durable rejected verdicts.  Do
        # not turn a known failure into another seed capture; reuse the verified
        # bootstrap evidence before adding any fallback URLs.
        urls = []
    if (
        not urls
        and verified_bootstrap
        and recent_targets
        and not prior_observations
        and candidate_urls <= prior_failed_urls
    ):
        _atomic_json(
            _state_path(skill_dir, state_dir, receipt_path),
            {
                "version": 1,
                "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "attempted": [],
                "captured": [row["source_url"] for row in verified_bootstrap],
                "captured_identity": {
                    row["source_url"]: row["rendered_identity"]
                    for row in verified_bootstrap
                    if isinstance(row.get("rendered_identity"), Mapping)
                },
                "captured_observations": verified_bootstrap,
                "skipped": [],
                "reused": True,
                "fallback": "verified-bootstrap",
                "candidate_targets": recent_targets,
                "candidate_set_sha256": candidate_set_hash,
            },
        )
        return verified_bootstrap
    if not urls and prior_observations:
        _atomic_json(
            _state_path(skill_dir, state_dir, receipt_path),
            {
                "version": 1,
                "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "attempted": [],
                "captured": [row["source_url"] for row in prior_observations],
                "skipped": [],
                "reused": True,
                "target_set_sha256": verified_target_hash,
                "candidate_set_sha256": candidate_set_hash,
            },
        )
        return prior_observations
    observations: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    def capture_one(url: str) -> dict[str, Any] | None:
        try:
            receipt = _capture_with_article_daily_lock(
                skill_dir,
                config,
                url,
                capturer,
                state_dir,
            )
        except (XArticleCaptureError, OSError, RuntimeError) as error:
            skipped.append({"url": url, "reason": str(error)})
            return None
        if not isinstance(receipt, dict):
            skipped.append({"url": url, "reason": "capture receipt is not an object"})
            return None
        body = receipt.get("full_body")
        source_url = receipt.get("source_url", url)
        source_sha256 = receipt.get("source_sha256")
        rendered_identity = _validated_rendered_identity(
            receipt,
            url=url,
            body=body if isinstance(body, str) else "",
        ) if isinstance(body, str) else None
        if (
            source_url != url
            or not isinstance(body, str)
            or not body.strip()
            or not isinstance(source_sha256, str)
            or SHA256_RE.fullmatch(source_sha256.lower()) is None
            or hashlib.sha256(body.encode("utf-8")).hexdigest() != source_sha256.lower()
            or receipt.get("capture_method") != "rendered_cdp_dom"
            or rendered_identity is None
        ):
            skipped.append({"url": url, "reason": "capture receipt failed compound Article identity/hash validation"})
            return None
        return {
            "observation_id": f"x-article:{receipt.get('target_id') or url.rsplit('/', 1)[-1]}",
            "source_family": "reader_demand",
            "source_url": source_url,
            "article_identity": receipt.get("article_identity"),
            "target_id": receipt.get("target_id"),
            "source_sha256": source_sha256,
            "full_body": body,
            "capture_method": receipt.get("capture_method"),
            "captured_at": receipt.get("captured_at"),
            "rendered_identity": rendered_identity,
        }

    for url in urls:
        captured = capture_one(url)
        if captured is not None:
            observations.append(captured)
    if recent_targets and target_file is not None:
        captured_urls = {str(row["source_url"]) for row in observations}
        identity_by_url = {
            str(row["source_url"]): row["rendered_identity"]
            for row in observations
            if isinstance(row.get("rendered_identity"), Mapping)
        }
        success_targets = [
            {
                **target,
                "rendered_identity": identity_by_url[target["url"]],
            }
            for target in recent_targets
            if target["url"] in captured_urls and target["url"] in identity_by_url
        ]
        verdicts: dict[str, dict[str, Any]] = {}
        skipped_by_url = {row["url"]: row["reason"] for row in skipped}
        for target in recent_targets:
            url = target["url"]
            if url in captured_urls:
                verdicts[url] = {"status": "captured"}
            else:
                reason = skipped_by_url.get(
                    url,
                    (
                        candidate_verdicts.get(url, {}).get("reason")
                        if isinstance(candidate_verdicts.get(url), dict)
                        else None
                    )
                    or "capture did not return a valid receipt",
                )
                verdicts[url] = {
                    "status": (
                        "pending"
                        if "article-daily publication lock held" in reason
                        else "rejected"
                    ),
                    "reason": reason,
                }
        _atomic_json(
            target_file,
            {
                "version": 1,
                "targets": success_targets,
                "target_set_sha256": _target_set_sha256(success_targets),
                "candidate_targets": recent_targets,
                "candidate_set_sha256": candidate_set_hash,
                "candidate_verdicts": verdicts,
            },
        )
    _atomic_json(
        _state_path(skill_dir, state_dir, receipt_path),
        {
            "version": 1,
            "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "attempted": urls,
            "captured": [row["source_url"] for row in observations],
            "captured_identity": {
                row["source_url"]: row["rendered_identity"]
                for row in observations
                if isinstance(row.get("rendered_identity"), Mapping)
            },
            "skipped": skipped,
            "pending": any(
                "article-daily publication lock held" in row["reason"]
                for row in skipped
            ),
            "candidate_targets": recent_targets,
            "candidate_set_sha256": candidate_set_hash,
        },
    )
    if not observations and skipped and recent_targets and not prior_observations:
        if verified_bootstrap:
            _atomic_json(
                _state_path(skill_dir, state_dir, receipt_path),
                {
                    "version": 1,
                    "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "attempted": urls,
                    "captured": [row["source_url"] for row in verified_bootstrap],
                    "captured_identity": {
                        row["source_url"]: row["rendered_identity"]
                        for row in verified_bootstrap
                        if isinstance(row.get("rendered_identity"), Mapping)
                    },
                    "captured_observations": verified_bootstrap,
                    "skipped": skipped,
                    "reused": True,
                    "fallback": "verified-bootstrap",
                    "candidate_targets": recent_targets,
                    "candidate_set_sha256": candidate_set_hash,
                },
            )
            return verified_bootstrap
        bootstrap = [config.get("x_article_urls", []), config.get("x_article_seed_urls", [])]
        bootstrap_urls = [
            url.strip()
            for source in bootstrap
            if isinstance(source, list)
            for url in source
            if isinstance(url, str) and url.strip() and url.strip() not in urls
        ]
        for url in bootstrap_urls:
            captured = capture_one(url)
            if captured is not None:
                observations.append(captured)
        if observations:
            # Bootstrap successes are verified bodies too, but are kept separate
            # from the live candidate manifest until a demand card commits them.
            _atomic_json(
                _state_path(skill_dir, state_dir, receipt_path),
                {
                    "version": 1,
                    "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "attempted": [*urls, *bootstrap_urls],
                    "captured": [row["source_url"] for row in observations],
                    "captured_identity": {
                        row["source_url"]: row["rendered_identity"]
                        for row in observations
                        if isinstance(row.get("rendered_identity"), Mapping)
                    },
                    "captured_observations": observations,
                    "skipped": skipped,
                    "pending": any(
                        "article-daily publication lock held" in row["reason"]
                        for row in skipped
                    ),
                    "fallback": "bootstrap",
                    "candidate_targets": recent_targets,
                    "candidate_set_sha256": candidate_set_hash,
                },
            )
            return observations
    if not observations and prior_observations:
        _atomic_json(
            _state_path(skill_dir, state_dir, receipt_path),
            {
                "version": 1,
                "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "attempted": urls,
                "captured": [row["source_url"] for row in prior_observations],
                "skipped": skipped,
                "reused": True,
                "fallback": True,
                "target_set_sha256": verified_target_hash,
                "candidate_targets": recent_targets,
                "candidate_set_sha256": candidate_set_hash,
            },
        )
        return prior_observations
    if (
        not observations
        and skipped
        and not prior_observations
        and all("article-daily publication lock held" in row["reason"] for row in skipped)
    ):
        # Publication owns the live browser right now.  Keep this wake retryable;
        # do not turn a temporary lock into a permanent candidate rejection.
        return []
    if not observations and skipped:
        raise DemandObservationError(
            "all X Article captures failed: " + ",".join(row["url"] for row in skipped)
        )
    return observations


def _demand_summary(observations: list[dict[str, Any]]) -> dict[str, Any]:
    body_hashes = []
    for row in observations:
        body = row.get("full_body")
        if isinstance(body, str) and body.strip():
            body_hashes.append(hashlib.sha256(body.strip().encode("utf-8")).hexdigest())
    return {
        "observations": len(observations),
        "families": sorted({str(row.get("source_family")) for row in observations}),
        "body_sha256": sorted(set(body_hashes)),
        "source_sha256": sorted(
            {str(row.get("source_sha256")) for row in observations if row.get("source_sha256")}
        ),
    }


def run_loop(
    skill_dir: Path | str,
    *,
    state_dir: Path | str | None = None,
    now: str,
    watcher: Callable[..., dict[str, Any]] = run_watch,
    refiller: Callable[..., dict[str, Any]] = refill_queue,
    chooser: Callable[[list[dict[str, Any]]], dict[str, Any]],
    floor: int = 3,
    demand_reader: Callable[[Path], list[dict[str, Any]]] | None = None,
    demand_bindings: dict[str, Any] | None = None,
    demand_chooser: Callable[
        [list[dict[str, Any]], list[dict[str, Any]]], dict[str, Any]
    ] | None = None,
    x_article_capturer: Callable[[str], dict[str, Any]] = capture_x_article_body,
) -> dict[str, Any]:
    skill_dir = Path(skill_dir)
    state = Path(state_dir) if state_dir is not None else skill_dir / "state"
    observed_at = now
    config = json.loads((skill_dir / "config/claim-watch.json").read_text(encoding="utf-8")) \
        if watcher is run_watch else {"version": 1, "sources": []}
    watch = watcher(
        config,
        state / "claims.sqlite3",
        state / "claim-watch-latest.json",
        observed_at=observed_at,
    )
    demand_mode = "required" if config.get("demand_mode") == "required" or demand_reader else "legacy-migration"
    effective_floor = 1 if demand_mode == "required" else floor
    demand_error = None
    demand_rows: list[dict[str, Any]] | None = None
    x_article_rows: list[dict[str, Any]] = []
    if demand_mode == "required":
        try:
            raw_demand_rows = list((demand_reader or _default_demand_reader)(state))
            if demand_reader is None and config.get("demand_source_id"):
                configured_rows = configured_full_body_observations(
                    skill_dir,
                    config,
                    observed_at=observed_at,
                    state_dir=state,
                )
                configured_urls = {
                    str(row.get("source_url"))
                    for row in configured_rows
                    if isinstance(row.get("source_url"), str)
                }
                # Replace any stale OpportunityStore/excerpt row for the same
                # canonical page; two full bodies at one URL cannot coexist in a
                # demand card, and the fresh capture is the authoritative receipt.
                raw_demand_rows = [
                    row
                    for row in raw_demand_rows
                    if row.get("source_url") not in configured_urls
                ]
                raw_demand_rows.extend(configured_rows)
            # A normal X status is a capture candidate, never demand evidence.  Keep
            # pre-verified reader_demand Article receipts, but strip all other X rows
            # before building the paid-demand card.
            unverified_x_rows = [
                row
                for row in raw_demand_rows
                if isinstance(row, Mapping)
                and _x_observation_url(row) is not None
                and row.get("source_family") != "reader_demand"
            ]
            demand_rows = [row for row in raw_demand_rows if row not in unverified_x_rows]
            x_candidate_rows = _recent_x_claim_candidates(
                state / "claims.sqlite3",
                limit=config.get("x_article_target_limit", X_TARGET_LIMIT),
            )
            x_article_rows = _x_article_observations(
                skill_dir,
                config,
                state_dir=state,
                # X ClaimStore rows are bounded capture candidates only; they are
                # appended to demand rows after the authenticated Article verifier.
                recent_observations=[*demand_rows, *x_candidate_rows, *unverified_x_rows],
                capturer=x_article_capturer,
            )
            demand_rows.extend(x_article_rows)
        except DemandObservationError as error:
            demand_rows = []
            demand_error = str(error)
    refill_kwargs = {
        "floor": effective_floor,
        "chooser": chooser,
        "now": observed_at,
    }
    if demand_mode == "required":
        refill_kwargs.update(
            {
                "demand_observations": demand_rows,
                "demand_bindings": demand_bindings or config.get("demand_bindings"),
                "demand_mode": "required",
            }
        )
        if demand_chooser is not None:
            refill_kwargs["demand_chooser"] = demand_chooser
    supply = refiller(
        state / "claims.sqlite3",
        state / "topics/queue",
        state / "claim-supply-latest.json",
        **refill_kwargs,
    )
    if demand_mode == "required" and x_article_rows:
        try:
            _commit_x_article_observations(
                skill_dir,
                config,
                x_article_rows,
                state_dir=state,
                supply=supply,
            )
        except DemandObservationError as error:
            demand_error = str(error)
    supply_ready = supply.get("status") in {"FILLED", "SUFFICIENT"}
    source_ok = int(watch.get("totals", {}).get("ok", 0))
    if supply_ready:
        status = "READY" if source_ok else "READY_WITH_SOURCE_OUTAGE"
    else:
        status = str(supply.get("status") or "SUPPLY_FAILED")
    receipt = {
        "version": 1,
        "observed_at": observed_at,
        "status": status,
        "watch": watch,
        "supply": supply,
        "demand": {
            "mode": demand_mode,
            **_demand_summary(demand_rows or []),
        },
    }
    if demand_error:
        receipt["demand"]["error"] = demand_error
    _atomic_json(state / "claim-loop-latest.json", receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, default=SCRIPT_DIR.parent)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--floor", type=int, default=3)
    parser.add_argument(
        "--now",
        default=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args(argv)
    now = args.now() if callable(args.now) else args.now
    state = args.state_dir or args.skill_dir / "state"
    state.mkdir(parents=True, exist_ok=True)
    lock_path = state / ".claim-loop.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"status": "LOCK_BUSY", "observed_at": now}, sort_keys=True))
            return 0
        runner = args.skill_dir / "runtime/model-runner.sh"
        run_id = f"claim-loop-{str(now).replace(':', '').replace('-', '')}"
        receipt = run_loop(
            args.skill_dir,
            state_dir=state,
            now=now,
            floor=args.floor,
            chooser=lambda rows: model_choose(rows, runner=runner, run_id=run_id),
            demand_chooser=lambda rows, observations: model_choose(
                rows,
                runner=runner,
                run_id=run_id,
                demand_observations=observations,
            ),
        )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if receipt["status"] in {"READY", "READY_WITH_SOURCE_OUTAGE"} else 75


if __name__ == "__main__":
    raise SystemExit(main())
