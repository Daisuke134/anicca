# TaskMarket external voice-poster submission evidence

## Economic boundary

| Field | Value |
|---|---|
| Task | `0x2b266ced9339168e3c4354fe552dc669e8940ac1ebb0fbb3999f9c782ef52d81` |
| Requester | `0xc0566E4F2760cD01D53727cB16D3a829C5787a63` |
| Gross / net reward | `4.000000 / 3.700000 USDC` |
| Mode | public competitive bounty |
| Submission count before this delivery | `36` |
| Award count before and after this delivery | `0` |
| Verified external revenue | `$0.00` |

The task requires a real-model poster showing one recorded studio hour becoming
a licensed voice asset that keeps paying its creator. Submission is acquisition
and delivery evidence only. It is not revenue until the external requester
awards it and a finalized native-USDC transfer independently matches.

## Artifact acceptance

The deliverable contains exactly three unarchived files:

| File | Local SHA-256 | Bytes | Remote readback |
|---|---|---:|---|
| `record-once-earn-when-it-speaks.png` | `bd35adfe0759451726e1c991f3743b1d9696fa8646c4473915d8089d641b7c74` | `2289334` | exact hash/size, `image/png`, role `final` |
| `concept-note.md` | `64301852a6230c45d5e1498ef6ca77bf3f48ac70e7210ba7859de30a41485f09` | `1704` | exact hash/size, `text/markdown`, role `final` |
| `sources.md` | `2e730d6fb5ef30a9fad186eaf572d667cdde3cc0aaf52c5a2ac395c5622cb5e8` | `625` | exact hash/size, `text/markdown`, role `final` |

The raster is `1003×1568`, RGB PNG. Visual inspection confirms the
left-to-right voice→authored-asset transformation, the non-default oxblood
ground, the named direction, and gallery-poster hierarchy. Tesseract read back
the headline, `$22M+`, `10,400+`, and the complete source line. A tight 8%
ImageMagick color-distance measurement classified `70.2041%` of pixels as the
oxblood ground, above the requested 40% quiet-ground floor.

Model: OpenAI GPT Image 2 through the built-in image generation path.

## Live submission and chain receipt

| Field | Value |
|---|---|
| Submission | `822f34f9-01f4-4267-a78c-dbd5bd7e41c6` |
| Worker | `0xd7Db94062AFec8a86F70250B931C77619acf8937` |
| Submitted at | `2026-07-28T06:30:21.434Z` |
| Deliverable hash | `0x225edf6d1157ab08bc63b6cee5b6d0246b8dec9338b7992ca56925d6d2c4da44` |
| Base tx | `0x5f8ce9d62e4f3cffc830c1fb4cde4319e27b3c152b8e122c7484c1b8a3c6d370` |
| Independent receipt | block `49215438`, status `0x1`, 13 confirmations at readback |

Remote readback returned the owned worker address, three final artifacts, and
exact local hashes, sizes, and MIME types.

## Automation readback

After delivery, only the existing TaskMarket label was kicked. It returned:

`runs=7 / tasks_seen=4 / pending=4 / recorded=0 / exit=0 / stderr empty`

No pre-existing Life Manager loop was stopped. A later award must pass the
external-requester, owned-worker, exact-award, finalized-Base-receipt, and
exactly-once gates before the ledger can advance.

## Sources

- [TaskMarket protocol documentation](https://docs-market.daydreams.systems/llms-full.txt)
- [TaskMarket maker guide](https://gist.github.com/LordSecretive/49d438b844b390fccd95549865490abe)
- [ElevenLabs voice actor payouts](https://elevenlabs.io/blog/introducing-voice-actor-payouts)
- [Base receipt](https://basescan.org/tx/0x5f8ce9d62e4f3cffc830c1fb4cde4319e27b3c152b8e122c7484c1b8a3c6d370)
