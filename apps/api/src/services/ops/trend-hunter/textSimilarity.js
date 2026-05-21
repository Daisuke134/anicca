/**
 * textSimilarity — Jaccard bi-gram similarity for duplicate detection
 */

/**
 * Calculate Jaccard similarity using character bi-grams.
 *
 * @param {string} text1 - First text
 * @param {string} text2 - Second text
 * @returns {number} Similarity score 0.0-1.0
 */
export function jaccardBigram(text1, text2) {
  const bigrams = (s) => {
    const normalized = s.replace(/\s+/g, ' ').trim().toLowerCase();
    const set = new Set();
    for (let i = 0; i < normalized.length - 1; i++) {
      set.add(normalized.substring(i, i + 2));
    }
    return set;
  };

  const a = bigrams(text1);
  const b = bigrams(text2);

  if (a.size === 0 && b.size === 0) return 0;

  const intersection = new Set([...a].filter(x => b.has(x)));
  const union = new Set([...a, ...b]);

  return union.size === 0 ? 0 : intersection.size / union.size;
}

/**
 * Check if two texts are duplicates based on Jaccard similarity threshold.
 *
 * @param {string} text1 - First text
 * @param {string} text2 - Second text
 * @param {number} threshold - Similarity threshold (default 0.7)
 * @returns {boolean} True if similarity >= threshold
 */
export function isDuplicate(text1, text2, threshold = 0.7) {
  return jaccardBigram(text1, text2) >= threshold;
}
