/**
 * F1 RED tests — founder-x402-self-facilitate (Phase 2a)
 *
 * Spec: ~/anicca/.vcsdd/features/founder-x402-self-facilitate/specs/behavioral-spec.md (iter-3, adversary PASS)
 * Verif: ~/anicca/.vcsdd/features/founder-x402-self-facilitate/specs/verification-architecture.md (iter-2)
 *
 * These tests target the POST-swap state of src/server.js (in-process x402Facilitator,
 * single POST /social/x, Base mainnet, payTo=X402_WALLET_ADDRESS, no CDP/Railway/Prisma/OpenAI).
 * They are EXPECTED TO FAIL against the current HTTPFacilitatorClient impl — that's the RED phase.
 *
 * Covers all 17 Tier-0 PROPs (some via static source-text checks, some via import-based unit
 * checks of the exported ROUTES constant + validateEnv() + resolveAcceptsAmount()).
 */

import { describe, it, expect, test, beforeAll } from 'vitest';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SRC_DIR = path.resolve(__dirname, '..');
const SERVER_JS = path.join(SRC_DIR, 'server.js');

let SOURCE = '';
beforeAll(() => {
  SOURCE = readFileSync(SERVER_JS, 'utf-8');
});

const TEST_KEY = '0x' + 'a'.repeat(64);
const TEST_ADDR = '0x' + 'b'.repeat(40);
const USDC_BASE_MAINNET = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913';

describe('PROP-001a [Tier 0] REQ-001 i+ii: viem walletClient on Base mainnet', () => {
  test('uses privateKeyToAccount(process.env.EVM_PRIVATE_KEY)', () => {
    expect(SOURCE).toMatch(/privateKeyToAccount\(\s*process\.env\.EVM_PRIVATE_KEY\b/);
  });
  test('createWalletClient with chain: base', () => {
    expect(SOURCE).toMatch(/createWalletClient\s*\([^)]*chain:\s*base/);
  });
});

describe('PROP-001b [Tier 0] REQ-001 iii: toFacilitatorEvmSigner wrapper', () => {
  test('imports + calls toFacilitatorEvmSigner exactly once (non-comment)', () => {
    const lines = SOURCE.split('\n').filter(
      (l) => !l.trim().startsWith('//') && !l.trim().startsWith('*'),
    );
    const code = lines.join('\n');
    const matches = code.match(/toFacilitatorEvmSigner\s*\(/g) || [];
    expect(matches.length).toBe(1);
  });
});

describe('PROP-001c [Tier 0] REQ-001 iv+v: in-process x402Facilitator + registerExactEvmScheme', () => {
  test('new x402Facilitator() appears exactly once', () => {
    const matches = SOURCE.match(/new\s+x402Facilitator\(\)/g) || [];
    expect(matches.length).toBe(1);
  });
  test('registerExactEvmScheme(facilitator, ...) appears exactly once', () => {
    const matches = SOURCE.match(/registerExactEvmScheme\(\s*facilitator\s*,/g) || [];
    expect(matches.length).toBe(1);
  });
});

describe('PROP-001d [Tier 0] REQ-001 vi+vii: x402ResourceServer.register + ExactEvmServerScheme', () => {
  // The current CDP impl calls `new x402ResourceServer(facilitatorClient)` (positional arg).
  // The in-process target calls `new x402ResourceServer({ verify, settle, getSupported })` (object-literal arg
  // bound to the in-process facilitator). The PROP requires the object-literal pattern.
  test('x402ResourceServer is constructed with in-process facilitator object-literal', () => {
    expect(SOURCE).toMatch(/new\s+x402ResourceServer\s*\(\s*\{/);
    expect(SOURCE).toMatch(/verify\s*:\s*facilitator\.verify/);
    // settle may be wrapped (e.g. wrapSettle(facilitator.settle.bind(facilitator))) for
    // REQ-014 logging — accept either form as long as facilitator.settle is referenced.
    expect(SOURCE).toMatch(/settle\s*:[^,\n]*facilitator\.settle/);
    expect(SOURCE).toMatch(/getSupported\s*:/);
  });
  test('.register(<base-mainnet>, new ExactEvmServerScheme()) appears exactly once', () => {
    // Accept either the literal "eip155:8453" or a named constant referencing it (REQ-016
    // forbids duplicating the literal; the const indirection is the canonical fix).
    const literal =
      SOURCE.match(/\.register\s*\(\s*["']eip155:8453["']\s*,\s*new\s+ExactEvmServerScheme/g) || [];
    const namedConst =
      SOURCE.match(/\.register\s*\(\s*[A-Z_][A-Z0-9_]*\s*,\s*new\s+ExactEvmServerScheme/g) || [];
    expect(literal.length + namedConst.length).toBe(1);
  });
});

describe('PROP-002 [Tier 0] REQ-002: ROUTES singleton bound to X402_WALLET_ADDRESS', () => {
  test('server.js exports ROUTES constant', async () => {
    const mod = await import('../server.js');
    expect(mod.ROUTES).toBeDefined();
  });
  test('exactly one paid route key = "POST /social/x"', async () => {
    const mod = await import('../server.js');
    expect(Object.keys(mod.ROUTES).length).toBe(1);
    expect(Object.keys(mod.ROUTES)[0]).toBe('POST /social/x');
  });
  test('payTo equals process.env.X402_WALLET_ADDRESS at config time', async () => {
    process.env.X402_WALLET_ADDRESS = TEST_ADDR;
    const mod = await import('../server.js');
    expect(mod.ROUTES['POST /social/x'].accepts.payTo).toBe(TEST_ADDR);
  });
});

describe('PROP-003 [Tier 0, PROMOTED] REQ-003: Base MAINNET only, never Sepolia', () => {
  // Combined PRESENCE-of-mainnet + ABSENCE-of-sepolia check so the single test fails pre-impl
  // (the current CDP impl has no `import base from viem/chains` and DOES have `eip155:84532`).
  test('imports base from viem/chains AND zero Sepolia references', () => {
    const hasBaseImport =
      /import\s+\{[^}]*\bbase\b[^}]*\}\s+from\s+['"]viem\/chains['"]/.test(SOURCE);
    const hasSepoliaImport = /\bbaseSepolia\b/.test(SOURCE);
    const hasSepoliaCaip = /eip155:84532/.test(SOURCE);
    expect({ hasBaseImport, hasSepoliaImport, hasSepoliaCaip }).toEqual({
      hasBaseImport: true,
      hasSepoliaImport: false,
      hasSepoliaCaip: false,
    });
  });
});

describe('PROP-004 [Tier 0] REQ-004: POST /social/x accepts shape', () => {
  test('accepts has full mainnet shape including extra.asset', async () => {
    process.env.X402_WALLET_ADDRESS = TEST_ADDR;
    const mod = await import('../server.js');
    const a = mod.ROUTES['POST /social/x'].accepts;
    expect(a.scheme).toBe('exact');
    expect(a.price).toBe('$0.003');
    expect(a.network).toBe('eip155:8453');
    expect(a.payTo).toBe(TEST_ADDR);
    expect(a.mimeType).toBe('application/json');
    expect(a.maxTimeoutSeconds).toBe(60);
    expect(a.extra).toBeDefined();
    expect(a.extra.asset).toBe(USDC_BASE_MAINNET);
  });
});

describe('PROP-004b [Tier 0] REQ-004b: $0.003 resolves to 3000 USDC base units', () => {
  test('server.js exports resolveAcceptsAmount', async () => {
    const mod = await import('../server.js');
    expect(typeof mod.resolveAcceptsAmount).toBe('function');
  });
  test('resolveAcceptsAmount(accepts) === "3000"', async () => {
    const mod = await import('../server.js');
    const a = mod.ROUTES['POST /social/x'].accepts;
    expect(mod.resolveAcceptsAmount(a)).toBe('3000');
  });
});

describe('PROP-005 [Tier 0] REQ-005: Bazaar POST shape (SDK-aligned ext.bazaar.info)', () => {
  test('extensions.bazaar.info.input has type:http + method:POST + bodyType:json + raw body', async () => {
    const mod = await import('../server.js');
    const ext = mod.ROUTES['POST /social/x'].extensions;
    expect(ext).toBeDefined();
    expect(ext.bazaar).toBeDefined();
    expect(ext.bazaar.info).toBeDefined();
    expect(ext.bazaar.info.input).toBeDefined();
    expect(ext.bazaar.info.input.type).toBe('http');
    expect(ext.bazaar.info.input.method).toBe('POST');
    expect(ext.bazaar.info.input.bodyType).toBe('json');
    expect(ext.bazaar.info.input.body).toBeDefined();
    expect(typeof ext.bazaar.info.input.body).toBe('object');
    // Body should be a non-empty object (a realistic example), not an empty wrapper
    expect(Object.keys(ext.bazaar.info.input.body).length).toBeGreaterThan(0);
  });
  test('extensions.bazaar.info.output has type:json + non-empty example', async () => {
    const mod = await import('../server.js');
    const ext = mod.ROUTES['POST /social/x'].extensions;
    expect(ext.bazaar.info.output).toBeDefined();
    expect(ext.bazaar.info.output.type).toBe('json');
    expect(ext.bazaar.info.output.example).toBeDefined();
    expect(typeof ext.bazaar.info.output.example).toBe('object');
  });
  test('extensions.bazaar.schema.properties.input.properties.body exists (inputSchema fed in)', async () => {
    const mod = await import('../server.js');
    const ext = mod.ROUTES['POST /social/x'].extensions;
    expect(ext.bazaar.schema).toBeDefined();
    const bodySchema = ext.bazaar.schema?.properties?.input?.properties?.body;
    expect(bodySchema).toBeDefined();
    expect(bodySchema.type).toBe('object');
    // Schema should carry our inputSchema's properties (e.g. "query") — not default empty
    expect(bodySchema.properties).toBeDefined();
    expect(Object.keys(bodySchema.properties || {}).length).toBeGreaterThan(0);
  });
});

describe('PROP-006 [Tier 0, PROMOTED] REQ-006: validateEnv format check', () => {
  test('server.js exports validateEnv + MissingEnvError', async () => {
    const mod = await import('../server.js');
    expect(typeof mod.validateEnv).toBe('function');
    expect(typeof mod.MissingEnvError).toBe('function');
  });
  test('throws on missing EVM_PRIVATE_KEY', async () => {
    const { validateEnv, MissingEnvError } = await import('../server.js');
    expect(() =>
      validateEnv({ X402_WALLET_ADDRESS: TEST_ADDR }),
    ).toThrow(MissingEnvError);
  });
  test('throws on empty EVM_PRIVATE_KEY', async () => {
    const { validateEnv, MissingEnvError } = await import('../server.js');
    expect(() =>
      validateEnv({ EVM_PRIVATE_KEY: '', X402_WALLET_ADDRESS: TEST_ADDR }),
    ).toThrow(MissingEnvError);
  });
  test('throws on malformed EVM_PRIVATE_KEY (not 64-hex)', async () => {
    const { validateEnv, MissingEnvError } = await import('../server.js');
    expect(() =>
      validateEnv({ EVM_PRIVATE_KEY: 'notakey', X402_WALLET_ADDRESS: TEST_ADDR }),
    ).toThrow(MissingEnvError);
  });
  test('throws on malformed X402_WALLET_ADDRESS (not 40-hex)', async () => {
    const { validateEnv, MissingEnvError } = await import('../server.js');
    expect(() =>
      validateEnv({ EVM_PRIVATE_KEY: TEST_KEY, X402_WALLET_ADDRESS: 'notanaddr' }),
    ).toThrow(MissingEnvError);
  });
  test('accepts a valid env pair', async () => {
    const { validateEnv } = await import('../server.js');
    expect(() =>
      validateEnv({ EVM_PRIVATE_KEY: TEST_KEY, X402_WALLET_ADDRESS: TEST_ADDR }),
    ).not.toThrow();
  });
});

describe('PROP-006a [Tier 0] REQ-006: createApp() throws on bad env', () => {
  test('createApp rejects/throws when env is missing', async () => {
    const orig = { ...process.env };
    delete process.env.EVM_PRIVATE_KEY;
    delete process.env.X402_WALLET_ADDRESS;
    const mod = await import('../server.js');
    await expect(mod.createApp()).rejects.toThrow();
    Object.assign(process.env, orig);
  });
});

describe('PROP-007 [Tier 0] REQ-007 + REQ-017: zero forbidden imports under src/', () => {
  test('server.js has no forbidden imports / env refs', () => {
    const forbidden = [
      /@coinbase\/x402/,
      /\bCDP_API_KEY/,
      /x402\.org\/facilitator/,
      /\bRAILWAY_/,
      /\bDATABASE_URL\b/,
      /\bOPENAI_API_KEY\b/,
      /@prisma\/client/,
      /from\s+['"]openai['"]/,
      /require\(\s*['"]openai['"]\s*\)/,
      /from\s+['"]\.\/lib\/prisma['"]/,
      /HTTPFacilitatorClient/,
    ];
    const violations = forbidden.filter((re) => re.test(SOURCE)).map((re) => re.toString());
    expect(violations, `forbidden patterns matched: ${violations.join(', ')}`).toEqual([]);
  });
});

describe('PROP-008 + PROP-008b [Tier 0] REQ-008: /health pure, no prisma anywhere', () => {
  test('server.js does not contain the string "prisma" (case-insensitive)', () => {
    expect(SOURCE.toLowerCase()).not.toMatch(/prisma/);
  });
});

describe('PROP-011 [Tier 0] REQ-011: replicable boot — only EVM_PRIVATE_KEY + X402_WALLET_ADDRESS + PORT (+ X402_RPC_URL for test determinism)', () => {
  test('server boots with only required env, prints "listening on port" within 2s, deterministic (no live RPC)', async () => {
    const env = { ...process.env };
    // Strip everything else
    delete env.DATABASE_URL;
    delete env.OPENAI_API_KEY;
    delete env.CDP_API_KEY_ID;
    delete env.CDP_API_KEY_SECRET;
    delete env.X402_NETWORK;
    for (const k of Object.keys(env)) {
      if (k.startsWith('RAILWAY_')) delete env[k];
    }
    env.EVM_PRIVATE_KEY = TEST_KEY;
    env.X402_WALLET_ADDRESS = TEST_ADDR;
    env.PORT = '0';
    env.NODE_ENV = 'test';
    // X402_RPC_URL pinned to an unreachable local port keeps the gas probe deterministic
    // (no live Base mainnet RPC during tests — REQ-010 compliance).
    env.X402_RPC_URL = 'http://127.0.0.1:1';

    const child = spawn(process.execPath, [SERVER_JS], {
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (d) => (stdout += d.toString()));
    child.stderr.on('data', (d) => (stderr += d.toString()));
    await new Promise((res) => {
      const timer = setTimeout(() => res(), 2000);
      child.once('exit', () => {
        clearTimeout(timer);
        res();
      });
    });
    try {
      child.kill('SIGTERM');
    } catch {
      /* already dead */
    }
    const combined = stdout + '\n' + stderr;
    expect(
      combined.toLowerCase(),
      `expected "listening on port" in output. stdout=${stdout} stderr=${stderr}`,
    ).toMatch(/listening on port/);
  });
});

// ============================================================================
// PROP-014 (added iter-2 per Phase 3 adversary feedback): wrapSettle unit test
// ============================================================================
describe('PROP-014 [Tier 0] REQ-014: wrapSettle logs [x402.settle.error] + rethrows', () => {
  test('wrapSettle is exported', async () => {
    const mod = await import('../server.js');
    expect(typeof mod.wrapSettle).toBe('function');
  });

  test('wrapSettle re-raises the original error', async () => {
    const { wrapSettle } = await import('../server.js');
    const cause = Object.assign(new Error('low gas'), { code: 'insufficient_funds' });
    const errs = [];
    const orig = console.error;
    console.error = (...a) => errs.push(a.map((x) => String(x)).join(' '));
    try {
      const wrapped = wrapSettle(async () => {
        throw cause;
      });
      await expect(wrapped()).rejects.toBe(cause);
    } finally {
      console.error = orig;
    }
  });

  test('wrapSettle logs [x402.settle.error] with the error code + message snippet', async () => {
    const { wrapSettle } = await import('../server.js');
    const cause = Object.assign(new Error('rpc timeout details'), { code: 'rpc_timeout' });
    const errs = [];
    const orig = console.error;
    console.error = (...a) => errs.push(a.map((x) => String(x)).join(' '));
    try {
      const wrapped = wrapSettle(async () => {
        throw cause;
      });
      await wrapped().catch(() => {});
      const joined = errs.join('\n');
      expect(joined).toMatch(/\[x402\.settle\.error\]/);
      expect(joined).toMatch(/rpc_timeout/);
      expect(joined).toMatch(/rpc timeout details/);
    } finally {
      console.error = orig;
    }
  });

  test('wrapSettle passes through on success', async () => {
    const { wrapSettle } = await import('../server.js');
    const errs = [];
    const orig = console.error;
    console.error = (...a) => errs.push(a.map((x) => String(x)).join(' '));
    try {
      const wrapped = wrapSettle(async () => ({ success: true, payer: '0xabc' }));
      const result = await wrapped();
      expect(result).toEqual({ success: true, payer: '0xabc' });
      expect(errs.join('\n')).not.toMatch(/\[x402\.settle\.error\]/);
    } finally {
      console.error = orig;
    }
  });
});

describe('PROP-013 [Tier 0] REQ-013: USDC Base mainnet contract address pin', () => {
  test('USDC mainnet contract appears exactly once in server.js', () => {
    const matches = SOURCE.match(/0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913/g) || [];
    expect(matches.length).toBe(1);
  });
});

describe('PROP-016 [Tier 0] REQ-016: single source of truth literals', () => {
  // quote-agnostic count (single or double — JS style is arbitrary, what matters is uniqueness).
  test('the literal $0.003 appears exactly once (quote-agnostic)', () => {
    const matches = SOURCE.match(/['"]\$0\.003['"]/g) || [];
    expect(matches.length).toBe(1);
  });
  test('the literal eip155:8453 appears exactly once (quote-agnostic)', () => {
    const matches = SOURCE.match(/['"]eip155:8453['"]/g) || [];
    expect(matches.length).toBe(1);
  });
});

describe('PROP-017 [Tier 0] REQ-017: deferred route files moved out of src/', () => {
  const FORBIDDEN_ROUTE_FILES = [
    'buddhistCounsel.js',
    'contextCompressor.js',
    'decisionClarifier.js',
    'emotionDetector.js',
    'focusCoach.js',
    'habitDesigner.js',
    'intentRouter.js',
    'promptSanitizer.js',
  ];

  test('none of the 8 deferred route files exist under src/routes/', () => {
    const routesDir = path.join(SRC_DIR, 'routes');
    if (!existsSync(routesDir)) return;
    const files = readdirSync(routesDir);
    const found = FORBIDDEN_ROUTE_FILES.filter((f) => files.includes(f));
    expect(
      found,
      `the following deferred route files must be moved out of src/routes/: ${found.join(', ')}`,
    ).toEqual([]);
  });

  test('src/lib/prisma.js does not exist', () => {
    expect(existsSync(path.join(SRC_DIR, 'lib', 'prisma.js'))).toBe(false);
  });
});
