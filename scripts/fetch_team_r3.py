#!/usr/bin/env python3
"""Download the team account's QOJ submissions and the contests they were made in.

    QOJ_USERNAME=Dedibeat QOJ_PASSWORD=... python3 scripts/fetch_team_r3.py [contest_id ...]

The submissions are always TEAM_R3's; QOJ_USERNAME is only the account that
reads the pages. TEAM_R3 itself has QOJ "Training Mode" on (kept on for
spoiler-free virtuals), which answers every /contest/<id>/standings with 404,
so log in with a personal account (Dedibeat) to get the boards.

Everything goes under data/team_r3/ and is reused on the next run: a file that
already exists is not fetched again (delete it to refresh). The submission list
itself is re-read every run so new submissions are picked up.

    submissions.json                 every submission of the account (newest first)
    code/<submission_id>.txt         its source
    contests/<id>/dashboard.json     name, year, problems (id/label/name), attachments
    contests/<id>/attachments/       every dashboard attachment (statements,
                                     tutorials, ...), PDFs also as .txt
    contests/<id>/statements/<L>.pdf per-problem statement (+ .txt); when QOJ
                                     refuses the PDF (4113: 403), <L>.html and
                                     <L>.txt from the problem page instead
    contests/<id>/standings_all.json      board with unofficial/virtual rows
                                          (TEAM_R3's virtual row is on it)
    contests/<id>/standings_official.json board with official rows only

Contests are the ones given on the command line plus every contest the account
submitted in. All requests use the shared browserless QOJ session. Parsing
reuses ../qoj-intergration/qoj.py. Needs curl_cffi and pdftotext.
"""

import argparse
import html
import json
import re
import sys
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError

if __package__:
    from .qoj_auth import BASE, QOJError, authenticate
else:
    from qoj_auth import BASE, QOJError, authenticate

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "qoj-intergration"))
import qoj  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "team_r3"
TEAM = "TEAM_R3"
ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
CELL = re.compile(r"<td>(.*?)</td>", re.S)
# qoj.CONTEST_PROBLEM_RE misses links with a /statement/<lang> suffix (e.g. contest 2575)
PROBLEM = re.compile(r'<tr>\s*<td(?:\s+[^>]*)?>([A-Z]+)</td>\s*<td>\s*'
                     r'<a href="/contest/\d+/problem/(\d+)(?:/[^"]*)?">(.+?)</a>', re.S)
ARTICLE = re.compile(r'<article class="uoj-article[^"]*"\s*>(.*?)</article>', re.S)
CODE = re.compile(r'<pre><code class="sh_[^"]*">(.*?)</code></pre>', re.S)


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
        r = s.get("/submissions", params={"submitter": user, "page": page}).text
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
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def pdf_with_text(path, data):
    save(path, data)
    if data[:4] == b"%PDF":
        path.with_suffix(".txt").write_text(qoj.pdf_to_text(data), encoding="utf-8", newline="\n")


def fetch_contest(session, cid):
    d = OUT / "contests" / str(cid)
    url = f"{BASE}/contest/{cid}"
    dash_path = d / "dashboard.json"
    if dash_path.exists():
        dash = json.loads(dash_path.read_text())
    else:
        page = session.get(url).text
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
            try:
                data = session.get(a["url"]).content
            except HTTPError as e:  # 4694's listed "Statements (en)" answers 404
                if e.code not in (403, 404):
                    raise
                print(f"  {cid} attachment {a['label']}: {e}", file=sys.stderr)
                continue
            ext = ".pdf" if data[:4] == b"%PDF" else ".zip" if data[:2] == b"PK" else ".bin"
            pdf_with_text(d / "attachments" / (stem + ext), data)
    for p in dash["problems"]:
        pdf = d / "statements" / f"{p['problem_label']}.pdf"
        if pdf.with_suffix(".txt").exists():
            continue
        try:
            data = session.get("/download.php", params={
                "type": "statement", "id": p["problem_id"], "contest_id": cid,
            }).content
        except HTTPError as e:
            if e.code not in (403, 404):
                raise
            data = b""
        if data[:4] == b"%PDF":
            pdf_with_text(pdf, data)
            continue
        # no PDF served: the problem page carries the statement as HTML (LaTeX source)
        page = session.get(f"{url}/problem/{p['problem_id']}").text
        m = ARTICLE.search(page)
        if not m or not m.group(1).strip():  # 4694: empty article, statement only in the PDF iframe
            print(f"  {cid} {p['problem_label']}: no statement", file=sys.stderr)
            continue
        save(pdf.with_suffix(".html"), m.group(1).encode())
        pdf.with_suffix(".txt").write_text(text(re.sub(r"<(?:/p|br\s*/?|/h\d|/li)>", "\n",
                                                       m.group(1))), encoding="utf-8", newline="\n")
    for name, options in (("standings_all", {}),
                          ("standings_official", {"cookies": {"show_unofficial_mode": ""},
                                                  "discard_cookies": True})):
        if (d / f"{name}.json").exists():
            continue
        try:
            page = session.get(f"{url}/standings", **options).text
            rows = qoj.parse_full_standings(page)
        except HTTPError as e:  # 404 under Training Mode (TEAM_R3)
            if e.code != 404:
                raise
            print(f"  {cid} {name}: {e}", file=sys.stderr)
            continue
        save(d / f"{name}.json", rows)
    return dash


def fetch_team(session, contest_ids):
    subs = fetch_submissions(session, TEAM)
    save(OUT / "submissions.json", subs)
    print(f"{len(subs)} submissions", file=sys.stderr)
    for sub in subs:
        path = OUT / "code" / f"{sub['submission_id']}.txt"
        if path.exists():
            continue
        try:
            page = session.get(f"/submission/{sub['submission_id']}").text
        except HTTPError as e:
            if e.code not in (403, 404):
                raise
            page = ""
        m = CODE.search(page)
        if not m:
            print(f"  submission {sub['submission_id']}: no source on the page", file=sys.stderr)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html.unescape(m.group(1)), encoding="utf-8", newline="\n")

    contests = sorted(set(contest_ids) |
                      {x["contest_id"] for x in subs if x["contest_id"]})
    for cid in contests:
        dash = fetch_contest(session, cid)
        print(f"contest {cid}: {dash['title']}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("contest_ids", metavar="contest_id", nargs="*", type=int)
    args = parser.parse_args()
    with closing(authenticate()) as session:
        fetch_team(session, args.contest_ids)


if __name__ == "__main__":
    try:
        main()
    except (QOJError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
