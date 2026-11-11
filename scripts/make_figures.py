#!/usr/bin/env python3
"""Plot only measured episode logs and verified campaign summaries."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("campaign", type=Path)
    args = p.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    groups = json.loads((args.campaign / "grouped_results.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5), constrained_layout=True)
    for ax, metric, title in zip(axes, ("success_count", "pedestrian_collision_count"), ("Goal success", "Episodes with pedestrian collision")):
        names = [r["density"] + "\n" + r["method"] for r in groups]
        ax.bar(range(len(groups)), [r[metric] / r["n"] for r in groups])
        ax.set_xticks(range(len(groups)), names, rotation=30, ha="right", fontsize=8)
        ax.set_ylim(0, 1)
        ax.set_title(title)
        ax.set_ylabel("Fraction of episodes")
    fig.savefig(args.campaign / "outcomes.png", dpi=200)
    fig.savefig(args.campaign / "outcomes.pdf")
    plt.close(fig)
    conditions = json.loads((args.campaign / "conditions.json").read_text())
    density, seed = conditions[0]["density"], min(r["seed"] for r in conditions)
    fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
    for method in ("baseline", "distance", "predictive"):
        path = args.campaign / f"{density}_seed{seed}_{method}" / "steps.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        points = [r["ego"]["position"] for r in rows if r["phase"] == "navigation"]
        if points:
            ax.plot([q[0] for q in points], [q[1] for q in points], label=method)
    ax.set(xlabel="Simulator x (m)", ylabel="Simulator y (m)", title=f"Prespecified example: {density}, seed {seed}")
    ax.axis("equal")
    ax.legend()
    fig.savefig(args.campaign / "paired_trajectory.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
