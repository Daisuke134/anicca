"""BFM-02: actual open Qwen3-4B model versus published human ratings of Japanese memes.

This benchmark has a *fixed, previously unused* set of 50 Japanese context IDs
from the prior Phase 9 experiment. We make a 24-context paired preference pilot
using *only CC-BY-4.0 text context, panel description and aggregate vote scores*.
Manga images and copyrighted manga dialogue are never used in model prompts.
Outcome: choose the candidate with a HIGHER independent 5-person binary-funny
fraction, not a directly observed human A/B comparison.

A real llama.cpp GGUF forward pass is optional in software tests, required for
the official BFM-02 GitHub cloud run. Invalid model answers count as losses.
Do not interpret this as Centaur or Be.FM inference, or as multimodal humor.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import subprocess
import time
import urllib.request
from pathlib import Path

SOURCE_COMMIT = "9e6eb0b7cc313e5a20ee8f059c7a23566dd60439"
SOURCE_BASE = f"https://raw.githubusercontent.com/CyberAgentAILab/mame-re/{SOURCE_COMMIT}/"
SOURCE_SHA256 = {
    "score.csv": "aad13533093fe9d2fcf80d0299c1abcaf751d3016e7d897b37604924abf56568",
    "context.csv": "9bcacaf1547ac95b4df9a1eb30b2d6013570c603322490a14678d79d4b1a41af",
    "image.csv": "4067278c6d6a03ad13fa61ab62befdf9010570e6984679c87aeb6fccfefcd326",
}
HERE = Path(__file__).resolve().parent
SPLIT_FILE = HERE / "data" / "mame_fixed_context_splits_v1.json"
GGUF_SHA256 = "2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e"
LLAMA_CPP_RELEASE = "b12137"
MODEL_NAME = "bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF"
SEED = 20261107
N_CASES = 24


def frozen_split(path: Path = SPLIT_FILE) -> tuple[list[int], list[int], list[int]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["upstream_commit"] != SOURCE_COMMIT:
        raise ValueError("split source commit differs")
    groups = [manifest[x] for x in (
        "train_context_ids", "validation_context_ids", "test_context_ids"
    )]
    if tuple(map(len, groups)) != (160, 40, 50):
        raise ValueError("split sizes changed")
    if sorted(int(i) for group in groups for i in group) != list(range(250)):
        raise ValueError("split must cover each original context once")
    return groups[0], groups[1], groups[2]


def download_pinned_text_data(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name, expected_sha in SOURCE_SHA256.items():
        path = folder / name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == expected_sha:
            continue
        req = urllib.request.Request(SOURCE_BASE + name, headers={"User-Agent": "Manager-BFM02-MaMe/0.1"})
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read(2_000_000)
        if hashlib.sha256(data).hexdigest() != expected_sha:
            raise ValueError(f"source bytes changed for {name}")
        path.write_bytes(data)


def verify_sources(folder: Path) -> dict:
    for name, expected_sha in SOURCE_SHA256.items():
        path = folder/name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
            raise ValueError(f"missing or incorrect source hash {name}")
    return SOURCE_SHA256.copy()


def human_preference(score_a: float, score_b: float) -> str | None:
    if not (0 <= score_a <= 1 and 0 <= score_b <= 1):
        raise ValueError("invalid score outside [0,1]")
    if score_a == score_b:
        return None
    return "A" if score_a > score_b else "B"


def pair_from_meta(prior_means: list[float], context_id: int, *,
                   seed: int, mode: str) -> tuple[int, int]:
    """Choose candidates from historical TRAIN ratings; zero test labels used."""
    if len(prior_means) < 10 or not all(math.isfinite(float(v)) for v in prior_means):
        raise ValueError("at least 10 finite historical item means required")
    if mode not in ("separated", "prior_close"):
        raise ValueError("unexpected pair selection rule")
    rng = random.Random(f"{seed}|{context_id}|{mode}")
    ranking = sorted(range(len(prior_means)), key=lambda j: (prior_means[j], j))
    n = len(ranking)
    bucket = max(2, n//5)
    if mode == "separated":
        a = rng.choice(ranking[:bucket])
        b = rng.choice(ranking[-bucket:])
    else:
        # adjacent historical popularities around median: no test labels used
        mid = ranking[2*bucket:3*bucket]
        pos = rng.randrange(len(mid)-1)
        a,b = mid[pos],mid[pos+1]
    if rng.random()<.5:
        a,b=b,a
    if a==b:raise AssertionError("candidate self-comparison")
    return a,b


def prompt_from_text_only(context: str, desc_a: str, desc_b: str) -> str:
    """No images, dialogue, historical ratings, hidden future outcomes or identities."""
    if not all(isinstance(x,str) and x.strip() for x in (context,desc_a,desc_b)):
        raise ValueError("missing licensed text features")
    if max(map(len,(context,desc_a,desc_b)))>800:
        raise ValueError("unexpectedly long source text")
    return (
        "<|im_start|>user\n"
        "次の日本語の日常の状況に対して、どちらの漫画コマの【描写】が"
        "ユーモラスな返答として適していると思いますか。漫画自体や台詞は提示していません。"
        "二つから一つだけ選び、必ず英字AまたはB一文字だけを答えてください。"
        "正解は人間の面白さ評価です。\n"
        f"状況: {context}\n"
        f"Aのコマの描写: {desc_a}\n"
        f"Bのコマの描写: {desc_b}\n"
        "回答（A/Bの一文字）:\n"
        "<|im_end|>\n<|im_start|>assistant\n"
    )


def parse_llama_reply(stdout: str) -> str | None:
    """Score only the GENERATED answer, including --no-display-prompt mode.

    Never scrape the A/B choices from the echoed Japanese context. A bare
    generated A/B line is valid in noninteractive, hidden-prompt CLI mode.
    """
    marker = "<|im_start|>assistant\n"
    text = re.sub(r"\x1b\[[0-9;]*m", "", stdout)
    if marker in text:
        generated = text.rsplit(marker, 1)[-1]
    else:
        # Fail closed if the response is an echoed prompt (not model output).
        if any(s in text for s in ("Aのコマの描写:", "Bのコマの描写:", "回答（A/Bの一文字）:")):
            return None
        generated = text
    choices = []
    for line in generated.splitlines():
        line = line.strip()
        if re.fullmatch(r"[ABab][\s\.\u3002\u3001]*", line):
            choices.append(line[0].upper())
    return choices[0] if len(choices) == 1 else None


def build_llama_command(cli: str, model: str, prompt: str) -> list[str]:
    """b12137 llama-cli automatically enables conversation mode for chat GGUF.

    Single-turn and simple-io prevent interactive-loop/terminal output in
    redirected subprocesses. No-display-prompt makes strict generated-answer
    parsing possible without leaking licensed source prompt text to the logs.
    """
    return [
        str(cli), "-m", str(model), "-p", prompt,
        "-n", "12", "-c", "2048", "-t", "4", "--temp", "0",
        "--simple-io", "--single-turn", "--no-display-prompt",
        "--no-show-timings"
    ]


def load_labeled_table(folder: Path) -> tuple[dict[int,str],dict[int,str],dict[tuple[int,int],float]]:
    verify_sources(folder)
    with (folder/"context.csv").open(encoding="utf-8-sig", newline="") as fh:
        contexts={int(x["id"]):x["text"] for x in csv.DictReader(fh)}
    with (folder/"image.csv").open(encoding="utf-8-sig",newline="") as fh:
        # The original manga dialogue column 'text' is consciously ignored.
        descriptions={int(x["id"]):x["description"] for x in csv.DictReader(fh)}
    scores={}
    with (folder/"score.csv").open(encoding="utf-8-sig",newline="") as fh:
        for x in csv.DictReader(fh):
            key=(int(x["context_id"]),int(x["image_id"]))
            if key in scores:raise ValueError("duplicate score pair")
            score=float(x["score"])
            if not 0 <= score <=1:raise ValueError("score out of range")
            scores[key]=score
    if len(contexts)!=250 or len(descriptions)!=400 or len(scores)!=100000:
        raise ValueError("source cardinality changed")
    return contexts,descriptions,scores


def build_cases(folder: Path, *, n_cases: int = N_CASES) -> list[dict]:
    contexts,descriptions,scores=load_labeled_table(folder)
    train, _, test=frozen_split()
    prior=[sum(scores[(i,j)] for i in train)/len(train) for j in range(400)]
    if not 2 <= n_cases <= len(test):
        raise ValueError("case budget exceeds heldout test contexts")
    # Selected context IDs determined independently of human ratings.
    choice_rng=random.Random(SEED)
    selected=choice_rng.sample(sorted(test),n_cases)
    cases=[]
    for ix,ctx_id in enumerate(selected):
        mode="separated" if ix%2==0 else "prior_close"
        a,b=pair_from_meta(prior,ctx_id,seed=SEED,mode=mode)
        prompt=prompt_from_text_only(contexts[ctx_id],descriptions[a],descriptions[b])
        baseline="A" if prior[a]>=prior[b] else "B"
        cases.append({
            "context_id":ctx_id,"item_a":a,"item_b":b,"prior_mode":mode,
            "baseline":baseline,
            "human_a":scores[(ctx_id,a)],"human_b":scores[(ctx_id,b)],
            "prompt_sha256":hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "_prompt":prompt
        })
    return cases


def score_pairs(rows: list[dict]) -> dict:
    total=len(rows)
    if not total:raise ValueError("empty scored pairs")
    non_ties=[r for r in rows if human_preference(r["human_a"],r["human_b"]) is not None]
    if not non_ties:raise ValueError("no non-tied human aggregate rating comparisons")
    n_model_invalid=0
    model_correct=0
    baseline_correct=0
    model_regret=[]
    baseline_regret=[]
    for row in rows:
        truth=human_preference(row["human_a"],row["human_b"])
        if truth is None: continue
        model=row.get("model")
        baseline=row.get("baseline")
        if baseline not in ("A","B"): raise ValueError("baseline must be fixed valid choice")
        if model not in ("A","B"):
            n_model_invalid+=1
        elif model==truth:model_correct+=1
        if baseline==truth:baseline_correct+=1
        top=max(row["human_a"],row["human_b"])
        # Invalid model has zero delivered choice, penalize against top reward.
        model_regret.append(top-(row[f"human_{model.lower()}"] if model in ("A","B") else 0))
        baseline_regret.append(top-row[f"human_{baseline.lower()}"])
    return {
        "n_total": total,
        "n_human_non_tied": len(non_ties),
        "n_ties": total-len(non_ties),
        "n_model_invalid": n_model_invalid,
        "model_strict_win_accuracy_including_invalid": model_correct/len(non_ties),
        "model_conditional_accuracy_among_valid": (
            model_correct/(len(non_ties)-n_model_invalid)
            if len(non_ties)>n_model_invalid else None
        ),
        "baseline_strict_win_accuracy":baseline_correct/len(non_ties),
        "mean_model_regret_invalid_counted":sum(model_regret)/len(non_ties),
        "mean_baseline_regret":sum(baseline_regret)/len(non_ties),
        "mean_random_expected_regret":sum(abs(r["human_a"]-r["human_b"])/2 for r in non_ties)/len(non_ties),
        "ground_truth": (
            "Winner determined by difference of two independently aggregated 5-human "
            "binary-funny fractions. NOT a 5-rater pairwise head-to-head comparison."
        ),
        "no_target_labels_seen_when_selecting_candidates":True,
    }


def perform_live_model(cases: list[dict], cli: Path, gguf: Path) -> list[dict]:
    if not cli.is_file() or not gguf.is_file():
        raise ValueError("llama-cli/model weights missing")
    # Official CI checks SHA256 against immutable model hash before invoking this.
    results=[]
    for i,row in enumerate(cases):
        started=time.monotonic()
        cmd=build_llama_command(str(cli), str(gguf), row["_prompt"])
        proc=subprocess.run(cmd,text=True,encoding="utf-8",errors="replace",stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=75)
        response=parse_llama_reply(proc.stdout) if proc.returncode==0 else None
        item={k:v for k,v in row.items() if k!="_prompt"}
        item.update({"model":response,"exit_code":proc.returncode,"seconds":round(time.monotonic()-started,3)})
        results.append(item)
        # Diagnostics contain ONLY assistant-generation tail, never source prompt.
        reply_marker = "<|im_start|>assistant\n"
        tail = proc.stdout.rsplit(reply_marker,1)[-1] if reply_marker in proc.stdout else ""
        diagnostic = {"marker_present": bool(tail),
                      "generated_prefix": repr(tail.strip()[:75]) if response is None else "",
                      "stdout_chars": len(proc.stdout)}
        print(json.dumps({
            "case":i+1,"context_id":item["context_id"],
            "response":response,"exit_code":proc.returncode,
            "seconds":item["seconds"],"diag": diagnostic},ensure_ascii=False),flush=True)
    return results


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-dir",required=True,type=Path)
    p.add_argument("--llama-cli",type=Path)
    p.add_argument("--model",type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--n-cases",type=int,default=N_CASES)
    p.add_argument("--dry-run",action="store_true",help="Only frozen source checks; no model accuracy claimed")
    args=p.parse_args()
    cases=build_cases(args.input_dir,n_cases=args.n_cases)
    if args.dry_run:
        out={"status":"SOURCE_AND_PROMPT_VALIDATION_ONLY","model_forward_pass_executed":False,
             "n_cases":len(cases),
             "case_manifest":[{k:v for k,v in c.items() if k not in ("_prompt","human_a","human_b")} for c in cases]}
    else:
        if args.llama_cli is None or args.model is None:
            p.error("--llama-cli and --model needed for real inference")
        if args.model.stat().st_size != 2497280736:
            raise ValueError("unexpected GGUF weight size")
        if hashlib.sha256(args.model.read_bytes()).hexdigest()!=GGUF_SHA256:
            raise ValueError("model weight SHA differs")
        scored=perform_live_model(cases,args.llama_cli,args.model)
        out={"status":"REAL_QWEN3_4B_CPU_TEXT_ONLY_HUMAN_AGGREGATE_EVAL",
             "model_forward_pass_executed":True,
             "model_name":MODEL_NAME,"model_sha256":GGUF_SHA256,
             "llama_cpp_release":LLAMA_CPP_RELEASE,"model_quantization":"Q4_K_M",
             "n_cases":len(cases),"scores":score_pairs(scored),
             "cases":scored,
             "limitation":"24 context-level pilot with selected prior-separated and prior-close pairs; no manga image/dialogue and no individual preference modeling; not original multimodal MaMe-Re leaderboard",
             "wall_time_seconds":sum(x["seconds"] for x in scored)}
    out.update({"dataset":"CyberAgent AI Lab MaMe-Re","dataset_commit":SOURCE_COMMIT,
      "file_sha256":verify_sources(args.input_dir),
      "source_rights":"CC BY 4.0 on score, context and image.description; image/text copyrighted manga excluded",
      "holdout":"frozen prior P09-5 context-disjoint 160 train/40 valid/50 test; 24 selected heldout contexts",
      "candidate_selection":"context and candidate pair selected before inspecting test human ratings, deterministic seed 20261107, half prior-separated half prior-close",
      "not_run":["Centaur 70B","Be.FM 1.5-4B adapter","any human-participant recruitment","general BFM training","multimodal visual understanding","real-world interventions"]})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"n_cases":len(cases),
                      "scores":out.get("scores"),"output":str(args.output)},ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
