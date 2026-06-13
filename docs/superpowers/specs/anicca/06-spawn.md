# 06 — Birth + Self-replication
Goal: `bash scripts/birth.sh` → a REAL Anicca is born and starts (local). With a provider API key → born in the cloud too. Self-replication: a profitable Anicca spawns a child (new key→wallet+AgentMail), seeds it, the child secures its own shelter and starts.
Files: scripts/birth.sh (idempotent: gen identity → start compute → start loop → register → report), skills/self/spawn_child.mjs.
Acceptance: birth.sh on a clean dir → running Anicca + first heartbeat mail within minutes (local); same with DO key (cloud). spawn_child creates a second running Anicca with its own wallet/mail.
