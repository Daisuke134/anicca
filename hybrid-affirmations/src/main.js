import "./styles.css";
import {
  MOODS,
  affirmationId,
  applyStreak,
  buildPrompt,
  demoAffirmation,
  describeInferenceSource,
  isLiveConfig,
  loadState,
  localIsoDate,
  missingLiveConfig,
  moodById,
  publicError,
  readDaily,
  resolveConfig,
  saveState,
  toggleFavourite,
  writeDaily,
} from "./logic.mjs";

const $ = (id) => document.getElementById(id);

const storage = window.localStorage;
let state = loadState(storage);
let today = localIsoDate();
let busy = false;
let lastError = "";
let deviceNote = "";
let demoOffset = 0;

const config = resolveConfig(window.__HYBRID_AFFIRMATIONS_CONFIG__ || {}, {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  appCheckSiteKey: import.meta.env.VITE_APPCHECK_SITE_KEY,
  appCheckDebugToken: import.meta.env.VITE_APPCHECK_DEBUG_TOKEN,
});
const live = isLiveConfig(config);
const missing = missingLiveConfig(config);

function persist() {
  saveState(storage, state);
}

function currentEntry() {
  return readDaily(state, today, state.mood);
}

function renderMoods() {
  const root = $("moods");
  root.replaceChildren();
  for (const mood of MOODS) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = mood.label;
    button.setAttribute("aria-pressed", String(mood.id === state.mood));
    button.title = mood.blurb;
    button.addEventListener("click", () => {
      state.mood = mood.id;
      persist();
      render();
    });
    root.appendChild(button);
  }
}

function renderCard() {
  const entry = currentEntry();
  $("card").hidden = !entry;
  $("write").hidden = Boolean(entry);
  $("another").hidden = !entry;
  if (!entry) return;
  const source = describeInferenceSource(entry.inferenceSource);
  const badge = $("badge");
  badge.dataset.source = source.id;
  badge.textContent = source.label;
  badge.title = source.detail;
  $("quote").textContent = entry.text;
  const who = state.name.trim() ? `for ${state.name.trim()}` : "for you";
  $("caption").textContent = `${moodById(state.mood).label} · ${who}. ${source.detail}`;
  const saved = state.favourites.some((item) => item.id === affirmationId(entry.text, state.mood));
  const save = $("save");
  save.setAttribute("aria-pressed", String(saved));
  save.textContent = saved ? "Kept close" : "Keep this close";
}

function renderFavourites() {
  const list = $("favourites");
  list.replaceChildren();
  $("empty-favourites").hidden = state.favourites.length > 0;
  for (const item of state.favourites) {
    const li = document.createElement("li");
    const copy = document.createElement("div");
    const text = document.createElement("p");
    text.textContent = item.text;
    const meta = document.createElement("p");
    meta.className = "meta";
    meta.textContent = `${moodById(item.mood).label} · ${describeInferenceSource(item.inferenceSource).label}`;
    copy.append(text, meta);
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
      state.favourites = state.favourites.filter((favourite) => favourite.id !== item.id);
      persist();
      render();
    });
    li.append(copy, remove);
    list.appendChild(li);
  }
}

function renderStatus() {
  const streak = $("streak");
  if (!state.streak) streak.textContent = "Start a streak";
  else if (state.lastCompleted === today) {
    streak.textContent = state.streak === 1 ? "1 day streak" : `${state.streak} day streak`;
  } else streak.textContent = `${state.streak} day streak · open one today`;

  $("privacy").textContent = live
    ? "A personal note is sent only when you ask for words. On-device, it stays in Chrome. If Gemini Nano is not ready, Firebase AI Logic sends that request to the cloud model."
    : "Offline demo. Notes stay in this browser and are not sent anywhere, because no model is configured.";

  $("wait-label").hidden = !live;
  const banner = $("banner");
  if (lastError) {
    banner.dataset.kind = "error";
    banner.textContent = lastError;
  } else if (deviceNote) {
    banner.dataset.kind = "live";
    banner.textContent = deviceNote;
  } else if (!live) {
    banner.dataset.kind = "demo";
    banner.textContent = `Offline demo. Live hybrid inference still needs: ${missing.map((item) => item.label).join("; ")}.`;
  } else {
    banner.dataset.kind = "live";
    banner.textContent =
      "Hybrid inference is on. Mode: prefer on-device, with an automatic cloud fallback. Each line is labeled with the source Firebase AI Logic reports.";
  }

  $("tech").textContent = live
    ? "Firebase AI Logic · InferenceMode.PREFER_ON_DEVICE · cloud model gemini-3.5-flash-lite · App Check is initialized before any model call."
    : "Offline demo · the Firebase AI Logic call lives in src/hybrid.js and runs once the config placeholders are replaced.";
}

function render() {
  $("name").value = state.name;
  renderMoods();
  renderCard();
  renderFavourites();
  renderStatus();
  if (!busy) $("progress").textContent = "";
}

async function writeAffirmation(another) {
  if (busy) return;
  state.name = $("name").value.slice(0, 40);
  persist();
  busy = true;
  lastError = "";
  deviceNote = "";
  $("write").disabled = true;
  $("another").disabled = true;
  $("progress").textContent = live ? "Asking Firebase AI Logic…" : "Choosing an offline sample…";
  try {
    let text;
    let inferenceSource;
    if (!live) {
      if (another) demoOffset += 1;
      text = demoAffirmation(state.mood, today, demoOffset);
      inferenceSource = "demo";
    } else {
      const { generateWithHybrid, getHybridModel } = await import("./hybrid.js");
      const model = await getHybridModel(config);
      const written = await generateWithHybrid(
        model,
        buildPrompt({ mood: state.mood, name: state.name, note: $("note").value }),
        {
          waitForDevice: $("wait-for-device").checked,
          onProgress(value) {
            const percent = Math.max(0, Math.min(100, Math.round(Number(value) * 100)));
            $("progress").textContent = `Preparing Gemini Nano… ${percent}%`;
          },
          onDeviceError(error) {
            deviceNote = `On-device preparation did not finish (${publicError(error, config)}). Firebase AI Logic can still answer from the cloud.`;
          },
        },
      );
      text = written.text;
      inferenceSource = written.inferenceSource;
    }
    state = writeDaily(state, today, state.mood, { text, inferenceSource });
    const streak = applyStreak(state, today);
    state.streak = streak.streak;
    state.lastCompleted = streak.lastCompleted;
    persist();
  } catch (error) {
    lastError = publicError(error, config);
  } finally {
    busy = false;
    $("write").disabled = false;
    $("another").disabled = false;
    render();
  }
}

$("name").addEventListener("change", () => {
  state.name = $("name").value.slice(0, 40);
  persist();
  renderCard();
});

$("write").addEventListener("click", () => writeAffirmation(false));
$("another").addEventListener("click", () => writeAffirmation(true));

$("save").addEventListener("click", () => {
  const entry = currentEntry();
  if (!entry) return;
  state.favourites = toggleFavourite(state.favourites, {
    id: affirmationId(entry.text, state.mood),
    text: entry.text,
    mood: state.mood,
    inferenceSource: entry.inferenceSource,
  });
  persist();
  render();
});

render();
