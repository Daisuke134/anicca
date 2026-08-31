"use strict";
// MEN-b — the words the MENTAL organ sends.
//
// Spec 9.11 is strict about the shape: the user's inbox is never dirtied with questions, so every line
// is a statement, and at most one emoji is allowed. The aniccaios affirmation assets are the seed of the
// stance, not the text — an English affirmation is never pasted into Japanese copy. What varies is the
// moment: the line sent before a meeting must not read like the line sent before sleep.

const TRIGGERS = Object.freeze(["pre_event", "between_events", "pre_sleep"]);
// One line per trigger per seed. Asking for more samples than that would mean inventing variety the
// seeds cannot actually carry.
const SEED_LIMIT = TRIGGERS.length;
const MAX_LENGTH = 120;

// A question mark in any script, or a phrase that asks for something back.
const QUESTION_MARK = /[?？]/;
const ASKS_FOR_A_REPLY = /(返信|返事|教えて|聞かせて|答えて|どう思う|reply|let me know|tell me)/i;
const EMOJI = /\p{Extended_Pictographic}/gu;

// Stances distilled from the affirmation assets. Each is a posture toward the moment, not a slogan.
const STANCES = Object.freeze([
  { enough: "いまのままで足りてる", release: "抱えなくていいものは置いていける" },
  { enough: "やることはもう手の中にある", release: "コントロールできないものは手放していい" },
  { enough: "準備は静かに済んでる", release: "焦りは事実じゃない" },
  { enough: "十分に積み上げてきた", release: "全部を背負う必要はない" },
  { enough: "できることはやってある", release: "今日の分はもう終わってる" },
  { enough: "土台はもうできてる", release: "急ぐ理由はどこにもない" },
  { enough: "手は動いてきた", release: "評価は他人の仕事だ" },
  { enough: "必要なものは持ってきてる", release: "残りは明日でいい" },
  { enough: "ここまで来ている", release: "うまくやらなくても構わない" },
  { enough: "そのままで通用する", release: "力を抜いていい場面だ" },
]);

function stanceFor(seed) {
  // FNV-1a keeps near-identical seeds from landing on the same stance.
  let hash = 0x811c9dc5;
  for (const character of String(seed)) {
    hash ^= character.codePointAt(0);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return STANCES[hash % STANCES.length];
}

function validateMentalMessage(text) {
  const value = String(text == null ? "" : text).trim();
  if (!value) return { ok: false, reason: "empty" };
  if (value.length > MAX_LENGTH) return { ok: false, reason: "too_long" };
  if (QUESTION_MARK.test(value) || ASKS_FOR_A_REPLY.test(value)) {
    return { ok: false, reason: "not_one_directional" };
  }
  if ((value.match(EMOJI) || []).length > 1) return { ok: false, reason: "too_many_emoji" };
  return { ok: true };
}

function buildMentalMessage({ trigger, seed } = {}) {
  if (!TRIGGERS.includes(trigger)) throw new Error(`unknown mental trigger ${String(trigger)}`);
  if (!String(seed || "").trim()) throw new Error("a seed affirmation is required");
  const stance = stanceFor(seed);
  if (trigger === "pre_event") return `${stance.enough}。あとは話すだけ`;
  if (trigger === "between_events") return `${stance.release}。次まで少し息を置いていい`;
  return `🌙 今日はここまでで充分だ。${stance.release}`;
}

function buildSamples(seeds, count) {
  const list = (Array.isArray(seeds) ? seeds : []).filter((seed) => String(seed || "").trim());
  if (count > SEED_LIMIT * list.length) {
    throw new Error(`cannot build ${count} samples from ${list.length} seeds`);
  }
  const samples = [];
  for (const trigger of TRIGGERS) {
    for (const seed of list) {
      if (samples.length >= count) return samples;
      samples.push({ trigger, seed, text: buildMentalMessage({ trigger, seed }) });
    }
  }
  return samples;
}

module.exports = { TRIGGERS, SEED_LIMIT, MAX_LENGTH, validateMentalMessage, buildMentalMessage, buildSamples };
