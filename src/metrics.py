"""The 12 style metrics and the xG target, one row per team per match.

Coordinates are StatsBomb's 120 x 80 pitch, always from the acting team's
point of view (x = 120 is the goal it attacks).
"""
import numpy as np
import pandas as pd

GOAL = np.array([120.0, 40.0])
FINAL_THIRD_X = 80
SET_PIECE_PASSES = {"Kick Off", "Throw-in", "Free Kick", "Corner", "Goal Kick"}
WON_INTERCEPTIONS = {"Won", "Success In Play", "Success To Team"}
LONG_BALL = 35  # StatsBomb units are roughly yards

METRICS = {
    # name: (pillar, plain-language definition)
    "possession_share": ("Build-up", "Share of all passes in the match made by the team"),
    "passes_per_possession": ("Build-up", "Open-play passes per team possession"),
    "pass_completion_under_pressure": ("Build-up", "Completion rate of open-play passes made under pressure"),
    "progressive_passes_p90": ("Progression", "Completed open-play passes that cut the distance to goal by 25%+ (starting outside own third), per 90"),
    "progressive_carries_p90": ("Progression", "Carries of 5+ units that cut the distance to goal by 25%+ (starting outside own third), per 90"),
    "directness": ("Progression", "Average forward gain (x) per open-play pass"),
    "long_ball_share": ("Progression", "Share of open-play passes of 35+ units"),
    "field_tilt": ("Territory", "Team share of both teams' passes made in the final third"),
    "crosses_per_entry": ("Territory", "Open-play crosses per final-third entry"),
    "pressures_per_opp_possession": ("Pressing", "Pressures per opponent possession"),
    "pressure_height": ("Pressing", "Average x of the team's pressures (higher = further up the pitch)"),
    "high_regains_p90": ("Pressing", "Ball recoveries and won interceptions in the opponent half, per 90"),
}


def _xy(col):
    """Split a column of [x, y] lists into two float arrays."""
    arr = np.full((len(col), 2), np.nan)
    for i, v in enumerate(col):
        if isinstance(v, (list, tuple)) and len(v) >= 2:
            arr[i] = v[:2]
    return arr[:, 0], arr[:, 1]


def prepare(ev):
    """Add numeric coordinates and helper flags once, for the whole event table."""
    ev = ev.copy()
    ev["x"], ev["y"] = _xy(ev["location"])
    end = ev["pass_end_location"].where(ev["type"] == "Pass", ev["carry_end_location"])
    ev["end_x"], ev["end_y"] = _xy(end)
    d0 = np.hypot(GOAL[0] - ev.x, GOAL[1] - ev.y)
    d1 = np.hypot(GOAL[0] - ev.end_x, GOAL[1] - ev.end_y)
    ev["progressive"] = (d1 <= 0.75 * d0) & (ev.x >= 40)
    ev["open_play_pass"] = (ev.type == "Pass") & ~ev.pass_type.isin(SET_PIECE_PASSES)
    ev["completed"] = (ev.type == "Pass") & ev.pass_outcome.isna()
    ev["under_pressure"] = ev.under_pressure.fillna(False).astype(bool)
    ev["pass_cross"] = ev.pass_cross.fillna(False).astype(bool)
    ts = pd.to_timedelta(ev.timestamp).dt.total_seconds()
    ev["t"] = ts  # seconds within the period
    return ev


def played_minutes(ev):
    """Minutes spanned by the given events, summed over periods (works for any time window)."""
    t = ev.groupby("period").t
    return (t.max() - t.min()).sum() / 60


def team_match_row(ev, team):
    """All metrics + xG for one team, computed on the events passed in."""
    mins = played_minutes(ev)
    p90 = 90 / mins
    own, opp = ev[ev.team == team], ev[ev.team != team]
    passes = own[own.type == "Pass"]
    op = own[own.open_play_pass]
    op_under = op[op.under_pressure]
    carries = own[own.type == "Carry"]
    carry_len = np.hypot(carries.end_x - carries.x, carries.end_y - carries.y)
    team_poss = ev.loc[ev.possession_team == team, "possession"].nunique()
    opp_poss = ev.loc[ev.possession_team != team, "possession"].nunique()
    all_passes = ev[ev.type == "Pass"]
    ft_passes = all_passes[all_passes.x >= FINAL_THIRD_X]
    entries = (
        ((op.x < FINAL_THIRD_X) & (op.end_x >= FINAL_THIRD_X) & op.completed).sum()
        + ((carries.x < FINAL_THIRD_X) & (carries.end_x >= FINAL_THIRD_X)).sum()
    )
    pressures = own[own.type == "Pressure"]
    regains = own[
        ((own.type == "Ball Recovery") & own.ball_recovery_recovery_failure.isna())
        | ((own.type == "Interception") & own.interception_outcome.isin(WON_INTERCEPTIONS))
    ]
    shots = own[own.type == "Shot"]
    pens = shots.shot_type == "Penalty"
    return {
        "team": team,
        "minutes": mins,
        "possession_share": len(passes) / max(len(all_passes), 1),
        "passes_per_possession": len(op) / max(team_poss, 1),
        "pass_completion_under_pressure": op_under.completed.mean(),
        "progressive_passes_p90": (op.completed & op.progressive).sum() * p90,
        "progressive_carries_p90": ((carry_len >= 5) & carries.progressive).sum() * p90,
        "directness": (op.end_x - op.x).mean(),
        "long_ball_share": (op.pass_length >= LONG_BALL).mean(),
        "field_tilt": (ft_passes.team == team).mean(),
        "crosses_per_entry": op.pass_cross.sum() / max(entries, 1),
        "pressures_per_opp_possession": len(pressures) / max(opp_poss, 1),
        "pressure_height": pressures.x.mean(),
        "high_regains_p90": (regains.x >= 60).sum() * p90,
        # target and context
        "xg_p90": shots.shot_statsbomb_xg.sum() * p90,
        "npxg_p90": shots.loc[~pens, "shot_statsbomb_xg"].sum() * p90,
        "xg": shots.shot_statsbomb_xg.sum(),
        "pen_xg": shots.loc[pens, "shot_statsbomb_xg"].sum(),
        "shots": len(shots),
        "goals": (shots.shot_outcome == "Goal").sum(),
    }


def team_match_table(ev, matches, periods=(1, 2, 3, 4)):
    """One row per team per match over `periods` (default: all open play incl. extra time, no shootout)."""
    meta = matches.set_index("match_id")
    rows = []
    for mid, g in ev[ev.period.isin(periods)].groupby("match_id"):
        m = meta.loc[mid]
        for team, opp in [(m.home_team, m.away_team), (m.away_team, m.home_team)]:
            r = team_match_row(g, team)
            r.update(match_id=mid, opponent=opp, stage=m.competition_stage, date=m.match_date)
            rows.append(r)
    cols = ["match_id", "date", "stage", "team", "opponent"]
    df = pd.DataFrame(rows)
    return df[cols + [c for c in df.columns if c not in cols]].sort_values(["date", "match_id"])
