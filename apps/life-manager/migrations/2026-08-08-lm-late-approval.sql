-- DAILY #5: durable late-notice approval ledger.
--
-- The draft row is the immutable user-visible snapshot.  Decisions, claims, and provider receipts
-- are separate append-only ledgers so a retry can never rewrite the evidence that was shown before
-- the user tapped a button.  All transitions below lock the draft row with FOR UPDATE.

CREATE TABLE IF NOT EXISTS public.lm_late_approval_drafts (
  draft_id text PRIMARY KEY DEFAULT md5(clock_timestamp()::text || random()::text || txid_current()::text),
  uid text NOT NULL CHECK (char_length(uid) BETWEEN 1 AND 256),
  event_key text NOT NULL CHECK (char_length(event_key) BETWEEN 1 AND 512),
  status text NOT NULL DEFAULT 'draft' CHECK (
    status IN (
      'draft', 'awaiting_decision', 'send_claimed', 'sent', 'do_not_send',
      'recipient_missing', 'recipient_ambiguous'
    )
  ),
  recipient_status text NOT NULL CHECK (
    recipient_status IN ('resolved', 'recipient_missing', 'recipient_ambiguous')
  ),
  recipient_snapshot jsonb NOT NULL CHECK (
    jsonb_typeof(recipient_snapshot) = 'array'
    AND (
      recipient_status <> 'resolved'
      OR jsonb_array_length(recipient_snapshot) > 0
    )
  ),
  evidence_snapshot jsonb NOT NULL CHECK (jsonb_typeof(evidence_snapshot) IN ('array', 'object')),
  body_snapshot text NOT NULL CHECK (char_length(body_snapshot) BETWEEN 1 AND 64000),
  eta_evidence_snapshot jsonb NOT NULL CHECK (jsonb_typeof(eta_evidence_snapshot) IN ('array', 'object')),
  decision text CHECK (decision IN ('send', 'do_not_send')),
  idempotency_key text CHECK (idempotency_key IS NULL OR char_length(idempotency_key) BETWEEN 1 AND 512),
  claim_token text,
  claim_worker_id text,
  claim_acquired_at timestamptz,
  claim_expires_at timestamptz,
  provider_message_id text,
  delivered_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (uid, event_key),
  CHECK (
    (recipient_status = 'resolved' AND status IN ('draft', 'awaiting_decision', 'send_claimed', 'sent', 'do_not_send'))
    OR (recipient_status = 'recipient_missing' AND status = 'recipient_missing')
    OR (recipient_status = 'recipient_ambiguous' AND status = 'recipient_ambiguous')
  ),
  CHECK (
    (status IN ('draft', 'awaiting_decision') AND decision IS NULL)
    OR (status = 'awaiting_decision' AND decision = 'send')
    OR (status = 'do_not_send' AND decision = 'do_not_send')
    OR (status IN ('send_claimed', 'sent') AND decision = 'send')
    OR (status IN ('recipient_missing', 'recipient_ambiguous') AND decision IS NULL)
  ),
  CHECK (
    status NOT IN ('send_claimed', 'sent')
    OR (claim_token IS NOT NULL AND claim_worker_id IS NOT NULL AND claim_acquired_at IS NOT NULL)
  ),
  CHECK (
    status <> 'sent'
    OR (provider_message_id IS NOT NULL AND delivered_at IS NOT NULL)
  ),
  CHECK (
    status <> 'do_not_send'
    OR (claim_token IS NULL AND provider_message_id IS NULL AND delivered_at IS NULL)
  )
);

CREATE TABLE IF NOT EXISTS public.lm_late_approval_decisions (
  decision_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  draft_id text NOT NULL REFERENCES public.lm_late_approval_drafts(draft_id),
  uid text NOT NULL CHECK (char_length(uid) BETWEEN 1 AND 256),
  decision text NOT NULL CHECK (decision IN ('send', 'do_not_send')),
  idempotency_key text NOT NULL CHECK (char_length(idempotency_key) BETWEEN 1 AND 512),
  decided_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (draft_id),
  UNIQUE (draft_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS public.lm_late_approval_claims (
  claim_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  draft_id text NOT NULL REFERENCES public.lm_late_approval_drafts(draft_id),
  worker_id text NOT NULL CHECK (char_length(worker_id) BETWEEN 1 AND 256),
  claim_token text NOT NULL UNIQUE CHECK (char_length(claim_token) BETWEEN 32 AND 256),
  claimed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  lease_expires_at timestamptz NOT NULL,
  UNIQUE (draft_id, claim_token)
);

CREATE TABLE IF NOT EXISTS public.lm_late_approval_receipts (
  receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  draft_id text NOT NULL REFERENCES public.lm_late_approval_drafts(draft_id),
  provider_message_id text NOT NULL UNIQUE CHECK (char_length(provider_message_id) BETWEEN 1 AND 512),
  delivered_at timestamptz NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE (draft_id)
);

CREATE INDEX IF NOT EXISTS lm_late_approval_drafts_status_idx
  ON public.lm_late_approval_drafts (status, updated_at);
CREATE INDEX IF NOT EXISTS lm_late_approval_drafts_uid_idx
  ON public.lm_late_approval_drafts (uid, created_at DESC);
CREATE INDEX IF NOT EXISTS lm_late_approval_claims_active_idx
  ON public.lm_late_approval_claims (draft_id, lease_expires_at DESC);

-- Evidence, recipient, ETA, and full body are the exact facts rendered in the approval card.  They
-- may never be changed after create, even by a retrying service-role request.
CREATE OR REPLACE FUNCTION public.lm_late_approval_snapshot_guard()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  IF NEW.uid IS DISTINCT FROM OLD.uid
    OR NEW.event_key IS DISTINCT FROM OLD.event_key
    OR NEW.recipient_status IS DISTINCT FROM OLD.recipient_status
    OR NEW.recipient_snapshot IS DISTINCT FROM OLD.recipient_snapshot
    OR NEW.evidence_snapshot IS DISTINCT FROM OLD.evidence_snapshot
    OR NEW.body_snapshot IS DISTINCT FROM OLD.body_snapshot
    OR NEW.eta_evidence_snapshot IS DISTINCT FROM OLD.eta_evidence_snapshot THEN
    RAISE EXCEPTION 'late approval evidence/body snapshot is immutable';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS lm_late_approval_snapshot_guard ON public.lm_late_approval_drafts;
CREATE TRIGGER lm_late_approval_snapshot_guard
  BEFORE UPDATE ON public.lm_late_approval_drafts
  FOR EACH ROW EXECUTE FUNCTION public.lm_late_approval_snapshot_guard();

CREATE OR REPLACE FUNCTION public.lm_late_approval_append_only_guard()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
END;
$$;

DROP TRIGGER IF EXISTS lm_late_approval_decisions_append_only ON public.lm_late_approval_decisions;
CREATE TRIGGER lm_late_approval_decisions_append_only
  BEFORE UPDATE OR DELETE ON public.lm_late_approval_decisions
  FOR EACH ROW EXECUTE FUNCTION public.lm_late_approval_append_only_guard();
DROP TRIGGER IF EXISTS lm_late_approval_claims_append_only ON public.lm_late_approval_claims;
CREATE TRIGGER lm_late_approval_claims_append_only
  BEFORE UPDATE OR DELETE ON public.lm_late_approval_claims
  FOR EACH ROW EXECUTE FUNCTION public.lm_late_approval_append_only_guard();
DROP TRIGGER IF EXISTS lm_late_approval_receipts_append_only ON public.lm_late_approval_receipts;
CREATE TRIGGER lm_late_approval_receipts_append_only
  BEFORE UPDATE OR DELETE ON public.lm_late_approval_receipts
  FOR EACH ROW EXECUTE FUNCTION public.lm_late_approval_append_only_guard();

CREATE OR REPLACE FUNCTION public.lm_create_late_draft(
  p_uid text,
  p_event_key text,
  p_recipient_status text,
  p_recipient_snapshot jsonb,
  p_evidence_snapshot jsonb,
  p_body_snapshot text,
  p_eta_evidence_snapshot jsonb,
  p_draft_id text DEFAULT NULL
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_row public.lm_late_approval_drafts%ROWTYPE;
BEGIN
  IF p_uid IS NULL OR char_length(p_uid) = 0 OR char_length(p_uid) > 256
    OR p_event_key IS NULL OR char_length(p_event_key) = 0 OR char_length(p_event_key) > 512 THEN
    RAISE EXCEPTION 'invalid late draft identity';
  END IF;
  IF p_recipient_status NOT IN ('resolved', 'recipient_missing', 'recipient_ambiguous') THEN
    RAISE EXCEPTION 'invalid late recipient status';
  END IF;
  IF jsonb_typeof(p_recipient_snapshot) <> 'array'
    OR (p_recipient_status = 'resolved' AND jsonb_array_length(p_recipient_snapshot) = 0) THEN
    RAISE EXCEPTION 'invalid late recipient snapshot';
  END IF;
  IF jsonb_typeof(p_evidence_snapshot) NOT IN ('array', 'object')
    OR jsonb_typeof(p_eta_evidence_snapshot) NOT IN ('array', 'object')
    OR p_body_snapshot IS NULL OR char_length(p_body_snapshot) NOT BETWEEN 1 AND 64000 THEN
    RAISE EXCEPTION 'invalid late evidence/body snapshot';
  END IF;

  -- INSERT ... DO NOTHING is the unique (uid,event_key) race gate.  The follow-up row lock is
  -- what makes retries observe one immutable snapshot instead of inventing a second draft.
  INSERT INTO public.lm_late_approval_drafts (
    draft_id, uid, event_key, status, recipient_status, recipient_snapshot,
    evidence_snapshot, body_snapshot, eta_evidence_snapshot
  ) VALUES (
    COALESCE(NULLIF(p_draft_id, ''), md5(clock_timestamp()::text || random()::text || txid_current()::text)),
    p_uid, p_event_key,
    CASE WHEN p_recipient_status = 'resolved' THEN 'awaiting_decision' ELSE p_recipient_status END,
    p_recipient_status, p_recipient_snapshot, p_evidence_snapshot, p_body_snapshot, p_eta_evidence_snapshot
  ) ON CONFLICT (uid, event_key) DO NOTHING
  RETURNING * INTO v_row;

  IF v_row.draft_id IS NOT NULL THEN
    RETURN to_jsonb(v_row);
  END IF;

  SELECT * INTO v_row
  FROM public.lm_late_approval_drafts
  WHERE uid = p_uid AND event_key = p_event_key
  FOR UPDATE;
  IF v_row.draft_id IS NULL THEN RAISE EXCEPTION 'late draft disappeared during retry'; END IF;
  IF v_row.recipient_status IS DISTINCT FROM p_recipient_status
    OR v_row.recipient_snapshot IS DISTINCT FROM p_recipient_snapshot
    OR v_row.evidence_snapshot IS DISTINCT FROM p_evidence_snapshot
    OR v_row.body_snapshot IS DISTINCT FROM p_body_snapshot
    OR v_row.eta_evidence_snapshot IS DISTINCT FROM p_eta_evidence_snapshot THEN
    RAISE EXCEPTION 'late draft immutable snapshot collision';
  END IF;
  RETURN to_jsonb(v_row) || jsonb_build_object('duplicate', true);
END;
$$;

CREATE OR REPLACE FUNCTION public.lm_decide_late_draft(
  p_uid text,
  p_draft_id text,
  p_decision text,
  p_idempotency_key text
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_row public.lm_late_approval_drafts%ROWTYPE;
BEGIN
  IF p_decision NOT IN ('send', 'do_not_send')
    OR p_idempotency_key IS NULL OR char_length(p_idempotency_key) = 0 OR char_length(p_idempotency_key) > 512 THEN
    RAISE EXCEPTION 'invalid late decision';
  END IF;
  SELECT * INTO v_row FROM public.lm_late_approval_drafts WHERE draft_id = p_draft_id FOR UPDATE;
  IF v_row.draft_id IS NULL THEN RAISE EXCEPTION 'late draft not found'; END IF;
  IF v_row.uid IS DISTINCT FROM p_uid THEN RAISE EXCEPTION 'late draft scope mismatch'; END IF;

  IF v_row.decision IS NOT NULL THEN
    IF v_row.decision = p_decision THEN RETURN to_jsonb(v_row) || jsonb_build_object('duplicate', true); END IF;
    RAISE EXCEPTION 'late decision conflict';
  END IF;
  IF v_row.status IN ('recipient_missing', 'recipient_ambiguous') THEN
    IF p_decision = 'send' THEN RAISE EXCEPTION 'recipient is not sendable'; END IF;
    RAISE EXCEPTION 'late draft is already terminal';
  END IF;
  IF v_row.status <> 'awaiting_decision' THEN RAISE EXCEPTION 'late draft is not awaiting a decision'; END IF;

  UPDATE public.lm_late_approval_drafts
  SET decision = p_decision,
      idempotency_key = p_idempotency_key,
      status = CASE WHEN p_decision = 'do_not_send' THEN 'do_not_send' ELSE status END,
      updated_at = clock_timestamp()
  WHERE draft_id = p_draft_id
  RETURNING * INTO v_row;

  INSERT INTO public.lm_late_approval_decisions (draft_id, uid, decision, idempotency_key)
  VALUES (v_row.draft_id, v_row.uid, p_decision, p_idempotency_key);
  RETURN to_jsonb(v_row);
END;
$$;

CREATE OR REPLACE FUNCTION public.lm_claim_late_delivery(
  p_draft_id text,
  p_worker_id text,
  p_lease_seconds integer DEFAULT 120
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_row public.lm_late_approval_drafts%ROWTYPE;
  v_token text;
  v_now timestamptz := clock_timestamp();
  v_recovered boolean := false;
BEGIN
  IF p_worker_id IS NULL OR char_length(p_worker_id) = 0 OR char_length(p_worker_id) > 256
    OR p_lease_seconds < 1 OR p_lease_seconds > 900 THEN
    RAISE EXCEPTION 'invalid late delivery claim';
  END IF;
  SELECT * INTO v_row FROM public.lm_late_approval_drafts WHERE draft_id = p_draft_id FOR UPDATE;
  IF v_row.draft_id IS NULL THEN RAISE EXCEPTION 'late draft not found'; END IF;
  IF v_row.status = 'sent' THEN RETURN to_jsonb(v_row) || jsonb_build_object('claimed', false, 'reason', 'sent'); END IF;
  IF v_row.status = 'do_not_send' THEN RETURN to_jsonb(v_row) || jsonb_build_object('claimed', false, 'reason', 'do_not_send'); END IF;
  IF v_row.status IN ('recipient_missing', 'recipient_ambiguous') THEN
    RETURN to_jsonb(v_row) || jsonb_build_object('claimed', false, 'reason', v_row.status);
  END IF;
  IF v_row.decision <> 'send' THEN
    RETURN to_jsonb(v_row) || jsonb_build_object('claimed', false, 'reason', 'decision_required');
  END IF;

  IF v_row.status = 'send_claimed' AND v_row.claim_expires_at > v_now THEN
    IF v_row.claim_worker_id <> p_worker_id THEN
      RETURN to_jsonb(v_row) || jsonb_build_object('claimed', false, 'reason', 'claimed_by_other_worker');
    END IF;
    UPDATE public.lm_late_approval_drafts
    SET claim_expires_at = v_now + make_interval(secs => p_lease_seconds), updated_at = v_now
    WHERE draft_id = p_draft_id
    RETURNING * INTO v_row;
    RETURN to_jsonb(v_row) || jsonb_build_object('claimed', true, 'retry', true);
  END IF;
  IF v_row.status = 'send_claimed' THEN v_recovered := true; END IF;

  v_token := md5(v_now::text || random()::text || p_draft_id || p_worker_id)
    || md5(clock_timestamp()::text || random()::text);
  UPDATE public.lm_late_approval_drafts
  SET status = 'send_claimed',
      claim_token = v_token,
      claim_worker_id = p_worker_id,
      claim_acquired_at = v_now,
      claim_expires_at = v_now + make_interval(secs => p_lease_seconds),
      updated_at = v_now
  WHERE draft_id = p_draft_id
  RETURNING * INTO v_row;
  INSERT INTO public.lm_late_approval_claims (draft_id, worker_id, claim_token, claimed_at, lease_expires_at)
  VALUES (v_row.draft_id, p_worker_id, v_token, v_now, v_row.claim_expires_at);
  RETURN to_jsonb(v_row) || jsonb_build_object(
    'claimed', true,
    'recovered', v_recovered
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.lm_record_late_delivery(
  p_draft_id text,
  p_provider_message_id text,
  p_delivered_at timestamptz,
  p_claim_token text DEFAULT NULL,
  p_worker_id text DEFAULT NULL
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_row public.lm_late_approval_drafts%ROWTYPE;
BEGIN
  IF p_provider_message_id IS NULL OR char_length(p_provider_message_id) = 0 OR char_length(p_provider_message_id) > 512
    OR p_delivered_at IS NULL THEN
    RAISE EXCEPTION 'invalid provider receipt';
  END IF;
  SELECT * INTO v_row FROM public.lm_late_approval_drafts WHERE draft_id = p_draft_id FOR UPDATE;
  IF v_row.draft_id IS NULL THEN RAISE EXCEPTION 'late draft not found'; END IF;
  IF v_row.status = 'sent' THEN
    IF v_row.provider_message_id = p_provider_message_id THEN RETURN to_jsonb(v_row) || jsonb_build_object('duplicate', true); END IF;
    RAISE EXCEPTION 'late provider receipt conflict';
  END IF;
  IF v_row.status <> 'send_claimed' THEN RAISE EXCEPTION 'late delivery was not claimed'; END IF;
  IF p_claim_token IS NOT NULL AND v_row.claim_token IS DISTINCT FROM p_claim_token THEN
    RAISE EXCEPTION 'late claim token mismatch';
  END IF;
  IF p_worker_id IS NOT NULL AND v_row.claim_worker_id IS DISTINCT FROM p_worker_id THEN
    RAISE EXCEPTION 'late claim worker mismatch';
  END IF;

  UPDATE public.lm_late_approval_drafts
  SET status = 'sent', provider_message_id = p_provider_message_id, delivered_at = p_delivered_at,
      updated_at = clock_timestamp()
  WHERE draft_id = p_draft_id
  RETURNING * INTO v_row;
  INSERT INTO public.lm_late_approval_receipts (draft_id, provider_message_id, delivered_at)
  VALUES (v_row.draft_id, p_provider_message_id, p_delivered_at);
  RETURN to_jsonb(v_row);
END;
$$;

ALTER TABLE public.lm_late_approval_drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_late_approval_drafts FORCE ROW LEVEL SECURITY;
ALTER TABLE public.lm_late_approval_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_late_approval_decisions FORCE ROW LEVEL SECURITY;
ALTER TABLE public.lm_late_approval_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_late_approval_claims FORCE ROW LEVEL SECURITY;
ALTER TABLE public.lm_late_approval_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lm_late_approval_receipts FORCE ROW LEVEL SECURITY;

-- Keep this migration runnable against the isolated Railway schema-only database, which does not
-- define Supabase's anon/authenticated/service_role roles.  On Supabase, the same block closes all
-- direct table access and grants only the four SECURITY DEFINER RPCs to service_role.
DO $$
DECLARE r text;
BEGIN
  FOREACH r IN ARRAY ARRAY['public', 'anon', 'authenticated', 'service_role'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('REVOKE ALL ON TABLE public.lm_late_approval_drafts, public.lm_late_approval_decisions, public.lm_late_approval_claims, public.lm_late_approval_receipts FROM %I', r);
    END IF;
  END LOOP;
  FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('REVOKE ALL ON FUNCTION public.lm_create_late_draft(text,text,text,jsonb,jsonb,text,jsonb,text) FROM %I', r);
      EXECUTE format('REVOKE ALL ON FUNCTION public.lm_decide_late_draft(text,text,text,text) FROM %I', r);
      EXECUTE format('REVOKE ALL ON FUNCTION public.lm_claim_late_delivery(text,text,integer) FROM %I', r);
      EXECUTE format('REVOKE ALL ON FUNCTION public.lm_record_late_delivery(text,text,timestamptz,text,text) FROM %I', r);
    END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT SELECT ON TABLE public.lm_late_approval_drafts, public.lm_late_approval_decisions, public.lm_late_approval_claims, public.lm_late_approval_receipts TO service_role;
    GRANT EXECUTE ON FUNCTION public.lm_create_late_draft(text,text,text,jsonb,jsonb,text,jsonb,text) TO service_role;
    GRANT EXECUTE ON FUNCTION public.lm_decide_late_draft(text,text,text,text) TO service_role;
    GRANT EXECUTE ON FUNCTION public.lm_claim_late_delivery(text,text,integer) TO service_role;
    GRANT EXECUTE ON FUNCTION public.lm_record_late_delivery(text,text,timestamptz,text,text) TO service_role;
  END IF;
END
$$;
