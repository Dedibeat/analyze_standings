#!/usr/bin/env python3
"""Team-level table for predicting regional gold with TabFM (BigQuery ``AI.PREDICT``).

One row per official team of the 2023-2025 mainland Asia East regionals
(Hong Kong/Macau excluded, as in ``arch_b.online_gold``).  Every feature is
known before the contest starts; each carries an availability tier so a run
can choose how late its prediction is made:

* ``online``        official online-round results of the team and its school
* ``rules``         site notice: capacity, bands, caps, WF/host entitlement
* ``history``       earlier regional results (previous season, and earlier
                    regionals of this season) of the team's members and school
* ``registration``  the registered official field (who attends, band/quota)

Labels: ``gold`` (BOOL -> AI.PREDICT classification with probabilities),
``medal`` (STRING, 4 classes) and ``rank_pct`` (FLOAT, regression).  No
feature uses the contest's own results; season-level quantities that are fit
on labels (rho, kappa) are left out, and the rules line uses no quota
adjustment.

Writes ``data/tabfm_gold/``: ``teams.csv``, ``schema.json`` (BigQuery load
schema), ``features.json`` (feature list, tiers, splits) and ``predict.sql``
(four AI.PREDICT calls: all features and the pre-registration subset, each
on the two leave-season-out splits).  Needs network once for the
XCPCIO contest dates (cached in ``data/ec_online_cache``).

    python3 scripts/build_tabfm_gold_data.py
"""

import collections
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from build_ec_online_data import CACHE, REGIONALS, fetch  # noqa: E402

from arch_b import online_gold as og  # noqa: E402
from arch_b import quota_teams as qt  # noqa: E402

OUT = ROOT / "data" / "tabfm_gold"
XCPCIO = "https://board.xcpcio.com/data/icpc/"
MEDAL_LEVEL = {"gold": 3, "silver": 2, "bronze": 1, "": 0}
SPLITS = {"test_2024": {"train": ["2023"], "test": "2024"},
          "test_2025": {"train": ["2023", "2024"], "test": "2025"}}

# (name, BigQuery type, tier, description)
FEATURES = [
    ("online_x", "FLOAT64", "online", "-mean(log online rank) over rounds entered; NULL if unlinked"),
    ("online_rank_r1", "INT64", "online", "round-1 team rank; NULL if absent or unranked"),
    ("online_rank_r2", "INT64", "online", "round-2 team rank; NULL if absent or unranked"),
    ("online_solved_r1", "INT64", "online", "round-1 problems solved"),
    ("online_solved_r2", "INT64", "online", "round-2 problems solved"),
    ("online_rounds", "INT64", "online", "online rounds the linked team entered (0-2)"),
    ("online_link", "STRING", "online", "how the regional team was linked: name / roster / none"),
    ("school_rank_combined", "INT64", "online", "school's combined online rank (slot rules use it)"),
    ("school_rank_best_round", "INT64", "online", "school's better per-round school rank"),
    ("school_online_teams", "INT64", "online", "school's teams in the online rounds"),
    ("school_top100_teams", "INT64", "online", "school's distinct teams ranked <= 100 in a round"),
    ("band_slots", "INT64", "rules", "school's rank-band slots at this site"),
    ("school_wf", "BOOL", "rules", "school reached a WF counted this season"),
    ("school_host", "BOOL", "rules", "school hosts an EC regional this or last season"),
    ("school_invitational", "BOOL", "rules", "school medalled at this site's spring invitational"),
    ("school_local", "BOOL", "rules", "school is on the site province's provincial board"),
    ("school_non_mainland", "BOOL", "rules", "Hong Kong / Macau / Taiwan / foreign school"),
    ("site_capacity", "INT64", "rules", "notice's official capacity"),
    ("site_band_seats", "INT64", "rules", "sum of rank-band slots"),
    ("site_quota_share", "FLOAT64", "rules", "1 - band seats / capacity"),
    ("site_school_cap", "INT64", "rules", "ordinary per-school team cap"),
    ("site_two_slot_band", "INT64", "rules", "last school rank with 2 band slots (0 if none)"),
    ("site_team_count_clause", "BOOL", "rules", ">=3 teams in the top N clause"),
    ("site_rules_line_x", "FLOAT64", "rules", "online strength of the 10% line among rule-admitted teams"),
    ("site_top50_entitlement", "INT64", "rules", "top-50 schools' WF/host quota seats (quota_teams)"),
    ("season_order", "INT64", "rules", "position of the regional in the season's calendar"),
    ("members_prev_regionals", "INT64", "history", "members with a previous-season official regional; NULL w/o members"),
    ("members_prev_golds", "INT64", "history", "members with a previous-season regional gold"),
    ("members_prev_best_medal", "INT64", "history", "best previous-season medal of a member (0-3)"),
    ("members_prev_best_rank_pct", "FLOAT64", "history", "best previous-season official rank / field"),
    ("earlier_regionals", "INT64", "history", "this season's earlier regionals of this team"),
    ("earlier_best_medal", "INT64", "history", "best medal there (0-3)"),
    ("earlier_best_rank_pct", "FLOAT64", "history", "best official rank / field there; NULL if none"),
    ("school_prev_golds", "INT64", "history", "school's previous-season regional golds"),
    ("school_prev_medals", "INT64", "history", "school's previous-season regional medals"),
    ("admission", "STRING", "registration", "band (online seat) or quota"),
    ("quota_channel", "STRING", "registration", "quota channel (quota_teams); '' for band teams"),
    ("team_index_in_school", "INT64", "registration", "1 = school's strongest-online team at the site"),
    ("school_teams_at_site", "INT64", "registration", "school's official teams at the site"),
    ("field_teams", "INT64", "registration", "official teams at the site"),
    ("field_linked_share", "FLOAT64", "registration", "share of the field linked to an online team"),
    ("field_top50_quota_teams", "INT64", "registration", "quota teams from top-50 online schools"),
    ("field_line_x", "FLOAT64", "registration", "strength of the 10% line among linked attendees"),
    ("field_strength_rank", "INT64", "registration", "team's online-strength rank among linked attendees"),
    ("x_minus_field_line", "FLOAT64", "registration", "online_x - field_line_x"),
]
LABELS = [("gold", "BOOL"), ("medal", "STRING"), ("rank_pct", "FLOAT64")]
IDS = [("row_id", "STRING"), ("season", "STRING"), ("site", "STRING"), ("school", "STRING"), ("team", "STRING")]


def contest_dates():
    out = {}
    for season, sites in REGIONALS.items():
        for site, board in sites.items():
            path = fetch(XCPCIO + board + "/config.json", CACHE / "xcpcio" / board.replace("/", "_") / "config.json")
            t = json.loads(path.read_text())["start_time"]
            t = t / 1000 if t > 1e11 else t
            out[(str(season), site)] = datetime.fromtimestamp(t, timezone.utc).date().isoformat()
    return out


def regional_entries(data, dates):
    """Every official regional result 2022-2025 (all sites), for history features."""
    size = collections.Counter((r["season"], r["site"]) for r in data["regional_teams"] if r["official"] == "1")
    out = []
    for r in data["regional_teams"]:
        if r["official"] != "1":
            continue
        out.append(dict(season=r["season"], site=r["site"], date=dates[(r["season"], r["site"])],
                        school=og.norm_school(r["school"]), team=og.norm_name(r["team"]),
                        members={og.norm_name(m) for m in r["members"].split("|") if m.strip()},
                        level=MEDAL_LEVEL[r["medal"]],
                        rank_pct=int(r["official_rank"]) / size[(r["season"], r["site"])]))
    return out


def online_index(data):
    teams = collections.defaultdict(dict)
    for r in data["online_teams"]:
        key = (r["season"], og.norm_school(r["school"]), og.norm_name(r["team"]))
        teams[key][r["round"]] = (int(r["rank"]) if r["rank"] else None, int(r["solved"]))
    schools = collections.defaultdict(dict)
    for r in data["online_schools"]:
        schools[(r["season"], og.norm_school(r["school"]))][r["table"]] = int(r["rank"])
    depth = collections.defaultdict(lambda: [set(), set()])
    for (season, school, team), rounds in teams.items():
        depth[(season, school)][0].add(team)
        if any(rank and rank <= 100 for rank, _ in rounds.values()):
            depth[(season, school)][1].add(team)
    return teams, schools, depth


def site_features(season, site, data, ev, strengths, dates):
    rule = data["rules"][(season, site)]
    slots = og.school_slots(season, rule, data)
    bands = rule["online_bands"]
    mainland = sorted(d for (s, st), d in dates.items() if s == season and st not in og.EXCLUDED_SITES)
    return dict(site_capacity=rule["official_capacity"], site_band_seats=sum(slots.values()),
                site_quota_share=round(max(0.0, 1 - sum(slots.values()) / rule["official_capacity"]), 4),
                site_school_cap=rule.get("school_cap") or 4,
                site_two_slot_band=max([hi for lo, hi, n in bands if n >= 2], default=0),
                site_team_count_clause=bool(rule.get("team_count_clause")),
                site_rules_line_x=round(og.rules_line(season, site, data, strengths), 5),
                site_top50_entitlement=qt.elite_entitlement(season, site, data, ev),
                season_order=mainland.index(dates[(season, site)]) + 1)


def history(team, entries_by_school, season, date):
    """Previous-season results of the members, this season's earlier results of the team."""
    prev = entries_by_school.get((str(int(season) - 1), team["school"]), [])
    now = entries_by_school.get((season, team["school"]), [])
    out = {}
    if team["members"]:
        mine = [[e for e in prev if m in e["members"]] for m in team["members"]]
        out.update(members_prev_regionals=sum(1 for es in mine if es),
                   members_prev_golds=sum(1 for es in mine if any(e["level"] == 3 for e in es)),
                   members_prev_best_medal=max((e["level"] for es in mine for e in es), default=0),
                   members_prev_best_rank_pct=min((round(e["rank_pct"], 4) for es in mine for e in es),
                                                  default=None))
    else:  # boards without member names (Xi'an 2023)
        out.update(members_prev_regionals=None, members_prev_golds=None,
                   members_prev_best_medal=None, members_prev_best_rank_pct=None)
    earlier = [e for e in now if e["date"] < date and
               (len(team["members"] & e["members"]) >= 2 or e["team"] == team["team"])]
    out.update(earlier_regionals=len(earlier),
               earlier_best_medal=max((e["level"] for e in earlier), default=0),
               earlier_best_rank_pct=min((round(e["rank_pct"], 4) for e in earlier), default=None),
               school_prev_golds=sum(1 for e in prev if e["level"] == 3),
               school_prev_medals=sum(1 for e in prev if e["level"] > 0))
    return out


def build():
    data = og.load()
    strengths = og.online_strengths(data["online_teams"])
    ev = qt.load_evidence()
    dates = contest_dates()
    entries = regional_entries(data, dates)
    by_school = collections.defaultdict(list)
    for e in entries:
        by_school[(e["season"], e["school"])].append(e)
    online, schools, depth = online_index(data)
    link = {(r["season"], r["site"], r["team"], r["school"]): r for r in og.link_regionals(data, strengths)}
    regional = {(r["season"], r["site"], r["team"], r["school"]): r
                for r in data["regional_teams"] if r["official"] == "1"}
    table = qt.team_table(data, strengths, ev)
    rows = []
    for (season, site), rs in sorted(qt._group(table, ("season", "site")).items()):
        date = dates[(season, site)]
        site_f = site_features(season, site, data, ev, strengths, dates)
        xs = sorted((link[(season, site, r["team"], r["school"])]["x"] for r in rs
                     if link[(season, site, r["team"], r["school"])]["x"] is not None), reverse=True)
        line = xs[max(1, round(og.GOLD_FRACTION * len(xs))) - 1]
        top50_quota = sum(1 for r in rs if r["admission"] == "quota" and r["school_online_rank"]
                          and r["school_online_rank"] <= qt.TOP_SCHOOLS)
        index = collections.Counter()
        for r in rs:  # team_table lists each school's teams strongest-online first
            key = (season, site, r["team"], r["school"])
            reg, x, okey = regional[key], link[key]["x"], link[key]["online_key"]
            school = og.norm_school(r["school"])
            index[school] += 1
            rounds = online.get(okey, {}) if okey else {}
            srank = schools.get((season, school), {})
            channels = set(r["school_channels"].split("|")) - {""}
            team = dict(school=school, team=og.norm_name(r["team"]),
                        members={og.norm_name(m) for m in reg["members"].split("|") if m.strip()})
            row = dict(row_id=f"{season}/{site}/{reg['team_id']}", season=season, site=site,
                       school=r["school"], team=r["team"],
                       online_x=round(x, 5) if x is not None else None,
                       online_rank_r1=rounds.get("1", (None,))[0], online_rank_r2=rounds.get("2", (None,))[0],
                       online_solved_r1=rounds["1"][1] if "1" in rounds else None,
                       online_solved_r2=rounds["2"][1] if "2" in rounds else None,
                       online_rounds=len(rounds), online_link=link[key]["link"] or "none",
                       school_rank_combined=srank.get("combined"),
                       school_rank_best_round=min([srank[t] for t in ("round1", "round2") if t in srank],
                                                  default=None),
                       school_online_teams=len(depth[(season, school)][0]),
                       school_top100_teams=len(depth[(season, school)][1]),
                       band_slots=r["band_slots"], school_wf="wf" in channels, school_host="host" in channels,
                       school_invitational="invitational" in channels, school_local="local" in channels,
                       school_non_mainland="non_mainland" in channels, **site_f,
                       **history(team, by_school, season, date),
                       admission=r["admission"], quota_channel=r["channel"],
                       team_index_in_school=index[school], school_teams_at_site=r["school_teams"],
                       field_teams=len(rs), field_linked_share=round(len(xs) / len(rs), 4),
                       field_top50_quota_teams=top50_quota, field_line_x=round(line, 5),
                       field_strength_rank=xs.index(x) + 1 if x is not None else None,
                       x_minus_field_line=round(x - line, 5) if x is not None else None,
                       gold=reg["medal"] == "gold", medal=reg["medal"] or "none",
                       rank_pct=round(int(reg["official_rank"]) / len(rs), 5))
            rows.append(row)
    return rows


def sql(feature_sets):
    """AI.PREDICT calls: one per (feature set, leave-season-out split)."""
    parts = ["-- Replace PROJECT.DATASET; load teams.csv with schema.json (skip the header row).",
             "-- A BOOL label makes AI.PREDICT classify; p_gold is the probability of label 'true'",
             "-- (check the label spelling in predicted_gold_probs with a smoke query first).",
             "-- Save each result as CSV (row_id, p_gold) and score: python3 -m arch_b.tabfm_gold --score FILE", ""]
    for set_name, features in feature_sets.items():
        cols = ",\n    ".join(features)
        for name, split in SPLITS.items():
            train = ", ".join(f"'{s}'" for s in split["train"])
            parts.append(f"""-- {set_name} / {name}: train on {split['train']}, predict {split['test']}.
-- Every non-label column of the training query is a feature, so ids appear only on the prediction side.
SELECT row_id, (SELECT prob FROM UNNEST(predicted_gold_probs) WHERE label = 'true') AS p_gold
FROM AI.PREDICT(
  (SELECT
    {cols},
    gold
   FROM `PROJECT.DATASET.teams` WHERE season IN ({train})),
  (SELECT
    row_id,
    {cols}
   FROM `PROJECT.DATASET.teams` WHERE season = '{split['test']}'),
  label_col => 'gold');
""")
    return "\n".join(parts)


def write(rows):
    OUT.mkdir(parents=True, exist_ok=True)
    fields = [n for n, _ in IDS] + [n for n, *_ in FEATURES] + [n for n, _ in LABELS]
    with open(OUT / "teams.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r[k] is None else str(r[k]).lower() if isinstance(r[k], bool) else r[k])
                        for k in fields})
    schema = [{"name": n, "type": t, "mode": "NULLABLE"} for n, t in IDS] + \
             [{"name": n, "type": t, "mode": "NULLABLE", "description": d} for n, t, _, d in FEATURES] + \
             [{"name": n, "type": t, "mode": "NULLABLE"} for n, t in LABELS]
    (OUT / "schema.json").write_text(json.dumps(schema, ensure_ascii=False, indent=1) + "\n")
    names = [n for n, *_ in FEATURES]
    meta = {"rows": len(rows), "features": [{"name": n, "type": t, "tier": tier, "description": d}
                                            for n, t, tier, d in FEATURES],
            "labels": dict(LABELS), "ids": [n for n, _ in IDS], "splits": SPLITS,
            "feature_limit": "AI.PREDICT accepts up to 50 feature columns and 10 classes (docs, 2026-09-27)",
            "tiers": {t: [n for n, _, tt, _ in FEATURES if tt == t]
                      for t in ("online", "rules", "history", "registration")},
            "null_features": {n: sum(1 for r in rows if r[n] is None) for n in names}}
    (OUT / "features.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n")
    pre = [n for n, _, tier, _ in FEATURES if tier != "registration"]
    (OUT / "predict.sql").write_text(sql({"all_features": names, "pre_registration": pre}))


def main():
    rows = build()
    write(rows)
    gold = sum(r["gold"] for r in rows)
    print(f"{len(rows)} teams, {len(FEATURES)} features, {gold} golds -> {OUT}")


if __name__ == "__main__":
    main()
