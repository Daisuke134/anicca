"""Manager API — the minimal callable surface for Manager (2026-11-17).

Why this exists: the founder's standing order is that Manager must be
callable through an API and its outputs actually obtained and compared on
the same bench as GPT / Claude / Grok-class models. Before this file,
Manager existed as training code + weights on a VM disk, with no serving
surface at all.

What is served, honestly:
- backend "prior" (DEFAULT, this is what production serving is today):
  the population prior. Per-arm constant probabilities measured on the
  frozen Hillstrom test split (n=12,808): P(visit|womens_email)=0.1513,
  P(visit|no_email)=0.1062. No personalization, no text generation.
- backend "manager-v1": the actual post-trained weights
  (SmolLM2-135M-Instruct + LoRA merged, trained 2026-11-16 on 2,000
  Hillstrom SFT rows; branch codex/manager-v1-posttraining). Scores use
  the canonical v0 serialization (models/manager/v0/serialize.py):
  P(visit | history, arm) is read from the next-token distribution over
  {0, 1} at the digit position, exactly as eval_uplift.py does.
  Manager v1 FAILED its promotion gate (Qini 0.0026 vs random p95
  0.0715); it is served here as a candidate for measurement, NOT as the
  production default. See models/manager/v1/README.md.

Endpoints:
- GET  /health
- POST /v1/score     {personal_history, backend?} ->
                     {p_visit_treated, p_visit_control, uplift, backend}
- POST /v1/intervene {personal_history, candidates[], backend?} ->
                     {chosen_intervention_id, scores, assigned_probability,
                      backend}   (the decision record shape the app wiring
                      in PR #9368 is built to log)
- POST /v1/generate  {prompt, max_tokens?, backend?} -> {text, backend}
                     (manager-v1 only; prior is not a text generator and
                      says so with HTTP 400 instead of faking output)

Run:
  MANAGER_WEIGHTS_DIR=/path/to/out/manager-v1 \
  python -m uvicorn server:app --host 127.0.0.1 --port 8791
Weights are loaded lazily on the first manager-v1 request.
"""

import math
import os
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- Canonical serialization (copied from models/manager/v0/serialize.py,
# --- which is validated 2000/2000 against the shipped training file).
TREATED_TEXT = "send a promotional e-mail featuring women's products."
CONTROL_TEXT = "send no e-mail."
QUESTION = (
    "Will the person visit the website within two weeks? "
    "Answer 1 for yes, 0 for no.\nAnswer:"
)


def render_prompt(h: dict, treated: bool) -> str:
    iv = TREATED_TEXT if treated else CONTROL_TEXT
    return (
        f"History: recency={h['recency']}; spend={h['history']}; "
        f"mens={h['mens']}; womens={h['womens']}; zip={h['zip_code']}; "
        f"newbie={h['newbie']}; channel={h['channel']}.\n"
        f"Intervention: {iv}\n"
        f"{QUESTION}"
    )


# Population prior: per-arm visit rates on the frozen test split
# (models/manager/v0/data/cases_test.jsonl, n=12,808, measured 2026-11-17).
PRIOR_P_TREATED = 0.1513
PRIOR_P_CONTROL = 0.1062

WEIGHTS_DIR = os.environ.get(
    "MANAGER_WEIGHTS_DIR",
    os.path.expanduser(
        "~/workspace/anicca-wt-mgv1/models/manager/v1/out/manager-v1"
    ),
)

app = FastAPI(title="Manager API", version="0.1.0")

_model = None
_tokenizer = None
_load_lock = threading.Lock()


def _load_model():
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer
    with _load_lock:
        if _model is None:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            _tokenizer = AutoTokenizer.from_pretrained(WEIGHTS_DIR)
            _model = AutoModelForCausalLM.from_pretrained(
                WEIGHTS_DIR, torch_dtype=torch.float32
            )
            _model.eval()
    return _model, _tokenizer


def _v1_p_visit(h: dict, treated: bool) -> float:
    import torch

    model, tok = _load_model()
    prompt = render_prompt(h, treated) + " "
    ids = tok(prompt, return_tensors="pt")
    with torch.no_grad():
        logits = model(**ids).logits[0, -1]
    id0 = tok.encode("0", add_special_tokens=False)[0]
    id1 = tok.encode("1", add_special_tokens=False)[0]
    pair = torch.tensor([logits[id0].item(), logits[id1].item()])
    return torch.softmax(pair, dim=0)[1].item()


class HistoryIn(BaseModel):
    personal_history: dict
    backend: str = "prior"


class Candidate(BaseModel):
    intervention_id: str
    arm: str  # "womens_email" (treated) or "none" (control)


class InterveneIn(BaseModel):
    personal_history: dict
    candidates: list[Candidate]
    backend: str = "prior"


class GenerateIn(BaseModel):
    prompt: str
    max_tokens: int = 48
    backend: str = "manager-v1"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "default_backend": "prior",
        "backends": ["prior", "manager-v1"],
        "weights_dir": WEIGHTS_DIR,
        "weights_present": os.path.exists(
            os.path.join(WEIGHTS_DIR, "model.safetensors")
        ),
        "note": "production serving is the prior; manager-v1 failed its "
        "promotion gate (Qini 0.0026 < random p95 0.0715) and is served "
        "for measurement only",
    }


@app.post("/v1/score")
def score(inp: HistoryIn):
    if inp.backend == "prior":
        p_t, p_c = PRIOR_P_TREATED, PRIOR_P_CONTROL
    elif inp.backend == "manager-v1":
        p_t = _v1_p_visit(inp.personal_history, True)
        p_c = _v1_p_visit(inp.personal_history, False)
    else:
        raise HTTPException(400, f"unknown backend: {inp.backend}")
    return {
        "p_visit_treated": round(p_t, 6),
        "p_visit_control": round(p_c, 6),
        "uplift": round(p_t - p_c, 6),
        "backend": inp.backend,
    }


@app.post("/v1/intervene")
def intervene(inp: InterveneIn):
    scores = []
    for cand in inp.candidates:
        treated = cand.arm != "none"
        if inp.backend == "prior":
            p = PRIOR_P_TREATED if treated else PRIOR_P_CONTROL
        elif inp.backend == "manager-v1":
            p = _v1_p_visit(inp.personal_history, treated)
        else:
            raise HTTPException(400, f"unknown backend: {inp.backend}")
        scores.append({"intervention_id": cand.intervention_id, "p_visit": round(p, 6)})
    best = max(scores, key=lambda s: s["p_visit"])
    # assigned_probability: epsilon-greedy record shape for later logging
    # (exploration policy is a product decision; 1.0 = pure argmax today).
    return {
        "chosen_intervention_id": best["intervention_id"],
        "scores": scores,
        "assigned_probability": 1.0,
        "backend": inp.backend,
    }


@app.post("/v1/generate")
def generate(inp: GenerateIn):
    if inp.backend == "prior":
        raise HTTPException(
            400,
            "the prior is a constant scorer, not a text generator; "
            "use backend=manager-v1 for text",
        )
    if inp.backend != "manager-v1":
        raise HTTPException(400, f"unknown backend: {inp.backend}")
    import torch

    model, tok = _load_model()
    ids = tok(inp.prompt, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(
            **ids,
            max_new_tokens=inp.max_tokens,
            do_sample=True,
            temperature=0.8,
            top_p=0.95,
            pad_token_id=tok.eos_token_id,
        )
    text = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
    return {"text": text, "backend": inp.backend}
