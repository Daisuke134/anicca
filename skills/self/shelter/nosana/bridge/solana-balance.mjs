// solana-balance.mjs — read a wallet's USDC balance on Solana. Mirrors ../deploy.mjs's
// readNosBalance shape exactly (getParsedTokenAccountsByOwner filtered by mint), just pointed at
// the canonical Solana USDC mint instead of the NOS mint — this is the "destination-side credit"
// signal reconcile.mjs polls.

import { SOLANA_USDC_MINT } from "./constants.mjs";

export async function getSolanaUsdcBalance({ connection, address, PublicKeyCtor }) {
  const resp = await connection.getParsedTokenAccountsByOwner(new PublicKeyCtor(address), {
    mint: new PublicKeyCtor(SOLANA_USDC_MINT),
  });
  if (!resp || !Array.isArray(resp.value) || resp.value.length === 0) return 0;
  const amount = resp.value[0].account.data.parsed.info.tokenAmount.uiAmount;
  return typeof amount === "number" ? amount : 0;
}
