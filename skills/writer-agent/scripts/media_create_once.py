#!/usr/bin/env python3
"""Atomically promote one valid generated image into an immutable run path."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

class MediaCreateRefused(ValueError):
    """The immutable destination already belongs to another candidate."""


REQUIRED_ASSETS: list[dict[str, str]] = [
    {
        "kind": "headline",
        "destination": "headline-image.png",
        "receipt": "gates/headline-image-create.json",
    },
    {
        "kind": "body",
        "destination": "body-diagram.png",
        "receipt": "gates/body-diagram-create.json",
    },
]


def _descriptor_from_file(path: Path) -> dict[str, object]:
    # Arming happens before generation and must not require Pillow. Image decoding
    # is imported only for commit/verify, where valid pixel evidence is mandatory.
    from media_integrity import descriptor_from_file

    return descriptor_from_file(path)


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _install_independent_copy_once(source: Path, target: Path) -> None:
    """Atomically install bytes without leaving a mutable hard-link alias."""
    temporary = target.with_name(f".{target.name}.{os.getpid()}.media-tmp")
    try:
        with source.open("rb") as input_handle, temporary.open("xb") as output_handle:
            shutil.copyfileobj(input_handle, output_handle)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        os.link(temporary, target)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def arm(run_dir: Path) -> dict[str, object]:
    run = run_dir.resolve(strict=True)
    gates = (run / "gates").resolve(strict=True)
    marker = gates / "media-create-required.json"
    payload: dict[str, object] = {
        "version": 1,
        "status": "required",
        "assets": REQUIRED_ASSETS,
    }
    if marker.exists():
        try:
            recorded = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise MediaCreateRefused("media-create-marker-invalid") from error
        if recorded != payload:
            raise MediaCreateRefused("media-create-marker-mismatch")
        return payload
    _atomic_json(marker, payload)
    return payload


def _read_json(path: Path, reason: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise MediaCreateRefused(reason) from error
    if not isinstance(payload, dict):
        raise MediaCreateRefused(reason)
    return payload


def verify(run_dir: Path) -> dict[str, object]:
    run = run_dir.resolve(strict=True)
    marker = _read_json(
        run / "gates/media-create-required.json",
        "media-create-marker-invalid",
    )
    expected_marker: dict[str, object] = {
        "version": 1,
        "status": "required",
        "assets": REQUIRED_ASSETS,
    }
    if marker != expected_marker:
        raise MediaCreateRefused("media-create-marker-mismatch")
    for asset in REQUIRED_ASSETS:
        destination = run / asset["destination"]
        receipt = _read_json(run / asset["receipt"], "media-create-receipt-invalid")
        descriptor = _descriptor_from_file(destination)
        if not all(
            isinstance(descriptor.get(field), int) and int(descriptor[field]) > 0
            for field in ("byte_length", "width", "height")
        ):
            raise MediaCreateRefused(f"media-create-asset-invalid:{asset['kind']}")
        if asset["kind"] == "body" and int(descriptor["height"]) < 110:
            raise MediaCreateRefused("media-create-body-too-flat-for-x")
        expected_receipt: dict[str, object] = {
            "version": 1,
            "status": "committed",
            "kind": asset["kind"],
            "destination": str(destination),
            "sha256": str(descriptor["sha256"]),
            "byte_length": int(descriptor["byte_length"]),
            "width": int(descriptor["width"]),
            "height": int(descriptor["height"]),
        }
        if receipt != expected_receipt:
            raise MediaCreateRefused(f"media-create-receipt-mismatch:{asset['kind']}")
    return {"version": 1, "status": "verified", "assets_verified": 2}


def commit(candidate: Path, destination: Path, receipt: Path, kind: str) -> dict[str, object]:
    source = candidate.resolve(strict=True)
    target = destination.parent.resolve(strict=True) / destination.name
    descriptor = _descriptor_from_file(source)
    if not all(
        isinstance(descriptor.get(field), int) and int(descriptor[field]) > 0
        for field in ("byte_length", "width", "height")
    ):
        raise MediaCreateRefused("candidate-not-decodable-image")
    if kind == "body" and int(descriptor["height"]) < 110:
        raise MediaCreateRefused("candidate-body-too-flat-for-x")
    payload: dict[str, object] = {
        "version": 1,
        "status": "committed",
        "kind": kind,
        "destination": str(target),
        "sha256": str(descriptor["sha256"]),
        "byte_length": int(descriptor["byte_length"]),
        "width": int(descriptor["width"]),
        "height": int(descriptor["height"]),
    }
    try:
        _install_independent_copy_once(source, target)
    except FileExistsError as error:
        target_descriptor = _descriptor_from_file(target)
        if target_descriptor.get("sha256") != descriptor.get("sha256"):
            raise MediaCreateRefused("canonical-media-already-committed") from error
        if receipt.exists():
            try:
                recorded = json.loads(receipt.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError) as receipt_error:
                raise MediaCreateRefused("canonical-media-receipt-invalid") from receipt_error
            if recorded != payload:
                raise MediaCreateRefused("canonical-media-receipt-mismatch")
    _atomic_json(receipt, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    arm_parser = subparsers.add_parser("arm")
    arm_parser.add_argument("--run-dir", required=True, type=Path)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--run-dir", required=True, type=Path)
    commit_parser = subparsers.add_parser("commit")
    commit_parser.add_argument("--candidate", required=True, type=Path)
    commit_parser.add_argument("--destination", required=True, type=Path)
    commit_parser.add_argument("--receipt", required=True, type=Path)
    commit_parser.add_argument("--kind", required=True, choices=("headline", "body"))
    args = parser.parse_args()
    try:
        if args.command == "arm":
            payload = arm(args.run_dir)
        elif args.command == "verify":
            payload = verify(args.run_dir)
        else:
            payload = commit(args.candidate, args.destination, args.receipt, args.kind)
    except MediaCreateRefused as error:
        print(
            json.dumps(
                {"status": "refused", "reason": str(error)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
