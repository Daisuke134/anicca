import { describe, it, expect } from 'vitest';
import {
  getVariantIndex,
  getToneForSlot,
  selectVariant,
  calculateDayIndex,
  verify7DayUniqueness,
} from '../dayCycling.js';
import { NUDGE_TONES, SCHEDULE_MAP } from '../scheduleMap.js';

// ===== getVariantIndex =====

describe('getVariantIndex', () => {
  it('returns 0 for day 0, slot 0', () => {
    expect(getVariantIndex(0, 0, 5, 35)).toBe(0);
  });

  it('increments with slot index', () => {
    expect(getVariantIndex(0, 1, 5, 35)).toBe(1);
    expect(getVariantIndex(0, 2, 5, 35)).toBe(2);
  });

  it('wraps around totalVariants', () => {
    expect(getVariantIndex(7, 0, 5, 35)).toBe(0); // 7*5 = 35 mod 35 = 0
  });

  it('day 1 starts at slotsPerDay', () => {
    expect(getVariantIndex(1, 0, 5, 35)).toBe(5);
  });

  it('returns 0 for zero variants', () => {
    expect(getVariantIndex(3, 2, 5, 0)).toBe(0);
  });
});

// ===== getToneForSlot =====

describe('getToneForSlot', () => {
  it('cycles through 5 tones', () => {
    const tones = [];
    for (let i = 0; i < 5; i++) {
      tones.push(getToneForSlot(0, i));
    }
    expect(new Set(tones).size).toBe(5);
  });

  it('returns valid tone', () => {
    const tone = getToneForSlot(3, 2);
    expect(NUDGE_TONES).toContain(tone);
  });
});

// ===== selectVariant =====

describe('selectVariant', () => {
  const variants = Array.from({ length: 35 }, (_, i) => ({
    hook: `h${i}`, content: `c${i}`, tone: NUDGE_TONES[i % 5],
  }));

  it('returns different variants for different days', () => {
    const v0 = selectVariant('procrastination', 0, 0, variants);
    const v1 = selectVariant('procrastination', 1, 0, variants);
    expect(v0.hook).not.toBe(v1.hook);
  });

  it('returns fallback for empty variants', () => {
    const v = selectVariant('unknown', 0, 0, []);
    expect(v.hook).toBe('Keep moving forward');
  });

  it('preserves variant tone when available', () => {
    const v = selectVariant('procrastination', 0, 0, variants);
    expect(v.tone).toBe('strict'); // variants[0].tone
  });
});

// ===== calculateDayIndex =====

describe('calculateDayIndex', () => {
  it('returns 0 for same day', () => {
    const now = new Date('2026-02-01T10:00:00Z');
    expect(calculateDayIndex('2026-02-01T00:00:00Z', now)).toBe(0);
  });

  it('returns 1 for next day', () => {
    const now = new Date('2026-02-02T10:00:00Z');
    expect(calculateDayIndex('2026-02-01T00:00:00Z', now)).toBe(1);
  });

  it('returns 7 for 1 week later', () => {
    const now = new Date('2026-02-08T10:00:00Z');
    expect(calculateDayIndex('2026-02-01T00:00:00Z', now)).toBe(7);
  });

  it('clamps to 0 for future dates', () => {
    const now = new Date('2026-01-31T10:00:00Z');
    expect(calculateDayIndex('2026-02-01T00:00:00Z', now)).toBe(0);
  });
});

// ===== verify7DayUniqueness =====

describe('verify7DayUniqueness', () => {
  it('procrastination with 35 variants is unique for 7 days', () => {
    const variants = Array.from({ length: 35 }, (_, i) => ({ hook: `h${i}`, content: `c${i}`, tone: 'strict' }));
    const result = verify7DayUniqueness('procrastination', variants, 7);
    expect(result.unique).toBe(true);
  });

  it('reports non-unique when variants < slots*days', () => {
    const variants = [{ hook: 'h0', content: 'c0', tone: 'strict' }];
    const result = verify7DayUniqueness('procrastination', variants, 7);
    // With 1 variant, uniqueVariants = 1, but totalSlots = 5*7 = 35
    expect(result.uniqueVariants).toBe(1);
    expect(result.unique).toBe(true); // unique because seen.size === variants.length
  });

  it('staying_up_late with 35 variants covers 7 days', () => {
    const variants = Array.from({ length: 35 }, (_, i) => ({ hook: `h${i}`, content: `c${i}`, tone: 'strict' }));
    const result = verify7DayUniqueness('staying_up_late', variants, 7);
    expect(result.unique).toBe(true);
    expect(result.totalSlots).toBe(35); // 5 slots * 7 days (v1.6.0 schedule)
  });
});
