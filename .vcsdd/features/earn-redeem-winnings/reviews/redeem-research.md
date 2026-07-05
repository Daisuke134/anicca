# Polymarket redeem "invalid authorization" — root-cause research (read-only)

Date: 2026-07-05. Method: docs.polymarket.com (llms.txt index + relayer-openapi.yaml,
firecrawl), installed SDK source read (`polymarket` 0.1.0b13 in `.venv-pysdk`), our own
`redeem.py` / `v2_mint_deploy.py`, and `gh search` across public GitHub repos that
implement the same relayer flow. No mutation, mint, delete, or redeem was executed.

## 1. The two separate credential systems (this is the core confusion)

| | CLOB API credentials | Relayer API Key |
|---|---|---|
| Shape | `{apiKey, secret, passphrase}` (HMAC) | `{apiKey (uuid), address}` (plain header, no HMAC) |
| Minted via | CLOB **L1** SIWE — EIP-712 `ClobAuthDomain`/`ClobAuth`, `POST/GET clob.polymarket.com/auth/api-key` | **Gamma auth** — a *different*, EIP-191 `personal_sign` SIWE against `gamma-api.polymarket.com`, session-cookie based |
| Used for | L2 CLOB headers (`POLY_API_KEY/PASSPHRASE/SIGNATURE/TIMESTAMP`) — trading, balances | Relayer headers (`RELAYER_API_KEY` + `RELAYER_API_KEY_ADDRESS`) on `relayer-v2.polymarket.com` — wallet deploy, batches, `/submit` |
| SDK method that touches it | `polymarket._internal.actions.auth.fetch_api_keys` / `delete_api_key` → `secure_clob.get_json("/auth/api-keys")` (**CLOB host**) | Not wrapped by the `polymarket` pip package at all — no `list`/`create`/`delete` method exists for it |
| Cap | none documented | **max 100 per address**, created via Gamma auth only (docs, verbatim below) |

Source (primary, exact quote), `https://docs.polymarket.com/api-spec/relayer-openapi.yaml`
(also mirrored at `docs.polymarket.com/api-reference/relayer-api-keys/get-all-relayer-api-keys.md`):

> "Relayer API keys let a user authenticate requests to relayer endpoints without Gamma
> auth. However, **Relayer API keys can only be created using Gamma auth. Every address
> can create a maximum of 100 keys.** ... `RELAYER_API_KEY_ADDRESS` must match the address
> that owns the key."

Source, `https://docs.polymarket.com/api-reference/authentication.md`: CLOB L1/L2 auth is
described purely in terms of `POLY_ADDRESS/POLY_SIGNATURE/POLY_TIMESTAMP/POLY_NONCE` (L1)
and `POLY_API_KEY/POLY_PASSPHRASE/...` (L2) against `clob.polymarket.com` — this is a
wholly separate registry from the relayer's `RELAYER_API_KEY`.

Source, `https://docs.polymarket.com/trading/deposit-wallets.md` ("Common Issues" section):

> "Relayer auth and CLOB auth are independent. Use the auth method required by your
> relayer environment for `/submit`. Use CLOB L1/L2 authentication for order and balance
> endpoints. **Do not reuse relayer cookies or headers as CLOB auth.**" (and implicitly:
> not the reverse either)

**Conclusion of finding ②** ("`fetch_api_keys()` の既存キー再利用 → 同じ invalid
authorization"): this was never going to work. `fetch_api_keys()` / `delete_api_key()`
in the installed SDK only talk to `clob.polymarket.com/auth/api-keys` — the CLOB
credential registry. They cannot see or touch the relayer's `RELAYER_API_KEY` registry at
all. Reusing a CLOB apiKey as a `RelayerApiKey` (or vice versa) will always 401 on
`/submit` with "invalid authorization" because the relayer validates against its own,
completely different key store.

## 2. Builder API Key is the other legitimate path — also requires a browser once

`POLY_BUILDER_API_KEY/PASSPHRASE/SIGNATURE/TIMESTAMP` (HMAC, same shape as CLOB creds) is
the *other* accepted auth for `/submit` (per the relayer OpenAPI spec's documented header
set). But per `https://docs.polymarket.com/builders/overview.md` and
`.../builders/api-keys.md`, a Builder profile is created at
`polymarket.com/settings?tab=builder` — again a browser/Gamma-authenticated action, not a
script-only flow. `https://docs.polymarket.com/trading/gasless.md` confirms: "Already have
a builder signing key? Your existing HMAC-based builder API key keeps working with the
Relayer." Neither Builder API Key nor Relayer API Key can be legitimately minted by a pure
CLOB-L1-SIWE script; both trace back to a real polymarket.com login.

## 3. What "Gamma auth" concretely is, reverse-engineered from working code (3 independent sources)

None of this is documented as a public POST endpoint in the OpenAPI spec (only `GET
/relayer/api/keys` is documented — confirmed no `POST`/`DELETE /relayer/api/keys` path
exists in `relayer-openapi.yaml`). But three independent, mutually-corroborating
implementations converge on the same undocumented-but-real flow:

1. `github.com/polymas/go-polymarket-sdk`, `examples/relayer_apikey_mint/main.go` (full
   working Go example, cache→ping→SIWE-login→list-or-mint):
   - `GET https://gamma-api.polymarket.com/nonce` → `{nonce}`
   - Build an EIP-4361 SIWE message (`domain=polymarket.com`, `statement="Welcome to
     Polymarket! Sign to connect."`, `uri=https://polymarket.com`, `chainId=137`, the
     nonce, `issuedAt`, `expirationTime`), **sign it with plain EIP-191 `personal_sign`**
     (`accounts.TextHash` in go-ethereum — NOT EIP-712 typed data, which is what the CLOB's
     `ClobAuth` uses)
   - `bearer = base64(json(msg) + ":::0x" + hex(signature))`
   - `GET https://gamma-api.polymarket.com/login` with `Authorization: Bearer <bearer>` →
     sets a session **cookie** in the client's cookie jar (this cookie *is* "Gamma auth")
   - With that cookie: `GET https://relayer-v2.polymarket.com/relayer/api/keys` → list
     existing keys for the address; if non-empty, **reuse the most recent one** (sorted by
     `createdAt`); only if empty, `POST https://relayer-v2.polymarket.com/relayer/api/auth`
     with body `{}` → mints a fresh `{apiKey, address}`.
   - The comment block states the exact rationale for list-before-mint: minting blindly
     burns into the 100-key cap.
2. `github.com/ZeroBlind2025/cryptoarbitrage`, `copy_trader.py` (`_get_relay_headers`,
   `_validate_relayer_key`): confirms `RELAYER_API_KEY` + `RELAYER_API_KEY_ADDRESS` are
   plain headers (no HMAC), confirms "Relayer API keys have NO daily limit (confirmed by
   Polymarket) — only per-minute (25 req/min on `/submit`) and min-gap limits," and — the
   single most load-bearing line for our bug — `# Ensure checksummed address — relay does
   exact string match`, i.e. **the relayer 401s if `RELAYER_API_KEY_ADDRESS` isn't
   byte-for-byte identical to the address the key was minted under.**
3. `github.com/sigma-quantiphi/polymarket-pandas`, `_relayer.py`: independently documents
   the same `RELAYER_API_KEY`/`RELAYER_API_KEY_ADDRESS` header pair and a "prefer Builder
   HMAC, fall back to Relayer API Key" priority, matching the official docs' "Builder API
   Key or Relayer API Key" wording on `/submit`.

## 4. Our own `redeem.py` already implements the correct flow — but has the exact anti-pattern flagged above

Read `~/.anicca-founder/skills/earn/polymarket-trade/redeem.py:199-273` and the sibling
`v2_mint_deploy.py` (the script the team says "proved live" for wallet deployment):

- `_mint_relayer_api_key()` (redeem.py:199) does the **correct** Gamma-auth SIWE
  (`gamma-api.polymarket.com/nonce` → EIP-191 `encode_defunct` personal-sign → base64
  bearer → `gamma-api.polymarket.com/login` → `relayer-v2.polymarket.com/relayer/api/auth`
  POST) — this matches source #1 above exactly, field-for-field. This is NOT the bug.
- **But `build_client()` (redeem.py:245-273) calls `_mint_relayer_api_key()` unconditionally
  on every invocation** — there is no `GET /relayer/api/keys` list-and-reuse step, no local
  cache, and no liveness ping first. Every single `build_client()` call — i.e. every EARN
  loop tick / every retry / every one of your "5 tries" — **mints a brand-new relayer key**.
  This is the precise anti-pattern the go-sdk reference's own comments call out as the
  reason to list-before-mint. Repeated redeem attempts (5 tries × however many
  build_client() calls per try) is a very plausible way to have burned through the
  100-key cap that "① 手動 SIWE mint" then hit directly.
- `v2_mint_deploy.py:63` builds `RelayerApiKey(key=api_key, address=ADDR)` where `ADDR =
  acct.address` (the locally-computed checksummed EOA address) — **neither script ever
  reads back the `address` field from the mint response** (`data.get("address")`) to
  confirm it's identical to `acct.address`. Given source #2's explicit warning that "relay
  does exact string match," this is the single most concrete, checkable next step: log
  `data` from the `POST /relayer/api/auth` response in full and diff its `address` field
  against `acct.address` byte-for-byte (case included) before assuming they match. Since
  `v2_mint_deploy.py`'s wallet-deployment DID succeed live with this exact same
  construction, the field is *probably* fine in the normal case — but it is the one part
  of the payload neither script defensively verifies, and it is cheap and safe to verify
  (a `GET /relayer/api/keys` call, read-only) before the next attempt.

## 5. Why EARN-1 succeeded and later attempts didn't (most likely explanation, clearly flagged as inference, not a doc citation)

No primary source documents an anti-abuse lockout for rapid re-minting, so this part is
inference from the evidence above, not a citation:
- EARN-1's 3 successful redeems each ran `build_client()` → fresh mint → immediately used
  that same key for `/submit` in the same process — one mint, one use, success.
- Between EARN-1 and now, the team describes "mint 乱発" (repeated manual minting across
  multiple debugging attempts). Every one of those attempts, plus every `redeem.py` run/
  retry, mints yet another key. Once the account is at or near the **100-key cap**, the
  most parsimonious explanation consistent with all observed symptoms (mint sometimes
  still returns 200 with a key, but `/submit` then 401s "invalid authorization" even for a
  key minted seconds earlier) is that the account has crossed into a state — cap reached,
  or a rate/abuse guard on repeated Gamma logins from the same address in a short window —
  where either the mint silently stops actually registering new usable keys, or the Gamma
  login/session itself is being rejected upstream of the mint (note: `redeem.py:235` and
  `v2_mint_deploy.py:46` do NOT check the `/login` response status before proceeding to
  mint — a silently-failed Gamma login would still let `POST /relayer/api/auth` run, and
  depending on server behavior that could itself explain a subsequently-invalid key).

## 6. Concrete, doc-grounded fix direction for `redeem.py` (design only — not implemented, per read-only instruction)

1. **List-before-mint, exactly like the go-sdk reference:** after the Gamma
   `/login`, call `GET https://relayer-v2.polymarket.com/relayer/api/keys` (cookie auth,
   documented endpoint) first. If it returns a non-empty array, take the entry with the
   newest `createdAt` and reuse its `{apiKey, address}` — do not mint. Only call `POST
   /relayer/api/auth` when the list is empty.
2. **Cache the winning key** (e.g. a small JSON file next to `AGENT_ENV`, keyed by EOA
   address) and on the next run, first try `GET /relayer/api/keys` with the cached
   `RELAYER_API_KEY`/`RELAYER_API_KEY_ADDRESS` headers (no cookie/login needed) — 200 means
   still alive, reuse; 401 means re-run the Gamma-login → list-or-mint path once. This is
   the exact 3-step priority (cache+ping → SIWE login+list-or-mint → persist) implemented
   in `polymas/go-polymarket-sdk`'s example — copy that state machine, not just the mint
   call.
3. **Verify the address field defensively**: after either list or mint, log/assert
   `returned["address"].lower() == acct.address.lower()` (or, safer given "exact string
   match" is documented, assert exact equality first and only fall back to case-insensitive
   with a loud warning) before constructing `RelayerApiKey(...)`.
4. **Check the `/login` response status** before proceeding to list/mint; treat a
   non-2xx there as a hard failure rather than silently continuing.
5. Given there is **no documented or working DELETE for relayer keys anywhere** (public
   OpenAPI spec has no delete path; none of the ~15 third-party repos surveyed implement
   one either — one independent debugging log, `cploveless123/workspace-backup/memory/
   2026-06-07.md`, explicitly records `POST /relayer/api/keys` → `405 (no creation
   endpoint)`, confirming that path is a dead end for both create and delete), the 100-key
   cap is **not recoverable by pruning** — the only sustainable fix is #1/#2 (stop
   minting per-call) so the existing ~N keys already burned are simply left alone and one
   of them (or one new one, minted exactly once) is reused going forward.

## Sources referenced (all fetched live via firecrawl/gh this session)

- `https://docs.polymarket.com/api-spec/relayer-openapi.yaml` (full relayer OpenAPI spec —
  confirms `/submit` auth headers, 401 "invalid authorization" example, the 100-key-cap
  note, and that only `GET /relayer/api/keys` is a documented path)
- `https://docs.polymarket.com/api-reference/relayer-api-keys/get-all-relayer-api-keys.md`
- `https://docs.polymarket.com/api-reference/relayer/submit-a-transaction.md`
- `https://docs.polymarket.com/trading/deposit-wallets.md`
- `https://docs.polymarket.com/trading/gasless.md`
- `https://docs.polymarket.com/trading/ctf/redeem.md`
- `https://docs.polymarket.com/api-reference/authentication.md`
- `https://docs.polymarket.com/builders/overview.md`, `.../builders/api-keys.md`
- `github.com/polymas/go-polymarket-sdk` — `examples/relayer_apikey_mint/main.go`
- `github.com/ZeroBlind2025/cryptoarbitrage` — `copy_trader.py`
- `github.com/sigma-quantiphi/polymarket-pandas` — `polymarket_pandas/mixins/_relayer.py`
- `github.com/RobotTraders/bits_and_bobs` — `polymarket_redeem.py` (independent, working
  redeem-all-positions reference script using `BuilderApiKeyCreds`)
- `github.com/cploveless123/workspace-backup` — `memory/2026-06-07.md` (another party's
  debugging log independently hitting the same `POST /relayer/api/keys` 405 / Gamma-auth
  401 wall)
- Installed SDK, read directly: `polymarket/_internal/actions/relayer/{submit,gasless,
  auth,nonce}.py`, `polymarket/_internal/actions/auth.py`, `polymarket/_internal/l1_auth.py`,
  `polymarket/_internal/wallet.py`, `polymarket/auth.py`, `polymarket/clients/secure.py`
- Our own: `~/.anicca-founder/skills/earn/polymarket-trade/redeem.py`,
  `~/.anicca-founder/skills/earn/polymarket-trade/v2_mint_deploy.py`
