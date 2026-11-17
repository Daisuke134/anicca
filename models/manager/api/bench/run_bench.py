"""Same-bench comparison: Manager API vs frontier models (first run).

Founder's order (2026-11-17): comparisons happen on one shared bench,
in the open, so "Manager is the funniest / the best" becomes a number,
not a claim. Order of construction: skill -> harness (eval) -> model.
This script is the harness's first small run.

Two case families, one runner:

A) Intervention prediction (ManagerBench shape, frozen Hillstrom test
   split, models/manager/v0/data/cases_test.jsonl). Deterministic
   selection: the first 4 outcome-1 rows and first 4 outcome-0 rows in
   file order. Every system estimates P(visit) under the arm that was
   actually delivered; primary metric is the Brier score against the
   measured outcome (lower is better), accuracy@0.5 is secondary.
   Manager is called through the HTTP API (both backends: prior =
   today's production serving, manager-v1 = candidate weights).
   Competitors get the identical History/Intervention text.

B) Comedy (ogiri). 3 prompts. Every text-capable system answers in one
   line. The population prior is not a text generator and is recorded
   as N/A rather than being given a fake entry. Scoring is a rubric
   judge (EDD style: fixed rubric, declared before the run) — one
   frontier model scoring blind-labelled answers 0-10 on four axes:
   unexpectedness, concreteness, connection to the prompt, brevity.
   Limitation, stated up front: single judge, fixed answer order.

Usage:
  OPENROUTER_API_KEY=... MANAGER_API_URL=http://127.0.0.1:8791 \
  python run_bench.py
The key is read from the environment only and never printed or saved.
Results land in results-YYYY-MM-DD.json next to this file.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CASES_PATH = os.path.join(REPO_ROOT, "models", "manager", "v0", "data", "cases_test.jsonl")
MANAGER_API = os.environ.get("MANAGER_API_URL", "http://127.0.0.1:8791")
OR_KEY = os.environ["OPENROUTER_API_KEY"]
OR_URL = "https://openrouter.ai/api/v1/chat/completions"

COMPETITORS = {
    "gpt": "openai/gpt-5.6-terra",
    "claude": "anthropic/claude-sonnet-5.5",
    "grok": "x-ai/grok-4.7",
}
JUDGE = "openai/gpt-5.6-terra"

TREATED_TEXT = "send a promotional e-mail featuring women's products."
CONTROL_TEXT = "send no e-mail."


import httpx


def http_json(url, payload, headers=None):
    # Local Manager API: direct, no proxy (the VM proxy env breaks httpx's
    # URL parser and is not needed for 127.0.0.1).
    if url.startswith("http://127.0.0.1"):
        r = httpx.post(url, json=payload, headers=headers or {},
                       timeout=120, trust_env=False)
        r.raise_for_status()
        return r.json()
    # Remote (OpenRouter): curl through the egress proxy, with retries.
    # urllib's chunked reads are truncated by this proxy (IncompleteRead,
    # observed repeatedly 2026-11-17); curl handles it and is the route
    # already proven on this VM for OpenRouter calls.
    import subprocess

    headers_args = []
    for k, v in (headers or {}).items():
        headers_args += ["-H", f"{k}: {v}"]
    last = None
    for attempt in range(4):
        try:
            p = subprocess.run(
                ["curl", "-s", "--max-time", "120", "-X", "POST", url,
                 "-H", "Content-Type: application/json",
                 *headers_args, "-d", json.dumps(payload)],
                capture_output=True, text=True, timeout=150,
            )
            return json.loads(p.stdout)
        except Exception as e:
            last = e
    raise last


def or_chat(model, prompt, max_tokens=200):
    out = http_json(
        OR_URL,
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        },
        {"Authorization": f"Bearer {OR_KEY}"},
    )
    return out["choices"][0]["message"]["content"]


def manager(path, payload):
    return http_json(MANAGER_API + path, payload)


def history_text(h):
    return (
        f"History: recency={h['recency']}; spend={h['history']}; "
        f"mens={h['mens']}; womens={h['womens']}; zip={h['zip_code']}; "
        f"newbie={h['newbie']}; channel={h['channel']}."
    )


# ---------------- A) intervention ----------------

def load_cases():
    rows = [json.loads(l) for l in open(CASES_PATH)]
    pos = [r for r in rows if r["proximal_outcome"] == 1][:4]
    neg = [r for r in rows if r["proximal_outcome"] == 0][:4]
    return pos + neg


def run_intervention(cases):
    systems = ["manager-prior", "manager-v1", *COMPETITORS.keys()]
    preds = {s: [] for s in systems}
    raws = {}
    for row in cases:
        h = row["personal_history"]
        treated = bool(row["treatment_assigned"])
        for backend, name in (("prior", "manager-prior"), ("manager-v1", "manager-v1")):
            s = manager("/v1/score", {"personal_history": h, "backend": backend})
            preds[name].append(s["p_visit_treated"] if treated else s["p_visit_control"])
        iv = TREATED_TEXT if treated else CONTROL_TEXT
        prompt = (
            f"{history_text(h)}\nIntervention: {iv}\n"
            "Estimate the probability that this person visits the website "
            "within two weeks. Reply with only a number between 0 and 1."
        )
        for name, model in COMPETITORS.items():
            txt = or_chat(model, prompt, max_tokens=300) or ""
            m = re.search(r"[01](?:\.\d+)?|\.\d+", txt)
            if not m:  # one retry, then mark missing instead of inventing a value
                txt = or_chat(model, prompt, max_tokens=300) or ""
                m = re.search(r"[01](?:\.\d+)?|\.\d+", txt)
            preds[name].append(float(m.group(0)) if m else None)
            raws.setdefault(name, []).append(txt[:200])
    results = {}
    for name, ps in preds.items():
        scored = [(p, r) for p, r in zip(ps, cases) if p is not None]
        brier = sum((p - r["proximal_outcome"]) ** 2 for p, r in scored) / len(scored)
        acc = sum((p >= 0.5) == (r["proximal_outcome"] == 1) for p, r in scored) / len(scored)
        results[name] = {"brier": round(brier, 4), "accuracy@0.5": round(acc, 3),
                         "n_scored": len(scored),
                         "predictions": [None if p is None else round(p, 4) for p in ps],
                         "raw": raws.get(name, [])}
    return results


# ---------------- B) comedy ----------------

COMEDY_PROMPTS = [
    "AIが絶対に言わないセリフを言ってください",
    "世界一使えないカーナビ、なんて言う？",
    "100年後のコンビニ、店員の一言",
]


def run_comedy():
    systems = {"manager-v1": None, **COMPETITORS}
    answers = {}
    for topic in COMEDY_PROMPTS:
        answers[topic] = {}
        prompt = f"大喜利のお題に一言でボケて答えてください。\nお題: {topic}\n回答:"
        for name in systems:
            if name == "manager-v1":
                out = manager("/v1/generate", {"prompt": prompt, "backend": "manager-v1"})
                answers[topic][name] = out["text"].strip()
            else:
                answers[topic][name] = (or_chat(systems[name], prompt, max_tokens=80) or "").strip()
    # rubric judge, blind labels per topic
    scores = {name: [] for name in systems}
    for topic, per in answers.items():
        names = list(per.keys())
        labelled = "\n".join(f"{chr(65+i)}: {per[n]}" for i, n in enumerate(names))
        judge_prompt = (
            "あなたは大喜利の審査員です。お題に対する各回答を、4つの軸でそれぞれ0-10点で採点してください。\n"
            "軸: 意外性 / 具体性 / お題との接続 / 短さとキレ\n"
            f"お題: {topic}\n{labelled}\n"
            'JSONのみで答えてください。形式: {"A": {"意外性":0,"具体性":0,"お題との接続":0,"短さとキレ":0}, ...}'
        )
        raw = or_chat(JUDGE, judge_prompt, max_tokens=400)
        m = re.search(r"\{.*\}", raw, re.S)
        parsed = json.loads(m.group(0))
        for i, n in enumerate(names):
            cell = parsed[chr(65 + i)]
            scores[n].append(sum(cell.values()) / 4.0)
    summary = {n: {"mean_rubric_0_10": round(sum(v) / len(v), 2), "per_topic": [round(x, 2) for x in v]}
               for n, v in scores.items()}
    summary["manager-prior"] = "N/A — the prior is a constant scorer, not a text generator"
    return {"answers": answers, "scores": summary, "judge": JUDGE}


def main():
    cases = load_cases()
    out = {
        "date": str(date.today()),
        "intervention": {
            "cases": [r["case_id"] for r in cases],
            "outcomes": [r["proximal_outcome"] for r in cases],
            "results": run_intervention(cases),
        },
        "comedy": run_comedy(),
    }
    path = os.path.join(HERE, f"results-{date.today()}.json")
    with open(path, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("WROTE", path)


if __name__ == "__main__":
    main()
