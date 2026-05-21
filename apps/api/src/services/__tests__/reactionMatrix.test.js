import { describe, it, expect } from 'vitest';
import { scoreReaction } from '../reactionMatrix.js';

describe('reactionMatrix', () => {
  it('scores app reactions', () => {
    expect(scoreReaction('app', { notification_tap: 1 })).toBe(3);
    expect(scoreReaction('app', { thumbs_up: 1, ignore: 1 })).toBe(1);
    expect(scoreReaction('app', { thumbs_down: 1 })).toBe(-2);
  });

  it('scores moltbook reactions', () => {
    expect(scoreReaction('moltbook', { upvote: 2 })).toBe(4);
    expect(scoreReaction('moltbook', { upvote: 1, reply: 1 })).toBe(3);
  });

  it('scores x reactions but does not imply reply behavior', () => {
    expect(scoreReaction('x', { like: 1, retweet: 1, reply: 1 })).toBe(4);
  });

  it('unknown platforms score 0', () => {
    expect(scoreReaction('unknown', { like: 1 })).toBe(0);
  });
});
