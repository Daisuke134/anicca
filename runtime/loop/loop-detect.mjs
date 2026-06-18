/**
 * loop-detect.mjs — Pure: isLooping(recentActions, window) → boolean
 *
 * REQ-005: Loop detect and idle guard.
 * Compares the last `window` consecutive action tuples for identity.
 * window=0 is treated as disabled (always returns false).
 *
 * PROP-008, PROP-009
 */

/**
 * Determines if the last `window` actions are all identical.
 *
 * @param {Array<{slot: string, args: object}>} recentActions
 * @param {number} window - number of entries to inspect (0 = disabled)
 * @returns {boolean}
 */
export function isLooping(recentActions, window) {
  if (!window || window <= 0) return false;
  if (!Array.isArray(recentActions) || recentActions.length < window) return false;

  const tail = recentActions.slice(-window);
  const serialised = tail.map(actionKey);
  return serialised.every(s => s === serialised[0]);
}

/**
 * Produce a stable key for an action (slot + sorted args JSON).
 * @param {{ slot: string, args: object }} action
 * @returns {string}
 */
function actionKey(action) {
  if (!action) return '';
  const argsStr = action.args != null
    ? JSON.stringify(sortedKeys(action.args))
    : '{}';
  return `${action.slot}:${argsStr}`;
}

/**
 * Return a new object with keys sorted — so JSON.stringify is stable.
 */
function sortedKeys(obj) {
  if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) return obj;
  return Object.fromEntries(
    Object.keys(obj).sort().map(k => [k, sortedKeys(obj[k])])
  );
}
