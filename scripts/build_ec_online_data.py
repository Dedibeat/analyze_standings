#!/usr/bin/env python3
"""Build the Asia East online-qualifier / regional-result data layer.

Sources (all official, fetched over HTTPS and cached under
``data/ec_online_cache/`` which is git-ignored):

* icpc.pku.edu.cn ranking notices: per-round team rankings, per-round school
  rankings and the combined school ranking that the slot rules use
  (seasons 2022-2026, 47th-51st).
* board.xcpcio.com: config/team/run data for every ordinary regional of the
  47th-50th seasons.  Official standings (solved, penalty) are recomputed from
  the submissions; the official flag and medal counts come from the board.

Outputs (``data/ec_online/``):

* ``online_teams.csv``   season, round, rank, school, team, solved, penalty
* ``online_schools.csv`` season, table (round1/round2/combined), rank, school
* ``online_rosters.csv`` season, round, school, team, members (2022-2024 only)
* ``regional_teams.csv`` one row per regional team with official rank and medal
* ``sources.json``       every URL used

The hand-encoded slot rules live in ``data/ec_online/slot_rules.json``; they
are not generated.

    python3 scripts/build_ec_online_data.py
"""

import bisect
import collections
import csv
import json
import math
import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "ec_online"
CACHE = ROOT / "data" / "ec_online_cache"
DOCS = "https://icpc.pku.edu.cn/docs/"

# season -> (round-1 team, round-2 team, round-1 school, round-2 school, combined school)
ONLINE_PDFS = {
    2022: ("20220918211105845189", "20220926081057819146",
           "20220918211121009200", "20220926081113919273", "20220929102543719363"),
    2023: ("20230919164621038819", "20230926152218286119",
           "20230919164631587945", "20230926152228426276", "20230926160353392359"),
    2024: ("20240924164622836969", "20240924164702184075",
           "20240924164730277117", "20240924164757740205", "20240924164833395322"),
    2025: ("2025-09/5db61bb82ae3433dbee2ba13fc5d0f94", "2025-09/3a9335df9003434e87737f02751221cb",
           "2025-09/94d12beea0324adcb9797df628a79fd9", "2025-09/9f4fdc3287154c0cb792c0a50146f708",
           "2025-09/79d2425fcdfb4ec9a391ae90b3a84c37"),
    2026: ("2026-09/2a8987cbca5e47bcb65e8895958ff2fd", "2026-09/61386cddf36f4ca1bd7aa996bde4e8de",
           "2026-09/48c0eb24cb104b3e87aba6ffd7eeb260", "2026-09/c3b4b63a095f4d30a21de83994349d72",
           "2026-09/6541acc790aa476a84ec865634480d5e"),
}

# Online registration lists (报名公示) with rosters.  Each entry: (season,
# round, pdf id, layout, column x-starts).  "team" layouts have one row per
# team with three member columns; "member" layouts repeat the team per member.
# 2025/2026 lists are only published on uep.pintia.cn and are not included.
ROSTER_PDFS = [
    (2022, 1, "20220909125001826069", "team",
     {"school": 53, "team": 157, "coach": 279, "m1": 344, "m2": 409, "m3": 474}),
    (2022, 2, "20220916083700096162", "member",
     {"school": 53, "team": 185, "coach": 330, "member": 411}),
    (2023, 1, "20230907095701223660", "team",
     {"school": 53, "team": 151, "coach": 347, "m1": 411, "m2": 506, "m3": 613}),
    (2023, 2, "20230907095710619754", "team",
     {"school": 53, "team": 207, "coach": 399, "m1": 466, "m2": 568, "m3": 662}),
    (2024, 1, "20240907232241590153", "member",
     {"regno": 57, "team": 114, "team_en": 285, "school": 490, "member": 590, "coach": 650}),
    (2024, 2, "20240911174933682697", "member",
     {"regno": 53, "team": 118, "team_en": 229, "school": 431, "member": 528, "coach": 593}),
]

# season -> {site: XCPCIO board path}.  2022 (47th) regionals were held online.
REGIONALS = {
    2022: {"xian": "47th/xian", "jinan": "47th/jinan", "hangzhou": "47th/hangzhou",
           "nanjing": "47th/nanjing", "hefei": "47th/hefei", "shenyang": "47th/shenyang",
           "hongkong": "47th/hongkong"},
    2023: {"nanjing": "48th/nanjing", "xian": "48th/xian", "jinan": "48th/jinan",
           "hefei": "48th/hefei", "hangzhou": "48th/hangzhou", "macau": "48th/macau",
           "shenyang": "48th/shenyang"},
    2024: {"kunming": "49th/kunming", "nanjing": "49th/nanjing", "chengdu": "49th/chengdu",
           "hongkong": "49th/hongkong", "shanghai": "49th/shanghai",
           "hangzhou": "49th/hangzhou", "shenyang": "49th/shenyang"},
    2025: {"nanjing": "50th/nanjing", "wuhan": "50th/wuhan", "chengdu": "50th/chengdu",
           "hongkong": "50th/hongkong", "xian": "50th/xian", "shanghai": "50th/shanghai",
           "shenyang": "50th/shenyang"},
}

# The 47th boards all carry a 35/70/105 medal block regardless of field size,
# so it is treated as a placeholder and the 10% rule is used instead.
PLACEHOLDER_MEDAL_SEASONS = {2022}

LABELS = {"rank": {"#", "排名"}, "school": {"学校"}, "team": {"队名", "队伍", "队伍名"},
          "solved": {"题数", "过题数"}, "penalty": {"罚时", "总用时"}}
EMPTY_CELL_COST = 1e4


def nfkc(s):
    return unicodedata.normalize("NFKC", s or "")


def fetch(url, dest):
    """Download ``url`` to ``dest`` once (cache hit if the file exists)."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-sSfL", "--retry", "3", "--max-time", "300",
                    "-o", str(dest), url], check=True)
    return dest


# ---------------------------------------------------------------- PDF parsing

def _words(pdf):
    out = subprocess.run(["pdftotext", "-tsv", str(pdf), "-"],
                         capture_output=True, text=True, check=True).stdout
    words = []
    for line in out.splitlines()[1:]:
        p = line.split("\t")
        if p[0] != "5":
            continue
        left, top, width, height = map(float, p[6:10])
        words.append(dict(page=int(p[1]), l=left, r=left + width, b=top + height,
                          y=top + height / 2, x=left + width / 2, s=nfkc(p[11])))
    return words


def _lines(words):
    """Group one column's words into visual lines, top to bottom."""
    lines = []
    for w in sorted(words, key=lambda w: (w["y"], w["l"])):
        if lines and abs(lines[-1][0]["y"] - w["y"]) < 3:
            lines[-1].append(w)
        else:
            lines.append([w])
    return [(sum(w["y"] for w in ln) / len(ln),
             " ".join(w["s"] for w in sorted(ln, key=lambda w: w["l"]))) for ln in lines]


def _segment(lines, ys, maxk=20):
    """Split the column's lines into one contiguous block per row anchor.

    Wrapped cells are vertically centred on their row, so the block whose mean
    y is closest to the anchor wins; empty blocks are heavily penalised.
    """
    n, m, inf = len(lines), len(ys), float("inf")
    dp = [[inf] * (n + 1) for _ in range(m + 1)]
    back = [[0] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = 0.0
    for j in range(1, m + 1):
        for i in range(n + 1):
            for k in range(min(maxk, i) + 1):
                prev = dp[j - 1][i - k]
                if prev == inf:
                    continue
                cost = EMPTY_CELL_COST if k == 0 else (
                    sum(y for y, _ in lines[i - k:i]) / k - ys[j - 1]) ** 2
                if prev + cost < dp[j][i]:
                    dp[j][i], back[j][i] = prev + cost, k
    if dp[m][n] == inf:
        return None
    blocks, i = [None] * m, n
    for j in range(m, 0, -1):
        k = back[j][i]
        blocks[j - 1], i = lines[i - k:i], i - k
    return blocks


def _join(block):
    txt = ""
    for _, t in block:
        if txt and txt[-1].isascii() and txt[-1].isalnum() and t[:1].isascii() and t[:1].isalnum():
            txt += " "
        txt += t
    return txt


def parse_team_pdf(pdf):
    """Rows of an official online team ranking: rank (None for unranked
    zero-solve teams), school, team, solved, penalty (minutes)."""
    words = _words(pdf)
    head = {}
    for w in words:
        for key, labels in LABELS.items():
            if w["page"] == 1 and w["s"] in labels and key not in head:
                head[key] = w
    for w in words:  # per-problem columns of the 2022/2023 layouts
        if w["page"] == 1 and re.fullmatch(r"[A-M]", w["s"]) and abs(w["y"] - head["rank"]["y"]) < 6:
            head["prob_" + w["s"]] = w
    cols = sorted(head, key=lambda k: head[k]["l"])
    header_bottom = max(head[k]["b"] for k in cols)
    body = [w for w in words if not (w["page"] == 1 and w["b"] <= header_bottom + 1)]
    bounds = []  # column boundary = x crossed by the fewest words
    for a, b in zip(cols, cols[1:]):
        lo, hi = int(head[a]["x"]), int(head[b]["l"])
        if hi <= lo:
            hi = int(head[b]["x"])
        best = None
        for x in range(lo, hi + 1):
            crossed = sum(1 for w in body if w["l"] < x < w["r"])
            if best is None or crossed <= best[0]:
                best = (crossed, x)
        bounds.append(best[1])
    right_edge = head[cols[-1]]["r"] + 40

    def column(w):
        return None if w["x"] > right_edge else cols[bisect.bisect(bounds, w["x"])]

    rows = []
    for page in sorted({w["page"] for w in body}):
        by_col = collections.defaultdict(list)
        for w in body:
            if w["page"] == page and column(w):
                by_col[column(w)].append(w)
        anchors = sorted((w for w in by_col["solved"] if w["s"].isdigit()), key=lambda w: w["y"])
        if not anchors:
            continue
        ys = [a["y"] for a in anchors]
        recs = [{"solved": int(a["s"])} for a in anchors]
        for key in ("rank", "penalty"):
            for r in recs:
                r[key] = None
            for w in by_col[key]:
                i = min(range(len(ys)), key=lambda i: abs(ys[i] - w["y"]))
                if abs(ys[i] - w["y"]) < 4 and w["s"].isdigit():
                    recs[i][key] = int(w["s"])
        for key in ("school", "team"):
            blocks = _segment(_lines(by_col[key]), ys)
            if blocks is None:
                raise ValueError(f"{pdf}: page {page} cannot segment {key}")
            for r, block in zip(recs, blocks):
                r[key] = _join(block)
        rows.extend(recs)
    return rows


def parse_school_pdf(pdf):
    """(school, rank) pairs of an official school ranking."""
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                          capture_output=True, text=True, check=True).stdout
    out, pending = [], None
    for line in text.splitlines():
        line = nfkc(line).strip()
        if not line:
            continue
        m = re.match(r"^(\S.*?)\s+(\d+)$", line)
        if m and m.group(1) not in ("学校", "排名", "学校排名"):
            out.append((m.group(1).strip(), int(m.group(2))))
            pending = None
        elif line.isdigit() and pending:  # rank wrapped onto its own line
            out.append((pending, int(line)))
            pending = None
        elif not re.search(r"\d", line) and line not in ("学校 排名", "学校 学校排名"):
            pending = line
    return out


def parse_roster_pdf(pdf, layout, starts):
    """Teams of a registration list: dicts with school, team, members (list).

    Words go to the last column whose x-start is left of them.  Lines holding
    a member name anchor a row; wrapped fragments (long school or team names)
    join the nearest anchor line on the same page.
    """
    names = sorted(starts, key=starts.get)
    xs = [starts[n] - 3 for n in names]
    member_cols = [n for n in names if n.startswith("m")]
    header_bottom = None
    rows = []
    for page_words in _pages(_words(pdf)):
        if header_bottom is None:  # page 1: drop the header line(s)
            first = min(w["y"] for w in page_words if w["s"] not in ("",))
            header_bottom = max(w["b"] for w in page_words if w["y"] < first + 8)
            page_words = [w for w in page_words if w["y"] > header_bottom]
        lines = collections.defaultdict(lambda: collections.defaultdict(list))
        for w in page_words:
            i = bisect.bisect(xs, w["l"]) - 1
            if i >= 0:
                lines[round(w["y"])][names[i]].append(w)
        ys = sorted(lines)
        anchors = [y for y in ys if any(lines[y].get(c) for c in member_cols)]
        cells = {y: collections.defaultdict(list) for y in anchors}
        for y in ys:
            if not anchors:
                break
            a = min(anchors, key=lambda a: abs(a - y))
            for col, ws in lines[y].items():
                cells[a][col].append((y, " ".join(w["s"] for w in sorted(ws, key=lambda w: w["l"]))))
        for a in anchors:
            rec = {col: _join(sorted(v)) for col, v in cells[a].items()}
            rows.append(rec)
    teams = []
    if layout == "team":
        for r in rows:
            members = [r[c] for c in member_cols if r.get(c)]
            if teams and not r.get("school") and not r.get("team"):
                teams[-1]["members"].extend(members)  # member on its own line
                continue
            teams.append(dict(school=r.get("school", ""), team=r.get("team", ""), members=members))
    else:  # one row per member; a new team starts when the key changes
        key_cols = ("regno",) if "regno" in starts else ("school", "team")
        for r in rows:
            key = tuple(r.get(c, "") for c in key_cols)
            if not teams or teams[-1]["_key"] != key or not all(key):
                teams.append(dict(_key=key, school=r.get("school", ""),
                                  team=r.get("team", ""), members=[]))
            if r.get("member"):
                teams[-1]["members"].append(r["member"])
        for t in teams:
            t.pop("_key")
    return teams


def _pages(words):
    by_page = collections.defaultdict(list)
    for w in words:
        by_page[w["page"]].append(w)
    return [by_page[p] for p in sorted(by_page)]


# ----------------------------------------------------------- XCPCIO standings

def _text(value):
    if isinstance(value, dict):
        texts = value.get("texts", {})
        return texts.get("zh-CN") or texts.get("en") or next(iter(texts.values()), "")
    return str(value or "")


def regional_standings(board):
    base = f"https://board.xcpcio.com/data/icpc/{board}/"
    cache = CACHE / "xcpcio" / board.replace("/", "_")
    config = json.loads(fetch(base + "config.json", cache / "config.json").read_text())
    teams = json.loads(fetch(base + "team.json", cache / "team.json").read_text())
    runs = json.loads(fetch(base + "run.json", cache / "run.json").read_text())
    teams = list(teams.values()) if isinstance(teams, dict) else teams
    orgs = {}
    if any("organization_id" in t for t in teams):
        orgs = {o["id"]: o["name"] for o in json.loads(
            fetch(base + "organizations.json", cache / "organizations.json").read_text())}
    unit = (config.get("options") or {}).get("submission_timestamp_unit")
    per_second = 1000 if unit == "millisecond" else 1
    penalty = config.get("penalty", 1200)

    by_cell = collections.defaultdict(list)
    for r in sorted(runs, key=lambda r: (r["timestamp"], str(r.get("id")))):
        by_cell[(str(r["team_id"]), str(r["problem_id"]))].append(r)
    score = collections.defaultdict(lambda: [0, 0])
    for (tid, _), cell in by_cell.items():
        wrong = 0
        for r in cell:
            if r["status"] == "ACCEPTED":
                minutes = r["timestamp"] // per_second // 60
                score[tid][0] += 1
                score[tid][1] += minutes * 60 + wrong * penalty
                break
            if r["status"] not in ("COMPILATION_ERROR", "PENDING", "FROZEN", "UNKNOWN"):
                wrong += 1

    rows = []
    for t in teams:
        tid = str(t.get("id", t.get("team_id")))
        group = t.get("group")
        official = "official" in group if group is not None else bool(t.get("official"))
        girl = ("girl" in group) if group is not None else bool(t.get("girl"))
        members = [_text(m.get("name") if isinstance(m, dict) else m) for m in t.get("members") or []]
        solved, pen = score[tid]
        rows.append(dict(team_id=tid, team=_text(t.get("name")),
                         school=_text(t.get("organization") or orgs.get(t.get("organization_id"), "")),
                         members="|".join(members), official=int(official), girl=int(girl),
                         solved=solved, penalty_minutes=pen // 60))
    official = sorted((r for r in rows if r["official"]),
                      key=lambda r: (-r["solved"], r["penalty_minutes"]))
    for r in rows:
        r["official_rank"] = ""
    for i, r in enumerate(official):
        tied = i and (r["solved"], r["penalty_minutes"]) == (official[i - 1]["solved"], official[i - 1]["penalty_minutes"])
        r["official_rank"] = official[i - 1]["official_rank"] if tied else i + 1
    return config, rows


def medal_counts(season, config, rows):
    """(gold, silver, bronze, source): board counts, else ICPC's 10/20/30%
    of official teams that solved at least one problem."""
    board = (config.get("medal") or {}).get("official")
    if board and season not in PLACEHOLDER_MEDAL_SEASONS:
        return board["gold"], board["silver"], board["bronze"], "board"
    n = sum(1 for r in rows if r["official"] and r["solved"] > 0)
    gold = math.ceil(0.1 * n)
    silver = math.ceil(0.3 * n) - gold
    bronze = math.ceil(0.6 * n) - gold - silver
    return gold, silver, bronze, "rule_10_20_30"


# ---------------------------------------------------------------------- main

def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources = {"online_pdfs": {}, "xcpcio_boards": {}}
    team_rows, school_rows = [], []
    for season, ids in ONLINE_PDFS.items():
        urls = [DOCS + i + ".pdf" for i in ids]
        sources["online_pdfs"][season] = dict(zip(
            ["round1_teams", "round2_teams", "round1_schools", "round2_schools", "combined_schools"], urls))
        pdfs = [fetch(u, CACHE / "pdf" / (i.replace("/", "_") + ".pdf")) for u, i in zip(urls, ids)]
        for rnd, pdf in enumerate(pdfs[:2], 1):
            for r in parse_team_pdf(pdf):
                team_rows.append(dict(season=season, round=rnd, rank=r["rank"] or "",
                                      school=r["school"], team=r["team"],
                                      solved=r["solved"], penalty=r["penalty"]))
        for table, pdf in zip(("round1", "round2", "combined"), pdfs[2:]):
            for school, rank in parse_school_pdf(pdf):
                school_rows.append(dict(season=season, table=table, rank=rank, school=school))
    write_csv(OUT / "online_teams.csv",
              ["season", "round", "rank", "school", "team", "solved", "penalty"], team_rows)
    write_csv(OUT / "online_schools.csv", ["season", "table", "rank", "school"], school_rows)

    roster_rows = []
    sources["online_rosters"] = {}
    for season, rnd, pid, layout, starts in ROSTER_PDFS:
        url = DOCS + pid + ".pdf"
        sources["online_rosters"][f"{season}/round{rnd}"] = url
        for t in parse_roster_pdf(fetch(url, CACHE / "pdf" / (pid + ".pdf")), layout, starts):
            roster_rows.append(dict(season=season, round=rnd, school=t["school"], team=t["team"],
                                    members="|".join(t["members"])))
    write_csv(OUT / "online_rosters.csv", ["season", "round", "school", "team", "members"], roster_rows)

    regional_rows = []
    for season, sites in REGIONALS.items():
        for site, board in sites.items():
            config, rows = regional_standings(board)
            gold, silver, bronze, how = medal_counts(season, config, rows)
            sources["xcpcio_boards"][f"{season}/{site}"] = f"https://board.xcpcio.com/icpc/{board}"
            for r in rows:
                rank = r["official_rank"]
                medal = ""
                if rank and r["solved"] > 0:
                    medal = ("gold" if rank <= gold else "silver" if rank <= gold + silver
                             else "bronze" if rank <= gold + silver + bronze else "")
                regional_rows.append(dict(season=season, site=site, medal_source=how, medal=medal, **r))
    write_csv(OUT / "regional_teams.csv",
              ["season", "site", "team_id", "school", "team", "members", "official", "girl",
               "solved", "penalty_minutes", "official_rank", "medal", "medal_source"], regional_rows)
    (OUT / "sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=1) + "\n")
    print(f"online teams {len(team_rows)}, school rows {len(school_rows)}, "
          f"regional teams {len(regional_rows)}")


if __name__ == "__main__":
    main()
