-- CFO-1g2: one delivery claim and one provider receipt per Telegram delivery.
ALTER TABLE public.lm_cfo_daily_snapshots
  ADD CONSTRAINT lm_cfo_daily_snapshots_owner_date_revision_ref_unique
  UNIQUE (uid, reporting_date, revision, public_ref);

CREATE TABLE IF NOT EXISTS public.lm_cfo_telegram_delivery_claims (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  public_ref uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE CHECK (public_ref <> '00000000-0000-0000-0000-000000000000'::uuid),
  uid text NOT NULL REFERENCES public.lm_users(uid),
  report_kind text NOT NULL CHECK (report_kind <> ''),
  reporting_date date NOT NULL,
  revision integer NOT NULL CHECK (revision > 0),
  snapshot_public_ref uuid NOT NULL CHECK (snapshot_public_ref <> '00000000-0000-0000-0000-000000000000'::uuid),
  created_at timestamptz NOT NULL DEFAULT statement_timestamp(),
  CONSTRAINT lm_cfo_telegram_delivery_claims_delivery_key_unique UNIQUE (uid, report_kind, reporting_date, revision),
  CONSTRAINT lm_cfo_telegram_delivery_claims_snapshot_fk
    FOREIGN KEY (uid, reporting_date, revision, snapshot_public_ref)
    REFERENCES public.lm_cfo_daily_snapshots (uid, reporting_date, revision, public_ref)
);

CREATE TABLE IF NOT EXISTS public.lm_cfo_telegram_delivery_receipts (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  public_ref uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE CHECK (public_ref <> '00000000-0000-0000-0000-000000000000'::uuid),
  claim_public_ref uuid NOT NULL UNIQUE REFERENCES public.lm_cfo_telegram_delivery_claims (public_ref),
  message_id bigint NOT NULL CHECK (message_id > 0),
  created_at timestamptz NOT NULL DEFAULT statement_timestamp()
);

ALTER TABLE public.lm_cfo_telegram_delivery_claims ENABLE ROW LEVEL SECURITY;
CREATE POLICY lm_cfo_telegram_delivery_claims_service_select ON public.lm_cfo_telegram_delivery_claims FOR SELECT TO service_role USING (true);
CREATE POLICY lm_cfo_telegram_delivery_claims_service_insert ON public.lm_cfo_telegram_delivery_claims FOR INSERT TO service_role WITH CHECK (true);
REVOKE ALL ON TABLE public.lm_cfo_telegram_delivery_claims FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.lm_cfo_telegram_delivery_claims TO service_role;
REVOKE UPDATE, DELETE ON TABLE public.lm_cfo_telegram_delivery_claims FROM service_role;
GRANT USAGE, SELECT ON SEQUENCE public.lm_cfo_telegram_delivery_claims_id_seq TO service_role;

ALTER TABLE public.lm_cfo_telegram_delivery_receipts ENABLE ROW LEVEL SECURITY;
CREATE POLICY lm_cfo_telegram_delivery_receipts_service_select ON public.lm_cfo_telegram_delivery_receipts FOR SELECT TO service_role USING (true);
CREATE POLICY lm_cfo_telegram_delivery_receipts_service_insert ON public.lm_cfo_telegram_delivery_receipts FOR INSERT TO service_role WITH CHECK (true);
REVOKE ALL ON TABLE public.lm_cfo_telegram_delivery_receipts FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT ON TABLE public.lm_cfo_telegram_delivery_receipts TO service_role;
REVOKE UPDATE, DELETE ON TABLE public.lm_cfo_telegram_delivery_receipts FROM service_role;
GRANT USAGE, SELECT ON SEQUENCE public.lm_cfo_telegram_delivery_receipts_id_seq TO service_role;

CREATE OR REPLACE FUNCTION public.reject_lm_cfo_telegram_delivery_mutation()
RETURNS trigger LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp
AS $$
BEGIN
  RAISE EXCEPTION 'lm_cfo_telegram_delivery is append-only' USING ERRCODE = '55000';
END;
$$;
DROP TRIGGER IF EXISTS lm_cfo_telegram_delivery_claims_append_only ON public.lm_cfo_telegram_delivery_claims;
CREATE TRIGGER lm_cfo_telegram_delivery_claims_append_only BEFORE UPDATE OR DELETE ON public.lm_cfo_telegram_delivery_claims
FOR EACH ROW EXECUTE FUNCTION public.reject_lm_cfo_telegram_delivery_mutation();
DROP TRIGGER IF EXISTS lm_cfo_telegram_delivery_receipts_append_only ON public.lm_cfo_telegram_delivery_receipts;
CREATE TRIGGER lm_cfo_telegram_delivery_receipts_append_only BEFORE UPDATE OR DELETE ON public.lm_cfo_telegram_delivery_receipts
FOR EACH ROW EXECUTE FUNCTION public.reject_lm_cfo_telegram_delivery_mutation();
REVOKE ALL ON FUNCTION public.reject_lm_cfo_telegram_delivery_mutation() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.reject_lm_cfo_telegram_delivery_mutation() TO service_role;

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

CREATE OR REPLACE FUNCTION public.lm_record_cfo_telegram_delivery(p_claim_public_ref uuid, p_message_id bigint)
RETURNS jsonb LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp
AS $$
DECLARE
  claim_row public.lm_cfo_telegram_delivery_claims%ROWTYPE;
  recorded public.lm_cfo_telegram_delivery_receipts%ROWTYPE;
BEGIN
  IF p_claim_public_ref IS NULL OR p_message_id IS NULL OR p_message_id <= 0 THEN
    RAISE EXCEPTION 'cfo_telegram_delivery_receipt_invalid' USING ERRCODE = '22023';
  END IF;
  SELECT * INTO claim_row FROM public.lm_cfo_telegram_delivery_claims WHERE public_ref = p_claim_public_ref;
  IF claim_row.id IS NULL THEN
    RAISE EXCEPTION 'cfo_telegram_delivery_claim_not_found' USING ERRCODE = '22023';
  END IF;
  INSERT INTO public.lm_cfo_telegram_delivery_receipts (claim_public_ref, message_id)
  VALUES (p_claim_public_ref, p_message_id)
  ON CONFLICT DO NOTHING RETURNING * INTO recorded;
  IF recorded.id IS NULL THEN
    SELECT * INTO recorded FROM public.lm_cfo_telegram_delivery_receipts WHERE claim_public_ref = p_claim_public_ref;
    IF recorded.message_id IS DISTINCT FROM p_message_id THEN
      RAISE EXCEPTION 'provider_receipt_conflict' USING ERRCODE = '23505';
    END IF;
  END IF;
  RETURN jsonb_build_object(
    'public_ref', recorded.public_ref,
    'claim_public_ref', recorded.claim_public_ref,
    'message_id', recorded.message_id,
    'created_at', recorded.created_at
  );
END;
$$;
REVOKE ALL ON FUNCTION public.lm_record_cfo_telegram_delivery(uuid, bigint) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.lm_record_cfo_telegram_delivery(uuid, bigint) TO service_role;
