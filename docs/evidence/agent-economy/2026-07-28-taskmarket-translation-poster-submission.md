# TaskMarket external translation-pricing poster submission evidence

## Economic boundary

| Field | Value |
|---|---|
| Task | `0x517d20d71b937485c56d7298538ab0b6aa7fbc149a09f02fee83bbcf4d79e281` |
| Requester | `0xc0566E4F2760cD01D53727cB16D3a829C5787a63` |
| Gross / net reward | `4.000000 / 3.700000 USDC` |
| Mode | public competitive bounty |
| Submission count at selection | `38` |
| Award count before and after this delivery | `0` |
| Verified external revenue | `$0.00` |

Delivery is acquisition evidence, not revenue. Only an external requester award
and independently finalized native-USDC receipt can advance 13c.

## Artifact acceptance

Version 1 was not submitted because it added unrequested readable grid labels.
Version 2 removes those labels and contains exactly three unarchived files:

| File | Local SHA-256 | Bytes | Remote readback |
|---|---|---:|---|
| `translation-from-words-to-outcomes.png` | `de997d81fd13eaf9c30e406258274e59341954e135e7950ddf4e5e1a2f9a81b3` | `2682281` | exact hash/size, `image/png`, role `final` |
| `concept-note.md` | `698aaecb266f6cd6f29ed26bf7fa6763f34ef74661b8a3ca7984906ea52cecc4` | `1697` | exact hash/size, `text/markdown`, role `final` |
| `sources.md` | `9e9587f3b3950db6834674a45dc8114bb1b016c9cba3db8a047c6f6dc42900e3` | `719` | exact hash/size, `text/markdown`, role `final` |

The `1024×1536` RGB PNG uses the locked dictionary/letterpress world, two inks,
distinct dated figures, and a per-word grid that becomes one complete bound
outcome. Visual inspection and segmented OCR confirm the required copy.
An 8% color-distance measurement classifies `45.0714%` of pixels as the sampled
aubergine ground, above the 40% quiet-ground floor.

Model: OpenAI GPT Image 2. Version 2 is a targeted image edit.

## Live submission and chain receipt

| Field | Value |
|---|---|
| Submission | `37810838-de62-44f4-8468-449e9d662737` |
| Worker | `0xd7Db94062AFec8a86F70250B931C77619acf8937` |
| Submitted at | `2026-07-28T06:45:43.485Z` |
| Deliverable hash | `0xd7da9d58ab1eb962e26ab3afe42149f1ca97291b407ab983b57ad3fbeb2e5ef4` |
| Base tx | `0xa6cc991d8076802bf751c83729125d28cfb13e8e82c899a5f19f77ba96683527` |
| Independent receipt | block `49215899`, status `0x1`, 11 confirmations at readback |

Remote readback returned the owned worker and three final artifacts whose
hashes, sizes, and MIME types exactly match local files.

## Automation readback

Only the existing TaskMarket label was kicked. It returned:

`runs=11 / tasks_seen=6 / pending=6 / recorded=0 / exit=0 / stderr empty`

No pre-existing Life Manager loop was stopped.

## Sources

- [TaskMarket protocol documentation](https://docs-market.daydreams.systems/llms-full.txt)
- [TaskMarket maker guide](https://gist.github.com/LordSecretive/49d438b844b390fccd95549865490abe)
- [Grand View Research market report](https://www.grandviewresearch.com/industry-analysis/language-services-market-report)
- [Translated research](https://translated.com/research)
- [Base receipt](https://basescan.org/tx/0xa6cc991d8076802bf751c83729125d28cfb13e8e82c899a5f19f77ba96683527)
