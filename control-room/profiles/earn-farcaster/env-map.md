# profiles/earn-farcaster/env-map.md

## § 1. Env vars

| Key NAME | Required | Source | Used for |
|---|---|---|---|
| `BWS_ACCESS_TOKEN` | yes | `~/.openclaw/.env` | vault unlock |
| `OPENROUTER_API_KEY` | yes | Bitwarden vault | LLM for cast composition |
| `NEYNAR_API_KEY` | yes | Bitwarden vault | post / read casts via Neynar |
| `FARCASTER_FID` | yes | env per instance | account FID, e.g., `123456` |
| `FARCASTER_SIGNER_UUID` | yes | Bitwarden vault | Neynar managed signer for posting |
| `FARCASTER_DISPLAY_NAME` | yes | env per instance | e.g., `Anicca Genesis` |
| `FARCASTER_USERNAME` | yes | env per instance | e.g., `anicca-genesis` |
| `CDP_API_KEY_ID` | yes | Bitwarden vault | sign tips |
| `CDP_API_KEY_SECRET` | yes | Bitwarden vault | sign tips |
| `CDP_WALLET_SECRET` | yes | Bitwarden vault | wallet identifier |

## § 2. Identity (per-instance Farcaster account)

Each Anicca instance has its **own** Farcaster account:

| Instance | Username | FID |
|---|---|---|
| `anicca-genesis` | `anicca-genesis` | <fid from Neynar signup> |
| `anicca001` | `anicca001` | <fid from Neynar signup> |
| `anicca002` | `anicca002` | <fid from Neynar signup> |

Account creation is part of `templates/new-instance.md` provisioning
(currently manual; automation TBD when Neynar exposes account creation API).

**Operator's personal Farcaster (`@daisuke134` if any) is never used here.**
NHOSS-pure.

## § 3. Persona config

`~/.hermes/profiles/<instance>-earn-farcaster/persona.md` defines the cast
tone. Default seed:

```
- Voice: terse, honest, no marketing-speak
- Topics: agent autonomy progress, x402 economics, Anicca colony health
- Avoid: vanity metrics, sycophantic replies, financial advice
- Cast format: ≤320 chars, often a single concrete fact + 1 number
- Reply policy: only reply when I can add a verifiable claim
```

## § 4. Frame config

`~/.hermes/profiles/<instance>-earn-farcaster/frame-config.json`:

```json
{
  "frames": {
    "/frame/research": { "price_usdc": "0.10", "ttl_sec": 60 },
    "/frame/imitate": { "price_usdc": "0.20", "ttl_sec": 120 }
  }
}
```

## § 5. Cross-references

| Concept | Authority |
|---|---|
| Vault policy | `control-room/shared/security.md` § 4 |
| Neynar managed signer | `docs.neynar.com/reference/post-managed-signer` |
| Frame spec | `docs.farcaster.xyz/reference/frames/spec` |

---

**END OF profiles/earn-farcaster/env-map.md.**
