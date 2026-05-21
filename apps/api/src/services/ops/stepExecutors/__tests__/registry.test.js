import { describe, it, expect } from 'vitest';
import { getExecutor } from '../registry.js';

describe('Executor Registry', () => {
  // T37: test_executorRegistry_unknownKind
  it('T37: throws Error for unknown step_kind', () => {
    expect(() => getExecutor('nonexistent')).toThrow('Unknown step_kind: nonexistent');
  });

  it('returns a function for draft_content', () => {
    const executor = getExecutor('draft_content');
    expect(typeof executor).toBe('function');
  });

  it('returns a function for verify_content', () => {
    const executor = getExecutor('verify_content');
    expect(typeof executor).toBe('function');
  });

  it('returns a function for post_x', () => {
    const executor = getExecutor('post_x');
    expect(typeof executor).toBe('function');
  });

  it('returns a function for all 12 registered kinds', () => {
    const kinds = [
      'draft_content', 'verify_content', 'post_x', 'post_tiktok',
      'fetch_metrics', 'analyze_engagement', 'diagnose', 'detect_suffering',
      'draft_nudge', 'send_nudge', 'evaluate_hook', 'run_trend_scan'
    ];
    for (const kind of kinds) {
      expect(typeof getExecutor(kind)).toBe('function');
    }
  });
});
