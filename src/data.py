"""Load and cache StatsBomb open data for the 2022 FIFA World Cup."""
import warnings
from pathlib import Path

import pandas as pd
from statsbombpy import sb

warnings.filterwarnings("ignore", message="credentials were not supplied")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
COMPETITION, SEASON_NAME = "FIFA World Cup", "2022"


def world_cup_ids():
    """Look up the competition and season ids instead of hard-coding them."""
    c = sb.competitions()
    row = c[(c.competition_name == COMPETITION) & (c.season_name == SEASON_NAME)].iloc[0]
    return int(row.competition_id), int(row.season_id)


def matches():
    path = DATA_DIR / "matches.pkl"
    if path.exists():
        return pd.read_pickle(path)
    comp_id, season_id = world_cup_ids()
    m = sb.matches(competition_id=comp_id, season_id=season_id)
    DATA_DIR.mkdir(exist_ok=True)
    m.to_pickle(path)
    return m


def events():
    """All events of all 64 matches in one frame (cached after the first pull)."""
    path = DATA_DIR / "events.pkl"
    if path.exists():
        return pd.read_pickle(path)
    frames = [sb.events(match_id=int(mid)) for mid in matches().match_id]
    ev = pd.concat(frames, ignore_index=True)
    ev.to_pickle(path)
    return ev


def final_match_id():
    m = matches()
    return int(m.loc[m.competition_stage == "Final", "match_id"].iloc[0])
