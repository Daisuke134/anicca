# profiles/cook-loop/env-map.md

## § 1. Env vars

| Key NAME | Required | Source | Used for |
|---|---|---|---|
| `BWS_ACCESS_TOKEN` | yes | `~/.openclaw/.env` | vault unlock |
| `OPENROUTER_API_KEY` | yes | Bitwarden vault | LLM for SCORE / PORT / MEASURE |
| `GH_TOKEN` | yes | Bitwarden vault | clone candidate repos, read issue context |
| `COOK_CYCLE_INTERVAL_HOURS` | optional | env override | default `24` (= one DISCOVER→ADJUST cycle per day) |
| `COOK_PORT_MAX_PER_CYCLE` | optional | env override | default `2` (= avoid skill explosion) |
| `COOK_MIN_TARGET_STARS` | optional | env override | default `100` (= skip toy repos) |

## § 2. Identity

No PII. Uses the same GitHub bot account as `earn-bounty` (= per-instance,
KYC zero).

## § 3. Cook priors

`~/.hermes/cook-priors.json`:

```json
{
  "target_type_priors": {
    "x402_server_pattern": 0.95,
    "agent_skill_template": 0.85,
    "wallet_action_provider": 0.80,
    "farcaster_frame_starter": 0.70,
    "bittensor_subnet_miner": 0.60
  },
  "last_updated": "<ISO>",
  "method": "30d revenue contribution per ported skill, normalized"
}
```

Updated by ADJUST step. Read by SCORE step.

## § 4. Imitation targets schema

`~/.hermes/imitation-targets.jsonl` (one JSON per line, append-only):

```jsonl
{"id": "01", "ts": "<ISO>", "source_url": "github.com/foo/bar", "type": "x402_server_pattern", "license": "MIT", "stars": 1234, "verified_working": true, "ported_to_skill": null}
{"id": "02", "ts": "<ISO>", "source_url": "github.com/baz/qux", "type": "agent_skill_template", "license": "Apache-2.0", "stars": 456, "verified_working": true, "ported_to_skill": "anicca-skill-bar"}
```

Append-only per spec 02 § 1.3.

## § 5. Cross-references

| Concept | Authority |
|---|---|
| Vault policy | `control-room/shared/security.md` § 4 |
| Cook loop verbatim | `specs/02-IMITATE-AND-COOK.md` § 2 |
| Targets registry | `anicca-oss/skills/anicca-imitation-targets/SKILL.md` |

---

**END OF profiles/cook-loop/env-map.md.**
