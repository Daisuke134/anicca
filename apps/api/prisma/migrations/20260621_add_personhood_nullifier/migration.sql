-- #36 World ID personhood sybil gate: one nullifier per action = one human.
-- The UNIQUE index is the ATOMIC guard a duplicate INSERT rejects (P2002), closing the TOCTOU race.
CREATE TABLE IF NOT EXISTS "personhood_nullifier" (
  "id"             BIGSERIAL PRIMARY KEY,
  "nullifier_hash" TEXT NOT NULL,
  "action"         TEXT NOT NULL,
  "signal"         TEXT,
  "created_at"     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS "personhood_nullifier_nullifier_hash_action_key"
  ON "personhood_nullifier" ("nullifier_hash", "action");
