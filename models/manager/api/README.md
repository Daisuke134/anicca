# Manager API

The minimal callable surface for **Manager**, Anicca's behavior model.
Built 2026-11-17 under the founder's order that Manager must be callable
through an API, its outputs actually obtained, and its quality compared
on one shared bench against frontier models (GPT / Claude / Grok class) —
the road to "Manager is the funniest / the best" as a measured number.

## Status, stated plainly

- There was **no API before this directory**: Manager existed as
  training code (`models/manager/v0`, `v1`) and weights on a VM disk,
  with no serving surface. Nothing outside the training scripts could
  call it.
- Production serving today is the **population prior** — per-arm
  constant probabilities measured on the frozen Hillstrom test split
  (n=12,808): P(visit | womens_email) = 0.1513, P(visit | no email) =
  0.1062. The API's default backend is `prior`, matching production.
- The post-trained candidate, **manager-v1** (SmolLM2-135M-Instruct +
  LoRA merged; 2,000 Hillstrom SFT rows; branch
  `codex/manager-v1-posttraining`), **failed its promotion gate**
  (frozen uplift eval: Qini 0.0026 vs random p95 0.0715; see
  `models/manager/v1/README.md`). It is served here for measurement,
  not as the default.
- No company model or dataset exists on Hugging Face as of 2026-11-17
  (checked: anicca / aniccaai / anicca-ai / mujo / Daisuke134 / diceai —
  all zero models). The v1 weights live on the team VM at
  `~/workspace/anicca-wt-mgv1/models/manager/v1/out/manager-v1/`
  (git-ignored `out/` directory, 269 MB safetensors) and in no other
  place — publishing them to HF is an open follow-up.

## Run

```bash
pip install -r requirements.txt
MANAGER_WEIGHTS_DIR=/path/to/out/manager-v1 \
  python -m uvicorn server:app --host 127.0.0.1 --port 8791
curl http://127.0.0.1:8791/health
python client_example.py score      # prior + manager-v1, same input
python client_example.py intervene  # candidate selection via manager-v1
python client_example.py generate   # text generation (manager-v1 only)
```

## Endpoints

| Endpoint | Input | Output |
|---|---|---|
| `GET /health` | — | backends, weights presence, serving note |
| `POST /v1/score` | `personal_history` (Hillstrom features), `backend` | `p_visit_treated`, `p_visit_control`, `uplift` |
| `POST /v1/intervene` | `personal_history`, `candidates[]`, `backend` | `chosen_intervention_id`, per-candidate `scores`, `assigned_probability` (the decision-record shape the app wiring logs) |
| `POST /v1/generate` | `prompt`, `max_tokens`, `backend` | `text` (manager-v1 only; the prior honestly refuses with HTTP 400) |

Scoring uses the canonical v0 serialization
(`models/manager/v0/serialize.py`, validated 2000/2000 against the
training file): P(visit | history, arm) is read from the next-token
distribution over {0, 1} at the digit position, exactly as
`eval_uplift.py` does.

## Bench (same-bench comparison)

`bench/run_bench.py` runs one shared case set through every system:

- **Intervention** (ManagerBench shape): 8 frozen test cases (first 4
  outcome-1 + first 4 outcome-0 in file order). Every system estimates
  P(visit) under the delivered arm. Primary metric: Brier score vs the
  measured outcome. Manager is called through this HTTP API;
  competitors (via OpenRouter) receive the identical History /
  Intervention text.
- **Comedy** (ogiri): 3 Japanese prompts, one-line answers, scored by a
  rubric judge declared before the run (unexpectedness / concreteness /
  connection to the prompt / brevity, 0–10 each). The prior is recorded
  as N/A — it is not a text generator. Limitations: single judge, fixed
  answer order, tiny n. This is a harness smoke run, not a leaderboard.

```bash
OPENROUTER_API_KEY=... MANAGER_API_URL=http://127.0.0.1:8791 \
  python bench/run_bench.py   # writes bench/results-YYYY-MM-DD.json
```

First-run results: `bench/results-2026-11-17.json` and the record in
anicca-ops `files/manager-api-callable-2026-11-17.md`.
