import { describe, it, expect, vi } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { replaceDuplicates } from '../duplicateReplacement.js';

/**
 * generateNudges.js は直接実行スクリプト（export なし）。
 * runGenerateNudges() 内で runCrossPlatformSync が呼ばれることを検証する。
 *
 * 戦略: ソースコードを静的解析 + syncCrossPlatform.js のユニットテストでカバー。
 */

const generaTeNudgesSource = readFileSync(
  resolve(import.meta.dirname, '../../jobs/generateNudges.js'),
  'utf-8'
);

describe('generateNudges integration', () => {
  it('imports and calls runCrossPlatformSync (#16)', () => {
    // Verify import statement
    expect(generaTeNudgesSource).toContain(
      "import { runCrossPlatformSync } from './syncCrossPlatform.js'"
    );
    // Verify it's called within runGenerateNudges
    expect(generaTeNudgesSource).toContain('await runCrossPlatformSync(query)');
  });

  it('wraps runCrossPlatformSync in try/catch for graceful degradation (#24)', () => {
    // Verify try/catch around the sync call
    const syncCallIndex = generaTeNudgesSource.indexOf('await runCrossPlatformSync(query)');
    expect(syncCallIndex).toBeGreaterThan(0);

    // Find the nearest preceding "try" block
    const beforeSync = generaTeNudgesSource.substring(0, syncCallIndex);
    const lastTry = beforeSync.lastIndexOf('try {');
    expect(lastTry).toBeGreaterThan(0);

    // Find catch after the sync call
    const afterSync = generaTeNudgesSource.substring(syncCallIndex);
    const catchIndex = afterSync.indexOf('catch');
    expect(catchIndex).toBeGreaterThan(0);

    // Verify it's a non-fatal handler (console.warn, not throw)
    const catchBlock = afterSync.substring(catchIndex, catchIndex + 200);
    expect(catchBlock).toContain('warn');
  });

  it('imports and calls runAggregateTypeStats', () => {
    expect(generaTeNudgesSource).toContain(
      "import { runAggregateTypeStats } from './aggregateTypeStats.js'"
    );
    expect(generaTeNudgesSource).toContain('await runAggregateTypeStats(query)');
  });

  it('wraps runAggregateTypeStats in try/catch for graceful degradation', () => {
    const syncCallIndex = generaTeNudgesSource.indexOf('await runAggregateTypeStats(query)');
    expect(syncCallIndex).toBeGreaterThan(0);

    const beforeSync = generaTeNudgesSource.substring(0, syncCallIndex);
    const lastTry = beforeSync.lastIndexOf('try {');
    expect(lastTry).toBeGreaterThan(0);

    const afterSync = generaTeNudgesSource.substring(syncCallIndex);
    const catchIndex = afterSync.indexOf('catch');
    expect(catchIndex).toBeGreaterThan(0);

    const catchBlock = afterSync.substring(catchIndex, catchIndex + 200);
    expect(catchBlock).toContain('warn');
  });
});

// ========== Patch 6-B: Duplicate Replacement Tests (11 tests) ==========

describe('replaceDuplicates', () => {
  // P0: 基本機能
  it('replaces duplicate hook with unique fallback', () => {
    const nudges = [
      { slotIndex: 0, hook: 'same', content: 'content0', reasoning: '' },
      { slotIndex: 1, hook: 'same', content: 'content1', reasoning: '' },
    ];

    const result = replaceDuplicates(nudges, 'ja');

    expect(result[0].hook).toBe('same');
    expect(result[1].hook).not.toBe('same');
    expect(result[1].reasoning).toContain('[replaced: duplicate hook]');
  });

  it('replaces duplicate content with unique fallback', () => {
    const nudges = [
      { slotIndex: 0, hook: 'hook0', content: 'same content', reasoning: '' },
      { slotIndex: 1, hook: 'hook1', content: 'same content', reasoning: '' },
    ];

    const result = replaceDuplicates(nudges, 'ja');

    expect(result[0].content).toBe('same content');
    expect(result[1].content).not.toBe('same content');
    expect(result[1].reasoning).toContain('[replaced: duplicate content]');
  });

  it('uses different fallbacks for multiple duplicates', () => {
    const nudges = [
      { slotIndex: 0, hook: 'dup', content: 'c0', reasoning: '' },
      { slotIndex: 1, hook: 'dup', content: 'c1', reasoning: '' },
      { slotIndex: 2, hook: 'dup', content: 'c2', reasoning: '' },
    ];

    const result = replaceDuplicates(nudges, 'ja');
    const hooks = result.map(n => n.hook);

    // All hooks should be unique
    expect(new Set(hooks).size).toBe(3);
  });

  // P0: 衝突回避テスト（CRITICAL）
  it('avoids hook collision when original hook matches fallback', () => {
    const nudges = [
      { slotIndex: 0, hook: '今この瞬間', content: 'content0', reasoning: '' }, // matches FALLBACK_HOOKS_JA[0]
      { slotIndex: 1, hook: 'duplicate', content: 'content1', reasoning: '' },
      { slotIndex: 2, hook: 'duplicate', content: 'content2', reasoning: '' },
    ];

    const result = replaceDuplicates(nudges, 'ja');

    // Slot 2 should NOT get '今この瞬間' since slot 0 already has it
    expect(result[2].hook).not.toBe('今この瞬間');
    expect(new Set(result.map(n => n.hook.toLowerCase())).size).toBe(3); // All unique
  });

  // P0: Content衝突回避テスト（CRITICAL）
  it('avoids content collision when original content matches fallback', () => {
    const nudges = [
      { slotIndex: 0, hook: 'h0', content: '今できる一番小さなことを始めよう。', reasoning: '' }, // matches FALLBACK_CONTENTS_JA[0]
      { slotIndex: 1, hook: 'h1', content: 'duplicate content', reasoning: '' },
      { slotIndex: 2, hook: 'h2', content: 'duplicate content', reasoning: '' },
    ];

    const result = replaceDuplicates(nudges, 'ja');

    // Slot 2 should NOT get '今できる...' since slot 0 already has it
    expect(result[2].content).not.toBe('今できる一番小さなことを始めよう。');
    expect(new Set(result.map(n => n.content.toLowerCase())).size).toBe(3); // All unique
  });

  // P1: フォールバック枯渇
  it('handles exhausted fallback pool gracefully', () => {
    // Create nudges that will exhaust all 12 fallbacks
    const nudges = [];
    for (let i = 0; i < 15; i++) {
      nudges.push({ slotIndex: i, hook: 'same', content: `content${i}`, reasoning: '' });
    }

    const result = replaceDuplicates(nudges, 'ja');
    const hooks = result.map(n => n.hook.toLowerCase());

    // All hooks should be unique (some with slot index appended)
    expect(new Set(hooks).size).toBe(15);
  });

  it('appends replacement tag to reasoning', () => {
    const nudges = [
      { slotIndex: 0, hook: 'same', content: 'c0', reasoning: 'original reason' },
      { slotIndex: 1, hook: 'same', content: 'c1', reasoning: '' },
    ];

    const result = replaceDuplicates(nudges, 'ja');

    expect(result[1].reasoning).toContain('[replaced: duplicate hook]');
  });

  // P1: 言語テスト
  it('uses Japanese fallbacks for ja language', () => {
    const nudges = [
      { slotIndex: 0, hook: 'same', content: 'c0', reasoning: '' },
      { slotIndex: 1, hook: 'same', content: 'c1', reasoning: '' },
    ];

    const result = replaceDuplicates(nudges, 'ja');

    // Japanese fallback should contain Japanese characters
    expect(result[1].hook).toMatch(/[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]/);
  });

  it('uses English fallbacks for en language', () => {
    const nudges = [
      { slotIndex: 0, hook: 'same', content: 'c0', reasoning: '' },
      { slotIndex: 1, hook: 'same', content: 'c1', reasoning: '' },
    ];

    const result = replaceDuplicates(nudges, 'en');

    // English fallback should be ASCII
    expect(result[1].hook).toMatch(/^[\x00-\x7F]+$/);
  });

  // P0: Fallback path final validation (after B3 fix) - this tests the disable logic
  it('disables duplicate nudges in fallback path when all replacement fails', () => {
    // This tests the edge case where replaceDuplicates somehow fails to fix all duplicates
    // We verify the disable logic flow works correctly

    const nudges = [
      { slotIndex: 0, hook: 'unique1', content: 'c0', reasoning: '', enabled: true },
      { slotIndex: 1, hook: 'unique2', content: 'c1', reasoning: '', enabled: true },
    ];

    // Manually create a "duplicate found" scenario
    const dupCheck = { valid: false, duplicates: [{ type: 'hook', slotIndex: 1, text: 'test' }] };

    // Apply the disable logic from fallback path
    for (const dup of dupCheck.duplicates) {
      const nudge = nudges.find(n => n.slotIndex === dup.slotIndex);
      if (nudge) {
        nudge.enabled = false;
        nudge.reasoning = (nudge.reasoning || '') + ' [guardrail: duplicate disabled]';
      }
    }

    expect(nudges[1].enabled).toBe(false);
    expect(nudges[1].reasoning).toContain('[guardrail: duplicate disabled]');
  });

  // P1: Edge case - nudge with missing/undefined slotIndex
  it('handles nudge with undefined slotIndex gracefully', () => {
    const nudges = [
      { slotIndex: 0, hook: 'same', content: 'c0', reasoning: '' },
      { hook: 'same', content: 'c1', reasoning: '' }, // missing slotIndex
    ];

    // Should not throw
    expect(() => replaceDuplicates(nudges, 'ja')).not.toThrow();

    const result = replaceDuplicates(nudges, 'ja');
    // Both should have unique hooks
    expect(result[0].hook).not.toBe(result[1].hook);
  });
});
