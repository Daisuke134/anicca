# Verification Report — capafy-skills-landing

## Proof Obligations

| Obligation | Result | Evidence |
|---|---|---|
| PROP-L1 | proved | 6-test unittest suite covers filtering, no-online failure, and invalid content boundaries |
| PROP-L2 | proved | generated live HTML contains 21 escaped cards and exact UTM links |
| PROP-L3 | proved | Playwright mobile light/dark and desktop screenshots; 21 cards; no horizontal overflow |
| PROP-L4 | proved | consecutive live builds produced MD5 `011a3615ea20d91532cffdb137f116dc` |
| PROP-L5 | proved | production curl HTTP 200 and 21 Capafy links; CTA browser navigation HTTP 200 |
| PROP-L6 | proved | `bash -n` and ShellCheck PASS; command runs before cadence gate and STEP5 uses landing URL |
| PROP-L7 | proved | branch diff has zero `.github/workflows` paths |

## Summary

All declared obligations are proved. Runtime evidence covers live Capafy input, actual Netlify production output, mobile/desktop pixels, light/dark media, CTA navigation, daily production redeploy, and recovery of the initially misdirected deploy to observable HTTP 404 state.
