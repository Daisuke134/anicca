import { describe, it, expect } from 'vitest';
import { join } from 'node:path';
import { resolveCardImagePath } from '../src/path-security.js';
import type { Language } from '../src/types.js';

const FAKE_ASSETS = '/tmp/fake-assets';

describe('resolveCardImagePath', () => {
  it('resolves valid card_id to correct path', () => {
    const result = resolveCardImagePath(FAKE_ASSETS, 'staying_up_late_0', 'en');
    expect(result).toBe(join(FAKE_ASSETS, 'en', 'staying_up_late_0.png'));
  });

  it('resolves valid card_id for ja language', () => {
    const result = resolveCardImagePath(FAKE_ASSETS, 'anxiety_13', 'ja');
    expect(result).toBe(join(FAKE_ASSETS, 'ja', 'anxiety_13.png'));
  });

  it('rejects path traversal (../)', () => {
    expect(() => resolveCardImagePath(FAKE_ASSETS, '../etc/passwd', 'en')).toThrow(/Invalid card_id format/);
  });

  it('rejects slash in card_id', () => {
    expect(() => resolveCardImagePath(FAKE_ASSETS, 'foo/bar_0', 'en')).toThrow(/Invalid card_id format/);
  });

  it('rejects uppercase card_id', () => {
    expect(() => resolveCardImagePath(FAKE_ASSETS, 'StayingUpLate_0', 'en')).toThrow(/Invalid card_id format/);
  });

  it('rejects empty string', () => {
    expect(() => resolveCardImagePath(FAKE_ASSETS, '', 'en')).toThrow(/Invalid card_id format/);
  });

  it('rejects card_id with trailing underscore (no digit)', () => {
    expect(() => resolveCardImagePath(FAKE_ASSETS, 'staying_up_late_', 'en')).toThrow(/Invalid card_id format/);
  });

  // ─────────────────────────────────────────────
  // Defense-in-depth: relative/isAbsolute guard tests
  // These bypass regex (valid card_id) but trigger path traversal via language
  // ─────────────────────────────────────────────
  it('detects path traversal via malicious language (../x)', () => {
    const maliciousLang = '../x' as unknown as Language;
    expect(() => resolveCardImagePath(FAKE_ASSETS, 'staying_up_late_0', maliciousLang))
      .toThrow(/Path traversal detected/);
  });

  it('detects path traversal via absolute language (/tmp)', () => {
    const absoluteLang = '/tmp' as unknown as Language;
    expect(() => resolveCardImagePath(FAKE_ASSETS, 'staying_up_late_0', absoluteLang))
      .toThrow(/Path traversal detected/);
  });
});
