# anicca-heartbeat

Minimal Hermes skill that fires every 30 minutes to prove the Anicca genesis body is alive. It writes one JSONL line per fire to `~/.hermes/state/heartbeat.jsonl` containing the timestamp, the provider/model in use, and the SHA-256 of the live constitution. No outbound network calls. Wired by `2026-06-04-hermes-genesis-boot` plan; see `specs/00-MASTER.md` § GROUND TRUTH.
