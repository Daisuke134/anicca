# Affiliate Agent — Revenue, Runtime, and Architecture SSOT

Last updated: 2026-08-16 JST

Implementation SSOT:

- Design and completion contract:
  `docs/superpowers/specs/2026-08-05-affiliate-agent-design.md`
- Atomic RED → GREEN → E2E plan:
  `docs/superpowers/plans/2026-08-05-affiliate-agent.md`

The ordered backlog in section 9 remains the product-level summary. The atomic
plan is authoritative for implementation order, exact files, tests, commits,
live verification, revenue gates, tenantization, and scale work.

## 0. Objective

Anicca is the company; Life Manager is the product, autonomous agent, and
canonical repository. Life Manager manages physical, mental, and financial
health. Affiliate Agent is one financial-health unit. It improves verified net
position through external affiliate receipts while preserving fees, reversals,
cost, concentration, cash timing, and policy risk. It never equates content,
clicks, estimates, pending commission, or GMV with earned money.

Canonical ownership is the Life Manager repository at `skills/affiliate/`.
The local proof phase has no Affiliate runtime, redirect, secret, or ledger in
`apps/api/` or Railway. The old
`/Users/anicca/profitable-claude/skills/affiliate` tree is migration evidence,
not a production home. Mutable state lives under
`${LIFE_MANAGER_STATE_HOME:-~/.local/state/life-manager}/affiliate/`; credentials,
sessions, provider exports, and ledgers never enter Git.

```mermaid
flowchart LR
  O[Authorized owner] --> LM[Life Manager]
  LM --> P[Physical Health]
  LM --> M[Mental Health]
  LM --> F[Financial Health]
  F --> H[Money-loop harness]
  H --> G[Gig Work]
  H --> A[Affiliate]
  H --> W[Writer]
  H --> N[Future earning loops]
  G --> L[Separate verified ledgers]
  A --> L
  W --> L
  N --> L
  L --> C[CFO projection]
  C --> T[Telegram and product UI]
```

Build one Affiliate Agent inside Life Manager's financial organ that launches in
English first, then operates isolated Japanese and admitted additional-language
market pods. Spanish is the first expansion candidate after English and Japanese;
it is not admitted merely because it has many speakers. The Agent
continuously discovers lawful offers, publishes useful evidence-led content,
attributes clicks and conversions, records external commission
receipts, repairs interrupted runs, and reallocates effort without daily human or
Codex operation.

No two locale pods share one social identity, browser profile, affiliate link,
publication history, attribution cohort, experiment, or operating budget.
English is first. The verified English X
identity is now `sela` / `@selawmqt`, logged in through the isolated
`capafy-mkt-provision` CloakBrowser profile; legacy `@aniccaen` is not an active
X username. Postiz and every external publishing API are out of scope by product
decision. The Agent itself must provision an isolated browser profile, recover or
establish the authorized user account, configure the profile, publish through the
rendered website, and verify the public result. A dedicated Japanese canary is
admitted only after English Gate E0 and uses a different browser profile. Spanish
and every later locale must pass the Locale Admission Gate in section 8 rather
than being created as blind translations.

“End to end” is proved first on the current macOS host. The first graduation
condition is not portability: it is one unattended local run covering authorized
account recovery, affiliate application/approval polling, research, content,
browser publication, acquisition, click attribution, provider reconciliation,
Telegram reporting, recovery, learning, and a real external commission receipt.
After this local Agent earns with positive unit economics, its proven runtime is
packaged for a scratch computer. Installation, encrypted authority inventory,
browser/profile provisioning, and minimal operator credential intake remain Agent
states in that later packaging phase; they are not allowed to delay the local
money loop.

### 0.1 Delivery order: Local → OSS → Cloud

```mermaid
flowchart LR
  L[1. Local Mac<br/>real commission] --> O[2. Open source<br/>one-command install]
  O --> C[3. Cloud web app<br/>phone-only users]
```

The local Mac is the economic laboratory and first production runtime. Code may
be public throughout development, but the project MUST NOT market the loop as a
working money printer until Gate E1 has an external approved commission receipt.
The OSS graduation gate is one scratch-Mac install reproducing the proven local
flow without copying mutable state. The cloud/web-app phase starts only after A2:
four revenue-positive weeks, positive net margin, and zero manual execution.

Cloud is a deployment target for the same state machine, not a second design.
It replaces local launchd with a tenant scheduler and local browser profiles with
isolated remote browser workers while preserving the same provider adapters,
action receipts, money states, policy gate, learner, and Telegram/product report.

The machine cannot guarantee $10,000, $10,000,000, or $100,000,000 revenue. It guarantees
measurable attempts, honest receipts, bounded experiments, compliance gates, and
same-run recovery. Revenue targets are gates, not claims or forecasts.

Affiliate commission belongs only to this Agent's ledger. Writer Agent revenue
continues to mean direct payment for writing; shared research and editorial
techniques do not merge the ledgers.

## 1. Measured current state

| Surface | Observation | Runtime decision |
|---|---|---|
| Amazon Associates Japan | Browser confirmed an existing Amazon.co.jp account for the private SSOT application email. No password exists in Chrome or macOS Keychain; password recovery sent an OTP to the masked matching mailbox, but no currently authenticated Gmail or macOS Mail authority could read it. No Associates application was submitted | `AUTH_RECOVERY_OTP_REQUIRED`; resume the same recovery intent only after authorized mail access is available, then inspect existing Associates state before creating any application |
| Kit | A real PartnerStack application was submitted with truthful Anicca, website, `@selawmqt`, audience-size, channel, country, and region fields. Kit's authenticated application-email reply says it decided not to move forward. It lists four possible fit issues but does not identify one applicant-specific cause: creator-economy audience fit, prohibited promotion methods, inaccessible/insufficient website content, or insufficient promotion detail | `APPLICATION_REJECTED`; do not count approval or reapply unchanged. Reconsider only after an accessible content body, creator-helping-creator audience evidence, and a detailed organic promotion plan are live; coupon, cashback, and paid advertising remain excluded |
| HubSpot / Impact | The official HubSpot flow created a real Impact account, verified the authorized Japanese mobile number, fixed country/timezone/currency to Japan/Tokyo/USD, completed the truthful profile, verified `aniccaai.com`, and rendered the one-shot HubSpot application `In Review`. The original signup generated a password and entered it successfully, but its Keychain writer passed bare `security -w` and stored an empty item. A fresh-tab attempt proved the value was empty before password submission; no credential mismatch or account lock is claimed. Re-sending generic reset again reproduced a redirect chain ending at host `app.impact.com$changepasswordurl`; the official support UI also hid its first backend failure. Posting the documented minimum `email + comment` payload returned `hasErrors=false`, and Impact acknowledged Customer Solutions ticket `868262` | `APPLICATION_PENDING + AUTH_RECOVERY_PROVIDER_DEFECT`; poll the ticket without duplicate requests. Store the replacement only in the private local MD and `keychain://ai.anicca.affiliate.provider.impact/primary`, then require a fresh-tab login before Grammarly or another Impact application |
| Notion / PartnerStack | The official public page still advertises the program, but the live PartnerStack application renders that Notion stopped accepting new affiliates and that all applications are auto-declined for the time being | `PROGRAM_PAUSED`; do not submit a guaranteed rejection. Poll for a real admission-state change before applying |
| ElevenLabs | The official affiliate entry reached ElevenLabs signup. The authorized email passed Arkose, the existing account was recovered through the official email reset, and a storage-isolated fresh login loaded `/app/home` from the Git-external private Markdown credential. Activating the rendered CTA immediately returned `You have an active affiliate account` and a default PartnerStack link. A separate anonymous browser context followed that link to `elevenlabs.io` with PartnerStack referral query parameters and three referral cookies | `ACTIVE_LINK_VERIFIED`; retain the exact link only in private runtime state, forbid paid search on ElevenLabs product terms as rendered by the authenticated UI, and build the first useful disclosed owned placement |
| Rakuten Affiliate | CDP rendered the public home page with `ログイン`; approval state is not observable | `AUTH_REQUIRED`, keep the provider adapter dormant |
| Postiz | A Japanese integration exists, but the product decision excludes Postiz | Do not read, connect, or use it in the Agent; this is not a blocker |
| X identity | Dedicated Affiliate CDP `9326` and authenticated `whoami` prove `@selawmqt`: 128 posts, 27 following, 0 followers. The semantic profile command changed the public name to `sela | AI Tools`, added an English practical-AI bio with affiliate-link disclosure, set `aniccaai.com`, and a second apply returned `changed=false + matches_config=true`. X rejected legacy `@aniccaen` as inactive | Preserve mixed historical posts, keep all future posts English-only, and never use Japanese `@aniccaxxx` or shared daily-driver `@diceai0`; the first post still requires a duplicate-post fence and public readback |
| X publication | The first Affiliate X placement is `LIVE` at `https://x.com/selawmqt/status/2088728168534597644`. The canonical skill verifies `@selawmqt:9326`, requires disclosure plus one `LIVE` owned article URL, writes an effect-possible fence before the click, resolves X's `t.co` anchor through HTTP HEAD to the exact owned URL, and requires status-page readback before `LIVE`. X's April 2026 rules warn that scripted website automation may permanently suspend an account | The initial real publish created one new timeline row but failed closed because X replaced the canonical URL with a multiline shortened display, so raw input-text equality could not pass. Read-only inspection found exactly one disclosed new post and its `t.co` anchor resolved to the exact article URL. Release `90025a3551d75aa1110af63ead8dbd9d93eedc77` then reconciled the existing effect without clicking Publish again and wrote `X_POST_PUBLIC_READBACK`. Keep action caps and immediate account quarantine |
| English source scout | The canonical `sources capture --plan elevenlabs-en` command live-captured six immutable local artifacts: five ElevenLabs official web pages through CRWL and the official `elevenlabs/elevenlabs-python` repository through `gh` | Each receipt stores adapter, locator, locale, evidence class, license, body SHA-256, parser version, observed time, and expiry. The first live run returned `captured=6 + new=6`; after allowlisting stable GitHub fields, an immediate repeat returned `captured=6 + new=0`. Exact hashes are in Git-external `source-captures.jsonl`. CRWL `-q` failed because no LLM provider is configured, so the admitted route deliberately uses deterministic `md-fit` without an LLM. Authenticated X research readback is still missing |
| First English content artifact | The versioned `elevenlabs-en-v1` template binds every price, rights, limitation, and case-study claim to five fresh official source captures. `affiliate content build` requires those support markers and the private executable link, then writes a mode-0600 Git-external artifact without printing its body or link. `content policy` verifies the artifact hash, exact fresh source hashes, disclosure before CTA, one owned HTTPS tracking link, and forbidden guarantees; `owned publish` independently requires the matching `PASS` receipt | Live build produced slug `elevenlabs-plans-for-solo-creators` and content SHA-256 `03089e860af9ed1e35a4656ebc045dd28d00dacc243739fe10b4f46f8e4822e9`. The first real policy attempt failed closed because a broad phrase matcher misclassified an explicit denial of guaranteed earnings. Narrowing the forbidden-claim set to affirmative guarantee phrases made the same artifact pass all five checks. Production commit `a333cf55044dbddf17f906150a173e1ee000aea1` passed Actions run `31906958939`; the installed publisher and CRWL independently read back the title, disclosure, buying checklist, evidence-refresh marker, and exact tracking link. The durable receipt is `LIVE` with rendered SHA-256 `3503c6bede5e059128be49acc90236b22b8014f46b88ca568adc527c09d64b8a`. No provider click or revenue is inferred |
| English foundation publication | `content build-foundation` produces a source-bound, explicitly non-affiliate evaluation guide with no tracking link. `owned publish` accepts only its hash-valid `READY_FOR_PUBLICATION` artifact, writes one deterministic `apps/landing/data/research/<slug>.json`, refuses unrelated dirt or index entries, commits/pushes that exact target, and records public HTML hash only after title plus three marker readback | Live local build returned SHA-256 `eac5ea080817823e3534a14f6b72e16621139dc109aac93095eb8e9ac7c079f0`. Production commit `fd9489bee59946bddc06bb127b2bfca0694d7e61` deployed through GitHub Actions run `31906437192`; the production smoke passed and `https://aniccaai.com/blog/how-to-test-ai-voice-tools-before-you-pay` independently returned the title, no-affiliate disclosure, evaluation marker, and purchase-decision marker. The durable receipt is `LIVE` with rendered SHA-256 `f7055977871bb405af0c491d29c74d41d591f87b95a551425dc5beece07d0039` |
| clip loop | launchd is installed, last exit code is 0, and logs show production/posting through 2026-08-01 | Not banned. Reuse its publisher, renderer, attribution, and scoring contracts |
| recent clip runs | Contract reports `skipped`; older stderr shows Telegram DNS delivery failures | Diagnose scheduler/business gates separately from platform health |

### 1.1 Implementation progress

| Task | State | Receipt |
|---|---|---|
| R0 canonical convergence | Complete; historical disabled release was `615206fd98fb555b0aada794454dd63e1cc95260` | Canonical skill and installer pass twice at 3/3; archived verifier 10/10; commission regression 6/6; manifests cover ten legacy files plus one archived parser dependency; remote SHA, immutable release bytes, valid JSON receipt, `current` symlink, untouched legacy state, and zero launchd owners all pass |
| F0 current-Mac bootstrap | Runtime and browser capability GREEN; Keychain admission corrected; historical disabled release was `e3de264f4a9b1c5d34b49a913ff66ad6202dd318`; real provider admission remains open | CloakBrowser Chromium `145.0.7632.109` and pinned PBS CPython `3.14.7+20260814` are live-receipted. The original vault probe proved item existence only and incorrectly accepted an empty value. Admission now requires successful Keychain read plus non-empty bytes, without logging value, digest, or length. Provider refs are versioned in the program registry; Impact is `MISSING_OR_EMPTY`, so browser login remains disabled until official recovery and fresh-tab proof |
| P0/F1 legacy migration | Complete | Runtime commits `84cac1e7`, `3494f8ff`, `5b1927dc`; migration 8/8, legacy verification 10/10, commission regression 6/6; remote `feature/affiliate-agent-runtime` at `5b1927dc` |
| Legacy wrapper cutover | Blocked by design until Task 11 | F1 receipts `run.sh` and `affiliate-cli.sh` path/SHA-256/size while preserving their bytes; Task 11 must verify these receipts before scheduling the new orchestrator |
| Mac-local runtime | Release `8665a487567632710c30e3330aea39cbf32c6d78` is installed and four Affiliate-owned launchd jobs isolate the loop, ElevenLabs browser, X browser, and Impact browser | Process 1 left the existing X placement job at `EFFECT_STARTED`; process 2 ran the normal installed publisher, found the same public status before any click, retained the original run/job IDs, advanced attempt `1→2` with `resumed=true`, and set `VERIFIED`. A direct timeline readback found exactly one matching status URL. This proves process-boundary resume and X publish reconciliation without duplication. The newer `33b1756e25630e141952261658394344c770ba16` credential-recovery code is pushed but not yet installed/live-proven; provider-application reconciliation, attributable click, commission, and revenue remain open |
| ElevenLabs isolated auth | Dedicated Affiliate CDP `9324` is authenticated from the Git-external private SSOT | Gmail readback identified the account used by the real reset and new-login notices; the private Login field, Password/Keychain mirror, and mode `0600` were reconciled without committing values. The semantic CDP resume then rendered `SIGN_IN_REQUIRED → AUTHENTICATED` at `/app/home`, with one successful submit and a sanitized receipt. No commission is inferred from login |
| ElevenLabs PartnerStack metrics | The Agent created a separate PartnerStack credential through the private-Markdown-first Skill, created and email-verified the network account, created the `Anicca` business team, confirmed the existing Eleven Labs Inc. partnership, accepted the program terms, and reached the rendered overview, Commission Report, and Payouts surfaces | The current aggregate is one baseline click and zero signups/revenue/pending/paid. `revenue capture` live-read 23 commission fields and six payout fields. The current PartnerStack bundle, SHA-256 `be00e11924a35f20b84dee69ae741ae65204f07d3350a3266ad73501e96d867f`, proves the provider row keys use `reward_key`, `reward_status`, and explicit sub-ID/click/link fields even though the UI says Commission key. DOM absence was rejected as row evidence; installed release `329cbfc45` captured official JSON `row_count=0`, the empty Payouts surface, `NO_LIVE_ROWS`, and a mode-0600 artifact at SHA-256 `dce77f0083b0f92e29a67ccf99e417e11fe6307009bdfe98bf2d5fc77b39154d`. Approved/reversed remain unknown rather than zero |
| Cloud rollback | Complete | Staging runs rollback commit `bb31c68ada4e041ef1c0e745d7933a94f683a029`; the mistaken deployment is `REMOVED`; both `AFFILIATE_*` variables are absent; the former Affiliate route returns HTTP `404` |

### 1.2 Truth checkpoint: implemented versus still hypothetical

This table prevents tests, fixtures, screenshots, or plans from being reported as
live autonomous operation.

| Surface | Current truth | What is not yet proven |
|---|---|---|
| Runtime | Canonical local launchd browser and loop are installed; the first loop process exited `0` | A full research → publish → provider reconciliation wake has not completed; a process exit is not economic success |
| F1 migration | Implemented, reviewed, pushed, and re-run from final HEAD | It does not publish, browse, attribute, or earn |
| F2 Agent brain | Commit `d9ad4acd7cb0474cf1a825a94cfb49e7847da22e` is pushed; root replay on 2026-08-06 passed focused 16/16, Python 3.9 compile/shell syntax, and 30/30 related regressions | Full-suite collection is blocked by legacy `test_affiliate_verify.py` import-time `sys.exit()`; fresh review and live-provider execution remain open, so F2 stays open |
| Provider auth | ElevenLabs is `ACTIVE_LINK_VERIFIED + DEDICATED_LOGIN_VERIFIED`; HubSpot/Impact is `APPLICATION_PENDING + AUTH_RECOVERY_PROVIDER_DEFECT`; Kit is `APPLICATION_REJECTED`; Systeme.io is `EXTERNAL_CHALLENGE` at visible reCAPTCHA; Amazon JP is `AUTH_RECOVERY_OTP_REQUIRED`; Rakuten remains `AUTH_REQUIRED` | ElevenLabs credential recovery, dedicated fresh login through semantic CDP controls, active-account readback, owned default link, anonymous link traversal, and attribution-cookie creation are proven. No commission, approved transaction, reversal, or payout is claimed yet |
| Publication | The first English owned Affiliate article and matching disclosed `@selawmqt` X post each have action receipts plus public readback | Provider click readback and every Japanese placement remain unproven |
| Attribution | Local placement receipts and direct provider-link resolution are implemented | No public placement or provider-side click/commission receipt exists yet; local clicks and estimates never count as money |
| Revenue | No new Affiliate revenue receipt | Legacy watermark, fixtures, clicks, estimates, and creator screenshots do not count |
| Telegram | The shared Life Manager allowlist target delivered a real Affiliate milestone with provider `messageId=7639`; the older F1 path failed because it did not use this resolved target | Reuse the validated target contract and build the Affiliate durable outbox/dedupe layer; delivery identity is no longer unknown |
| Autonomous operation | launchd ownership and isolated browser are live; queue, publisher, reconciliation, recovery, and reports remain open | No-human-loop money behavior is not yet achieved |

### 1.2.1 Active execution contract: provider review is never passive wait

A pending provider review blocks only that provider's executable tracking link.
It does not block the Affiliate Agent project or the rest of the English funnel.
While HubSpot/Impact remains `APPLICATION_PENDING`, the Agent MUST continue all
independent work below:

1. poll the authenticated Impact page and authorized Gmail for a state change,
   preserving one deterministic transition ID and never resubmitting the same
   application;
2. discover every current English B2B SaaS and creator/productivity program,
   read its official terms, inspect official CLI/API and licensed OSS support,
   and create a current eligibility receipt;
3. apply immediately to every program that passes the eligibility gate; do not
   bulk-apply to programs whose audience, traffic minimum, region, channel,
   website-content, payout, or policy requirements are not yet satisfied;
4. make `aniccaai.com` an accessible, content-rich owned acquisition surface and
   publish useful non-affiliate English foundation content before links exist;
5. rebrand and verify `@selawmqt` as the English identity, add the required
   disclosure, and build relevant organic distribution without claiming results;
6. implement direct provider-link placement receipts, the append-only money
   ledger, policy gate, public readback, Telegram outbox, browser recovery, and
   launchd packaging on the operator's Mac;
7. prepare provider-specific placements as unpublished intents, then attach only
   an approved, owned, executable tracking link after an E-1 receipt exists.

The Agent MUST NOT report “waiting for approval” as the run result while any item
above is executable. A wait receipt is valid only for the provider-specific
application work item and MUST name the external reason, next poll time, durable
owner, and independent work selected for the same wake.

### 1.2.2 Current hard blockers, non-blockers, and honest struggles

| Condition | Class | Consequence and required action |
|---|---|---|
| HubSpot/Impact has not approved or rejected the application | External blocker for HubSpot link only | Continue polling with dedupe; execute the rest of the funnel and apply to other eligible programs |
| ElevenLabs has returned the first owned executable tracking link, but no disclosed public placement or provider transaction exists | Acquisition and revenue blocker, not authority blocker | Build the first useful disclosed owned placement, verify public readback and click attribution, then reconcile the first external transaction without counting clicks as money |
| Kit rejected the submitted application without naming one applicant-specific cause | Closed negative receipt | Do not reapply unchanged; first make audience fit, accessible content, and organic promotion evidence materially stronger |
| `@selawmqt` has zero followers and mixed historical language | Acquisition weakness, not implementation blocker | Rebrand future output to English, preserve history, publish useful material, and measure qualified reach honestly |
| The owned site does not yet present a deep affiliate-relevant English content body | Approval and conversion weakness | Publish evidence-led B2B SaaS/creator workflows and comparison foundations before another fit-sensitive application |
| `agent-browser 0.27.0` hung against the live multi-tab CloakBrowser | Tool-path failure, not browser incapability | Use the live-proven raw-CDP path now; retain the failure receipt and replace only when a candidate passes the same live postcondition |
| Provider signup/login/OTP/contract/application writes are not yet fully exposed by `affiliate provider` | Product implementation gap | Turn every successful operator action into an idempotent semantic playbook and CLI state |
| Provider reconciliation and Affiliate money ledger are incomplete | Revenue-truth implementation gap | The local placement receipt is exact-once, but no public readback or provider money receipt exists; no click or estimate may be reported as commission |
| No first-party CTR, conversion, approval, reversal, or payout cohort exists | Learning uncertainty | Do not fabricate best/base/worst revenue forecasts; collect the first live 30-day cohort |
| Scratch-Mac dependency installation is incomplete | Packaging gap, not current-Mac money blocker | Finish only after the current Mac closes a positive-unit-economics local slice |

The most difficult part is not text generation. It is obtaining lawful provider
authority, preserving identity across browser recovery, proving every external
side effect exactly once, and joining a real provider transaction back to the
exact public placement without inventing revenue. Those are the harness defects
the implementation must close.

### 1.2.3 Desktop continuity and durable ownership

During an active local Codex execution, the operator MUST NOT force-quit the
ChatGPT/Codex desktop application because active local tool execution is not
guaranteed to survive process termination. Closing or minimizing a window is
allowed. Git commits, pushed branches, this SSOT, and runtime receipts are the
durable recovery boundary; they preserve progress but do not guarantee that an
in-flight command continues.

The Affiliate browser and wake launchd owners are installed and live-proven.
Provider polling, research, publication recovery, reconciliation, and Telegram
reporting are not yet wired into that wake, so desktop independence is still a
product gate rather than a completed behavior. After wiring, the desktop becomes
an observation/steering surface rather than the process owner.

### 1.2.4 Credential-first provider preflight

Before opening any provider signup, the Agent MUST execute this order and
receipt status metadata only, never a secret value:

1. inventory the Git-external mode-0600
   `~/.config/anicca/affiliate-credentials.md` for an existing login,
   verification state, application state, and tracking link;
2. inspect authorized browser profiles for an already authenticated account and
   read back the provider identity;
3. when a local credential exists, attempt one isolated fresh login from the MD;
   Keychain is only an optional mirror and never the sole recovery source;
4. when the account exists but login fails, use official recovery and write the
   replacement to the private MD before reset submission;
5. create a new account only after credential inventory and provider account
   discovery both prove that no reusable account exists;
6. when an active affiliate account or executable link exists, reuse and verify
   it instead of submitting another application.

This preflight explains the current provider routing. Impact has an existing
application but broken recovery and an open provider ticket. Systeme.io has an
existing credential but a visible reCAPTCHA checkpoint. ElevenLabs had an
existing account and was the shortest unblocked route to the first executable
English offer. Its recovery closed E-1; it was not chosen because existing
credentials were ignored or because ElevenLabs is a mandatory final niche.

### 1.3 R0 legacy inventory

The legacy source is clean within its own `skills/affiliate` path and contains
ten tracked files totaling 40,572 bytes. Its two pure suites pass 16/16 and four
shell entrypoints pass syntax checks. It is a Japanese Instagram carousel →
Amazon-account-total workflow, not the planned English/X Affiliate Agent.

Literal copying cannot produce a working loop. The fixed-path Instagram poster,
slideshow composer, Amazon report reader, and affiliate ledger recorder are
absent or moved, while the source also hardcodes one macOS user, Homebrew paths,
port 9225, and a Japanese browser profile. These gaps are recorded as
`UNAVAILABLE`, never silently replaced or reported as parity.

At the R0 inventory checkpoint, no Affiliate launchd service, tmux session,
process, or open file was live, and two old launchd plists were disabled
artifacts. R0 therefore
preserves the ten files byte-for-byte under canonical `skills/affiliate/legacy`,
receipts the archived verifier parser separately in `DEPENDENCIES.sha256`, and
adds a relocatable but non-executing skill shell. The focused installer test
proves immutable install, idempotency, stale-symlink repair, valid JSON receipt,
launchd non-interference, and fail-closed detection of a modified release. That
historical disabled release was installed from pushed SHA
`615206fd98fb555b0aada794454dd63e1cc95260` under
`~/.local/share/life-manager/affiliate/releases/`; its private ownership receipt
is under `~/.local/state/life-manager/affiliate/`. The later local release and
launchd state are reported in section 1.1; publisher and money parity remain open.

### 1.4 No-dry-run equivalence rule

| Evidence | It may prove | It never proves |
|---|---|---|
| Unit/fixture test | Local contract behavior | Live login, publication, click, conversion, or revenue |
| CloakBrowser login page | Page reachability and observed auth state | Affiliate approval or account ownership |
| Fake browser/fixture response | Adapter parsing | A public X/article placement |
| Local placement/link check | Placement schema and provider-link resolution | Organic buyer intent or commission |
| Provider report fixture | Reconciliation arithmetic | External approved or paid commission |
| Legacy commission watermark | Historical unattributed aggregate | New Agent revenue or placement attribution |

Every report labels evidence as `TEST`, `LIVE_READBACK`, or
`EXTERNAL_MONEY_RECEIPT`. Only the final class closes a revenue gate. A task with
external completion criteria remains open after code completion until the named
external receipt exists.

### 1.5 Ideal autonomous flow

```mermaid
flowchart TD
  W[launchd wakes every 10 minutes] --> J{Unfinished durable job?}
  J -->|Yes| RS[Resume same run and job]
  J -->|No| AC[Account, login, profile, application Skill]
  AC --> OF[Approved offer and executable owned link]
  RS --> OF
  OF --> EV[CRWL, GitHub, X and product evidence]
  EV --> AS[Useful decision asset with disclosure]
  AS --> PB[Owned site and X publish]
  PB --> RD[Public readback and exact-once receipt]
  RD --> AU[Real audience discovers asset]
  AU --> PR[Provider records click, lead or sale]
  PR --> MR[Import hashed provider receipt]
  MR --> LD[Ledger: pending, approved, reversed, paid]
  LD --> TG[Telegram: action, money, blocker, next job]
  LD --> AL[Allocator: 80% proven winners, 20% canaries]
  AL --> W
  AC -->|Failure| FH[Classify and patch the harness]
  EV -->|Failure| FH
  PB -->|Ambiguous| FH
  MR -->|Auth or parser drift| FH
  FH --> CK[Minimal money, secret, duplicate-effect check]
  CK --> IN[Install release and resume same job]
  IN --> RS
```

Ten minutes is the default coordination wake. Provider polling, posting, and
research each retain their own policy/rate-limit cooldown, so a wake does not
imply an external action every ten minutes. Every job is durable; a crash resumes
the same job and ambiguous publication is read back before any retry. The model
plans and diagnoses, while deterministic code owns money states, permission,
idempotency, budgets, and evidence. This is the target, not a current revenue
claim.

The money boundary is `C → R`. An article, post, click, signup, dashboard
screenshot, or model estimate is never revenue. The ledger increases only when
the external provider exposes a non-test commission transaction. `pending`,
`approved`, `reversed`, and `paid` remain separate. The owner does not operate
the browser or choose the next task; Telegram is an observable control surface,
not a daily approval queue.

Every box above must be invokable through the versioned `skills/affiliate`
dispatcher. Browser signup, login, profile setup, application, publication,
public readback, dashboard observation, and recovery are Skill operations rather
than undocumented setup performed by Codex. The local launchd owner invokes the
same commands that a future clean-Mac installer and cloud scheduler invoke.

## 2. Evidence-backed constraints

1. Every affiliate surface carries a clear disclosure adjacent to the link or
   recommendation. Amazon requires a prominent associate statement: “As an Amazon
   Associate I earn from qualifying purchases.”
   Source: [Amazon Associates Operating Agreement](https://affiliate-program.amazon.com/help/operating/agreement), section 5.
2. A post must help a reader decide; scaled thin or copied pages are rejected.
   Google defines scaled content abuse as generating many pages primarily to
   manipulate rankings rather than help users.
   Source: [Google Search spam policies](https://developers.google.com/search/docs/essentials/spam-policies).
3. The relationship must be obvious without making the reader hunt for it.
   Source: [FTC Disclosures 101](https://www.ftc.gov/business-guidance/resources/disclosures-101-social-media-influencers).
4. Rakuten explicitly supports product/service introductions on SNS and blogs,
   and exposes high-rate products and link-level reports.
   Source: [Rakuten Affiliate](https://affiliate.rakuten.co.jp/).
5. High-value Japanese CPA supply cannot be reduced to Amazon/Rakuten. A8.net
   supports only its registered/approved media and explicitly excludes Twitter
   advertising; afb reports roughly 17,000 promotions across 18 categories and
   identifies medical beauty and related lead-gen offers as high-price/high-
   conversion areas. Supply never implies channel eligibility.
   Sources: [A8.net](https://www.a8.net/), [afb](https://www.afi-b.com/).
6. Postiz exposes scheduling, articles, a public API, CLI, and MCP. It is a
   publisher adapter, not the Agent's brain or ledger.
   Source: [Postiz documentation](https://docs.postiz.com/).
7. Amazon does not guarantee traffic or commission income and may suspend an
   account for contract breaches. Amazon inventory is therefore not a revenue
   forecast and cannot bypass the policy gate.
   Source: [Amazon Associates Operating Agreement](https://affiliate-program.amazon.com/help/operating/agreement).
8. FTC disclosure must be hard to miss, accompany the endorsement, and use the
   same language as the endorsement. Locale-specific accounts and disclosures
   are therefore a contract, not a branding preference.
   Source: [FTC Disclosures 101](https://www.ftc.gov/business-guidance/resources/disclosures-101-social-media-influencers).
9. NerdWallet's official 2025 filing describes revenue per action, click, lead,
   and funded loan, but also reports organic-search pressure and a customer that
   represented 26% of revenue. Deep partner events work; channel and partner
   concentration remain material risks.
   Source: [NerdWallet 2025 Form 10-K](https://www.sec.gov/Archives/edgar/data/1625278/000162527826000014/nrds-20251231.htm).
10. A first-person five-figure affiliate launch used an existing email audience,
    social and blog distribution, years of product use, a 40% commission, and a
    staged launch funnel. It is evidence for trust and distribution, not evidence
    that copying a prompt reproduces revenue.
    Source: [Smart Passive Income five-figure affiliate promotion](https://www.smartpassiveincome.com/blog/5-figure-jv-affiliate-promotion/).
11. Current English candidate economics include Kit's 50% first-year commission,
    HubSpot's 30% monthly recurring commission for up to one year, and Semrush's
    tiered sale/trial commissions. These are candidates only until our own
    application, ownership, terms, and executable link are read back.
    Sources: [Kit Affiliate Program](https://kit.com/affiliate),
    [Kit Affiliate Terms](https://kit.com/affiliate-tos),
    [HubSpot Affiliate Program](https://www.hubspot.com/partners/affiliates), and
    [Semrush Affiliate Program](https://www.semrush.com/lp/affiliate-program/en/).
12. A8 forbids affiliate ads on Twitter, unregistered LINE messages and other
    unregistered media, publication of program reward conditions, and
    indiscriminate bulk partnership applications. Its high-ticket offers cannot
    be sent through the article's proposed X → LINE funnel unless a separate
    provider-specific written permission supersedes the observed terms.
    Source: [A8.net prohibited matters](https://www.a8.net/compliance/prohibited-matter.php),
    “Twitterについても広告を掲載することは禁止しています。”
13. First-person experience cannot be generated when the operator has not used
    the product. Source: [FTC Disclosures 101](https://www.ftc.gov/business-guidance/resources/disclosures-101-social-media-influencers),
    “You can’t talk about your experience with a product you haven’t tried.”
14. X allows separate language-specific brand accounts and localized cross-posts,
    but prohibits bulk/duplicative content, aggressive automated engagement, and
    scripted website automation. Source: [X authenticity policy](https://help.x.com/en/rules-and-policies/platform-manipulation),
    “branded entities specific to unique locations or languages”; and
    [X automation rules](https://help.x.com/en/rules-and-policies/x-automation),
    “Use non-API-based forms of automation, such as scripting the X website” may
    result in permanent suspension.
15. Awin's Spanish publisher page describes the real money state transition:
    tracked sales first appear pending, the advertiser validates them, and only
    approved commissions become payable. It also states there is no global
    minimum follower count, while each advertiser controls admission.
    Source: [Awin España — Afiliados](https://www.awin.com/es/afiliados).
16. Hotmart exposes products by format, niche, language, and popularity and says
    affiliates are paid for attributed sales. This proves multi-language offer
    supply, not that a translated campaign will convert or be approved.
    Source: [Hotmart Affiliates](https://hotmart.com/en/affiliates), “Sign up.
    Pick a product. Start promoting.”
17. Kit's current official page states “50% commission for 12 months” and a
    further “10-20% recurring revenue beyond 12 months when you earn status.” It
    also says commissions are held for 31 days for refunds. The Agent models the
    hold and status tiers instead of treating a click or pending sale as cash.
    Source: [Kit Affiliate Program](https://kit.com/affiliate).

Creator revenue screenshots and claims found on X are market signals only. They
never enter earnings or train a prompt as a winner without a matching external
receipt from this Agent.

### 2.1 External playbook intake: ブッタ article

The [2026-08 article by `@buttanoteragoya`](https://x.com/i/article/2084059581924454404) is stored as
`SELF_REPORTED_UNVERIFIED`: the profile and article are real, but the claimed
monthly income, approval rates, conversion funnel, and one-month result have no
public provider or payout receipts. It changes the workflow, not the revenue
forecast.

| Decision | Adopted pattern |
|---|---|
| COPY | Four boundaries: authenticated offer discovery → evidence-led decision asset → distribution variants → actual-data learning |
| COPY | Pain, mechanism, workflow, fit/not-fit, limitations, and one CTA |
| COPY | Generate hook variants and choose tomorrow's one action plus one stop action from observed data |
| TWEAK | Rank only offers returned by authenticated ASP/API/browser receipts; unknown approval rate, payout, or channel remains `UNKNOWN` |
| TWEAK | First-person copy requires an `ExperienceClaimReceipt`; otherwise use official evidence, direct tests, and explicit limitations |
| TWEAK | X, LINE, email, and owned pages each require a fresh `ChannelEligibilityReceipt`; owned registered pages are the default |
| REJECT | Revenue promises, predicted impressions/CVR, hidden advertising, fabricated experience, article-volume quotas, automated engagement, and A8 X/LINE direct ads |

Every external playbook stores `source_url`, author, capture time, claim type,
evidence grade, checked provider terms, `COPY|TWEAK|REJECT`, and reason. A prompt
is never promoted merely because its author reports income.

### 2.2 Continuous best-practice intake

The Agent searches official program pages with CRWL, creator cases and platform
discussion through authenticated browser/X collectors, and GitHub through `gh`
plus raw files. A source becomes executable knowledge only after:

1. capture with URL, immutable content hash, author, language, and evidence grade;
2. exact claim extraction and provider-policy cross-check;
3. license classification as `COPY_CODE`, `COPY_PATTERN`, or `NO_REUSE`;
4. one causal hypothesis and one-variable canary in exactly one locale pod;
5. promotion only from this Agent's mature external click/commission receipts.

Popularity, stars, screenshots, author income claims, estimates, and prompt scores
are discovery signals. They never become revenue, conversion truth, or an
auto-promoted winner.

### 2.3 Aggressive but bounded revenue policy

“Aggressive” means faster evidence collection, more creative variation, quicker
offer replacement, and higher capacity only after positive net receipts. It does
not mean hidden advertising, fabricated experience, unauthorized channels,
engagement manipulation, challenge evasion, or risking the payout account. The
browser-only X lane is an explicit accepted enforcement risk, not a claim of X
approval. The Agent may test strong hooks, contrarian angles, profile-versus-owned-page
distribution, pricing frames, CTA placement, and content format one variable at
a time. Any tactic that requires deception or threatens account/payout survival
has negative expected value and is rejected by the deterministic gate.

## 3. Single recommended strategy

Start with one narrow English buyer problem on `@selawmqt`. Its X login is
provisioned; account presentation and browser publishing remain Agent work. The initial
candidate set is non-regulated B2B SaaS and
creator/productivity software because its official programs expose higher or
recurring payouts and the existing English publication lane reduces launch
friction. Exact market-size superiority is unproven and is not a premise.
Before its first Affiliate placement, change the current `sela` presentation to
an English Anicca identity with an adjacent profile disclosure; future content
is English-only. The 128 historical mixed-language posts remain historical data,
not a reason to delete or fabricate a clean track record.

Initial English capacity allocation:

- 70%: one authenticated high-value or recurring software portfolio with a
  genuine reader fit;
- 20%: owned comparison/how-to assets and their measured distribution;
- 10%: bounded exploration, including Amazon only when executable and useful.

Regulated financial products are excluded from the initial lane despite proven
affiliate economics. Japanese discovery may continue read-only, but Japanese
publication stays disabled until English E0; Japanese J1 is then earned by its
own account, offer, placement, click lineage, and commission receipt.

Do not start as a generic deal feed. Publish decision assets: comparisons,
cost calculators, migration guides, tested workflows, failure-mode guides, and
“who should not buy” sections. Each content unit maps one reader problem to one
primary offer and at most two honest alternatives.

### 3.1 Money model

The loop earns only when an external partner approves a downstream event:

`net commission = qualified visits × observed partner conversion × confirmed payout − reversals − content/compute cost − paid acquisition`

The learner therefore ranks signals in this order: paid/approved net commission,
approved sale or lead, qualified trial, provider-confirmed click, then engagement.
Posts, views, and prompt scores are diagnostic proxies, never money. Before 30
days of live cohorts, each conversion input and revenue forecast remains
`unknown`; best/base/worst cases are computed only from observed receipts.

## 4. Architecture

```mermaid
flowchart TB
  BP[CRWL + X/TikTok + GitHub evidence scout] --> SR[Provenance and license registry]
  SR --> PC[Playbook compiler]
  PC --> K[Shared deterministic kernel]

  subgraph KERNEL[Shared truth and recovery]
    K --> Q[Durable queue and state machine]
    Q --> B[Browser authority and action receipts]
    B --> L[Attribution and commission ledger]
    L --> H[Self-healer and experiment learner]
    H --> TG[Owner-language Telegram events]
  end

  K --> EN[English pod]
  K --> JA[Japanese pod]
  K -. Locale Admission Gate .-> ES[Spanish pod]
  K -. later .-> NX[Next locale pod]

  EN --> F[Offer → evidence → decision asset → distribution]
  JA --> F
  ES --> F
  NX --> F
  F --> RD[Direct provider link + local receipt]
  RD --> L
```

This is one durable Agent with specialized workers, not independent agents with
separate truth. PostgreSQL/SQLite state and append-only receipts are canonical;
prompts and browser sessions are replaceable executors.

The kernel is shared code, not shared market state. Each locale pod owns its
identity, browser storage, provider membership, executable links, disclosures,
evidence pack, experiments, ledger partition, and budget. A useful English asset
may seed a hypothesis for Japanese or Spanish, but the destination pod must
re-research native intent, terms, claims, alternatives, and wording before a
canary. Translation alone can never authorize publication.

### 4.1 Components

| Component | Contract |
|---|---|
| Provider adapters | English B2B/creator programs first; Amazon, Rakuten, A8, afb, and later networks normalize offers, terms, commission events, and account health only after authenticated readback |
| Offer verifier | Re-reads landing page, price, availability, geo, payout, prohibited claims, allowed channels, disclosure, and expiry before publication |
| Portfolio allocator | Selects by expected **net** value: qualified intent × observed conversion × confirmed payout − refunds − content/compute cost − compliance risk |
| Evidence pack | Stores official facts, direct product evidence, alternatives, audience pain, counterclaims, and freshness TTL |
| Content studio | Produces an English article, X thread/post, X Article, carousel, slideshow, or video; the later Japanese pod uses independent evidence, identity, and localization rather than mixed-language reuse |
| Policy gate | Fail-closed for missing disclosure, unverified claims, prohibited categories, self-dealing, stale price, broken link, or unregistered surface |
| Browser publisher | Observe semantically, execute one typed action, then require before/after URL and observation hashes, expected identity, external object URL/ID when visible, screenshot hash, and fresh public readback. Before retrying an ambiguous publish, search the ledger and live account for the content fingerprint |
| Attribution | Agent records content, placement, offer, language, and experiment locally, publishes the provider tracking link directly, and reconciles only provider-side click/commission receipts |
| Receipt reconciler | Navigates provider dashboards and downloaded reports through the browser, hashes the source artifact, and joins transaction/sub-ID rows to clicks. Unknown is never zero; pending, approved, reversed, and paid remain distinct |
| Learner | Promotes a tactic only from mature cohorts and deepest common signal: net commission → approved orders → qualified leads → clicks → engagement |
| Recovery controller | Same `run_id`, artifact hash, placement, and publication intent resume after failure; exponential retry obeys provider `Retry-After` |
| Best-practice scout | Captures official terms, first-person cases, platform signals, and OSS code with provenance, license, evidence grade, TTL, and `COPY_CODE|COPY_PATTERN|NO_REUSE` disposition |
| Locale pod controller | Creates or resumes one isolated identity/provider/content/ledger slice only after the Locale Admission Gate; prevents cross-locale cookies, links, claims, and learning leakage |

### 4.2 Canonical records

`source_capture`, `crawler_adapter_receipt`, `provider_account`, `offer`,
`offer_snapshot`, `external_playbook_intake`,
`channel_eligibility_receipt`, `experience_claim_receipt`, `evidence_claim`, `content_unit`,
`placement`, `publish_intent`, `public_readback`, `click`, `conversion`,
`commission_receipt`, `experiment`, `policy_decision`, `wait_state`, and
`recovery_attempt` are the minimum entities.

Every commission receipt stores provider transaction ID, click/sub-ID when
available, currency, gross commission, reversal/refund, fees, net amount,
status, observed time, and immutable source hash. Canonical states are
`pending`, `approved`, `reversed`, and `paid`; UI may say “approved, not paid”
but that phrase is not a fifth storage state. Approved and paid are never combined.

## 5. Loop and state machine

```mermaid
stateDiagram-v2
  [*] --> Bootstrap
  Bootstrap --> AuthorityInventory
  AuthorityInventory --> BrowserProvision
  BrowserProvision --> AccountReady
  AccountReady --> ProfileReady
  ProfileReady --> ProgramDiscovery
  ProgramDiscovery --> ApplyOrLogin
  ApplyOrLogin --> ApprovalPolling
  ApprovalPolling --> OfferReady
  OfferReady --> Evidence
  Evidence --> Produce
  Produce --> BrowserPublish
  BrowserPublish --> PublicReadback
  PublicReadback --> Acquire
  Acquire --> Reconcile
  Reconcile --> Learn
  Learn --> ProgramDiscovery
  ApplyOrLogin --> ExternalChallenge: OTP, CAPTCHA, KYC, contract
  ExternalChallenge --> ApplyOrLogin: authorized evidence becomes available
  BrowserPublish --> Recover: ambiguous or changed UI
  Recover --> BrowserPublish: no duplicate found
```

The deterministic kernel owns transitions, leases, budgets, idempotency, money,
and receipts. One semantic browser planner handles unfamiliar pages. After a
successful path, the Agent stores a versioned playbook; later runs replay it and
invoke semantic recovery only when observation or postcondition hashes diverge.
This is one durable Agent with role prompts, not a swarm of independent ledgers.

Minimum receipt chain:

`BootstrapReceipt → AuthorityReceipt → AuthReceipt → ProfileReceipt → ProgramApplicationReceipt → OfferApprovalReceipt → EvidenceReceipt → PublishIntent → BrowserActionReceipt → PublicReadbackReceipt → ClickReceipt → CommissionReceipt → PayoutReceipt → LearningReceipt`.

Screenshots prove rendered state, not money. Only hashed provider dashboard/report
readback can create `pending`, `approved`, `reversed`, or `paid` commission rows.

```mermaid
stateDiagram-v2
  [*] --> Discover
  Discover --> Verify
  Verify --> Reject: stale, forbidden, or no fit
  Verify --> Produce: executable offer
  Produce --> PolicyGate
  PolicyGate --> Repair: failed claim or disclosure
  Repair --> PolicyGate
  PolicyGate --> Publish: pass
  Publish --> Readback
  Readback --> Recover: missing or mismatched
  Recover --> Publish
  Readback --> Measure: verified live
  Measure --> Reconcile
  Reconcile --> Learn
  Learn --> Discover
```

Cadence:

- every 5 minutes: reconcile leases and ambiguous side effects, resume failed
  intents, ingest receipts, and flush the Telegram outbox; it does not create a
  new article every five minutes;
- hourly: offer/price/link/account health and provider/application polling;
- daily during launch: measure prior English cohorts, verify terms, choose one
  reader problem, produce at most one English primary decision asset, derive
  compliant distribution, perform public readback, and reconcile reports;
- 24/72 hours and 7/30 days: cohort measurement and learning;
- weekly: provider mix, reversals, net margin, concentration, and policy audit;
- monthly: close currency/reversal/payout truth and decide whether a locale or
  provider has earned more budget.

Platform publication windows block only that placement. Every wait has a retry
time and durable owner; “wait for next schedule” is invalid.

## 6. Self-improvement without self-corruption

- Preserve at least 20% exploration and require at least ten mature comparable
  placements before winner/loser mutation, matching the existing Marketing
  Engine scoring contract.
- Change one causal variable per experiment: offer, hook, proof shape, CTA,
  format, channel, or publish time.
- Optimize net approved commission per 1,000 qualified impressions and net
  commission per content dollar. Never optimize raw post volume.
- A provider, offer, prompt, or account is quarantined after repeated policy,
  reversal, link-health, or reach failures; the Agent shifts to an independent
  provider/channel while diagnosing it.
- Prompt mutations are versioned and reversible. A winning claim cannot be
  invented by the learner; factual claims always come from a fresh evidence pack.

## 7. Reuse and OSS decision

Reuse from the existing system:

- Writer Agent: research acquisition, JA/EN localization, X/article publisher
  adapters, public readback, same-run resume, claim registry;
- Marketing Engine: generic publication receipts, account-isolation patterns,
  slideshow/video/carousel renderers, mature-cohort scoring, and Telegram
  reporting; its Postiz publisher is explicitly not reused;
- Life Manager financial ledgers: verified money semantics and reporting.

Repository audit result: no inspected repository proves an autonomous affiliate
loop from account/application through an externally approved commission. We do
not fork a repository and call it the product. We copy only the following proven,
licensed parts into the existing local runtime:

| Repository | Measured truth | Decision |
|---|---|---|
| [BlockRunAI/Franklin](https://github.com/BlockRunAI/Franklin) | Apache-2.0 source; durable goals/scheduler, wallet budget, resumable sessions, task event logs, lost-task detection, and Telegram control. Its README says it **spends** money toward work; it does not reconcile affiliate income | `COPY_PATTERN`: bounded goals, cost caps, durable task lifecycle, evidence challenge. Do not import its wallet/trading subsystem or treat spend as earnings |
| [paraggit/affiliate-automation](https://github.com/paraggit/affiliate-automation) | MIT file; provider abstraction, retry/backoff, persistence, tests, content and Twitter scheduling. Runtime still asks `Start scheduler?`; no commission or payout ingest exists | `COPY_CODE` selectively: provider protocol, retry, and tests. Replace interactive scheduler and API publisher with our queue/browser/receipt kernel |
| [stay4ever role agents](https://github.com/stay4ever) | MIT files and small tested scout/content/analyst packages. Niche scores and performance examples use estimates or caller-supplied data | `COPY_CODE` selectively: role/tool schemas and disclosure template. Never import estimated traffic, CVR, or benchmark revenue as truth |
| [anacgr05/affiliate-agents](https://github.com/anacgr05/affiliate-agents) | Role graph, PostgreSQL/Redis/Celery/SSE and explicit human approval; no license file and no external commission reconciler | `COPY_PATTERN` only: critic/feedback state boundaries; do not copy code or human gate |
| [ricky-affiliate-agent](https://github.com/sujalmanpara/ricky-affiliate-agent) | Amazon → 15 images → Postiz. No license file despite README saying MIT; code warns “Commissions won't be tracked to your account” when the tag is absent | `NO_REUSE` as a base; Postiz and untracked output violate the product/revenue contract |
| [amazon-affiliate-automation-pipeline](https://github.com/haramhussain110/amazon-affiliate-automation-pipeline) | Five-file, unlicensed content pipeline; README says videos are “ready to check and post manually” and “I'm not auto-posting anything” | `NO_REUSE` as a base; at most reimplement the ASIN→video idea after provider-policy verification |
| [autonomous-marketing-agent](https://github.com/abandini/autonomous-marketing-agent) | No license file; scheduler/recovery shapes coexist with mock approvals and hard-coded revenue/conversion payloads | `NO_REUSE` code; retain only the abstract recovery vocabulary |
| [awesome-OpenClaw-Money-Maker](https://github.com/BlockRunAI/awesome-OpenClaw-Money-Maker) | A catalog, not an executable system; README says “These are potential earnings, not guarantees” | Discovery index only; every linked project receives its own code/license/money audit |

Local Writer/Gig loops are more valuable than any inspected affiliate repository
for production behavior: they already supply launchd ownership, same-run
reconciliation, public readback, durable receipts, and Telegram delivery patterns.
Their interfaces are reused while their ledgers remain isolated.

### 7.0.1 File-level reuse map

The audit reads implementation files, not only READMEs. `COPY_CODE` still means a
small compatible slice with license attribution; it never means importing a whole
runtime. The current disk floor is 10 GiB free. Below that floor the Agent stops
new clones, media generation, and browser downloads while continuing ledger and
health reporting. GitHub tree/raw access replaces a clone when it proves the same
code boundary.

| Source file | Proven mechanism | Exact use in Affiliate Agent | Explicitly excluded |
|---|---|---|---|
| [Franklin `src/tasks/store.ts`](https://github.com/BlockRunAI/Franklin/blob/main/src/tasks/store.ts) | Atomic temp-file rename plus append-only `events.jsonl`; one writer per task | Keep the existing `job_journal.py` contract: immutable `run_id`/`job_id`, append-before-effect, tolerant replay, same-job resume | Franklin wallet, trading, generic command runner, and any revenue inference |
| [Franklin `src/tasks/lost-detection.ts`](https://github.com/BlockRunAI/Franklin/blob/main/src/tasks/lost-detection.ts) and [`src/scheduler/store.ts`](https://github.com/BlockRunAI/Franklin/blob/main/src/scheduler/store.ts) | Reconcile a dead owner as `lost`; after sleep fire one current slot rather than replaying every missed interval | A14.7 watchdog, stale-owner detection, and one bounded catch-up wake | Copying its process model or creating a second scheduler beside launchd |
| [Forage `forage/agent/core.py`](https://github.com/Nerfed-Lab/forage/blob/main/forage/agent/core.py) | Repeating check-vitals → decide → act → reflect → persist cycle | Copy only the cycle boundary and cost-aware action selection into the existing local loop | Its capability-returned `revenue` value; Affiliate money must come from a hashed provider transaction |
| [Forage `forage/economy/ledger.py`](https://github.com/Nerfed-Lab/forage/blob/main/forage/economy/ledger.py) | Append-oriented income/expense queries and profitability windows | Reuse the profitability/window vocabulary; preserve Affiliate's richer pending/approved/reversed/paid lineage | Treating a local action result or wallet balance as commission |
| [paraggit `src/core/base_affiliate.py`](https://github.com/paraggit/affiliate-automation/blob/main/src/core/base_affiliate.py) | Small provider protocol and normalized product record | Reimplement the protocol shape as provider playbooks with authenticated ownership, terms, allowed-channel, link and report states | Its Amazon/Flipkart assumptions and price/deal ranking as the primary strategy |
| [paraggit `src/utils/retry.py`](https://github.com/paraggit/affiliate-automation/blob/main/src/utils/retry.py) | Bounded typed retry with exponential delay | Reference for read-only transient retries only; writes remain journaled and reconcile-before-retry | Its interactive scheduler, generic content prompt, Tweepy publisher, and unverified success booleans |
| [Crawlee `recoverable_state.py`](https://github.com/apify/crawlee-python/blob/master/src/crawlee/_utils/recoverable_state.py) and [`RequestQueue` example](https://github.com/apify/crawlee-python/blob/master/docs/introduction/code_examples/02_request_queue.py) | Persisted crawler state and durable request queue across restart | Admit only when CRWL cannot cover a real multi-page/JS research job; emit normalized `SourceCapture` receipts | Making Crawlee the Agent brain or adding it for single-page fetches |

The first implementation choice is therefore local reuse, then the smallest
licensed external mechanism. There is no dependency addition for a mechanism
already implemented by `job_journal.py`, launchd, CRWL, CloakBrowser, or the
Writer/Gig publication and receipt contracts.

### 7.1 Closest end-to-end OSS and public-claim gate

No inspected OSS project closes the whole chain from lawful account authority to
an externally approved recurring income receipt. The nearest reusable systems
are complementary, not substitutes for the Affiliate Agent:

| Project | Closest proven boundary | Missing money boundary | Decision |
|---|---|---|---|
| [Nerfed-Lab/forage](https://github.com/Nerfed-Lab/forage) | MIT autonomous cycle, budgets, ledger, evolution, and Gumroad listing; cloned suite passed 39 tests | Its measured revenue remains `0.0`; Stripe/crypto payout and external receipt ingest remain TODO | Copy the economic-agent cycle and budget/ledger tests, not an earnings claim |
| [diptobiswas/agentwork](https://github.com/diptobiswas/agentwork) | Closest marketplace shape: agent profiles, gigs, escrow contract, and on-chain settlement vocabulary | Observed public market had one active agent, zero gigs, and `$0` earned; production recipient lookup remains TODO; no root license | Pattern only; do not copy unlicensed code or call escrow capability revenue |
| [coinbase/x402-paid-api-starter](https://github.com/coinbase/x402) | Closest real settlement substrate: idempotent transaction/settlement receipts; relevant cloned slice passed 13 tests | It does not acquire customers, publish, or choose profitable work | Reuse receipt/settlement patterns for an x402 loop, not as Affiliate Agent |
| [paraggit/affiliate-automation](https://github.com/paraggit/affiliate-automation) | Closest licensed affiliate code: MIT provider abstraction, persistence, retry, content, scheduling; audited suite passed 41 tests | Interactive confirmation; no program application, commission reconciliation, payout, or public ledger | Selective code reuse behind our deterministic queue/browser/receipt contracts |
| [No Human in the Loop](https://nohumanintheloop.com/) | Self-reported real-world precedent: zero approvals and `$2,152` from 74 Gumroad copies | Public GitHub is a static two-file site, not a reproducible harness/ledger, and has no reusable license | Evidence that generic “world's first money loop” is unsafe |

Until a public proof gate closes, README language is only: “We are building an
open-source, receipt-verified affiliate earning loop.” The qualified claim “To
our knowledge, Life Manager is the first open-source, receipt-verified agent loop
that autonomously operates affiliate marketing from authorized account bootstrap
through settled commission” becomes eligible only when all of these exist:

1. canonical public Life Manager source and reproducible macOS installation;
2. a live E1 commission and later payout receipt, redacted and content-addressed;
3. a privacy-safe append-only ledger separating gross, net, pending, approved,
   reversed, paid, currency, cost, and payout;
4. an independent verifier that replays receipt hashes and ledger invariants;
5. a public prior-art registry with search date, routes, repositories, licenses,
   code/tests inspected, and explicit uncertainty;
6. no secret, tax, bank, customer, session, or provider-internal identifier in
   the public projection.

This gate permits a qualified prior-art statement, never a guaranteed-income or
generic “world's first money-printing loop” claim.

### 7.2 Crawling and scraping substrate

“Every platform” is implemented as one typed `CrawlerAdapter` registry, not one
fragile scraper pretending every site has the same access model. Every adapter
returns normalized `SourceCapture` records with URL/object ID, platform, locale,
author, captured time, raw artifact hash, parser version, access route, and
readback class. Empty results are distinguishable from auth, rate-limit, parser,
policy, and upstream failures.

| Surface | Primary route | Clone/code evidence | Runtime decision |
|---|---|---|---|
| Public web and linked articles | Existing `crwl crawl`; Scrapy only for parser/HTML fallback | [Scrapy](https://github.com/scrapy/scrapy) is BSD-licensed; cloned retry, robots, and throttle suites passed 90 tests with 14 environment skips | Reuse the installed CLI first. Do not add a framework for a one-page fetch |
| Durable multi-page/JS crawl | Crawlee Python `HttpCrawler`/`PlaywrightCrawler` with persistent `RequestQueue`, session pool, robots delay, `Retry-After`, and backoff | [Crawlee Python](https://github.com/apify/crawlee-python) is Apache-2.0; cloned queue/session/throttle suites passed 338 tests with 2 memory-storage skips, and its official `HttpCrawler` example fetched `crawlee.dev` with 1 finished/0 failed | `COPY_CODE`/dependency only when a durable crawl is actually required; this is the shared substrate, not the Agent brain |
| X search and logged-in pages | Existing `x-search-cdp` on the exact daily-driver tab; CloakBrowser semantic read for authenticated articles | Local code drives the rendered tweet DOM. Current probe returned `no logged-in x.com tab`, so this route is not presently healthy | Repair/re-provision the authorized tab inside the Agent; never launch a duplicate browser silently |
| Public X tweet/profile fallback | `x-tweet-fetcher`: FxTwitter → Nitter → browser fallback, normalized schema and SQLite dedupe | [x-tweet-fetcher](https://github.com/ythx-101/x-tweet-fetcher) is MIT; 97 tests passed and live `@selawmqt` profile readback matched 128 posts, 0 followers, 27 following | Adopt for read-only public objects. X Articles still require a browser; no posting capability |
| X private-API fallback | None in production | [Twscrape](https://github.com/vladkens/twscrape) is MIT and 192 cloned tests passed, but it rotates accounts and consumes X internal GraphQL operations; fixture success does not prove live account safety | `NO_REUSE` initially. It may enter an isolated research canary only after a live/policy/account-risk review |
| TikTok | `clockworks/tiktok-scraper` and task-specific Apify Actors via their fetched input schemas | Existing code calls the Actor and normalizes videos/slideshows, but its current combined test file cannot collect because it still imports deleted `rss_parser`; old `drawrowfly/tiktok-scraper` is unlicensed and stale | Managed Actor adapter remains the candidate, but production admission requires a fresh one-item live dataset receipt and a repaired focused contract test |
| Instagram, Facebook, YouTube, Google Search/Trends/Maps | Task-specific Apify Actor selected by the local `apify-ultimate-scraper` registry | Actor IDs and input discovery exist locally; Actor implementation code is not assumed open source | Fetch actor schema, run a bounded live canary, hash dataset/schema, then admit. Never claim code reuse when only a hosted Actor is used |
| Reddit | PRAW with authorized read-only OAuth; public HTML through CRWL only as fallback | [PRAW](https://github.com/praw-dev/praw) is BSD-licensed; cloned auth/read-only/rate-limit unit slice passed 34 tests | Adopt official client semantics; do not use unauthenticated bulk-scraper repos as the primary route |
| GitHub | `gh` API/search plus raw files, then clone candidate repositories | GitHub CLI returned repositories and full clones supplied the code/license/test evidence in this audit | Already canonical; README alone never closes an audit |
| Amazon, Rakuten, A8, afb, PartnerStack and ASP dashboards | Official product/program API when explicitly allowed; otherwise isolated CloakBrowser rendered pages and report downloads | Affiliate-specific public scrapers either lack licenses, omit posting/revenue, or bypass the authenticated ownership state required by the ledger | Never substitute product scraping for provider approval, tracking-link ownership, or commission reconciliation |

Adapter selection follows a fixed ladder: official/authenticated interface →
installed CRWL → licensed public-object adapter → Crawlee/Scrapy → rendered
CloakBrowser. A failed route emits evidence and advances only to an allowed
fallback. It never rotates stolen accounts, bypasses challenges, or turns a parser
failure into an empty market signal.

No external prompt or source is copied unless its license permits reuse. Public
workflow ideas are reimplemented against our own contracts and evidence.

## 8. Revenue gates

| Gate | Verifiable completion |
|---|---|
| E-1 | English provider auth and ownership readback for one executable offer on the dedicated English identity |
| E0 | One English placement has public readback, an executable direct provider/custom link, and a provider click receipt; this unlocks a separate Japanese canary |
| E1 | First non-test English approved commission joined end-to-end |
| J-1 | After E0, Japanese provider/account ownership and one executable offer are independently read back |
| J0/J1 | Japanese public placement/click lineage, then approved commission, each closed independently of English |
| L0 | Any later locale has a separate identity/browser/provider/link/disclosure, at least one executable offer, native evidence review, and a receipted canary; Spanish is the first expansion candidate |
| A2 | Four revenue-positive weeks, positive net margin, zero manual execution |
| A3 | Three consecutive months at $10,000 gross affiliate commission with net, reversals, and attribution reported separately |
| A4 | Diversified scale: no provider, offer, or channel exceeds 40% of net commission |
| A5 | $10,000,000 cumulative or monthly target is defined explicitly and then met only by external receipts; never inferred from traffic |
| A6 | $100,000,000 monthly net remains `HORIZON_OPEN` until one externally settled month passes FX, reversal, cost, concentration, policy, partner-capacity, and tenant-isolation audits; GMV and forecasts do not count |
| OSS1 | After E1, one clean macOS user installs the public repository with one command and reaches the same pre-publication state without copying credentials, sessions, or mutable receipts |
| C1 | After A2 and OSS1, one isolated cloud tenant reproduces the same state machine, browser action receipts, money ledger, recovery, and report without weakening policy or tenant isolation |

Best/base/worst planning is computed only after 30 days of real funnel data.
Before that, revenue is `unknown`, not a fabricated conversion forecast.

## 9. Ordered implementation backlog

### 9.0 One-line route to USD 10,000/month

```mermaid
flowchart LR
  E0[E0: attributable click] --> E1[E1: first approved commission]
  E1 --> P10[10 comparable placements]
  P10 --> A2[A2: 4 profitable unattended weeks]
  A2 --> D[3+ providers and no concentration above 40%]
  D --> A3[A3: 3 receipted months at USD 10k gross]
```

There is no honest fixed promise that a known number of posts produces USD
10,000. After 30 days, the Agent computes the required portfolio from observed
provider receipts. For example, USD 10,000 can equal 100 approved commissions at
USD 100 net, 20 at USD 500 net, or a mixture. Those are arithmetic decompositions,
not forecasts. The allocator increases only cohorts with positive approved net
commission after reversals and cost, preserves 20% exploration, and limits any
one provider, offer, or channel to 40% of net commission. A3 closes only after
three external monthly receipts each reach USD 10,000 gross and the corresponding
net, cost, reversal, and concentration views reconcile.

The Agent does not scale by increasing post count blindly. It closes the measured
ladder in order: executable offer → attributable post-baseline click → approved
commission → ten comparable placements → four profitable unattended weeks →
three diversified providers → an observed portfolio equation that sums to USD
10,000. If observed net commission per approved conversion is `N`, required
monthly approved conversions are `ceil(10000 / N)`; required qualified visits are
computed only from the cohort's observed conversion rate. Before those receipts,
the inputs remain `unknown`.

### 9.0.1 Remaining atomic execution queue

This is the exact execution order from the current live state. Each production
step ends with a versioned Skill command, durable receipt, installed-release
replay, SSOT update, commit, and push. A check is minimal: one normal path plus
only money corruption, secret leak, duplicate external effect, or data-loss
regressions relevant to that step.

#### A. Close revenue truth for the live ElevenLabs placement

- [x] **A12.1** Preserve the first PartnerStack overview as an immutable baseline;
  later observations store deltas without overwriting its timestamp or values.
- [x] **A12.2** Make `affiliate revenue observe` replay-safe and prove two live
  observations return the provider browser to ElevenLabs home.
- [x] **A12.3** Inspect the rendered PartnerStack Commissions and Reports surfaces;
  record which transaction ID, click/sub-ID, currency, status, and dates actually
  exist, leaving absent fields `null`.
- [x] **A12.4** Add one transaction-report capture command that stores the raw
  download or rendered artifact hash outside Git.
- [ ] **A12.5** Normalize real rows into `pending|approved|reversed|paid` without
  treating overview totals or unknown values as transactions. The bundle-backed
  normalizer is implemented for `pending|hold|approved|scheduled|declined|paid`,
  preserves raw provider status, excludes customer PII, and currently reports
  `NO_LIVE_ROWS`; this item closes only after a real non-empty row is normalized.
- [x] **A12.6** Make repeated imports idempotent by provider transaction ID plus
  source hash; a status change appends a transition rather than rewriting history.
- [ ] **A12.7** Join a provider row to placement/click/sub-ID when supported; store
  an explicit unmatched receipt when the provider exposes no join key. The
  resolver now indexes only `LIVE` owned publications and matches sub-ID/shared-ID
  or tracking-link fingerprints without storing the raw link; `UNMATCHED` and
  `AMBIGUOUS` fail closed. This closes only after a live non-empty row proves the
  join or the unmatched path.
- [x] **A12.8** Mark the existing one-click total `BASELINE_ONLY`; only a post-
  baseline increase can qualify for E0 and it still does not qualify as money.
- [x] **A12.9** Wire the revenue observer and report importer into the 10-minute
  loop under provider cooldown and exact-once job ownership.

#### B. Make the owner experience observable on Telegram

- [x] **A13.1** Define one owner-readable event containing what happened, public
  URL, provider/program, money state, gross/net/cost, recovery, and next job.
- [x] **A13.2** Add an append-only outbox before network send so a crash cannot lose
  a milestone.
- [x] **A13.3** Send through the existing Life Manager Telegram transport and save
  provider `messageId`; never create a second Telegram runtime.
- [x] **A13.4** Deduplicate by stable event UUID and retry a failed send without
  duplicating the underlying publication or money transition.
- [ ] **A13.5** Prove real messages for `PLACEMENT_LIVE`, `CLICK_DELTA`,
  `COMMISSION_PENDING`, `COMMISSION_APPROVED`, `SELF_HEALED`, and `BLOCKED`.

`SELF_HEALED` is live-proven with Telegram `messageId=20298`; `BLOCKED` is
live-proven with `messageId=20305`. The other four event classes remain bound to
their real external states.

Installed proof: immutable release `e4176c8a83832d10c880b379b3d99c3294b241ec`
created one real `REVENUE_RECONCILED` outbox row before sending, stored Telegram
`messageId=20279`, and exited `0`. A second real launchd kickstart produced
`NO_PENDING`, kept the sent ledger at one row, and exited `0`. The remaining
A13.5 event types wait for their real external states; no synthetic click or
commission message counts.

#### C. Make the loop repair itself instead of requiring Codex

- [x] **A14.1** Persist `run_id`, `job_id`, state, attempt, action fingerprint,
  cooldown, and last verified external object before every external mutation.
- [x] **A14.2** Resume the same unfinished job after process crash or Mac restart.
- [ ] **A14.3** For ambiguous publish/application outcomes, search public/provider
  state first and reconcile the existing effect before any retry.
- [ ] **A14.4** Detect expired login, invoke the credential/recovery Skill, verify a
  fresh authenticated page, then resume the original job.
- [ ] **A14.5** Detect selector drift from semantic expected-state failure, capture
  sanitized evidence, let the fixing agent patch the smallest adapter/playbook,
  run its minimal regression, install the new release, and resume the same job.
- [ ] **A14.6** Quarantine only the failing provider/channel after repeated auth,
  policy, reach, or reversal failures; healthy work continues.
- [ ] **A14.7** Add watchdog, retry/backoff, action caps, daily cost cap, disk-space
  floor, browser-owner health, and stale-lock recovery.
- [ ] **A14.8** Induce one isolated recoverable failure and prove the live loop
  reports, repairs, resumes, and completes without owner action.

A14.1 implementation basis and checkpoint:

- [Temporal Workflow Execution](https://docs.temporal.io/workflow-execution): a
  workflow is identified by Workflow ID and Run ID; persisted state and event
  history let execution recover and resume from its latest state.
- [AWS Builders' Library — Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/):
  AWS prefers a unique caller-provided request identifier and retains the
  original request parameters so retries preserve intent.
- [AWS Step Functions redrive（日本語）](https://docs.aws.amazon.com/ja_jp/step-functions/latest/dg/redrive-executions.html):
  redrive keeps the same execution identity/input, preserves successful steps,
  and resumes from the failed step.
- The canonical Skill now copy+tweaks the Writer publication guard into one
  secret-refusing `job_journal.py`. Provider login submit, X profile save, X post
  publish, owned Git push, and Telegram send write all seven required fields
  before mutation and set `VERIFIED` only after real readback. A focused check
  proves the unresolved-effect gate and append-only transition history. Installed
  release `cab6a976d706684a755654378ae294487cf0a35d` then wrapped a real Telegram
  mutation, stored provider `messageId=20293`, retained all seven fields, and
  transitioned `EFFECT_STARTED → VERIFIED`. Replay returned `NO_PENDING` while
  both sent and job-event counts stayed unchanged; A14.1 is DONE.

A14.2 proof: the common journal and all five live adapters
now reconcile exactly one unresolved `kind + target` only after a fresh semantic
readback. The recovered transition retains the original `run_id` and `job_id`,
increments `attempt`, sets `resumed=true`, and appends rather than overwrites its
history. Installed process 1 left the existing `elevenlabs-en-1` X job unresolved;
installed process 2 recovered the same job through the real public timeline and
returned its original status URL. A second read-only timeline pass found exactly
one matching URL, so no duplicate publish occurred; A14.2 is DONE. A14.3 remains
open for application-side ambiguity even though X publication is now proven.

Impact recovery incident: the prior Skill example incorrectly named protected
CDP `9223` as HubSpot/Impact. Live inspection proved that port is controlled by
another earning loop, so Affiliate stopped using it; no application, publication,
or payment mutation occurred. The canonical release now provisions isolated
`impact-en:9327` under `ai.anicca.affiliate-impact-browser`. Only that owner may
perform future Impact recovery and application readback.

A14.4 current evidence: dedicated `impact-en:9327` redirected the application
home request to `login.user`, proving auth expiry. Gmail contains only ticket
`868262` acknowledgement, not a human support reply. The latest official reset
email has one exact reset anchor, and the isolated browser reached the genuine
`app.impact.com/password/change.ihtml` form with exactly two password fields and
one submit control. The versioned `provider reset-password` command now requires
that exact state, reads only the pre-saved mode-0600 MD credential, journals the
mutation, and requires redirect readback. A14.4 stays open until reset, fresh
login, and `APPLICATION_PENDING` readback all succeed live.

#### D. Earn the first externally approved commission

- [ ] **A15.1** Keep ElevenLabs active and poll HubSpot/Impact; never resubmit the
  rejected Kit application unchanged or submit to paused Notion.
- [ ] **A15.2** Admit another English B2B/creator program only after official terms,
  allowed-channel, payout, tracking-link ownership, and fresh login are Skill-
  receipted; applications themselves are durable browser jobs.
- [ ] **A15.3** Continuously capture buyer questions and product evidence through
  CRWL, `gh`, authenticated X, and admitted platform adapters.
- [ ] **A15.4** Produce one source-bound decision asset per qualified intent with
  disclosure-before-CTA, limitations, alternatives, and exactly one owned link.
- [ ] **A15.5** Publish through the owned site and English X browser, require public
  readback, and refuse duplicate effects.
- [ ] **A15.6** Reconcile post-baseline clicks and provider transactions on every
  eligible poll while continuing research and publication work.
- [ ] **A15.7 — E0.** Record one real post-baseline provider click connected to a
  live English placement; do not manufacture or self-click it.
- [ ] **A15.8 — E1.** Record one non-test `approved` commission with public
  placement, provider source hash, transaction lineage, costs, and Telegram event.

#### E. Scale the proven local loop to USD 10,000/month

- [ ] **B16.1** Reach ten mature comparable English placements and change only one
  variable per experiment.
- [ ] **B16.2** Rank by approved net commission per 1,000 qualified impressions and
  per content dollar; engagement is diagnostic only.
- [ ] **B17.1** Add at least three independently receipted providers/offers and keep
  provider, offer, and channel concentration at or below 40% of net commission.
- [ ] **B20.1 — A2.** Complete four revenue-positive weeks with positive net margin,
  zero manual execution, and at least one live self-heal.
- [ ] **B21.1** Compute the observed commission/traffic requirement for USD 10,000,
  allocate 80% to mature winners and 20% to bounded experiments, and stop cohorts
  with negative approved unit economics.
- [ ] **B21.2 — A3.** Reconcile three consecutive months at USD 10,000 gross while
  showing net, reversals, costs, payout timing, and concentration separately.

#### F. Add locales, then package the already-proven loop

- [ ] **B18.1** After E0, create a separate Japanese browser identity, provider
  membership/link, native evidence pack, disclosure, attribution cohort, and J0/J1
  canary; never mix Japanese and English on one account.
- [ ] **B19.1** Admit Spanish only after English and Japanese proof and the same L0
  gate; later languages follow observed executable-offer value, not population.
- [ ] **C22.1** After E1, remove machine-specific paths while preserving the exact
  local state machine and keeping credentials, sessions, receipts, and ledgers out
  of Git.
- [ ] **C23.1** Ship one-command macOS install, minimal credential intake, isolated
  browser/profile provisioning, health, update, rollback, and uninstall commands.
- [ ] **C24.1 — OSS1.** Reproduce pre-publication readiness on a clean macOS user
  without copying this Mac's secrets or mutable state.
- [ ] **C25.1** Publish a privacy-safe ledger verifier and dated prior-art registry;
  make only the qualified claims allowed by section 7.1.
- [ ] **D26.1** Only after A2 + OSS1, replace launchd/browser ownership with tenant
  scheduler and isolated remote browser workers while keeping the same contracts.
- [ ] **D27.1–D30.1** Add encrypted tenant authority, deletion/audit controls,
  Telegram/web UX, prove one isolated cloud E1, then pilot phone-only users.

### Phase A — Current Mac earns the first real commission

1. **DONE.** Converge the canonical skill, private state boundary, immutable
   release, and legacy evidence without touching the earning Coconala runtime.
2. **DONE.** Finish the Railway rollback and delete the two Affiliate-only
   staging variables; rollback commit, removed deployment, zero variables, and
   HTTP `404` on the old route are live-read back.
3. **DONE.** Make `placement_ready` exact-once and prove the installed release,
   both launchd owners, CDP `9324`, wake lock, browser-start wait, and append-only
   local receipts from the installed artifact rather than source.
4. **DONE.** Change the coordination cadence from 30 minutes to 10 minutes;
   provider, research, and publication cooldowns remain independent and bounded.
5. **PARTIAL.** Complete credential-first signup/login/recovery/application states.
   ElevenLabs dedicated login is live-proven through the reusable semantic CDP
   playbook, and its state poll is wired into each 10-minute source wake with a
   stable transition ID. Impact is pending and Kit is rejected. Impact status
   polling and any future provider write still require exact-once semantic playbooks.
6. **DONE.** Rebrand and verify English `@selawmqt`; its isolated `x-en:9326`
   launchd owner, English name/bio, disclosure, URL, semantic apply, idempotent DOM
   readback, and receipt are live. The first publisher boundary and its minimal
   regression check now implement the duplicate-post fence and post-level exact
   readback. The first disclosed artifact is `LIVE` at status
   `2088728168534597644` with a durable `X_POST_PUBLIC_READBACK` receipt.
7. **PARTIAL.** The source scout now runs CRWL and `gh` from a versioned English
   ElevenLabs plan and stores immutable raw artifacts plus provenance, license,
   locale, evidence class, parser version, freshness, and explicit adapter failure
   classes outside Git. The live run captured five official pages and one official
   MIT repository. Add authenticated X read-only capture and record a failed
   adapter receipt before this item becomes DONE.
8. **DONE.** The content and owned publisher reuse Writer's immutable artifact,
   source-hash, useful-reader-first, disclosure-before-CTA, and Git-external state
   boundaries without touching its live loop or revenue. The publisher also reuses
   its exact-target git delivery and marker-bound public readback pattern. Production
   commit `fd9489bee59946bddc06bb127b2bfca0694d7e61`, Actions run `31906437192`,
   and rendered SHA-256 `f7055977871bb405af0c491d29c74d41d591f87b95a551425dc5beece07d0039`
   close the first production `LIVE` receipt.
9. **DONE.** The useful non-affiliate English foundation artifact is public at
   `https://aniccaai.com/blog/how-to-test-ai-voice-tools-before-you-pay`; CRWL and
   the installed publisher independently read back the title, disclosure, evaluation
   marker, and purchase-decision marker after the production smoke passed.
10. **DONE.** The first source-bound ElevenLabs plan comparison is live-built
    against the private executable direct link. The deterministic policy receipt
    passed artifact hash, exact fresh source hashes, disclosure-before-CTA, one
    owned HTTPS tracking link, and forbidden-guarantee checks. The existing
    exact-once boundary recorded one `TRACKING_LINK_VERIFIED` placement intent
    without exposing the link, and the artifact is `READY_FOR_PUBLICATION`.
11. **DONE.** The policy gate passed and the disclosed article is `LIVE` at
    `https://aniccaai.com/blog/elevenlabs-plans-for-solo-creators` from production
    commit `a333cf55044dbddf17f906150a173e1ee000aea1`. Actions run `31906958939`, the
    installed publisher, and CRWL independently verified the public result and
    exact tracking link. The matching disclosed X artifact is `LIVE` at status
    `2088728168534597644`; its shortened anchor resolves to the exact owned article,
    and the fixed installed release reconciled the first effect without duplication.
12. **PARTIAL.** PartnerStack account/email/team/partnership/program-terms bootstrap
    is complete and the rendered overview is accessible. `revenue observe` records
    bilingual dashboard cards and preserves the first aggregate and timestamp as
    immutable baseline: one total click, zero signups, zero paid signups, and zero
    revenue/pending/paid. Source and installed release replays both observed zero
    delta and returned the provider browser to ElevenLabs home. The installed
    report capture also proved zero commission rows through the official JSON
    response and zero payout rows through rendered readback. The installed
    reconciler replayed the same source twice with zero appended transitions;
    status changes are append-only and customer PII is excluded from normalized
    rows. Approved and reversed stay `null`. Add a real non-empty transaction and
    placement attribution before DONE; estimates remain out.
13. **PARTIAL.** Durable owner-readable Telegram delivery is live with append-before-
    send, stable-UUID dedupe, and provider message-ID receipts. The real empty-report
    transition is proven; click, commission, self-heal, and blocked variants close
    only when those external states actually occur.
14. **PARTIAL.** Same-job process-boundary resume and X ambiguous-write dedupe are
    live-proven. Application reconciliation, login recovery, selector repair,
    provider/channel quarantine, watchdog, and cost caps remain.
15. **PENDING — Gate E1.** Run unattended until one non-test approved English
    commission is joined from public placement to provider receipt.

### Phase B — Local profitability and multilingual pods

16. **PENDING.** Run at least ten comparable English placements; change one
    variable per canary and allocate by net commission, never engagement alone.
17. **PENDING.** Add only eligible English B2B/creator providers so no provider,
    offer, or channel exceeds 40% of net commission.
18. **PENDING.** After English E0, create an isolated Japanese identity, browser,
    provider/link, native evidence pack, disclosure, ledger cohort, and J0/J1 canary.
19. **PENDING.** After English and Japanese proof, admit Spanish through the same
    L0 gate; later languages are ranked by executable offers and observed net value,
    not population or translation volume.
20. **PENDING — Gate A2.** Achieve four revenue-positive weeks, positive net margin,
    zero manual execution, and receipted recovery from at least one real failure.
21. **PENDING — Gate A3.** Reach three externally receipted months at $10,000 gross
    commission while reporting net profit, reversals, costs, and concentration.

### Phase C — Open-source reproducibility

22. **PENDING.** Remove machine-specific paths and package only proven dependencies,
    provider contracts, browser profiles, state migrations, and rollback logic.
23. **PENDING.** Ship one-command macOS install, credential intake, health check,
    update, uninstall, and local privacy-safe proof ledger.
24. **PENDING — Gate OSS1.** On a clean macOS user, install from the public repo and
    reproduce the pre-publication state without copying sessions, secrets, or receipts.
25. **PENDING.** Publish the independent verifier and prior-art registry; describe
    observed earnings precisely and avoid unqualified “world's first” claims.

### Phase D — Cloud/web app for phone-only users

26. **PENDING after A2 + OSS1.** Replace launchd with a durable tenant scheduler and
    local profiles with isolated remote browser workers; keep the same job/state API.
27. **PENDING.** Add encrypted tenant credentials, per-tenant provider consent,
    budgets, audit receipts, browser leases, data deletion, and account-risk controls.
28. **PENDING.** Build the Life Manager web/mobile UX for onboarding, goal setting,
    provider status, actions, earnings, blockers, self-heals, and Telegram linking.
29. **PENDING — Gate C1.** One cloud tenant reproduces the local E1 lineage without
    cross-tenant state, credential, browser, link, or ledger leakage.
30. **PENDING.** Pilot phone-only users, compare cloud unit economics with local,
    then scale only cohorts that remain compliant and net-profitable.

## 10. Rejected designs

- **Generic high-volume AI SEO farm:** fastest way to produce pages, but violates
  the reader-value and search-quality constraints and teaches from vanity volume.
- **Amazon/Rakuten-only:** simplest auth model, but low-price physical goods alone
  create concentration and payout ceilings.
- **X-only direct links:** cheap distribution, but weak ownership, fragile reach,
  poor long-form trust, and incomplete attribution.
- **Separate autonomous agents with separate ledgers:** parallel-looking but
  produces duplicate offers, conflicting claims, and double-counted revenue.

The strongest rejected alternative is the Amazon/Rakuten deal-feed model: it
has abundant inventory and easy creative generation. It loses because a feed
optimizes output count instead of reader intent and net commission, and it
cannot safely support the $10,000 gate without extreme traffic.

The most likely way this recommendation is wrong is that an authenticated
provider reveals an unusually strong, durable, low-reversal physical-product
program. The allocator can discover that from receipts and increase its share
without changing the architecture.

## 11. Visible uncertainties and blocked proof

### 11.1 Cleared implementation decisions

- All external platform operations are browser-only. Postiz and third-party
  publishing APIs are neither prerequisites nor fallbacks. Provider tracking
  links are used directly; local JSONL/SQLite interfaces may coordinate state,
  but the local proof phase owns no public redirect service.
- Rebranding, account creation/recovery, program application, dashboard scraping,
  report download, and payout reconciliation are Agent states, not manual setup.
- Architecture is one durable portfolio Agent with specialized role prompts and
  one ledger; it is not a multi-agent swarm with separate truths.
- Stable flows are deterministic cached playbooks; unfamiliar or drifted pages
  invoke the semantic planner; every write requires fresh rendered readback.
- Browser retries are at-most-once: an ambiguous write is externally searched by
  content/action fingerprint before any retry.
- The $10,000/month target closes only after three consecutive externally
  receipted months; software completion cannot promise revenue.

### 11.2 Must be cleared by implementation tests

- Reproducible bootstrap on a clean macOS user/profile; pinned browser/runtime
  versions; encrypted secret persistence; upgrades and rollback. Ubuntu parity is
  not an initial completion condition.
- Semantic action schema, browser profile leases, account switching, downloads,
  DOM/screenshot hashing, selector drift, localization, popups, and crash resume.
- Signup/login/recovery/profile workflows that resume without duplicating an
  account, application, post, or payout request.
- Reliable publication fingerprinting when a website returns an ambiguous result;
  deletion/edit/repost policy; acquisition cadence and account-risk caps.
- Durable scheduler ownership, watchdog, cost budgets, Telegram outbox/dedupe,
  receipt compaction, disaster recovery, and safe remote updates.
- Provider playbook discovery and promotion: how many successful replays are
  needed before a semantic path becomes cached, and what drift revokes it.
- Browser-only provider-report normalization, currency/FX timestamps, sub-ID
  coverage, reversal windows, and payout artifact integrity.

### 11.3 Can only be learned from live canaries

- The English niche is fixed to B2B SaaS and creator/productivity software.
  HubSpot is the first pending browser-verified application; Kit is a rejected
  receipt and Semrush remains unqualified until its current audience/site gate is
  satisfied. Live canaries determine which approved offer, content format,
  cadence, and acquisition path produces the highest approved net commission.
- Actual reach throttling/suspension rate, UI-drift rate, provider approval rate,
  CTR, partner conversion, reversal/refund rate, payout delay, and unit economics.
- Time and capacity required for the first approved commission, $10k/month, and
  later scale; prompt copying cannot determine these outcomes.

### 11.4 Irreducible external constraints

- A scratch computer cannot invent a legal identity, email/phone ownership, tax
  data, payout account, contractual consent, or affiliate-program acceptance.
  The deployment contract therefore requires an authorized identity bundle.
- Email/SMS OTP may be automated only when the user-authorized inbox/device is
  available. CAPTCHA, biometric checks, KYC, tax attestations, and contracts are
  never bypassed or fabricated; the Agent records `EXTERNAL_CHALLENGE` and keeps
  independent work running.
- X explicitly warns that non-API website scripting may permanently suspend an
  account. Browser-only operation is the user's accepted product direction, but
  no implementation can make it platform-approved or guarantee account survival.
- Providers may reject the applicant, prohibit a channel, change terms/UI, reverse
  commissions, withhold payout, or terminate a program. Quarantine and portfolio
  diversification limit damage; they cannot erase this uncertainty.

- Kit has one receipted application and an authenticated official rejection
  email. The email lists possible audience, promotion-method, website-content,
  and application-detail issues without selecting one applicant-specific cause.
  Kit stays `APPLICATION_REJECTED`; no unchanged reapplication is allowed.
- English X ownership/login is resolved as `sela` / `@selawmqt`; legacy
  `@aniccaen` is inactive. The account has 128 mixed-language historical posts
  and 0 followers, so rebranding and audience acquisition are required and
  organic distribution power remains unproven.
- One disclosed owned article and one browser-published Affiliate X placement are
  live and public-readback verified. No post-baseline organic click exists yet.
- Amazon JP is `AUTH_RECOVERY_OTP_REQUIRED`; Rakuten remains `AUTH_REQUIRED`;
  Associates/affiliate acceptance is unknown.
- English total addressable market and the claim that it is larger than Japanese
  are not quantified by the collected primary sources.
- No first-party audience baseline exists yet: qualified impressions, clicks,
  email subscribers, conversion rate, reversal rate, and payout delay are unknown.
- HubSpot and every newly discovered program are candidate economics until
  approval, allowed-channel ownership, executable-link readback, and realized
  payout. Kit is already rejected; Semrush is not yet an eligible application.
- The Smart Passive Income result is a first-person case with an established
  audience and relationship; its causal contribution cannot be isolated and its
  outcome is not transferable by prompt copying.
- Inspected OSS repositories show useful role/adapter/runtime patterns but no
  verified autonomous approved-commission loop. Code reuse is limited to actual
  compatible license files; README license claims and popularity are insufficient.
- The current `x-search-cdp` probe has no logged-in X tab. Public profile fallback
  works, but authenticated X search/article collection remains unhealthy until the
  Agent restores and verifies the exact daily-driver tab.
- The existing TikTok Apify adapter has implementation code, but its combined
  test module imports a deleted `rss_parser`; it needs a focused test and live
  one-item Actor receipt before Affiliate production use.
- Spanish has official multi-language program supply, but no first-party account,
  audience, executable offer, native canary, or unit economics. It remains a
  candidate pod, not a proven second-largest or next-most-profitable market.
- F2 has a pushed implementation and root-verified focused tests, but lacks fresh
  review, live model/provider boundary proof, a clean worktree audit, and a
  collection-safe all-tests command.
- Affiliate Telegram append-before-send, stable-UUID dedupe, provider message-ID
  receipt, `SELF_HEALED`, and `BLOCKED` are live-proven. Real `CLICK_DELTA`,
  `COMMISSION_PENDING`, and `COMMISSION_APPROVED` wait for those external states.
- Production placement and same-job X crash resume are proven. Organic click,
  approved commission, paid payout, full research-to-money wake, and an induced
  end-to-end self-repair remain unproven.
- `ai.anicca.affiliate-browser`, `ai.anicca.affiliate-impact-browser`,
  `ai.anicca.affiliate-x-browser`, and `ai.anicca.affiliate-loop` are registered;
  non-Affiliate browser ports and legacy earning-loop owners are out of scope.
- `$10k`, `$10M`, and `$100M` are outcome gates. There is no honest date or
  probability forecast until live cohorts and partner capacity are measured.
