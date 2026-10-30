# Data dictionary: StatsBomb open data, FIFA World Cup 2022

Source: StatsBomb open data (competition_id 43, season_id 106). 64 matches, all with events + 360.
Final: match_id 3869685. Counts below ("n") are from the final (4,407 events).

Coordinates: pitch is 120 x 80 (StatsBomb units, about yards). Origin is top-left. Every event is
drawn from the acting team's perspective, attacking left to right (x=120 is the opponent goal line).

## 1. Match level (one row per match, 64 rows)
| Variable | Meaning |
|---|---|
| match_id, match_date, kick_off | Match key, date, kick-off time |
| home_team / away_team (+ ids, group, country) | Teams; group letter for group stage |
| home_score / away_score | Final score incl. extra time, excl. shootout |
| competition_stage | Group Stage / Round of 16 / QF / SF / 3rd place / Final |
| match_week | Matchday number |
| stadium, referee (+ ids, country) | Venue and referee |
| home/away_manager_* | Manager name, nickname, DOB, nationality |
| match_status, match_status_360 | Whether events / 360 are available |
| data_version, shot_fidelity_version, xy_fidelity_version | StatsBomb spec versions (coordinate precision) |

## 2. Lineup level (one row per player per match)
| Variable | Meaning |
|---|---|
| player_id, player_name, player_nickname, jersey_number, country | Player identity |
| cards | Cards received (type, time) |
| positions | List of spells: position played, from/to clock time, from/to period, start_reason (Starting XI, Substitution - On, Tactical Shift), end_reason. Gives exact minutes played per position |

## 3. Event level (one row per on-ball action; ~4,400 per match, ~230k tournament)
### 3a. Common fields (every event)
| Variable | Meaning | Resolution |
|---|---|---|
| id, index | Unique event id (UUID); order within match | per event |
| period | 1, 2 = regulation halves; 3, 4 = extra-time halves; 5 = shootout | |
| timestamp, minute, second | Clock time. timestamp is ms within the period; minute is cumulative match minute | milliseconds |
| type | Event type (33 types, list below) | |
| team, team_id | Team performing the action | |
| player, player_id, position | Actor and the position they were playing at that moment | n=4,378 (missing only for team events) |
| location | [x, y] where the action happened | n=4,352 (missing for admin events) |
| duration | Seconds the action lasted (passes, carries, pressures) | n=3,293 |
| possession | Possession sequence number (increments when control changes) | per possession |
| possession_team | Team in possession during this sequence (may differ from `team` for defensive actions) | |
| play_pattern | How the possession started: Regular Play, From Counter, From Free Kick, From Corner, From Throw In, From Goal Kick, From Keeper, From Kick Off, Other | per possession |
| under_pressure | Actor was being pressured by an opponent | n=769 flagged |
| counterpress | Defensive action within 5 s of losing the ball | n=146 |
| off_camera | Event not visible on broadcast; location estimated | n=62 |
| out | Ball went out of play at this event | n=36 |
| related_events | IDs of linked events (e.g. pass to receipt, pressure to the pressured action) | |
| tactics | Formation (e.g. 433) + player-to-position map, only on Starting XI / Tactical Shift | n=9 |

### 3b. Event types (counts in final, ARG / FRA)
Pass 693/570 · Ball Receipt 625/489 · Carry 513/427 · Pressure 167/194 · Ball Recovery 59/56 ·
Duel 50/48 · Foul Committed 29/19 · Block 26/24 · Clearance 26/19 · Shot 24/14 · Dribbled Past 22/9 ·
Dribble 21/33 · Dispossessed 19/15 · Foul Won 18/26 · Goal Keeper 17/27 · Miscontrol 16/19 ·
Interception 13/15 · Substitution 6/7 · Injury Stoppage 6/3 · Half Start/End 5/5 · 50/50 4/4 ·
Tactical Shift 3/4 · Bad Behaviour 1/1 · Starting XI 1/1 · Player Off/On 1/0 · Offside 1/0 · Shield 0/1

### 3c. Type-specific fields
**Pass** (n=1,263)
| Variable | Meaning |
|---|---|
| pass_end_location | [x, y] where the pass ended |
| pass_length, pass_angle | Length (units) and angle (radians, 0 = straight forward) |
| pass_recipient(_id) | Intended/actual receiver (n=1,114; missing = incomplete with no clear target) |
| pass_outcome | Null = complete; else Incomplete, Out, Pass Offside, Unknown, Injury Clearance |
| pass_height | Ground / Low (below shoulder) / High |
| pass_body_part | Left Foot, Right Foot, Head, Other, Keeper Arm, No Touch |
| pass_type | Restart type: Kick Off, Throw-in, Free Kick, Corner, Goal Kick, Recovery, Interception |
| pass_technique | Through Ball, Inswinging, Outswinging, Straight |
| pass_cross, pass_switch, pass_through_ball | Flags: cross into box; switch of play (>50% pitch width); through ball |
| pass_shot_assist, pass_goal_assist, pass_assisted_shot_id | Pass led to a shot / goal; link to that shot |
| pass_aerial_won, pass_deflected, pass_inswinging/outswinging | Minor flags |

**Ball Receipt** (n=1,114): ball_receipt_outcome (null = controlled, Incomplete = not received).

**Carry** (n=940): carry_end_location; with location + duration gives distance and speed of each carry.

**Shot** (n=38)
| Variable | Meaning |
|---|---|
| shot_statsbomb_xg | xG = expected goals: probability the shot is scored (0–1) |
| shot_outcome | Goal, Saved, Off T(arget), Blocked, Wayward, Post, Saved to Post |
| shot_end_location | [x, y, z]: z is height at the goal line |
| shot_type | Open Play, Penalty, Free Kick, Corner |
| shot_body_part, shot_technique | Foot/head; Normal, Volley, Half Volley, Lob, Backheel, etc. |
| shot_first_time, shot_one_on_one, shot_aerial_won | Flags |
| shot_key_pass_id | Pass that created the shot |
| shot_freeze_frame | Location + identity + team of every player at the moment of the shot (named players, unlike 360) |

**Pressure** (n=361): location + duration only (who pressed, where, for how long).

**Duel** (n=98): duel_type (Aerial Lost, Tackle), duel_outcome (Won, Lost In Play, Success In Play, ...).

**Dribble** (n=54): dribble_outcome (Complete/Incomplete), nutmeg, overrun, no_touch.
**Dribbled Past**: defender who was beaten (location only).

**Ball Recovery** (n=115): recovery_failure, offensive flags. **Interception** (n=28): interception_outcome.

**Block / Clearance**: block_deflection, block_offensive, block_save_block; clearance_body_part, aerial_won.

**Goal Keeper** (n=44): goalkeeper_type (Shot Saved, Collected, Punch, Keeper Sweeper, Goal Conceded, Penalty Saved...), outcome, technique, position (Set/Moving/Prone), body_part, end_location.

**Foul Committed / Won**: type (Handball, Dangerous Play...), card, advantage, penalty, offensive/defensive flags.

**50/50**: outcome. **Miscontrol, Dispossessed**: location only. **Bad Behaviour**: card.

**Substitution** (n=13): player off (= player), substitution_replacement(_id) on, substitution_outcome (Tactical / Injury).

## 4. 360 frame level (one frame per event; 3,683 of 4,407 events in final, ~84%)
| Variable | Meaning |
|---|---|
| event_uuid | Links to event `id` |
| visible_area | Polygon of the pitch visible in the broadcast frame at that moment |
| freeze_frame[] | One entry per visible player (about 17 on average): |
| · location | [x, y] of that player |
| · teammate | True = same team as the event actor |
| · actor | True = the player performing the event |
| · keeper | True = goalkeeper |

**Limitation:** 360 players are anonymous (no player id except the actor), and only players inside the camera view are included. It supports team-shape measures (width, depth, defensive line height, players ahead of the ball) but not individual off-ball tracking.

## 5. Derived resolutions available
| Resolution | How |
|---|---|
| Per event | Native |
| Per possession | Group by `possession` (tempo, length, directness, how it started/ended) |
| Per phase / time window | Slice by period + timestamp (subs/goals give exact cut points) |
| Per player per phase | Lineups `positions` give exact minutes on pitch, so rates per 90 are exact |
| Player pairs | Pass to pass_recipient gives directed edges |
| Per match / per team (tournament) | 64 matches x 2 teams = 128 team-matches for baselines |
