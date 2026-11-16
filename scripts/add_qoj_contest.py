#!/usr/bin/env python3
"""Add one QOJ contest's standings to data/tagged.json for the rating fit.

    QOJ_USERNAME=... QOJ_PASSWORD=... python3 scripts/add_qoj_contest.py 4071 \
        --name "EC Online (I)" --region "Asia East Continent"

QOJ shows contest pages only to logged-in users, so the script logs in with
QOJ_USERNAME / QOJ_PASSWORD through the browserless flow of
``../p1/qoj/BROWSERLESS_AUTH.md`` (curl_cffi Chrome impersonation, md5 password,
``_token`` from the page's JS; the session cookies are cached per account in the
git-ignored ``data/.cookies-<user>.json`` and reused until they go stale) and
reads two pages:

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

A contest id already in tagged.json is left as it is; ``--refresh`` re-fetches it
and replaces the stored entry (used to pull a board's newer standings).
"""

import argparse
import hashlib
import html
import json
import os
import re
import urllib.parse

from curl_cffi import requests as cr_requests  # TLS impersonation: QOJ 403s plain clients

BASE = "https://qoj.ac"
DATA = os.path.join(os.path.dirname(__file__), os.pardir, "data")
TAGGED = os.path.join(DATA, "tagged.json")
TOKEN = re.compile(r'_token\s*:\s*"([A-Za-z0-9]{60})"')
MEMBERS = re.compile(r"^(.*\S) \(([^()]*)\)$")


class Qoj:
    """Browserless session (``../p1/qoj/BROWSERLESS_AUTH.md``): Chrome TLS
    fingerprint, md5 password, ``_token`` from the page's JS, cookies cached per
    account in the git-ignored ``data/.cookies-<user>.json``."""

    def __init__(self):
        self.session = cr_requests.Session(impersonate="chrome136")
        self.user = None

    def get(self, path, data=None):
        url = BASE + path
        resp = (self.session.post(url, data=data, timeout=60) if data is not None
                else self.session.get(url, timeout=60))
        if "Just a moment" in resp.text[:3000]:
            raise SystemExit(f"Cloudflare challenge on {path}; retry later")
        if urllib.parse.urlparse(resp.url).path == "/login" and path != "/login":
            raise SystemExit(f"QOJ asked for a login again on {path}")
        return resp.text

    def _logged_in(self):
        return "My Profile" in self.get(f"/user/profile/{self.user}")

    def login(self):
        self.user = os.environ.get("QOJ_USERNAME")
        password = os.environ.get("QOJ_PASSWORD")
        if not self.user:
            raise SystemExit("set QOJ_USERNAME (and QOJ_PASSWORD for a fresh login): "
                             "QOJ shows contests only to logged-in users")
        cookies = os.path.join(DATA, f".cookies-{self.user}.json")
        if os.path.exists(cookies):
            with open(cookies) as f:
                self.session.headers["Cookie"] = "; ".join(
                    f"{k}={v}" for k, v in json.load(f).items())
            if self._logged_in():
                return
        if not password:
            raise SystemExit("saved cookies are stale; set QOJ_PASSWORD")
        token = TOKEN.search(self.get("/login"))
        if not token:
            raise SystemExit("QOJ's login page has no _token; the login needs updating")
        form = {"_token": token.group(1), "login": "", "username": self.user,
                "password": hashlib.md5(password.encode()).hexdigest()}  # md5 hex, not plaintext
        if self.get("/login", form).strip() != "ok":
            raise SystemExit("QOJ rejected the login")
        if not self._logged_in():
            raise SystemExit("QOJ said ok but the session is not authenticated")
        with open(cookies, "w") as f:
            json.dump({c.name: c.value for c in self.session.cookies.jar}, f, indent=2)


def page_var(page, name):
    m = re.search(rf"^{name}=(.*);$", page, re.M)
    if not m:
        raise SystemExit(f"standings page has no `{name}`; the parser needs updating")
    return json.loads(m.group(1))


def _team_fields(raw, affiliation):
    """Split a QOJ display name into (team, members, affiliation).

    Two encodings exist: ``Team (m1, m2)`` (Universal Cup, online rounds) and the
    domjudge ``Affiliation - Team - m1, m2`` form of the imported ICPC regionals,
    which carries the affiliation in the name (the affiliation field is empty
    there). The ``Aff: team`` colon form is not split: team names contain colons.
    """
    team = re.sub(r"\s+", " ", raw).strip()
    affiliation = (affiliation or "").strip() or None
    members = []
    m = MEMBERS.match(team)
    if m and ("," in m.group(2) or (m.group(2)[:1].isupper() and " " in m.group(2))):
        team, members = m.group(1).strip(), [x.strip() for x in m.group(2).split(",") if x.strip()]
    if affiliation is None and " - " in team:
        parts = [x.strip() for x in team.split(" - ")]
        affiliation = parts[0] or None
        if not members and len(parts) >= 3 and "," in parts[-1]:
            members = [x.strip() for x in parts[-1].split(",") if x.strip()]
            team = " - ".join(parts[1:-1])
        else:
            team = " - ".join(x for x in parts[1:] if x).strip(" -")
    return team, members, affiliation


def standing_row(entry, cells, labels):
    total_score, penalty, user, rank = entry[0], entry[1], entry[2], entry[3]
    raw = user[3]
    team, members, affiliation = _team_fields(
        raw, user[6] if len(user) > 6 else None)
    if isinstance(cells, list):  # PHP encodes cells keyed 0..k-1 (or none) as a list
        cells = dict(enumerate(cells))
    problems = {}
    for idx in sorted(cells, key=int):
        score, seconds, _, wrong = cells[idx][:4]
        problems[labels[int(idx)]] = {"solved": score > 0, "score": score,
                                      "time_seconds": seconds, "wrong_attempts": wrong}
    return {
        "rank": rank, "team_id": user[0], "team_name": team, "members": members,
        "affiliation": affiliation, "display_name_raw": raw,
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
    parser.add_argument("--refresh", action="store_true",
                        help="re-fetch a contest already in tagged.json and replace it")
    args = parser.parse_args()

    with open(TAGGED, encoding="utf-8") as f:
        contests = json.load(f)
    existing = next((i for i, c in enumerate(contests)
                     if c["contest_id"] == args.contest_id), None)
    if existing is not None and not args.refresh:
        print(f"contest {args.contest_id} is already in tagged.json; nothing to do")
        return

    qoj = Qoj()
    qoj.login()
    contest = fetch_contest(qoj, args.contest_id, args.name, args.region, args.year)
    if existing is None:
        contests.append(contest)
        verb = "added"
    else:
        old = contests[existing]
        contests[existing] = contest
        verb = (f"refreshed {len(old['standings'])} -> {len(contest['standings'])} rows, "
                f"{len(old['problems'])} -> {len(contest['problems'])} problems;")
    with open(TAGGED, "w", encoding="utf-8") as f:
        json.dump(contests, f, ensure_ascii=False)
    print(f"{verb} {contest['contest_id']} {contest['contest_name']} {contest['year']}: "
          f"{len(contest['problems'])} problems, {len(contest['standings'])} rows, "
          + " ".join(f"{p['problem_label']}={p['problem_solved_in_contest']}"
                     for p in contest["problems"]))


if __name__ == "__main__":
    main()
