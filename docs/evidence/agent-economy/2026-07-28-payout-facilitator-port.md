# Life Manager payout facilitator dedicated-port repair

## Failure reproduced

Life Manager reserves loopback port `8406` for the production payout facilitator. `services/facilitator/start.sh` exported `PORT=8406`, but both checked-in facilitator configs contained `"port": 8405`. The x402-rs binary treats the config value as authoritative, started on `8405`, and made the wrapper's `8406/health` readiness check fail after 15 seconds.

This was observed with the real release binary and Base mainnet config before any Life Manager user payout existed. No existing launchd loop was stopped.

## RED → GREEN

`services/facilitator/tests/start-port-contract.sh` copies the wrapper into a bounded temporary sandbox and launches a real HTTP fake facilitator whose bind port comes only from `CONFIG`.

| State | Result |
|---|---|
| RED, original wrapper | exit `1`: `facilitator failed to start` because requested port and config port differed |
| GREEN, runtime-config wrapper | PASS: requested port served `/health`, canonical config SHA-256 unchanged |

The wrapper now validates the requested port and writes a mode-`0600` per-port runtime config under `state/`, changing only its `port` field. x402-rs receives that runtime config; the checked-in chain configuration is never mutated.

## Live verification

The repaired wrapper started the real release binary on `127.0.0.1:8406` with the Base mainnet config. Both `/health` and `/supported` advertised x402 v2 `exact` on `eip155:8453`. The temporary verification process was then stopped by exact PID; no persistent loop was changed.

The same real facilitator binary separately verified and settled the agent-owned bootstrap transfer `0x65034f070374f7dd6ce624717dfaad909b93f663ebe2deddc3925bf8b2ef8741` on Base, proving the release binary's mainnet settlement path. That transfer is not a Life Manager user payout and is not external revenue.

Focused verification:

- shell syntax: PASS
- dedicated-port black-box contract: PASS
- `base-usdc-payout` + `run-agent-payout`: 18/18 PASS
- live `8406` `/health` and `/supported`: PASS

## Remaining boundary

The 13d engine no longer has the dedicated-port startup defect, but an actual user payout still requires verified external surplus above the `$35` reserve. Until 13c produces that economic state, 13d remains pending.

