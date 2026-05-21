import { describe, it, expect, beforeEach } from 'vitest';
import { Tracker } from '../src/tracker.js';
import type { TrackerData } from '../src/types.js';

/** Helper: create a minimal card_order for testing */
function makeCardOrder(count: number): string[] {
  const order: string[] = [];
  const types = [
    'staying_up_late', 'cant_wake_up', 'self_loathing', 'rumination',
    'procrastination', 'anxiety', 'lying', 'bad_mouthing',
    'porn_addiction', 'alcohol_dependency', 'anger', 'obsessive', 'loneliness',
  ];
  let idx = 0;
  for (const type of types) {
    const variants = type === 'staying_up_late' ? 21 : 14;
    for (let v = 0; v < variants && idx < count; v++, idx++) {
      order.push(`${type}_${v}`);
    }
    if (idx >= count) break;
  }
  return order;
}

function emptyTracker(cardCount = 5): TrackerData {
  return {
    version: 1,
    cards: {},
    next_index: { en: 0, ja: 0 },
    card_order: makeCardOrder(cardCount),
  };
}

describe('Tracker', () => {
  let tracker: Tracker;

  beforeEach(() => {
    tracker = new Tracker(emptyTracker());
  });

  // ─────────────────────────────────────────────
  // Test #5: getNextUnpostedCard
  // ─────────────────────────────────────────────
  it('test_getNextUnpostedCard_returnsCorrectCard', () => {
    const card = tracker.getNextUnpostedCard('en');
    expect(card).toBe('staying_up_late_0');
  });

  // ─────────────────────────────────────────────
  // Test #6: markAsPosted
  // ─────────────────────────────────────────────
  it('test_markAsPosted_updatesJSON', () => {
    tracker.reserveNextCard('en', 'run-1');

    tracker.markAsPosted('staying_up_late_0', 'en');

    const data = tracker.getData();
    const entry = data.cards['staying_up_late_0']?.en;
    expect(entry?.status).toBe('posted');
    expect(entry?.posted_at).toBeTruthy();
  });

  // ─────────────────────────────────────────────
  // Test #7: allCardsPosted
  // ─────────────────────────────────────────────
  it('test_allCardsPosted_returnsTrue', () => {
    const small = new Tracker(emptyTracker(2));

    small.reserveNextCard('en', 'run-1');
    small.markAsPosted('staying_up_late_0', 'en');
    small.reserveNextCard('en', 'run-2');
    small.markAsPosted('staying_up_late_1', 'en');

    expect(small.allCardsPosted('en')).toBe(true);
    expect(small.allCardsPosted('ja')).toBe(false);
  });

  // ─────────────────────────────────────────────
  // Test #8: no duplicate card within language
  // ─────────────────────────────────────────────
  it('test_no_duplicate_card_within_language', () => {
    tracker.reserveNextCard('en', 'run-1');
    tracker.markAsPosted('staying_up_late_0', 'en');

    const next = tracker.getNextUnpostedCard('en');
    expect(next).toBe('staying_up_late_1');
    expect(next).not.toBe('staying_up_late_0');
  });

  // ─────────────────────────────────────────────
  // Test #9: EN/JA daily runs post exactly once each
  // ─────────────────────────────────────────────
  it('test_two_daily_runs_post_en_and_ja_exactly_once_each', () => {
    const enResult = tracker.reserveNextCard('en', 'run-en');
    tracker.markAsPosted(enResult.cardId, 'en');

    const jaResult = tracker.reserveNextCard('ja', 'run-ja');
    tracker.markAsPosted(jaResult.cardId, 'ja');

    const data = tracker.getData();
    expect(data.next_index.en).toBe(1);
    expect(data.next_index.ja).toBe(1);
    expect(enResult.cardId).toBe('staying_up_late_0');
    expect(jaResult.cardId).toBe('staying_up_late_0');
  });

  // ─────────────────────────────────────────────
  // Test #10: rule-based priority (card_order deterministic)
  // ─────────────────────────────────────────────
  it('test_selector_prioritizes_rule_based', () => {
    const data = tracker.getData();
    expect(data.card_order[0]).toBe('staying_up_late_0');
    expect(data.card_order.length).toBeGreaterThan(0);
  });

  // ─────────────────────────────────────────────
  // Test #23: in_flight → posted transition
  // ─────────────────────────────────────────────
  it('test_in_flight_to_posted_transition', () => {
    tracker.reserveNextCard('en', 'run-1');
    const data1 = tracker.getData();
    expect(data1.cards['staying_up_late_0']?.en?.status).toBe('in_flight');

    tracker.markAsPosted('staying_up_late_0', 'en');

    const data2 = tracker.getData();
    const entry = data2.cards['staying_up_late_0']?.en;
    expect(entry?.status).toBe('posted');
    expect(entry?.posted_at).toBeTruthy();
    expect(data2.next_index.en).toBe(1);
  });

  // ─────────────────────────────────────────────
  // Test #24: in_flight post failure → rollback
  // ─────────────────────────────────────────────
  it('test_in_flight_post_failure_rolls_back', () => {
    tracker.reserveNextCard('en', 'run-1');
    expect(tracker.getData().next_index.en).toBe(1);

    tracker.rollbackInFlight('staying_up_late_0', 'en');

    const data = tracker.getData();
    expect(data.cards['staying_up_late_0']?.en).toBeUndefined();
    expect(data.next_index.en).toBe(0);
    expect(tracker.getNextUnpostedCard('en')).toBe('staying_up_late_0');
  });

  // ─────────────────────────────────────────────
  // Test #26: in_flight without blotato_post_id → needs_manual_reconcile
  // ─────────────────────────────────────────────
  it('test_in_flight_without_blotato_post_id_goes_to_manual_reconcile', async () => {
    const data = tracker.getData();
    const oneHourAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    data.cards['staying_up_late_0'] = {
      en: {
        status: 'in_flight',
        reserved_at: oneHourAgo,
        run_id: 'old-run',
        posted_at: null,
        blotato_post_id: null,
      },
    };
    data.next_index.en = 1;
    const stalledTracker = new Tracker(data);

    await stalledTracker.recoverStalledInFlights('en', async () => {
      throw new Error('Should not be called when blotato_post_id is null');
    });

    const recovered = stalledTracker.getData();
    expect(recovered.cards['staying_up_late_0']?.en?.status).toBe('needs_manual_reconcile');
  });

  // ─────────────────────────────────────────────
  // Test: in_flight with blotato_post_id + checkStatus returns null → needs_manual_reconcile
  // ─────────────────────────────────────────────
  it('test_in_flight_with_blotato_post_id_unresolvable_goes_to_manual_reconcile', async () => {
    const data = tracker.getData();
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    data.cards['staying_up_late_0'] = {
      en: {
        status: 'in_flight',
        reserved_at: twoHoursAgo,
        run_id: 'old-run',
        posted_at: null,
        blotato_post_id: 'blot-stalled-123',
      },
    };
    data.next_index.en = 1;
    const stalledTracker = new Tracker(data);

    await stalledTracker.recoverStalledInFlights('en', async () => null);

    const recovered = stalledTracker.getData();
    expect(recovered.cards['staying_up_late_0']?.en?.status).toBe('needs_manual_reconcile');
  });

  // ─────────────────────────────────────────────
  // Test #30: reserveNextCard sets in_flight with blotato_post_id: null
  // ─────────────────────────────────────────────
  it('test_reserveNextCard_sets_in_flight', () => {
    const result = tracker.reserveNextCard('en', 'run-42');

    expect(result.cardId).toBe('staying_up_late_0');
    expect(result.cardKey).toBe('staying_up_late_0_en');

    const data = tracker.getData();
    const entry = data.cards['staying_up_late_0']?.en;
    expect(entry?.status).toBe('in_flight');
    expect(entry?.run_id).toBe('run-42');
    expect(entry?.reserved_at).toBeTruthy();
    expect(entry?.blotato_post_id).toBeNull();
    expect(data.next_index.en).toBe(1);
  });

  // ─────────────────────────────────────────────
  // Test: saveBlotatoPostId stores blotato_post_id on in_flight entry
  // ─────────────────────────────────────────────
  it('test_saveBlotatoPostId_stores_on_in_flight_entry', () => {
    tracker.reserveNextCard('en', 'run-1');

    tracker.saveBlotatoPostId('staying_up_late_0', 'en', 'blot-abc-123');

    const data = tracker.getData();
    expect(data.cards['staying_up_late_0']?.en?.blotato_post_id).toBe('blot-abc-123');
    expect(data.cards['staying_up_late_0']?.en?.status).toBe('in_flight');
  });

  // ─────────────────────────────────────────────
  // Test: saveBlotatoPostId throws if not in_flight
  // ─────────────────────────────────────────────
  it('test_saveBlotatoPostId_throws_if_not_in_flight', () => {
    expect(() => tracker.saveBlotatoPostId('staying_up_late_0', 'en', 'blot-123')).toThrow(
      /not in_flight/,
    );
  });

  // ─────────────────────────────────────────────
  // Test #33: needs_manual_reconcile → posted
  // ─────────────────────────────────────────────
  it('test_manual_reconcile_to_posted', () => {
    const data = tracker.getData();
    data.cards['staying_up_late_0'] = {
      en: {
        status: 'needs_manual_reconcile',
        reserved_at: '2026-02-07T08:00:00Z',
        run_id: 'old-run',
        posted_at: null,
        blotato_post_id: 'blot-old',
      },
    };
    data.next_index.en = 1;
    const t = new Tracker(data);

    t.resolveManualReconcile('staying_up_late_0', 'en', 'posted', 'blot-found');

    const resolved = t.getData();
    expect(resolved.cards['staying_up_late_0']?.en?.status).toBe('posted');
    expect(resolved.cards['staying_up_late_0']?.en?.blotato_post_id).toBe('blot-found');
    expect(resolved.next_index.en).toBe(1);
  });

  // ─────────────────────────────────────────────
  // Test #34: needs_manual_reconcile → unposted rollback
  // ─────────────────────────────────────────────
  it('test_manual_reconcile_to_unposted_rollback', () => {
    const data = tracker.getData();
    data.cards['staying_up_late_0'] = {
      en: {
        status: 'needs_manual_reconcile',
        reserved_at: '2026-02-07T08:00:00Z',
        run_id: 'old-run',
        posted_at: null,
        blotato_post_id: 'blot-old',
      },
    };
    data.next_index.en = 1;
    const t = new Tracker(data);

    t.resolveManualReconcile('staying_up_late_0', 'en', 'unposted');

    const resolved = t.getData();
    expect(resolved.cards['staying_up_late_0']?.en).toBeUndefined();
    expect(resolved.next_index.en).toBe(0);
  });

  // ─────────────────────────────────────────────
  // Test #35: in_flight rollback decrements next_index
  // ─────────────────────────────────────────────
  it('test_in_flight_rollback_decrements_next_index', () => {
    tracker.reserveNextCard('en', 'run-1');
    tracker.markAsPosted('staying_up_late_0', 'en');
    tracker.reserveNextCard('en', 'run-2');
    expect(tracker.getData().next_index.en).toBe(2);

    tracker.rollbackInFlight('staying_up_late_1', 'en');

    expect(tracker.getData().next_index.en).toBe(1);
    expect(tracker.getNextUnpostedCard('en')).toBe('staying_up_late_1');
  });

  // ─────────────────────────────────────────────
  // Test #36: reserve blocked when manual reconcile exists
  // ─────────────────────────────────────────────
  it('test_reserve_blocked_when_manual_reconcile_exists', () => {
    const data = tracker.getData();
    data.cards['staying_up_late_0'] = {
      en: {
        status: 'needs_manual_reconcile',
        reserved_at: '2026-02-07T08:00:00Z',
        run_id: 'old-run',
        posted_at: null,
        blotato_post_id: null,
      },
    };
    data.next_index.en = 1;
    const t = new Tracker(data);

    expect(() => t.reserveNextCard('en', 'run-new')).toThrow(
      /manual.*reconcile/i,
    );
  });

  // ─────────────────────────────────────────────
  // Test: blotato_post_id saved → Phase 2 failure → in_flight preserved
  // ─────────────────────────────────────────────
  it('test_blotato_post_id_preserved_after_phase2_failure', () => {
    tracker.reserveNextCard('en', 'run-1');
    tracker.saveBlotatoPostId('staying_up_late_0', 'en', 'blot-phase2-fail');

    const data = tracker.getData();
    const entry = data.cards['staying_up_late_0']?.en;

    expect(entry?.status).toBe('in_flight');
    expect(entry?.blotato_post_id).toBe('blot-phase2-fail');
  });

  // ─────────────────────────────────────────────
  // Test: reserve blocked when in_flight already exists
  // ─────────────────────────────────────────────
  it('test_reserve_blocked_when_in_flight_exists', () => {
    const data = tracker.getData();
    data.cards['staying_up_late_0'] = {
      en: {
        status: 'in_flight',
        reserved_at: new Date().toISOString(),
        run_id: 'old-run',
        posted_at: null,
        blotato_post_id: 'blot-phase2-fail',
      },
    };
    data.next_index.en = 1;
    const t = new Tracker(data);

    expect(() => t.reserveNextCard('en', 'run-new')).toThrow(
      /in_flight.*already exists/i,
    );
  });

  // ─────────────────────────────────────────────
  // Test #31: TTL recovery with blotato_post_id + found post → posted
  // ─────────────────────────────────────────────
  it('test_ttl_recovery_with_blotato_post_id_resolves_found_post_to_posted', async () => {
    const data = tracker.getData();
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    data.cards['staying_up_late_0'] = {
      en: {
        status: 'in_flight',
        reserved_at: twoHoursAgo,
        run_id: 'old-run',
        posted_at: null,
        blotato_post_id: 'blot-recovered-456',
      },
    };
    data.next_index.en = 1;
    const t = new Tracker(data);

    await t.recoverStalledInFlights('en', async (blotatoPostId) => {
      expect(blotatoPostId).toBe('blot-recovered-456');
      return { status: 'published', publicUrl: 'https://tiktok.com/abc' };
    });

    const recovered = t.getData();
    expect(recovered.cards['staying_up_late_0']?.en?.status).toBe('posted');
  });

  // ─────────────────────────────────────────────
  // Test #32: TTL recovery — non-terminal status → needs_manual_reconcile (catch-all)
  // ─────────────────────────────────────────────
  it('test_ttl_recovery_non_terminal_status_goes_to_needs_manual_reconcile', async () => {
    const data = tracker.getData();
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    data.cards['staying_up_late_0'] = {
      en: {
        status: 'in_flight',
        reserved_at: twoHoursAgo,
        run_id: 'old-run',
        posted_at: null,
        blotato_post_id: 'blot-processing',
      },
    };
    data.next_index.en = 1;
    const t = new Tracker(data);

    await t.recoverStalledInFlights('en', async () => {
      return { status: 'processing', publicUrl: null };
    });

    const recovered = t.getData();
    expect(recovered.cards['staying_up_late_0']?.en?.status).toBe('needs_manual_reconcile');
  });

  // ─────────────────────────────────────────────
  // Test #33: TTL recovery — FAILED status → needs_manual_reconcile
  // ─────────────────────────────────────────────
  it('test_ttl_recovery_failed_status_becomes_needs_manual_reconcile', async () => {
    const data = tracker.getData();
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    data.cards['staying_up_late_0'] = {
      en: {
        status: 'in_flight',
        reserved_at: twoHoursAgo,
        run_id: 'old-run',
        posted_at: null,
        blotato_post_id: 'blot-failed',
      },
    };
    data.next_index.en = 1;
    const t = new Tracker(data);

    await t.recoverStalledInFlights('en', async () => {
      return { status: 'failed', publicUrl: null };
    });

    const recovered = t.getData();
    expect(recovered.cards['staying_up_late_0']?.en?.status).toBe('needs_manual_reconcile');
  });

  // ─────────────────────────────────────────────
  // Test #34: TTL recovery — null checkStatus → needs_manual_reconcile
  // ─────────────────────────────────────────────
  it('test_ttl_recovery_null_checkstatus_becomes_needs_manual_reconcile', async () => {
    const data = tracker.getData();
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    data.cards['staying_up_late_0'] = {
      en: {
        status: 'in_flight',
        reserved_at: twoHoursAgo,
        run_id: 'old-run',
        posted_at: null,
        blotato_post_id: 'blot-unknown',
      },
    };
    data.next_index.en = 1;
    const t = new Tracker(data);

    await t.recoverStalledInFlights('en', async () => null);

    const recovered = t.getData();
    expect(recovered.cards['staying_up_late_0']?.en?.status).toBe('needs_manual_reconcile');
  });

  // ─────────────────────────────────────────────
  // Test: TTL recovery — published without publicUrl → needs_manual_reconcile
  // ─────────────────────────────────────────────
  it('test_ttl_recovery_published_without_publicUrl_goes_to_needs_manual_reconcile', async () => {
    const data = tracker.getData();
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    data.cards['staying_up_late_0'] = {
      en: {
        status: 'in_flight',
        reserved_at: twoHoursAgo,
        run_id: 'old-run',
        posted_at: null,
        blotato_post_id: 'blot-no-url',
      },
    };
    data.next_index.en = 1;
    const t = new Tracker(data);

    await t.recoverStalledInFlights('en', async () => {
      return { status: 'published', publicUrl: null };
    });

    const recovered = t.getData();
    expect(recovered.cards['staying_up_late_0']?.en?.status).toBe('needs_manual_reconcile');
  });

  // ─────────────────────────────────────────────
  // Test: TTL recovery — checkStatus throws → needs_manual_reconcile
  // ─────────────────────────────────────────────
  it('test_ttl_recovery_checkstatus_throws_goes_to_needs_manual_reconcile', async () => {
    const data = tracker.getData();
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    data.cards['staying_up_late_0'] = {
      en: {
        status: 'in_flight',
        reserved_at: twoHoursAgo,
        run_id: 'old-run',
        posted_at: null,
        blotato_post_id: 'blot-error',
      },
    };
    data.next_index.en = 1;
    const t = new Tracker(data);

    await t.recoverStalledInFlights('en', async () => {
      throw new Error('API unreachable');
    });

    const recovered = t.getData();
    expect(recovered.cards['staying_up_late_0']?.en?.status).toBe('needs_manual_reconcile');
  });
});
