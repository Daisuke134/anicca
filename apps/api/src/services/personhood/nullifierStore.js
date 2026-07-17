// nullifierStore.js — production dedup store for the World ID sybil gate, backed by the
// personhood_nullifier table's UNIQUE(nullifier_hash, action) index (the atomic guard).
//
// Implements the { has, add } contract verifyPersonhood expects. add() does a bare INSERT: on a
// duplicate the DB throws P2002, which propagates so verifyPersonhood's catch maps it to
// already_claimed — this is what actually closes the TOCTOU race (security review #1). Never swallow
// the unique-violation here; let it throw.
//
// The default Prisma client is resolved LAZILY (only when no prisma is injected) so this module is
// importable/testable without the generated client present.

async function resolvePrisma(injected) {
  if (injected) return injected;
  const mod = await import('../../lib/prisma.js');
  return mod.prisma;
}

export function makeNullifierStore({ action, signal = null, prisma } = {}) {
  if (!action) throw new Error('nullifierStore: action required');
  return {
    has: async (nullifierHash) => {
      const db = await resolvePrisma(prisma);
      const row = await db.personhood_nullifier.findUnique({
        where: { nullifierHash_action: { nullifierHash, action } },
      });
      return !!row;
    },
    // INSERT — throws on duplicate (Prisma P2002). Do NOT catch here; verifyPersonhood maps it.
    add: async (nullifierHash) => {
      const db = await resolvePrisma(prisma);
      await db.personhood_nullifier.create({ data: { nullifierHash, action, signal } });
    },
  };
}
