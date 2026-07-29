# OSS-SECURITY-BASELINE-1 evidence

## Verdict

**VERIFIED for the Life Manager repository boundary.** The distributable tree
and all six PR gates are clean. Every
historical finding has been classified without placing a raw credential in this
file. Firecrawl, Vibecode, Exa, Anthropic, ElevenLabs, Slack, Google Cloud, and
Sourcegraph no longer leave a known active historical credential.

An external Anicca iOS/API incident remains open: two historical RevenueCat
secret keys still authenticate. RevenueCat is not a Life Manager connector,
metric source, implementation cursor, or repository-retirement gate. The facts
and required external-owner remediation remain visible below.

No loaded Mac loop was stopped, restarted, or moved while credentials were
investigated or rotated.

## Current distributable tree

| Gate | Fresh result |
|---|---|
| Current-tree `gitleaks dir` | `0` findings |
| Current-tree PII-shape scan | `0` findings |
| TruffleHog filesystem + Git history | `0` verified secrets |
| Python unit suite | `153/153 PASS` |
| PR workflow | GitHub Actions run `30437476922`: all six jobs PASS |
| Runtime/browser focused tests | Browser-auth suite `88/88 PASS`; production harness `9/9 PASS` |
| App regression | `669/669 PASS`; all eight deterministic eval suites at `100%` |

GitHub readback:
<https://github.com/Daisuke134/life-manager/actions/runs/30437476922>

## Historical gitleaks adjudication

The full-history report contains `1,628` findings. A finding is not treated as a
live secret merely because a detector matched it; every row is assigned to a
bounded class, and every credential-shaped class is checked against its provider.

| Class | Count | Adjudication |
|---|---:|---|
| Vendored/generated PlantUML material | 1,340 | Generated third-party content; not a runtime credential |
| Public mobile/content identifiers | 78 | Public SDK/content identifiers; not secret authentication |
| Generated browser profile | 23 | Generated local profile material; excluded from the current distributable tree |
| Test fixtures | 11 | Synthetic fixtures; no provider authentication |
| Operational docs | 64 | Historical command/example shapes; candidate-bearing rows separately provider-checked |
| Credential candidates | 25 | Provider-tested; outcomes recorded below |
| Other detector matches | 87 | Reviewed; provider-shaped rows separately provider-checked |
| **Total** | **1,628** | **Unclassified: 0** |

Detector-rule totals independently reconcile to the same report: generic
`1,595`, JWT `17`, Google Cloud `5`, Stripe `4`, curl authorization `3`,
private-key shape `2`, Slack `1`, and Sourcegraph `1`.

## Provider verification and rotation ledger

Raw values, reset links, OTPs, and credential suffixes are intentionally absent.
An HTTP success here means the old credential was genuinely accepted before the
change; an invalid response after the change proves revocation rather than a
dashboard-only visual assertion.

| Provider | Before | Action | After | State |
|---|---|---|---|---|
| Firecrawl current runtime | Authenticated (`200`) | Generated a second-generation runtime key and updated both runtime stores | New key authenticated (`200`) | PASS |
| Firecrawl historical runtime | Authenticated (`200`) | Logged into the historical team and revoked the matching dashboard row | Poll reached `401` (`200 → 200 → 401`) | PASS |
| Firecrawl superseded runtime | Authenticated (`200`) | Revoked both superseded dashboard rows, including the first replacement after it appeared in diagnostic output | Old key reached `401`; replacement remains `200` | PASS |
| Vibecode | CLI user readback authenticated | Regenerated the dashboard API key and atomically updated the runtime store | New key authenticated; old key rejected | PASS |
| Exa | Historical key authenticated but account had no credits (`402`) | Deleted the matching historical dashboard key while preserving the current runtime row | Historical key `401`; current runtime still authenticates | PASS |
| Anthropic | Rejected before this atomic | No active credential to rotate | Provider rejection retained | PASS |
| ElevenLabs | Rejected before this atomic | No active credential to rotate | Provider rejection retained | PASS |
| Slack | `invalid_auth` before this atomic | No active credential to rotate | Provider rejection retained | PASS |
| Google Cloud | Rejected before this atomic | No active credential to rotate | Provider rejection retained | PASS |
| Sourcegraph | Rejected before this atomic | No active credential to rotate | Provider rejection retained | PASS |
| RevenueCat historical secret A | Authenticated as a valid V2-only secret | Rotation pending | Still authenticates | **OPEN** |
| RevenueCat historical secret B | `/v2/projects` returned `200` | Rotation pending | Still authenticates | **OPEN** |

The RevenueCat production consumer is the `Anicca/API` service only. Its
`fetchCustomerEntitlements`, `deleteSubscriber`, customer creation, balance, and
virtual-currency transaction calls all use `/v2/projects/...`; the other checked
production services contain no `REVENUECAT_*` secret. The replacement must
therefore be a V2 key with only the read/write permissions required by those
operations, and it must be installed and proven on that consumer before either
old key is revoked.

## External security basis

RevenueCat's official authentication documentation states:

> “Secret API keys, prefixed `sk_`, should be kept confidential and only stored
> on your own servers.”

It also says to rotate secret keys when there is risk of a leak and documents
that project administrators can create and revoke them:
<https://www.revenuecat.com/docs/projects/authentication>.

Vibecode's official CLI README identifies the account API-key page and the
authenticated `vibecode-cli user` command used for the before/after proof:
<https://github.com/vibecode/vibecode-cli/blob/main/README.md>.

## External Anicca iOS/API incident close condition

The Life Manager repository baseline is already verified. The external incident
closes only after all rows below pass:

| Order | Required proof | Current |
|---:|---|---|
| 1 | Create least-privilege V2 replacement RevenueCat keys from the authenticated project | Blocked by provider password-reset rate limit (`429`); an account-access request was sent by replying to RevenueCat's official reset email |
| 2 | Update local and Railway consumers without stopping existing Mac loops | Pending |
| 3 | Real API readback succeeds through each replacement consumer | Pending |
| 4 | Revoke both historical RevenueCat secrets and observe provider rejection | Pending |
| 5 | Re-run history/current-tree scans and the full PR workflow from the final commit | Pending |
| 6 | Update the canonical spec from `current` to `verified`, commit, push, and read back green CI | Pending |
