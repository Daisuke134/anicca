-- CFO-1g2: forward-deploy the fail-closed snapshot identity check.
CREATE OR REPLACE FUNCTION public.lm_claim_cfo_telegram_delivery(
  p_uid text, p_snapshot_public_ref uuid, p_report_kind text, p_reporting_date date, p_revision integer
)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp
AS $$
DECLARE
  claimed public.lm_cfo_telegram_delivery_claims%ROWTYPE;
  decision text;
BEGIN
  IF p_uid IS NULL OR p_uid = '' OR p_report_kind IS NULL OR p_report_kind = ''
    OR p_snapshot_public_ref IS NULL OR p_snapshot_public_ref = '00000000-0000-0000-0000-000000000000'::uuid
    OR p_reporting_date IS NULL OR p_revision IS NULL OR p_revision <= 0 THEN
    RAISE EXCEPTION 'cfo_telegram_delivery_claim_invalid' USING ERRCODE = '22023';
  END IF;
  INSERT INTO public.lm_cfo_telegram_delivery_claims (uid, report_kind, reporting_date, revision, snapshot_public_ref)
  VALUES (p_uid, p_report_kind, p_reporting_date, p_revision, p_snapshot_public_ref)
  ON CONFLICT DO NOTHING RETURNING * INTO claimed;
  IF claimed.id IS NOT NULL THEN
    decision := 'send';
  ELSE
    SELECT * INTO claimed FROM public.lm_cfo_telegram_delivery_claims
    WHERE uid = p_uid AND report_kind = p_report_kind AND reporting_date = p_reporting_date AND revision = p_revision;
    IF claimed.id IS NULL THEN
      RAISE EXCEPTION 'cfo_telegram_delivery_claim_unavailable' USING ERRCODE = '40001';
    END IF;
    IF claimed.snapshot_public_ref IS DISTINCT FROM p_snapshot_public_ref THEN
      RAISE EXCEPTION 'cfo_telegram_delivery_claim_snapshot_mismatch' USING ERRCODE = '22023';
    END IF;
    IF EXISTS (
      SELECT 1 FROM public.lm_cfo_telegram_delivery_receipts WHERE claim_public_ref = claimed.public_ref
    ) THEN
      decision := 'sent';
    ELSE
      decision := 'reconcile';
    END IF;
  END IF;
  RETURN jsonb_build_object(
    'public_ref', claimed.public_ref,
    'decision', decision,
    'reporting_date', claimed.reporting_date,
    'revision', claimed.revision,
    'created_at', claimed.created_at
  );
END;
$$;
REVOKE ALL ON FUNCTION public.lm_claim_cfo_telegram_delivery(text, uuid, text, date, integer) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lm_claim_cfo_telegram_delivery(text, uuid, text, date, integer) TO service_role;
