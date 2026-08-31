DO $$
DECLARE constraint_name text;
BEGIN
  SELECT conname INTO constraint_name
  FROM pg_constraint
  WHERE conrelid = 'public.lm_event_participations'::regclass
    AND contype = 'c'
    AND pg_get_constraintdef(oid) LIKE '%submission_queued%';
  IF constraint_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE public.lm_event_participations DROP CONSTRAINT %I', constraint_name);
  END IF;
END;
$$;

ALTER TABLE public.lm_event_participations
  ADD CONSTRAINT lm_event_participations_state_graph_check CHECK (
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
      AND state IN (
        'discovered', 'application_ready', 'submission_queued', 'submitted',
        'provider_verified', 'accepted', 'rejected', 'withdrawn', 'presented'
      )
      AND availability IN ('open', 'closed', 'invite_only', 'not_offered', 'unknown')
      AND talk_format IN ('lightning_talk', 'cfp', 'demo', 'pitch', 'workshop', 'other')
      AND ((availability = 'open' AND action_ref IS NOT NULL) OR (availability <> 'open' AND action_ref IS NULL))
    )
  );

DO $$
DECLARE constraint_name text;
BEGIN
  SELECT conname INTO constraint_name
  FROM pg_constraint
  WHERE conrelid = 'public.lm_talk_application_transitions'::regclass
    AND contype = 'c'
    AND pg_get_constraintdef(oid) LIKE '%submission_queued%';
  IF constraint_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE public.lm_talk_application_transitions DROP CONSTRAINT %I', constraint_name);
  END IF;
END;
$$;

ALTER TABLE public.lm_talk_application_transitions
  ADD CONSTRAINT lm_talk_application_transition_growth_graph_check CHECK (
    (from_state = 'discovered' AND to_state IN ('application_ready', 'submission_queued'))
    OR (from_state = 'application_ready' AND to_state IN ('submitted', 'withdrawn'))
    OR (from_state = 'submission_queued' AND to_state IN ('submitted', 'withdrawn'))
    OR (from_state = 'submitted' AND to_state IN ('provider_verified', 'accepted', 'rejected', 'withdrawn'))
    OR (from_state = 'provider_verified' AND to_state IN ('accepted', 'rejected', 'withdrawn'))
    OR (from_state = 'accepted' AND to_state IN ('presented', 'withdrawn'))
  );
