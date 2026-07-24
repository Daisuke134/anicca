-- PHASE C / PC-1 (C3 ask→remember): per-user remembered locations so a recurring vague event
-- ("Lunch with Mai", "おばあちゃんの家") is asked ONCE then auto-filled from memory on the next same-summary
-- event. Keyed by (uid, phrase) where phrase = a deterministic normalization of the event summary
-- (bookkeeping, not a judgment). Supabase (NOT mem0) — pooled-compatible, no new dependency. Re-runnable.

CREATE TABLE IF NOT EXISTS public.lm_user_places (
  uid        text        NOT NULL,
  phrase     text        NOT NULL,             -- normalized event summary (lowercase, collapsed whitespace)
  address    text        NOT NULL,             -- the resolved/answered location to reuse
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (uid, phrase)                         -- one remembered place per (user, phrase); upsert on conflict
);
CREATE INDEX IF NOT EXISTS lm_user_places_uid_idx ON public.lm_user_places (uid);

-- RLS: the ask/reply loops use the service-role key (bypasses RLS); enable it so the anon key can't read.
ALTER TABLE public.lm_user_places ENABLE ROW LEVEL SECURITY;
