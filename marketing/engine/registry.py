"""Compose isolated product, channel, and learning-slice contracts."""

from __future__ import annotations

import re
import json
import os
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    audience: tuple[str, ...]
    pain: str
    promise: str
    proof: tuple[str, ...]
    offer: str


@dataclass(frozen=True)
class Attribution:
    landing_url: str
    start_url: str
    activation_predicate: str
    paid_predicate: str
    join_keys: tuple[str, ...]


@dataclass(frozen=True)
class Campaign:
    product_id: str
    channel_id: str
    slice_name: str
    reward: str
    opponent_file: Path
    weight_seed_file: Path
    weight_file: Path
    product: Product
    attribution: Attribution

    @property
    def scope(self) -> str:
        return f"{self.product_id}/{self.channel_id}/{self.slice_name}"


def _read_toml(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"missing manifest: {path}")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _validate_id(label: str, value: str) -> None:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ValueError(f"invalid {label}: {value!r}")


def _inside(base: Path, relative: str, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"{label} path is required")
    base = base.resolve()
    candidate = (base / relative).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError(f"{label} must stay inside product pack")
    return candidate


def _required_text(manifest: dict, field: str) -> str:
    value = manifest.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    return value


def _required_texts(manifest: dict, field: str) -> tuple[str, ...]:
    value = manifest.get(field)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise ValueError(f"{field} must be a non-empty string array")
    return tuple(value)


def load_campaign(
    *,
    registry_root: Path,
    product_id: str,
    channel_id: str,
    slice_name: str,
    runtime_root: Path,
) -> Campaign:
    """Load one scope without importing any product or channel implementation."""

    for label, value in (
        ("product_id", product_id),
        ("channel_id", channel_id),
        ("slice_name", slice_name),
    ):
        _validate_id(label, value)

    registry_root = Path(registry_root).resolve()
    runtime_root = Path(runtime_root).resolve()
    product_root = registry_root / "products" / product_id
    channel_root = registry_root / "channels" / channel_id
    product = _read_toml(product_root / "product.toml")
    attribution_manifest = _read_toml(product_root / "attribution.toml")
    channel = _read_toml(channel_root / "channel.toml")
    rewards = _read_toml(product_root / "rewards.toml")

    if product.get("id") != product_id:
        raise ValueError("product manifest identity mismatch")
    if channel.get("id") != channel_id:
        raise ValueError("channel manifest identity mismatch")
    if slice_name not in channel.get("slices", []):
        raise ValueError("slice is not declared by channel")

    try:
        contract = rewards[channel_id][slice_name]
    except (KeyError, TypeError) as error:
        raise ValueError("missing product/channel/slice reward contract") from error
    if not isinstance(contract, dict):
        raise ValueError("reward contract must be a table")

    reward = contract.get("reward")
    if not isinstance(reward, str) or not reward:
        raise ValueError("reward is required")
    product_contract = Product(
        id=product_id,
        name=_required_text(product, "name"),
        audience=_required_texts(product, "audience"),
        pain=_required_text(product, "pain"),
        promise=_required_text(product, "promise"),
        proof=_required_texts(product, "proof"),
        offer=_required_text(product, "offer"),
    )
    attribution = Attribution(
        landing_url=_required_text(attribution_manifest, "landing_url"),
        start_url=_required_text(attribution_manifest, "start_url"),
        activation_predicate=_required_text(
            attribution_manifest,
            "activation_predicate",
        ),
        paid_predicate=_required_text(attribution_manifest, "paid_predicate"),
        join_keys=_required_texts(attribution_manifest, "join_keys"),
    )
    expected_keys = (
        "product_id",
        "run_id",
        "artifact_id",
        "variant_id",
        "click_id",
    )
    if attribution.join_keys != expected_keys:
        raise ValueError("attribution join_keys must use exact lineage order")
    if not (
        attribution.landing_url.startswith("https://")
        and attribution.start_url.startswith("https://")
    ):
        raise ValueError("attribution URLs must use https")
    opponent_file = _inside(
        product_root,
        contract.get("opponent"),
        label="opponent",
    )
    if not opponent_file.is_file():
        raise ValueError(f"missing opponent corpus: {opponent_file}")

    declared_weight = _inside(
        product_root,
        contract.get("weight"),
        label="weight",
    )
    expected_suffix = Path("weights") / channel_id / f"{slice_name}.json"
    if not declared_weight.as_posix().endswith(expected_suffix.as_posix()):
        raise ValueError(
            "weight declaration must match weights/<channel>/<slice>.json"
        )
    if not declared_weight.is_file():
        raise ValueError(f"missing weight seed: {declared_weight}")
    raw_weights = json.loads(declared_weight.read_text(encoding="utf-8"))
    if (
        not isinstance(raw_weights, dict)
        or not raw_weights
        or any(not isinstance(value, (int, float)) for value in raw_weights.values())
    ):
        raise ValueError("weight seed must be a non-empty numeric object")

    weight_file = (
        runtime_root
        / "products"
        / product_id
        / channel_id
        / slice_name
        / "weights.json"
    )
    return Campaign(
        product_id=product_id,
        channel_id=channel_id,
        slice_name=slice_name,
        reward=reward,
        opponent_file=opponent_file,
        weight_seed_file=declared_weight,
        weight_file=weight_file,
        product=product_contract,
        attribution=attribution,
    )


def materialize_weights(campaign: Campaign) -> dict[str, str]:
    """Create external runtime weights once; never overwrite learned state."""

    destination = campaign.weight_file
    if destination.exists():
        return {"status": "preserved", "weight_file": destination.as_posix()}
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = campaign.weight_seed_file.read_bytes()
    fd, temporary = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return {"status": "created", "weight_file": destination.as_posix()}
