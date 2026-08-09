REVOKE ALL ON TABLE public.lm_cfo_daily_snapshots FROM service_role;
GRANT SELECT, INSERT ON TABLE public.lm_cfo_daily_snapshots TO service_role;
REVOKE ALL ON TABLE public.lm_cfo_daily_snapshots FROM PUBLIC, anon, authenticated;
