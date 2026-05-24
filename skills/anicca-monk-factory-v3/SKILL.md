---
name: anicca-monk-factory-v3
description: "Ajahn Sutta AI-monk video factory (Shalev/Yang Mun system, faithfully copied). Locked face + locked voice + 30-script bank. Renders talking-head shorts via HeyGen UI ({{profile.lateness.stakeholders.channel}}, NOT API), posts to TikTok/IG via Postiz. EN-first; JP shares the face, swaps voice."
homepage: https://github.com/anicca-ai/anicca-monk-factory
metadata:
  tags: tiktok, ai-avatar, heygen, elevenlabs, nano-banana, monk, anicca, postiz, automation, shalev, yangmun
  requires:
    bins: [ffmpeg, ffprobe, curl, jq, python3, magick, oathtool]
    env: [ELEVENLABS_API_KEY, POSTIZ_API_KEY, GOOGLE_LOGIN_EMAIL]
---

# Anicca Monk Factory v3 — Ajahn Sutta

Faithful copy of the Shalev / Yang Mun system, as **Ajahn Sutta** (Anicca's monk:
"the body and the mind are not two"). Reverse-engineered from 10 real @yangmun2
videos (whisper transcripts in `~/anicca-monk-factory/references/anicca.monk/yangmun/`).

## 🟢🟢 DAILY ORCHESTRATION — run this end-to-end (hardened for UNATTENDED cron 2026-05-23)
Any agent (Anicca/cron/Claude) runs these EXACT steps. All paths absolute. Mechanical = scripts;
judgment (write caption) = the running model itself (HARD RULE #6). **SKILL dir is the source of
scripts — NOT ~/anicca-monk-factory (that is only the renders/captions OUTPUT dir).**

```
SKILL=/Users/anicca/.openclaw/skills/anicca-monk-factory-v3      # scripts + bank live HERE
OUT=/Users/anicca/anicca-monk-factory/renders_v3                 # mp4/caption OUTPUT dir
export GOG_KEYRING_PASSWORD=<password>

[0] LOGIN GUARD  bash $SKILL/scripts/ensure-heygen-login.sh        # autonomous HeyGen login (magic-link+gog)
       → must print HEYGEN_ALREADY_LOGGED_IN or HEYGEN_LOGIN_OK before continuing.
[1] PICK SCRIPT  J=$(bash $SKILL/scripts/pick-next-script.sh next) # rotation: next UNUSED from bank (cycles)
       ID=$(echo "$J"|jq -r .id) ; SCRIPT=$(echo "$J"|jq -r .script)   # NEVER write a new script — rotate the bank.
[2] RENDER       camofox HeyGen Video Agent (see "REPEATABLE FACTORY"): avatar=Wise Elder of Tranquility
       (verify composer img src contains ee4d1127) + attach /Users/anicca/Downloads/avatar.mp4 + STRICT
       english instruction (no translate / talking-head / 9:16) + the $SCRIPT + Submit.
       After Submit, CONFIRM the agent reply text says ENGLISH + talking-head (not Japanese/Tao) [#8],
       then capture the project URL (the current tab url, /video-agent/<id>) and run:
           bash $SKILL/scripts/render-download.sh "<project_url>" $OUT/$ID.mp4
       ⏳ render-download.sh polls up to 18 min and downloads the finished mp4. 🔴 IT READS THE <video>
       src VIA JS (/evaluate), because the finished mp4 download src is NOT in the a11y/text snapshot —
       polling the text snapshot loops forever (that was the unattended bug 2026-05-23). Do NOT hand-poll
       the snapshot; just call render-download.sh and wait for DOWNLOAD_OK (or RENDER_TIMEOUT → report honestly).
[3] CAPTIONS     bash $SKILL/scripts/burn-captions.sh $OUT/$ID.mp4 $OUT/${ID}_captioned.mp4
[4] WRITE CAPTION model writes a UNIQUE caption (Yang Mun voice: hook + "comment STILL" + 8-10 hashtags,
       NEVER reuse) → $OUT/${ID}_tiktok.txt and $OUT/${ID}_ig.txt. Run humanizer first.
[5a] POST TIKTOK bash $SKILL/scripts/post-tiktok.sh $OUT/${ID}_captioned.mp4 $OUT/${ID}_tiktok.txt  # {{profile.lateness.stakeholders.channel}}, verify gate
[5b] POST IG     bash $SKILL/scripts/post-ig-postiz.sh $OUT/${ID}_captioned.mp4 $OUT/${ID}_ig.txt   # Postiz (interim)
[6] MARK USED    bash $SKILL/scripts/pick-next-script.sh mark $ID    # ONLY after a successful post
[7] SLACK REPORT bash $SKILL/scripts/report-slack.sh "Monk Factory $ID: TikTok=<url|state> IG=<releaseURL|state>. <honest result>"
       ★ MANDATORY every run (success OR failure). This is how Dais knows it ran. If render/post failed,
         still report the honest blocker to Slack #metrics.
```

**Routing (canonical):** TikTok=@anicca_cemetery {{profile.lateness.stakeholders.channel}}-manual (post-tiktok.sh, creds .env MONK_TIKTOK_EN_*).
IG=@monk.anicca via Postiz integration cmoopzaak04yop70y1yx1bwr1 (post-ig-postiz.sh) — interim until IG
account cools, then real-Chrome cookie → {{profile.lateness.stakeholders.channel}}-manual (#17). 2FA: TikTok→Gmail(gog), IG-{{profile.lateness.stakeholders.channel}}(later)→
WhatsApp(whatsapp-cli store ~/.openclaw/tools/whatsapp-cli-store). DO NOT touch HeyGen My Voices — voice is
baked into the avatar. ROTATE the bank (pick-next-script.sh) — never invent new scripts.

## The 5 LOCKED layers (never change without human re-bless)
| layer | locked value |
|---|---|
| CHARACTER | Ajahn Sutta — `01-character/biography_en.md` |
| VOICE EN | ElevenLabs `Anicca Monk EN` voice_id `hjMjWnCImm501JEVJorD` |
| VOICE JP | ElevenLabs `Anicca Monk JP` voice_id `8cjRZwLoPS7Sl0oRIZWL` |
| FACE | `/Users/anicca/Desktop/monk-compare/v3-regen-20260521/option_a.jpeg` (EN+JP共通) |
| SCRIPT | `04-script/bank_en.jsonl` (30 scripts, 2 tracks) + `04-script/formulas.md` (SSOT) |

## Script doctrine (copied from real Yang Mun, see `references/yangmun-analysis.md`)
- 75–120s (~90s). Structure: number/curiosity HOOK → retention bait → authority
  ("I am Ajahn Sutta, fifty years...") → numbered body, each wrapped in poetic nature
  mechanism → ONE specific NAMED answer (never abstract) → comment-KEYWORD + share.
- Two tracks alternate: **T1 body/wellness** (sleep, breath, energy) and
  **T2 suffering/mind** (letting go, overthinking, peace). Both end with a concrete answer.
- ebook/app CTA only ~1 in 5 (default cta = engage: comment+share+follow).
- Outbound text passes `humanizer` (EN) / `humanizer-ja` (JP).

## Render pipeline (per video)
```
1. pick next unused script from bank_en.jsonl (alternate T1/T2)
2. ElevenLabs TTS → mp3 (voice_id above, settings stability0.45/style0.3/speed0.9)
   → ~/anicca-monk-factory/renders_v3/<ID>_anicca_monk_en.mp3
3. HeyGen UI ({{profile.lateness.stakeholders.channel}}, camofox :9377) — see "HeyGen login" + "HeyGen render" below
4. download mp4 → VERIFY with eyes (ffmpeg frames + audio + 9:16) [HARD RULE #8]
5. burn captions if needed
6. Postiz → TikTok (EN integration) + IG. Record HONEST terminal state (draft≠live).
```

## HeyGen login ({{profile.lateness.stakeholders.channel}} — NO API, Dais rule)
**Use {{profile.lateness.stakeholders.channel}}+password, NOT Google (Google OAuth opens a popup camofox can't drive).**
```
camofox up: bash ~/.openclaw/skills/camofox-{{profile.lateness.stakeholders.channel}}/scripts/start.sh
open https://app.heygen.com/login  (redirects to auth.heygen.com/login)
click "Use {{profile.lateness.stakeholders.channel}}" → type GOOGLE_LOGIN_EMAIL ({{profile.contact.personalEmail}})
click "Use password" → type password (Dukkha2026!) → click "Log in"
→ TOTP 2FA: enter 6-digit code.
   If HEYGEN_TOTP_SEED in env: code=$(oathtool --totp -b "$HEYGEN_TOTP_SEED")  [autonomous]
   else: ask Dais for the 6-digit code (one-time per session).
Cookie persists in ~/.camofox/profiles/anicca/default after success.
```

## 🟢 REPEATABLE FACTORY (CONFIRMED working 2026-05-23) — same avatar+voice, new script daily

The whole point: **same face (avatar.mp4), same voice (Anicca Monk EN), DIFFERENT script
every day** (or 30 at once per month). Anyone who loads this skill runs the loop below.

### Locked reusable assets (never change)
- AVATAR (HeyGen My Avatars): group `anicca_en_monk_v1` → look **"Wise Elder of Tranquility"**
  (LEFTMOST of 3 looks). Verify by composer avatar img src containing `ee4d1127d3cb44479a8e917a5aa08553`
  (other looks: `5a52533987…`=Saffron Seer, `77364c20…`=Serene Monk).
- AVATAR.MP4: `/Users/anicca/Downloads/avatar.mp4` (1080x1920, 91s). **The voice (Anicca Monk EN)
  is BAKED INTO the avatar + this mp4.** Dais rule (忘れたら殺す): DO NOT touch HeyGen "My Voices"
  — the custom Voice-Design "Anicca Monk EN" does NOT sync into HeyGen (My Voices = ElevenLabs
  premade only). The avatar carries the voice; attach avatar.mp4 + instruct "use the mp4's voice".
- SCRIPTS: `04-script/bank_en.jsonl` (30, rotate one per video; refill via formulas.md).

### Daily render loop (HeyGen Video Agent via camofox — CONFIRMED 2026-05-23)
```
0. source ~/.openclaw/skills/camofox-{{profile.lateness.stakeholders.channel}}/scripts/cf.sh ; TAB=$(cf_open_tab "https://app.heygen.com/video-agent")
   (camofox :9377 stays logged into HeyGen across restarts via disk cache.)
1. pick next unused script from bank_en.jsonl (alternate T1/T2)
2. SET AVATAR = Wise Elder of Tranquility:
   /click .glass-pill:has-text("Avatar") → cf_click e5 (My Avatars tab)
   → /click div.tw-text-xs:text-is("Browse 3 looks")  (expand anicca_en_monk_v1)
   → /click img[alt="Wise Elder of Tranquility"] then :nth-match(button:has-text("Use Avatar"),1)
   → VERIFY composer avatar img src contains ee4d1127 (#8). DO NOT touch the Voice chip.
3. ATTACH avatar.mp4: POST /tabs/$TAB/upload {files:["/Users/anicca/Downloads/avatar.mp4"],
   selector:"input[type=file]"}  → "avatar.mp4 Video" chip appears (attach ONCE — no dup).
4. TYPE strict instruction into [placeholder*="Describe"] textbox:
   "STRICT: use selected avatar (anicca_en_monk_v1 Wise Elder) + voice from attached avatar.mp4,
    do NOT change avatar/voice. ENGLISH content — speak the script word-for-word, DO NOT translate
    to Japanese, no rewrite. ONE talking-head portrait 9:16 for TikTok, no B-roll/scene/narrator swap.
    Script to speak verbatim in English: <bank script>"
5. /click button:has-text("Submit") → lands /video-agent/<id>. Agent generates a Video Plan then
   auto-builds. CONFIRM the agent reply says ENGLISH + talking-head (not Japanese/Tao) — #8 gate.
6. poll the project until the video appears under "Videos" tab; download mp4
   → ~/anicca-monk-factory/renders_v3/<scriptID>.mp4
7. VERIFY (#8): ffmpeg frames + 9:16 + audio = our voice + the right monk face + ENGLISH
8. POST: TikTok = DRAFT (native), Instagram = DIRECT with caption (Postiz)
```

### Tooling that WORKS vs FAILS (hard-won, 2026-05-22/23)
- ✅ **camofox (:9377) is the tool** — logged into HeyGen, login persists across restart (disk cache).
- ✅ camofox `/click` = Playwright real mouse (boundingBox center) → reliable on HeyGen React chips
  (the old "JS .click() unreliable" note was a stale build). React chips have no a11y ref →
  `/evaluate` to find element + assign `el.id` + `/click selector="#id"`.
- ✅ camofox `/tabs/:tabId/upload` (setInputFiles) — ADDED to ~/work/camofox-{{profile.lateness.stakeholders.channel}}/server.js
  (commit). Targets input[type=file]; attaches avatar.mp4.
- 🔴 CDP to Dais's real Chrome (port 9223) = BANNED (not skillifiable, Dais).
- 🔴 HeyGen "My Voices" never has our custom Voice-Design voice (HeyGen-side filter). Voice lives in the avatar.
- 🔴 Video Agent auto-pilot translates to JP + swaps avatar to "Tao" + B-roll BY DEFAULT
  (failed project 75cf27b3). The strict step-4 instruction PREVENTS this (confirmed: project 921d17ba
  → "speaking your exact English script… portrait talking-head throughout", no translation).
- File access: NOT a sandbox — local Mac Mini. Direct full paths read fine (ls/ffprobe/Read);
  only `ls`/`find` directory LISTING on Desktop/Downloads hits TCC. Use exact paths or `mdfind`.

## HeyGen render (earlier photo-to-video flow — reference)
### (CONFIRMED working flow, authed via magic link 2026-05-22)
```
1. authed /home → click tile "Make an avatar video from a photo" → lands /avatar
   ("Quick create", Photo-to-video panel: left=Script box, right=photo preview, tabs Script/Photo-to-video).
2. Upload locked face: POST /tabs/:id/upload
   {userId, selector:'input[type="file"][accept^="image/png"]', files:[option_a.jpeg]}
   → monk photo appears in the right preview (blobImgs:1). ✅
3. Use OUR locked ElevenLabs voice: click "Voice" → "Import from 3rd party"
   → field "Paste your API key here" → set value = $ELEVENLABS_API_KEY → click "Confirm". ✅
   (one-time; ElevenLabs connection saved to the HeyGen account)
   Then pick voice "Anicca Monk EN" from the imported ElevenLabs list.
4. Paste the script (from bank_en.jsonl) into the Script box.
5. Set aspect ratio 9:16. Click "Generate". Wait for render. Download mp4.
NOTE: clicking "Confirm" on the import returned to the /avatar dashboard — re-open
"Make an avatar video from a photo", re-confirm photo is set, select the imported voice, paste script, generate.
```

## Filesystem
```
01-character/  biography_en.md
02-voice/      voice_lock_en.json voice_lock_jp.json (ids above)
03-face/       (locked master = Desktop/monk-compare/v3-regen-20260521/option_a.jpeg)
04-script/     formulas.md  deep_pain_inventory_en.json  content_angles_en.json  bank_en.jsonl  sample_*.md
05-engine/     (step scripts — to build once render UI flow is confirmed)
references/    yangmun-analysis.md  heygen-ui-notes.md
runtime: ~/anicca-monk-factory/renders_v3/  (audio + mp4 outputs — REAL folder, never /tmp)
```

## Status (2026-05-22)
DONE: character, voice EN+JP, face, 30 scripts, 3 audio (A02/A11/A16), HeyGen {{profile.lateness.stakeholders.channel}}+password verified to 2FA.
BLOCKED: HeyGen TOTP 6-digit (need Dais code or HEYGEN_TOTP_SEED). After that: upload→avatar→render→verify→post.
Old skills yangmun-monk-factory / watercolor-monk-factory stay until v3 is live, then replace (see spec §17).
