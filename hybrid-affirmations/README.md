# Anicca Hybrid Affirmations

A Chrome web app for the [#BuildHybridAI 2026](https://firebasehybridaihackathon.devpost.com/) hackathon. You pick what feels heavy — anxiety, self-doubt, procrastination, heartbreak, overwhelm, or starting over — and Anicca writes one short, warm affirmation. You can keep lines you want to see again, and a daily streak records the days you came back.

This folder is the hackathon entry. The rest of the Life Manager repository is the existing project. The license for this app is the repository [MIT license](../LICENSE).

## What it does

- Lets you choose a feeling and, optionally, a name and a short personal note.
- Writes one first-person affirmation in a calm voice.
- Shows a visible badge for every line: **On-device**, **Cloud**, or **Offline demo**.
- Saves favourites in this browser.
- Keeps a daily streak in this browser. One completed day counts once. A missed day starts the streak over.

No account, no payment, and no other model API. Favourites and the streak never leave the browser.

## How hybrid inference is used

All model calls go through the Firebase AI Logic web SDK (`firebase` 13.2.0), checked against the installed type definitions and the official guide [Build hybrid experiences in Web apps](https://firebase.google.com/docs/ai-logic/hybrid/web/get-started) (page updated 2026-11-10).

`src/hybrid.js` does this, and only this, for inference:

1. `initializeApp` from `firebase/app`.
2. `initializeAppCheck` from `firebase/app-check`, after setting `self.FIREBASE_APPCHECK_DEBUG_TOKEN` when a debug token is configured. A real reCAPTCHA v3 site key uses `ReCaptchaV3Provider`. With no site key, a `CustomProvider` is passed only so App Check can initialize; debug mode exchanges the debug token and does not call that provider. This matches the [App Check debug provider](https://firebase.google.com/docs/app-check/web/debug-provider) guide.
3. `getAI(app, { backend: new GoogleAIBackend() })` from `firebase/ai` (Gemini Developer API, the no-cost provider recommended in the guide).
4. `getGenerativeModel` with `mode: InferenceMode.PREFER_ON_DEVICE`.
5. Cloud fallback model `gemini-3.5-flash-lite` via `inCloudParams` (the SDK default from JS SDK 13.0.0, set explicitly). `generationConfig` asks for at most 120 tokens.
6. On-device system prompt via `onDeviceParams.createOptions.initialPrompts`, with English text input and output. On-device inference is single-turn text, which is what this app needs. Chat, tools, and other unsupported features are not used.
7. On the button click (a user gesture, required by Chrome), `model.initializeDeviceModel(progress)` then `model.generateContent(prompt)`.
8. The badge reads `result.response.inferenceSource`. In SDK 13.2.0 the values are the strings `"on_device"` and `"in_cloud"` (`InferenceSource.ON_DEVICE` / `InferenceSource.IN_CLOUD`).

`PREFER_ON_DEVICE` uses Gemini Nano through Chrome's Prompt API when it is ready, and falls back to the cloud model when it is not. The official SDK behavior is: if `generateContent` runs before the on-device download finishes, this mode does **not** wait, and the answer comes from the cloud. The checkbox "Wait for Gemini Nano before writing" awaits `initializeDeviceModel` first so a demo can show the on-device badge after the download. The badge always reports the source the SDK returned for that response, not the mode we requested.

The app does not call the Gemini REST API, the Chrome `LanguageModel` API, or any other model provider.

## What was built during the hackathon window

The hackathon submission window opened on **2026-11-11**. Built in this folder during that window:

- This Chrome client and its calm reading screen.
- The Firebase AI Logic hybrid call, App Check initialization, and the on-device / cloud badge.
- Local favourites, the daily cache, and the streak.
- Offline demo mode so the UI runs before a Firebase project is attached.
- Tests, the production build smoke check, and `SUBMISSION.md`.

The Anicca affirmation product already existed as an iOS app and as design copy in this repository. Those earlier clients are not this entry. This web client, and every Firebase AI Logic call in it, is new work for #BuildHybridAI.

## Setup

Requirements: Node.js 22 or newer for the Vite build. The `firebase` 13.2.0 package declares `node >= 24.12.0` for its Node entry point. This app only uses the browser build, and `npm run smoke` has been run on Node 22. Chrome desktop 139 or newer is required for on-device inference.

```bash
cd hybrid-affirmations
npm install
npm test
npm run smoke
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`).

`npm test` runs the logic tests. `npm run smoke` runs those tests, builds the static site, and checks that the built JavaScript still contains the hybrid SDK markers (`prefer_on_device`, `initializeDeviceModel`, `inferenceSource`, `gemini-3.5-flash-lite`, `FIREBASE_APPCHECK_DEBUG_TOKEN`).

## Offline demo mode

The committed `public/firebase-config.js` contains placeholders. While any required value is still a placeholder, the app does not call Firebase. "Write today's words" shows a stable sample for that feeling and day, badged **Offline demo**. "Write another" rotates the sample. Favourites and the streak still work. Nothing in the demo is labeled on-device or cloud.

## Config for live hybrid inference

Two ways to inject config. Environment variables override the file when they are non-empty. Do not commit a real App Check debug token.

**File:** edit `public/firebase-config.js` (or replace that file in the hosted `dist/` output).

**Env:** copy `.env.example` to `.env.local` and fill in:

| Value | Where it comes from |
|---|---|
| `apiKey` | Firebase console → Project settings → Your apps → Web app |
| `authDomain` | same config object |
| `projectId` | same config object |
| `storageBucket` | same config object (optional for this app) |
| `messagingSenderId` | same config object (optional for this app) |
| `appId` | same config object |
| `appCheckSiteKey` | reCAPTCHA v3 site key registered for App Check |
| `appCheckDebugToken` | `true` on localhost, or a token you already registered. Never commit it. |

Live mode starts only when `apiKey`, `authDomain`, `projectId`, and `appId` are real **and** either a reCAPTCHA site key or a debug token is set. The in-app banner lists whatever is still missing.

### Firebase project checklist

1. Create a Firebase project (no Analytics and no billing required to start).
2. Add a Web app and copy the config.
3. AI Services → AI Logic → Get started. Choose the **Gemini Developer API**. The guided setup enforces App Check for AI Logic.
4. For localhost, set `appCheckDebugToken` to `true`, open the app, copy the debug token from the browser console, and register it under Security → App Check → Apps → Manage debug tokens. The hackathon accepts debug tokens.
5. For a public host, register a production App Check provider (reCAPTCHA v3). Do not ship a debug token.
6. Confirm Security → App Check → APIs shows Firebase AI Logic as enforced.

### Chrome, for the on-device badge

From the Firebase guide:

1. Chrome desktop 139 or newer (`chrome://settings/help`).
2. Enable `chrome://flags/#prompt-api-for-gemini-nano-multimodal-input` and restart.
3. The first on-device use downloads Gemini Nano. That download can take several minutes. Until it finishes, `PREFER_ON_DEVICE` answers from the cloud and the badge says **Cloud**.
4. Optional, in the Chrome console, before the first request: `await LanguageModel.availability()` then `await LanguageModel.create()`. That is Chrome setup, not a call this app makes.

## Hosting

The app is a static Vite site. `npm run build` writes `dist/`. No server and no paid Firebase product is required.

**Firebase Hosting (free Spark plan):**

```bash
npm run build
cp .firebaserc.example .firebaserc   # then set your project id
npx firebase-tools deploy --only hosting
```

`firebase.json` publishes `dist/`. `.firebaserc` is gitignored once you copy it; the example file ships with `YOUR_PROJECT_ID`.

**GitHub Pages:** publish the contents of `dist/`. `base` is `./`, so the built files work from a subpath as well as a domain root. Replace `dist/firebase-config.js` with the real config on the host, or rebuild with `.env.local`.

There is no Firebase project attached in this repository. See the list in the final handoff, and the banner inside the running app, for the exact missing values.

## Tests

```bash
npm test
npm run smoke
```

The tests cover streak rules, favourites, config detection, prompt shape, the on-device/cloud labels, and the presence of the verified SDK calls in `src/hybrid.js`. They do not call Google.
