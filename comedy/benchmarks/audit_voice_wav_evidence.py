#!/usr/bin/env python3
"""Offline PCM-WAV evidence audit. Never claims to judge jokes, intelligibility, or voice compliance."""

from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import wave

CONFIG_KEYS = ("model_version", "skill_blob_sha", "script_blob_sha", "voice_mode",
               "mic_setup_id", "speaker_output_id")
HEX_SHA = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    """Read files in chunks to avoid loading an entire performance recording into RAM."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pcm_metrics(path: Path) -> dict:
    """Sample-domain diagnostics, not LUFS, SPL, ASR, or speech intelligibility."""
    with wave.open(str(path), "rb") as wav:
        channels, width = wav.getnchannels(), wav.getsampwidth()
        rate, frames = wav.getframerate(), wav.getnframes()
        if wav.getcomptype() != "NONE" or width != 2 or channels not in (1, 2):
            raise ValueError("unsupported_wav: require PCM 16-bit mono/stereo")
        if rate <= 0 or frames <= 0:
            raise ValueError("empty_or_invalid_wav")
        count, sumsq, peak, clipped = 0, 0, 0, 0
        while True:
            raw = wav.readframes(32768)
            if not raw:
                break
            values = array("h")
            values.frombytes(raw)
            if sys.byteorder != "little":
                values.byteswap()
            for value in values:
                count += 1
                sumsq += value * value
                peak = max(peak, abs(value))
                if value in (-32768, 32767):
                    clipped += 1
        if count != frames * channels:
            raise ValueError("truncated_wav")
    rms = math.sqrt(sumsq / count) / 32768
    return {
        "duration_s": round(frames / rate, 3),
        "sample_rate_hz": rate,
        "channels": channels,
        "sample_count": count,
        "rms_dbfs": round(20 * math.log10(rms), 2) if rms else None,
        "sample_peak_dbfs": round(20 * math.log10(peak / 32768), 2) if peak else None,
        "sample_clip_fraction": round(clipped / count, 8),
        "digital_silence": peak == 0,
    }


def audit(manifest: Path) -> dict:
    """Verify files against supplied SHA-256, distinguish synthetic from claimed rehearsals."""
    root = manifest.parent.resolve()
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    configurations: set[tuple] = set()
    audio_formats: set[tuple[int, int]] = set()
    items: list[dict] = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"line {index}: expected JSON object")
        tid = row.get("trial_id")
        if not isinstance(tid, str) or not tid or tid in seen_ids:
            raise ValueError(f"line {index}: missing/duplicate trial_id")
        seen_ids.add(tid)
        errors: list[str] = []
        origin = row.get("source_kind")
        if origin not in ("synthetic_fixture", "claimed_real_rehearsal"):
            errors.append("invalid_source_kind")
        rel = row.get("wav_path")
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
            errors.append("invalid_relative_path")
            file_path = None
        else:
            file_path = (root / rel).resolve()
            if not file_path.is_relative_to(root):
                errors.append("path_outside_manifest_dir")
                file_path = None
        announced = row.get("sha256")
        if not isinstance(announced, str) or not HEX_SHA.fullmatch(announced):
            errors.append("missing_or_invalid_sha256")
        for key in CONFIG_KEYS:
            if not isinstance(row.get(key), str) or not row[key].strip():
                errors.append(f"missing_config:{key}")
        if all(isinstance(row.get(k), str) and row[k] for k in CONFIG_KEYS):
            configurations.add(tuple(row[k] for k in CONFIG_KEYS))
        metrics = None
        actual = None
        if file_path is not None:
            if not file_path.is_file():
                errors.append("wav_not_found")
            else:
                actual = sha256_file(file_path)
                if actual != announced:
                    errors.append("sha256_mismatch")
                if actual in seen_hashes:
                    errors.append("duplicate_audio_bytes")
                seen_hashes.add(actual)
                try:
                    metrics = pcm_metrics(file_path)
                    audio_formats.add((metrics["sample_rate_hz"], metrics["channels"]))
                except (wave.Error, ValueError, EOFError, OSError) as exc:
                    errors.append(f"invalid_wav:{str(exc)[:80]}")
        items.append({
            "trial_id": tid,
            "source_kind_claimed": origin,
            "file": Path(rel).name if isinstance(rel, str) else None,
            "wav_sha256_computed": actual,
            "checks": "PASS" if not errors else "FAIL",
            "issues": errors,
            "sample_domain_metrics": metrics,
        })
    all_ok = bool(items) and all(x["checks"] == "PASS" for x in items)
    synthetic = sum(1 for x in items if x["source_kind_claimed"] == "synthetic_fixture")
    claimed_real = sum(1 for x in items if x["source_kind_claimed"] == "claimed_real_rehearsal")
    return {
        "schema_version": "1.0",
        "input_count": len(items),
        "verified_wav_count": sum(x["checks"] == "PASS" for x in items),
        "synthetic_fixture_count": synthetic,
        "claimed_real_rehearsal_count": claimed_real,
        "wav_byte_integrity": "PASS" if all_ok else "FAIL" if items else "NOT_MEASURED",
        "repeated_config_consistency": "CONSISTENT" if all_ok and len(configurations) == 1 and len(audio_formats) == 1
                                       else "DIFFERENT_CONFIGS" if len(configurations) > 1 or len(audio_formats) > 1
                                       else "NOT_MEASURED",
        "audio_origin_authenticity": "NOT_VERIFIED",
        "voice_reproducibility": "NOT_MEASURED",
        "opening_cue_compliance": "NOT_MEASURED",
        "phone_ai_role_understanding": "NOT_MEASURED",
        "audience_laughter": "NOT_MEASURED",
        "back_row_intelligibility": "NOT_MEASURED",
        "publication_enabled": False,
        "auto_reply_enabled": False,
        "items": items,
        "limitations": "RMS/peak/clipping are digital sample proxies; no LUFS, SPL, hearing test, speech recognition, human reaction or audience judgement.",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        result = audit(args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wav_integrity={result['wav_byte_integrity']} n={result['input_count']} "
          f"voice_reproducibility={result['voice_reproducibility']}")
    return 0 if result["wav_byte_integrity"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
