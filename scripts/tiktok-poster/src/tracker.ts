import type {
  TrackerData,
  Language,
  CardEntry,
  ReserveResult,
  ReconcileResolution,
} from './types.js';

const IN_FLIGHT_TTL_MS = 60 * 60 * 1000; // 1 hour

/** Check post status by blotato_post_id. Returns { status, publicUrl } or null. */
type CheckStatusFn = (
  blotatoPostId: string,
) => Promise<{ status: string; publicUrl: string | null } | null>;

export class Tracker {
  private data: TrackerData;

  constructor(data: TrackerData) {
    this.data = structuredClone(data);
  }

  getData(): TrackerData {
    return structuredClone(this.data);
  }

  /** Returns the next card_id to post for the given language, or null if all posted */
  getNextUnpostedCard(language: Language): string | null {
    const idx = this.data.next_index[language];
    if (idx >= this.data.card_order.length) return null;
    return this.data.card_order[idx];
  }

  /** Returns true if all cards have been posted for the given language */
  allCardsPosted(language: Language): boolean {
    return this.data.next_index[language] >= this.data.card_order.length;
  }

  /** Fail-fast guard: throws if any needs_manual_reconcile or in_flight exists for the language */
  private guardBeforeReserve(language: Language): void {
    for (const cardId of Object.keys(this.data.cards)) {
      const entry = this.data.cards[cardId]?.[language];
      if (entry?.status === 'needs_manual_reconcile') {
        throw new Error(
          `Cannot reserve: manual reconcile pending for ${cardId} (${language}). ` +
          `Resolve all needs_manual_reconcile entries before continuing.`,
        );
      }
      if (entry?.status === 'in_flight') {
        throw new Error(
          `Cannot reserve: in_flight already exists for ${cardId} (${language}). ` +
          `Complete or recover the existing in_flight before reserving a new card.`,
        );
      }
    }
  }

  /** Stage 1: Reserve the next card as in_flight and increment next_index */
  reserveNextCard(language: Language, runId: string): ReserveResult {
    this.guardBeforeReserve(language);

    const cardId = this.getNextUnpostedCard(language);
    if (!cardId) {
      throw new Error(`All cards posted for ${language}`);
    }

    const entry: CardEntry = {
      status: 'in_flight',
      reserved_at: new Date().toISOString(),
      run_id: runId,
      posted_at: null,
      blotato_post_id: null,
    };

    if (!this.data.cards[cardId]) {
      this.data.cards[cardId] = {};
    }
    this.data.cards[cardId][language] = entry;
    this.data.next_index[language]++;

    return {
      cardId,
      cardKey: `${cardId}_${language}`,
    };
  }

  /** Save blotato_post_id on an in_flight entry (called after postPhoto, before polling) */
  saveBlotatoPostId(cardId: string, language: Language, blotatoPostId: string): void {
    const entry = this.data.cards[cardId]?.[language];
    if (!entry || entry.status !== 'in_flight') {
      throw new Error(`Card ${cardId}/${language} is not in_flight (status: ${entry?.status})`);
    }
    entry.blotato_post_id = blotatoPostId;
  }

  /** Stage 2 success: Transition in_flight → posted */
  markAsPosted(cardId: string, language: Language): void {
    const entry = this.data.cards[cardId]?.[language];
    if (!entry || entry.status !== 'in_flight') {
      throw new Error(`Card ${cardId}/${language} is not in_flight (status: ${entry?.status})`);
    }

    entry.status = 'posted';
    entry.posted_at = new Date().toISOString();
  }

  /** Stage 2 failure: Delete in_flight entry and decrement next_index */
  rollbackInFlight(cardId: string, language: Language): void {
    const entry = this.data.cards[cardId]?.[language];
    if (!entry || entry.status !== 'in_flight') {
      throw new Error(`Card ${cardId}/${language} is not in_flight (status: ${entry?.status})`);
    }

    delete this.data.cards[cardId]![language];
    if (Object.keys(this.data.cards[cardId] ?? {}).length === 0) {
      delete this.data.cards[cardId];
    }
    this.data.next_index[language]--;
  }

  /**
   * Recover stalled in_flight entries (TTL exceeded).
   * Uses blotato_post_id + GET /v2/posts/{id} for recovery.
   * Entries without blotato_post_id go directly to needs_manual_reconcile.
   * Unknown/non-terminal statuses also go to needs_manual_reconcile (prevent in_flight lockup).
   */
  async recoverStalledInFlights(
    language: Language,
    checkStatus: CheckStatusFn,
  ): Promise<void> {
    const now = Date.now();

    for (const cardId of Object.keys(this.data.cards)) {
      const entry = this.data.cards[cardId]?.[language];
      if (!entry || entry.status !== 'in_flight') continue;

      const reservedAt = new Date(entry.reserved_at!).getTime();
      if (now - reservedAt < IN_FLIGHT_TTL_MS) continue;

      // TTL exceeded — attempt recovery via blotato_post_id
      const blotatoPostId = entry.blotato_post_id;

      if (!blotatoPostId) {
        // No blotato_post_id (crash before postPhoto completed)
        entry.status = 'needs_manual_reconcile';
        continue;
      }

      let result: { status: string; publicUrl: string | null } | null;
      try {
        result = await checkStatus(blotatoPostId);
      } catch {
        entry.status = 'needs_manual_reconcile';
        continue;
      }

      if (result && result.status === 'published' && result.publicUrl) {
        // Post was actually published — fix tracker
        entry.status = 'posted';
        entry.posted_at = new Date().toISOString();
      } else {
        // failed, unknown status, null result, or no publicUrl
        // → needs_manual_reconcile (prevents in_flight lockup)
        entry.status = 'needs_manual_reconcile';
      }
    }
  }

  /** Manual resolution of needs_manual_reconcile entries */
  resolveManualReconcile(
    cardId: string,
    language: Language,
    resolution: ReconcileResolution,
    blotatoPostId?: string,
  ): void {
    const entry = this.data.cards[cardId]?.[language];
    if (!entry || entry.status !== 'needs_manual_reconcile') {
      throw new Error(
        `Card ${cardId}/${language} is not in needs_manual_reconcile (status: ${entry?.status})`,
      );
    }

    if (resolution === 'posted') {
      entry.status = 'posted';
      entry.posted_at = new Date().toISOString();
      if (blotatoPostId) {
        entry.blotato_post_id = blotatoPostId;
      }
    } else {
      // Confirmed NOT posted — delete and rollback next_index
      const cardIndex = this.data.card_order.indexOf(cardId);
      delete this.data.cards[cardId]![language];
      if (Object.keys(this.data.cards[cardId] ?? {}).length === 0) {
        delete this.data.cards[cardId];
      }
      if (cardIndex >= 0) {
        this.data.next_index[language] = cardIndex;
      }
    }
  }
}
