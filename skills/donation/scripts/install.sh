#!/usr/bin/env bash
# DEPRECATED — donation v1 (Stripe Connect rail) does NOT use an install hook.
# Charity onboarding to Stripe Connect is performed manually by the charity
# itself. After charges_enabled=true on the Stripe Dashboard, set
# charges_enabled_verified=true in recipients.json.
#
# The agent-{{profile.lateness.stakeholders.channel}}-driven install hook is preserved at
#   ~/.openclaw/skills/donation-v2-archive/scripts/install.sh
echo "❌ install.sh is no-op in v1. See ~/.openclaw/skills/donation/SKILL.md → 'Two payment rails'."
exit 1
