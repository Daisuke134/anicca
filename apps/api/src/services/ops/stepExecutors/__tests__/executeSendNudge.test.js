import { describe, it, expect } from 'vitest';

describe('executeSendNudge', () => {
  // T52: test_executeSendNudge_skipsWhenNoContent
  it('T52: skips and returns empty events when no nudge content', async () => {
    const { executeSendNudge } = await import('../executeSendNudge.js');
    const result = await executeSendNudge({
      input: { nudgeContent: null, targetProblemType: 'anxiety' }
    });

    expect(result.output.skipped).toBe(true);
    expect(result.output.sent).toBe(false);
    expect(result.events).toEqual([]);
  });

  it('sends nudge and emits event when content is provided', async () => {
    const { executeSendNudge } = await import('../executeSendNudge.js');
    const result = await executeSendNudge({
      input: { nudgeContent: '大丈夫。まず深呼吸から。', targetProblemType: 'anxiety' }
    });

    expect(result.output.sent).toBe(true);
    expect(result.events).toHaveLength(1);
    expect(result.events[0].kind).toBe('nudge_sent');
  });
});
