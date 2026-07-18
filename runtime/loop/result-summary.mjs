/**
 * result-summary.mjs — Pure: summarizeSkillResult(rawOutput) → string
 *
 * TOOL-2 Phase A: skills' contract is "stdout emits one JSON line" (the same convention run.sh
 * scripts across skills/earn, skills/report, etc. already follow for their own trace/ledger lines).
 * When a skill honours that contract, parsing the LAST non-empty stdout line as JSON and recording
 * the STRUCTURED object lets the next wake's prompt reason over real fields (sales count, error
 * reason, tx hash) instead of re-parsing an arbitrary raw-text slice. Falls back to the pre-existing
 * raw-slice behaviour (whitespace-collapsed, capped at 900 chars) for any output that isn't a clean
 * trailing JSON line — byte-identical to the old inline logic for every non-JSON skill.
 */

const RAW_SLICE_MAX = 900;
const JSON_SLICE_MAX = 600;

/**
 * @param {string} rawOutput - the skill's combined stdout+stderr (already redacted/capped upstream)
 * @returns {string} the value to store as the ledger `result` field, '' if rawOutput is empty
 */
export function summarizeSkillResult(rawOutput) {
  const text = typeof rawOutput === 'string' ? rawOutput : '';
  if (!text) return '';

  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  const lastLine = lines.length ? lines[lines.length - 1] : '';
  if (lastLine) {
    try {
      const parsed = JSON.parse(lastLine);
      // typeof [] === 'object' in JS -- exclude arrays explicitly so only a genuine JSON *object*
      // line (the skills' actual stdout contract) is treated as structured.
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return JSON.stringify(parsed).slice(0, JSON_SLICE_MAX);
      }
    } catch {
      // not a clean trailing JSON line — fall through to raw-slice behaviour
    }
  }
  return text.replace(/\s+/g, ' ').slice(0, RAW_SLICE_MAX);
}
