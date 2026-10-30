"""The final: split by score state, with extra time as its own window."""
import pandas as pd

import metrics as M

# (label, start, end) as (period, minute, second); the end is exclusive. Score times come from the event data.
WINDOWS = [
    ("0–22'\n0–0", (1, 0, 0), (1, 22, 24)),
    ("22–79'\nARG lead", (1, 22, 24), (2, 79, 24)),
    ("79–90'\nFRA comeback", (2, 79, 24), (3, 0, 0)),
    ("91–120'\nextra time", (3, 0, 0), (5, 0, 0)),
]


def goals(ev):
    shots = ev[(ev.type == "Shot") & (ev.shot_outcome == "Goal") & (ev.period < 5)]
    return shots[["period", "minute", "second", "team", "player", "shot_type"]]


def substitutions(ev):
    subs = ev[ev.type == "Substitution"]
    return subs[["period", "minute", "second", "team", "player", "substitution_replacement", "substitution_outcome"]]


def by_window(final_ev):
    key = final_ev.period * 10_000 + final_ev.minute * 60 + final_ev.second
    rows = []
    for label, (p0, m0, s0), (p1, m1, s1) in WINDOWS:
        g = final_ev[(key >= p0 * 10_000 + m0 * 60 + s0) & (key < p1 * 10_000 + m1 * 60 + s1)]
        for team in ["Argentina", "France"]:
            rows.append({"window": label, **M.team_match_row(g, team)})
    return pd.DataFrame(rows).set_index(["window", "team"])


SHORT_NAMES = {"Lionel Andrés Messi Cuccittini": "Messi", "Ángel Fabián Di María Hernández": "Di María",
               "Kylian Mbappé Lottin": "Mbappé"}


def _elapsed(final_ev):
    """Minutes of play since kick-off, stoppage time included (periods laid end to end)."""
    lengths = final_ev[final_ev.period < 5].groupby("period").t.max() / 60
    starts = lengths.cumsum().shift(fill_value=0)
    return final_ev.period.map(starts) + final_ev.t / 60, list(starts.values), float(lengths.sum())


def xg_timeline(final_ev):
    """Shots (with cumulative-xG inputs) and substitutions on one elapsed-time axis, shootout excluded."""
    ev = final_ev[final_ev.period < 5].copy()
    ev["elapsed"], starts, end = _elapsed(ev)
    shots = ev[ev.type == "Shot"].assign(
        xg=lambda d: d.shot_statsbomb_xg, penalty=lambda d: d.shot_type == "Penalty",
        goal=lambda d: d.shot_outcome == "Goal",
    )
    shots["label"] = [
        f"{SHORT_NAMES.get(p, p)}{' (pen)' if pen else ''} {m + 1}'"
        for p, pen, m in zip(shots.player, shots.penalty, shots.minute)
    ]
    shots = shots[["team", "elapsed", "xg", "penalty", "goal", "label"]].sort_values("elapsed")
    shots.attrs["end"] = end
    subs = ev[ev.type == "Substitution"][["team", "elapsed"]]
    return shots, subs, starts
