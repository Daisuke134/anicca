import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { join } from 'node:path';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { loadTracker, saveTracker } from '../src/tracker-io.js';
import { Tracker } from '../src/tracker.js';
import { generateCardOrder } from '../src/card-order.js';
import type { TrackerData } from '../src/types.js';

describe('tracker-io', () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), 'tracker-test-'));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true });
  });

  it('loadTracker returns default when file missing', async () => {
    const tracker = await loadTracker(join(tempDir, 'missing.json'));
    const data = tracker.getData();
    expect(data.version).toBe(1);
    expect(data.cards).toEqual({});
    expect(data.next_index).toEqual({ en: 0, ja: 0 });
  });

  it('saveTracker + loadTracker round-trip preserves data', async () => {
    const filePath = join(tempDir, 'tracker.json');

    const initial: TrackerData = {
      version: 1,
      cards: {
        'staying_up_late_0': {
          en: {
            status: 'posted',
            reserved_at: '2026-01-01T00:00:00Z',
            run_id: 'r1',
            posted_at: '2026-01-01T00:01:00Z',
            blotato_post_id: 'blot-1',
          },
        },
      },
      next_index: { en: 1, ja: 0 },
      card_order: generateCardOrder(),
    };
    const tracker = new Tracker(initial);

    await saveTracker(filePath, tracker);
    const loaded = await loadTracker(filePath);
    const data = loaded.getData();

    expect(data.version).toBe(1);
    expect(data.next_index.en).toBe(1);
    expect(data.cards['staying_up_late_0']?.en?.status).toBe('posted');
    expect(data.cards['staying_up_late_0']?.en?.blotato_post_id).toBe('blot-1');
  });

  // ─────────────────────────────────────────────
  // Validation: invalid card_id in card_order
  // ─────────────────────────────────────────────
  it('rejects invalid card_id in card_order', async () => {
    const filePath = join(tempDir, 'bad-order.json');
    const badData = {
      version: 1,
      cards: {},
      next_index: { en: 0, ja: 0 },
      card_order: ['staying_up_late_0', '../../../etc/passwd'],
    };
    await writeFile(filePath, JSON.stringify(badData), 'utf-8');

    await expect(loadTracker(filePath)).rejects.toThrow(/Invalid card_id/);
  });

  // ─────────────────────────────────────────────
  // Validation: card_id in cards not in canonical set
  // ─────────────────────────────────────────────
  it('rejects unknown card_id in cards', async () => {
    const filePath = join(tempDir, 'orphan.json');
    const fullOrder = generateCardOrder();
    const badData = {
      version: 1,
      cards: {
        'unknown_card_99': {
          en: {
            status: 'posted',
            reserved_at: '2026-01-01T00:00:00Z',
            run_id: 'r1',
            posted_at: '2026-01-01T00:01:00Z',
            blotato_post_id: 'blot-1',
          },
        },
      },
      next_index: { en: 1, ja: 0 },
      card_order: fullOrder,
    };
    await writeFile(filePath, JSON.stringify(badData), 'utf-8');

    await expect(loadTracker(filePath)).rejects.toThrow(/Unknown card_id in cards/);
  });

  // ─────────────────────────────────────────────
  // Validation: unknown card_id in card_order (valid format but not in canonical 189-card set)
  // ─────────────────────────────────────────────
  it('rejects unknown card_id in card_order (not in canonical set)', async () => {
    const filePath = join(tempDir, 'unknown.json');
    const badData = {
      version: 1,
      cards: {},
      next_index: { en: 0, ja: 0 },
      card_order: ['staying_up_late_0', 'foo_1'],  // foo_1 passes regex but is not a real card
    };
    await writeFile(filePath, JSON.stringify(badData), 'utf-8');

    await expect(loadTracker(filePath)).rejects.toThrow(/Unknown card_id.*foo_1/);
  });

  // ─────────────────────────────────────────────
  // Validation: incomplete card_order (missing cards from canonical 189 set)
  // ─────────────────────────────────────────────
  it('rejects incomplete card_order (fewer than 189 canonical cards)', async () => {
    const filePath = join(tempDir, 'incomplete.json');
    const badData = {
      version: 1,
      cards: {},
      next_index: { en: 0, ja: 0 },
      card_order: ['staying_up_late_0', 'staying_up_late_1'],  // only 2 of 189
    };
    await writeFile(filePath, JSON.stringify(badData), 'utf-8');

    await expect(loadTracker(filePath)).rejects.toThrow(/card_order has 2 entries but canonical set has 189/);
  });

  // ─────────────────────────────────────────────
  // Validation: duplicate card_id in card_order
  // ─────────────────────────────────────────────
  it('rejects duplicate card_id in card_order', async () => {
    const filePath = join(tempDir, 'dupe.json');
    const badData = {
      version: 1,
      cards: {},
      next_index: { en: 0, ja: 0 },
      card_order: ['staying_up_late_0', 'staying_up_late_0'],
    };
    await writeFile(filePath, JSON.stringify(badData), 'utf-8');

    await expect(loadTracker(filePath)).rejects.toThrow(/Duplicate card_id/);
  });
});
