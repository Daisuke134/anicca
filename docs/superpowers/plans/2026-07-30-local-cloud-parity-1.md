# LOCAL-CLOUD-PARITY-1 Implementation Plan

> Acceptance contract: spec `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`
> program row 4 — "canonicalの同じcommitをlocal OSSとmulti-tenant cloud web appの両方で起動し、
> 同じengine/skills/action contractを使う。clean VM local E2Eとcloud E2Eのgit SHA/runtime version一致。
> local-only/cloud-only実装、別repo copy、Mac browser dependency 0"。
> 順序の根拠は §0.4.6c。§0.4.6a MUST 6（Mac loopをparity完了前に止めない）は本planでも不変。

**Goal:** the same canonical commit boots the same Life Manager engine locally on a clean VM and in
the multi-tenant cloud, and both report the same git SHA through the same endpoint.

**Tech Stack:** Node.js, `node:test`, existing `apps/life-manager` server, Railway.

## Measured current state (2026-07-30, verified on canonical `a67e2f782`)

| # | Gap | Evidence |
|---:|---|---|
| G1 | `/health` returns a hardcoded `build: "lm27-voicemail-v1"`; no git SHA is exposed, so local and cloud SHAs cannot be compared at all | `apps/life-manager/server.js:257-261` |
| G2 | The Steel base URL is a hardcoded Railway-private hostname, so the browser rail cannot run anywhere but Railway | `apps/life-manager/lib/steel-cdp-client.js:27` |
| G3 | The documented clean-VM path boots `runtime/loop/index.mjs` (the earning automaton), not the Life Manager product; `apps/life-manager` has no documented local boot | `README.md:27-30`, `apps/life-manager/package.json` `start` exists but is undocumented |
| G4 | `scripts/verify-fresh-clone.sh` runs install + unit/eval only; it never starts `server.js`, never makes a request, never compares against the deployed SHA | `scripts/verify-fresh-clone.sh:39-56` |
| G5 | No parity evidence artifact exists | `docs/evidence/` contains none |

Enabling fact (measured): `RAILWAY_GIT_COMMIT_SHA` is present in the deployed container and read back
as `041f59c29957f2131fb4802b6e9bf54fcf5e027b`, so the cloud side can report a real SHA today.

## Global Constraints

- No behavior may differ between local and cloud beyond configuration values. A new `if (cloud)`
  branch in runtime code is a FAIL.
- The Steel default stays exactly `http://steel-browser.railway.internal:8080`; only an override is added.
- Mac launchd loops stay loaded; this plan does not unload anything.
- No secret value is printed by any new endpoint, script, or test.
- `/health` stays unauthenticated and must not leak tenant data, tokens, or env values.

---

### Task 1: Report the real build identity at `/health`

**Files:**
- Modify: `apps/life-manager/server.js`
- Create: `apps/life-manager/lib/build-identity.js`
- Test: `apps/life-manager/lib/build-identity.test.js`

**Interfaces:**
- Consumes: `RAILWAY_GIT_COMMIT_SHA` when present, else a `LM_BUILD_SHA` override, else the resolved
  git HEAD of the checkout, else `"unknown"`
- Produces: `{ ok, service, ws, commit, commit_source, node, started_at }` from `/health`

- [ ] **Step 1: Write failing tests**

Assert: a 40-hex `RAILWAY_GIT_COMMIT_SHA` wins; `LM_BUILD_SHA` is used when Railway's is absent; a
malformed value is rejected rather than echoed; the resolver never throws; the emitted object
contains no key whose value matches any other environment variable (secret-leak guard).

- [ ] **Step 2: Run and verify RED**

```bash
cd apps/life-manager
node --test lib/build-identity.test.js
```

- [ ] **Step 3: Implement**

Pure resolver in `lib/build-identity.js`; `server.js` calls it once at boot and serves the frozen
object. Keep the existing `ok`, `service`, `ws` keys so nothing that reads `/health` breaks.

- [ ] **Step 4: Verify GREEN and no regression**

```bash
cd apps/life-manager
node --test lib/build-identity.test.js
npm test
```

- [ ] **Step 5: Commit**

```bash
git add apps/life-manager/server.js apps/life-manager/lib/build-identity.js apps/life-manager/lib/build-identity.test.js
git commit -m "feat(health): report the real build identity"
```

### Task 2: Make the Steel base URL configurable without changing the default

**Files:**
- Modify: `apps/life-manager/lib/steel-cdp-client.js`
- Test: `apps/life-manager/lib/steel-cdp-client.test.js`

**Interfaces:**
- Consumes: optional `LM_STEEL_BASE_URL`
- Produces: the same client, pointed at the override when set

- [ ] **Step 1: Write failing tests**

Assert: with no override the base URL is byte-identical to today's constant; a valid `http(s)` URL
override is honored; a malformed or non-http override fails closed rather than silently falling back;
the `.railway.internal` Host-header rewrite still applies only to `.railway.internal` hosts.

- [ ] **Step 2: Run and verify RED**

```bash
cd apps/life-manager
node --test lib/steel-cdp-client.test.js lib/cdp-connection.test.js
```

- [ ] **Step 3: Implement**

Read the override in `makeSteelCdpClient`'s default, validate it, keep the constant as the fallback.

- [ ] **Step 4: Verify GREEN**

```bash
cd apps/life-manager
node --test lib/steel-cdp-client.test.js lib/cdp-connection.test.js
npm run test:browser-auth
```

- [ ] **Step 5: Commit**

```bash
git add apps/life-manager/lib/steel-cdp-client.js apps/life-manager/lib/steel-cdp-client.test.js
git commit -m "feat(browser): allow a non-Railway steel base url"
```

### Task 3: Give the Life Manager app a documented clean-VM local boot

**Files:**
- Create: `apps/life-manager/README.md`
- Modify: `apps/life-manager/.env.example`

**Interfaces:**
- Consumes: a minimal env set
- Produces: `node server.js` serving `/health` locally with no Railway service reachable

- [ ] **Step 1: Determine the true minimum env**

Boot `node server.js` locally with an empty env, read what actually fails, and record the minimum set
that yields a `200` on `/health`. Do not guess: the recorded list must come from observed failures.
Optional integrations must degrade rather than block boot; if any of them hard-block, note it as a
finding instead of adding a cloud/local branch.

- [ ] **Step 2: Write the README**

Document: prerequisites, the minimum env, `npm ci`, `node server.js`, the `curl /health` check with
the `commit` field, and which capabilities are inactive without their connector. State plainly that
the browser rail needs a reachable Steel (`LM_STEEL_BASE_URL`, e.g. the upstream Docker image) and is
otherwise inactive.

- [ ] **Step 3: Commit**

```bash
git add apps/life-manager/README.md apps/life-manager/.env.example
git commit -m "docs(life-manager): document the local boot path"
```

### Task 4: Parity harness — same commit, same engine, both sides

**Files:**
- Create: `scripts/verify-local-cloud-parity.mjs`
- Test: `scripts/verify-local-cloud-parity.test.mjs`

**Interfaces:**
- Consumes: a local base URL and a cloud base URL
- Produces:

```js
{ local_commit, cloud_commit, match: true, local_service, cloud_service, checked_at }
```

- [ ] **Step 1: Write failing tests**

Assert with injected fetch: equal commits pass; differing commits fail closed; a missing or
non-40-hex `commit` on either side fails closed; a non-200 fails closed; the output contains no
header, token, or env value.

- [ ] **Step 2: Run and verify RED**

```bash
node --test scripts/verify-local-cloud-parity.test.mjs
```

- [ ] **Step 3: Implement**

Fetch both `/health` endpoints, compare `commit`, emit one bounded JSON line, exit non-zero on any
mismatch or malformed response.

- [ ] **Step 4: Verify GREEN**

```bash
node --test scripts/verify-local-cloud-parity.test.mjs
node scripts/verify-oss-self-contained.mjs
```

- [ ] **Step 5: Commit**

```bash
git add scripts/verify-local-cloud-parity.mjs scripts/verify-local-cloud-parity.test.mjs
git commit -m "test(parity): compare local and cloud build identity"
```

### Task 5: Prove it on the real deployment and record evidence

**Files:**
- Create: `docs/evidence/runtime/2026-07-30-local-cloud-parity-1.md`
- Modify: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`

- [ ] **Step 1: Merge and deploy the exact canonical commit**

Require all security checks, merge, and read back the Railway deployment status at the exact merge SHA.

- [ ] **Step 2: Run both sides**

Start `node server.js` from a fresh clone of that exact commit locally, then run the parity harness
against the local server and the deployed service. Record `match: true` with both commits.

- [ ] **Step 3: Record what is NOT yet equal**

Honest inventory: which capabilities are inactive locally (browser rail without Steel, connectors
without credentials) and why that does or does not violate the acceptance criteria. Do not claim
parity for a capability that was not exercised on both sides.

- [ ] **Step 4: Update the SSOT**

Mark row 4 done only if the acceptance criteria are met, and move the cursor to `CLOUD-LOOPS-1`.
Keep every Mac loop loaded.

- [ ] **Step 5: Commit and merge**

Require PII, gitleaks, TruffleHog, OSS boundary, Python and Shell checks to pass.
