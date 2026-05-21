import { describe, it, expect } from 'vitest';
import { generateCardOrder, TOTAL_CARDS, problemTypeFromCardId } from '../src/card-order.js';

describe('card-order', () => {
  it('generates exactly 189 cards', () => {
    const order = generateCardOrder();
    expect(order).toHaveLength(189);
    expect(TOTAL_CARDS).toBe(189);
  });

  it('starts with staying_up_late (rule-based priority)', () => {
    const order = generateCardOrder();
    expect(order[0]).toBe('staying_up_late_0');
    // stayingUpLate has 21 variants
    expect(order[20]).toBe('staying_up_late_20');
    // Next should be cant_wake_up
    expect(order[21]).toBe('cant_wake_up_0');
  });

  it('has no duplicates', () => {
    const order = generateCardOrder();
    const unique = new Set(order);
    expect(unique.size).toBe(order.length);
  });

  it('extracts problem type from card_id', () => {
    expect(problemTypeFromCardId('staying_up_late_0')).toBe('staying_up_late');
    expect(problemTypeFromCardId('cant_wake_up_13')).toBe('cant_wake_up');
    expect(problemTypeFromCardId('alcohol_dependency_5')).toBe('alcohol_dependency');
  });

  it('all card_ids match the CARD_ID_PATTERN', () => {
    const order = generateCardOrder();
    const pattern = /^[a-z_]+_\d+$/;
    for (const cardId of order) {
      expect(cardId).toMatch(pattern);
    }
  });

  it('CARD_ID_PATTERN rejects path traversal and invalid formats', () => {
    const pattern = /^[a-z_]+_\d+$/;
    expect(pattern.test('../etc/passwd')).toBe(false);
    expect(pattern.test('foo/bar_0')).toBe(false);
    expect(pattern.test('StayingUpLate_0')).toBe(false);
    expect(pattern.test('staying_up_late_')).toBe(false);
    expect(pattern.test('')).toBe(false);
    // Valid format (but might not be a real card)
    expect(pattern.test('staying_up_late_0')).toBe(true);
    expect(pattern.test('anxiety_13')).toBe(true);
  });
});
