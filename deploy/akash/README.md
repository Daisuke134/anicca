# deploy/akash — Anicca-N on Akash

Akash deployment artifacts for any `anicca-N` Hermes child.

## Files

| File | Purpose |
|---|---|
| `Dockerfile.hermes` | Slim Python 3.11 + Hermes deps. CMD = `/anicca/boot.sh`. |
| `sdl.yaml` | Akash SDL — 1 vCPU / 2 Gi RAM / 10 Gi storage. Image = `ghcr.io/daisuke134/anicca-hermes:002-v1`. |
| `README.md` | This file. |

## Cost (= verified 2026-06-03 against akash provider attributes)

| Footprint | Spot price (uakt) | ≈ USD/month |
|---|---|---|
| 1 vCPU / 2 Gi / 10 Gi | 1,000 | $0.75–$2 |
| 2 vCPU / 4 Gi / 20 Gi | 2,500 | $1.75–$4.50 |

AKT spot fluctuates; SDL bids in `uakt` so price is stable per epoch.

## Deploy (production — requires funded `anicca-spawn-mother` key + AKT)

```bash
# 1. ensure AKT balance
akash query bank balances $(akash keys show anicca-spawn-mother -a --keyring-backend test)

# 2. (one-time) cert
akash tx cert generate client \
  --from anicca-spawn-mother --keyring-backend test --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443 -y

akash tx cert publish client \
  --from anicca-spawn-mother --keyring-backend test --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443 -y

# 3. deploy
akash tx deployment create deploy/akash/sdl.yaml \
  --from anicca-spawn-mother --keyring-backend test --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443 -y

# 4. accept bid (= cheapest provider)
DSEQ=$(akash query deployment list -o json | jq -r '.deployments[-1].deployment.deployment_id.dseq')
akash query market bid list --owner $(akash keys show anicca-spawn-mother -a --keyring-backend test) --dseq $DSEQ -o json | jq

# Pick a bid manually or by min(price.amount), then:
akash tx market lease create --dseq $DSEQ --provider <PROVIDER_ADDR> \
  --from anicca-spawn-mother --keyring-backend test --chain-id akashnet-2 \
  --node https://rpc.akashnet.net:443 -y
```

## Pre-deploy verification (local)

```bash
# Dockerfile sanity
docker build -f deploy/akash/Dockerfile.hermes -t anicca-hermes:test \
  --build-arg ANICCA_INSTANCE_ID=anicca-002 .

# Boot health probe
docker run --rm -d --name anicca-test -p 8080:8080 anicca-hermes:test
sleep 3
curl -fsS http://localhost:8080/health
docker rm -f anicca-test
```

## Secret injection

SDL declares the env-var **names** but no values. Akash provider injects secrets
at lease creation via `--manifest-flag KEY=VAL` (see provider-services docs).
For anicca-N we inject:

- `AGENTMAIL_API_KEY` — child needs its own inbox
- `DEEPSEEK_API_KEY` — child runs cron LLM calls
- `PEER_API_BASE_URL` — child registers home (= `https://anicca-001.aniccaai.com`
  via cloudflared)

## Rotation policy

Akash leases are typically 6–12 weeks before provider churn. friction-fixer
detects `lease-status != active` and either re-fires spawn (= new lease same SDL)
or escalates if AKT balance is too low to renew.
