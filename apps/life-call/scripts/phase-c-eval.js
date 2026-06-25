"use strict";
// PHASE C / PC-2 — NO-MOCK eval of the location judgment (real Gemini, temperature 0) against the canonical
// cases. Verifies C1 filled / C2 online / C5 routines / C7 EN-JA, and C4 determinism (same kind over N runs).
// NOT in npm test (hits the real Gemini + Maps API). Run: GEMINI_API_KEY=… LIFE_MAPS_KEY=… node scripts/phase-c-eval.js
const { agentResolveLocation } = require("../lib/ask.js");

const GEMINI = process.env.GEMINI_API_KEY;
const MAPS = process.env.LIFE_MAPS_KEY || process.env.GOOGLE_API_KEY;
const HOME = process.env.EVAL_HOME || "東京都渋谷区"; // disambiguation context
const N = Number(process.env.EVAL_N || 5);

// case → expected kind. The judgment (agentResolveLocation) decides; this asserts it lands where the spec says.
const CASES = [
  // C1 FILLED — must web-search to a real address, never ask (REQ-01..04, C7 EN)
  { summary: "東京スカイツリーで打合せ", expect: "filled", tag: "C1/JA landmark" },
  { summary: "スタバ新宿南口店", expect: "filled", tag: "C1/JA shop" },
  { summary: "Meeting at Tokyo Skytree", expect: "filled", tag: "C1/EN landmark (C7)" },
  // C2 ONLINE — phone/video/online, even with a named person → no-travel, never ask (REQ-05/06)
  { summary: "藤井さんと電話オンライン", expect: "online", tag: "C2/JA phone" },
  { summary: "Zoom sync", expect: "online", tag: "C2/EN video" },
  { summary: "三島さんとオンラインミーティング", expect: "online", tag: "C2/JA online mtg w/ person" },
  // C5 ROUTINES — personal routine at/from home → no-travel, never "where is your run" (REQ-07)
  { summary: "Morning run", expect: "online", tag: "C5/EN routine" },
  { summary: "Sleep", expect: "online", tag: "C5 routine" },
  { summary: "瞑想", expect: "online", tag: "C5/JA meditation" },
  // C3 ASK — real meetup but no findable venue / user-only place → ask (REQ-08/09)
  { summary: "Lunch with Mai", expect: "ask", tag: "C3/EN vague person" },
  { summary: "おばあちゃんの家", expect: "ask", tag: "C3/JA user-only place" },
];

(async () => {
  if (!GEMINI || !MAPS) { console.log("missing GEMINI_API_KEY / LIFE_MAPS_KEY"); process.exit(2); }
  let pass = 0, fail = 0;
  const PASS_FRAC = 0.8; // the expected kind must be ≥80% of N runs (C4 determinism, temp 0 ⇒ usually 100%)
  for (const c of CASES) {
    const counts = {};
    for (let i = 0; i < N; i++) {
      let res;
      try {
        res = await agentResolveLocation(
          { summary: c.summary, location: "", start: { dateTime: "2026-07-01T10:00:00+09:00" } },
          { home: HOME, mapsKey: MAPS, geminiKey: GEMINI },
        );
      } catch (e) { res = { kind: `ERR:${e.message.slice(0, 30)}` }; }
      counts[res.kind] = (counts[res.kind] || 0) + 1;
    }
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
    const expectCount = counts[c.expect] || 0;
    const ok = top[0] === c.expect && expectCount >= Math.ceil(PASS_FRAC * N);
    ok ? pass++ : fail++;
    console.log(`${ok ? "PASS" : "FAIL"} [${c.tag}] "${c.summary}" → ${JSON.stringify(counts)} (expect ${c.expect}, determ ${((top[1] / N) * 100).toFixed(0)}%)`);
  }
  console.log(`\nPHASE C eval: ${pass}/${CASES.length} cases PASS (N=${N}/case, threshold ${PASS_FRAC * 100}%)`);
  process.exit(fail ? 1 : 0);
})();
