-- Widen only the existing lm_travel_log.leg CHECK for Telegram claim legs.
-- The ledger table, rows, unique key, and RLS policy remain unchanged.
DO $$
DECLARE
  old_constraint record;
BEGIN
  FOR old_constraint IN
    SELECT c.conname
      FROM pg_constraint AS c
     WHERE c.conrelid = 'public.lm_travel_log'::regclass
       AND c.contype = 'c'
       AND c.conkey = ARRAY[(
         SELECT a.attnum
           FROM pg_attribute AS a
          WHERE a.attrelid = 'public.lm_travel_log'::regclass
            AND a.attname = 'leg'
            AND NOT a.attisdropped
       )]::smallint[]
  LOOP
    EXECUTE format('ALTER TABLE public.lm_travel_log DROP CONSTRAINT %I', old_constraint.conname);
  END LOOP;

  EXECUTE $migration$
    ALTER TABLE public.lm_travel_log
      ADD CONSTRAINT lm_travel_log_leg_check
      CHECK (leg IN ('go', 'return', 'telegram-t5', 'trial-upgrade')) NOT VALID
  $migration$;
END;
$$;

ALTER TABLE public.lm_travel_log
  VALIDATE CONSTRAINT lm_travel_log_leg_check;
