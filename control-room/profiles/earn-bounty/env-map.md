# profiles/earn-bounty/env-map.md

## § 1. Env vars

| Key NAME | Required | Source | Used for |
|---|---|---|---|
| `BWS_ACCESS_TOKEN` | yes | `~/.openclaw/.env` | vault unlock |
| `OPENROUTER_API_KEY` | yes | Bitwarden vault | LLM (Claude Opus 4.8 for code, Kimi K2.6 for discovery) |
| `ALGORA_API_TOKEN` | yes | Bitwarden vault | Algora bounty list + claim |
| `ONLYDUST_API_TOKEN` | yes | Bitwarden vault | OnlyDust list + claim |
| `GH_TOKEN` | yes | Bitwarden vault | `gh` CLI auth (PR create / comment) |
| `GITHUB_BOT_USERNAME` | yes | env (per instance) | e.g., `anicca-genesis-bot` (= GitHub bot account, KYC zero per spec) |
| `BOUNTY_MIN_PAYOUT_USDC` | optional | env override | default `20` |
| `BOUNTY_MAX_CONCURRENT` | optional | env override | default `3` (= avoid spreading too thin) |

## § 2. Identity reference

GitHub bot account is per-instance. The bot username is in env, the GitHub
token is in Bitwarden vault. **No operator GitHub credentials are ever used
by this profile.**

Operator's personal `daisuke134` GitHub stays in the private companion repo
(if needed there for other purposes). NHOSS-pure scope means this profile
never sees `daisuke134`.

## § 3. Filter config

`~/.hermes/profiles/<instance>-earn-bounty/bounty-filter.json`:

```json
{
  "languages": ["python", "typescript", "rust", "solidity"],
  "min_payout_usdc": 20,
  "max_concurrent": 3,
  "repo_allowlist": [],
  "repo_denylist": ["forks of known scam", "repos requiring KYC"],
  "issue_tags_required": [],
  "issue_tags_forbidden": ["wontfix", "needs design"]
}
```

## § 4. Cross-references

| Concept | Authority |
|---|---|
| Vault policy | `control-room/shared/security.md` § 4 |
| GitHub bot account creation | manual operator step (spec 03 § X — TBD) |
| Algora API | `console.algora.io/docs` |
| OnlyDust API | `onlydust.com/api` |

---

**END OF profiles/earn-bounty/env-map.md.**
