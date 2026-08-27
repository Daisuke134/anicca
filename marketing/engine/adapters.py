"""Load side-effect adapters without importing producer implementations."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class ProducerAdapter:
    id: str
    channel_id: str
    form: str
    craft_file: Path
    launchd_labels: tuple[str, ...]
    artifact_media_type: str
    publication_receipt_schema: Path


def _inside(base: Path, relative: str, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"{label} path is required")
    base = base.resolve()
    candidate = (base / relative).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"{label} must stay inside its declared root")
    return candidate


def load_producer(
    *,
    registry_root: Path,
    producer_id: str,
) -> ProducerAdapter:
    """Load one producer's launch boundary as data."""

    if not isinstance(producer_id, str) or _ID.fullmatch(producer_id) is None:
        raise ValueError("invalid producer_id")
    registry_root = Path(registry_root).resolve()
    producer_root = (
        registry_root / "channels" / "video" / "producers" / producer_id
    )
    manifest_path = producer_root / "producer.toml"
    if not manifest_path.is_file():
        raise ValueError(f"missing producer manifest: {manifest_path}")
    with manifest_path.open("rb") as handle:
        manifest = tomllib.load(handle)

    if manifest.get("id") != producer_id:
        raise ValueError("producer manifest identity mismatch")
    if manifest.get("channel_id") != "video":
        raise ValueError("producer channel must be video")
    form = manifest.get("form")
    if not isinstance(form, str) or not form:
        raise ValueError("producer form is required")
    labels = manifest.get("launchd_labels")
    if (
        not isinstance(labels, list)
        or not labels
        or any(
            not isinstance(item, str) or not item.startswith("ai.anicca.")
            for item in labels
        )
        or len(labels) != len(set(labels))
    ):
        raise ValueError("launchd_labels must be unique ai.anicca labels")
    media_type = manifest.get("artifact_media_type")
    if media_type != "video/mp4":
        raise ValueError("video producer artifact_media_type must be video/mp4")

    craft_file = _inside(
        producer_root,
        manifest.get("craft"),
        label="craft",
    )
    receipt_schema = _inside(
        registry_root,
        manifest.get("publication_receipt_schema"),
        label="publication receipt schema",
    )
    if not craft_file.is_file():
        raise ValueError(f"missing producer craft: {craft_file}")
    if not receipt_schema.is_file():
        raise ValueError(f"missing publication schema: {receipt_schema}")

    return ProducerAdapter(
        id=producer_id,
        channel_id="video",
        form=form,
        craft_file=craft_file,
        launchd_labels=tuple(labels),
        artifact_media_type=media_type,
        publication_receipt_schema=receipt_schema,
    )


def kickstart_command(
    adapter: ProducerAdapter,
    label: str,
    *,
    uid: int,
) -> tuple[str, ...]:
    """Return the native trigger only for a label declared by the adapter."""

    if label not in adapter.launchd_labels:
        raise ValueError("launchd label is not declared by producer")
    if not isinstance(uid, int) or uid < 0:
        raise ValueError("uid must be a non-negative integer")
    return (
        "launchctl",
        "kickstart",
        "-k",
        f"gui/{uid}/{label}",
    )


def adapter_health(
    adapter: ProducerAdapter,
    *,
    available_labels: set[str],
) -> dict[str, object]:
    """Compare declared labels with an observed launchd label set."""

    present = sorted(set(adapter.launchd_labels) & available_labels)
    missing = sorted(set(adapter.launchd_labels) - available_labels)
    return {
        "producer_id": adapter.id,
        "status": "pass" if not missing else ("missing" if not present else "partial"),
        "present": present,
        "missing": missing,
    }
