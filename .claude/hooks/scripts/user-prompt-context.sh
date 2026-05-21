#!/bin/bash
# UserPromptSubmit hook: Inject context on user message
BRANCH=$(git -C /Users/anicca/anicca-project branch --show-current 2>/dev/null)
if [ "$BRANCH" != "dev" ] && [ "$BRANCH" != "main" ]; then
  echo "NOTE: Currently on branch '$BRANCH' (not dev/main)"
fi
