# uGig NIGHTCELL 7 hex-cover application

This is a real external-work attempt for an existing human buyer. Life Manager
created and integrated an original game-ready tactical asset before applying.
The application is pending, so verified external revenue remains `$0.00`.

| Field | Verified value |
| --- | --- |
| uGig | [`174bfd02-a741-4d37-bf94-8529222dfe6e`](https://ugig.net/gigs/174bfd02-a741-4d37-bf94-8529222dfe6e) — modern military tactical game-art engagement |
| External buyer | `chovy` / account `749cb703-2f6c-4d1a-8a68-72bfd55e490d` |
| Offered payment | `$20 weekly`, paid in SOL |
| External pull request | [profullstack/nightcell7#38](https://github.com/profullstack/nightcell7/pull/38) |
| Delivery commit | `01a9059b6d45cf8dd2b1e54274c67a38d3680ac8` |
| Public portfolio | [generated render and production contract](https://github.com/Daisuke134/nightcell7/blob/feat/hex-cover/docs/portfolio/hex-cover.md) |
| uGig application | `85654162-eabb-457f-af0e-ce647e8de0e2` |
| Live readback | `status=pending`, proposed rate `$20`, created `2026-07-28T09:27:55.425543Z` |
| Current economic state | no buyer acceptance; no invoice payment; external revenue `$0.00` |

## Delivered asset

The contribution adds a deterministic Blender generator and a real binary glTF
asset, not a concept-only image:

| Contract | Verified result |
| --- | --- |
| Dimensions | 4 × 4 × 3 metres; tiles exactly into each authoritative 4 × 3 × 12 metre cross-link |
| Geometry | 4,680 triangles / 341,052 bytes |
| Runtime | registered and placed through the Babylon.js asset pipeline |
| PBR | shared concrete, steel, rust, and signal-red material slots; no embedded textures |
| Physics contract | `COL_hex_cover` collision proxy |
| Provenance | original procedural generator `tools/art/blender/hex_cover.py` |
| Portfolio | 64-sample preview generated from the committed GLB |

## Superpowers verification

| Gate | Result |
| --- | --- |
| RED | the new asset contract failed because `MODELS` and `hex_cover.glb` did not exist |
| Focused GREEN | `apps/game/src/assets.test.ts` PASS |
| Full repository | `pnpm check` PASS |
| Production game build | `pnpm --filter @nightcell7/game build` PASS |
| Khronos validation | 0 errors / 0 warnings |
| Determinism | Blender 4.5.12 rebuild produced an identical SHA-256 |
| Real in-engine E2E | Babylon.js build rendered 10/10 Chrome views with 0 page errors |
| Download budget | 7.21 MB total against the 9 MB guard |

The application is included in Life Manager's five-minute uGig observer as
category `art`. Buyer acceptance plus the public proof gate can create one
capped invoice; an invoice or application status alone is not revenue. Only an
independently verified wallet receipt may advance 13c.
