"""Simple matplotlib figures for the README. One question per chart."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from model import NAMES, PCS

FIG_DIR = Path(__file__).resolve().parents[1] / "figures"
TEAM_COLORS = {"Argentina": "#2a78d6", "France": "#eb6834"}
CREDIT = "Data: StatsBomb open data, FIFA World Cup 2022"

plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 10})


def _save(fig, name):
    fig.text(0.99, -0.04, CREDIT, ha="right", va="top", fontsize=7, color="grey")
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png", dpi=150, bbox_inches="tight")
    return fig


def drivers(baseline):
    """Stage 1: how much each style component moved non-penalty xG."""
    e = baseline.effects.sort_values("effect")
    fig, ax = plt.subplots(figsize=(7, 3.6))
    y = np.arange(len(e))
    colors = ["#2a78d6" if p < 0.05 else "lightgrey" for p in e["p"]]
    ax.barh(y, e["effect"], color=colors,
            xerr=[e["effect"] - e["lo"], e["hi"] - e["effect"]], error_kw={"ecolor": "grey", "lw": 1})
    ax.set_yticks(y, [NAMES[pc] for pc in e.index])
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Change in non-penalty xG per 90 for +1 SD of the component")
    ax.set_title("Stage 1: what went with more chances (grey = no clear effect)", loc="left")
    return _save(fig, "fig1_drivers")


def predicted_vs_actual(before, final):
    """Stages 2 and 3: chances predicted from style vs actual, with penalties shown on top."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    panels = [(axes[0], before, "Before the final (average per 90 min)"),
              (axes[1], final, "In the final (whole 120 min)")]
    for ax, d, title in panels:
        for i, team in enumerate(TEAM_COLORS):
            c, r = TEAM_COLORS[team], d.loc[team]
            ax.bar(i - 0.2, r["predicted"], width=0.38, color="white", edgecolor=c, hatch="//",
                   label="Predicted from style" if i == 0 else None)
            ax.bar(i + 0.2, r["non_penalty"], width=0.38, color=c,
                   label="Actual, without penalties" if i == 0 else None)
            ax.bar(i + 0.2, r["penalties"], bottom=r["non_penalty"], width=0.38, color=c, alpha=0.4,
                   label="Penalties" if i == 0 else None)
            ax.text(i - 0.2, r["predicted"] + 0.03, f"{r['predicted']:.2f}", ha="center", fontsize=9)
            ax.text(i + 0.2, r["non_penalty"] + r["penalties"] + 0.03,
                    f"{r['non_penalty']:.2f}\n+ {r['penalties']:.2f} pens", ha="center", fontsize=9)
        ax.set_xticks([0, 1], list(TEAM_COLORS))
        ax.set_ylabel("xG")
        ax.set_ylim(0, max(3.0, ax.get_ylim()[1] * 1.15))
        ax.set_title(title, loc="left")
    axes[0].legend(frameon=False, fontsize=8.5, loc="upper right")
    fig.suptitle("Stages 2 and 3: non-penalty chances predicted from style vs actual, with penalties on top",
                 x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    return _save(fig, "fig2_predicted_vs_actual")


def style_shift(usual, final):
    """Stage 3: each finalist's style in the final vs its usual style."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    y = np.arange(len(PCS))[::-1]
    for ax, (team, c) in zip(axes, TEAM_COLORS.items()):
        ax.barh(y + 0.2, usual.loc[team, PCS], height=0.38, color="lightgrey", label="Usual (6 matches)")
        ax.barh(y - 0.2, final.loc[team, PCS], height=0.38, color=c, label="Final")
        ax.axvline(0, color="black", lw=0.8)
        ax.set_yticks(y, [NAMES[p] for p in PCS])
        ax.set_xlim(-2, 2)
        ax.set_xlabel("Component score (0 = average team)")
        ax.set_title(team, loc="left")
    axes[0].legend(frameon=False, fontsize=8.5, ncol=2, loc="upper left", bbox_to_anchor=(0, -0.18))
    fig.suptitle("Stage 3: each team's style in the final vs its usual style", x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    return _save(fig, "fig3_style_shift")


def xg_timeline(shots, subs, period_starts):
    """Stage 3: cumulative xG over the 120 minutes of the final."""
    end = shots.attrs["end"]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axvspan(period_starts[2], end, color="whitesmoke")
    ax.text((period_starts[2] + end) / 2, 0.1, "extra time", ha="center", color="grey")
    for team, c in TEAM_COLORS.items():
        s = shots[shots.team == team]
        ax.step(np.r_[0, s.elapsed, end], np.r_[0, s.xg.cumsum(), s.xg.sum()], where="post", color=c, label=team)
        cum = s.xg.cumsum()
        for idx, g in s[s.goal].iterrows():
            ax.plot(g.elapsed, cum[idx], "s" if g.penalty else "o", color=c, mec="black")
            ax.annotate(g.label, (g.elapsed, cum[idx]), xytext=(-4, 6), textcoords="offset points",
                        ha="right", fontsize=8)
    ax.set_xticks(period_starts + [end], ["0'", "45'", "90'", "105'", "120'"])
    ax.set_xlim(0, end)
    ax.set_ylim(0, None)
    ax.set_ylabel("Cumulative xG")
    ax.legend(frameon=False, loc="upper left", title="square = penalty", title_fontsize=8)
    ax.set_title("Stage 3: chances through the final", loc="left")
    return _save(fig, "fig4_xg_timeline")
