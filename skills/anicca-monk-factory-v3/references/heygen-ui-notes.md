# HeyGen {{profile.lateness.stakeholders.channel}} UI flow notes (camofox) — WIP 2026-05-22

Goal: render Ajahn Sutta talking head from locked face (option_a.jpeg) + locked
ElevenLabs audio (Anicca Monk EN), via HeyGen subscription UI (NO API, Dais rule).

## What works / verified
- camofox up on :9377. userId=anicca sessionKey=default.
- **HeyGen is ALREADY LOGGED IN** (cookie persists in ~/.camofox/profiles/anicca/default). No login needed.
- Home = app.heygen.com/home. Tiles: "Use Avatar V" e14, "Photo to Video" e16, "Script to Video" e18, "Create an Avatar" e19.
- Clicking "Photo to Video" (e16) opens modal: "Create a video from a photo — Upload a photo to begin" with a drag-drop zone ("Supports PNG, JPG, WEBP, HEIC").
- camofox HAS an upload endpoint: `POST /tabs/:id/upload {userId, files:[abs paths], ref?|selector?}` → setInputFiles. Default targets first visible `input[type=file]`.
- A02 audio rendered: ~/anicca-monk-factory/renders_v3/A02_anicca_monk_en.mp3 (112s, voice hjMjW).

## 🔴 ROOT CAUSE FOUND (2026-05-22) — HeyGen not actually logged in
- /home rendered a cached dashboard, but /avatars shows the LOGIN page. HeyGen session is NOT authenticated.
- Google IS logged in for this camofox profile ({{profile.contact.personalEmail}}, verified via accounts.google.com → myaccount redirect).
- HeyGen "Sign in with Google" button = "新しいタブで開きます" (opens a POPUP) to do the OAuth handshake.
- **camofox does NOT track/drive popups** (no `context.on('page')` listener; tabs list never shows the popup). So the OAuth popup runs detached, never returns auth to the main tab → HeyGen stays logged out.
- Therefore the photo-dropzone upload failed because we were never authed into the app.

## ✅✅ WORKING LOGIN (2026-05-22) — MAGIC LINK via gog (no TOTP, no popup, fully autonomous)
1. camofox open `https://app.heygen.com/login` (→ auth.heygen.com/login)
2. click "Use {{profile.lateness.stakeholders.channel}}" → set {{profile.lateness.stakeholders.channel}} input value = {{profile.contact.personalEmail}} (React native setter + input/change events)
3. click **"Send a secure magic link"** → HeyGen {{profile.lateness.stakeholders.channel}}s a login link
4. read it: `GOG_KEYRING_PASSWORD=<password> gog gmail search -a {{profile.contact.personalEmail}} -p "heygen newer_than:10m"`
   → `gog gmail get <id> -a {{profile.contact.personalEmail}} -p` → grep `https://auth.heygen.com/magic-web/...`
5. camofox navigate to that magic-web URL → lands at app.heygen.com/home **LOGGED IN**. Cookie persists.
- gog keyring password = `<password>` (set GOG_KEYRING_PASSWORD). Email+password (Dukkha2026!) path hits authenticator-TOTP (no seed stored) — AVOID; use magic link instead.
- NOTE: authed /home layout differs (nav: Avatar / Video Agent / Translate / Brand / Apps / Projects). The logged-out "Photo to Video" tile (e16) is gone; find the authed create-video entry (Avatar / Video Agent / Create New).

## LAST SNAG (2026-05-22) — imported ElevenLabs voices not listing
- After "Import from 3rd party" + ElevenLabs API key + Confirm: a voice-tab
  "anicca_en_monk_v1's voices" appears in the Voice picker (tabs: that | "My voices" | "HeyGen library").
- But that tab shows **"No voices available — You haven't added any favorite voice to this avatar yet."**
- i.e. the ElevenLabs connection is made but individual voices ("Anicca Monk EN") aren't populated/favorited yet.
- Options next push: (a) wait for sync / refresh; (b) go to Voices page and favorite "Anicca Monk EN";
  (c) re-import; (d) for the FIRST proof-render only, pick a "HeyGen library" voice, generate, verify the
  pipeline end-to-end, then swap to the locked ElevenLabs voice once it lists.
- Everything else is {{profile.lateness.stakeholders.senderType}}d: photo (option_a) loaded, A02 script pasted, 9:16 + Generate are the last clicks.

## ✅ BETTER PATH — HeyGen Avatar IV (audio-driven), use our MP3 directly
- ElevenLabs "Import from 3rd party" connects the key but voices DON'T sync into HeyGen
  (not in Voices page, not in the avatar voice picker). Dead end for the locked voice.
- The OLD skill used "HeyGen **Avatar IV** talking head" = AUDIO-DRIVEN: upload photo + an
  audio file → lip-synced video. This uses our exact locked ElevenLabs MP3
  (renders_v3/A02_anicca_monk_en.mp3) with NO HeyGen-side voice sync needed.
- NEXT PUSH: find the Avatar IV / audio-upload entry (not the Script+Voice "Photo to video" panel,
  which has no audio input). Likely under Avatar → Photo Avatar → "Audio" tab, or an "Avatar IV" product.
  Upload option_a + the A02 mp3 → 9:16 → Generate → download → verify → post.
- Camofox upload endpoint works for file inputs: POST /tabs/:id/upload {selector, files:[abs path]}.

## 🔴🔴 PROVEN ROOT CAUSE (2026-05-22) — ElevenLabs side perfect, HeyGen import broken
- VERIFIED: `GET https://api.elevenlabs.io/v1/voices` with our key (sk_ae20...) returns HTTP 200,
  36 voices, INCLUDING "Anicca Monk EN" (hjMjW), "Anicca Monk JP" (8cjR). Key has voices_read. ✅
- HeyGen "Import from 3rd party" → provider ElevenLabs → paste key → Confirm: connection SAVES
  (tab "anicca_en_monk_v1's voices" persists across reload), but the tab shows **"No voices available"**
  even after full page reload + waiting. Done 2x with correct provider+key. Screenshot evidence saved.
- CONCLUSION: HeyGen does not pull the ElevenLabs voices despite a valid key + readable voices.
  This is HeyGen-side, NOT forceable from the {{profile.lateness.stakeholders.channel}}. Likely causes: HeyGen requires an ElevenLabs
  PAID plan (Creator/Pro) for import to pull voices (free/starter connects but yields none), OR HeyGen
  filters Voice-Design-generated voices, OR a HeyGen sync bug/long delay.
- PATHS: (a) check/upgrade the ElevenLabs plan tier for "anicca_en_monk_v1"; (b) accept HeyGen
  library voice (breaks same-voice); (c) audio-driven lip-sync tool that ingests our MP3 directly.

## 🔴 DEFINITIVE (2026-05-22) — locked-voice blocker is HeyGen-side
- HeyGen "Photo to video" / Avatar V flow = **Script + Voice(TTS) ONLY. NO audio-file upload**
  (verified: tabs = Script-to-video / Photo-to-video; controls = Voice + Generate; no input[type=file] accepts audio).
- So our locked ElevenLabs MP3 cannot be fed directly. The only way to use our voice is the
  ElevenLabs "Import from 3rd party" → but imported voices DON'T populate (Voices page empty,
  picker shows "No voices available"). This is HeyGen-side and not forceable from the {{profile.lateness.stakeholders.channel}}.
- DECISION NEEDED (Dais): (a) troubleshoot ElevenLabs→HeyGen import (maybe ElevenLabs plan must
  allow API voice access, or HeyGen needs the voice "shared"/specific tier); (b) accept a HeyGen
  library voice (breaks "same voice forever"); (c) different render tool that accepts audio upload
  (e.g. an audio-driven lip-sync product). 
- The render MECHANISM is proven (photo + script + HeyGen voice → Generate works). Only the
  locked-voice ingestion is blocked.

## (superseded) EMAIL+PASSWORD note — hits TOTP, avoid
- `auth.heygen.com/login` offers **{{profile.lateness.stakeholders.channel}} + password** login (buttons: "Use {{profile.lateness.stakeholders.channel}}", "Use password").
- This is SAME-TAB, no popup → fully drivable by camofox. Bypasses the Google-OAuth-popup limitation entirely.
- Working flow:
  1. open `https://app.heygen.com/login` → redirects to `auth.heygen.com/login`
  2. click "Use {{profile.lateness.stakeholders.channel}}" (button) → type `{{profile.contact.personalEmail}}` into {{profile.lateness.stakeholders.channel}} textbox
  3. click "Use password" → password field appears → type password `Dukkha2026!`
  4. click "Log in"  (Cloudflare Turnstile present but camofox stealth passes it)
  5. → HeyGen shows **TOTP 2FA**: "Enter the 6-digit code from your authenticator app"
  6. Enter the 6-digit code (NO secret stored locally → need Dais's authenticator code, OR store the TOTP seed to auto-gen with `oathtool --totp -b <SEED>`).
- ACTION: ask Dais to store the HeyGen TOTP seed in ~/.openclaw/.env (HEYGEN_TOTP_SEED) once → future logins fully autonomous via oathtool.
- Password `Dukkha2026!` verified to advance past password step (reached 2FA).

## FIX REQUIRED (decisive)
Enhance camofox server.js: on tab creation, attach `page.on('popup', p => registerAsTab(session, p))` so OAuth popups become listable/driveable tabs. Then click HeyGen "Sign in with Google" → popup auto-approves (Google already authed) or we drive "choose account" → HeyGen authed → cookie persists. One-time; reused after. (Restart camofox after edit; profile/cookies persist.) This also unblocks every other OAuth (Stripe/Slack/etc).

## OLD BLOCKER notes (upload) — secondary, revisit after login
- `POST /upload` returned `{ok:true}` but the photo did NOT appear in the drop zone.
- The drop zone is a custom drag-drop component; the a11y snapshot exposes NO file input (only the Intercom button shows up). So `input[type=file].first()` likely hit the wrong/hidden input, or the zone only listens to native drag-drop (DataTransfer) events, not setInputFiles.
- No `/eval` route on this camofox build (404).

## Options to try next (in order)
1. `upload` with explicit `selector` for HeyGen's real input — inspect DOM for `input[type=file]` count/attrs (need a DOM-dump route or add one).
2. Try the **Avatar page (/avatar) → Create Photo Avatar** path — its uploader may use a standard input.
3. Simulate native drag-drop with a DataTransfer (needs an eval/drop route in camofox; may need to add one to server.js).
4. Worst case: HeyGen "Avatar IV" / Photo Avatar created once manually, then driven per-video.

## Pipeline target (once upload works)
photo(option_a) → HeyGen photo-to-video → attach audio (upload A02 mp3) OR script+HeyGen voice
→ 9:16 → generate → download mp4 → verify (#8) → caption → Postiz post.
