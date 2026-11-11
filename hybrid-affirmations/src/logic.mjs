export const STORAGE_KEY = "anicca-hybrid-affirmations-v1";

export const CLOUD_MODEL = "gemini-3.5-flash-lite";

export const SYSTEM_PROMPT = [
  "You write one short affirmation for the Anicca app.",
  "Voice: warm, specific, calm, first person, one or two sentences, under 40 words.",
  "No quotation marks, title, hashtags, emoji, medical advice, or preamble.",
  "Meet the feeling without diagnosing it and without toxic positivity.",
].join(" ");

export const MOODS = [
  { id: "anxiety", label: "Anxiety", blurb: "A tight chest and a loud mind." },
  { id: "self-doubt", label: "Self-doubt", blurb: "The voice that says you are not enough." },
  { id: "procrastination", label: "Procrastination", blurb: "The task that keeps waiting." },
  { id: "heartbreak", label: "Heartbreak", blurb: "Something tender that still hurts." },
  { id: "overwhelm", label: "Overwhelm", blurb: "Too many things, not enough room." },
  { id: "beginning", label: "Starting over", blurb: "A first step after a long pause." },
];

const DEMO_LINES = {
  anxiety: [
    "I can feel this rush and still choose one slower breath.",
    "My body is loud right now, and I can stay with it without believing every alarm.",
    "I do not have to solve the whole day. I only have to meet this minute.",
  ],
  "self-doubt": [
    "The doubt is speaking, and it is not the only voice I have.",
    "I can be unfinished and still be someone I trust.",
    "I do not need to become impressive before I am allowed to begin.",
  ],
  procrastination: [
    "Starting small still counts. I can open the task without finishing my whole life.",
    "Avoidance has been protecting me. I can thank it and take one honest step.",
    "I am allowed to do this imperfectly and still be in motion.",
  ],
  heartbreak: [
    "What I loved was real, and I do not have to rush the ache out of me.",
    "I can miss them and still keep a place that is only mine.",
    "Grief can sit beside me today. I do not have to host it perfectly.",
  ],
  overwhelm: [
    "Too much is here, so I will set down everything except the next true thing.",
    "I can close a few doors and still be a person who cares.",
    "My worth is not the length of the list I finish.",
  ],
  beginning: [
    "A quiet start is still a start. I can begin where I actually am.",
    "I do not owe anyone the old version of this story.",
    "Today can be small and still be the day I came back.",
  ],
};

const CORE_FIELDS = [
  ["apiKey", "Firebase Web apiKey"],
  ["authDomain", "Firebase authDomain"],
  ["projectId", "Firebase projectId"],
  ["appId", "Firebase appId"],
];

export function isPlaceholder(value) {
  if (value == null) return true;
  const text = String(value).trim();
  if (!text) return true;
  return /your_|placeholder|changeme|\bxxx+\b|\btodo\b/i.test(text);
}

export function normalizeDebugToken(value) {
  if (value === true || value === "true") return true;
  if (typeof value !== "string") return undefined;
  const text = value.trim();
  if (!text || text === "false" || isPlaceholder(text)) return undefined;
  return text;
}

export function resolveConfig(fileConfig = {}, envConfig = {}) {
  const merged = { ...fileConfig };
  for (const [key, value] of Object.entries(envConfig)) {
    if (value == null) continue;
    if (typeof value === "string" && value.trim() === "") continue;
    merged[key] = value;
  }
  return merged;
}

export function missingLiveConfig(config = {}) {
  const missing = [];
  for (const [key, label] of CORE_FIELDS) {
    if (isPlaceholder(config[key])) missing.push({ key, label });
  }
  const hasSiteKey = !isPlaceholder(config.appCheckSiteKey);
  const hasDebug = normalizeDebugToken(config.appCheckDebugToken) !== undefined;
  if (!hasSiteKey && !hasDebug) {
    missing.push({
      key: "appCheck",
      label:
        "App Check reCAPTCHA v3 site key (appCheckSiteKey), or appCheckDebugToken set to true or a console-registered debug token",
    });
  }
  return missing;
}

export function isLiveConfig(config) {
  return missingLiveConfig(config).length === 0;
}

export function localIsoDate(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function shiftIsoDate(iso, days) {
  const [year, month, day] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function emptyState() {
  return {
    streak: 0,
    lastCompleted: "",
    favourites: [],
    name: "",
    mood: "anxiety",
    daily: {},
  };
}

export function moodById(id) {
  return MOODS.find((mood) => mood.id === id) || MOODS[0];
}

export function applyStreak(state, today) {
  const streak = Number(state?.streak) || 0;
  const last = state?.lastCompleted || "";
  if (last === today) {
    return { streak: Math.max(streak, 1), lastCompleted: today };
  }
  const next = last === shiftIsoDate(today, -1) ? streak + 1 : 1;
  return { streak: next, lastCompleted: today };
}

export function affirmationId(text, mood) {
  const raw = `${mood}\n${String(text || "").trim().toLowerCase()}`;
  let hash = 0;
  for (let index = 0; index < raw.length; index += 1) {
    hash = (hash * 31 + raw.charCodeAt(index)) >>> 0;
  }
  return hash.toString(16);
}

export function toggleFavourite(list, entry) {
  const favourites = Array.isArray(list) ? list : [];
  if (favourites.some((item) => item.id === entry.id)) {
    return favourites.filter((item) => item.id !== entry.id);
  }
  return [entry, ...favourites].slice(0, 50);
}

export function dailyKey(date, mood) {
  return `${date}:${mood}`;
}

export function readDaily(state, date, mood) {
  const entry = state?.daily?.[dailyKey(date, mood)];
  if (!entry || typeof entry.text !== "string" || !entry.text.trim()) return null;
  return entry;
}

export function writeDaily(state, date, mood, entry) {
  const daily = pruneDaily(
    { ...(state?.daily || {}), [dailyKey(date, mood)]: entry },
    date,
  );
  return { ...state, daily };
}

export function pruneDaily(daily, today) {
  const earliest = shiftIsoDate(today, -13);
  return Object.fromEntries(
    Object.entries(daily || {}).filter(([key]) => key.slice(0, 10) >= earliest),
  );
}

export function buildPrompt({ mood, name, note }) {
  const feeling = moodById(mood).label;
  const who = String(name || "").trim();
  const context = String(note || "").trim().slice(0, 280);
  const nameLine = who
    ? `The person's name is ${who}. Use the name at most once.`
    : "Do not invent a name.";
  const noteLine = context
    ? `What they said, in their words: ${context}`
    : "They did not add a personal note.";
  return `${SYSTEM_PROMPT}\n\nFeeling: ${feeling}.\n${nameLine}\n${noteLine}\n\nWrite the affirmation now.`;
}

export function cleanAffirmation(raw) {
  let text = String(raw || "").replace(/\s+/g, " ").trim();
  text = text.replace(/^(affirmation|response|output)\s*:\s*/i, "");
  if (
    (text.startsWith('"') && text.endsWith('"')) ||
    (text.startsWith("“") && text.endsWith("”")) ||
    (text.startsWith("'") && text.endsWith("'"))
  ) {
    text = text.slice(1, -1).trim();
  }
  return text;
}

export function demoAffirmation(mood, dayKey, offset = 0) {
  const lines = DEMO_LINES[moodById(mood).id];
  let hash = 0;
  const seed = `${moodById(mood).id}:${dayKey}`;
  for (const char of seed) hash = (hash * 33 + char.charCodeAt(0)) >>> 0;
  const index = (hash + Number(offset || 0)) % lines.length;
  return lines[index];
}

export function describeInferenceSource(source) {
  const value = String(source || "").toLowerCase();
  if (value === "on_device" || value === "on-device") {
    return {
      id: "on-device",
      label: "On-device",
      detail: "Written by Gemini Nano on this Chrome device through Firebase AI Logic.",
    };
  }
  if (value === "in_cloud" || value === "in-cloud" || value === "cloud") {
    return {
      id: "cloud",
      label: "Cloud",
      detail: "Gemini Nano was not ready, so Firebase AI Logic used the cloud model.",
    };
  }
  if (value === "demo" || value === "offline-demo") {
    return {
      id: "demo",
      label: "Offline demo",
      detail: "A saved sample. No model was called.",
    };
  }
  return {
    id: "unknown",
    label: "Hybrid",
    detail: "Firebase AI Logic did not report an inference source for this line.",
  };
}

export function publicError(error, config = {}) {
  let message = String(error?.message || error || "Something went wrong while writing.");
  for (const value of [
    config.apiKey,
    config.appId,
    config.appCheckSiteKey,
    config.appCheckDebugToken,
  ]) {
    const secret = String(value || "");
    if (secret.length > 6 && secret !== "true" && secret !== "false") {
      message = message.split(secret).join("[redacted]");
    }
  }
  return message.slice(0, 400);
}

export function loadState(storage) {
  try {
    const parsed = JSON.parse(storage.getItem(STORAGE_KEY) || "");
    if (!parsed || typeof parsed !== "object") return emptyState();
    const mood = MOODS.some((item) => item.id === parsed.mood) ? parsed.mood : "anxiety";
    const favourites = Array.isArray(parsed.favourites)
      ? parsed.favourites.filter((item) => item && typeof item.text === "string" && item.id)
      : [];
    return {
      streak: Number(parsed.streak) || 0,
      lastCompleted: typeof parsed.lastCompleted === "string" ? parsed.lastCompleted : "",
      favourites,
      name: typeof parsed.name === "string" ? parsed.name.slice(0, 40) : "",
      mood,
      daily: parsed.daily && typeof parsed.daily === "object" ? parsed.daily : {},
    };
  } catch {
    return emptyState();
  }
}

export function saveState(storage, state) {
  storage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function createMemoryStorage(initial = {}) {
  const data = { ...initial };
  return {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : null;
    },
    setItem(key, value) {
      data[key] = String(value);
    },
  };
}
