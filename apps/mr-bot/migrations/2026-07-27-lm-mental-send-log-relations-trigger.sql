DO $$
DECLARE
  names text[];
  found int;
BEGIN
  SELECT array_agg(conname ORDER BY conname) INTO names
  FROM pg_constraint
  WHERE conrelid = 'public.lm_mental_send_log'::regclass
    AND contype = 'c'
    AND pg_get_constraintdef(oid) ILIKE '%pre_sleep%';
  found := coalesce(array_length(names, 1), 0);
  IF found <> 1 THEN
    RAISE EXCEPTION
      'lm_mental_send_log: expected exactly 1 CHECK constraint mentioning pre_sleep, found %: [%]',
      found, coalesce(array_to_string(names, ', '), '');
  END IF;
  EXECUTE format('ALTER TABLE public.lm_mental_send_log DROP CONSTRAINT %I', names[1]);
END $$;

ALTER TABLE public.lm_mental_send_log
  ADD CONSTRAINT lm_mental_send_log_trigger_check
  CHECK (trigger IN (
    'pre_event', 'between_events', 'pre_sleep', 'precepts', 'precepts_mirror', 'relations'
  ));
