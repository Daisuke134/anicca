# SSOT §9.0 item 4c — the non-publishing probe cannot exist, and here is the measurement

Measured 2026-08-07. Evidence as data: `config/note-422-draft-surface-observation.json`.
Executable contract: `tests/test_note_422_publish_only_surface.py`.

Item 4c asked for a bounded probe that narrows the `note/ja` rejection

```
NoteNativePublishError: Note native publish HTTP 422:
{"error":{"code":"invalid","message":"本文に利用できない内容が含まれています。"}}
```

by bisecting the rejected body against note's **draft** surface, so nothing public is
ever produced. The prerequisite for building it was to show the draft surface rejects
the same body the same way. It does not. The probe is therefore not built.

## What each note surface in this repository actually does

| Script | Requests that reach note | Effect |
|---|---|---|
| `scripts/note-stage1-render.py` | none — local markdown transform, table PNGs rendered from `file://` | nothing |
| `scripts/note-draft-ledger.py` | none — local JSON with an flock'd read-modify-write | nothing |
| `scripts/note_stage2_assets.py` | none to note — `kroki.io` renders mermaid, or canonical run assets are used hash-bound | nothing |
| `scripts/note-stage2-publish.py` | `upload_body_image` (note image upload), then `POST /v1/text_notes/draft_save?id=N&is_temp_saved=true` via note-mcp `update_article` | **mutates a draft**, never public |
| note-mcp `create_draft` | `POST /v1/text_notes`, then the same `draft_save` | **creates a draft**, never public |
| `note-publish/publish-paid.py` `get_authenticated_note` | `GET /api/v3/notes/{key}` authenticated | read-only |
| `note-publish/publish-paid.py` `put_paid_note` | `PUT /api/v1/text_notes/{numeric_id}` with `status: "published"` | **the only public one — this is what returned 422** |
| `note-publish/publish-paid.py` `verify_note_publication` | `GET /api/v3/notes/{key}` unauthenticated | read-only |

## The rejected payload is reconstructible offline, exactly

`publish-paid.py` writes `payload_sha256` into `gates/note-native-effect.json` *before*
the PUT, so that hash names the exact bytes note refused. The incident draft
`n47735d9811e8` is still `status: draft`, so its body is still retrievable. Replaying
`build_paid_publish_payload` over that body offline, sweeping every distinct separator
block, reproduces the recorded hash exactly:

```
4e06c659a09e459bd0f041ebd4d729b80878a1e68f5d195a652c55b9a56b67d6
  price 500 · tags [] · after_chars 2447
  separator d44c0a65-1a70-415e-b959-27294926cdc7
  free_body 8019 chars · pay_body 5681 chars
  body 13700 chars · 62 blocks · visible body_length 3817
```

Zero requests to note are needed to obtain it. Whatever narrows this failure next starts
from the real payload, not a guess.

## The measurement

The exact rejected body was replayed against the draft surface on a throwaway scratch
draft — whole, then as each half of the rejected split. Three `draft_save` calls,
3 seconds apart, no `status` field in any payload, no publish endpoint touched.

| Fragment sent as `body` | Result |
|---|---|
| the whole 13700-char rejected body | `201` `{"data":{"result":true,…}}` |
| `free_body` alone (8019 chars) | `201` `{"data":{"result":true,…}}` |
| `pay_body` alone (5681 chars) | `201` `{"data":{"result":true,…}}` |

The scratch read back `status draft`, `price 0`, `publish_at null` after every write; its
unauthenticated public URL returned `404`; it is now `status deleted`. The incident's own
article was only ever read.

**The draft surface does not reject this content.** A draft-surface bisection has no
signal to bisect.

## Why that is not merely bad luck

The rejected request carries `free_body`, `pay_body`, `separator`, `price` and
`status: "published"`. `draft_save` carries `name`, `body`, `body_length`, `index`,
`is_lead_form`, `hashtags` — and no `body` field exists in the rejected payload at all.
The paid split has no draft representation, which this repository had already measured
independently on 2026-07-16 and recorded in `publish-paid.py`'s own module docstring:
paid type, price and the paywall line are transient editor form state that note commits
only on 投稿する.

So the surface that rejected the article and the surface that would have been bisected do
not accept the same object. Building the probe anyway would have measured a different
validator on different inputs and returned a confident wrong answer.

## The honest alternative

Do not probe. Make the next real publish attempt carry the narrowing evidence, at zero
additional public artifacts and zero additional requests, because the daily loop attempts
that publish regardless.

1. **Fingerprint the payload where it is already hashed.** `publish-paid.py` writes
   `note-native-effect.json` with `state: intent` before the PUT and `state: rejected`
   plus the response body after. Add a normalized structural fingerprint next to
   `payload_sha256` — per-field lengths, per-block ids and hashes for `free_body` and
   `pay_body`, which block the separator names, whether the split lands inside an
   element, and inventories of embed/URL and character classes. Hashes and counts only,
   never raw text. That costs no request and turns each real attempt into one observation.
2. **Bisect along the axis the loop already varies.** `after_chars` is chosen per run, and
   it alone changes `separator`, `free_body` and `pay_body` for the same body. If the 422
   tracks the split point, the offending element is identified from production attempts
   alone; if it does not, the body is implicated and the daily-changing body supplies the
   second axis.
3. **Use today's exclusion as the prior.** note's draft validator finds nothing
   objectionable in these bytes, whole or split. Whatever the publish validator objects to
   is a property of the paid-publish request, not a banned string in the body.

## What is still unverified

- **Determinism of the 422.** The PUT was never re-sent, because re-sending it is the one
  action that can make something public. One observed 422 is not proof of a stable rule.
- **Which element note objects to.** This narrows only by exclusion.
- **`PUT /v1/text_notes/{id}` with a non-published status.** Not attempted. It is the same
  endpoint and probably the same validator, but the risk that note publishes anyway cannot
  be bounded in advance, and a transient public artifact is still a public artifact.

## Incidental finding, worth keeping

`DELETE /api/v1/notes/n/{key}` returns `422 {"error":"Unprocessable Entity"}` when
`Origin`, `Referer` and `X-Requested-With` are absent, and `200 {"data":{"result":true}}`
with them. A 422 from note is therefore not always about content — the same status code
carries at least one pure header-shape failure.
