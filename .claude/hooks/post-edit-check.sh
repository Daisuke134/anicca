#!/usr/bin/env bash
# Runs after Edit/Write tools — reminds to TaskUpdate + commit
cat <<EOF
=== POST-EDIT CHECK (= HARD RULE 0.32) ===
You just edited a file. Did you:
  [ ] Update relevant task status (in_progress → completed via TaskUpdate)?
  [ ] Stage + commit + push the change (HARD RULE 0.4 / 0.28)?
  [ ] Update spec section if scope changed?
If any unchecked = HARD RULE violation = self-revert and do it now.
EOF
