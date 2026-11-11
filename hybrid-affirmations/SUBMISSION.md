# Devpost submission — Anicca Hybrid Affirmations

Hackathon: [#BuildHybridAI 2026](https://firebasehybridaihackathon.devpost.com/)
Platform to select: **Web (Chrome)**
Closes: 2026-11-30 14:00 PT
Repository: https://github.com/Daisuke134/life-manager
Entry path: `hybrid-affirmations/`
License: MIT (repository root `LICENSE`)

The official `/rules` page still said the full legal rules were not posted when this text was written on 2026-11-11. The requirements below follow the hackathon overview that was live the same day: Firebase AI Logic hybrid inference for every model call, Web/Chrome with Gemini Nano, App Check (debug tokens accepted), a public open-source repo, an English description, and a public YouTube demo of three minutes or less.

Suggested project name: **Anicca Hybrid Affirmations**

Suggested tagline: **A daily affirmation that runs on your laptop when it can, and in the cloud when it cannot.**

---

## Inspiration

Affirmation apps ask people to read the same stock lines every morning. The lines are generic, the apps want an account, and the "personal" ones send your mood to a server you never see.

Anicca already existed as a small affirmation practice: one feeling, a few honest sentences, nothing clinical. The hybrid SDK made a version of that practice that can tell the truth about where the words were written. On a Chrome desktop that has Gemini Nano, the sentence can be generated on the device. On a machine that does not, the same button still works, through the cloud model, and the screen says which one happened.

The feeling we kept returning to was privacy at the moment someone is already tender. Anxiety, heartbreak, and self-doubt are bad moments to be vague about where a note went.

## What it does

Anicca Hybrid Affirmations is a static Chrome web app.

- You pick a struggle: anxiety, self-doubt, procrastination, heartbreak, overwhelm, or starting over.
- You can add a first name and a short note about what is actually going on.
- You press one button and get a short, warm, first-person affirmation.
- A badge on that line says **On-device** or **Cloud**, using the inference source Firebase AI Logic returns for that response. It does not guess.
- You can keep a line. Favourites stay in the browser.
- Coming back on consecutive days builds a streak. Miss a day and it starts again at one.
- The line for a feeling is cached for that local day, so a refresh does not spend another request. "Write another" asks again on purpose.
- If Firebase is not configured, the same screen runs as an offline demo with clearly labeled samples. Those samples are never badged as model output.

The app is free to run. Text inference stays inside the Firebase AI Logic free tier. There is no second model provider.

## How we built it with Firebase AI Logic hybrid

The client is Vite and plain JavaScript in `hybrid-affirmations/`. The only inference module is `src/hybrid.js`.

We followed the web hybrid guide and then checked the names against Firebase JS SDK 13.2.0, because the guide's prose and the package's string values are not identical. The SDK exports `InferenceMode.PREFER_ON_DEVICE` as `"prefer_on_device"` and reports `response.inferenceSource` as `"on_device"` or `"in_cloud"`.

The call path is:

1. Initialize the Firebase web app from an injected config.
2. Initialize App Check before any AI call. Localhost uses `self.FIREBASE_APPCHECK_DEBUG_TOKEN` (`true`, or a token already registered in the console). A production host can use a reCAPTCHA v3 site key via `ReCaptchaV3Provider`. Debug tokens are not committed.
3. `getAI(app, { backend: new GoogleAIBackend() })` selects the Gemini Developer API.
4. `getGenerativeModel` is created with `mode: InferenceMode.PREFER_ON_DEVICE`, cloud model `gemini-3.5-flash-lite`, and an on-device system prompt in `onDeviceParams`.
5. The click handler calls `initializeDeviceModel` (Chrome requires a user gesture before the on-device download) and then `generateContent`. This is single-turn text. Hybrid on-device inference does not support multi-turn chat, so the app does not use chat.
6. The badge renders `inferenceSource`.

`PREFER_ON_DEVICE` is the hybrid behavior the prize is about: Nano when Chrome has it, cloud otherwise, one code path. A checkbox can wait for the on-device download so a demo can show the badge change from Cloud to On-device after Gemini Nano finishes installing. If the download is still running, the SDK answers from the cloud and the badge says so.

We did not call `generativelanguage.googleapis.com`, the Chrome Prompt API, or any other model SDK ourselves. The Firebase SDK is the only caller.

## Challenges

- **The badge has to be the SDK's answer.** It was tempting to label a response "on-device" because we asked for that mode. The SDK will use the cloud if Nano is missing or still downloading. The UI copies `inferenceSource` and explains the fallback in a sentence.
- **The first request is a race with a download.** Official behavior for `PREFER_ON_DEVICE` is that `generateContent` does not wait for `initializeDeviceModel`. Waiting by default would freeze the first session for several minutes. We start the download on the click, return the cloud line if Nano is not ready, and let the person opt in to waiting.
- **App Check is mandatory and easy to get half-wrong.** AI Logic enforces it. The debug token has to be set before `initializeAppCheck`, and a registered token is a credential, so the repo only has a placeholder. Without a Firebase project we cannot complete a live round trip here.
- **On-device inference is a narrow API.** No chat, no tools, English text in and out, Chrome desktop 139+ with a flag. The product is shaped to fit that box: one sentence, one turn, one badge.
- **The docs and the package disagree on the spelling of the source.** The guide says the property is `ON_DEVICE` or `IN_CLOUD`. The 13.2.0 enum values are `on_device` and `in_cloud`. We coded to the package.

## What's next

- Attach a Firebase project, register an App Check debug token, and record the badge on a Chrome profile that has Gemini Nano and on one that does not.
- Host `dist/` on the Firebase Hosting free tier.
- Add the Android (Gemini Nano) and iOS (Apple Foundation Models) clients through the same Firebase AI Logic hybrid SDK. The hackathon gives stronger grand-prize consideration to apps that run on more than one platform. This submission is the Web/Chrome client.
- Replace the debug provider with reCAPTCHA v3 before a public launch.
- Keep the voice, and keep refusing a second model vendor.

## Demo video script

Target length: about 2 minutes 20 seconds. Under 3 minutes. English voice-over. Record the real app in Chrome, not a mock. Upload the unlisted or public video to YouTube and paste that URL into Devpost. This script is not a substitute for the video.

**0:00–0:18 — The problem**
On camera, say: "Most affirmation apps send your worst morning to a server and hand you a generic line. This one tells you where the sentence was written."
Show the Anicca screen with no line yet, and the six feelings.

**0:18–0:45 — A line, and the badge**
Select Heartbreak. Type a first name. Leave the note empty for this take, or type one short clause you are willing to have in a public video.
Click "Write today's words."
Point at the badge. Read it out loud: "Cloud" or "On-device," whichever the SDK returned.
Read the caption under the quote, which repeats that source in a sentence.

**0:45–1:15 — Why the source changes**
Say: "The mode is prefer on-device. Firebase AI Logic uses Gemini Nano in Chrome when the model is already here. If it is still downloading, or this Chrome cannot run it, the same call falls back to gemini-3.5-flash-lite and the badge says Cloud."
If Nano is still downloading, check "Wait for Gemini Nano before writing," click "Write another," and show the progress text. If the second badge says On-device, pause on it. If it stays Cloud, say that this machine had no on-device model and the fallback is the feature, not a failure.

**1:15–1:40 — Favourites and the streak**
Click "Keep this close." Show the line under "Kept close" with the same source label.
Reload the page. Show that the line, the favourite, and the streak are still there.
Say: "That state never leaves the browser."

**1:40–2:05 — App Check, in one sentence**
Open the console only if a debug token is printing, and do not leave a real token readable in the final cut. Say: "Cloud calls are protected by Firebase App Check. A debug token is enough for the hackathon. The model call is Firebase AI Logic, not a separate API."

**2:05–2:20 — Close**
Say: "One button. On-device when Chrome can do it. Cloud when it cannot. You can see which one you got."
End on the badge.

Shot list if you need stills as well:

1. Feeling picker and the hybrid banner.
2. A finished line with the On-device badge, or the Cloud badge if that is what the machine returned.
3. Kept close, with the source still visible.
4. The streak after reload.

## Submission checklist

- [x] Public GitHub repo with an MIT license at the repository root
- [x] Source imports and calls Firebase AI Logic (`src/hybrid.js`)
- [x] Web / Chrome client
- [x] App Check is initialized; debug tokens are supported and not committed
- [x] English description (this file)
- [ ] Public YouTube demo, 3 minutes or less, English audio or captions
- [ ] Hosted URL (needs a Firebase project; Spark Hosting is enough)
- [ ] Devpost form submitted before 2026-11-30 14:00 PT

Built with: Firebase AI Logic, Firebase App Check, Chrome, Vite.
