/**
 * queryBuilder — ProblemType × contentType × lang → search query string
 */
import { QUERY_DICT } from './config.js';

/**
 * Build a search query string for a given ProblemType, contentType, and language.
 *
 * @param {string} problemType - One of the 13 ProblemTypes
 * @param {'empathy'|'solution'} contentType - Query category
 * @param {'ja'|'en'} lang - Language
 * @param {Object} [options] - Additional options
 * @param {number} [options.minFaves] - Minimum favorites filter (appended for X search)
 * @returns {string} Search query string
 * @throws {Error} If problemType is not in QUERY_DICT
 */
export function buildQuery(problemType, contentType, lang, options = {}) {
  const queries = QUERY_DICT[problemType];
  if (!queries) {
    throw new Error(`Unknown ProblemType: ${problemType}`);
  }

  const key = `${contentType}_${lang}`;
  const query = queries[key];
  if (!query) {
    throw new Error(`No query found for ${problemType}/${contentType}/${lang}`);
  }

  if (options.minFaves) {
    return `${query} min_faves:${options.minFaves}`;
  }

  return query;
}
