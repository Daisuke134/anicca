# O1C-21 YC Provider Knowledge Port Design

## Goal

Deprecated `apply-to-yc` is no longer executable knowledge. Its useful form knowledge becomes a checked-in, content-addressed contract consumed by the successor YC provider. The port covers the 20-field main page, founder video, demo video, and progress page. It does not decide current batch facts, reuse stale answers, open a browser, or submit an application.

## Considered approaches

1. Copy `yc-w26.json` into the repository. This preserves names but also preserves stale value sources, per-field reloads, ambiguous `Yes` clicks, and unverified success.
2. Add a canonical manifest plus a deterministic plan builder. This preserves field/video/progress knowledge while requiring current resolved values, exact source references, page-atomic execution, closed readback, and zero submit operations. **Selected.**
3. Replace the complete generic funder form engine. This could remove more runtime debt, but it mixes O1C-21 with browser migration, current YC facts, preview, and submission owned by O1C-22 through O1C-26.

## Boundary

The agent reads current Application Kit, profile, dashboard, and provider surface and decides the truthful value for each semantic answer. Deterministic code does not infer answer meaning. It verifies the exact inventory, source-reference provenance, operation grouping, file digests, progress-vector shape, locator strategy, readback contract, and plan digest.

```text
deprecated apply-to-yc                  current truthful sources
  20 field names ─────┐                 Application Kit / profile / dashboard
  video + demo ───────┼──> canonical manifest <── resolved values + source refs
  progress shape ─────┘                           |
                                                  v
                                      content-addressed preview plan
                                      ├─ main: one page-atomic patch
                                      ├─ video: one exact file operation
                                      ├─ demo: one exact file operation
                                      └─ progress: one page-atomic patch
                                                  |
                                      readback required for every operation
                                      submit_operations = 0
```

## Canonical contract

`apps/life-manager/config/yc-application-provider.json` is the successor provider's structural source of truth. It records provenance from `apply-to-yc`, the existing `yc-application` browser route, four page paths, exact field order, React-native setter events, and save/readback requirements.

The main page contains exactly:

```text
name describe url productLink make where wherewhy howfar worked techstack
since acc exp get money ideas whyapply howhear cofounder others2
```

All 20 mutations are one page-atomic operation. The executor must resolve every locator before changing anything, apply all native setters without navigation, save once, then read back all fields. A missing or mismatched field fails the page; it is never reported as filled.

Founder and demo videos retain the exact `video/*` file-input knowledge. Founder video must carry the already validated `application-kit://videos/Anicca_intro_EN.mp4` source contract. Demo remains a separately resolved current Application Kit video; legacy `~/Desktop/ycsummer2026.MOV` is not canonical.

Progress retains `usernums`, `revenuesource`, `growthrate`, and exactly six chronological monthly revenue inputs. Its two `Yes` controls are scoped by exact question label (`Are people using your product?` and `Do you have revenue?`) plus exact option text. Global text-regex clicking is forbidden. The browser executor must first bind each question container and prove exactly one matching option within it.

## Safety and ownership

- `mode=preview_only`; `submit_operations=0` is invariant.
- The manifest contains no application ID, batch, deadline, amount, static answer, local secret path, or browser launch command.
- O1C-22 owns live application continuation, O1C-23 current official facts, O1C-24 transport migration, O1C-25 full preview, and O1C-26 exactly-once submission.
- A plan is accepted only when all 28 logical fields are present: 20 main, 1 founder video, 1 demo video, and 6 progress fields (three text, one six-value series, two scoped choices).
- Every value has a non-legacy source reference and every file has a SHA-256 digest. Raw values are not included in evidence; evidence records only inventory and digests.
- Every mutation requires exact readback before success. Submission state remains owned by the authoritative receipt path, never by provider stdout.

## Runtime handoff

The checked-in builder produces the provider-neutral operation plan that `apply-to-funder` must consume when its YC browser adapter is replaced. O1C-21 proves that the successor contract contains all legacy knowledge and rejects the known unsafe patterns. It intentionally does not alter the live browser script because route transport and actual preview/submit are later atomic items.

