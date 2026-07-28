import { privateKeyToAccount } from 'viem/accounts';
import {
  createPaymentPayload,
  extractPaymentDetails,
  parsePaymentRequired,
} from '@blockrun/llm';

export const BLOCKRUN_IMAGE_URL = 'https://blockrun.ai/api/v1/images/generations';
export const GPT_IMAGE_MODEL = 'openai/gpt-image-2';
export const USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

const USER_AGENT = 'anicca-taskmarket-work/1.0';

function parseQuote(header) {
  if (!header) throw new Error('image response has no payment-required header');
  const required = parsePaymentRequired(header);
  const details = extractPaymentDetails(required);
  if (!details || !/^\d+$/.test(String(details.amount || ''))) {
    throw new Error('image quote amount is invalid');
  }
  return {
    required,
    details,
    amountUsd: Number(BigInt(details.amount)) / 1_000_000,
  };
}

async function defaultCreateSignature({ walletKey, details, required }) {
  const account = privateKeyToAccount(walletKey);
  return createPaymentPayload(
    walletKey,
    account.address,
    details.recipient,
    details.amount,
    details.network,
    {
      resourceUrl: details.resource?.url || BLOCKRUN_IMAGE_URL,
      resourceDescription: details.resource?.description || 'BlockRun GPT Image 2 generation',
      maxTimeoutSeconds: details.maxTimeoutSeconds || 600,
      extra: details.extra,
      extensions: required.extensions,
    },
  );
}

async function imageResult(response, costUsd) {
  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error('image response is not JSON');
  }
  const url = body?.data?.[0]?.url;
  if (typeof url !== 'string' || !/^https:\/\//i.test(url) || body.data.length !== 1) {
    throw new Error('image response must contain one HTTPS image URL');
  }
  return {
    url,
    model: GPT_IMAGE_MODEL,
    costUsd,
    created: body.created ?? null,
  };
}

export async function generateImage({
  prompt,
  walletKey,
  fetchImpl = fetch,
  createSignature = defaultCreateSignature,
  reserveSpend = async () => {},
  maxQuoteUsd = 0.07,
}) {
  if (typeof prompt !== 'string' || prompt.trim().length === 0 || prompt.length > 12_000) {
    throw new Error('image prompt must contain 1..12000 characters');
  }
  if (!/^0x[0-9a-fA-F]{64}$/.test(String(walletKey || ''))) {
    throw new Error('agent image wallet key is missing or invalid');
  }
  const body = JSON.stringify({
    model: GPT_IMAGE_MODEL,
    prompt,
    size: '1024x1024',
    n: 1,
  });
  const request = {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': USER_AGENT,
    },
    body,
  };
  const challenge = await fetchImpl(BLOCKRUN_IMAGE_URL, request);
  if (challenge.status === 200) return imageResult(challenge, 0);
  if (challenge.status !== 402) {
    throw new Error(`image challenge returned HTTP ${challenge.status}`);
  }

  const header = challenge.headers.get('payment-required')
    || challenge.headers.get('x-payment-required');
  const quote = parseQuote(header);
  if (quote.details.network !== 'eip155:8453') {
    throw new Error('image quote is not for Base mainnet');
  }
  if (String(quote.details.asset || '').toLowerCase() !== USDC_BASE.toLowerCase()) {
    throw new Error('image quote is not for Base USDC');
  }
  if (!Number.isFinite(quote.amountUsd) || quote.amountUsd <= 0
    || quote.amountUsd > Number(maxQuoteUsd) + Number.EPSILON) {
    throw new Error(`image quote exceeds ${maxQuoteUsd} USDC cap`);
  }

  const signature = await createSignature({
    walletKey,
    details: quote.details,
    required: quote.required,
    amountUsd: quote.amountUsd,
  });
  await reserveSpend(quote.amountUsd);
  const paid = await fetchImpl(BLOCKRUN_IMAGE_URL, {
    ...request,
    headers: {
      ...request.headers,
      'PAYMENT-SIGNATURE': signature,
    },
  });
  if (paid.status !== 200) {
    throw new Error(`paid image generation returned HTTP ${paid.status}`);
  }
  return imageResult(paid, quote.amountUsd);
}
