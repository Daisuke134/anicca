import type { FranklinAgent } from "./franklin-agent.js";

export interface FranklinEnv extends Cloudflare.Env {
  FRANKLIN_AGENT: DurableObjectNamespace<FranklinAgent>;
  INTERNAL_API_TOKEN?: string;
}

export type FranklinId = string & { readonly __brand: "FranklinId" };

export interface FranklinState {
  franklinId: FranklinId | null;
  revision: number;
  lastCommand: string | null;
  updatedAt: number | null;
}

export interface FranklinAgentProps extends Record<string, unknown> {
  franklinId: FranklinId;
}

export interface FranklinMutation {
  command: string;
}

const FRANKLIN_ID_PATTERN = /^[a-z0-9][a-z0-9_-]{0,62}$/;

export function parseFranklinId(value: string): FranklinId | null {
  return FRANKLIN_ID_PATTERN.test(value) ? (value as FranklinId) : null;
}

export interface ChainReceipt {
  chainId: string;
  transactionHash: string;
  assetId: string;
  amountAtomic: string;
  status: "confirmed" | "failed";
}

/** Future boundary only: implementation must live outside this slice. */
export interface FutureSignerPort {
  sign(payload: Uint8Array): Promise<Uint8Array>;
}

/** Future balance source: only confirmed chain receipts may update balances. */
export interface FutureChainReceiptReaderPort {
  readConfirmedReceipts(input: { accountId: string }): Promise<readonly ChainReceipt[]>;
}

/** Future x402 boundary only: no payment receiving is implemented here. */
export interface FutureX402ReceiptPort {
  acceptReceipt(receipt: ChainReceipt): Promise<void>;
}

/** Future WebMCP boundary only: no browser or MCP execution is implemented here. */
export interface FutureWebMCPPort {
  invoke(toolName: string, input: unknown): Promise<unknown>;
}
