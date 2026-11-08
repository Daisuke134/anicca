"""Generic GGUF forward-pass evaluation on the frozen BFM-02 MaMe-Re slice.

Runs ANY llama.cpp GGUF model (optionally with one GGUF LoRA adapter) on the
identical 24 held-out contexts, identical prompt text and identical scoring
as the BFM-02 Qwen3-4B pilot (qwen3_mame_text_eval); the chat-template
wrapper is each model family's native one (--prompt-format, recorded in the
receipt). Used for:
  * Minitaur-8B (Centaur family, full GGUF weights, non-gated), and
  * Be.FM 1.5-4B (LoRA adapter converted to GGUF, applied on top of the same
    pinned bartowski Qwen3-4B Q4_K_M GGUF artifact as BFM-02).

The receipt binds every number to the exact model/adapter bytes via SHA-256.
Cases, candidate selection, the train-prior baseline and score_pairs are
imported verbatim from qwen3_mame_text_eval; nothing about the benchmark
definition changes between models.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from qwen3_mame_text_eval import (
    build_cases,
    build_llama_command,
    parse_llama_reply,
    score_pairs,
    verify_sources,
)


CHATML_PREFIX = "<|im_start|>user\n"
CHATML_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n"


def rewrap_prompt(prompt: str, prompt_format: str) -> str:
    """Re-wrap the frozen BFM-02 prompt body in a model's native chat
    template. The Japanese instruction text is byte-identical for every
    model; only the control-token wrapper changes. ChatML is native to the
    Qwen family; Llama-3 models do not treat <|im_start|> as a control
    token, so feeding them ChatML measures the harness, not the model
    (BFM-05 canary, run 42491777987: exit 0, no parseable answer)."""
    if prompt_format == "chatml":
        return prompt
    if prompt_format == "llama3":
        assert prompt.startswith(CHATML_PREFIX) and prompt.endswith(
            CHATML_SUFFIX)
        body = prompt[len(CHATML_PREFIX):-len(CHATML_SUFFIX)]
        return ("<|begin_of_text|><|start_header_id|>user<|end_header_id|>"
                "\n\n" + body +
                "<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n")
    raise ValueError(f"unknown prompt format: {prompt_format}")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def command_for(cli: str, model: str, prompt: str, lora: Path | None,
                extra_flags: list[str] | None = None) -> list[str]:
    cmd = build_llama_command(cli, model, prompt)
    if lora is not None:
        cmd = cmd + ["--lora", str(lora)]
    if extra_flags:
        cmd = cmd + extra_flags
    return cmd


def run_cases(cases, cli: Path, model: Path, lora: Path | None,
              only_first: bool = False,
              extra_flags: list[str] | None = None,
              prompt_format: str = "chatml",
              keep_raw: bool = False) -> list[dict]:
    results = []
    todo = cases[:1] if only_first else cases
    for i, row in enumerate(todo):
        started = time.monotonic()
        prompt = rewrap_prompt(row["_prompt"], prompt_format)
        cmd = command_for(str(cli), str(model), prompt, lora,
                          extra_flags)
        proc = subprocess.run(cmd, text=True, encoding="utf-8",
                              errors="replace", stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=300)
        response = (parse_llama_reply(proc.stdout, expected_prompt=prompt)
                    if proc.returncode == 0 else None)
        item = {k: v for k, v in row.items() if k != "_prompt"}
        item.update({"model": response, "exit_code": proc.returncode,
                     "seconds": round(time.monotonic() - started, 3)})
        if keep_raw:
            item["stdout_tail"] = proc.stdout[-240:]
        results.append(item)
        print(json.dumps({"case": i + 1, "context_id": item["context_id"],
                          "response": response, "exit_code": proc.returncode,
                          "seconds": item["seconds"]}, ensure_ascii=False),
              flush=True)
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", required=True, type=Path)
    p.add_argument("--llama-cli", required=True, type=Path)
    p.add_argument("--model", required=True, type=Path)
    p.add_argument("--model-label", required=True)
    p.add_argument("--model-repo", required=True)
    p.add_argument("--lora", type=Path)
    p.add_argument("--adapter-label")
    p.add_argument("--adapter-repo")
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--n-cases", type=int, default=24)
    p.add_argument("--canary-only", action="store_true",
                   help="Run only the first frozen case and require a valid A/B")
    p.add_argument("--extra-flags", default="",
                   help="Comma-separated extra llama-cli flags (recorded)")
    p.add_argument("--prompt-format", choices=["chatml", "llama3"],
                   default="chatml",
                   help="Native chat template wrapper for the frozen prompt "
                        "text (recorded in the receipt)")
    args = p.parse_args()
    extra_flags = [f for f in args.extra_flags.split(",") if f]

    if not args.llama_cli.is_file() or not args.model.is_file():
        raise ValueError("llama-cli/model weights missing")
    if args.lora is not None and not args.lora.is_file():
        raise ValueError("lora adapter file missing")

    cases = build_cases(args.input_dir, n_cases=args.n_cases)
    scored = run_cases(cases, args.llama_cli, args.model, args.lora,
                       only_first=args.canary_only, extra_flags=extra_flags,
                       prompt_format=args.prompt_format,
                       keep_raw=args.canary_only)
    if args.canary_only:
        ok = len(scored) == 1 and scored[0]["model"] in ("A", "B")
        print(json.dumps({"canary_ok": ok, "answer": scored[0]["model"],
                          "stdout_tail": scored[0].get("stdout_tail")},
                         ensure_ascii=False))
        if not ok:
            raise SystemExit("canary failed: no valid A/B from model")
        return

    out = {
        "status": "REAL_GGUF_CPU_TEXT_ONLY_HUMAN_AGGREGATE_EVAL",
        "model_forward_pass_executed": True,
        "model_label": args.model_label,
        "model_repo": args.model_repo,
        "model_sha256": sha256_of(args.model),
        "model_bytes": args.model.stat().st_size,
        "adapter_label": args.adapter_label,
        "adapter_repo": args.adapter_repo,
        "adapter_sha256": sha256_of(args.lora) if args.lora else None,
        "adapter_bytes": args.lora.stat().st_size if args.lora else None,
        "llama_cpp_release": "b12137",
        "prompt_format": args.prompt_format,
        "extra_llama_flags": extra_flags,
        "n_cases": len(cases),
        "scores": score_pairs(scored),
        "cases": scored,
        "dataset": "CyberAgent AI Lab MaMe-Re",
        "file_sha256": verify_sources(args.input_dir),
        "holdout": ("frozen prior P09-5 context-disjoint 160 train/40 valid/50 "
                    "test; identical 24 selected heldout contexts, seed "
                    "20261107, identical prompts and scoring as BFM-02"),
        "wall_time_seconds": sum(x["seconds"] for x in scored),
        "limitation": ("24 context-level pilot; text-only (no manga images or "
                       "dialogue); the Japanese instruction text is identical "
                       "for every model, wrapped in each model family's "
                       "native chat template (prompt_format field); the "
                       "BFM-02 Qwen runs used the same text with ChatML"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": out["status"], "scores": out["scores"],
                      "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
