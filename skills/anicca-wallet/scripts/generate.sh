#!/usr/bin/env bash
# anicca-wallet/scripts/generate.sh
# Anicca own smart wallet を 生成 (pure offline keygen + optional CDP smart account)

set -uo pipefail
[ -f "$HOME/.openclaw/.env" ] && set -a && source "$HOME/.openclaw/.env" && set +a

SKILL_DIR="$HOME/.openclaw/skills/anicca-wallet"
STATE="$SKILL_DIR/state"
mkdir -p "$STATE"

if [ -f "$STATE/wallet.json" ]; then
  echo "[anicca-wallet] existing wallet found, skipping generation"
  cat "$STATE/wallet.json"
  exit 0
fi

# Method B: pure eth-account offline keygen (no network、 no third party)
python3 - <<'PYEOF'
import json, os, secrets, hashlib, time, pathlib

state_dir = pathlib.Path.home() / ".openclaw/skills/anicca-wallet/state"
state_dir.mkdir(parents=True, exist_ok=True)

try:
    from eth_account import Account
    Account.enable_unaudited_hdwallet_features()
except ImportError:
    print("[anicca-wallet] installing eth-account...", flush=True)
    import subprocess
    subprocess.check_call(["python3", "-m", "pip", "install", "--user", "-q", "eth-account"])
    from eth_account import Account
    Account.enable_unaudited_hdwallet_features()

# Generate new mnemonic + account
acct, mnemonic = Account.create_with_mnemonic()
address = acct.address
private_key = acct.key.hex()

# Encrypt private key with passphrase (= WALLET_VAULT_PASS or random)
vault_pass = os.environ.get("WALLET_VAULT_PASS") or secrets.token_urlsafe(32)
encrypted = Account.encrypt(private_key, vault_pass)

# Save (key encrypted, address public)
(state_dir / "wallet.json").write_text(json.dumps({
    "address": address,
    "network": "base",
    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "type": "eoa_eth_account_offline",
    "encrypted_key_path": "state/wallet.encrypted",
}, indent=2))

(state_dir / "wallet.encrypted").write_text(json.dumps(encrypted, indent=2))
(state_dir / "wallet.encrypted").chmod(0o600)

# Mnemonic = ONE-TIME display only, write to a one-time file that should be backed up
(state_dir / "MNEMONIC_BACKUP_ONCE.txt").write_text(
    f"# Anicca wallet seed phrase - BACKUP IMMEDIATELY and delete this file\n# Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n\n{mnemonic}\n"
)
(state_dir / "MNEMONIC_BACKUP_ONCE.txt").chmod(0o600)

# Save vault pass to .env (append) if not already set
env_path = pathlib.Path.home() / ".openclaw/.env"
env_content = env_path.read_text() if env_path.exists() else ""
if "WALLET_VAULT_PASS=" not in env_content:
    with env_path.open("a") as f:
        f.write(f"\n# anicca-wallet vault password (auto-generated {time.strftime('%Y-%m-%d')})\nWALLET_VAULT_PASS={vault_pass}\n")
    env_path.chmod(0o600)
    print(f"[anicca-wallet] vault pass saved to ~/.openclaw/.env")

# Anicca own wallet address - also save to .env
if "ANICCA_WALLET_ADDR=" not in env_content:
    with env_path.open("a") as f:
        f.write(f"ANICCA_WALLET_ADDR={address}\n")

print(f"\n[anicca-wallet] ✓ Generated new wallet:")
print(f"  address: {address}")
print(f"  network: base (Base L2)")
print(f"  encrypted_key: {state_dir / 'wallet.encrypted'}")
print(f"  MNEMONIC: see {state_dir / 'MNEMONIC_BACKUP_ONCE.txt'} (delete after backup)")
print(f"  Add to wallets: import via mnemonic in Coinbase Wallet / MetaMask / Rainbow")
PYEOF
