#!/usr/bin/env python3
"""床ガード — セッション起動時の固定コンテキスト（床）を実測し、予算超過を叫ぶ。

なぜ必要か: 床 = 毎 API 呼び出しで再読込される固定費。tool 1回 = API 1回 = 床を1回払う。
放置すると CLAUDE.md / memory / skill description / MCP が再び太り、同じ事故が起きる。
「気をつける」では止まらないので、機械が毎セッション測って叫ぶ。

使い方:
  python3 ~/.claude/scripts/floor-guard.py            # 直近セッションの床を実測して判定
  python3 ~/.claude/scripts/floor-guard.py --parts    # 床の内訳（何が太ったか）
"""
import glob
import json
import os
import re
import sys

BUDGET = 25_000        # 床の上限 tok。超えたら赤。
BUDGET_MD = 12_000     # 我々の markdown（CLAUDE.md 群 + MEMORY.md）の上限 tok

MD_FILES = [
    "~/.claude/CLAUDE.md",
    "~/.claude/projects/-Users-anicca-anicca-project/memory/MEMORY.md",
    "~/anicca-project/CLAUDE.md",
    "~/anicca-project/CLAUDE.local.md",
]
PROJECT_DIR = "~/.claude/projects/-Users-anicca-anicca-project"


def tok(nbytes: int) -> int:
    """日本語混在の概算: 2.2 bytes/token."""
    return int(nbytes / 2.2)


def measured_floor():
    """直近セッションの最初の API 呼び出しの input + cache_creation = 実測の床。"""
    files = sorted(
        glob.glob(os.path.expanduser(PROJECT_DIR + "/*.jsonl")),
        key=os.path.getmtime,
        reverse=True,
    )
    for f in files[:5]:
        for line in open(f):
            try:
                d = json.loads(line)
            except Exception:
                continue
            u = (d.get("message") or {}).get("usage")
            if not u:
                continue
            cc = u.get("cache_creation_input_tokens", 0)
            if cc:
                return u.get("input_tokens", 0) + cc, os.path.basename(f)[:8]
    return None, None


CACHE_READ_RED = 150_000   # 1呼び出しでこれ以上読み直していたら、会話が太りすぎ = 畳む


def conversation_watch():
    """直近セッションの「1呼び出しあたり cache_read」と使用モデル。

    床は起動時に決まるが、会話は使うほど太る。太った会話は全呼び出しに課金されるので、
    どこまで太ったかを毎回見えるようにする（今日 434k まで肥大して1セッション $77 になった）。
    """
    files = sorted(
        glob.glob(os.path.expanduser(PROJECT_DIR + "/*.jsonl")),
        key=os.path.getmtime,
        reverse=True,
    )
    if not files:
        return None
    last_read, calls, model = 0, 0, "?"
    for line in open(files[0]):
        try:
            d = json.loads(line)
        except Exception:
            continue
        m = d.get("message") or {}
        u = m.get("usage")
        if not u:
            continue
        calls += 1
        model = m.get("model", model)
        last_read = max(last_read, u.get("cache_read_input_tokens", 0))
    return {"last_read": last_read, "calls": calls, "model": model}


def markdown_floor():
    rows = []
    total = 0
    for p in MD_FILES:
        f = os.path.expanduser(p)
        if not os.path.exists(f):
            continue
        t = tok(os.path.getsize(f))
        total += t
        rows.append((t, p.split("/")[-1]))
    # paths: を持たない = 無条件ロードされる rules だけ数える
    for f in glob.glob(os.path.expanduser("~/anicca-project/.claude/rules/*.md")):
        head = open(f).read(120)
        if not (head.startswith("---") and "paths:" in head):
            t = tok(os.path.getsize(f))
            total += t
            rows.append((t, "rules/" + os.path.basename(f) + " ← paths: が無い"))
    return total, sorted(rows, reverse=True)


def skill_descriptions():
    """model 呼び出し可能な skill の name+description = 床に載る分。"""
    total, heavy, n = 0, [], 0
    seen = set()
    for root in ["~/.claude/skills", "~/anicca-project/.claude/skills"]:
        for f in glob.glob(os.path.expanduser(root) + "/**/SKILL.md", recursive=True):
            try:
                s = open(f).read(4000)
            except Exception:
                continue
            m = re.search(r"^---\s*(.*?)^---", s, re.S | re.M)
            if not m:
                continue
            fm = m.group(1)
            if "disable-model-invocation: true" in fm:
                continue  # リストから完全に消えている = 床に載らない
            nm = re.search(r"^name:\s*(.+)$", fm, re.M)
            if not nm or nm.group(1).strip() in seen:
                continue
            seen.add(nm.group(1).strip())
            desc = re.search(r"^description:\s*(.+?)(?=^\w+:|\Z)", fm, re.S | re.M)
            c = (len(nm.group(1)) + len(desc.group(1) if desc else "")) // 4
            total += c
            n += 1
            heavy.append((c, nm.group(1).strip()))
    return total, n, sorted(heavy, reverse=True)[:10]


def main():
    floor, sess = measured_floor()
    md, md_rows = markdown_floor()
    sk, n_sk, heavy = skill_descriptions()

    print("=" * 62)
    if floor:
        state = "OK " if floor <= BUDGET else "OVER BUDGET"
        print(f"実測の床: {floor:,} tok  (予算 {BUDGET:,})  [{state}]  session {sess}")
        print(f"  → tool 1回 = API 1回 = この床を毎回払う")
    else:
        print("実測の床: 取得できず（transcript なし）")
    print(f"我々の markdown: {md:,} tok  (予算 {BUDGET_MD:,})  "
          f"[{'OK' if md <= BUDGET_MD else 'OVER'}]")
    print(f"skill description: {sk:,} tok  ({n_sk} 個が model 呼び出し可能)")

    w = conversation_watch()
    if w:
        state = "OK" if w["last_read"] <= CACHE_READ_RED else "★赤信号: 会話が太りすぎ → 畳め★"
        print(f"直近セッション: {w['calls']} API呼び出し / 1呼び出しの cache_read 最大 "
              f"{w['last_read']:,} tok  [{state}]")
        if "[1m]" in w["model"] or "1m" in w["model"].lower().split("-")[-1:]:
            print("★1M 窓で走っている = auto-compact のブレーキが外れている。対話では使うな★")

    if "--parts" in sys.argv:
        print("\n-- markdown 内訳 --")
        for t, name in md_rows:
            print(f"  {t:>6} tok  {name}")
        print("\n-- 重い skill description TOP10（不要なら disable-model-invocation: true）--")
        for c, name in heavy:
            print(f"  {c:>6} tok  {name}")

    if (floor and floor > BUDGET) or md > BUDGET_MD:
        print("\n★ 床が予算を超えた。足す前に削れ。")
        print("  1. CLAUDE.md は 200行以下   2. rules に paths: を付ける")
        print("  3. skill 化（on-demand）    4. 使わない skill は disable-model-invocation: true")
        print("  5. 未使用 MCP は /mcp で切る  ★@import は床を減らさない（公式）★")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
