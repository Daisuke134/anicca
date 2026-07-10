// spawn-funding-swap pure constants — REQ-006/REQ-003/REQ-007/REQ-012. Every value here is a literal,
// defined ONCE, in this one file, NEVER read from process.env/CLI flags/genome/config (REQ-006's
// single-choke-point discipline, mirrored for MIN_GAS_WEI/TOLERANCE_BPS per FIND-001/FIND-002). No
// second definition of any of these values is permitted anywhere else in this feature's codebase.

// USDC_DECIMALS_BASE — Base USDC's on-chain decimal precision (REQ-012).
export const USDC_DECIMALS_BASE = 6;

// AKT_DECIMALS — Akash uakt's on-chain decimal precision (REQ-001, REQ-012).
export const AKT_DECIMALS = 6;

// SWAP_MAX_USD — the hard, never-overridable per-invocation spend cap (REQ-006, NFR-3). A small literal
// consistent with this feature's own bootstrap scale (behavioral-spec.md cites a live-confirmed
// 15 USDC-in -> ~24.65 AKT-out quote); matches the exact illustrative value verification-architecture.md's
// PROP-019 description uses for its own worked example (`SWAP_MAX_USD=20`).
export const SWAP_MAX_USD = 20;

// MIN_GAS_WEI — the hard, never-overridable minimum Base-chain native-gas balance required before
// signing (REQ-003, FIND-001 fix). 0.001 ETH — a 25-100x margin over a typical single Base L2 tx's
// total fee (execution gas + L1 data fee), sized to cover both an ERC-20 approve tx and the swap-
// broadcast tx leg 1 may require, per behavioral-spec.md's REQ-003 reasoning. MUST NEVER be 0n.
export const MIN_GAS_WEI = 1_000_000_000_000_000n;

// TOLERANCE_BPS — the hard, never-overridable settlement slippage tolerance (REQ-007, FIND-002 fix).
// 50 bps (0.5%) — tight enough to reject a materially worse-than-quoted fill while tolerating ordinary
// multi-hop IBC rounding/fee dust, per behavioral-spec.md's REQ-007 reasoning.
export const TOLERANCE_BPS = 50;
