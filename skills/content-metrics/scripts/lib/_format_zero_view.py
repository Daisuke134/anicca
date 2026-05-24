import sys, json
rows = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        rows.append(json.loads(line))
    except Exception:
        pass
flagged = [r for r in rows if r.get('streak', 0) >= 3]
if not flagged:
    print("🟢 *content-zero-view-watcher* — no accounts at 3+ day streak below 100 views.")
    sys.exit(0)
print(f"🚨 *content-zero-view-watcher* — {len(flagged)} account(s) flagged DYING:")
for r in flagged:
    print(f"• `{r['handle']}` ({r['platform']}) — {r['streak']} consecutive days <100 views")
print("\nActions:")
print("• 🔥 launch warmup new account")
print("• 🩹 try last-resort hook reset")
print("• 💀 sentence to death (append to ~/anicca-monk-factory/accounts/burn/burned.jsonl)")
