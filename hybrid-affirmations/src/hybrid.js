import { getApp, initializeApp } from "firebase/app";
import {
  CustomProvider,
  ReCaptchaV3Provider,
  initializeAppCheck,
} from "firebase/app-check";
import {
  GoogleAIBackend,
  InferenceMode,
  getAI,
  getGenerativeModel,
} from "firebase/ai";
import {
  CLOUD_MODEL,
  SYSTEM_PROMPT,
  cleanAffirmation,
  isPlaceholder,
  normalizeDebugToken,
} from "./logic.mjs";

let modelPromise;
let appCheckReady = false;

export function resetHybridSession() {
  modelPromise = undefined;
}

function firebaseApp(config) {
  try {
    return getApp("hybrid-affirmations");
  } catch {
    return initializeApp(
      {
        apiKey: config.apiKey,
        authDomain: config.authDomain,
        projectId: config.projectId,
        storageBucket: config.storageBucket || undefined,
        messagingSenderId: config.messagingSenderId || undefined,
        appId: config.appId,
      },
      "hybrid-affirmations",
    );
  }
}

export function createHybridModel(config) {
  const debugToken = normalizeDebugToken(config.appCheckDebugToken);
  if (debugToken !== undefined) {
    self.FIREBASE_APPCHECK_DEBUG_TOKEN = debugToken;
  }

  const app = firebaseApp(config);

  const provider = isPlaceholder(config.appCheckSiteKey)
    ? new CustomProvider({
        getToken: async () => {
          throw new Error(
            "App Check needs a reCAPTCHA v3 site key when the debug token is off.",
          );
        },
      })
    : new ReCaptchaV3Provider(config.appCheckSiteKey);

  if (!appCheckReady) {
    initializeAppCheck(app, {
      provider,
      isTokenAutoRefreshEnabled: true,
    });
    appCheckReady = true;
  }

  const ai = getAI(app, { backend: new GoogleAIBackend() });
  return getGenerativeModel(ai, {
    mode: InferenceMode.PREFER_ON_DEVICE,
    inCloudParams: {
      model: CLOUD_MODEL,
      generationConfig: {
        maxOutputTokens: 120,
        temperature: 0.9,
      },
    },
    onDeviceParams: {
      createOptions: {
        expectedInputs: [{ type: "text", languages: ["en"] }],
        expectedOutputs: [{ type: "text", languages: ["en"] }],
        initialPrompts: [
          {
            role: "system",
            content: [{ type: "text", value: SYSTEM_PROMPT }],
          },
        ],
      },
    },
  });
}

export function getHybridModel(config) {
  if (!modelPromise) {
    modelPromise = Promise.resolve()
      .then(() => createHybridModel(config))
      .catch((error) => {
        modelPromise = undefined;
        throw error;
      });
  }
  return modelPromise;
}

export async function generateWithHybrid(model, prompt, options = {}) {
  let preparing = Promise.resolve();
  try {
    preparing = model.initializeDeviceModel((value) => {
      options.onProgress?.(value);
    });
  } catch (error) {
    options.onDeviceError?.(error);
  }
  if (!preparing || typeof preparing.then !== "function") preparing = Promise.resolve();
  if (options.waitForDevice) {
    try {
      await preparing;
    } catch (error) {
      options.onDeviceError?.(error);
    }
  } else {
    preparing.catch((error) => options.onDeviceError?.(error));
  }

  const result = await model.generateContent(prompt);
  const text = cleanAffirmation(result?.response?.text?.() || "");
  if (!text) throw new Error("The model returned an empty affirmation.");
  return {
    text,
    inferenceSource: result.response.inferenceSource,
  };
}
