import { describe, it, expect } from 'vitest';
import { generateCaption, loadCaptionPool, extractCardIndex } from '../src/caption.js';

describe('Caption', () => {
  // ─────────────────────────────────────────────
  // extractCardIndex
  // ─────────────────────────────────────────────
  it('extracts numeric suffix from cardId', () => {
    expect(extractCardIndex('staying_up_late_0')).toBe(0);
    expect(extractCardIndex('staying_up_late_12')).toBe(12);
    expect(extractCardIndex('cant_wake_up_3')).toBe(3);
    expect(extractCardIndex('self_loathing_0')).toBe(0);
  });

  it('returns 0 for cardId without numeric suffix', () => {
    expect(extractCardIndex('no_number')).toBe(0);
  });

  // ─────────────────────────────────────────────
  // loadCaptionPool
  // ─────────────────────────────────────────────
  it('loads EN caption pool with correct structure', () => {
    const pool = loadCaptionPool('staying_up_late', 'en');
    expect(pool.captions.length).toBeGreaterThanOrEqual(5);
    expect(pool.hashtags.length).toBeGreaterThanOrEqual(3);
    for (const entry of pool.captions) {
      expect(entry.hook).toBeTruthy();
      expect(entry.value).toBeTruthy();
      expect(entry.cta).toBeTruthy();
    }
  });

  it('loads JA caption pool with correct structure', () => {
    const pool = loadCaptionPool('staying_up_late', 'ja');
    expect(pool.captions.length).toBeGreaterThanOrEqual(5);
    expect(pool.hashtags.length).toBeGreaterThanOrEqual(3);
  });

  it('loads all 13 problem types for EN', () => {
    const types = [
      'staying_up_late', 'cant_wake_up', 'self_loathing', 'rumination',
      'procrastination', 'anxiety', 'lying', 'bad_mouthing',
      'porn_addiction', 'alcohol_dependency', 'anger', 'obsessive', 'loneliness',
    ];
    for (const type of types) {
      const pool = loadCaptionPool(type, 'en');
      expect(pool.captions.length).toBeGreaterThanOrEqual(5);
    }
  });

  it('loads all 13 problem types for JA', () => {
    const types = [
      'staying_up_late', 'cant_wake_up', 'self_loathing', 'rumination',
      'procrastination', 'anxiety', 'lying', 'bad_mouthing',
      'porn_addiction', 'alcohol_dependency', 'anger', 'obsessive', 'loneliness',
    ];
    for (const type of types) {
      const pool = loadCaptionPool(type, 'ja');
      expect(pool.captions.length).toBeGreaterThanOrEqual(5);
    }
  });

  // ─────────────────────────────────────────────
  // generateCaption: content quality
  // ─────────────────────────────────────────────
  it('caption contains hook, value, cta, and hashtags', () => {
    const caption = generateCaption({
      cardId: 'staying_up_late_0',
      language: 'en',
      problemType: 'staying_up_late',
    });

    // Hook from first caption entry
    expect(caption).toContain("it's 3am again");
    // Has hashtags
    expect(caption).toContain('#insomnia');
    expect(caption).toContain('#mentalhealth');
  });

  it('caption does NOT contain card IDs or app download CTA', () => {
    const caption = generateCaption({
      cardId: 'staying_up_late_0',
      language: 'en',
      problemType: 'staying_up_late',
    });

    // No technical IDs
    expect(caption).not.toContain('[staying_up_late_0_en]');
    expect(caption).not.toContain('staying_up_late_0');
    // No app promo
    expect(caption).not.toContain('Download');
    expect(caption).not.toContain('download');
    expect(caption).not.toContain('Anicca');
  });

  it('JA caption does NOT contain app promo', () => {
    const caption = generateCaption({
      cardId: 'self_loathing_0',
      language: 'ja',
      problemType: 'self_loathing',
    });

    expect(caption).not.toContain('ダウンロード');
    expect(caption).not.toContain('Anicca');
    expect(caption).not.toContain('[self_loathing_0_ja]');
  });

  // ─────────────────────────────────────────────
  // generateCaption: deterministic rotation
  // ─────────────────────────────────────────────
  it('different cardIndex produces different captions', () => {
    const caption0 = generateCaption({
      cardId: 'staying_up_late_0',
      language: 'en',
      problemType: 'staying_up_late',
    });
    const caption1 = generateCaption({
      cardId: 'staying_up_late_1',
      language: 'en',
      problemType: 'staying_up_late',
    });
    expect(caption0).not.toBe(caption1);
  });

  it('same cardId always produces same caption (deterministic)', () => {
    const a = generateCaption({
      cardId: 'anxiety_2',
      language: 'en',
      problemType: 'anxiety',
    });
    const b = generateCaption({
      cardId: 'anxiety_2',
      language: 'en',
      problemType: 'anxiety',
    });
    expect(a).toBe(b);
  });

  it('caption wraps around when cardIndex exceeds pool size', () => {
    // Card index 5 wraps to 0 (pool has 5 entries)
    const caption5 = generateCaption({
      cardId: 'staying_up_late_5',
      language: 'en',
      problemType: 'staying_up_late',
    });
    const caption0 = generateCaption({
      cardId: 'staying_up_late_0',
      language: 'en',
      problemType: 'staying_up_late',
    });
    expect(caption5).toBe(caption0);
  });

  // ─────────────────────────────────────────────
  // generateCaption: caption length (200+ chars for image posts)
  // ─────────────────────────────────────────────
  it('caption is at least 200 chars (optimal for image posts)', () => {
    const caption = generateCaption({
      cardId: 'procrastination_0',
      language: 'en',
      problemType: 'procrastination',
    });
    expect(caption.length).toBeGreaterThanOrEqual(200);
  });

  it('caption is within TikTok limit (2000 chars)', () => {
    const caption = generateCaption({
      cardId: 'loneliness_0',
      language: 'en',
      problemType: 'loneliness',
    });
    expect(caption.length).toBeLessThanOrEqual(2000);
  });
});
