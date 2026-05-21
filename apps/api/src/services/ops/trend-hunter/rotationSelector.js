/**
 * rotationSelector — executionCount → ProblemType group (v1 fixed rotation)
 */
import { ROTATION_GROUPS } from './config.js';

/**
 * Select the ProblemType group for the current execution based on fixed rotation.
 *
 * @param {number} executionCount - Current execution count
 * @returns {string[]} Array of ProblemType strings for this rotation
 */
export function selectRotationGroup(executionCount) {
  const groupIndex = executionCount % ROTATION_GROUPS.length;
  return ROTATION_GROUPS[groupIndex];
}
