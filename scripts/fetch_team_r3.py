#!/usr/bin/env python3
"""Download the team account's QOJ submissions and the contests they were made in.

    QOJ_USERNAME=TEAM_R3 QOJ_PASSWORD=... python3 scripts/fetch_team_r3.py [contest_id ...]

Everything goes under data/team_r3/ and is reused on the next run: a file that
already exists is not fetched again (delete it to refresh). The submission list
itself is re-read every run so new submissions are picked up.

    submissions.json                 every submission of the account (newest first)
    code/<submission_id>.txt         its source
    contests/<id>/dashboard.json     name, year, problems (id/label/name), attachments
    contests/<id>/attachments/       every dashboard attachment (statements,
                                     tutorials, ...), PDFs also as .txt
    contests/<id>/statements/<L>.pdf per-problem statement (+ .txt), when QOJ has one

No scoreboards: TEAM_R3 has QOJ "Training Mode" on, which answers every
/contest/<id>/standings with 404 (kept on deliberately, for spoiler-free
virtuals). Boards come from data/tagged.json and XCPCIO instead.

Contests are the ones given on the command line plus every contest the account
submitted in. Login is the browserless flow of ../p1/qoj/BROWSERLESS_AUTH.md
(curl_cffi Chrome impersonation, md5 password, _token from the page's JS).
Parsing reuses ../qoj-intergration/qoj.py. Needs curl_cffi and pdftotext.
"""

import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
from pathlib import Path

from curl_cffi import requests as cr

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "qoj-intergration"))
import qoj  # noqa: E402

BASE = "https://qoj.ac"
OUT = Path(__file__).resolve().parent.parent / "data" / "team_r3"
COOKIES = OUT / ".cookies.json"
TOKEN = re.compile(r'_token\s*:\s*"([A-Za-z0-9]{60})"')
ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
CELL = re.compile(r"<td>(.*?)</td>", re.S)
# qoj.CONTEST_PROBLEM_RE misses links with a /statement/<lang> suffix (e.g. contest 2575)
PROBLEM = re.compile(r'<tr>\s*<td(?:\s+[^>]*)?>([A-Z]+)</td>\s*<td>\s*'
                     r'<a href="/contest/\d+/problem/(\d+)(?:/[^"]*)?">(.+?)</a>', re.S)
CODE = re.compile(r'<pre><code class="sh_[^"]*">(.*?)</code></pre>', re.S)


def polite(fetch, *args, **kw):
    """Run one request, pacing them and waiting out Cloudflare's 429 rate limit.

    `fetch` is a session GET (checked by status) or a qoj.fetch_* helper (raises
    HTTPError 429). Too-fast fetching gets every page answered with a 429
    "Just a moment" page."""
    for attempt in range(8):
        time.sleep(1.5)
        try:
            r = fetch(*args, **kw)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
        else:
            if getattr(r, "status_code", 200) != 429:
                return r
        wait = 30 * (attempt + 1)
        print(f"  rate-limited; waiting {wait}s", file=sys.stderr)
        time.sleep(wait)
    raise SystemExit("still rate-limited after 8 tries; re-run later (finished files are kept)")


def session_from(jar):
    s = cr.Session(impersonate="chrome136")
    s.headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in jar.items())
    return s


def logged_in(s, user):
    return "My Profile" in polite(s.get, f"{BASE}/user/profile/{user}", timeout=40).text


def login():
    user, password = os.environ.get("QOJ_USERNAME"), os.environ.get("QOJ_PASSWORD")
    if not user:
        raise SystemExit("set QOJ_USERNAME (and QOJ_PASSWORD for a fresh login)")
    if COOKIES.exists():
        jar = json.loads(COOKIES.read_text())
        s = session_from(jar)
        if logged_in(s, user):
            return s, user, jar
    if not password:
        raise SystemExit("saved cookies are stale; set QOJ_PASSWORD")
    s = cr.Session(impersonate="chrome136")
    token = TOKEN.search(s.get(f"{BASE}/login", timeout=40).text)
    if not token:
        raise SystemExit("no _token on /login; the login flow has changed")
    body = s.post(f"{BASE}/login", timeout=40, data={
        "_token": token.group(1), "login": "", "username": user,
        "password": hashlib.md5(password.encode()).hexdigest()}).text.strip()
    if body != "ok" or not logged_in(s, user):
        raise SystemExit(f"QOJ rejected the login ({body[:40]!r})")
    jar = {c.name: c.value for c in s.cookies.jar}
    OUT.mkdir(parents=True, exist_ok=True)
    COOKIES.write_text(json.dumps(jar))
    return s, user, jar


def text(cell):
    return html.unescape(re.sub(r"<.*?>", "", cell)).strip()


def parse_submission_rows(page):
    rows = []
    for row in ROW.findall(page[page.find("<tbody>"):]):
        cells = CELL.findall(row)
        if len(cells) != 9:
            continue
        prob = re.search(r'href="/(?:contest/(\d+)/)?problem/(\d+)"', cells[1])
        score = re.search(r'data-full="([\d.]+)" data-score="([\d.]+)"', cells[3])
        when = re.search(r'datetime="([^"]+)"', cells[8])
        rows.append({
            "submission_id": int(re.search(r"/submission/(\d+)", cells[0]).group(1)),
            "contest_id": int(prob.group(1)) if prob and prob.group(1) else None,
            "problem_id": int(prob.group(2)) if prob else None,
            "problem": text(cells[1]),
            # QOJ marks a submission made during the (virtual) contest with a <sup>#</sup>
            "in_contest": "<sup>" in cells[2],
            "verdict": text(cells[3]),
            "score": float(score.group(2)) if score else None,
            "full_score": float(score.group(1)) if score else None,
            "time": text(cells[4]), "memory": text(cells[5]),
            "language": text(cells[6]), "size": text(cells[7]),
            "submit_time": when.group(1) if when else text(cells[8]),
        })
    return rows


def fetch_submissions(s, user):
    subs, page = [], 1
    while True:
        r = polite(s.get, f"{BASE}/submissions?submitter={user}&page={page}", timeout=40).text
        rows = parse_submission_rows(r)
        subs += rows
        pages = [int(p) for p in re.findall(r"page=(\d+)", r)]
        if not rows or page >= max(pages, default=1):
            return subs
        page += 1


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def pdf_with_text(path, data):
    save(path, data)
    if data[:4] == b"%PDF":
        path.with_suffix(".txt").write_text(qoj.pdf_to_text(data), encoding="utf-8")


def fetch_contest(cid):
    d = OUT / "contests" / str(cid)
    url = f"{BASE}/contest/{cid}"
    dash_path = d / "dashboard.json"
    if dash_path.exists():
        dash = json.loads(dash_path.read_text())
    else:
        page = polite(qoj.fetch_text, url)
        dash = {"contest_id": cid, "title": text(qoj.H1_RE.search(page).group(1)),
                **qoj.parse_dashboard_metadata(page),
                "problems": [{"problem_id": int(pid), "problem_label": lab,
                              "problem_name": text(name)}
                             for lab, pid, name in PROBLEM.findall(page)],
                "attachments": qoj.parse_dashboard_attachments(page)}
        save(dash_path, dash)
    for i, a in enumerate(dash["attachments"]):
        stem = re.sub(r"[^\w().-]+", "_", f"{i}-{a['label']}")
        if not list((d / "attachments").glob(stem + ".*")):
            data = polite(qoj.fetch_pdf, a["url"])
            ext = ".pdf" if data[:4] == b"%PDF" else ".zip" if data[:2] == b"PK" else ".bin"
            pdf_with_text(d / "attachments" / (stem + ext), data)
    for p in dash["problems"]:
        pdf = d / "statements" / f"{p['problem_label']}.pdf"
        miss = pdf.with_suffix(".missing")
        if pdf.exists() or miss.exists():
            continue
        try:
            data = polite(qoj.fetch_pdf, f"{BASE}/download.php?type=statement&id={p['problem_id']}"
                                 f"&contest_id={cid}")
        except OSError as e:
            data = b""
            print(f"  {cid} {p['problem_label']}: no statement ({e})", file=sys.stderr)
        if data[:4] == b"%PDF":
            pdf_with_text(pdf, data)
        else:
            save(miss, data)  # QOJ served no per-problem PDF; the full set is in attachments
    return dash


def main():
    s, user, jar = login()
    os.environ["QOJ_COOKIES"] = "; ".join(f"{k}={v}" for k, v in jar.items())

    subs = fetch_submissions(s, user)
    save(OUT / "submissions.json", subs)
    print(f"{len(subs)} submissions", file=sys.stderr)
    for sub in subs:
        path = OUT / "code" / f"{sub['submission_id']}.txt"
        if path.exists():
            continue
        m = CODE.search(polite(s.get, f"{BASE}/submission/{sub['submission_id']}",
                               timeout=40).text)
        if not m:
            print(f"  submission {sub['submission_id']}: no source on the page", file=sys.stderr)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html.unescape(m.group(1)), encoding="utf-8")

    contests = sorted({int(c) for c in sys.argv[1:]} |
                      {x["contest_id"] for x in subs if x["contest_id"]})
    for cid in contests:
        dash = fetch_contest(cid)
        print(f"contest {cid}: {dash['title']}", file=sys.stderr)


if __name__ == "__main__":
    main()
