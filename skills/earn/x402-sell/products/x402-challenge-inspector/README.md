# x402 Challenge Inspector

A dependency-free Node.js module and CLI for inspecting an x402 v2 Payment-Required challenge before a caller builds a payment.

The inspector works offline and accepts a plain object, JSON string, or Base64 header value. It rejects unsupported versions, non-exact schemes, malformed CAIP-2 EVM networks, invalid amounts or addresses, unsafe timeout values, duplicate requirements, and inputs larger than 64 KiB.

Only these fields are returned:

- `x402Version`
- `scheme`
- `network`
- `amount`
- `asset`
- `payTo`
- `maxTimeoutSeconds`

Unknown fields are not copied into output.

## Test

```bash
npm test
```

## Library

```js
import { inspectX402Challenge } from './src/inspector.mjs';

const safeSummary = inspectX402Challenge(paymentRequiredHeader);
```

## CLI

Pipe a JSON or Base64 challenge into standard input:

```bash
printf '%s' "$PAYMENT_REQUIRED" | node bin/inspect.mjs
```

The CLI prints one allowlisted JSON summary or exits non-zero. It does not make network requests, sign messages, create payments, or persist the input.

## Boundary

This component validates challenge shape only. It does not establish merchant identity, service quality, payment safety, settlement, delivery, or profitability. Buyers must apply their own policy before paying.

## License

Offered under the SpawnXchange Standard Buyer License v1. See `LICENSE`.
