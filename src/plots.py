"""Figures. One question per chart; the title is the takeaway."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

from model import NAMES, PCS, SUMMARIES

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"
LOGO = plt.imread(ROOT / "assets" / "statsbomb_logo.png")

INK, INK_2, MUTED, GRID, SURFACE, PANEL = "#0b0b0b", "#52514e", "#a3a29c", "#e4e3df", "#fcfcfb", "#f0efec"
TEAM_COLORS = {"Argentina": "#2a78d6", "France": "#eb6834"}
UP, DOWN, TOTAL = "#2a78d6", "#e34948", "#52514e"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlelocation": "left", "axes.titlesize": 11, "axes.titlecolor": INK,
})


def _finish(fig, title, subtitle, name, credit=True):
    fig.suptitle(title, x=0.02, ha="left", fontsize=14, fontweight="bold", color=INK)
    fig.text(0.02, 0.925, subtitle, ha="left", va="top", fontsize=10, color=INK_2)
    if credit:
        fig.text(0.98, 0.015, "Data: StatsBomb open data, FIFA World Cup 2022", ha="right", va="bottom",
                 fontsize=8, color=INK_2)
        logo_ax = fig.add_axes([0.02, 0.01, 0.10, 0.035])
        logo_ax.imshow(LOGO)
        logo_ax.axis("off")
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png", dpi=160)
    return fig


def pipeline():
    """Fig 0: how the analysis works, in three stages."""
    stages = [
        ("Stage 1", "What drives chances?",
         "All 64 matches (final held out).\n12 style metrics per team per match\n→ grouped into 5 style components\n→ which components go with more xG?"),
        ("Stage 2", "Argentina and France\nvs everyone",
         "Score each team on the same components.\nSplit its xG into: average team\n+ each style component + penalties\n+ what style does not explain."),
        ("Stage 3", "The final",
         "Same scoring for the final (120 min).\nHow far did each team move from\nits usual style, and how did the\nchances flow by score state?"),
    ]
    fig, ax = plt.subplots(figsize=(13, 3.6))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.78, bottom=0.04)
    ax.set_xlim(0, 3)
    ax.set_ylim(0.18, 1)
    ax.axis("off")
    for i, (tag, head, body) in enumerate(stages):
        x0 = i + 0.04
        ax.add_patch(FancyBboxPatch((x0, 0.2), 0.84, 0.74, boxstyle="round,pad=0,rounding_size=0.04",
                                    facecolor=PANEL, edgecolor="none"))
        ax.text(x0 + 0.05, 0.86, tag.upper(), fontsize=9, fontweight="bold", color=UP, va="top")
        ax.text(x0 + 0.05, 0.76, head, fontsize=12.5, fontweight="bold", color=INK, va="top")
        ax.text(x0 + 0.05, 0.56, body, fontsize=9.5, color=INK_2, va="top", linespacing=1.5)
        if i < 2:
            ax.annotate("", xy=(i + 1.03, 0.57), xytext=(i + 0.9, 0.57),
                        arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=2))
    return _finish(fig, "How the analysis works",
                   "One model, fitted once on the whole tournament, then used to read the two finalists and the "
                   "final.", "fig0_pipeline", credit=False)


def stage1_drivers(baseline):
    """Fig 1: how much each style component moves non-penalty xG."""
    e = baseline.effects.sort_values("effect")
    fig, ax = plt.subplots(figsize=(11, 5.6))
    fig.subplots_adjust(left=0.37, right=0.95, top=0.80, bottom=0.17)
    y = np.arange(len(e))
    sig = (e["p"] < 0.05).values
    ax.axvline(0, color=MUTED, lw=1)
    ax.barh(y, e["effect"], height=0.55, color=np.where(sig, UP, GRID), edgecolor=SURFACE, linewidth=2)
    ax.hlines(y, e["lo"], e["hi"], color=INK_2, lw=1.5)
    for yi, (pc, r) in zip(y, e.iterrows()):
        ax.text(max(r["hi"], 0) + 0.012, yi, f"{r['effect']:+.2f}", va="center", fontsize=10, color=INK)
    ax.set_yticks(y, [f"{NAMES[pc]}\n{SUMMARIES[pc]}" for pc in e.index], fontsize=9.5)
    for lbl in ax.get_yticklabels():
        lbl.set_color(INK)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlim(-0.15, 0.45)
    ax.set_xlabel("Extra non-penalty xG per 90 when a team is 1 SD higher on the component (line = 95% CI)")
    r2 = baseline.ols.rsquared
    return _finish(fig, "Stage 1 · Control, direct-and-wide play and ball-carrying go with chances",
                   f"126 team-matches before the final, extra time included. Grey = not clearly different from zero. "
                   f"Style explains {r2:.0%} of the variation in xG.", "fig1_stage1_drivers")


def _waterfall(ax, row, title):
    steps = [("Average team", row["average_team"], "total")]
    steps += [(NAMES[pc], row[NAMES[pc]], "step") for pc in PCS]
    steps += [("Not\nexplained", row["other"], "step"), ("Penalties", row["penalties"], "step"),
              ("Actual xG", row["actual_xg"], "total")]
    level = 0.0
    for i, (label, v, kind) in enumerate(steps):
        if kind == "total":
            ax.bar(i, v, width=0.62, color=TOTAL, edgecolor=SURFACE, linewidth=2)
            ax.text(i, v + 0.03, f"{v:.2f}", ha="center", fontsize=9.5, fontweight="bold", color=INK)
            level = v
        else:
            ax.bar(i, v, bottom=level, width=0.62, color=UP if v >= 0 else DOWN, edgecolor=SURFACE, linewidth=2)
            ax.text(i, max(level, level + v) + 0.03, f"{v:+.2f}", ha="center", fontsize=9, color=INK_2)
            if i < len(steps) - 1:
                ax.plot([i + 0.31, i + 0.69], [level + v] * 2, color=MUTED, lw=1)
            level += v
    wrap = {"Direct & wide": "Direct &\nwide", "Pressing volume": "Pressing\nvolume",
            "Pressing height": "Pressing\nheight", "Ball-carrying": "Ball-\ncarrying", "Average team": "Average\nteam",
            "Actual xG": "Actual\nxG"}
    ax.set_xticks(range(len(steps)), [wrap.get(s[0], s[0]) for s in steps], fontsize=8.5)
    ax.set_ylim(0, 2.15)
    ax.yaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, fontsize=11)


def stage2_breakdown(team_avgs):
    """Fig 2: where each finalist's xG came from, before the final."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), sharey=True)
    fig.subplots_adjust(left=0.05, right=0.99, top=0.78, bottom=0.17, wspace=0.06)
    for ax, team in zip(axes, TEAM_COLORS):
        _waterfall(ax, team_avgs.loc[team], f"{team}: 6 matches before the final")
    axes[0].set_ylabel("xG per 90")
    return _finish(fig, "Stage 2 · Argentina's edge was control plus penalties; France's was ball-carrying",
                   "Each team's average xG per 90 split into parts. Blue lifts xG above an average team, red lowers it.\n"
                   "Penalties are measured against the average team (0.11 xG/90): Argentina won 4 in 6 games, France none.",
                   "fig2_stage2_breakdown")


def stage3_style_shift(usual, final):
    """Fig 3: each finalist's style in the final vs its usual style."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
    fig.subplots_adjust(left=0.12, right=0.98, top=0.78, bottom=0.14, wspace=0.08)
    y = np.arange(len(PCS))[::-1]
    for ax, (team, c) in zip(axes, TEAM_COLORS.items()):
        u, f = usual.loc[team, PCS].values, final.loc[team, PCS].values
        ax.axvline(0, color=MUTED, lw=1)
        for yi, a, b in zip(y, u, f):
            ax.annotate("", xy=(b, yi), xytext=(a, yi), arrowprops=dict(arrowstyle="-|>", color=c, lw=1.8,
                                                                        shrinkA=6, shrinkB=5))
        ax.scatter(u, y, s=70, facecolor=SURFACE, edgecolor=c, linewidth=2, zorder=3, label="Usual (6 matches)")
        ax.scatter(f, y, s=70, color=c, edgecolor=SURFACE, linewidth=1.5, zorder=3, label="Final (120 min)")
        ax.set_yticks(y, [NAMES[p] for p in PCS])
        ax.tick_params(axis="y", length=0)
        ax.set_xlim(-2.3, 2.3)
        ax.set_xlabel("Component score (0 = average team; ±1 ≈ a typical spread)")
        ax.xaxis.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        ax.set_title(team, fontsize=11)
        ax.legend(loc="lower left", frameon=False, fontsize=8.5)
    return _finish(fig, "Stage 3a · In the final Argentina went direct and wide; France lost control",
                   "Hollow = the team's usual style, filled = the final. Arrows show the move.",
                   "fig3_stage3_style_shift")


def stage3_xg_race(shots, events_marks, period_starts):
    """Fig 4: cumulative xG over the 120 minutes, with goals, substitutions and score-state windows."""
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.subplots_adjust(left=0.06, right=0.97, top=0.80, bottom=0.17)
    end = shots.attrs["end"]
    ax.axvspan(period_starts[2], end, color=PANEL, zorder=0)
    ax.text((period_starts[2] + end) / 2, 0.08, "EXTRA TIME", ha="center", va="bottom", fontsize=9, fontweight="bold",
            color=INK_2, transform=ax.get_xaxis_transform())
    for team, c in TEAM_COLORS.items():
        s = shots[shots.team == team]
        x = np.r_[0, s.elapsed.values, end]
        yv = np.r_[0, s.xg.cumsum().values, s.xg.sum()]
        ax.step(x, yv, where="post", color=c, lw=2.2, label=f"{team}  ({s.xg.sum():.2f} xG, "
                                                              f"{s.loc[~s.penalty, 'xg'].sum():.2f} without pens)")
        for _, g in s[s.goal].iterrows():
            yg = s.loc[: g.name, "xg"].sum()
            ax.scatter(g.elapsed, yg, s=90, color=c, edgecolor=INK, linewidth=1.2, zorder=4,
                       marker="s" if g.penalty else "o")
            ax.annotate(g.label, (g.elapsed, yg), xytext=(-9, -14) if g.penalty else (-6, 9),
                        textcoords="offset points", fontsize=8.5, ha="right", color=INK)
    for _, m in events_marks.iterrows():
        ax.axvline(m.elapsed, ymin=0, ymax=0.04, color=TEAM_COLORS[m.team], lw=2)
    ax.set_xticks(period_starts + [end], ["Kick-off", "2nd half", "Extra time", "ET 2nd half", "120'"])
    ax.set_xlim(0, end)
    ax.set_ylim(0, None)
    ax.set_ylabel("Cumulative xG")
    ax.yaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, fontsize=9.5)
    ax.text(0.012, 0.80, "■ penalty goal   ● open-play goal   short ticks on the x-axis = substitutions",
            transform=ax.transAxes, ha="left", fontsize=8.5, color=INK_2)
    return _finish(fig, "Stage 3b · Argentina created the open-play chances; France's three goals included two "
                        "penalties",
                   "Cumulative xG over all 120 minutes of the final (shootout excluded). x-axis = minutes of play, "
                   "stoppage time included.", "fig4_stage3_xg_race")
