#!/usr/bin/env node
// DEPRECATED — replaced by the v1 Python pipeline (profile-day.py + match-clawhub.py).
// Kept in place because the sandboxed mount denies file unlink. Do not invoke.
console.error("skill-for-you.js is deprecated — run:");
console.error("  python3 ~/.openclaw/skills/skill-for-you/scripts/profile-day.py");
console.error("  python3 ~/.openclaw/skills/skill-for-you/scripts/match-clawhub.py");
process.exit(1);
