# Gig profile assets — provider-neutral, language-neutral

One source for every marketplace profile (Coconala, Lancers, CrowdWorks, Fiverr, Freelancer,
Upwork-class sites, and non-Japanese markets). Sites differ in field names and limits; the
substance below does not. Never re-author a profile per site — render this bundle into the
site's fields.

## Why this exists

Coconala is the only lane that has produced money, and its profile is the proven artifact.
Measured on Lancers 2026-08-31: the site itself states 「プロフィールの完成度が高いと受注率が
14倍になります」, and the Lancers profile sat at 50% with zero 実績 while the Coconala profile
was complete. Profile completeness is the highest-leverage lever before any application volume
work, which is why `ELZ-L03B` is ordered before `ELZ-L04`.

## Hard rules

- **Persona, not personal identity.** The working Coconala profile trades as
  `Kosuke｜教育×AI専門家`, not under the operator's legal name. Do not publish the operator's
  legal name, address, date of birth, phone number, or identity documents to any marketplace.
- **Illustrated avatar, never a real photograph.** The proven avatar is a stylised character
  image. This keeps the asset reusable across sites and languages and avoids publishing a face.
- **Every claim must be true.** Credentials on the badge must correspond to a verified fact.
  No invented years of experience, no invented residence, no invented certifications.
- Identity verification that requires uploading personal documents is **operator-only** and is
  never automated. If a site gates earning on it, record it as a blocker; do not fabricate.

## The bundle

### Persona
- handle / display name: `Kosuke`
- role tagline: `教育×AI専門家`
- secondary role line: `プロダクトデザイナー／資料制作`
- rendered display name: `Kosuke｜教育×AI専門家`

### Value proposition (cover headline)
- primary: `AI活用 × 教育・資料作成`
- supporting: `PowerPoint制作／業務自動化／研修資料の内製化を支援`

### Trust promises (cover strip)
- `修正無制限`
- `即日対応可`
- `平日9-23時 リアルタイム返信`

These are operational commitments, not claims about the past, which is why a profile with zero
completed jobs can still carry them honestly. Keep them only while the lane can actually meet them.

### Credential badge
- `慶應義塾大学卒`
- `教育×AI専門家`

### Price anchor
- entry: `AI活用支援・業務自動化 5,000円〜`
- category label: `生成AI活用・開発・制作`

### Images
- `avatar` — stylised character portrait, square, used as the profile icon
- `cover` — wide banner carrying the headline, supporting line, trust strip and badge

Both are assets, not per-site artwork. Store the source files next to this file and re-render
text layers per language rather than redrawing. Generated cover art per locale is acceptable;
the avatar stays identical across sites so the persona is recognisable.

## Rendering to a new marketplace

1. Map persona → display name field; role tagline → headline/title field.
2. Map value proposition + supporting line → self-introduction, expanded to the site's minimum
   length (Lancers requires 300+ characters and already satisfies this field).
3. Map trust promises → whatever the site calls service commitments, or append to the intro.
4. Map credential badge → education / qualification fields, only where the claim is verified.
5. Map price anchor → the cheapest published package, so the profile has an entry point.
6. Upload `avatar`; upload `cover` where a banner field exists.
7. Complete every non-document verification the site offers (NDA agreement, e-mail, business
   category). Leave document-based identity verification to the operator.
8. Read the profile back from the public URL and record completeness before applying to anything.

## Localisation

The bundle is authored in Japanese because the proven lane is Japanese. For English, Spanish,
Portuguese, Tagalog and other markets, translate the persona tagline, value proposition, trust
promises and price anchor; do not translate the operator's legal identity because it is not here.
Currency and price anchors are per-market and must be re-derived, not converted blindly.

## Open items

- Source image files for `avatar` and `cover` are not yet stored beside this file; they currently
  exist only inside the live Coconala account. Capture them into this directory so a new
  marketplace can be onboarded without touching the Coconala browser.
- Lancers, as of 2026-08-31, is missing: profile photo, business experience / qualification,
  identity verification, NDA confirmation, phone verification. Of these, business experience and
  NDA confirmation are automatable from this bundle; identity and phone verification are
  operator-gated.
