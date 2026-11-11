#!/usr/bin/env python3
"""Complete figure for the 2026-11-11 BehaviorBench first-run article pair.

Three panels covering every task that was run, all numbers from the run
recorded in goals/manager-bfm-benchmarks behaviorbench-run-2026-11-11.md
(section 5), plus the human split-half baseline in bb-work/
human_baseline_games.json:
  A) surv_resp_pred (n=20, 16 target-item groups averaged): Accuracy of
     survey-response prediction on a 1-5 scale; higher is better.
  B) pers_score_pred (n=20, 5 Big Five dimensions averaged): MAE of the
     predicted trait scores (range 10-50); lower is better.
  C) game_behavior_dictator (50 samples, temperature 1.0, human reference
     n=200): Wasserstein distance to the human distribution; lower is
     closer. The shaded band is the human-vs-human split-half distance
     (50 vs 150 humans, R=200): mean 3.433, SD 1.585.
Output PNG path is printed; the publisher copies it to
articles/visuals/ and publication/2026-10-19/media/<sha256>.png.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.6))

# Panel A: survey response prediction, individual level
ax = axes[0]
labels_a = ["Qwen3-4B\nInstruct-2507", "prior_marginal\n(most frequent answer)", "Be.FM\n1.5-4B", "prior_constant\n(midpoint 3)"]
vals_a = [0.4375, 0.4167, 0.3542, 0.2708]
colors_a = ["#b0b0b0", "#c98a2d", "#2e7d5b", "#d6d6d6"]
bars = ax.bar(labels_a, vals_a, color=colors_a, width=0.6)
ax.set_ylabel("Accuracy (answers on a 1-5 scale)")
ax.set_title("A. Survey response prediction: individual level\n(n=20, 16 item groups averaged; higher = better)", fontsize=10)
for b, v in zip(bars, vals_a):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.012, f"{v:.4f}", ha="center", fontsize=10)
ax.set_ylim(0, 0.5)
ax.tick_params(axis="x", labelsize=8.5)
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

# Panel C: dictator game, distribution level, with human split-half band
ax = axes[2]
models_c = ["Be.FM\n1.5-4B", "Qwen3-4B\nInstruct-2507"]
vals_c = [2.105, 20.275]
ax.axhspan(3.433 - 1.585, 3.433 + 1.585, color="#7a9e7e", alpha=0.25)
ax.axhline(3.433, color="#4a7a4f", linestyle="--", linewidth=1.2)
ax.text(1.42, 3.433 + 1.585 + 0.7, "humans vs humans\n(split-half): 3.43 ± 1.59", fontsize=9, color="#33502f", ha="right")
bars = ax.bar(models_c, vals_c, color=["#2e7d5b", "#b0b0b0"], width=0.5)
ax.set_ylabel("Wasserstein distance to human distribution")
ax.set_title("C. Dictator game: distribution match\n(50 samples, temp 1.0; human n=200; lower = closer)", fontsize=10)
for b, v in zip(bars, vals_c):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.3f}", ha="center", fontsize=10)
ax.set_ylim(0, 23)
ax.set_xlim(-0.55, 1.55)
ax.spines[["top", "right"]].set_visible(False)

fig.tight_layout()
out = "/tmp/behaviorbench-2026-11-11-figure-full.png"
fig.savefig(out, dpi=200)
print(out)
