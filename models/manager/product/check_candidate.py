"""Offline candidate veto for the existing mobile backend deployment path.

Does not select or deploy a model. Even a screen pass needs all release gates.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]/"files/eval/managerbench"))
from regression_guard import evaluate, candidate_preflight

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    args=parser.parse_args()
    status=candidate_preflight(evaluate(args.receipt),args.candidate,args.checkpoint_sha256)
    print(json.dumps({"status":status,"release_approved":False}))
    # Passing this diagnostic is not production approval.
    return 0 if status=="SCREEN_PASS_NOT_APPROVED" else 2

if __name__=="__main__":
    raise SystemExit(main())
