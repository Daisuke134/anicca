#!/usr/bin/env python3
"""anicca-payout-ubi — weekly UBI fan-out (dry-run by default).

Reads:
  - CFO state at ~/.openclaw/skills/cfo-core/data/anicca-cfo.json
    (override path via ANICCA_PAYOUT_CFO_OVERRIDE for tests)
  - Recipients at ~/.hermes/state/ubi-recipients.json
    (override via ANICCA_PAYOUT_RECIPIENTS_OVERRIDE for tests)

Computes:
  reserve_usd      = runtime_monthly * reserve_months          (default 3)
  distributable    = max(0, wallet_usd - reserve_usd)
  total_payout_usd = round(distributable * payout_percent/100, 2)
  per recipient    = round(total_payout_usd * weight/100, 2)

Modes (defense in depth — broadcast requires THREE independent signals):
  default (no flags, or --dry-run) → action="dry-run", logs and exits 0.
  --confirm WITHOUT env ANICCA_PAYOUT_LIVE=1 → action="refused-no-live-env", exits 0.
  --confirm AND ANICCA_PAYOUT_LIVE=1 BUT any recipient row has allow_live!=True
    OR label=="PLACEHOLDER" → action="live-recipient-validation-failed", exits NON-ZERO,
    NOTHING is sent.
  --confirm AND ANICCA_PAYOUT_LIVE=1 AND all recipients pass live validation →
    signs + broadcasts via wallet_lib.load_signer() (#324 P2) on Base; logs each tx.

Signer: imports wallet_lib from ../anicca-wallet/scripts/wallet_lib.py
(canonical Anicca wallet at 0xa3CDd4Ec…; same chokepoint as #324 x402).
NO cdp CLI dependency.

Pre-flight guard: invokes anicca-constitution-guard --action "<description>" on
EVERY mode (dry-run included). Missing guard symlink is FAIL-CLOSED in production;
ONLY when env ANICCA_PAYOUT_TEST=1 does missing-guard return OK (for tests that run
before symlink install).

Append-only log: ~/.hermes/state/payout.jsonl (one JSON line per invocation).
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
STATE_DIR = HOME / ".hermes" / "state"
LOG = STATE_DIR / "payout.jsonl"
DEFAULT_CFO = HOME / ".openclaw" / "skills" / "cfo-core" / "data" / "anicca-cfo.json"
DEFAULT_RECIPIENTS = STATE_DIR / "ubi-recipients.json"
OPENCLAW_ENV = HOME / ".openclaw" / ".env"

GUARD = HOME / ".hermes" / "skills" / "anicca-constitution-guard" / "scripts" / "check.sh"
# #324 P2 wallet_lib chokepoint — single sign path across all anicca-oss skills.
WALLET_LIB_DIR = Path("/Users/anicca/anicca-oss/skills/anicca-wallet/scripts")
# Base mainnet USDC contract (Coinbase canonical) — re-exported via wallet_lib.BASE_USDC
BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


def env_from_file(name: str, default: str = "") -> str:
    try:
        txt = OPENCLAW_ENV.read_text()
    except Exception:
        return default
    m = re.search(rf"^{name}=(.*)$", txt, re.M)
    if not m:
        return default
    return m.group(1).strip().strip('"').strip("'")


def read_cfo() -> dict:
    path = Path(os.environ.get("ANICCA_PAYOUT_CFO_OVERRIDE", str(DEFAULT_CFO)))
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def read_recipients() -> dict:
    path = Path(os.environ.get("ANICCA_PAYOUT_RECIPIENTS_OVERRIDE",
                               str(DEFAULT_RECIPIENTS)))
    try:
        d = json.loads(path.read_text())
    except Exception:
        return {"recipients": [], "payout_percent": 10, "reserve_months": 3}
    d.setdefault("payout_percent", 10)
    d.setdefault("reserve_months", 3)
    d.setdefault("recipients", [])
    return d


def derive(cfo: dict) -> tuple[float, float]:
    spends = cfo.get("spends") or {}
    runtime_monthly = float(spends.get("anicca_runtime_usd") or 0)
    wallet_block = cfo.get("wallet") or {}
    wallet_usd = float(
        wallet_block.get("base_usdc") or
        wallet_block.get("usd_total") or
        (cfo.get("lifeline") or {}).get("wallet_usd") or 0
    )
    return wallet_usd, runtime_monthly


def validate_recipients(recipients: list) -> tuple[bool, str]:
    """Schema-level validation (runs on every mode)."""
    if not recipients:
        return False, "no_recipients_configured"
    total = sum(float(r.get("weight", 0)) for r in recipients)
    if abs(total - 100.0) > 0.01:
        return False, f"weights_dont_sum_to_100 (got {total})"
    for r in recipients:
        addr = r.get("address", "")
        if not re.match(r"^0x[a-fA-F0-9]{40}$", addr):
            return False, f"bad_address {addr!r}"
    return True, ""


def validate_recipients_for_live(recipients: list) -> tuple[bool, str]:
    """Codex P4-burn-address-live-risk: BEFORE any broadcast every row MUST have
    allow_live==True AND label!="PLACEHOLDER". A single missing flag aborts the
    whole run — fail closed, no partial sends. This is the third defense layer
    on top of --confirm flag and ANICCA_PAYOUT_LIVE=1."""
    for r in recipients:
        label = (r.get("label") or "").strip()
        if label.upper() == "PLACEHOLDER":
            return False, (f"label PLACEHOLDER blocks live broadcast for "
                           f"{r.get('address')!r} — edit ubi-recipients.json")
        if r.get("allow_live") is not True:
            return False, (f"allow_live must be true for {r.get('address')!r} "
                           f"(got {r.get('allow_live')!r}) — edit ubi-recipients.json")
    return True, ""


def round2(x: float) -> float:
    return round(x + 1e-9, 2)


def call_guard(action_text: str) -> tuple[int, str]:
    """Codex P4-guard-bypass-ok: production MUST fail closed when the guard
    symlink is absent. The 'guard_not_installed OK' bypass is allowed ONLY when
    env ANICCA_PAYOUT_TEST=1 (so the RED test in Task 2, which runs before the
    symlink lands in Task 3 Step 8, can proceed)."""
    if not GUARD.exists():
        if os.environ.get("ANICCA_PAYOUT_TEST") == "1":
            return 0, json.dumps({"decision": "OK", "reason": "guard_not_installed_test_mode"})
        # Fail closed — exit code 2 (= same as BLOCKED rule match)
        return 2, json.dumps({"decision": "BLOCKED", "reason": "guard_not_installed"})
    out = subprocess.run([str(GUARD), "--action", action_text],
                         capture_output=True, text=True, timeout=10)
    return out.returncode, out.stdout.strip()


def send_via_wallet_lib(to_addr: str, amount_usd: float) -> str | None:
    """Codex P4-cdp-unverified: signing path uses the #324 P2 wallet_lib
    chokepoint, NOT the cdp CLI. wallet_lib.load_signer() returns (address, signer)
    where signer is an eth_account LocalAccount and address is the canonical
    Anicca wallet (asserted by wallet_lib.EXPECTED_ADDRESS). The exact RPC path
    is documented in this plan's HARD RULE #-1 disclosure block."""
    if str(WALLET_LIB_DIR) not in sys.path:
        sys.path.insert(0, str(WALLET_LIB_DIR))
    try:
        import wallet_lib  # type: ignore  # ships from #324 P2
    except ModuleNotFoundError:
        sys.stderr.write(
            "[payout-ubi] wallet_lib not found — run #324 P2 (2026-06-04-wallet-x402.md) first\n"
        )
        return None
    try:
        from_addr, signer = wallet_lib.load_signer()
    except Exception as exc:
        sys.stderr.write(f"[payout-ubi] wallet_lib.load_signer failed: {exc!r}\n")
        return None
    atomic = round(amount_usd * 1_000_000)  # USDC = 6 decimals
    # The actual EIP-3009 transferWithAuthorization build + send is implemented
    # in wallet_lib.send_usdc() (helper added in #324 P2). If that helper is
    # absent in your wallet_lib version, escalate to #324 maintainer — do NOT
    # fall back to cdp.
    if not hasattr(wallet_lib, "send_usdc"):
        sys.stderr.write(
            "[payout-ubi] wallet_lib.send_usdc() missing — add helper in #324 P2 then retry\n"
        )
        return None
    try:
        tx_hash = wallet_lib.send_usdc(signer=signer, to_addr=to_addr, amount_atomic=atomic)
    except Exception as exc:
        sys.stderr.write(f"[payout-ubi] wallet_lib.send_usdc failed: {exc!r}\n")
        return None
    # Defensive: ensure 0x… 32-byte hex tx hash shape
    if not (isinstance(tx_hash, str) and re.match(r"^0x[a-fA-F0-9]{64}$", tx_hash)):
        sys.stderr.write(f"[payout-ubi] unexpected tx_hash shape: {tx_hash!r}\n")
        return None
    return tx_hash


def write_log(row: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", default=False,
                    help="Default. Compute amounts, log decision, do NOT broadcast.")
    ap.add_argument("--confirm", action="store_true", default=False,
                    help="Required to broadcast. Also requires env ANICCA_PAYOUT_LIVE=1.")
    args = ap.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cfo = read_cfo()
    cfg = read_recipients()
    wallet_usd, runtime_monthly = derive(cfo)
    payout_pct = float(cfg.get("payout_percent", 10))
    reserve_months = float(cfg.get("reserve_months", 3))
    reserve_usd = round2(runtime_monthly * reserve_months)
    distributable = max(0.0, wallet_usd - reserve_usd)
    total_payout = round2(distributable * payout_pct / 100.0)

    # Guard MUST run on every invocation (even dry-run) — audit-first design.
    guard_action = (
        f"UBI weekly payout: wallet={wallet_usd:.2f} USDC, reserve={reserve_usd:.2f}, "
        f"distribute={total_payout:.2f} to {len(cfg.get('recipients', []))} recipient(s) on Base"
    )
    grc, gout = call_guard(guard_action)
    if grc != 0:
        try:
            guard_reason = json.loads(gout).get("reason", "guard_blocked")
        except Exception:
            guard_reason = "guard_blocked"
        row = {"ts": ts, "action": "blocked-by-guard", "reason": guard_reason,
               "guard_rc": grc, "guard_out": gout, "wallet_usd": wallet_usd,
               "runtime_monthly": runtime_monthly, "reserve_usd": reserve_usd,
               "would_send_usd": total_payout}
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return grc

    # Validate recipients
    ok, why = validate_recipients(cfg.get("recipients", []))
    if not ok:
        row = {"ts": ts, "action": "invalid-recipients", "reason": why,
               "wallet_usd": wallet_usd, "runtime_monthly": runtime_monthly,
               "reserve_usd": reserve_usd, "would_send_usd": total_payout}
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return 0

    # If nothing to distribute, log and exit OK
    if total_payout <= 0:
        row = {"ts": ts, "action": "below-threshold",
               "wallet_usd": wallet_usd, "runtime_monthly": runtime_monthly,
               "reserve_usd": reserve_usd, "would_send_usd": 0.0,
               "distributable": distributable}
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return 0

    # Compute per-recipient amounts
    rec_breakdown = []
    for r in cfg["recipients"]:
        amt = round2(total_payout * float(r["weight"]) / 100.0)
        rec_breakdown.append({
            "address": r["address"],
            "weight": float(r["weight"]),
            "amount_usd": amt,
            "label": r.get("label", ""),
        })

    # Refuse broadcast unless BOTH --confirm AND env are set
    live_env = os.environ.get("ANICCA_PAYOUT_LIVE") == "1"
    if args.confirm and not live_env:
        row = {"ts": ts, "action": "refused-no-live-env",
               "reason": "set ANICCA_PAYOUT_LIVE=1 in env to enable broadcast",
               "wallet_usd": wallet_usd, "runtime_monthly": runtime_monthly,
               "reserve_usd": reserve_usd, "would_send_usd": total_payout,
               "recipients": rec_breakdown}
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return 0

    if not args.confirm:
        # Default dry-run
        row = {"ts": ts, "action": "dry-run",
               "wallet_usd": wallet_usd, "runtime_monthly": runtime_monthly,
               "reserve_usd": reserve_usd, "would_send_usd": total_payout,
               "recipients": rec_breakdown}
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return 0

    # Codex P4-burn-address-live-risk: third defense layer before broadcast.
    # Every recipient row must have allow_live==True AND label!="PLACEHOLDER".
    live_ok, live_why = validate_recipients_for_live(cfg["recipients"])
    if not live_ok:
        row = {"ts": ts, "action": "live-recipient-validation-failed",
               "reason": live_why,
               "wallet_usd": wallet_usd, "runtime_monthly": runtime_monthly,
               "reserve_usd": reserve_usd, "would_send_usd": total_payout,
               "recipients": rec_breakdown,
               "sent": []}
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return 2  # non-zero — refuse to proceed

    # --confirm + ANICCA_PAYOUT_LIVE=1 + all live-validation passed → REAL broadcast
    # Signing via wallet_lib chokepoint from #324 P2 (NOT cdp CLI).
    sent = []
    failed = []
    for r in rec_breakdown:
        if r["amount_usd"] <= 0:
            continue
        tx = send_via_wallet_lib(r["address"], r["amount_usd"])
        if tx:
            sent.append({**r, "tx_hash": tx,
                         "basescan": f"https://basescan.org/tx/{tx}"})
        else:
            failed.append(r)
    row = {"ts": ts,
           "action": "sent" if sent and not failed else ("partial" if sent else "send-failed"),
           "wallet_usd": wallet_usd, "runtime_monthly": runtime_monthly,
           "reserve_usd": reserve_usd, "total_payout_usd": total_payout,
           "sent": sent, "failed": failed}
    write_log(row)
    print(json.dumps(row, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
