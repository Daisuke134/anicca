#!/usr/bin/env node
// economy/gig/mcp-server.mjs — MCP stdio server exposing the P2.2 gig board as ordinary Franklin tools.
// SPEC.md §9.1: Franklin's own MCP loader (@blockrun/franklin, dist/mcp/config.js) reads
// ~/.blockrun/mcp.json's "mcpServers" map at startup and wraps any listed stdio server into its normal
// tool set -- Franklin itself is never touched, we only ADD a server entry (wiring snippet in README,
// NOT applied to the live file here -- that's the witness step the team lead runs separately).
//
// Each tool call takes the CALLING agent's own private key as an argument (never stored by this
// process beyond the single call) -- the gig board holds no custody over poster/taker wallets, only
// over its own escrow keypair (GIG_ESCROW_PRIVATE_KEY, see README "Escrow model").
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { gigPost, gigList, gigTake, gigDeliver, gigVerifyAndPay, registerIdentity, verifyIdentity } from "./gig.mjs";

const server = new McpServer({ name: "anicca-gig", version: "0.1.0" });

function textResult(obj) {
  return { content: [{ type: "text", text: JSON.stringify(obj) }] };
}

server.registerTool(
  "gig_post",
  {
    title: "Post a gig",
    description:
      "Post a paid task with a bounty. Requires a valid ERC-8004 identity (posterAgentId must be owned " +
      "by your own wallet, on-chain verified) -- fail-closed, no unverified poster. Funds the bounty " +
      "into escrow IMMEDIATELY via a real gasless on-chain settle (poster -> escrow, through the " +
      "self-host x402 facilitator) -- if identity verification or the settle fails, no gig is created. " +
      "Returns the new gig id.",
    inputSchema: {
      posterPrivateKey: z.string().describe("0x-prefixed private key of the posting agent's own wallet (also proves poster identity for later gig_verify_and_pay calls)"),
      posterAgentId: z.string().describe("your ERC-8004 agentId (from identity_register) -- verified on-chain to be owned by your own wallet"),
      taskSpec: z.string().describe("what the taker must deliver"),
      bountyUsdcBase: z.number().int().positive().describe("bounty in USDC base units (6 decimals; 1000 = 0.001 USDC)"),
    },
  },
  async ({ posterPrivateKey, posterAgentId, taskSpec, bountyUsdcBase }) =>
    textResult(await gigPost({ posterPrivateKey, posterAgentId, taskSpec, bountyUsdcBase }))
);

server.registerTool(
  "gig_list",
  {
    title: "List gigs",
    description: "List gigs on the board, optionally filtered by status (open|taken|delivered|paid|rejected).",
    inputSchema: {
      status: z.enum(["open", "taken", "delivered", "paid", "rejected"]).optional(),
    },
  },
  async ({ status }) => textResult(await gigList({ status }))
);

server.registerTool(
  "gig_take",
  {
    title: "Take a gig",
    description:
      "Claim an OPEN gig as its taker. Requires a valid ERC-8004 identity (takerAgentId must be owned " +
      "by takerAddress, on-chain verified) -- fail-closed, no unverified taker. Fails if the gig is not " +
      "currently 'open', or if two takers race for it (only one wins).",
    inputSchema: {
      gigId: z.string(),
      takerAddress: z.string().describe("the taking agent's own wallet address (receives payout later)"),
      takerAgentId: z.string().describe("your ERC-8004 agentId (from identity_register) -- verified on-chain to be owned by takerAddress"),
    },
  },
  async ({ gigId, takerAddress, takerAgentId }) => textResult(await gigTake({ gigId, takerAddress, takerAgentId }))
);

server.registerTool(
  "gig_deliver",
  {
    title: "Deliver a gig",
    description: "Submit the deliverable for a gig you've taken. Fails if the gig is not currently 'taken'.",
    inputSchema: {
      gigId: z.string(),
      deliverable: z.string().describe("the delivered result (URL, text, or content hash)"),
    },
  },
  async ({ gigId, deliverable }) => textResult(await gigDeliver({ gigId, deliverable }))
);

server.registerTool(
  "gig_verify_and_pay",
  {
    title: "Verify and pay a gig",
    description:
      "POSTER-ONLY (enforced, not just documented): you must supply posterPrivateKey; its derived " +
      "address is checked against the gig's poster and the call is REJECTED if it doesn't match -- a " +
      "taker or anyone else can never verify/pay their own delivery. verified=true triggers a REAL " +
      "on-chain escrow release to the taker (re-verifying the taker's ERC-8004 identity first) and only " +
      "marks the gig 'paid' if that settle actually succeeds. verified=false rejects the delivery -- no " +
      "payout, ever. Concurrent calls for the same gig are serialized: at most one can ever pay.",
    inputSchema: {
      gigId: z.string(),
      verified: z.boolean(),
      posterPrivateKey: z.string().describe("0x-prefixed private key of the gig's poster -- proves you are authorized to verify/pay THIS gig"),
    },
  },
  async ({ gigId, verified, posterPrivateKey }) => textResult(await gigVerifyAndPay({ gigId, verified, posterPrivateKey }))
);

server.registerTool(
  "identity_register",
  {
    title: "Register an ERC-8004 identity",
    description:
      "Mint an ERC-8004 Trustless-Agent identity (on-chain ERC-721) owned by your own wallet, on the " +
      "live IdentityRegistry for this board's active network (GIG_CHAIN env var: base-sepolia testnet " +
      "by default, or base mainnet). Requires a small amount of native ETH on that network for gas " +
      "(register() is not gasless).",
    inputSchema: {
      privateKey: z.string().describe("0x-prefixed private key of the agent registering itself"),
    },
  },
  async ({ privateKey }) => textResult(await registerIdentity({ privateKey }))
);

server.registerTool(
  "identity_verify",
  {
    title: "Verify a counterparty's ERC-8004 identity",
    description: "Check on-chain whether `agentId` exists and is owned by `expectedAddress` -- the trust primitive for trading with a stranger.",
    inputSchema: {
      agentId: z.string(),
      expectedAddress: z.string(),
    },
  },
  async ({ agentId, expectedAddress }) => textResult(await verifyIdentity({ agentId, expectedAddress }))
);

await server.connect(new StdioServerTransport());
