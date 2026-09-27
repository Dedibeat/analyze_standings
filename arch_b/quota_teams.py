"""Which teams reached each Asia East regional through a quota seat, and why.

``arch_b.online_gold.quota_split`` counts quota entrants per contest: every
official team beyond its school's online rank-band slots (band slots go to
the school's strongest-online teams).  This module keeps the individual
teams and labels the channel that explains each seat, from the official
evidence in ``data/ec_online/quota_evidence.json``
(``scripts/build_quota_evidence.py``):

* ``host``          school hosted an EC regional that season or the previous
                    one (+2 seats; most notices count the last two seasons)
* ``wf``            school reached one of the season's counted World Finals (+1)
* ``invitational``  school medalled at the site's spring invitational (+1)
* ``non_mainland``  Hong Kong / Macau / Taiwan / foreign school (+1)
* ``local``         school is on the site province's provincial-contest board (+1)
* ``girls``         all-girl team flag on the board
* ``unexplained``   none of the above, or the school already used its
                    channel seats (wildcards, problem setters, second-round
                    applications)

Within a school, quota teams take the school's channels in the order above,
strongest team first; the split between two channels of one school is
therefore a convention, the school-level counts are not.

Validation: Shanghai 2024 and 2025 published every school's online and
reward seats; the inferred band/quota counts and the reward schools are
checked against them.

    python3 -m arch_b.quota_teams

Writes ``output/quota_teams.csv`` (one row per official team) and
``output/quota_teams.md``.
"""

import collections
import csv
import json
import math
import re

import numpy as np

from arch_b import online_gold as og

CHANNELS = ("host", "wf", "invitational", "non_mainland", "local", "girls", "unexplained")
CHANNEL_SEATS = {"host": 2, "wf": 1, "invitational": 1, "non_mainland": 1, "local": 1, "girls": 1}
NON_MAINLAND = re.compile(r"香港|澳门|澳門|台湾|臺灣|國立|蒙古国立")
CJK = re.compile(r"[一-鿿]")


def load_evidence():
    return json.loads((og.DATA / "quota_evidence.json").read_text())


def school_channels(season, site, school, ev):
    """Channels a school qualifies for at (season, site), in priority order."""
    s = og.norm_school(school)
    wf = {og.norm_school(x) for e in ev["wf_editions_by_season"].get(season, [])
          for x in ev["wf_schools"][str(e)]}
    hosts = {og.norm_school(x) for y in (season, str(int(season) - 1)) for x in ev["hosts"].get(y, {})}
    inv = ev["invitational_medal_schools"].get(f"{season}/{site}")
    local = {og.norm_school(x) for b in ev["provincial_schools"].get(site, {}).values() for x in b}
    out = []
    if s in hosts:
        out.append("host")
    if s in wf:
        out.append("wf")
    if inv and s in {og.norm_school(x) for x in inv["schools"]}:
        out.append("invitational")
    if NON_MAINLAND.search(school) or not CJK.search(school):
        out.append("non_mainland")
    if s in local:
        out.append("local")
    return out


def team_table(data, strengths, ev, seasons=og.MODEL_SEASONS):
    """One row per official mainland-regional team: band or quota, and channel."""
    girl = {(r["season"], r["site"], r["team"], r["school"]): r["girl"] == "1"
            for r in data["regional_teams"] if r["official"] == "1"}
    comb = {(r["season"], og.norm_school(r["school"])): int(r["rank"])
            for r in data["online_schools"] if r["table"] == "combined"}
    regional = collections.defaultdict(list)
    for r in og.link_regionals(data, strengths):
        if r["season"] in seasons and r["site"] not in og.EXCLUDED_SITES:
            regional[(r["season"], r["site"])].append(r)
    rows = []
    for (season, site), teams in sorted(regional.items()):
        rule = data["rules"].get((season, site))
        if not rule or not rule.get("online_bands"):
            continue
        slots = og.school_slots(season, rule, data)
        by_school = collections.defaultdict(list)
        for r in teams:
            by_school[og.norm_school(r["school"])].append(r)
        for school, rs in by_school.items():
            rs.sort(key=lambda r: -(r["x"] if r["x"] is not None else -1e9))
            k = slots.get(school, 0)
            channels = school_channels(season, site, rs[0]["school"], ev)
            left = [c for c in channels for _ in range(CHANNEL_SEATS[c])]
            for i, r in enumerate(rs):
                row = dict(season=season, site=site, school=r["school"], team=r["team"],
                           band_slots=k, school_teams=len(rs), school_online_rank=comb.get((season, school)),
                           school_channels="|".join(channels), linked=r["link"] or "none",
                           online_rank=round(math.exp(-r["x"]), 1) if r["x"] is not None else None,
                           gold=r["gold"], admission="band" if i < k else "quota", channel="")
                if row["admission"] == "quota":
                    if girl.get((season, site, r["team"], r["school"])):
                        row["channel"] = "girls"
                    elif left:
                        row["channel"] = left.pop(0)
                    else:
                        row["channel"] = "unexplained"
                rows.append(row)
    return rows


def medal_lookup(data):
    return {(r["season"], r["site"], r["team"], r["school"]): r["medal"]
            for r in data["regional_teams"] if r["official"] == "1"}


# ------------------------------------------------------------- validation

def shanghai_check(rows, ev):
    """Inferred Shanghai band/quota counts and reward schools vs the published lists."""
    out = {}
    for season, d in ev["shanghai_allocation"].items():
        pub = {og.norm_school(r["school"]): r for r in d["schools"]}
        at = collections.defaultdict(list)
        for r in rows:
            if (r["season"], r["site"]) == (season, "shanghai"):
                at[og.norm_school(r["school"])].append(r)
        band_ok = sum(1 for s, rs in at.items() if s in pub and rs[0]["band_slots"] == pub[s]["online"])
        on_list = [s for s in at if s in pub]
        over = {s: len(rs) - pub[s]["total"] for s, rs in at.items() if s in pub and len(rs) > pub[s]["total"]}
        quota = [r for rs in at.values() for r in rs if r["admission"] == "quota"]
        reward_pub = {s for s, r in pub.items() if r["reward"] > 0}
        reward_inf = {og.norm_school(r["school"]) for r in rows if r["season"] == season
                      and set(r["school_channels"].split("|")) & {"wf", "host"}}
        listed_reward_schools = {s for s in reward_pub if s in pub}
        out[season] = {
            "published_schools": len(pub), "attending_schools": len(at),
            "attending_on_list": len(on_list),
            "band_slots_match": f"{band_ok}/{len(on_list)}",
            "schools_over_published_total": over,
            "quota_teams": len(quota),
            "quota_teams_from_unlisted_schools": sum(1 for r in quota if og.norm_school(r["school"]) not in pub),
            "quota_teams_covered_by_published_reward": sum(
                min(pub[s]["reward"], max(0, len(rs) - pub[s]["online"]))
                for s, rs in at.items() if s in pub),
            "reward_schools_published": len(listed_reward_schools),
            "reward_schools_explained_by_wf_or_host": len(listed_reward_schools & reward_inf),
            "reward_schools_unexplained": sorted(pub[s]["school"] for s in listed_reward_schools - reward_inf),
            "inferred_wf_host_not_rewarded": sorted(
                {r["school"] for r in rows if r["season"] == season and og.norm_school(r["school"]) in pub
                 and og.norm_school(r["school"]) in reward_inf - reward_pub}),
        }
    return out


# ------------------------------------------------------------- patterns

def channel_summary(rows, medals):
    band = [r for r in rows if r["admission"] == "band"]
    band_gold = sum(r["gold"] for r in band) / len(band)
    out = {"band": _stats(band, medals, band_gold)}
    for c in CHANNELS:
        rs = [r for r in rows if r["channel"] == c]
        if rs:
            out[c] = _stats(rs, medals, band_gold)
    out["all_quota"] = _stats([r for r in rows if r["admission"] == "quota"], medals, band_gold)
    return out


def _stats(rs, medals, band_gold):
    ranks = [r["online_rank"] for r in rs if r["online_rank"] is not None]
    med = [medals.get((r["season"], r["site"], r["team"], r["school"]), "") for r in rs]
    gold = sum(r["gold"] for r in rs) / len(rs)
    return {"teams": len(rs), "gold": sum(r["gold"] for r in rs), "gold_rate": round(gold, 4),
            "relative_gold_rate": round(gold / band_gold, 3),
            "medal_rate": round(sum(1 for m in med if m) / len(rs), 3),
            "linked_online": round(len(ranks) / len(rs), 3),
            "median_online_rank": round(float(np.median(ranks)), 1) if ranks else None}


def by_contest(rows):
    out = []
    for (season, site), rs in sorted(_group(rows, ("season", "site")).items()):
        q = [r for r in rs if r["admission"] == "quota"]
        mix = collections.Counter(r["channel"] for r in q)
        out.append(dict(season=season, site=site, band=len(rs) - len(q), quota=len(q),
                        explained=round(1 - mix["unexplained"] / max(1, len(q)), 3),
                        quota_golds=sum(r["gold"] for r in q), **{c: mix[c] for c in CHANNELS}))
    return out


def _group(rows, keys):
    g = collections.defaultdict(list)
    for r in rows:
        g[tuple(r[k] for k in keys)].append(r)
    return g


def rank_bin(rank, edges=(50, 100)):
    if rank is None:
        return "none"
    return next((f"<={e}" for e in edges if rank <= e), f">{edges[-1]}")


PREDICTORS = {
    "pooled": lambda r: "all",
    "by_channel": lambda r: r["channel"],
    "by_school_rank": lambda r: rank_bin(r["school_online_rank"]),
    "by_team_rank": lambda r: rank_bin(r["online_rank"], (30, 100, 300)),
}


def channel_rho_check(rows):
    """Which grouping of quota teams predicts each contest's quota golds?
    Gold rates per group come from the other seasons (leave-season-out),
    shrunk to the pooled rate by one pseudo-team."""
    seasons = sorted({r["season"] for r in rows})
    res = []
    for test in seasons:
        q_train = [r for r in rows if r["season"] != test and r["admission"] == "quota"]
        pooled = sum(r["gold"] for r in q_train) / len(q_train)
        rates = {}
        for name, key in PREDICTORS.items():
            n, g = collections.Counter(key(r) for r in q_train), collections.Counter()
            for r in q_train:
                g[key(r)] += r["gold"]
            rates[name] = {k: (g[k] + pooled) / (n[k] + 1) for k in n}
        for (season, site), rs in _group([r for r in rows if r["season"] == test], ("season", "site")).items():
            q = [r for r in rs if r["admission"] == "quota"]
            res.append(dict(season=season, site=site, actual=sum(r["gold"] for r in q),
                            **{name: sum(rates[name].get(key(r), pooled) for r in q)
                               for name, key in PREDICTORS.items()}))
    actual = np.array([r["actual"] for r in res])
    err = {k: float(np.mean(np.abs(np.array([r[k] for r in res]) - actual))) for k in PREDICTORS}
    corr = {k: float(np.corrcoef([r[k] for r in res], actual)[0, 1]) for k in PREDICTORS}
    return {"contests": res, "mae": {k: round(v, 2) for k, v in err.items()},
            "corr": {k: round(v, 3) for k, v in corr.items()}}


TOP_SCHOOLS = 50  # combined online school rank that separates contending quota teams


def elite_entitlement(season, site, data, ev):
    """Quota seats the WF/host channels promise top-50 online schools at a
    site, known before registration: each such school's WF/host seats, capped
    by its headroom (privileged cap minus band slots)."""
    rule = data["rules"][(season, site)]
    slots = og.school_slots(season, rule, data)
    cap = rule.get("school_cap_privileged") or rule.get("school_cap") or 4
    total = 0
    for r in data["online_schools"]:
        if r["season"] == season and r["table"] == "combined" and int(r["rank"]) <= TOP_SCHOOLS:
            seats = sum(CHANNEL_SEATS[c] for c in school_channels(season, site, r["school"], ev)
                        if c in ("wf", "host"))
            total += min(seats, max(0, cap - slots.get(og.norm_school(r["school"]), 0)))
    return total


def school_rank_quota_model(rows, data, ev):
    """Best predictor of quota golds, fit on ``rows`` (``team_table``):
    quota teams of top-50 online schools and of all other schools win gold at
    ``rho_top50`` and ``rho_rest`` times the band teams' rate, and top-50
    schools fill ``kappa`` quota seats per WF/host entitlement seat."""
    band = [r for r in rows if r["admission"] == "band"]
    band_rate = sum(r["gold"] for r in band) / len(band)
    quota = [r for r in rows if r["admission"] == "quota"]
    top = [r for r in quota if r["school_online_rank"] and r["school_online_rank"] <= TOP_SCHOOLS]
    rest = [r for r in quota if not (r["school_online_rank"] and r["school_online_rank"] <= TOP_SCHOOLS)]
    contests = sorted({(r["season"], r["site"]) for r in rows})
    entitled = sum(elite_entitlement(s, site, data, ev) for s, site in contests)
    return {"rho_top50": sum(r["gold"] for r in top) / len(top) / band_rate,
            "rho_rest": sum(r["gold"] for r in rest) / len(rest) / band_rate,
            "rho_pooled": sum(r["gold"] for r in quota) / len(quota) / band_rate,
            "kappa": len(top) / entitled, "contests": len(contests)}


def pre_contest_check(rows, data, ev):
    """Quota golds per contest predicted before registration, leave-season-out:
    pooled rate on the notices' planned quota seats vs the school-rank model
    (kappa x top-50 WF/host entitlement at rho_top50, the rest at rho_rest).
    Also the top-50 quota seat forecast itself."""
    res = []
    for test in sorted({r["season"] for r in rows}):
        train = [r for r in rows if r["season"] != test]
        m = school_rank_quota_model(train, data, ev)
        band = [r for r in train if r["admission"] == "band"]
        band_rate = sum(r["gold"] for r in band) / len(band)
        planned = {k: _planned_quota(*k, data) for k in _group(train, ("season", "site"))}
        pooled_rate = sum(r["gold"] for r in train if r["admission"] == "quota") / sum(planned.values())
        for (season, site), rs in _group([r for r in rows if r["season"] == test], ("season", "site")).items():
            q = [r for r in rs if r["admission"] == "quota"]
            plan = _planned_quota(season, site, data)
            top = min(plan, m["kappa"] * elite_entitlement(season, site, data, ev))
            res.append(dict(season=season, site=site, actual=sum(r["gold"] for r in q),
                            pooled=plan * pooled_rate,
                            school_rank=band_rate * (m["rho_top50"] * top + m["rho_rest"] * (plan - top)),
                            top50_actual=sum(1 for r in q if r["school_online_rank"]
                                             and r["school_online_rank"] <= TOP_SCHOOLS),
                            top50_forecast=round(top, 1)))
    actual = np.array([r["actual"] for r in res])
    out = {"contests": res}
    for k in ("pooled", "school_rank"):
        pred = np.array([r[k] for r in res])
        out[k] = {"mae": round(float(np.mean(np.abs(pred - actual))), 2),
                  "corr": round(float(np.corrcoef(pred, actual)[0, 1]), 3)}
    t = np.array([[r["top50_forecast"], r["top50_actual"]] for r in res])
    out["top50_seats"] = {"mae": round(float(np.mean(np.abs(t[:, 0] - t[:, 1]))), 1),
                          "corr": round(float(np.corrcoef(t[:, 0], t[:, 1])[0, 1]), 3)}
    return out


def _planned_quota(season, site, data):
    rule = data["rules"][(season, site)]
    return max(0, rule["official_capacity"] - sum(og.school_slots(season, rule, data).values()))


def repeat_schools(rows, top=15):
    """Schools that most often send quota teams, with their channels."""
    per = collections.defaultdict(list)
    for r in rows:
        if r["admission"] == "quota":
            per[r["school"]].append(r)
    out = []
    for school, rs in sorted(per.items(), key=lambda kv: -len(kv[1]))[:top]:
        out.append(dict(school=school, quota_teams=len(rs),
                        contests=len({(r["season"], r["site"]) for r in rs}),
                        golds=sum(r["gold"] for r in rs),
                        channels=dict(collections.Counter(r["channel"] for r in rs).most_common())))
    return out


def school_rank_profile(rows):
    """Quota teams by their school's combined online rank (None = no ranked team)."""
    bins = [(1, 50), (51, 100), (101, 200), (201, 400), (401, 10 ** 6)]
    out = []
    for lo, hi in bins + [(None, None)]:
        if lo is None:
            rs = [r for r in rows if r["admission"] == "quota" and r["school_online_rank"] is None]
            label = "not ranked online"
        else:
            rs = [r for r in rows if r["admission"] == "quota" and r["school_online_rank"]
                  and lo <= r["school_online_rank"] <= hi]
            label = f"{lo}-{hi}" if hi < 10 ** 6 else f"{lo}+"
        mix = collections.Counter(r["channel"] for r in rs)
        out.append(dict(school_rank=label, quota_teams=len(rs), golds=sum(r["gold"] for r in rs),
                        top_channels=dict(mix.most_common(3))))
    return out


# ------------------------------------------------------------------ report

def markdown(res):
    L = ["# Quota entrants at Asia East regionals, 2023-2025", "",
         "Generated by `python3 -m arch_b.quota_teams`. A quota team is an official team beyond its "
         "school's online rank-band slots (the school's strongest-online teams take the band slots). "
         "Channels come from official evidence (`data/ec_online/quota_evidence.json`). Per-team rows: "
         "`output/quota_teams.csv`.", "",
         "## Validation against Shanghai's published per-school lists", "",
         "| season | schools listed / attending | band slots match | quota teams | covered by published reward | "
         "from unlisted schools | reward schools explained by WF/host | unexplained reward schools |",
         "|---|---|---|---|---|---|---|---|"]
    for s, v in res["shanghai_check"].items():
        L.append(f"| {s} | {v['published_schools']} / {v['attending_schools']} | {v['band_slots_match']} | "
                 f"{v['quota_teams']} | {v['quota_teams_covered_by_published_reward']} | "
                 f"{v['quota_teams_from_unlisted_schools']} | {v['reward_schools_explained_by_wf_or_host']}/"
                 f"{v['reward_schools_published']} | {', '.join(v['reward_schools_unexplained'])} |")
    for s, v in res["shanghai_check"].items():
        L.append(f"\n{s}: {sum(v['schools_over_published_total'].values())} teams above their school's "
                 f"published total; WF/host schools inferred but not rewarded: "
                 f"{', '.join(v['inferred_wf_host_not_rewarded']) or 'none'}.")
    L += ["", "## Channels (pooled 2023-2025 mainland regionals)", "",
          "| group | teams | golds | gold rate | vs band | medal rate | linked online | median online rank |",
          "|---|---|---|---|---|---|---|---|"]
    for c, v in res["channels"].items():
        L.append(f"| {c} | {v['teams']} | {v['gold']} | {v['gold_rate']:.1%} | {v['relative_gold_rate']} | "
                 f"{v['medal_rate']:.0%} | {v['linked_online']:.0%} | {v['median_online_rank']} |")
    L += ["", "## Channel mix per contest", "",
          "| season | site | band | quota | explained | quota golds | " + " | ".join(CHANNELS) + " |",
          "|---|---|---|---|---|---|" + "---|" * len(CHANNELS)]
    for t in res["contests"]:
        L.append(f"| {t['season']} | {t['site']} | {t['band']} | {t['quota']} | {t['explained']:.0%} | "
                 f"{t['quota_golds']} | " + " | ".join(str(t[c]) for c in CHANNELS) + " |")
    rc = res["channel_rho_check"]
    L += ["", "## What predicts a contest's quota golds? (leave-season-out)", "",
          "Each contest's quota golds predicted from gold rates of the other seasons, grouping quota "
          "teams by: nothing (pooled rho), channel, school combined online rank (<=50, <=100, >100, "
          "none), or the team's own linked online rank (<=30, <=100, <=300, >300, unlinked).", "",
          "| grouping | MAE (golds per contest) | correlation |", "|---|---|---|"]
    L += [f"| {k} | {rc['mae'][k]} | {rc['corr'][k]} |" for k in PREDICTORS]
    pc = res["pre_contest_check"]
    L += ["", "## Before registration: forecasting a contest's quota golds (leave-season-out)", "",
          "Only rules and evidence known before registration: the notice's planned quota seats "
          "(capacity minus band slots), and top-50 schools' WF/host entitlement. The school-rank "
          "model (backtested in `arch_b.online_gold` as `rules_line_school_rank`) expects kappa x "
          "entitlement quota teams from "
          "top-50 schools at their gold rate and the remaining planned seats at the others' rate.", "",
          "| predictor | MAE (golds per contest) | correlation |", "|---|---|---|",
          f"| pooled rate x planned quota seats | {pc['pooled']['mae']} | {pc['pooled']['corr']} |",
          f"| school-rank model | {pc['school_rank']['mae']} | {pc['school_rank']['corr']} |", "",
          f"Top-50 quota seats forecast vs actual: MAE {pc['top50_seats']['mae']}, correlation "
          f"{pc['top50_seats']['corr']}. Full-data fit: " +
          ", ".join(f"{k} {v:.3f}" for k, v in res["school_rank_model"].items() if k != "contests") + ".", "",
          "| season | site | quota golds | pooled | school-rank | top-50 quota seats (forecast / actual) |",
          "|---|---|---|---|---|---|"]
    L += [f"| {c['season']} | {c['site']} | {c['actual']} | {c['pooled']:.1f} | {c['school_rank']:.1f} | "
          f"{c['top50_forecast']} / {c['top50_actual']} |" for c in pc["contests"]]
    L += ["", "## Quota teams by their school's combined online rank", "",
          "| school rank | quota teams | golds | top channels |", "|---|---|---|---|"]
    for b in res["school_rank_profile"]:
        L.append(f"| {b['school_rank']} | {b['quota_teams']} | {b['golds']} | {b['top_channels']} |")
    L += ["", "## Schools sending the most quota teams", "",
          "| school | quota teams | contests | golds | channels |", "|---|---|---|---|---|"]
    for s in res["repeat_schools"]:
        L.append(f"| {s['school']} | {s['quota_teams']} | {s['contests']} | {s['golds']} | {s['channels']} |")
    L += ["", "Evidence gaps: " + " ".join(res["gaps"])]
    return "\n".join(L) + "\n"


def run():
    data = og.load()
    strengths = og.online_strengths(data["online_teams"])
    ev = load_evidence()
    rows = team_table(data, strengths, ev)
    medals = medal_lookup(data)
    for r in rows:
        r["medal"] = medals.get((r["season"], r["site"], r["team"], r["school"]), "")
    res = {"shanghai_check": shanghai_check(rows, ev), "channels": channel_summary(rows, medals),
           "contests": by_contest(rows), "channel_rho_check": channel_rho_check(rows),
           "pre_contest_check": pre_contest_check(rows, data, ev),
           "school_rank_model": school_rank_quota_model(rows, data, ev),
           "school_rank_profile": school_rank_profile(rows), "repeat_schools": repeat_schools(rows),
           "gaps": ev["gaps"]}
    return rows, res


def main():
    rows, res = run()
    og.OUT.mkdir(exist_ok=True)
    with open(og.OUT / "quota_teams.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    md = markdown(res)
    (og.OUT / "quota_teams.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
