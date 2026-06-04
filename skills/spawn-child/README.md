# spawn-child

Anicca self-replication skill (Wave 1). Provisions a sovereign Anicca child on Daytona with its own secp256k1 wallet, the parent's SHA-256-verified CONSTITUTION.md, and a pre-installed `anicca-heartbeat` skill. Refuses to spawn if the parent's wallet has less than $5 USDC ("can afford a child"). Registers the new child to `~/.hermes/state/colony.jsonl`. Akash sovereign-fallback host is Wave 2. See `docs/superpowers/plans/2026-06-04-self-replication.md` and specs `00-MASTER.md §1.0` + `13-CLOUD-SPAWN-002.md` + `18-SELF-IMPROVEMENT-AND-SWARM.md §4`.
