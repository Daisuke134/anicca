#!/usr/bin/env python3
"""Original figure for the 2026-11-11 BehaviorBench first-run article pair.

Two panels, both from the run recorded in
goals/manager-bfm-benchmarks behaviorbench-run-2026-11-11.md (section 5):
  A) game_behavior_dictator (50 samples, temperature 1.0, human reference
     n=200): Wasserstein distance to the human distribution; lower is closer.
  B) pers_score_pred (n=20, 5 Big Five dimensions averaged): MAE of the
     predicted trait scores (range 10-50); lower is better.
Output PNG path is printed; the publisher copies it to
publication/2026-10-19/media/<sha256>.png.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))

# Panel A: dictator game, distribution level
ax = axes[0]
models_a = ["Be.FM\n1.5-4B", "Qwen3-4B\nInstruct-2507"]
vals_a = [2.105, 20.275]
bars = ax.bar(models_a, vals_a, color=["#2e7d5b", "#b0b0b0"], width=0.55)
ax.set_ylabel("Wasserstein distance to human distribution")
ax.set_title("A. Dictator game: distribution match\n(50 samples, temp 1.0; human n=200; lower = closer)", fontsize=10)
for b, v in zip(bars, vals_a):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.3f}", ha="center", fontsize=10)
ax.set_ylim(0, 23)
ax.spines[["top", "right"]].set_visible(False)

# Panel B: Big Five score prediction, individual level
ax = axes[1]
labels_b = ["prior_marginal\n(per-dimension mean)", "Be.FM\n1.5-4B", "Qwen3-4B\nInstruct-2507", "prior_constant\n(midpoint 30)"]
vals_b = [4.73, 5.68, 6.59, 7.29]
colors_b = ["#c98a2d", "#2e7d5b", "#b0b0b0", "#d6d6d6"]
bars = ax.bar(labels_b, vals_b, color=colors_b, width=0.6)
ax.set_ylabel("MAE (score range 10-50)")
ax.set_title("B. Big Five score prediction: individual level\n(n=20, 5 dimensions averaged; lower = better)", fontsize=10)
for b, v in zip(bars, vals_b):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.15, f"{v:.2f}", ha="center", fontsize=10)
ax.set_ylim(0, 8.2)
ax.tick_params(axis="x", labelsize=8.5)
ax.spines[["top", "right"]].set_visible(False)

fig.tight_layout()
out = "/tmp/behaviorbench-2026-11-11-figure.png"
fig.savefig(out, dpi=200)
print(out)
