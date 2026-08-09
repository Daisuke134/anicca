REVOKE ALL ON SEQUENCE public.lm_cfo_daily_snapshots_id_seq FROM PUBLIC, anon, authenticated, service_role;
GRANT USAGE, SELECT ON SEQUENCE public.lm_cfo_daily_snapshots_id_seq TO service_role;
