# Devpost fields — Anicca Hybrid Affirmations

Hackathon: [#BuildHybridAI](https://firebasehybridaihackathon.devpost.com/)
Platform: Web (Chrome)
Submission target named for this entry: 2026-11-29 12:00 JST

## Title

Anicca Hybrid Affirmations

## Tagline

A short daily affirmation that asks Gemini Nano on this laptop first, and Firebase AI Logic in the cloud when Nano is not ready.

## What it does

Anicca Hybrid Affirmations is a static Chrome page in `hybrid-affirmations/`.

- Six feelings: anxiety, self-doubt, procrastination, heartbreak, overwhelm, starting over.
- Optional first name and a short note. The note stays in the browser until you press the button.
- One press returns one short first-person line.
- The badge copies `response.inferenceSource` from Firebase AI Logic: `on_device` shows **On-device**, `in_cloud` shows **Cloud**. The app does not label a line from the mode it requested.
- Favourites and the daily streak are stored in `localStorage` under `anicca-hybrid-affirmations-v1`.
- Today's line for a feeling is cached in the browser. "Write another" asks again on purpose.
- With the committed placeholder config, the same screen uses a fixed sample for that day and feeling and badges it **Offline demo**. Those samples are not model output.

## How Firebase AI Logic / Gemini Nano is used

The only inference module is `src/hybrid.js`. It imports `getAI`, `getGenerativeModel`, `GoogleAIBackend`, and `InferenceMode` from `firebase/ai` (Firebase JS SDK 13.2.0).

1. App Check is initialized before any AI call. A non-empty debug token is assigned to `self.FIREBASE_APPCHECK_DEBUG_TOKEN` before `initializeAppCheck`. A reCAPTCHA v3 site key uses `ReCaptchaV3Provider`. No debug token is committed.
2. `getAI(app, { backend: new GoogleAIBackend() })`.
3. `getGenerativeModel` uses `mode: InferenceMode.PREFER_ON_DEVICE` (`"prefer_on_device"`).
4. On-device options set English text in and English text out, plus the system prompt. The cloud model in `inCloudParams` is `gemini-3.5-flash-lite`, with `maxOutputTokens: 120` and `temperature: 0.9`.
5. The click calls `initializeDeviceModel`, then `generateContent`. This is one turn. The module does not start a chat.
6. `PREFER_ON_DEVICE` does not wait for the Gemini Nano download. If Nano is missing or still downloading, the SDK answers from the cloud and `inferenceSource` is `in_cloud`. A checkbox can wait for the download before `generateContent`.

The page does not call `generativelanguage.googleapis.com`, `api.openai.com`, or Chrome's `LanguageModel` itself. Chrome on-device use still needs desktop Chrome 139+ and `chrome://flags/#prompt-api-for-gemini-nano-multimodal-input`.

Live hybrid inference is not active in the published demo. The committed config is still the placeholders `YOUR_FIREBASE_API_KEY`, `YOUR_PROJECT_ID`, `YOUR_FIREBASE_APP_ID`, and `YOUR_RECAPTCHA_V3_SITE_KEY`, and `appCheckDebugToken` is empty. The running page lists those missing fields.

## Demo URL

https://daisuke134.github.io/anicca/hybrid-affirmations/

Checked on 2026-11-27: the HTML, CSS, JS, favicon, and placeholder `firebase-config.js` returned HTTP 200. A headless Chrome pass selected Anxiety, pressed "Write today's words", and showed the badge **OFFLINE DEMO** with the sample "I can feel this rush and still choose one slower breath." No page error. This host does not show an On-device or Cloud badge, because no Firebase project is configured.

## Video

Path: `hybrid-affirmations/demo/demo.mp4`

Public file (this branch): https://github.com/Daisuke134/anicca/blob/cursor/hybrid-affirmations-hackathon-2641/hybrid-affirmations/demo/demo.mp4

Measured with ffprobe: 12.96 seconds, 1280×720, no audio. It is a headless Chrome capture of the published flow's local twin: Heartbreak, the name Noa, **OFFLINE DEMO**, save, then "Write another". It does not show an On-device or Cloud badge.

YouTube was not uploaded. There is no YouTube credential in this environment, so Devpost's video field still needs a YouTube URL if the form requires one. The file above is the recording that exists.

## Repo URL

https://github.com/Daisuke134/anicca

Entry: https://github.com/Daisuke134/anicca/tree/cursor/hybrid-affirmations-hackathon-2641/hybrid-affirmations

Pull request: https://github.com/Daisuke134/life-manager/pull/9335

License: MIT (`LICENSE` at the repository root).
