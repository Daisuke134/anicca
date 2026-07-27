import { prisma } from './prisma.js';

const ADDRESS = /^0x[0-9a-f]{40}$/;
const TRANSACTION = /^0x[0-9a-f]{64}$/;
const ROUTE = /^\/[a-z0-9][a-z0-9/_-]{0,126}$/;
const NETWORK = /^[a-z0-9]+:[a-zA-Z0-9._-]{1,64}$/;

function address(value) {
  const normalized = String(value || '').toLowerCase();
  return ADDRESS.test(normalized) ? normalized : null;
}

function transaction(value) {
  const normalized = String(value || '').toLowerCase();
  return TRANSACTION.test(normalized) ? normalized : null;
}

function settlementRow(row) {
  const request = row?.requestPayload;
  const response = row?.responsePayload;
  const createdAt = row?.createdAt instanceof Date ? row.createdAt : new Date(row?.createdAt);
  const observedAt = Number.isNaN(createdAt.getTime()) ? null : createdAt.toISOString();
  if (!row?.id || !observedAt || !request || !response) return null;
  return {
    id: row.id,
    observed_at: observedAt,
    route: request.route,
    method: request.method,
    scheme: request.scheme,
    network: request.network,
    asset: request.asset,
    amount_atomic: request.amount_atomic,
    pay_to: request.pay_to,
    transaction: response.transaction,
    payer: response.payer,
    success: response.success === true,
  };
}

export function settlementAuditData(context) {
  const requirements = context?.requirements;
  const result = context?.result;
  const request = context?.transportContext?.request;
  const route = String(request?.path || '').toLowerCase();
  const method = String(request?.method || '').toUpperCase();
  const scheme = String(requirements?.scheme || '').toLowerCase();
  const network = String(requirements?.network || '');
  const asset = address(requirements?.asset);
  const payTo = address(requirements?.payTo);
  const payer = address(result?.payer);
  const tx = transaction(result?.transaction);
  const amount = String(requirements?.amount || '');

  if (result?.success !== true
    || !ROUTE.test(route)
    || !['GET', 'POST'].includes(method)
    || scheme !== 'exact'
    || !NETWORK.test(network)
    || !asset
    || !payTo
    || !payer
    || !tx
    || !/^[1-9]\d*$/.test(amount)) {
    return null;
  }

  return {
    eventType: 'x402_settlement',
    executedBy: 'x402_facilitator',
    requestPayload: {
      route,
      method,
      scheme,
      network,
      asset,
      amount_atomic: amount,
      pay_to: payTo,
    },
    responsePayload: {
      success: true,
      transaction: tx,
      payer,
    },
  };
}

export async function recordSettlement(context, {
  prismaClient = prisma,
  logger = console,
} = {}) {
  const data = settlementAuditData(context);
  if (!data) return false;
  try {
    await prismaClient.agentAuditLog.create({ data });
    return true;
  } catch {
    // Settlement has already happened. Never turn a successful paid response into
    // a retry/double-payment risk because the public audit feed is unavailable.
    logger.error('x402 settlement audit persistence failed');
    return false;
  }
}

export async function listSettlementRecords({
  prismaClient = prisma,
  limit = 100,
} = {}) {
  const boundedLimit = Math.min(100, Math.max(1, Number.isInteger(Number(limit)) ? Number(limit) : 100));
  const rows = await prismaClient.agentAuditLog.findMany({
    where: { eventType: 'x402_settlement' },
    orderBy: { createdAt: 'desc' },
    take: boundedLimit,
    select: {
      id: true,
      createdAt: true,
      requestPayload: true,
      responsePayload: true,
    },
  });
  return rows.map(settlementRow).filter(Boolean);
}
