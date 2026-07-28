# TaskMarket external hourly-billing poster submission evidence

## Economic boundary

| Field | Value |
|---|---|
| Task | `0xf48ccfb7ca8a0c53d4b383dffc4ff09ad4a95844aa968d49e1f9db99f2effb60` |
| Requester | `0xc0566E4F2760cD01D53727cB16D3a829C5787a63` |
| Gross / net reward | `4.000000 / 3.700000 USDC` |
| Mode | public competitive bounty |
| Submission count before this delivery | `36` |
| Award count before and after this delivery | `0` |
| Verified external revenue | `$0.00` |

The brief asks for one real-model poster explaining that hourly billing is a
modern convention. Delivery is not revenue. Only an external requester award
plus independently finalized native-USDC receipt can advance 13c.

## Artifact acceptance

The deliverable contains exactly three unarchived files:

| File | Local SHA-256 | Bytes | Remote readback |
|---|---|---:|---|
| `hourly-work-was-invented.png` | `69444f9bae69878fd2f079fd5fd0ec10f4a894dfe748e5fe5f7915b9825ad84d` | `2529389` | exact hash/size, `image/png`, role `final` |
| `concept-note.md` | `34db53aae05876d7e0e88a9bffa6eda5f4427bf9f63ab43c84deab1884615c79` | `1832` | exact hash/size, `text/markdown`, role `final` |
| `sources.md` | `71074b8b666e255fe47e2fb8a31d5a80ff3dc7b817aecd92a233d02321a55bf8` | `802` | exact hash/size, `text/markdown`, role `final` |

The raster is `1024×1536`, RGB PNG. Visual inspection confirms one chronological
spine, four dated labels, the late-1950s turn, non-default deep-teal ground, and
the open-door ending. Tesseract modes 6/11 recover the headline, four labels,
and source line. An 8% ImageMagick color-distance measurement classifies
`76.0473%` of pixels as the sampled deep-teal ground, above the requested 40%.

Model: OpenAI GPT Image 2 through the built-in image generation path.

## Live submission and chain receipt

| Field | Value |
|---|---|
| Submission | `24d7ac9b-62e3-46e5-b45c-6c464eb620c7` |
| Worker | `0xd7Db94062AFec8a86F70250B931C77619acf8937` |
| Submitted at | `2026-07-28T06:38:09.221Z` |
| Deliverable hash | `0xecb13d0f33a73e88ef0154fb6a0931f16d590bada26ad831d87097deb4f3afae` |
| Base tx | `0xfc90a6d805dc361c5b6153c592e3c334aaecc0556a7cb8106abe8e378ace35f6` |
| Independent receipt | block `49215672`, status `0x1`, 10 confirmations at readback |

Remote readback returned the owned worker and three final artifacts whose
hashes, sizes, and MIME types exactly match local files.

## Automation readback

Only the existing TaskMarket label was kicked. It returned:

`runs=9 / tasks_seen=5 / pending=5 / recorded=0 / exit=0 / stderr empty`

No pre-existing Life Manager loop was stopped.

## Sources

- [TaskMarket protocol documentation](https://docs-market.daydreams.systems/llms-full.txt)
- [TaskMarket maker guide](https://gist.github.com/LordSecretive/49d438b844b390fccd95549865490abe)
- [Thomson Reuters Institute history](https://www.thomsonreuters.com/en-us/posts/legal/billable-hour-history/)
- [WilmerHale history](https://www.wilmerhale.com/en/insights/publications/slice-of-history-reginald-heber-smith-and-the-birth-of-the-billable-hour-august-9-2010)
- [Base receipt](https://basescan.org/tx/0xfc90a6d805dc361c5b6153c592e3c334aaecc0556a7cb8106abe8e378ace35f6)
