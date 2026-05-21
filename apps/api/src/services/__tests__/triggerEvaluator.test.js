import { describe, it, expect } from 'vitest';
import { evaluateTriggers } from '../triggerEvaluator.js';

describe('triggerEvaluator', () => {
  it('matches triggers using all matching events, not only latest event', () => {
    const now = new Date('2026-02-09T12:00:00.000Z');
    const triggers = [
      { id: 't1', eventType: 'suffering_detected', minCount: 2, windowMs: 24 * 60 * 60 * 1000 },
      { id: 't2', eventType: 'crisis:detected', minCount: 1, windowMs: 24 * 60 * 60 * 1000 },
    ];

    const events = [
      { eventType: 'suffering_detected', createdAt: '2026-02-09T10:00:00.000Z' },
      { eventType: 'suffering_detected', createdAt: '2026-02-09T11:00:00.000Z' },
      { eventType: 'crisis:detected', createdAt: '2026-02-09T11:30:00.000Z' },
    ];

    const matched = evaluateTriggers(triggers, events, now);
    expect(matched.map((m) => m.triggerId).sort()).toEqual(['t1', 't2']);
  });

  it('respects evaluation window', () => {
    const now = new Date('2026-02-09T12:00:00.000Z');
    const triggers = [
      { id: 't1', eventType: 'suffering_detected', minCount: 1, windowMs: 60 * 60 * 1000 },
    ];

    const events = [
      { eventType: 'suffering_detected', createdAt: '2026-02-09T10:00:00.000Z' },
    ];

    const matched = evaluateTriggers(triggers, events, now);
    expect(matched).toHaveLength(0);
  });
});
