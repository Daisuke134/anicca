#!/usr/bin/env python3
"""
update-experiments-json.py
experiments.json を安全に更新するスクリプト。

Subcommands:
  archive       — current 実験を history に移動
  add-pattern   — winning/losing パターンを追加
  set-current   — 新しい実験を current にセット
  show          — 現在の状態を表示
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path.home() / ".openclaw/skills/screenshot-ab/workspace"
JSON_PATH = WORKSPACE / "experiments.json"


def load():
    if not JSON_PATH.exists():
        print(f"❌ {JSON_PATH} が見つかりません。setup-workspace.sh を実行してください。", file=sys.stderr)
        sys.exit(1)
    return json.loads(JSON_PATH.read_text())


def save(data):
    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"✅ {JSON_PATH} 更新完了")


def cmd_archive(args):
    data = load()
    current = data.get("current")
    if not current or not current.get("experiment_id"):
        print("⚠️  current に実験がありません。アーカイブ不要。")
        return

    current["result"] = args.result
    current["control_cvr"] = args.control_cvr
    current["treatment_cvr"] = args.treatment_cvr
    current["days_run"] = args.days
    current["archived_at"] = datetime.now().isoformat()

    data.setdefault("history", []).append(current)
    data["current"] = {
        "experiment_id": None,
        "name": None,
        "treatment_id": None,
        "en_loc": None,
        "ja_loc": None,
        "headlines_en": [],
        "headlines_ja": [],
        "started_at": None
    }
    save(data)
    print(f"📦 実験 {current['experiment_id']} を history にアーカイブ（結果: {args.result}）")


def cmd_add_pattern(args):
    data = load()
    key = f"{args.type}_patterns"
    data.setdefault(key, [])
    if args.pattern not in data[key]:
        data[key].append(args.pattern)
        save(data)
        print(f"➕ {args.type} パターン追加: {args.pattern}")
    else:
        print(f"⏭️  パターンは既に存在: {args.pattern}")


def cmd_set_current(args):
    data = load()
    data["current"] = {
        "experiment_id": args.experiment_id,
        "name": args.name,
        "treatment_id": args.treatment_id,
        "en_loc": args.en_loc,
        "ja_loc": args.ja_loc,
        "headlines_en": args.headlines_en.split("|") if args.headlines_en else [],
        "headlines_ja": args.headlines_ja.split("|") if args.headlines_ja else [],
        "started_at": datetime.now().isoformat()
    }
    save(data)
    print(f"🚀 current 実験セット: {args.experiment_id}")


def cmd_show(_args):
    data = load()
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="experiments.json 管理")
    sub = parser.add_subparsers(dest="command")

    # archive
    p_archive = sub.add_parser("archive", help="current を history にアーカイブ")
    p_archive.add_argument("--result", required=True, choices=["WINNER", "NULL", "TIMEOUT"])
    p_archive.add_argument("--control-cvr", type=float, required=True)
    p_archive.add_argument("--treatment-cvr", type=float, required=True)
    p_archive.add_argument("--days", type=int, required=True)

    # add-pattern
    p_pattern = sub.add_parser("add-pattern", help="winning/losing パターン追加")
    p_pattern.add_argument("--type", required=True, choices=["winning", "losing"])
    p_pattern.add_argument("--pattern", required=True)

    # set-current
    p_current = sub.add_parser("set-current", help="新実験を current にセット")
    p_current.add_argument("--experiment-id", required=True)
    p_current.add_argument("--name", required=True)
    p_current.add_argument("--treatment-id", required=True)
    p_current.add_argument("--en-loc", required=True)
    p_current.add_argument("--ja-loc", required=True)
    p_current.add_argument("--headlines-en", default="")
    p_current.add_argument("--headlines-ja", default="")

    # show
    sub.add_parser("show", help="現在の状態表示")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    {"archive": cmd_archive, "add-pattern": cmd_add_pattern, "set-current": cmd_set_current, "show": cmd_show}[args.command](args)


if __name__ == "__main__":
    main()
