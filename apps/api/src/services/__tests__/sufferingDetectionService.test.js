import { describe, it, expect } from 'vitest';
import { detectSuffering, estimateSeverityScore } from '../sufferingDetectionService.js';

describe('sufferingDetectionService', () => {
  it('detects crisis from explicit severityScore', () => {
    const result = detectSuffering({ context: 'test', severityScore: 0.95 });
    expect(result.safeTTriggered).toBe(true);
    expect(result.eventTypes).toContain('crisis:detected');
  });

  it('detects suffering from text heuristics', () => {
    const result = detectSuffering({ context: 'もう無理でつらい' });
    expect(result.safeTTriggered).toBe(false);
    expect(result.eventTypes).toContain('suffering_detected');
  });

  it('returns empty detections when no signal', () => {
    const result = detectSuffering({ context: '今日は散歩した' });
    expect(result.detections).toHaveLength(0);
    expect(result.eventTypes).toEqual([]);
  });

  it('maps crisis severity flag to high score', () => {
    expect(estimateSeverityScore('test', null, 'crisis')).toBeGreaterThanOrEqual(0.9);
  });
});
