# Nosana shelter state persistence (S4)

Externalizes Franklin's Nosana shelter state so a rebuilt job container restores the same
identity, ledgers, and audit trail a torn-down one had. This is the prerequisite for Nosana:
Nosana gives a job's compute no cross-job persistent volume (see "Why not a Nosana persistent
volume" below) — every job posting starts from a clean filesystem. Without this, every rebuild
would lose the wallet manifest, the ledgers, and the audit trail, i.e. lose the money and the
history behind it.

## What round-trips, and what never does

| Synced (addresses/amounts only, all already public on-chain) | Never synced |
|---|---|
| `wallet-manifest.json` — Solana **address only** | The private key / seed / base58 secret |
| `shelter-cost.jsonl` (settled lease costs + corrections) | |
| `nosana-renewal-intents.jsonl` (extend/repost intent + settlement) | |
| `nosana-funding-intents.jsonl`, `nosana-funding.jsonl` (NOS-swap intent + settlement) | |
| `nosana-deploy-intents.jsonl` (deploy intent + settlement — see `ledger-files.mjs` for why this fifth file is in scope even though the S4 brief names only four categories) | |

The restored agent resolves its own key locally exactly as it does today —
`resolveSolanaSecret` / `$ANICCA_HOME/.blockrun/.solana-session` — this layer never participates
in that resolution, only in cross-checking the result against the manifest (`restoreState`'s
`addressesMatch`).

## Why not a Nosana persistent volume

Verified live 2026-07-25 against Nosana's own docs and the `nosana-ci/nosana-cli` source (`main`
branch):

- The **`resources`** property only pulls data **IN** at job start (HuggingFace repos, S3-compatible
  objects) — learn.nosana.com/deployments/jobs/job-definition/resources.html: *"You can use the
  resources property of the Nosana Job Definition to load external resources into your jobs."*
  There is no matching "push resources out" counterpart.
- `container/create-volume` is named in the job-definition schema table (`type` ✅ `"container/run"`
  or `"container/create-volume"`) with **no args table and no worked example anywhere in the
  docs** — confirmed by fetching `schema.html` directly. The CLI source explains why:
  `Provider.ts`'s `taskManagerVolumeCreateOperation` names the volume `flow.id + '-' + op.args.name`
  — keyed to **that one job run's own flow id** — and the accompanying comment says the stop/delete
  step is deliberately skipped only "because it will delete the volume that might be used by other
  operations **in the group**" (i.e. other ops of the *same* job), not across separate job postings.
- The CLI's own `-o/--output` flag — the one feature that *would* have used `create-volume` to shuttle
  a finished job's output to persistent storage (Pinata-pinned IPFS) — is **currently dead code** in
  `nosana-ci/nosana-cli`'s `src/cli/job/post/action.ts` (`main`, fetched live): the function returns
  immediately with `formatter.throw(OUTPUT_EVENTS.OUTPUT_ARTIFACT_SUPPORT_INCOMING_ERROR, { error:
  new Error('artifact support coming soon!') })` **before** ever reaching the create-volume/IPFS-pin
  code beneath it.

Conclusion: there is no real, shipped, cross-job persistent-volume mechanism on Nosana today. An
external store is not an optional nicety here — it is the only way state survives a rebuild.

## The store: a private git repo, not S3 or IPFS

`github-store.mjs` is the one real `RemoteStateStore` implementation, backed by
[`Daisuke134/franklin-shelter-state`](https://github.com/Daisuke134/franklin-shelter-state) (private,
created 2026-07-25). Checked before choosing this, 2026-07-25:

- **No S3-compatible credentials exist anywhere on this machine**: no `~/.aws/{credentials,config}`,
  no `AWS_ACCESS_KEY_ID`/`S3_BUCKET`/`R2`/`B2`/`BACKBLAZE` env vars, no `aws`/`rclone`/`mc` binary.
- **No IPFS/Pinata/web3.storage/nft.storage credentials or daemon exist either**: no matching env
  vars or config files anywhere in the repo or home directory, `ipfs` is not installed.
- `gh` **is** already authenticated (`repo`+`gist` scopes) and plain `git` over https already works
  against a private repo with zero extra setup — verified live against an existing private repo on
  the same account. This account already uses a private git repo for exactly this kind of thing:
  `Daisuke134/anicca-genesis` ("Hermes runtime state, crons, ledgers... auto-updated") and
  `Daisuke134/anicca-monk-factory-state` are both live precedents.

No new provider, no new paid dependency, no new credential. `store.mjs`'s `createLocalFsStore` is
the injectable test double every unit test in `__tests__/` uses instead.

## Merge/dedupe rule

One rule (`merge.mjs`'s `mergeAppendOnly`), used symmetrically by both directions: the **receiving**
side's existing lines are never reordered, rewritten, or dropped; any row from the other side whose
`dedupeKeyForRow` (built from real fields — `ts` + `jobAddress`/`guessedAddress`/`address` +
`signature` + `intentId`; correction rows key on what they correct) isn't already present gets
appended, byte-for-byte, at the tail. Deterministic, idempotent (a second run always appends
nothing new), and never silently prefers one writer over another — see
`__tests__/github-store.test.mjs`'s real two-writer race test.

## Commands

```bash
# Report what would be pushed, without pushing (default).
ANICCA_HOME=$HOME/.blockrun bin/citizen-state snapshot --dry

# Actually push local ledgers + a fresh wallet manifest to the remote.
ANICCA_HOME=$HOME/.blockrun bin/citizen-state snapshot --live

# Report what would be restored, without writing (default).
ANICCA_HOME=$HOME/.blockrun bin/citizen-state restore --dry

# Actually restore into the live state dir (or --target-dir DIR for a clean location).
ANICCA_HOME=$HOME/.blockrun bin/citizen-state restore --live
```
