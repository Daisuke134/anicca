import { describe, it, expect } from 'vitest';
import { getVariantIndex } from '../../../agents/dayCycling.js';
import { SCHEDULE_MAP } from '../../../agents/scheduleMap.js';

describe('variant index / day-cycling', () => {
  it('normal problems (3/day, 42 variants): day15 equals day1; day16 equals day2', () => {
    const pt = 'anxiety';
    const slotsPerDay = SCHEDULE_MAP[pt].length;
    expect(slotsPerDay).toBe(3);
    const totalVariants = 42;

    for (let slot = 0; slot < slotsPerDay; slot++) {
      const day1 = getVariantIndex(0, slot, slotsPerDay, totalVariants);
      const day15 = getVariantIndex(14, slot, slotsPerDay, totalVariants);
      const day2 = getVariantIndex(1, slot, slotsPerDay, totalVariants);
      const day16 = getVariantIndex(15, slot, slotsPerDay, totalVariants);
      expect(day15).toBe(day1);
      expect(day16).toBe(day2);
    }
  });

  it('staying_up_late (5/day, 70 variants): day15 equals day1; day16 equals day2', () => {
    const pt = 'staying_up_late';
    const slotsPerDay = SCHEDULE_MAP[pt].length;
    expect(slotsPerDay).toBe(5);
    const totalVariants = 70;
    for (let slot = 0; slot < slotsPerDay; slot++) {
      const day1 = getVariantIndex(0, slot, slotsPerDay, totalVariants);
      const day15 = getVariantIndex(14, slot, slotsPerDay, totalVariants);
      const day2 = getVariantIndex(1, slot, slotsPerDay, totalVariants);
      const day16 = getVariantIndex(15, slot, slotsPerDay, totalVariants);
      expect(day15).toBe(day1);
      expect(day16).toBe(day2);
    }
  });
});

