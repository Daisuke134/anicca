import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  applyStreak,
  buildPrompt,
  cleanAffirmation,
  createMemoryStorage,
  demoAffirmation,
  describeInferenceSource,
  loadState,
  missingLiveConfig,
  publicError,
  resolveConfig,
  saveState,
  shiftIsoDate,
  toggleFavourite,
  writeDaily,
  readDaily,
} from "../src/logic.mjs";

describe("live config", () => {
  it("treats the committed placeholders as missing", () => {
    const missing = missingLiveConfig({
      apiKey: "YOUR_FIREBASE_API_KEY",
      authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
      projectId: "YOUR_PROJECT_ID",
      appId: "YOUR_FIREBASE_APP_ID",
      appCheckSiteKey: "YOUR_RECAPTCHA_V3_SITE_KEY",
      appCheckDebugToken: "",
    });
    assert.deepEqual(
      missing.map((item) => item.key),
      ["apiKey", "authDomain", "projectId", "appId", "appCheck"],
    );
  });

  it("accepts a debug token in place of a reCAPTCHA site key", () => {
    const missing = missingLiveConfig({
      apiKey: "AIzaSyExampleKeyValue123456",
      authDomain: "anicca-hybrid.firebaseapp.com",
      projectId: "anicca-hybrid",
      appId: "1:123:web:abc",
      appCheckSiteKey: "",
      appCheckDebugToken: "true",
    });
    assert.deepEqual(missing, []);
  });

  it("lets non-empty env values override the file", () => {
    const config = resolveConfig(
      { apiKey: "YOUR_FIREBASE_API_KEY", projectId: "YOUR_PROJECT_ID" },
      { apiKey: "real-key", projectId: "  " },
    );
    assert.equal(config.apiKey, "real-key");
    assert.equal(config.projectId, "YOUR_PROJECT_ID");
  });
});

describe("streak and favourites", () => {
  it("starts, continues, and resets a daily streak", () => {
    assert.deepEqual(applyStreak({ streak: 0, lastCompleted: "" }, "2026-11-11"), {
      streak: 1,
      lastCompleted: "2026-11-11",
    });
    assert.deepEqual(applyStreak({ streak: 1, lastCompleted: "2026-11-11" }, "2026-11-11"), {
      streak: 1,
      lastCompleted: "2026-11-11",
    });
    assert.deepEqual(applyStreak({ streak: 1, lastCompleted: "2026-11-11" }, "2026-11-12"), {
      streak: 2,
      lastCompleted: "2026-11-12",
    });
    assert.equal(shiftIsoDate("2026-11-11", -1), "2026-11-10");
    assert.deepEqual(applyStreak({ streak: 4, lastCompleted: "2026-11-10" }, "2026-11-12"), {
      streak: 1,
      lastCompleted: "2026-11-12",
    });
  });

  it("toggles a favourite by id and keeps the newest first", () => {
    const first = { id: "a", text: "One", mood: "anxiety" };
    const second = { id: "b", text: "Two", mood: "heartbreak" };
    const saved = toggleFavourite(toggleFavourite([], first), second);
    assert.deepEqual(saved.map((item) => item.id), ["b", "a"]);
    assert.deepEqual(toggleFavourite(saved, first).map((item) => item.id), ["b"]);
  });

  it("round-trips state and today's cached line", () => {
    const storage = createMemoryStorage();
    const today = "2026-11-11";
    let state = loadState(storage);
    state = { ...state, name: "Ada", mood: "heartbreak" };
    state = {
      ...state,
      ...applyStreak(state, today),
    };
    state = writeDaily(state, today, "heartbreak", {
      text: "I can miss them and still keep a place that is only mine.",
      inferenceSource: "on_device",
    });
    saveState(storage, state);
    const loaded = loadState(storage);
    assert.equal(loaded.name, "Ada");
    assert.equal(loaded.streak, 1);
    assert.equal(readDaily(loaded, today, "heartbreak").inferenceSource, "on_device");
  });
});

describe("affirmation text", () => {
  it("builds a prompt from the mood and keeps an empty note out", () => {
    const prompt = buildPrompt({
      mood: "procrastination",
      name: "  ",
      note: "",
    });
    assert.match(prompt, /Procrastination/);
    assert.match(prompt, /Do not invent a name/);
    assert.match(prompt, /did not add a personal note/);
    assert.doesNotMatch(prompt, /What they said/);
  });

  it("includes a trimmed personal note once", () => {
    const prompt = buildPrompt({
      mood: "anxiety",
      name: "Noa",
      note: "  the presentation tomorrow  ",
    });
    assert.match(prompt, /name is Noa/);
    assert.match(prompt, /the presentation tomorrow/);
  });

  it("cleans labels and wrapping quotes", () => {
    assert.equal(
      cleanAffirmation('Affirmation: "I can begin where I actually am."'),
      "I can begin where I actually am.",
    );
  });

  it("picks a stable offline sample per day and mood", () => {
    const first = demoAffirmation("anxiety", "2026-11-11", 0);
    assert.equal(demoAffirmation("anxiety", "2026-11-11", 0), first);
    assert.notEqual(demoAffirmation("anxiety", "2026-11-11", 1), first);
  });
});

describe("inference source", () => {
  it("labels the SDK values on_device and in_cloud", () => {
    assert.equal(describeInferenceSource("on_device").id, "on-device");
    assert.equal(describeInferenceSource("in_cloud").id, "cloud");
    assert.equal(describeInferenceSource("demo").label, "Offline demo");
    assert.match(describeInferenceSource("on_device").detail, /Gemini Nano/);
    assert.match(describeInferenceSource("in_cloud").detail, /cloud model/);
  });

  it("redacts config values from errors", () => {
    const message = publicError(new Error("request failed for AIzaSySecretValue123"), {
      apiKey: "AIzaSySecretValue123",
    });
    assert.equal(message.includes("AIzaSySecretValue123"), false);
    assert.match(message, /\[redacted\]/);
  });
});

describe("hybrid client source", () => {
  it("calls the Firebase AI Logic hybrid SDK by its verified names", () => {
    const source = readFileSync(
      fileURLToPath(new URL("../src/hybrid.js", import.meta.url)),
      "utf8",
    );
    for (const needle of [
      'from "firebase/ai"',
      'from "firebase/app-check"',
      "GoogleAIBackend",
      "InferenceMode.PREFER_ON_DEVICE",
      "getAI",
      "getGenerativeModel",
      "initializeDeviceModel",
      "generateContent",
      "inferenceSource",
      "FIREBASE_APPCHECK_DEBUG_TOKEN",
      "initializeAppCheck",
      "CLOUD_MODEL",
    ]) {
      assert.equal(source.includes(needle), true, needle);
    }
    assert.equal(source.includes("generativelanguage.googleapis.com"), false);
    assert.equal(source.includes("api.openai.com"), false);
    const logic = readFileSync(
      fileURLToPath(new URL("../src/logic.mjs", import.meta.url)),
      "utf8",
    );
    assert.match(logic, /gemini-3\.5-flash-lite/);
  });
});
