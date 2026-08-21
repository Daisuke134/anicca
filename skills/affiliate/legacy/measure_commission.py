"""measure_commission.py — MEASURE (account-level delta). Detects whether the affiliate
Amazon Associates account's monthly commission total has increased since the last check,
and records only the real, positive delta. Never attributes commission to a specific post
(Amazon's dashboard only exposes an account-wide monthly aggregate, verified live 2026-07-05:
amazon_report.py takes no arguments and has no per-post breakdown — per-post attribution is
not possible with this data source). Runs unconditionally every wake (see run.sh wiring),
independent of SET/HANDLE/EARN_MODE, and never blocks POST regardless of its own outcome.

Design history: docs/superpowers/specs/2026-07-05-affiliate-bounty-state-machine-design.md §2
(8 rounds of VCSDD adversary review, REV8 GATE 1 PASS).
"""
import json
import os
import subprocess
import sys
import time

AFFILIATE_SLIDESHOW_SCRIPTS = os.path.expanduser("~/.claude/skills/earn-affiliate-slideshow/scripts")


def _load(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f)


def measure_commission(watermark_path, ledger_record_fn, now, amazon_report_fn):
    """アカウント全体の当月コミッションの増分だけを検知。個別投稿とは紐付けない。
    呼び出し元(run.sh)が毎wake無条件に呼ぶ。POSTを一切ブロックしない(self_heal.py型)。"""
    report = amazon_report_fn()  # amazon_report.pyの実際の出力: {commission_jpy, asof, store_id, ...}
    if report.get("error"):
        return {"status": "error", "detail": report["error"]}  # ログイン切れ等、正直に報告して終了
    wm = _load(watermark_path) or {"month": None, "last_commission_jpy": 0, "last_checked_at": None}
    this_month = report["asof"][:7]  # "2026-07-05 ..." → "2026-07"
    if wm["month"] != this_month:
        # 月が変わった: Amazon側のカードも新しい月のカウントにリセットされている。
        # 新月の初回確認時点の値自体を「0からの増分」として記録してから、それをbaselineにする
        # (前月からの繰越ではなく、新月の実績として正しく計上 — 単に無記録でbaseline化すると
        # 月初の実コミッションを毎月確実に取りこぼすバグになる、VCSDD round 3で発見)。
        if report["commission_jpy"] > 0:
            export_id = f"live-scrape-{report['asof'].replace(' ', 'T').replace(':', '')}"
            ledger_record_fn({
                "source": "amazon_report", "amount_jpy": report["commission_jpy"],
                "report_date": report["asof"][:10], "report_export_id": export_id,
                "order_items": report.get("ordered_items"),
            })
        wm = {"month": this_month, "last_commission_jpy": report["commission_jpy"], "last_checked_at": now}
        _save(watermark_path, wm)
        return {"status": "new-month-baseline-recorded" if report["commission_jpy"] > 0 else "new-month-baseline",
                "commission_jpy": report["commission_jpy"]}
    delta = report["commission_jpy"] - wm["last_commission_jpy"]
    wm["last_checked_at"] = now
    if delta > 0:
        export_id = f"live-scrape-{report['asof'].replace(' ', 'T').replace(':', '')}"
        ledger_record_fn({
            "source": "amazon_report", "amount_jpy": delta,
            "report_date": report["asof"][:10], "report_export_id": export_id,
            "order_items": report.get("ordered_items"),
        })
        wm["last_commission_jpy"] = report["commission_jpy"]
        _save(watermark_path, wm)
        return {"status": "recorded", "delta_jpy": delta}
    _save(watermark_path, wm)
    return {"status": "no-change"}


def _amazon_report_fn():
    """amazon_report.pyをsubprocessで呼び、そのJSON標準出力をパースする。引数なし
    (スクリプト自体が引数を取らない)。CDP_PORTはenv経由でdaily-driver(9222)を使う
    既存のデフォルトのまま、明示的な上書きはしない。"""
    p = os.path.join(AFFILIATE_SLIDESHOW_SCRIPTS, "amazon_report.py")
    try:
        out = subprocess.run([sys.executable, p], capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return {"error": "amazon_report.py timed out after 30s"}
    try:
        return json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:
        return {"error": f"amazon_report.py did not return valid JSON: {out.stdout[:200]!r} {out.stderr[:200]!r}"}


def _ledger_record_fn(row):
    """record-affiliate-earn.mjsをsubprocessで呼ぶ。INV-1〜5はmjs側が検証する。
    例外はここでcatchし、呼び出し元がresult["ledger_errors"]として最終JSON出力に
    含める(run.shが標準エラーを捨てても標準出力のJSONにはエラーが残るように)。"""
    p = os.path.join(AFFILIATE_SLIDESHOW_SCRIPTS, "record-affiliate-earn.mjs")
    try:
        subprocess.run(["node", p, "--row", json.dumps(row)], check=True, timeout=15,
                        capture_output=True, text=True)
        return None  # 成功
    except subprocess.CalledProcessError as e:
        return f"record-affiliate-earn.mjs REJECTED: {e.stderr.strip()[:300]}"
    except Exception as e:
        return f"record-affiliate-earn.mjs invocation failed: {e}"


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--watermark", required=True)
    ap.add_argument("--wake", required=True)
    a = ap.parse_args()
    ledger_errors = []

    def _ledger_wrapper(row):
        err = _ledger_record_fn(row)
        if err:
            ledger_errors.append(err)

    result = measure_commission(a.watermark, _ledger_wrapper, time.time(), _amazon_report_fn)
    result["wake"] = a.wake
    if ledger_errors:
        result["ledger_errors"] = ledger_errors
    print(json.dumps(result, ensure_ascii=False))
