/**
 * Day-Cycling Algorithm (Phase 7)
 *
 * Ensures deterministic day-cycling. For ProblemType nudges we set totalVariants to
 * 42 (14 days * 3/day) or 70 (14 days * 5/day), which guarantees the first 14 days
 * are unique per-problem (no slot-crossing duplicates) before repeating.
 * Deterministic: same dayIndex + slotIndex → same variant.
 *
 * dayIndex = days since user registration
 * slotIndexInProblem = slot number within that problem's schedule (0-based)
 * variantIndex = (dayIndex * slotsPerDay + slotIndexInProblem) % totalVariants
 */

import { SCHEDULE_MAP, NUDGE_TONES } from './scheduleMap.js';

/**
 * Calculate the variant index for a given day and slot.
 *
 * @param {number} dayIndex - Days since registration (0-based)
 * @param {number} slotIndexInProblem - Slot index within the problem (0-based)
 * @param {number} slotsPerDay - Number of slots per day for this problem
 * @param {number} totalVariants - Total number of available variants
 * @returns {number} The variant index to use
 */
export function getVariantIndex(dayIndex, slotIndexInProblem, slotsPerDay, totalVariants) {
  if (totalVariants <= 0) return 0;
  return (dayIndex * slotsPerDay + slotIndexInProblem) % totalVariants;
}

/**
 * Get the tone for a given slot using round-robin across 5 tones.
 *
 * @param {number} dayIndex - Days since registration
 * @param {number} slotIndexInProblem - Slot index within the problem
 * @returns {string} Tone name
 */
export function getToneForSlot(dayIndex, slotIndexInProblem) {
  const index = (dayIndex * 5 + slotIndexInProblem) % NUDGE_TONES.length;
  return NUDGE_TONES[index];
}

/**
 * Apply Day-Cycling to rule-based nudges.
 * Selects variants based on dayIndex to avoid repetition.
 *
 * @param {string} problemType
 * @param {number} dayIndex - Days since registration
 * @param {number} slotIndexInProblem - Slot index within the problem
 * @param {Array} variants - Available content variants for this problem
 * @returns {{ hook: string, content: string, tone: string }}
 */
export function selectVariant(problemType, dayIndex, slotIndexInProblem, variants) {
  if (!variants || variants.length === 0) {
    return {
      hook: 'Keep moving forward',
      content: 'Start with a small step.',
      tone: getToneForSlot(dayIndex, slotIndexInProblem),
    };
  }

  const slotsPerDay = (SCHEDULE_MAP[problemType] || ['dummy']).length;
  const variantIndex = getVariantIndex(dayIndex, slotIndexInProblem, slotsPerDay, variants.length);
  const variant = variants[variantIndex];

  return {
    hook: variant.hook,
    content: variant.content,
    tone: variant.tone || getToneForSlot(dayIndex, slotIndexInProblem),
  };
}

/**
 * Calculate dayIndex from user registration date.
 *
 * @param {Date|string} registrationDate
 * @param {Date} [now]
 * @returns {number} Days since registration (0-based)
 */
export function calculateDayIndex(registrationDate, now = new Date()) {
  const reg = new Date(registrationDate);
  const diffMs = now.getTime() - reg.getTime();
  return Math.max(0, Math.floor(diffMs / (24 * 60 * 60 * 1000)));
}

/**
 * Verify 7-day uniqueness for a problem type.
 * Used in testing to confirm the algorithm produces unique content.
 *
 * @param {string} problemType
 * @param {Array} variants
 * @param {number} [days=7]
 * @returns {{ unique: boolean, totalSlots: number, uniqueVariants: number }}
 */
export function verify7DayUniqueness(problemType, variants, days = 7) {
  const slotsPerDay = (SCHEDULE_MAP[problemType] || []).length;
  const seen = new Set();
  let totalSlots = 0;

  for (let d = 0; d < days; d++) {
    for (let s = 0; s < slotsPerDay; s++) {
      const idx = getVariantIndex(d, s, slotsPerDay, variants.length);
      seen.add(idx);
      totalSlots++;
    }
  }

  return {
    unique: seen.size === totalSlots || seen.size === variants.length,
    totalSlots,
    uniqueVariants: seen.size,
  };
}
