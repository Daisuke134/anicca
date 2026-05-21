/**
 * Duplicate Replacement Logic (Patch 6-B)
 *
 * Replaces duplicate hooks/content with unique fallbacks.
 * Separated from generateNudges.js for testability.
 */

// ========== Fallback Constants for Duplicate Replacement ==========
const FALLBACK_HOOKS_JA = [
  "今この瞬間", "一歩だけ", "深呼吸して", "立ち上がれ",
  "5秒で動け", "自分を信じろ", "小さく始めよ", "今日を生きろ",
  "動き出せ", "変わる時", "諦めるな", "前を向け"
];
const FALLBACK_HOOKS_EN = [
  "This moment", "One step", "Breathe deep", "Stand up",
  "Move in 5", "Trust yourself", "Start small", "Live today",
  "Get moving", "Time to change", "Don't give up", "Look ahead"
];
const FALLBACK_CONTENTS_JA = [
  "今できる一番小さなことを始めよう。",
  "完璧じゃなくていい。動き出すことが全て。",
  "過去は変えられない。今この瞬間に集中しよう。",
  "難しいのはわかってる。それでも一歩だけ。",
  "5秒数えろ。その間に体を動かせ。",
  "自分との約束を一つだけ守ろう。",
  "大きな目標より、今日できることを。",
  "失敗しても大丈夫。また明日がある。",
  "息を吸って、吐いて。それだけでいい。",
  "自分を責めるな。前に進め。",
  "小さな一歩が大きな変化を生む。",
  "今日の自分を信じろ。"
];
const FALLBACK_CONTENTS_EN = [
  "Start with the smallest thing you can do right now.",
  "You don't need to be perfect. Just move.",
  "You can't change the past. Focus on this moment.",
  "I know it's hard. Just take one step.",
  "Count to 5. Move your body before it ends.",
  "Keep just one promise to yourself today.",
  "Forget big goals. What can you do today?",
  "It's okay to fail. Tomorrow is another chance.",
  "Breathe in, breathe out. That's enough.",
  "Don't blame yourself. Move forward.",
  "Small steps create big changes.",
  "Trust yourself today."
];

/**
 * Collision-safe fallback selection
 * Avoids selecting a fallback that's already in the seenSet
 */
function selectUniqueFallback(fallbacks, seenSet, startIndex, slotIndex) {
  let index = startIndex;
  let attempts = 0;

  while (attempts < fallbacks.length) {
    const candidate = fallbacks[index % fallbacks.length];
    const candidateLower = candidate.trim().toLowerCase();

    if (!seenSet.has(candidateLower)) {
      return { value: candidate, nextIndex: index + 1 };
    }

    index++;
    attempts++;
  }

  // All fallbacks collide - create unique version with slot index
  console.warn(`⚠️ [DuplicateReplacement] All fallbacks collide for slot ${slotIndex}, creating unique variant`);
  return {
    value: `${fallbacks[startIndex % fallbacks.length]} (${slotIndex ?? 'X'})`,
    nextIndex: startIndex + 1
  };
}

/**
 * Replace duplicate hooks/content with unique fallbacks
 * @param {Array} nudges - Array of nudge objects
 * @param {string} preferredLanguage - 'ja' or 'en'
 * @returns {Array} - nudges with duplicates replaced
 */
export function replaceDuplicates(nudges, preferredLanguage) {
  const seenHooks = new Set();
  const seenContents = new Set();
  let hookFallbackIndex = 0;
  let contentFallbackIndex = 0;

  const isJapanese = preferredLanguage === 'ja';
  const fallbackHooks = isJapanese ? FALLBACK_HOOKS_JA : FALLBACK_HOOKS_EN;
  const fallbackContents = isJapanese ? FALLBACK_CONTENTS_JA : FALLBACK_CONTENTS_EN;

  for (const nudge of nudges) {
    const hookLower = (nudge.hook || '').trim().toLowerCase();
    const contentLower = (nudge.content || '').trim().toLowerCase();

    // Hook重複チェック & 置換
    if (hookLower && seenHooks.has(hookLower)) {
      const { value: newHook, nextIndex } = selectUniqueFallback(
        fallbackHooks, seenHooks, hookFallbackIndex, nudge.slotIndex
      );
      console.warn(`⚠️ [DuplicateReplacement] Replacing duplicate hook at slot ${nudge.slotIndex}: "${nudge.hook}" → "${newHook}"`);
      nudge.hook = newHook;
      nudge.reasoning = (nudge.reasoning || '') + ' [replaced: duplicate hook]';
      hookFallbackIndex = nextIndex;
    }
    seenHooks.add((nudge.hook || '').trim().toLowerCase());

    // Content重複チェック & 置換
    if (contentLower && seenContents.has(contentLower)) {
      const { value: newContent, nextIndex } = selectUniqueFallback(
        fallbackContents, seenContents, contentFallbackIndex, nudge.slotIndex
      );
      console.warn(`⚠️ [DuplicateReplacement] Replacing duplicate content at slot ${nudge.slotIndex}: "${(nudge.content || '').slice(0, 20)}..." → "${newContent.slice(0, 20)}..."`);
      nudge.content = newContent;
      nudge.reasoning = (nudge.reasoning || '') + ' [replaced: duplicate content]';
      contentFallbackIndex = nextIndex;
    }
    seenContents.add((nudge.content || '').trim().toLowerCase());
  }

  return nudges;
}
