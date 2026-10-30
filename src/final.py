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
