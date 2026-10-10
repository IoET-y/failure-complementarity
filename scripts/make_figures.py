#!/usr/bin/env python3
"""Draw the four figures of the write-up from ``results/data/headline_numbers.json`` (static SVG, light surface).

Palette: categorical slots 1-3 of the reference palette (validated with the dataviz validator: all checks pass; aqua is
< 3:1 on white, so every value is labelled directly and the article carries the data tables).

    python scripts/make_figures.py --out docs/blog/figures
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, GRID, SURFACE = "#111827", "#6b7280", "#e5e7eb", "#ffffff"
BLUE, ORANGE, AQUA, GRAY, LIGHT = "#2a78d6", "#eb6834", "#1baf7a", "#9ca3af", "#d1d5db"
NAMES = {"qwen36dense": "Qwen3.6-27B", "qwen36moe": "Qwen3.6-35B-A3B", "devstral": "Devstral Small 2 (24B)",
         "glm47flash": "GLM-4.7-Flash", "qwen": "Qwen3-Coder-30B-A3B", "nemotron3nano": "Nemotron-3-Nano-30B-A3B",
         "gptoss120b": "gpt-oss-120b"}

plt.rcParams.update({
    "svg.fonttype": "none", "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"], "font.size": 9,
    "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 1, "xtick.major.width": 1, "ytick.major.width": 1,
})


def clean(ax, grid="x"):
    ax.grid(axis=grid, color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)


def fig1(d, out):
    s = d["screening"]
    order = sorted(s, key=lambda m: s[m]["solved"])
    selected, excluded = {"devstral", "glm47flash"}, {"nemotron3nano", "gptoss120b"}
    fig, ax = plt.subplots(figsize=(7.2, 3.5))
    for i, m in enumerate(order):
        k, n = s[m]["solved"], s[m]["n"]
        lo, hi = s[m]["ci95"]
        color = BLUE if m in selected else (LIGHT if m in excluded else GRAY)
        ax.barh(i, k / n, height=0.55, color=color, hatch="////" if m in excluded else None,
                edgecolor="#9ca3af" if m in excluded else color, linewidth=0, zorder=3)
        ax.plot([lo, hi], [i, i], color=INK, linewidth=1, zorder=4, solid_capstyle="butt")
        ax.text(hi + 0.012, i, f"{100 * k / n:.0f}%  ({k}/{n})", va="center", ha="left", color=INK, fontsize=8.5)
    ax.set_yticks(range(len(order)), [NAMES[m] for m in order])
    ax.set_xlim(0, 1.08)
    ax.set_xticks([0, .2, .4, .6, .8, 1.0], ["0", "20%", "40%", "60%", "80%", "100%"])
    ax.set_xlabel("share of the 40 non-HARD screening tasks solved (line: 95% Wilson interval)")
    clean(ax)
    ax.legend(handles=[Patch(facecolor=BLUE, label="selected pair"), Patch(facecolor=GRAY, label="other candidates"),
                       Patch(facecolor=LIGHT, hatch="////", edgecolor="#9ca3af", label="excluded: harness incompatibility")],
              loc="lower right", frameon=False, fontsize=8.5, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(out / "fig1_screening.svg")
    plt.close(fig)


def fig2(d, out):
    P = d["pilot_v2_pooled"]["all"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6), sharey=True)
    labels = {"devstral": "Devstral", "glm47flash": "GLM-4.7-Flash"}
    for ax, a in zip(axes, ("devstral", "glm47flash")):
        o = "glm47flash" if a == "devstral" else "devstral"
        t = P[a]["table"]
        groups = [(f"same model\n({labels[a]})", f"V0 {a}->{a}", f"note {a}->{a}", f"Repo0 {a}"),
                  (f"other model\n({labels[o]})", f"V0 {a}->{o}", f"note {a}->{o}", f"Repo0 {o}")]
        for gi, (glabel, *keys) in enumerate(groups):
            for ci, (key, color) in enumerate(zip(keys, (BLUE, ORANGE, AQUA))):
                x = gi + (ci - 1) * 0.25
                c = t[key]
                ax.bar(x, c["rate"], width=0.17, color=color, zorder=3)
                reps = [k / n for k, n in c["per_replicate"]]
                ax.scatter([x] * len(reps), reps, s=14, color=SURFACE, edgecolor=INK, linewidth=1, zorder=5)
                ax.text(x, max(reps + [c["rate"]]) + 0.012, f"{100 * c['rate']:.0f}%", ha="center", va="bottom",
                        fontsize=8.5, color=INK)
        ax.set_xticks([0, 1], [g[0] for g in groups])
        ax.set_xlim(-0.55, 1.55)
        ax.set_ylim(0, 0.34)
        ax.set_yticks([0, .1, .2, .3], ["0", "10%", "20%", "30%"])
        ax.set_title(f"{labels[a]} failed  (N = {P[a]['n_failed_tasks']} tasks)", loc="left", fontsize=9.5, color=INK)
        ax.tick_params(axis="x", length=0)
        clean(ax, "y")
    axes[0].set_ylabel("success rate of the rescuing run")
    from matplotlib.lines import Line2D
    fig.legend(handles=[Patch(facecolor=BLUE, label="failed workspace"),
                        Patch(facecolor=ORANGE, label="failed workspace + note"),
                        Patch(facecolor=AQUA, label="pristine repo (control)"),
                        Line2D([], [], marker="o", linestyle="", markerfacecolor=SURFACE, markeredgecolor=INK, markersize=5,
                               label="one replicate")],
               loc="lower center", ncol=4, frameon=False, fontsize=8, labelcolor=MUTED, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(out / "fig2_recovery.svg")
    plt.close(fig)


def fig3(d, out):
    C = d["contrasts"]["all"]
    rows = [("HRG  (other model − same model, V0)", None),
            ("combined", "COMBINED HRG_V0"), ("Devstral failed", "HRG_V0 devstral->glm47flash"), ("GLM failed", "HRG_V0 glm47flash->devstral"),
            ("FTV  (failed workspace − pristine control)", None),
            ("combined", "COMBINED FTV"), ("Devstral → Devstral", "FTV devstral->devstral"), ("Devstral → GLM", "FTV devstral->glm47flash"),
            ("GLM → GLM", "FTV glm47flash->glm47flash"), ("GLM → Devstral", "FTV glm47flash->devstral"),
            ("CTV  (with handoff note − without)", None),
            ("combined", "COMBINED CTV"), ("Devstral → Devstral", "CTV devstral->devstral"), ("Devstral → GLM", "CTV devstral->glm47flash"),
            ("GLM → GLM", "CTV glm47flash->glm47flash"), ("GLM → Devstral", "CTV glm47flash->devstral")]
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    n = len(rows)
    for i, (label, key) in enumerate(rows):
        y = n - 1 - i
        if key is None:
            ax.text(-0.285, y, label, ha="left", va="center", fontsize=9, color=INK, fontweight="bold")
            continue
        c = C[key]
        comb = key.startswith("COMBINED")
        lo, hi = c["ci95"]
        ax.plot([lo, hi], [y, y], color=BLUE if comb else GRAY, linewidth=2 if comb else 1.4, zorder=3, solid_capstyle="round")
        ax.scatter([c["mean"]], [y], s=46 if comb else 26, color=BLUE if comb else GRAY, edgecolor=SURFACE, linewidth=2, zorder=4)
        ax.text(-0.27, y, label, ha="left", va="center", fontsize=8.5, color=INK if comb else MUTED)
        ax.text(0.205, y, f"{c['mean']:+.3f}  [{lo:+.3f}, {hi:+.3f}]", ha="left", va="center", fontsize=8, color=INK if comb else MUTED)
    ax.axvline(0, color=MUTED, linewidth=1, zorder=2)
    ax.set_xlim(-0.285, 0.38)
    ax.set_ylim(-0.7, n - 0.3)
    ax.set_yticks([])
    ax.set_xticks([-0.2, -0.1, 0, 0.1], ["−0.2", "−0.1", "0", "+0.1"])
    ax.set_xlabel("change in success probability (per-task mean over 3 replicates; 95% interval by bootstrap over tasks)", fontsize=8)
    ax.grid(axis="x", color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "fig3_contrasts.svg")
    plt.close(fig)


def fig4(d, out):
    t = d["pilot_v2_pooled"]["all"]["glm47flash"]["table"]
    series = [("start from failed workspace", "V0 glm47flash->glm47flash", BLUE),
              ("failed workspace + handoff note", "note glm47flash->glm47flash", ORANGE),
              ("pristine repo (control)", "Repo0 glm47flash", AQUA)]
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    for si, (label, key, color) in enumerate(series):
        for r, (k, n) in enumerate(t[key]["per_replicate"]):
            x = r + (si - 1) * 0.22
            ax.scatter([x], [k], s=70, color=color, edgecolor=SURFACE, linewidth=2, zorder=4)
            ax.text(x, k + 0.7, f"{k}", fontsize=8.5, color=INK, ha="center")
    ax.set_xticks([0, 1, 2], ["replicate 1 (the original run)", "replicate 2", "replicate 3"])
    ax.set_xlim(-0.5, 2.5)
    ax.set_ylim(0, 13.5)
    ax.set_ylabel("tasks rescued (of 44)")
    clean(ax, "y")
    ax.tick_params(axis="x", length=0)
    ax.legend(handles=[Patch(facecolor=c, label=l) for l, _, c in series], loc="upper left", ncol=3, frameon=False,
              fontsize=8, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(out / "fig4_replicates.svg")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs/blog/figures"))
    ap.add_argument("--json", default=str(ROOT / "results/data/headline_numbers.json"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    d = json.loads(Path(a.json).read_text())
    for f in (fig1, fig2, fig3, fig4):
        f(d, out)
    print("wrote", sorted(p.name for p in out.glob("*.svg")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
