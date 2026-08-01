CREATE TABLE IF NOT EXISTS public.lm_event_participations (
  participation_id text PRIMARY KEY CHECK (participation_id ~ '^event-participation:[0-9a-f]{64}$'),
  tenant_id text NOT NULL CHECK (tenant_id ~ '^[a-z0-9][a-z0-9._-]{0,199}$'),
  event_ref text NOT NULL CHECK (char_length(event_ref) BETWEEN 10 AND 1000),
  event_start_at timestamptz NOT NULL,
  kind text NOT NULL CHECK (kind IN ('audience_registration', 'talk_application')),
  state text NOT NULL DEFAULT 'discovered',
  availability text,
  talk_format text,
  action_ref text CHECK (action_ref IS NULL OR char_length(action_ref) BETWEEN 10 AND 1000),
  evidence_ref text NOT NULL CHECK (
    char_length(evidence_ref) BETWEEN 10 AND 1000
    AND evidence_ref LIKE 'evidence://event/%'
  ),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (tenant_id, event_ref, event_start_at, kind),
  CHECK (
    (
      kind = 'audience_registration'
      AND state IN ('discovered', 'registration_queued', 'registered', 'waitlist', 'cancelled')
      AND availability IS NULL
      AND talk_format IS NULL
      AND action_ref = event_ref
    )
    OR
    (
      kind = 'talk_application'
      AND state IN ('discovered', 'submission_queued', 'submitted', 'accepted', 'rejected', 'withdrawn', 'presented')
      AND availability IN ('open', 'closed', 'invite_only', 'not_offered', 'unknown')
      AND talk_format IN ('lightning_talk', 'cfp', 'demo', 'pitch', 'workshop', 'other')
      AND ((availability = 'open' AND action_ref IS NOT NULL) OR (availability <> 'open' AND action_ref IS NULL))
    )
  )
);

CREATE INDEX IF NOT EXISTS lm_event_participations_tenant_state_idx
  ON public.lm_event_participations (tenant_id, kind, state, event_start_at);

ALTER TABLE public.lm_event_participations ENABLE ROW LEVEL SECURITY;
