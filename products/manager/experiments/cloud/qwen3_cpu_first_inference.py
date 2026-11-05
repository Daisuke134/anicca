"""BFM-01: attest a *real* cloud CPU inference on an existing open Qwen3 model.

This does NOT run the gated Be.FM LoRA and does NOT produce human-benchmark
accuracy or identify behavior-change causality. Synthetic nonpersonal prompt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BASE_MODEL = "Qwen/Qwen3-4B-Instruct-2507"
QUANTIZED_MODEL = "bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF"
HF_REVISION = "ae44f08e1392f39c0e474af10c3ff8355c8b6688"
HF_FILENAME = "Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
GGUF_SHA256 = "2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e"
LLAMA_CPP_TAG = "b12137"
LLAMA_ARCHIVE_SHA256 = "d9be8922022f26524efe5af7449b50414f0fc781e9b740042e4af7e50e511525"

STUDY_PROMPT = (
    "<|im_start|>user\n"
    "In a fictional one-round anonymous dictator game, you receive ten "
    "tokens and can transfer any integer from 0 to 10 to another player. "
    "What number of tokens do you transfer? Answer only the integer.\n"
    "<|im_end|>\n<|im_start|>assistant\n"
)


def receipt(stdout: str, duration_seconds: int, model_sha256: str) -> dict:
    """Record exactly what was run; never turn an example into a science score."""
    if duration_seconds < 0:
        raise ValueError("duration cannot be negative")
    if model_sha256 != GGUF_SHA256:
        raise ValueError("unexpected GGUF hash")
    if not stdout.strip():
        raise ValueError("empty inference transcript; do not claim success")
    return {
        "kind": "actual_open_model_cpu_inference_not_human_benchmark",
        "inference_executed": True,
        "quantized_model": QUANTIZED_MODEL,
        "original_base_model": BASE_MODEL,
        "huggingface_revision": HF_REVISION,
        "gguf_file": HF_FILENAME,
        "gguf_sha256_verified": model_sha256,
        "llama_cpp_release": LLAMA_CPP_TAG,
        "llama_cpp_release_sha256": LLAMA_ARCHIVE_SHA256,
        "compute": "GitHub Actions ubuntu-24.04 CPU (no dedicated GPU)",
        "duration_seconds": duration_seconds,
        "prompt": STUDY_PROMPT,
        "stdout_excerpt": stdout[-4500:],
        "behavior_prediction_accuracy_measured": False,
        "be_fm_adapter_loaded": False,
        "manager_model_trained": False,
        "causal_effect_measured": False,
        "user_intervention_performed": False,
        "human_participant_data_used": False,
        "warning": "Single synthetic example. No observed human behavior, no benchmark accuracy.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Attest real Qwen3 CPU inference.")
    parser.add_argument("--stdout", required=True)
    parser.add_argument("--duration", type=int, required=True)
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    transcript = Path(args.stdout).read_text(encoding="utf-8", errors="replace")
    result = receipt(transcript, args.duration, args.model_sha256)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "model": QUANTIZED_MODEL,
        "real_inference": True,
        "duration_seconds": args.duration,
        "model_sha256": args.model_sha256,
        "human_benchmark_scored": False,
        "adapter_loaded": False,
    }))


if __name__ == "__main__":
    main()
