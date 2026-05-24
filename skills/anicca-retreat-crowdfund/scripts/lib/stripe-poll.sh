#!/usr/bin/env bash
set -euo pipefail

# Poll Stripe Checkout Sessions for retreat-build-fund donations.
# Recipe (exact tool): raw curl to https://api.stripe.com/v1/checkout/sessions
# (NOT Stripe MCP, NOT @stripe/stripe-node — same pattern as netlify function)
#
# Usage: stripe_poll_donations [since_unix_ts]
# Output JSON: { total_count, total_amount_jpy, sessions: [{id, amount, customer_{{profile.lateness.stakeholders.channel}}, created}] }

stripe_poll_donations() {
  local since_ts="${1:-0}"
  : "${STRIPE_SECRET_KEY:?required}"

  local url="https://api.stripe.com/v1/checkout/sessions?limit=100&status=complete"
  if [ "$since_ts" -gt 0 ]; then
    url="${url}&created[gte]=${since_ts}"
  fi

  curl -sS "$url" \
    -H "Authorization: Bearer $STRIPE_SECRET_KEY" \
    | jq '
      [
        .data[]
        | select(.metadata.product == "retreat-build-fund")
        | {
            id: .id,
            amount_jpy: .amount_total,
            currency: .currency,
            customer_{{profile.lateness.stakeholders.channel}}: .customer_details.{{profile.lateness.stakeholders.channel}},
            tier_label: .metadata.tier_label,
            created: .created,
            payment_status: .payment_status
          }
      ]
      | {
          total_count: length,
          total_amount_jpy: ([.[] | select(.payment_status == "paid") | .amount_jpy] | add // 0),
          sessions: .
        }
    '
}
