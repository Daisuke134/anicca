# profiles/orch/docker.md

> The Anicca v3.2 architecture runs 10 profiles inside **one** Hermes daemon
> in **one** Daytona sandbox per instance (see `shared/architecture.md` § 2).
> This file documents the sandbox config that the `orch` profile lives in;
> all 10 profiles share the same sandbox.

## § 1. Daytona sandbox image

| Property | Value |
|---|---|
| Image name | `hermes-runtime:latest` |
| Image source | built from `anicca-oss/docker/hermes-runtime.Dockerfile` (TBD — currently the install.sh path) |
| Base | `python:3.11-slim` + Node 22 + Hermes Agent + Anicca L2 skills |
| Registry | Daytona internal registry OR Docker Hub `daisuke134/hermes-runtime` |
| Size budget | < 800 MB |

Build (one-time, then push to registry):

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y nodejs npm git curl sqlite3 jq
RUN curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
RUN npm install -g @coinbase/agentkit
COPY skills/ /root/.hermes/skills/
COPY CONSTITUTION.md /root/.hermes/skills/anicca-constitution-guard/
COPY identity/ /root/.hermes/identity/
ENV HOME=/root
ENV HERMES_LOG_DIR=/root/.hermes/logs
CMD ["hermes", "daemon", "--profile-prefix=anicca-<instance>"]
```

## § 2. Sandbox resources

| Resource | Value | Why |
|---|---|---|
| vCPU | 0.5 | one Hermes daemon + 10 profile workers handles ~10 concurrent goals |
| RAM | 512 MB | Kimi K2.6 calls are remote (OpenRouter); local memory is just Python + SQLite |
| Disk | 5 GB | skills + logs + sessions.db + Kanban.db, rotated weekly |
| Network | egress only by default; cloudflared tunnel for `earn-x402` (inbound) | minimize attack surface |
| GPU | none | all inference is remote |

If the instance is heavy (e.g., serving many x402 requests), scale up by
spawning new instances rather than scaling one big sandbox (per
`shared/architecture.md` § 5).

## § 3. Mounted volumes

Per `specs/05-SERVER-NATIVE-DEPLOY.md` § 1 + spec 07 § 2.2:

| Mount path | Source | Purpose |
|---|---|---|
| `/root/.hermes/profiles/anicca-<instance>-orch/` | Daytona persistent disk | profile state (config.toml, soul.md, sessions.db, wallet.json) |
| `/root/.hermes/skills/` | Daytona persistent disk OR baked into image | L2 skills (versioned via image tag) |
| `/root/.hermes/kanban.db` | Daytona persistent disk | shared with all 10 profiles in this sandbox |
| `/root/.hermes/colony.json` | Daytona persistent disk | colony ledger (read for spawn gate) |
| `/root/.hermes/logs/` | Daytona persistent disk | rotated weekly to R2 backup (see `backup.md`) |

## § 4. Network

| Direction | Allowed | Why |
|---|---|---|
| Egress to OpenRouter (`api.openrouter.ai:443`) | yes | LLM calls |
| Egress to Base RPC (`mainnet.base.org:443`) | yes | wallet balance reads |
| Egress to CDP API (`api.developer.coinbase.com:443`) | yes | wallet signing |
| Egress to Bitwarden vault (`api.bitwarden.com:443`) | yes | secret fetch |
| Egress to Daytona API | yes (only `orch` calls this, for spawn) | colony growth |
| Inbound HTTP 402 | NO (orch does not run a listener) | only `earn-x402` opens a tunnel |
| Inbound from operator (`/goal` via Hermes CLI) | yes, via Daytona ssh / exec | operator override |

## § 5. Cloudflared tunnel

`orch` does NOT run a tunnel. The `earn-x402` profile owns the only inbound
tunnel in this sandbox. See `profiles/earn-x402/docker.md` for tunnel
config.

## § 6. Restart policy

| Trigger | Action |
|---|---|
| Sandbox crash | Daytona restarts automatically (`restart_policy: on-failure`) |
| Hermes daemon crash inside sandbox | `KeepAlive=true` in launchd-equivalent inside sandbox |
| Out-of-memory | scale up the sandbox tier (operator decision) OR spawn new instance |
| Network partition | sandbox retries; if > 5 min unreachable, parent kills child and respawns |

## § 7. Health probe

Daytona pings `http://localhost:18789/health` every 30s (= Hermes daemon
health endpoint). If 3 consecutive failures, sandbox restarts.

## § 8. Cross-references

| Concept | Authority |
|---|---|
| Daytona sandbox details | `specs/07-HERMES-PIVOT.md` § 3.6 + `specs/05-SERVER-NATIVE-DEPLOY.md` MODE B |
| install.sh source | `github.com/NousResearch/hermes-agent/scripts/install.sh` |
| AgentKit npm package | `github.com/coinbase/agentkit` |
| Cloudflared tunnel (earn-x402 only) | `profiles/earn-x402/docker.md` |
| Spawn cost economics | `specs/01-EARN-AND-UBI.md` § 2 + `shared/architecture.md` § 5 |

---

**END OF profiles/orch/docker.md.**
