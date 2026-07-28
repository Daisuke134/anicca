# TaskMarket ice-core poster — live submission evidence

## Outcome

The dedicated external-work wallet submitted a seventh real deliverable to the public TaskMarket bounty below. This proves live discovery, artifact upload, marketplace readback, and Base submission. It is not revenue until the external requester awards the work and the finalized USDC transfer is independently verified.

| Field | Verified value |
|---|---|
| Task | `0x4def3ba5993528738570583e4b2586c631f3762b8821f352a5c035b74432ca23` |
| External requester | `0xc0566E4F2760cD01D53727cB16D3a829C5787a63` |
| Worker wallet | `0xd7Db94062AFec8a86F70250B931C77619acf8937` |
| Submission | `a498585f-de59-429d-bbfb-f944d38f0ced` |
| Submitted at | `2026-07-28T06:58:25.974Z` |
| Gross / net reward | `5.000000 / 4.625000 USDC` |
| Submit transaction | `0x0ce87805f1931b04114012bc5d7539eb82bb47deda23fc0e2f3685140e7f4ac0` |
| Base receipt | `status=0x1`, block `0x2eefb18`, 22 confirmations at verification |
| Marketplace state after submit | `46` submissions, owned submission present, `awardCount=0` |
| Ledger bridge after kick | `runs=15`, `tasks_seen=7`, `pending=7`, `recorded=0`, `duplicates=0`, exit `0`, stderr empty |

## Artifact contract

Exactly three files were delivered without an archive:

| File | MIME / dimensions | Local and remote SHA-256 |
|---|---|---|
| `hero.png` | `image/png`, `1254x1254`, sRGB | `45ebb5ac17b9c3302f450a787baa472ce360949a1e0fd3da2952fa4fab9b98f0` |
| `concept-note.md` | `text/markdown` | `89e085b174558ccdf89c6122656cded30a6fa8735a2eef6d6e86bb2deedc8a56` |
| `sources.md` | `text/markdown` | `e71bbaed5d167cb8b5a16120a4d72e72ce4623b7409c8fa2eb7e92fcadf90c9f` |

OCR readback was exactly `2,800 METRES OF ICE HOLDS 1.2 MILLION YEARS.` The corner sample was black-cherry (`mean RGB=0.0438519,0.00222657,0.00246598`), not the prohibited white, pale grey, or navy. The image is square, uses one headline, and introduces no unlocked figures.

## Revenue boundary

The transaction proves a live submission only. The TaskMarket ledger loop correctly returned `pending=7 / recorded=0`; therefore verified external revenue remains `$0.00`. On a later award, the existing loop must re-read the market state, verify a finalized Base USDC `Transfer`, bind it to this external requester and owned worker wallet, and append exactly one six-decimal ledger row.

## Sources

- TaskMarket public task/readback and submission API.
- Beyond EPICA project: https://www.beyondepica.eu/en/
- European Commission CORDIS fact sheet: https://cordis.europa.eu/project/id/815384
- Base mainnet JSON-RPC: https://mainnet.base.org
