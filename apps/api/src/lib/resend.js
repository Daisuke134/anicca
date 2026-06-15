/**
 * Resend client (lazy singleton).
 *
 * Constructed on first use rather than at import time so that a missing
 * RESEND_API_KEY never crashes module import / server startup. Send failures
 * (including a missing key) are handled gracefully by callers
 * (feedback → 202 queued, newsletter → failed_resend_calls dead-letter row).
 */
import { Resend } from 'resend';

let client = null;

export function getResend() {
  if (!client) {
    client = new Resend(process.env.RESEND_API_KEY);
  }
  return client;
}
