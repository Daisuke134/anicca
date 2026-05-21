export type Language = 'en' | 'ja';
export type CardStatus = 'in_flight' | 'posted' | 'needs_manual_reconcile';

export interface CardEntry {
  status: CardStatus;
  reserved_at: string | null;
  run_id: string | null;
  posted_at: string | null;
  blotato_post_id: string | null;
}

export interface TrackerData {
  version: number;
  cards: Record<string, Partial<Record<Language, CardEntry>>>;
  next_index: Record<Language, number>;
  card_order: string[];
}

export interface ReserveResult {
  cardId: string;
  cardKey: string;
}

export type ReconcileResolution = 'posted' | 'unposted';
