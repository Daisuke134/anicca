# Verification Architecture — capafy-skills-landing

## Proof Obligations

| ID | Requirement | Tier | Method |
|---|---|---:|---|
| PROP-L1 | REQ-L1/REQ-L6 | 1 | unit tests inject mixed online/offline records and invalid/no-online cases |
| PROP-L2 | REQ-L2/REQ-L3 | 1 | unit tests parse output text for escaped fields, exact UTM links, header, tagline, footer count |
| PROP-L3 | REQ-L4 | 1 | static assertions for viewport, single-column CSS, color-scheme, focus-visible, reduced-motion, no script/external asset references; real browser viewport inspection |
| PROP-L4 | REQ-L5 | 1 | render twice from same records and compare bytes; assert stable case-insensitive name order |
| PROP-L5 | REQ-L7 | 2 | real Netlify production deploy; curl HTTP 200 and link count > 0 |
| PROP-L6 | REQ-L8/REQ-L9 | 1 | `bash -n`; diff/static check for unconditional regen/redeploy and conditional landing BIO target |
| PROP-L7 | REQ-L10 | 0 | git diff contains no `.github/workflows` path |

## Purity Boundary Map

- `filter_online_agents()` and `render_html()` accept data and return deterministic values; unit tests cover them without network or disk.
- `_fetch_agents()` owns the Capafy subprocess boundary.
- `build()` owns the output directory and overwrite boundary.
- Netlify and browser checks run against real production output; mocks cannot satisfy PROP-L5.

## Negative Tests

- offline listing text and ID never appear.
- `<script>` in API text is escaped, never executable markup.
- empty online pool exits non-zero.
- repeated input produces identical bytes.
- deploy verification fails on non-200 or zero card links.
