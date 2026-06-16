#!/usr/bin/env python3
"""execute-0xwork — the external-revenue executor run.sh calls for EARN_STRATEGY=0xwork.

Mirrors execute-swap.py's contract: reads env, drives 0xwork, prints ONE JSON line to stdout.
GATE-0 = EXTERNAL revenue: a third-party poster funds a USDC bounty into 0xwork escrow
(taskPool). On approval the escrow releases USDC FROM the poster INTO Anicca's wallet — the
payout tx has from = taskPool, not Anicca. A swap has no such transfer and can NEVER be GATE-0.

INPUTS (env):
  OXWORK_PKVAR / BLOCKRUN_WALLET_KEY   signing+receiving wallet (the ledger/usdc proof reads it)
  OXWORK_API        default https://api.0xwork.org
  OXWORK_TASK_ID    (optional) pin a specific task; else pickTask via discover
  OXWORK_DELIVER    path to the deliverable file the agent produced this wake (to submit)
  OXWORK_SUMMARY    reviewer-friendly description of the deliverable
  OXWORK_ANY_CATEGORY  "1" => allow any category (e.g. claim a "Social" task)
  OXWORK_POLL_SECS  default 0  (0 = do NOT block on approval; return claimed/awaiting -> NARRATE)

EXACT CALLS (CLI is the supported surface; @0xwork/cli installed, quickstart-verified):
  register (idempotent):  0xwork register --name=Anicca --capabilities=...
  discover:               0xwork discover --json --scope open   -> open tasks
  task details:           0xwork task <id> --json               -> status / payout_tx_hash
  claim:                  0xwork claim <id> --json              -> on-chain claim tx
  submit:                 0xwork submit <id> --files=$DELIVER --summary="..." --json
  payout (post-approval): the poster approves -> escrow releases USDC. The payout tx hash is
                          read from `0xwork task <id> --json` field payout_tx_hash (or related).
                          We do NOT fabricate it: if the task is not yet Completed/Paid,
                          payout_tx is "" and the wake NARRATEs (honest residual).

OUTPUT (stdout, one JSON object — same shape run.sh already parses):
  {"task_id": "<id>", "payout_tx": "0x<66hex>" | "", "status": "0x1" | "",
   "before_usdc": <n>, "after_usdc": <n>, "stage": "registered|claimed|submitted|paid|none"}
Errors print {"error": "<msg>"} and run.sh degrades to a NARRATE line (never bricks, never GATE-0).
NO HUMAN, NO CLAUDE: the agent picks/does/submits the task; this script only orchestrates the CLI
and surfaces the real, externally-approved payout tx. Claude verifies; Claude does not run it.
"""
import json
import os
import re
import subprocess
import sys
import time

API = os.environ.get("OXWORK_API", "https://api.0xwork.org")
TX_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
PAYOUT_FIELDS = (
    "payout_tx_hash",
    "payoutTxHash",
    "payout_tx",
    "payoutTx",
    "release_tx_hash",
    "releaseTxHash",
    "settlement_tx_hash",
)
DONE_STATES = {"completed", "paid", "approved", "released"}


def _run(args, timeout=120):
    """Run a 0xwork CLI command; return (rc, stdout, stderr)."""
    try:
        p = subprocess.run(
            ["0xwork", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy(),
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except FileNotFoundError:
        return 127, "", "0xwork CLI not found (npm i -g @0xwork/cli)"
    except subprocess.TimeoutExpired:
        return 124, "", f"0xwork {args[0]} timed out"


def _json(stdout):
    """Parse the last JSON object/array out of CLI --json output (tolerates banners)."""
    stdout = stdout.strip()
    if not stdout:
        return None
    try:
        return json.loads(stdout)
    except Exception:
        pass
    # find the largest {...} or [...] block
    for opener, closer in (("{", "}"), ("[", "]")):
        i = stdout.find(opener)
        j = stdout.rfind(closer)
        if i != -1 and j > i:
            try:
                return json.loads(stdout[i : j + 1])
            except Exception:
                continue
    return None


def _wallet_addr(key):
    try:
        from eth_account import Account

        return Account.from_key(key).address.lower()
    except Exception:
        return None


def _usdc_balance(addr):
    """USDC (6dp) balance on Base via eth_call balanceOf(address). 0.0 on any error."""
    if not addr:
        return 0.0
    try:
        import urllib.request

        rpc = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
        usdc = os.environ.get("USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
        data = "0x70a08231" + addr.replace("0x", "").rjust(64, "0")
        payload = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [{"to": usdc, "data": data}, "latest"],
            }
        ).encode()
        req = urllib.request.Request(
            rpc,
            data=payload,
            headers={"content-type": "application/json", "user-agent": "anicca-earn/1.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            j = json.loads(r.read())
        hexv = j.get("result") or "0x0"
        return int(hexv, 16) / 1e6 if hexv not in ("0x", "") else 0.0
    except Exception:
        return 0.0


def _find_payout_tx(detail):
    """Pull a real payout tx hash from task detail JSON; '' if not yet settled."""
    if not isinstance(detail, dict):
        return ""
    # unwrap a {task: {...}} envelope
    for container in (detail, detail.get("task") if isinstance(detail.get("task"), dict) else None):
        if not isinstance(container, dict):
            continue
        for f in PAYOUT_FIELDS:
            v = container.get(f)
            if isinstance(v, str) and TX_RE.match(v):
                return v
    return ""


def _task_status(detail):
    if not isinstance(detail, dict):
        return ""
    container = detail.get("task") if isinstance(detail.get("task"), dict) else detail
    return str(container.get("status", "")).lower()


def main():
    pkvar = os.environ.get("OXWORK_PKVAR") or os.environ.get("PKVAR", "BLOCKRUN_WALLET_KEY")
    key = os.environ.get(pkvar) or os.environ.get("BLOCKRUN_WALLET_KEY")
    if not key:
        print(json.dumps({"error": f"no wallet key in env ({pkvar})"}))
        sys.exit(2)
    wallet = _wallet_addr(key)
    before = _usdc_balance(wallet)

    # 1) register (idempotent — already-registered returns ok/no-op).
    _run(
        [
            "register",
            "--name=Anicca",
            "--description=autonomous research/writing/code agent",
            "--capabilities=Writing,Research,Code,Data,Social",
            "--framework=OpenClaw",
            "--json",
        ]
    )

    # 2) pick a task: pinned, or discover the first doable open task.
    task_id = os.environ.get("OXWORK_TASK_ID", "").strip()
    if not task_id:
        rc, out, err = _run(["discover", "--json", "--scope", "open", "--limit", "20"])
        data = _json(out)
        tasks = []
        if isinstance(data, dict):
            tasks = data.get("tasks") or data.get("results") or []
        elif isinstance(data, list):
            tasks = data
        any_cat = os.environ.get("OXWORK_ANY_CATEGORY") == "1"
        caps = {
            c.strip().lower()
            for c in os.environ.get("OXWORK_CAPS", "Writing,Research,Code,Data,Social").split(",")
        }
        for t in tasks:
            if not isinstance(t, dict):
                continue
            if str(t.get("status", "")).lower() != "open":
                continue
            stake = t.get("stake_amount")
            if not (stake is None or float(stake or 0) == 0):
                continue
            bounty = t.get("bounty_amount", t.get("bounty"))
            try:
                if not (float(bounty) > 0):
                    continue
            except Exception:
                continue
            if any_cat or str(t.get("category", "")).lower() in caps:
                task_id = str(t.get("id") or t.get("task_id") or t.get("chain_task_id") or "")
                if task_id:
                    break
    if not task_id:
        print(
            json.dumps(
                {
                    "task_id": "",
                    "payout_tx": "",
                    "status": "",
                    "before_usdc": before,
                    "after_usdc": before,
                    "stage": "none",
                }
            )
        )
        return

    # 3) already-settled? read detail first (idempotent re-entry across wakes).
    rc, out, err = _run(["task", task_id, "--json"])
    detail = _json(out)
    paytx = _find_payout_tx(detail)
    if paytx:
        after = _usdc_balance(wallet)
        print(
            json.dumps(
                {
                    "task_id": task_id,
                    "payout_tx": paytx,
                    "status": "0x1",
                    "before_usdc": before,
                    "after_usdc": after,
                    "stage": "paid",
                }
            )
        )
        return

    # 4) claim (best-effort; already-claimed-by-us is fine).
    _run(["claim", task_id, "--json"])

    # 5) submit the deliverable produced by the agent this wake.
    deliver = os.environ.get("OXWORK_DELIVER", "").strip()
    summary = os.environ.get(
        "OXWORK_SUMMARY", "Deliverable produced autonomously by Anicca for this task."
    )
    if deliver and os.path.exists(deliver):
        _run(["submit", task_id, f"--files={deliver}", f"--summary={summary}", "--json"])

    # 6) optionally poll for the approved payout (default 0 = do not block -> NARRATE).
    poll = int(os.environ.get("OXWORK_POLL_SECS", "0") or "0")
    deadline = time.time() + poll
    stage = "submitted"
    while True:
        rc, out, err = _run(["task", task_id, "--json"])
        detail = _json(out)
        paytx = _find_payout_tx(detail)
        if paytx:
            after = _usdc_balance(wallet)
            print(
                json.dumps(
                    {
                        "task_id": task_id,
                        "payout_tx": paytx,
                        "status": "0x1",
                        "before_usdc": before,
                        "after_usdc": after,
                        "stage": "paid",
                    }
                )
            )
            return
        if _task_status(detail) in DONE_STATES:
            stage = "paid-no-tx"
        if poll <= 0 or time.time() >= deadline:
            break
        time.sleep(min(15, max(1, deadline - time.time())))

    # No payout this wake -> honest NARRATE (claimed/submitted, awaiting poster approval).
    print(
        json.dumps(
            {
                "task_id": task_id,
                "payout_tx": "",
                "status": "",
                "before_usdc": before,
                "after_usdc": before,
                "stage": stage,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"error": str(e)[:300]}))
        sys.exit(1)
