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

The Express mount uses existing requireAuth, also requiring unexpired JWTs. Incoming
subject headers are discarded; only the verified account subject is forwarded.
Missing configuration, timeout, invalid upstream JSON and redirects fail closed.
Existing /api routes and APNs scheduling are unchanged.
