#!/usr/bin/env python3
"""Add one QOJ contest's standings to data/tagged.json for the rating fit.

    QOJ_USERNAME=... QOJ_PASSWORD=... python3 scripts/add_qoj_contest.py 4071 \
        --name "EC Online (I)" --region "Asia East Continent"

QOJ shows contest pages only to logged-in users, so the script logs in with
QOJ_USERNAME / QOJ_PASSWORD (the same login as ../my-react-app/src/qoj_sync.py)
and reads two pages:

* the dashboard (``/contest/<id>``) for problem names and, unless ``--year`` is
  given, the year in the contest title;
* the standings (``/contest/<id>/standings``) as QOJ serves them by default,
  with "Show unofficial" on -- the same row set the earlier QOJ fetches kept.
  The page embeds ``standings``, ``score``, ``problems`` and ``problems_id`` as
  JSON, one variable per line.

Rows use the existing tagged.json format. A cell is solved when its score is
positive: an ICPC board totals 100 per positive cell, and 97 marks an accepted
run that later failed added tests. A name ending in "(A, B, C)" gives the team
name and members; other names are kept whole (EC online-round rosters are
attached afterwards by scripts/attach_online_rosters.py). Statements,
editorials, submissions and solutions are not fetched.

A contest id already in tagged.json is left as it is.
"""

import argparse
import hashlib
import html
import http.cookiejar
import json
import os
import re
import urllib.parse
import urllib.request

BASE = "https://qoj.ac"
TAGGED = os.path.join(os.path.dirname(__file__), os.pardir, "data", "tagged.json")
USER_AGENT = (  # QOJ answers 403 to non-browser user agents
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)
TOKEN = re.compile(r'_token\s*:\s*"([A-Za-z0-9]{60})"')
MEMBERS = re.compile(r"^(.*\S) \(([^()]*)\)$")


class Qoj:
    def __init__(self):
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def get(self, path, data=None):
        req = urllib.request.Request(BASE + path, data=data, headers={
            "User-Agent": USER_AGENT, "Referer": f"{BASE}/login"})
        with self.opener.open(req, timeout=60) as resp:
            if urllib.parse.urlparse(resp.geturl()).path == "/login" and path != "/login":
                raise SystemExit(f"QOJ asked for a login again on {path}")
            return resp.read().decode("utf-8")

    def login(self):
        username, password = os.environ.get("QOJ_USERNAME"), os.environ.get("QOJ_PASSWORD")
        if not username or not password:
            raise SystemExit("set QOJ_USERNAME and QOJ_PASSWORD: QOJ shows contests only "
                             "to logged-in users")
        token = TOKEN.search(self.get("/login"))
        if not token:
            raise SystemExit("QOJ's login page has no _token; the login needs updating")
        form = urllib.parse.urlencode({
            "_token": token.group(1), "login": "", "username": username,
            "password": hashlib.md5(password.encode()).hexdigest(),  # QOJ expects md5 hex
        }).encode()
        if self.get("/login", form).strip() != "ok":
            raise SystemExit("QOJ rejected the login")


def page_var(page, name):
    m = re.search(rf"^{name}=(.*);$", page, re.M)
    if not m:
        raise SystemExit(f"standings page has no `{name}`; the parser needs updating")
    return json.loads(m.group(1))


def standing_row(entry, cells, labels):
    total_score, penalty, user, rank = entry[0], entry[1], entry[2], entry[3]
    raw = user[3]
    m = MEMBERS.match(raw)
    team, members = (m.group(1), [x.strip() for x in m.group(2).split(",")]) if m else (raw, [])
    if isinstance(cells, list):  # PHP encodes cells keyed 0..k-1 (or none) as a list
        cells = dict(enumerate(cells))
    problems = {}
    for idx in sorted(cells, key=int):
        score, seconds, _, wrong = cells[idx][:4]
        problems[labels[int(idx)]] = {"solved": score > 0, "score": score,
                                      "time_seconds": seconds, "wrong_attempts": wrong}
    return {
        "rank": rank, "team_id": user[0], "team_name": team, "members": members,
        "affiliation": (user[6] if len(user) > 6 else None) or None,
        "display_name_raw": raw,
        "total_solved": sum(p["solved"] for p in problems.values()),
        "total_score": total_score, "penalty_seconds": penalty, "problems": problems,
    }


def fetch_contest(qoj, cid, name, region, year=None):
    dashboard = qoj.get(f"/contest/{cid}")
    names = {int(pid): html.unescape(title) for pid, title in re.findall(
        rf'<a href="/contest/{cid}/problem/(\d+)">([^<]*)</a>', dashboard)}
    if year is None:
        title = re.search(r"<title>([^<]*)</title>", dashboard).group(1)
        m = re.search(r"\b(20\d\d)\b", title)
        if not m:
            raise SystemExit(f"no year in the title {title!r}; pass --year")
        year = int(m.group(1))

    page = qoj.get(f"/contest/{cid}/standings")
    if page_var(page, "contest_type") != "ICPC":
        raise SystemExit(f"contest {cid} is not an ICPC-format contest")
    ids, labels = page_var(page, "problems"), page_var(page, "problems_id")
    score = page_var(page, "score")
    standings = [standing_row(e, score.get(e[2][0], {}), labels)
                 for e in page_var(page, "standings")]
    problems = [{
        "problem_id": pid, "problem_label": label, "problem_name": names[pid],
        "problem_url": f"{BASE}/contest/{cid}/problem/{pid}",
        "problem_solved_in_contest": sum(r["problems"].get(label, {}).get("solved", False)
                                         for r in standings),
    } for pid, label in zip(ids, labels)]
    return {
        "contest_id": cid, "contest_name": name, "year": year, "region": region,
        "contest_url": f"{BASE}/contest/{cid}", "editorial_url": None,
        "problems": problems, "standings": standings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("contest_id", type=int)
    parser.add_argument("--name", required=True, help='short name, e.g. "EC Online (I)"')
    parser.add_argument("--region", required=True, help='e.g. "Asia East Continent"')
    parser.add_argument("--year", type=int, help="default: the year in the QOJ title")
    args = parser.parse_args()

    with open(TAGGED, encoding="utf-8") as f:
        contests = json.load(f)
    if any(c["contest_id"] == args.contest_id for c in contests):
        print(f"contest {args.contest_id} is already in tagged.json; nothing to do")
        return

    qoj = Qoj()
    qoj.login()
    contest = fetch_contest(qoj, args.contest_id, args.name, args.region, args.year)
    contests.append(contest)
    with open(TAGGED, "w", encoding="utf-8") as f:
        json.dump(contests, f, ensure_ascii=False)
    print(f"added {contest['contest_id']} {contest['contest_name']} {contest['year']}: "
          f"{len(contest['problems'])} problems, {len(contest['standings'])} rows, "
          + " ".join(f"{p['problem_label']}={p['problem_solved_in_contest']}"
                     for p in contest["problems"]))


if __name__ == "__main__":
    main()
