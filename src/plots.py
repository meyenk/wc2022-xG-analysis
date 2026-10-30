"""Figures. Each one answers one question; the title is the takeaway."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

from metrics import METRICS
from model import NAMES, PCS

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "figures"
LOGO = plt.imread(ROOT / "assets" / "statsbomb_logo.png")

INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#a3a29c", "#e4e3df", "#fcfcfb"
TEAM_COLORS = {"Argentina": "#2a78d6", "France": "#eb6834"}
OTHER = "#b9b8b2"
DIVERGING = LinearSegmentedColormap.from_list("div", ["#e34948", "#f0efec", "#2a78d6"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
    "axes.titlelocation": "left", "axes.titlesize": 11, "axes.titlecolor": INK,
})

METRIC_LABELS = {
    "possession_share": "Possession share",
    "passes_per_possession": "Passes per possession",
    "pass_completion_under_pressure": "Pass completion under pressure",
    "progressive_passes_p90": "Progressive passes /90",
    "progressive_carries_p90": "Progressive carries /90",
    "directness": "Directness (forward gain per pass)",
    "long_ball_share": "Long-ball share",
    "field_tilt": "Field tilt",
    "crosses_per_entry": "Crosses per final-third entry",
    "pressures_per_opp_possession": "Pressures per opp. possession",
    "pressure_height": "Pressure height",
    "high_regains_p90": "Regains in opp. half /90",
}


def _finish(fig, title, subtitle, name):
    fig.suptitle(title, x=0.01, ha="left", fontsize=14, fontweight="bold", color=INK)
    fig.text(0.01, 0.935, subtitle, ha="left", va="top", fontsize=10, color=INK_2)
    fig.text(0.99, 0.01, "Data: StatsBomb open data, FIFA World Cup 2022", ha="right", va="bottom",
             fontsize=8, color=INK_2)
    logo_ax = fig.add_axes([0.01, 0.005, 0.11, 0.035])
    logo_ax.imshow(LOGO)
    logo_ax.axis("off")
    FIG_DIR.mkdir(exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png", dpi=160)
    return fig


def what_drives_xg(baseline, score_sd):
    """Fig 1: loadings (what each component means) + effect of 1 SD of each component on xG/90."""
    L = baseline.loadings.rename(index=METRIC_LABELS)
    effect = baseline.coefs.loc[PCS].mul(score_sd[PCS], axis=0)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 6.8), gridspec_kw={"width_ratios": [1.5, 1]})
    fig.subplots_adjust(left=0.22, right=0.97, top=0.72, bottom=0.10, wspace=0.55)

    a1.imshow(L.values, cmap=DIVERGING, vmin=-0.75, vmax=0.75, aspect="auto")
    a1.set_yticks(range(len(L)), L.index)
    heads = [f"{NAMES[p].replace(' ', chr(10), 1)}\n{baseline.explained[p]:.0%} var." for p in PCS]
    a1.set_xticks(range(len(PCS)), heads, fontsize=8.5)
    a1.xaxis.tick_top()
    a1.tick_params(length=0)
    for s in a1.spines.values():
        s.set_visible(False)
    for i in range(L.shape[0]):
        for j in range(L.shape[1]):
            v = L.values[i, j]
            if abs(v) >= 0.25:
                a1.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=8,
                        color="white" if abs(v) > 0.55 else INK)
    a1.set_title("What each style component is made of (PCA loadings)", pad=52, fontsize=10, color=INK_2)

    y = np.arange(len(PCS))[::-1]
    sig = effect["p"] < 0.05
    a2.axvline(0, color=MUTED, lw=1)
    a2.hlines(y, effect["lo"], effect["hi"], color=INK_2, lw=2)
    a2.scatter(effect["coef"], y, s=70, color=np.where(sig, "#2a78d6", SURFACE),
               edgecolor="#2a78d6", linewidth=2, zorder=3)
    for yi, (pc, r) in zip(y, effect.iterrows()):
        a2.text(r["hi"] + 0.01, yi, f"{r['coef']:+.2f}", va="center", fontsize=9, color=INK)
    a2.set_yticks(y, [NAMES[p] for p in PCS])
    a2.set_xlabel("xG/90 change per +1 SD (95% CI)")
    a2.set_xlim(-0.2, 0.55)
    a2.set_title("How much each component moves xG", pad=52, fontsize=10, color=INK_2)
    a2.spines["left"].set_visible(False)
    a2.tick_params(axis="y", length=0)
    a2.text(0.98, 1.0, "filled = p < 0.05", transform=a2.transAxes, ha="right", fontsize=8, color=INK_2)

    r2 = baseline.ols.rsquared
    return _finish(fig, "Control, directness and ball-carrying go with chances; pressing height does not",
                   f"PCA of 12 style metrics over 126 team-matches (final excluded), then xG/90 regressed on the "
                   f"5 components. R² = {r2:.2f}.", "fig1_what_drives_xg")


def actual_vs_predicted(teams):
    """Fig 2: every team's average actual xG/90 against what its style predicts."""
    fig, ax = plt.subplots(figsize=(9, 7.4))
    fig.subplots_adjust(left=0.1, right=0.96, top=0.84, bottom=0.12)
    lim = (0.25, 1.95)
    ax.plot(lim, lim, color=MUTED, lw=1, ls="--")
    ax.text(1.85, 1.80, "as predicted", rotation=38, color=INK_2, fontsize=8, ha="right")
    rest = teams.drop(list(TEAM_COLORS))
    ax.scatter(rest.predicted, rest.xg_p90, s=40, color=OTHER, edgecolor=SURFACE, linewidth=1.5)
    for t in ["Brazil", "Spain", "England", "Morocco", "Croatia", "Germany"]:
        if t in rest.index:
            ax.annotate(t, (rest.predicted[t], rest.xg_p90[t]), xytext=(6, -3), textcoords="offset points",
                        fontsize=8, color=INK_2)
    for t, c in TEAM_COLORS.items():
        r = teams.loc[t]
        ax.scatter(r.predicted, r.xg_p90, s=110, color=c, edgecolor=SURFACE, linewidth=2, zorder=4)
        ax.annotate(t, (r.predicted, r.xg_p90), xytext=(9, 4), textcoords="offset points",
                    fontsize=10, fontweight="bold", color=INK)
    a = teams.loc["Argentina"]
    # Without penalties: actual npxG against the prediction of the same model refitted on npxG.
    ax.scatter(a.npxg_predicted, a.npxg_p90, s=110, facecolor=SURFACE, edgecolor=TEAM_COLORS["Argentina"],
               linewidth=2, zorder=4)
    ax.annotate("", xy=(a.npxg_predicted, a.npxg_p90 + 0.03), xytext=(a.predicted, a.xg_p90 - 0.03),
                arrowprops=dict(arrowstyle="->", color=INK_2, lw=1.2))
    ax.annotate(f"Hollow: Argentina without penalties,\nagainst the same model fitted on non-penalty xG.\n"
                f"It lands on the line: 4 penalties in 6 games\nwere worth {a.pen_xg_p90:.2f} xG/90.",
                (a.npxg_predicted, a.npxg_p90), xytext=(0.30, 1.60), textcoords="data", fontsize=8.5,
                color=INK_2, va="top")
    ax.set_xlim(*lim)
    ax.set_ylim(*lim)
    ax.set_xlabel("xG per 90 predicted from style (tournament model)")
    ax.set_ylabel("Actual xG per 90 (incl. penalties)")
    return _finish(fig, "Argentina out-created their style, and the surplus is penalties",
                   "Team averages over matches before the final (regulation time). Above the line = more xG than "
                   "the style predicts.", "fig2_actual_vs_predicted")


def team_contributions(scored_team_avgs, final_scored, intercept):
    """Fig 3: which components lifted or lowered each team's xG vs an average team; tournament vs final."""
    rows = [f"contrib_{p}" for p in PCS] + ["residual"]
    labels = [NAMES[p] for p in PCS] + ["Not explained by style"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6), sharey=True)
    fig.subplots_adjust(left=0.17, right=0.97, top=0.78, bottom=0.14, wspace=0.08)
    y = np.arange(len(rows))[::-1]
    for ax, team in zip(axes, TEAM_COLORS):
        avg, fin = scored_team_avgs.loc[team, rows], final_scored.loc[team, rows]
        ax.axvline(0, color=MUTED, lw=1)
        ax.barh(y, avg.values, height=0.55, color=TEAM_COLORS[team], edgecolor=SURFACE, linewidth=2)
        ax.scatter(fin.values, y, marker="D", s=46, color=INK, zorder=3, label="Final (first 90 minutes)")
        for yi, v in zip(y, avg.values):
            ax.text(v + (0.02 if v >= 0 else -0.02), yi + 0.32, f"{v:+.2f}", ha="left" if v >= 0 else "right",
                    fontsize=8, color=INK_2)
        ax.set_yticks(y, labels)
        ax.set_xlim(-0.75, 0.85)
        ax.set_xlabel("xG per 90 vs an average team")
        tot = scored_team_avgs.loc[team, "xg_p90"]
        ax.set_title(f"{team}: {tot:.2f} xG/90 before the final (average team {intercept:.2f})", fontsize=10)
    axes[0].annotate("≈ penalty surplus", (0.33, y[-1]), xytext=(6, -14), textcoords="offset points", fontsize=8,
                     color=INK_2)
    axes[1].legend(loc="upper right", bbox_to_anchor=(1.0, 1.2), frameon=False, fontsize=9, handletextpad=0.2)
    return _finish(fig, "Argentina's xG came from control and carrying; France's mostly from carrying",
                   "Bars: average contribution of each style component across the 6 matches before the final. "
                   "Diamonds: the same in the final (first 90 minutes).", "fig3_team_contributions")


def final_by_game_state(windows):
    """Fig 4: how the final changed with the score, and what extra time looked like."""
    panels = [("xg_p90", "xG per 90"), ("pressure_height", "Pressure height (x, higher = further up)"),
              ("progressive_carries_p90", "Progressive carries per 90")]
    order = list(dict.fromkeys(windows.index.get_level_values(0)))
    x = np.arange(len(order))
    fig, axes = plt.subplots(1, 3, figsize=(13, 5))
    fig.subplots_adjust(left=0.05, right=0.98, top=0.76, bottom=0.2, wspace=0.25)
    for ax, (col, label) in zip(axes, panels):
        ax.axvspan(len(order) - 1.5, len(order) - 0.5, color="#f0efec", zorder=0)
        for (team, c), dx in zip(TEAM_COLORS.items(), (-0.06, 0.06)):
            v = windows.xs(team, level=1).loc[order, col].values
            ax.plot(x + dx, v, color=c, lw=2, marker="o", ms=8, mec=SURFACE, mew=1.5, label=team)
        ax.set_xticks(x, order, fontsize=8.5)
        ax.set_title(label, fontsize=10)
        ax.yaxis.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)
    axes[0].text(len(order) - 1, axes[0].get_ylim()[1], "extra time", ha="center", va="top", fontsize=8,
                 color=INK_2)
    axes[0].legend(frameon=False, fontsize=9, loc="upper left")
    return _finish(fig, "France's comeback came with a higher press and more carries; extra time was Argentina's",
                   "The final split by score state. Both late France xG points include a penalty (0.78 xG each). "
                   "Short windows are noisy: 79–90' is about 19 minutes of play.", "fig4_final_by_game_state")
