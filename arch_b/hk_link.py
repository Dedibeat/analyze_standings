"""Link Hong Kong / Macau regional teams to their online-qualifier results.

``arch_b.online_gold`` links mainland regional teams by school + team name or
by a roster sharing >= 2 members, all in Chinese.  Hong Kong / Macau boards
list English (pinyin) member, team and school names, so neither works there.

Here each Chinese roster member is turned into pinyin with ``pypinyin`` (all
readings of each character, surname first and last, compound surnames split
as two characters; ``lyu``/``lv``/``lu`` merged) and a regional team links to
the roster team of the same season sharing the most members, if >= 2.  The
match ignores school; the school is checked afterwards where the English name
is in ``school_names_en.csv`` (PTA's English names, ``add_pta_rosters.py``).
Teams without members fall back to school + team name (school mapped through
the same table).  The XCPCIO boards of Hong Kong 2022 and Macau 2023 carry no
members at all, so those seasons can only link by name.

    python3 -m arch_b.hk_link

Writes ``output/hk_link.json`` and ``output/hk_link.md``.
"""

import collections
import csv
import itertools
import json
import math
import re

from pypinyin import Style, pinyin

from arch_b.online_gold import DATA, OUT, load, norm_name, norm_school, online_strengths

SITES = ("hongkong", "macau")
COMPOUND_SURNAMES = set("欧阳 司马 上官 诸葛 东方 皇甫 尉迟 公孙 慕容 长孙 宇文 司徒 夏侯 令狐 端木 "
                        "独孤 南宫 西门 申屠 轩辕 闻人 赫连 澹台 万俟 呼延".split())
LOCAL = re.compile(r"hong kong|macau|macao", re.I)
NOT_LOCAL = re.compile(r"shenzhen|guangzhou|united international", re.I)  # mainland campuses


def canon_person(s):
    """Letters only; ü spellings (lyu / lv / lu, nyu / nv / nu) merged."""
    s = re.sub(r"[^a-z]", "", s.lower())
    return s.replace("lyu", "lu").replace("nyu", "nu").replace("v", "u")


def pinyin_variants(name, cap=16):
    """Canonical pinyin spellings of a Chinese name in both name orders."""
    han = "".join(c for c in name if "一" <= c <= "鿿")
    if len(han) < 2:
        return set()
    out = set()
    for k in (2, 1) if han[:2] in COMPOUND_SURNAMES else (1,):
        parts = [["".join(p) for p in itertools.islice(
            itertools.product(*pinyin(seg, style=Style.NORMAL, heteronym=True)), cap)]
            for seg in (han[:k], han[k:])]
        for sur, given in itertools.product(*parts):
            out.update((canon_person(sur + given), canon_person(given + sur)))
    return out


def norm_school_en(s):
    return re.sub(r"^the", "", re.sub(r"[^a-z]", "", s.lower()))


def school_map():
    with open(DATA / "school_names_en.csv", encoding="utf-8") as f:
        return {norm_school_en(r["school_en"]): norm_school(r["school"]) for r in csv.DictReader(f)}


def roster_index(rosters):
    """{(season, pinyin): {(school, team)}} over every online roster member."""
    idx = collections.defaultdict(set)
    for r in rosters:
        team = (norm_school(r["school"]), norm_name(r["team"]))
        for m in r["members"].split("|"):
            for v in pinyin_variants(m):
                idx[(r["season"], v)].add(team)
    return idx


def link_hk(data, strengths):
    """Official Hong Kong / Macau rows with the linked online team, if any."""
    idx, en2cn = roster_index(data["online_rosters"]), school_map()
    online_schools = {(k[0], k[1]) for k in strengths}
    out = []
    for r in data["regional_teams"]:
        if r["site"] not in SITES or r["official"] != "1":
            continue
        season, mapped = r["season"], en2cn.get(norm_school_en(r["school"]))
        members = [m for m in r["members"].split("|") if m and "coach" not in m.lower()]
        votes = collections.Counter()
        for m in members:
            votes.update(idx.get((season, canon_person(m)), ()))
        ranked = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))
        key, how, ambiguous = None, "", False
        if ranked and ranked[0][1] >= 2:
            key, how = (season, *ranked[0][0]), "members"
            ambiguous = len(ranked) > 1 and ranked[1][1] == ranked[0][1]
        elif mapped and (season, mapped, norm_name(r["team"])) in strengths:
            key, how = (season, mapped, norm_name(r["team"])), "name"
        if key is None:
            check = ""
        else:
            check = "unmapped" if mapped is None else "same" if mapped == key[1] else "different"
        if key is not None and key not in strengths:  # roster team with no ranking row
            key, how = None, "roster_only"
        if how in ("members", "name"):
            reason = ""
        elif LOCAL.search(r["school"]) and not NOT_LOCAL.search(r["school"]):
            reason = "local"
        elif mapped and (season, mapped) in online_schools:
            reason = "school_online"  # the school played online, this line-up did not
        else:
            reason = "school_not_online"
        out.append(dict(season=season, site=r["site"], school=r["school"], team=r["team"],
                        members="|".join(members), official_rank=r["official_rank"], medal=r["medal"],
                        gold=int(r["medal"] == "gold"), link=how, school_check=check,
                        ambiguous=ambiguous, unlinked_reason=reason,
                        online_school=key[1] if key else None, online_team=key[2] if key else None,
                        online_ranks=strengths[key]["ranks"] if key else None,
                        x=round(strengths[key]["x"], 4) if key else None))
    return out


def summary(rows):
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["season"], r["site"])].append(r)
    out = []
    for (season, site), rs in sorted(by.items()):
        linked = [r for r in rs if r["x"] is not None]
        golds = [r for r in rs if r["gold"]]
        gold_ranks = sorted(math.exp(-r["x"]) for r in golds if r["x"] is not None)
        out.append(dict(
            season=season, site=site, official=len(rs), with_members=sum(bool(r["members"]) for r in rs),
            linked=len(linked), by_members=sum(r["link"] == "members" for r in rs),
            by_name=sum(r["link"] == "name" for r in rs), golds=len(golds),
            golds_linked=sum(r["x"] is not None for r in golds),
            school_check=dict(collections.Counter(r["school_check"] for r in linked)),
            ambiguous=sum(r["ambiguous"] for r in linked),
            roster_only=sum(r["link"] == "roster_only" for r in rs),
            unlinked=dict(collections.Counter(r["unlinked_reason"] for r in rs if r["x"] is None)),
            gold_online_rank_median=round(gold_ranks[len(gold_ranks) // 2], 1) if gold_ranks else None))
    return out


def markdown(result):
    lines = ["# Hong Kong / Macau teams linked to online results", "",
             "Official teams linked to an online-qualifier result (`arch_b.hk_link`). Members are matched",
             "in pinyin against the same season's online rosters (>= 2 shared members); otherwise school +",
             "team name. Online rank = exp(mean log rank) over the rounds entered.", "",
             "| contest | official | with members | linked | by members | by name | golds linked | "
             "school check same / unmapped / different | gold median online rank |",
             "|---|---|---|---|---|---|---|---|---|"]
    for s in result["summary"]:
        c = s["school_check"]
        lines.append(f"| {s['season']} {s['site']} | {s['official']} | {s['with_members']} | "
                     f"{s['linked']} ({s['linked'] / s['official']:.0%}) | {s['by_members']} | {s['by_name']} | "
                     f"{s['golds_linked']} / {s['golds']} | {c.get('same', 0)} / {c.get('unmapped', 0)} / "
                     f"{c.get('different', 0)} | {s['gold_online_rank_median'] or '-'} |")
    lines += ["", "Unlinked teams by reason (`local`: Hong Kong/Macau school; `school_online`: the school",
              "has online teams that season but not this line-up; `school_not_online`: no online team of",
              "the school, or its English name is not in `school_names_en.csv`):", "",
              "| contest | local | school_online | school_not_online | roster only |", "|---|---|---|---|---|"]
    for s in result["summary"]:
        u = s["unlinked"]
        lines.append(f"| {s['season']} {s['site']} | {u.get('local', 0)} | {u.get('school_online', 0)} | "
                     f"{u.get('school_not_online', 0)} | {s['roster_only']} |")
    lines += ["", "Unlinked golds:", ""]
    lines += [f"- {r['season']} {r['site']} #{r['official_rank']} {r['school']}: {r['team']} "
              f"({r['unlinked_reason']})" for r in result["rows"] if r["gold"] and r["x"] is None]
    lines += ["", "Member links whose school disagrees with the English-name map:", ""]
    lines += [f"- {r['season']} {r['school']}: {r['team']} -> {r['online_school']} / {r['online_team']}"
              for r in result["rows"] if r["school_check"] == "different"] or ["- none"]
    return "\n".join(lines) + "\n"


def run():
    data = load()
    rows = link_hk(data, online_strengths(data["online_teams"]))
    return {"summary": summary(rows), "rows": rows}


def main():
    result = run()
    OUT.mkdir(exist_ok=True)
    (OUT / "hk_link.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md = markdown(result)
    (OUT / "hk_link.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
