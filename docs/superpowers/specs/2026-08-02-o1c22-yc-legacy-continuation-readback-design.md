# O1C-22 YC Legacy Continuation Readback Design

## Goal

Determine from the current authenticated YC Home whether the legacy Summer 2026 application ID can continue as the current Fall 2026 application. Record a privacy-minimal, content-addressed receipt without editing either application, starting another application, or submitting anything.

## Observed identity boundary

The canonical spec names legacy application `99b966b0-7e90-4856-ab0d-93651488a4ea`. Existing O1C-04 through O1C-08 evidence binds the submitted Fall 2026 application to `0b61fe42-e383-490d-b60e-04f1ad7ec5df`. They are distinct provider identities, so an old state file cannot answer whether YC currently offers a continuation path.

## Considered approaches

1. Save a manual browser note. This is fast but cannot reject a copied, stale, or internally contradictory claim.
2. Perform a live read-only inspection and bind an agent assessment to exact page excerpts, application links, timestamps, and body digests through a deterministic receipt builder. **Selected.**
3. Rewrite the complete YC browser adapter. This would mix continuation inspection with transport migration, current fact updates, preview, and submission owned by O1C-24 through O1C-26.

## Architecture

```text
existing CloakBrowser daily-driver :9222
                    |
         one temporary owned tab
                    |
          +---------+----------+
          |                    |
     YC /home GET       legacy /apps/<id> GET
          |                    |
          +---------+----------+
                    v
        agent reads full current surfaces
        and provides exact supporting excerpts
                    |
                    v
       deterministic receipt validator
       ├─ exact HTTPS origin and paths
       ├─ current and legacy UUID identity
       ├─ excerpt containment
       ├─ source-body SHA-256
       ├─ application-link inventory
       ├─ observation chronology
       └─ cross-field consistency
                    |
                    v
        privacy-minimal continuation receipt
```

The temporary tab is closed in `finally`; existing tabs and the browser process remain untouched. Browser reads use GET navigation only. No button, form, input, file control, or submit control is activated.

## Judgment boundary

The agent owns the semantic reading of the current pages: which text states the current batch/status, which text identifies the legacy batch, and what the absence of a legacy Home link means for the user-facing continuation path. It supplies exact excerpts and a concise rationale.

Deterministic code owns only fixed-format parsing and bookkeeping. It verifies that excerpts occur in the supplied page bodies, hashes those bodies, validates exact YC URLs and UUIDs, checks that Home links the current application but not the legacy ID, checks that the legacy preview is still bound to the legacy ID, and rejects cross-source or time-inconsistent observations. It does not use keyword or regex classification to infer page meaning.

## Receipt decision

The supported current observation is `separate_historical_application`:

- authenticated Home links the Fall application ID and does not link the legacy ID;
- the Fall and legacy IDs differ;
- the legacy direct preview remains accessible as a Summer 2026 application;
- no current Home continuation control is observed for the legacy ID.

This means the old ID is not the identity used for the current Fall application and the current Home offers no path to continue that old ID into Fall. It does **not** claim that an undocumented YC backend operation is impossible. The safe operational consequence is to keep the already-submitted Fall application, never create or submit a duplicate, and retain the Summer application only as historical source material.

## Privacy and evidence

Raw Home/preview bodies, founder details, answer text, cookies, headers, and browser WebSocket URLs are never persisted. The receipt stores only:

- source URL and observation time;
- source body SHA-256 and length;
- current and legacy application IDs;
- batch/status labels selected by the agent;
- hashes of exact supporting excerpts;
- application-link inventory;
- decision, rationale digest, and receipt digest;
- tab ownership counts and zero-effect assertions.

## Failure behavior

Unknown authentication, non-YC origin, redirect away from the exact path, missing current application link, legacy ID present on Home, identical current/legacy IDs, inaccessible legacy preview, excerpt mismatch, stale or reversed timestamps, raw-secret fields, or any observed write operation fails closed. Such a failure leaves O1C-22 open and performs no recovery write.

## Scope

O1C-22 records current identity/continuation behavior only. O1C-23 owns current official batch/deadline/amount/URL facts, O1C-24 owns browser transport migration, O1C-25 owns full answer/media/progress preview, and O1C-26 owns any exactly-once Submit effect.

