-- O1C-18: one tenant-bound snapshot for the authenticated fundraising funnel.

CREATE OR REPLACE FUNCTION public.lm_panel_fundraising_funnel(p_uid text)
RETURNS jsonb
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
DECLARE
  snapshot jsonb;
BEGIN
  IF p_uid IS NULL OR p_uid !~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$' THEN
    RAISE EXCEPTION 'invalid fundraising funnel tenant';
  END IF;

  WITH sources AS (
    SELECT tenant_id, ledger_id, funder_id, mail_thread_id, submitted_at
    FROM public.lm_funder_submission_ledger
    WHERE tenant_id = p_uid
  ), events AS (
    SELECT source.funder_id, source.ledger_id AS source_id,
      'application'::text AS event_kind, source.submitted_at AS occurred_at,
      1 AS stage_order
    FROM sources AS source
    UNION ALL
    SELECT source.funder_id, source.ledger_id AS source_id,
      CASE result.status
        WHEN 'confirmed' THEN 'confirmation'
        WHEN 'meeting_requested' THEN 'interview'
        WHEN 'offer_received' THEN 'offer'
        WHEN 'rejected' THEN 'rejected'
        WHEN 'funded' THEN 'funded'
      END AS event_kind,
      result.occurred_at,
      CASE result.status
        WHEN 'confirmed' THEN 2
        WHEN 'meeting_requested' THEN 3
        WHEN 'offer_received' THEN 4
        WHEN 'rejected' THEN 5
        WHEN 'funded' THEN 6
      END AS stage_order
    FROM public.lm_outbound_result_ledger AS result
    JOIN sources AS source
      ON source.tenant_id = result.tenant_id
     AND source.ledger_id = result.source_id
     AND source.funder_id = result.entity_id
     AND source.mail_thread_id = result.provider_thread_id
    WHERE result.organ = 'fundraising'
      AND result.workflow = 'funder_application'
      AND result.source_kind = 'funder_submission'
      AND result.status IN (
        'confirmed', 'meeting_requested', 'offer_received', 'rejected', 'funded'
      )
  )
  SELECT jsonb_build_object(
    'schema_version', 1,
    'events', COALESCE(jsonb_agg(jsonb_build_object(
      'funder_id', funder_id,
      'source_id', source_id,
      'event_kind', event_kind,
      'occurred_at', occurred_at
    ) ORDER BY source_id, occurred_at, stage_order), '[]'::jsonb)
  ) INTO snapshot
  FROM events;

  RETURN snapshot;
END
$$;

REVOKE ALL ON FUNCTION public.lm_panel_fundraising_funnel(text) FROM PUBLIC;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON FUNCTION public.lm_panel_fundraising_funnel(text) FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON FUNCTION public.lm_panel_fundraising_funnel(text) FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.lm_panel_fundraising_funnel(text) TO service_role';
  END IF;
END
$$;
