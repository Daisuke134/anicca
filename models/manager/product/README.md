# Authenticated Manager product service

Run from the anicca repository root:
`python -m uvicorn models.manager.product.http_api:app_from_env --factory --host 127.0.0.1 --port 8792`

Install FastAPI and uvicorn. Configure MANAGER_STORE_PATH on durable private storage,
MANAGER_PSEUDONYM_KEY (at least 32 bytes), and MANAGER_SERVICE_TOKEN through the
deployment secret store. Never commit their values. The proxy needs the same
MANAGER_SERVICE_TOKEN and MANAGER_PRODUCT_URL pointing to this private service.
Use private networking / TLS for inter-host traffic; do not expose the service publicly.

Default remains prior, using PR #9385's canonical constants. Prior cannot produce
the Swift generated-decision contract, so decisions return 503 with explicit prior
labelling. This is intentional: mounting does not promote the failed manager-v1
candidate. Health is 200 with generation_available=false. Observations and deletion
use authenticated pseudonymous ownership. No paid API or catalogue fallback.

Model-generated mode (integrated 2026-11-17, branch codex/manager-integration-2026-11-17):
set MANAGER_LLM_BASE_URL (any OpenAI-compatible chat base, e.g.
https://api.openai.com/v1) and MANAGER_LLM_MODEL, plus MANAGER_LLM_API_KEY
(or OPENAI_API_KEY) when the endpoint needs one. Decisions are then generated
per person at decision time by that LLM (ChatLLMGenerator in interventions.py):
the person's context and synthetic-user push_state go in, a validated candidate
distribution comes out, and the chosen word is what gets delivered. Health then
reports generation_available=true and the generator model name; every decision
record also carries generator_model for provenance. Optionally set
MANAGER_SENDER_TOKEN to enable the sender-only /manager/push-decisions batch
route used by the APNs sender patch. A free keyless compatible endpoint works
for local verification; production should use the already-paid OpenAI key that
the proxy's LLM nudges already use. There is still no catalogue fallback: if
generation fails or returns invalid candidates, nothing is sent.

The Express mount uses existing requireAuth, also requiring unexpired JWTs. Incoming
subject headers are discarded; only the verified account subject is forwarded.
Missing configuration, timeout, invalid upstream JSON and redirects fail closed.
Existing /api routes and APNs scheduling are unchanged.

## Model words and ManagerBench (2026-11-20)

The default configured-credit engine is now OpenRouter
`https://openrouter.ai/api/v1`, `deepseek/deepseek-v4.1-flash-1017`, using only
`MANAGER_LLM_API_KEY` or `OPENROUTER_API_KEY`. No OPENAI_API_KEY fallback.
Explicit MANAGER_LLM_BASE_URL/MODEL overrides remain for existing deployments
and local fixture endpoints. With no key or explicit endpoint, fail closed.
This supersedes the historical OpenAI-key recommendation above.

App `/decisions` context may carry `synthetic_user: {answer_ids, answer_version}`.
The sender's existing `push_state.profile.personalization.answerIds` is normalized
to the same conditioning shape. Unrelated metadata and raw reaction payloads do
not reach the LLM. Invalid context/output or an unavailable provider suppresses.

Every new SQLite case atomically includes `managerbench_case`, with chosen text,
generator model, categorical situation, candidate IDs and the actual conditional
selection propensity. An assignment is not delivery: response remains unknown.
Export private JSONL for ManagerBench with:

```
python -m models.manager.product.export_cases /private/cases.db > /private/cases.jsonl
```

Only measured in-window observations become positive response fields. Missing
observations stay unknown; old rows without the new projection are skipped.
The export is read-only, and account deletion removes the source rows.
