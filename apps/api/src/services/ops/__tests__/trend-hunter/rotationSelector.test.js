import { describe, it, expect } from 'vitest';
import { selectRotationGroup } from '../../trend-hunter/rotationSelector.js';
import { ROTATION_GROUPS } from '../../trend-hunter/config.js';

describe('rotationSelector', () => {
  // #6
  it('returns group 0 for executionCount=0', () => {
    const result = selectRotationGroup(0);
    expect(result).toEqual(ROTATION_GROUPS[0]);
  });

  // #7
  it('returns group 1 for executionCount=1', () => {
    const result = selectRotationGroup(1);
    expect(result).toEqual(ROTATION_GROUPS[1]);
  });

  // #8
  it('returns group 2 for executionCount=2', () => {
    const result = selectRotationGroup(2);
    expect(result).toEqual(ROTATION_GROUPS[2]);
  });

  // #9
  it('wraps around: executionCount=3 returns group 0', () => {
    const result = selectRotationGroup(3);
    expect(result).toEqual(ROTATION_GROUPS[0]);
  });

  // #10
  it('handles large numbers: executionCount=999 returns group 999%3=0', () => {
    const result = selectRotationGroup(999);
    expect(result).toEqual(ROTATION_GROUPS[999 % 3]);
  });
});
