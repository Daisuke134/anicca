-- Web reply-by-email: store the short opaque Reply-To token on the ask row so the /inbound-email webhook
-- can resolve a reply (reply+<token>@reply.aniccaai.com) back to (uid, event_id). Mailbox-hash pattern.
ALTER TABLE lm_ask_log ADD COLUMN IF NOT EXISTS reply_token text;
CREATE INDEX IF NOT EXISTS lm_ask_log_reply_token_idx ON lm_ask_log(reply_token);
