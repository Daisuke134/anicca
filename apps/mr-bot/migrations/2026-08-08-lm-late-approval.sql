-- DAILY #5: durable late-notice approval ledger.
--
-- The draft row is the immutable user-visible snapshot.  Decisions, claims, and provider receipts
-- are separate append-only ledgers so a retry can never rewrite the evidence that was shown before
-- the user tapped a button.  All transitions below lock the draft row with FOR UPDATE.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

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
  provider_idempotency_key text NOT NULL DEFAULT encode(gen_random_bytes(32), 'hex')
    CHECK (provider_idempotency_key ~ '^[0-9a-f]{64}$'),
  claim_token text,
  claim_worker_id text,
  claim_acquired_at timestamptz,
  claim_expires_at timestamptz,
  provider_message_id text,
  delivered_at timestamptz,
  telegram_receipt_status text NOT NULL DEFAULT 'pending' CHECK (telegram_receipt_status IN ('pending', 'send_claimed', 'sent')),
  telegram_receipt_chat_id text CHECK (telegram_receipt_chat_id IS NULL OR char_length(telegram_receipt_chat_id) BETWEEN 1 AND 256),
  telegram_receipt_text text CHECK (telegram_receipt_text IS NULL OR char_length(telegram_receipt_text) BETWEEN 1 AND 4096),
  telegram_receipt_claim_token text,
  telegram_receipt_worker_id text,
  telegram_receipt_claimed_at timestamptz,
  telegram_receipt_claim_expires_at timestamptz,
  telegram_receipt_message_id text,
  telegram_receipt_error text,
  telegram_receipt_attempts integer NOT NULL DEFAULT 0 CHECK (telegram_receipt_attempts >= 0),
  telegram_approval_chat_id text CHECK (telegram_approval_chat_id IS NULL OR char_length(telegram_approval_chat_id) BETWEEN 1 AND 256),
  telegram_approval_message_id text CHECK (telegram_approval_message_id IS NULL OR char_length(telegram_approval_message_id) BETWEEN 1 AND 512),
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
  ),
  CHECK (
    telegram_receipt_status <> 'sent'
    OR (telegram_receipt_message_id IS NOT NULL AND telegram_receipt_chat_id IS NOT NULL AND telegram_receipt_text IS NOT NULL)
  ),
  CHECK (
    telegram_receipt_status <> 'send_claimed'
    OR (telegram_receipt_claim_token IS NOT NULL AND telegram_receipt_worker_id IS NOT NULL AND telegram_receipt_claimed_at IS NOT NULL)
  ),
  CHECK (
    (telegram_approval_message_id IS NULL AND telegram_approval_chat_id IS NULL)
    OR (telegram_approval_message_id IS NOT NULL AND telegram_approval_chat_id IS NOT NULL)
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

-- Keep a rerun safe for a database that already has the pre-provider-key draft table.  Existing
-- rows receive one cryptographically random key, and the unique index prevents two drafts from
-- sharing a provider idempotency identity.
ALTER TABLE public.lm_late_approval_drafts
  ADD COLUMN IF NOT EXISTS provider_idempotency_key text;
UPDATE public.lm_late_approval_drafts
SET provider_idempotency_key = encode(gen_random_bytes(32), 'hex')
WHERE provider_idempotency_key IS NULL;
ALTER TABLE public.lm_late_approval_drafts
  ALTER COLUMN provider_idempotency_key SET DEFAULT encode(gen_random_bytes(32), 'hex'),
  ALTER COLUMN provider_idempotency_key SET NOT NULL;
ALTER TABLE public.lm_late_approval_drafts
  ADD COLUMN IF NOT EXISTS telegram_receipt_status text,
  ADD COLUMN IF NOT EXISTS telegram_receipt_chat_id text,
  ADD COLUMN IF NOT EXISTS telegram_receipt_text text,
  ADD COLUMN IF NOT EXISTS telegram_receipt_claim_token text,
  ADD COLUMN IF NOT EXISTS telegram_receipt_worker_id text,
  ADD COLUMN IF NOT EXISTS telegram_receipt_claimed_at timestamptz,
  ADD COLUMN IF NOT EXISTS telegram_receipt_claim_expires_at timestamptz,
  ADD COLUMN IF NOT EXISTS telegram_receipt_message_id text,
  ADD COLUMN IF NOT EXISTS telegram_receipt_error text,
  ADD COLUMN IF NOT EXISTS telegram_receipt_attempts integer,
  ADD COLUMN IF NOT EXISTS telegram_approval_chat_id text,
  ADD COLUMN IF NOT EXISTS telegram_approval_message_id text;
UPDATE public.lm_late_approval_drafts
SET telegram_receipt_status = COALESCE(telegram_receipt_status, 'pending'),
    telegram_receipt_attempts = COALESCE(telegram_receipt_attempts, 0)
WHERE telegram_receipt_status IS NULL OR telegram_receipt_attempts IS NULL;
ALTER TABLE public.lm_late_approval_drafts
  ALTER COLUMN telegram_receipt_status SET DEFAULT 'pending',
  ALTER COLUMN telegram_receipt_status SET NOT NULL,
  ALTER COLUMN telegram_receipt_attempts SET DEFAULT 0,
  ALTER COLUMN telegram_receipt_attempts SET NOT NULL;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_late_approval_drafts'::regclass
      AND conname = 'lm_late_approval_drafts_telegram_receipt_status'
  ) THEN
    ALTER TABLE public.lm_late_approval_drafts
      ADD CONSTRAINT lm_late_approval_drafts_telegram_receipt_status
      CHECK (telegram_receipt_status IN ('pending', 'send_claimed', 'sent'));
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_late_approval_drafts'::regclass
      AND conname = 'lm_late_approval_drafts_telegram_receipt_attempts'
  ) THEN
    ALTER TABLE public.lm_late_approval_drafts
      ADD CONSTRAINT lm_late_approval_drafts_telegram_receipt_attempts
      CHECK (telegram_receipt_attempts >= 0);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_late_approval_drafts'::regclass
      AND conname = 'lm_late_approval_drafts_telegram_receipt_sent_fields'
  ) THEN
    ALTER TABLE public.lm_late_approval_drafts
      ADD CONSTRAINT lm_late_approval_drafts_telegram_receipt_sent_fields
      CHECK (
        telegram_receipt_status <> 'sent'
        OR (telegram_receipt_message_id IS NOT NULL AND telegram_receipt_chat_id IS NOT NULL AND telegram_receipt_text IS NOT NULL)
      );
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_late_approval_drafts'::regclass
      AND conname = 'lm_late_approval_drafts_telegram_receipt_claim_fields'
  ) THEN
    ALTER TABLE public.lm_late_approval_drafts
      ADD CONSTRAINT lm_late_approval_drafts_telegram_receipt_claim_fields
      CHECK (
        telegram_receipt_status <> 'send_claimed'
        OR (telegram_receipt_claim_token IS NOT NULL AND telegram_receipt_worker_id IS NOT NULL AND telegram_receipt_claimed_at IS NOT NULL)
      );
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_late_approval_drafts'::regclass
      AND conname = 'lm_late_approval_drafts_telegram_approval_card_fields'
  ) THEN
    ALTER TABLE public.lm_late_approval_drafts
      ADD CONSTRAINT lm_late_approval_drafts_telegram_approval_card_fields
      CHECK (
        (telegram_approval_message_id IS NULL AND telegram_approval_chat_id IS NULL)
        OR (telegram_approval_message_id IS NOT NULL AND telegram_approval_chat_id IS NOT NULL)
      );
  END IF;
END
$$;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.lm_late_approval_drafts'::regclass
      AND conname = 'lm_late_approval_drafts_provider_idempotency_key_format'
  ) THEN
    ALTER TABLE public.lm_late_approval_drafts
      ADD CONSTRAINT lm_late_approval_drafts_provider_idempotency_key_format
      CHECK (provider_idempotency_key ~ '^[0-9a-f]{64}$');
  END IF;
END
$$;
CREATE UNIQUE INDEX IF NOT EXISTS lm_late_approval_drafts_provider_idempotency_key_idx
  ON public.lm_late_approval_drafts (provider_idempotency_key);

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
    OR NEW.eta_evidence_snapshot IS DISTINCT FROM OLD.eta_evidence_snapshot
    OR NEW.provider_idempotency_key IS DISTINCT FROM OLD.provider_idempotency_key THEN
    RAISE EXCEPTION 'late approval evidence/body snapshot is immutable';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS lm_late_approval_snapshot_guard ON public.lm_late_approval_drafts;
CREATE TRIGGER lm_late_approval_snapshot_guard
  BEFORE UPDATE ON public.lm_late_approval_drafts
  FOR EACH ROW EXECUTE FUNCTION public.lm_late_approval_snapshot_guard();

-- Draft reads use the same deny-by-default RPC boundary as every state transition.  The callback
-- needs the immutable snapshot after Telegram authenticates the chat, but the table itself stays
-- inaccessible to application roles (including service_role) so a future read path cannot bypass
-- the tenant filter by accident.
CREATE OR REPLACE FUNCTION public.lm_get_late_draft(
  p_uid text,
  p_draft_id text
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_row public.lm_late_approval_drafts%ROWTYPE;
BEGIN
  IF p_uid IS NULL OR char_length(p_uid) = 0 OR char_length(p_uid) > 256
    OR p_draft_id IS NULL OR char_length(p_draft_id) = 0 OR char_length(p_draft_id) > 128 THEN
    RAISE EXCEPTION 'invalid late draft lookup';
  END IF;
  SELECT * INTO v_row
  FROM public.lm_late_approval_drafts
  WHERE uid = p_uid AND draft_id = p_draft_id;
  IF v_row.draft_id IS NULL THEN RAISE EXCEPTION 'late draft not found'; END IF;
  RETURN to_jsonb(v_row);
END;
$$;

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

-- The receipt boundary is deliberately replaced rather than overloaded: callers must provide the
-- tenant and the exact current claim identity on every attempt.
DROP FUNCTION IF EXISTS public.lm_record_late_delivery(text, text, timestamptz, text, text);
CREATE OR REPLACE FUNCTION public.lm_record_late_delivery(
  p_uid text,
  p_draft_id text,
  p_provider_message_id text,
  p_delivered_at timestamptz,
  p_claim_token text,
  p_worker_id text
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_row public.lm_late_approval_drafts%ROWTYPE;
BEGIN
  IF p_uid IS NULL OR char_length(p_uid) = 0 OR char_length(p_uid) > 256
    OR p_claim_token IS NULL OR char_length(p_claim_token) = 0 OR char_length(p_claim_token) > 512
    OR p_worker_id IS NULL OR char_length(p_worker_id) = 0 OR char_length(p_worker_id) > 256
    OR p_provider_message_id IS NULL OR char_length(p_provider_message_id) = 0 OR char_length(p_provider_message_id) > 512
    OR p_delivered_at IS NULL THEN
    RAISE EXCEPTION 'invalid provider receipt';
  END IF;
  SELECT * INTO v_row
  FROM public.lm_late_approval_drafts
  WHERE draft_id = p_draft_id AND uid = p_uid
  FOR UPDATE;
  IF v_row.draft_id IS NULL THEN RAISE EXCEPTION 'late draft not found'; END IF;
  IF v_row.claim_token IS DISTINCT FROM p_claim_token THEN
    RAISE EXCEPTION 'late claim token mismatch';
  END IF;
  IF v_row.claim_worker_id IS DISTINCT FROM p_worker_id THEN
    RAISE EXCEPTION 'late claim worker mismatch';
  END IF;
  IF v_row.status = 'sent' THEN
    IF v_row.provider_message_id = p_provider_message_id THEN RETURN to_jsonb(v_row) || jsonb_build_object('duplicate', true); END IF;
    RAISE EXCEPTION 'late provider receipt conflict';
  END IF;
  IF v_row.status <> 'send_claimed' THEN RAISE EXCEPTION 'late delivery was not claimed'; END IF;

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

CREATE OR REPLACE FUNCTION public.lm_enqueue_late_telegram_receipt(
  p_uid text,
  p_draft_id text,
  p_chat_id text,
  p_receipt_text text
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_row public.lm_late_approval_drafts%ROWTYPE;
BEGIN
  IF p_uid IS NULL OR char_length(p_uid) = 0 OR char_length(p_uid) > 256
    OR p_draft_id IS NULL OR char_length(p_draft_id) = 0 OR char_length(p_draft_id) > 128
    OR p_chat_id IS NULL OR char_length(p_chat_id) = 0 OR char_length(p_chat_id) > 256
    OR p_receipt_text IS NULL OR char_length(p_receipt_text) = 0 OR char_length(p_receipt_text) > 4096 THEN
    RAISE EXCEPTION 'invalid Telegram receipt queue item';
  END IF;
  SELECT * INTO v_row
  FROM public.lm_late_approval_drafts
  WHERE draft_id = p_draft_id AND uid = p_uid
  FOR UPDATE;
  IF v_row.draft_id IS NULL THEN RAISE EXCEPTION 'late draft not found'; END IF;
  IF v_row.status <> 'sent' OR v_row.provider_message_id IS NULL THEN
    RAISE EXCEPTION 'Telegram receipt requires a durable provider receipt';
  END IF;
  IF v_row.telegram_receipt_chat_id IS NOT NULL AND v_row.telegram_receipt_chat_id <> p_chat_id THEN
    RAISE EXCEPTION 'Telegram receipt chat collision';
  END IF;
  IF v_row.telegram_receipt_text IS NOT NULL AND v_row.telegram_receipt_text <> p_receipt_text THEN
    RAISE EXCEPTION 'Telegram receipt text collision';
  END IF;
  UPDATE public.lm_late_approval_drafts
  SET telegram_receipt_chat_id = p_chat_id,
      telegram_receipt_text = p_receipt_text,
      telegram_receipt_status = COALESCE(telegram_receipt_status, 'pending'),
      updated_at = clock_timestamp()
  WHERE draft_id = p_draft_id
  RETURNING * INTO v_row;
  RETURN to_jsonb(v_row);
END;
$$;

CREATE OR REPLACE FUNCTION public.lm_record_late_approval_card(
  p_uid text,
  p_draft_id text,
  p_chat_id text,
  p_telegram_message_id text
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_row public.lm_late_approval_drafts%ROWTYPE;
BEGIN
  IF p_uid IS NULL OR char_length(p_uid) = 0 OR char_length(p_uid) > 256
    OR p_draft_id IS NULL OR char_length(p_draft_id) = 0 OR char_length(p_draft_id) > 128
    OR p_chat_id IS NULL OR char_length(p_chat_id) = 0 OR char_length(p_chat_id) > 256
    OR p_telegram_message_id IS NULL OR char_length(p_telegram_message_id) = 0 OR char_length(p_telegram_message_id) > 512 THEN
    RAISE EXCEPTION 'invalid Telegram approval card';
  END IF;
  SELECT * INTO v_row
  FROM public.lm_late_approval_drafts
  WHERE draft_id = p_draft_id AND uid = p_uid
  FOR UPDATE;
  IF v_row.draft_id IS NULL THEN RAISE EXCEPTION 'late draft not found'; END IF;
  IF v_row.recipient_status <> 'resolved' THEN
    RAISE EXCEPTION 'only a resolved late draft can own an approval card';
  END IF;
  IF v_row.telegram_approval_message_id IS NOT NULL
    AND v_row.telegram_approval_message_id <> p_telegram_message_id THEN
    RAISE EXCEPTION 'Telegram approval card message collision';
  END IF;
  IF v_row.telegram_approval_chat_id IS NOT NULL
    AND v_row.telegram_approval_chat_id <> p_chat_id THEN
    RAISE EXCEPTION 'Telegram approval card chat collision';
  END IF;
  UPDATE public.lm_late_approval_drafts
  SET telegram_approval_chat_id = p_chat_id,
      telegram_approval_message_id = p_telegram_message_id,
      updated_at = clock_timestamp()
  WHERE draft_id = p_draft_id
  RETURNING * INTO v_row;
  RETURN to_jsonb(v_row);
END;
$$;

CREATE OR REPLACE FUNCTION public.lm_claim_late_telegram_receipt(
  p_uid text,
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
  IF p_uid IS NULL OR char_length(p_uid) = 0 OR char_length(p_uid) > 256
    OR p_draft_id IS NULL OR char_length(p_draft_id) = 0 OR char_length(p_draft_id) > 128
    OR p_worker_id IS NULL OR char_length(p_worker_id) = 0 OR char_length(p_worker_id) > 256
    OR p_lease_seconds < 1 OR p_lease_seconds > 900 THEN
    RAISE EXCEPTION 'invalid Telegram receipt claim';
  END IF;
  SELECT * INTO v_row
  FROM public.lm_late_approval_drafts
  WHERE draft_id = p_draft_id AND uid = p_uid
  FOR UPDATE;
  IF v_row.draft_id IS NULL THEN RAISE EXCEPTION 'late draft not found'; END IF;
  IF v_row.status <> 'sent' OR v_row.provider_message_id IS NULL THEN
    RETURN to_jsonb(v_row) || jsonb_build_object('claimed', false, 'reason', 'provider_receipt_required');
  END IF;
  IF v_row.telegram_receipt_chat_id IS NULL OR v_row.telegram_receipt_text IS NULL THEN
    RETURN to_jsonb(v_row) || jsonb_build_object('claimed', false, 'reason', 'receipt_not_queued');
  END IF;
  IF v_row.telegram_receipt_status = 'sent' THEN
    RETURN to_jsonb(v_row) || jsonb_build_object('claimed', false, 'reason', 'telegram_sent');
  END IF;
  IF v_row.telegram_receipt_status = 'send_claimed'
    AND v_row.telegram_receipt_claim_expires_at > v_now THEN
    RETURN to_jsonb(v_row) || jsonb_build_object('claimed', false, 'reason', 'receipt_claimed_by_other_worker');
  END IF;
  IF v_row.telegram_receipt_status = 'send_claimed' THEN v_recovered := true; END IF;

  v_token := md5(v_now::text || random()::text || p_draft_id || p_worker_id)
    || md5(clock_timestamp()::text || random()::text);
  UPDATE public.lm_late_approval_drafts
  SET telegram_receipt_status = 'send_claimed',
      telegram_receipt_claim_token = v_token,
      telegram_receipt_worker_id = p_worker_id,
      telegram_receipt_claimed_at = v_now,
      telegram_receipt_claim_expires_at = v_now + make_interval(secs => p_lease_seconds),
      telegram_receipt_attempts = COALESCE(telegram_receipt_attempts, 0) + 1,
      telegram_receipt_error = NULL,
      updated_at = v_now
  WHERE draft_id = p_draft_id
  RETURNING * INTO v_row;
  RETURN to_jsonb(v_row) || jsonb_build_object('claimed', true)
    || CASE WHEN v_recovered THEN jsonb_build_object('recovered', true) ELSE '{}'::jsonb END;
END;
$$;

CREATE OR REPLACE FUNCTION public.lm_record_late_telegram_receipt(
  p_uid text,
  p_draft_id text,
  p_claim_token text,
  p_worker_id text,
  p_telegram_message_id text
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_row public.lm_late_approval_drafts%ROWTYPE;
BEGIN
  IF p_uid IS NULL OR char_length(p_uid) = 0 OR char_length(p_uid) > 256
    OR p_draft_id IS NULL OR char_length(p_draft_id) = 0 OR char_length(p_draft_id) > 128
    OR p_claim_token IS NULL OR char_length(p_claim_token) = 0 OR char_length(p_claim_token) > 512
    OR p_worker_id IS NULL OR char_length(p_worker_id) = 0 OR char_length(p_worker_id) > 256
    OR p_telegram_message_id IS NULL OR char_length(p_telegram_message_id) = 0 OR char_length(p_telegram_message_id) > 512 THEN
    RAISE EXCEPTION 'invalid Telegram receipt';
  END IF;
  SELECT * INTO v_row
  FROM public.lm_late_approval_drafts
  WHERE draft_id = p_draft_id AND uid = p_uid
  FOR UPDATE;
  IF v_row.draft_id IS NULL THEN RAISE EXCEPTION 'late draft not found'; END IF;
  IF v_row.telegram_receipt_status = 'sent' THEN
    IF v_row.telegram_receipt_message_id = p_telegram_message_id THEN
      RETURN to_jsonb(v_row) || jsonb_build_object('duplicate', true);
    END IF;
    RAISE EXCEPTION 'Telegram receipt conflict';
  END IF;
  IF v_row.telegram_receipt_status <> 'send_claimed' THEN
    RAISE EXCEPTION 'Telegram receipt was not claimed';
  END IF;
  IF v_row.telegram_receipt_claim_token IS DISTINCT FROM p_claim_token THEN
    RAISE EXCEPTION 'Telegram receipt claim token mismatch';
  END IF;
  IF v_row.telegram_receipt_worker_id IS DISTINCT FROM p_worker_id THEN
    RAISE EXCEPTION 'Telegram receipt claim worker mismatch';
  END IF;
  UPDATE public.lm_late_approval_drafts
  SET telegram_receipt_status = 'sent',
      telegram_receipt_message_id = p_telegram_message_id,
      telegram_receipt_error = NULL,
      updated_at = clock_timestamp()
  WHERE draft_id = p_draft_id
  RETURNING * INTO v_row;
  RETURN to_jsonb(v_row);
END;
$$;

CREATE OR REPLACE FUNCTION public.lm_release_late_telegram_receipt(
  p_uid text,
  p_draft_id text,
  p_claim_token text,
  p_worker_id text,
  p_error text
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_row public.lm_late_approval_drafts%ROWTYPE;
BEGIN
  IF p_uid IS NULL OR char_length(p_uid) = 0 OR char_length(p_uid) > 256
    OR p_draft_id IS NULL OR char_length(p_draft_id) = 0 OR char_length(p_draft_id) > 128
    OR p_claim_token IS NULL OR char_length(p_claim_token) = 0 OR char_length(p_claim_token) > 512
    OR p_worker_id IS NULL OR char_length(p_worker_id) = 0 OR char_length(p_worker_id) > 256
    OR p_error IS NOT NULL AND char_length(p_error) > 1024 THEN
    RAISE EXCEPTION 'invalid Telegram receipt release';
  END IF;
  SELECT * INTO v_row
  FROM public.lm_late_approval_drafts
  WHERE draft_id = p_draft_id AND uid = p_uid
  FOR UPDATE;
  IF v_row.draft_id IS NULL THEN RAISE EXCEPTION 'late draft not found'; END IF;
  IF v_row.telegram_receipt_status = 'sent' THEN
    RETURN to_jsonb(v_row) || jsonb_build_object('duplicate', true);
  END IF;
  IF v_row.telegram_receipt_status <> 'send_claimed' THEN
    RAISE EXCEPTION 'Telegram receipt was not claimed';
  END IF;
  IF v_row.telegram_receipt_claim_token IS DISTINCT FROM p_claim_token THEN
    RAISE EXCEPTION 'Telegram receipt claim token mismatch';
  END IF;
  IF v_row.telegram_receipt_worker_id IS DISTINCT FROM p_worker_id THEN
    RAISE EXCEPTION 'Telegram receipt claim worker mismatch';
  END IF;
  UPDATE public.lm_late_approval_drafts
  SET telegram_receipt_status = 'pending',
      telegram_receipt_claim_token = NULL,
      telegram_receipt_worker_id = NULL,
      telegram_receipt_claimed_at = NULL,
      telegram_receipt_claim_expires_at = NULL,
      telegram_receipt_error = p_error,
      updated_at = clock_timestamp()
  WHERE draft_id = p_draft_id
  RETURNING * INTO v_row;
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

-- The ten SECURITY DEFINER functions are deny-by-default.  PUBLIC is explicit here because
-- PostgreSQL grants new functions to PUBLIC unless it is revoked by name.
REVOKE ALL ON TABLE
  public.lm_late_approval_drafts,
  public.lm_late_approval_decisions,
  public.lm_late_approval_claims,
  public.lm_late_approval_receipts
FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE
  public.lm_late_approval_drafts,
  public.lm_late_approval_decisions,
  public.lm_late_approval_claims,
  public.lm_late_approval_receipts
FROM service_role;

REVOKE ALL ON FUNCTION public.lm_create_late_draft(text,text,text,jsonb,jsonb,text,jsonb,text)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.lm_get_late_draft(text,text)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.lm_decide_late_draft(text,text,text,text)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.lm_claim_late_delivery(text,text,integer)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.lm_record_late_delivery(text,text,text,timestamptz,text,text)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.lm_enqueue_late_telegram_receipt(text,text,text,text)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.lm_record_late_approval_card(text,text,text,text)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.lm_claim_late_telegram_receipt(text,text,text,integer)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.lm_record_late_telegram_receipt(text,text,text,text,text)
  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.lm_release_late_telegram_receipt(text,text,text,text,text)
  FROM PUBLIC, anon, authenticated;

-- Role fixtures are installed by the isolated staging preflight when this migration is exercised
-- outside Supabase.  The conditional grants allow only service_role to cross the RPC boundary
-- where that role exists; direct table access remains revoked for every application role.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.lm_create_late_draft(text,text,text,jsonb,jsonb,text,jsonb,text) TO service_role';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.lm_get_late_draft(text,text) TO service_role';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.lm_decide_late_draft(text,text,text,text) TO service_role';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.lm_claim_late_delivery(text,text,integer) TO service_role';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.lm_record_late_delivery(text,text,text,timestamptz,text,text) TO service_role';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.lm_enqueue_late_telegram_receipt(text,text,text,text) TO service_role';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.lm_record_late_approval_card(text,text,text,text) TO service_role';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.lm_claim_late_telegram_receipt(text,text,text,integer) TO service_role';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.lm_record_late_telegram_receipt(text,text,text,text,text) TO service_role';
    EXECUTE 'GRANT EXECUTE ON FUNCTION public.lm_release_late_telegram_receipt(text,text,text,text,text) TO service_role';
  END IF;
END
$$;
